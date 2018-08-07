#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import requests
from datetime import datetime
from pytz import timezone
from time import sleep
from configobj import ConfigObj
from pyowm import OWM
from pymodbus.client.sync import ModbusSerialClient as ModbusClient

# read settings from config file
config = ConfigObj("pvoutput.txt")
SYSTEMID = config['SYSTEMID']
APIKEY = config['APIKEY']
OWMKey = config['OWMKEY']
OWMLon = float(config['Longitude'])
OWMLat = float(config['Latitude'])
LocalTZ = timezone(config['TimeZone'])


# Local time with timezone
def localnow():
    return datetime.now(tz=LocalTZ)


class Inverter(object):
    # Inverter properties
    status = -1
    pv_power = 0.0
    pv_volts = 0.0
    ac_volts = 0.0
    ac_power = 0.0
    wh_today = 0
    wh_total = 0
    temp = 0.0
    firmware = ''
    control_fw = ''
    model_no = ''
    serial_no = ''
    dtc = -1
    cmo_str = ''

    def __init__(self, address, port):
        """Return a Inverter object with port set to *port* and
         values set to their initial state."""
        self.inv = ModbusClient(method='rtu', port=port, baudrate=9600, stopbits=1,
                                parity='N', bytesize=8, timeout=1)
        self.unit = address
        self.date = timezone('UTC').localize(datetime(1970, 1, 1, 0, 0, 0))

    def read_inputs(self):
        """Try read input properties from inverter, return true if succeed"""
        ret = False

        if self.inv.connect():
            # by default read first 45 registers (from 0 to 44)
            # they contain all basic information needed to report
            rr = self.inv.read_input_registers(0, 45, unit=self.unit)
            if not rr.isError():
                ret = True

                self.status = rr.registers[0]
                if self.status != -1:
                    self.cmo_str = 'Status: '+str(self.status)
                # my setup will never use high nibble but I will code it anyway
                self.pv_power = float((rr.registers[1] << 16)+rr.registers[2])/10
                self.pv_volts = float(rr.registers[3])/10
                self.ac_power = float((rr.registers[11] << 16)+rr.registers[12])/10
                self.ac_volts = float(rr.registers[14])/10
                self.wh_today = float((rr.registers[26] << 16)+rr.registers[27])*100
                self.wh_total = float((rr.registers[28] << 16)+rr.registers[29])*100
                self.temp = float(rr.registers[32])/10
                self.date = localnow()

            else:
                self.status = -1
                ret = False

            self.inv.close()
        else:
            print 'Error connecting to port'
            ret = False

        return ret

    def version(self):
        """Read firmware version"""
        ret = False

        if self.inv.connect():
            # by default read first 45 holding registers (from 0 to 44)
            # they contain more than needed data
            rr = self.inv.read_holding_registers(0, 45, unit=self.unit)
            if not rr.isError():
                ret = True
                # returns G.1.8 on my unit
                self.firmware = \
                    str(chr(rr.registers[9] >> 8) + chr(rr.registers[9] & 0x000000FF) +
                        chr(rr.registers[10] >> 8) + chr(rr.registers[10] & 0x000000FF) +
                        chr(rr.registers[11] >> 8) + chr(rr.registers[11] & 0x000000FF))

                # does not return any interesting thing on my model
                self.control_fw = \
                    str(chr(rr.registers[12] >> 8) + chr(rr.registers[12] & 0x000000FF) +
                        chr(rr.registers[13] >> 8) + chr(rr.registers[13] & 0x000000FF) +
                        chr(rr.registers[14] >> 8) + chr(rr.registers[14] & 0x000000FF))

                # does match the label in the unit
                self.serial_no = \
                    str(chr(rr.registers[23] >> 8) + chr(rr.registers[23] & 0x000000FF) +
                        chr(rr.registers[24] >> 8) + chr(rr.registers[24] & 0x000000FF) +
                        chr(rr.registers[25] >> 8) + chr(rr.registers[25] & 0x000000FF) +
                        chr(rr.registers[26] >> 8) + chr(rr.registers[26] & 0x000000FF) +
                        chr(rr.registers[27] >> 8) + chr(rr.registers[27] & 0x000000FF))

                # as per Growatt protocol
                mo = (rr.registers[28] << 16) + rr.registers[29]
                self.model_no = (
                    'T' + str((mo & 0XF00000) >> 20) + ' Q' + str((mo & 0X0F0000) >> 16) +
                    ' P' + str((mo & 0X00F000) >> 12) + ' U' + str((mo & 0X000F00) >> 8) +
                    ' M' + str((mo & 0X0000F0) >> 4) + ' S' + str((mo & 0X00000F))
                )

                # 134 for my unit meaning single phase/single tracker inverter
                self.dtc = rr.registers[43]
            else:
                self.firmware = ''
                self.control_fw = ''
                self.model_no = ''
                self.serial_no = ''
                self.dtc = -1
                ret = False

            self.inv.close()
        else:
            print 'Error connecting to port'
            ret = False

        return ret


class Weather(object):
    API = ''
    lat = 0.0
    lon = 0.0
    temperature = 0.0
    cloud_pct = 0
    cmo_str = ''

    def __init__(self, API, lat, lon):
        self.API = API
        self.lat = lat
        self.lon = lon
        self.owm = OWM(self.API)

    def get(self):
        obs = self.owm.weather_at_coords(self.lat, self.lon)
        w = obs.get_weather()
        status = w.get_detailed_status()
        self.temperature = w.get_temperature(unit='celsius')['temp']
        self.cloud_pct = w.get_clouds()
        cmo_str = ('%s with cloud coverage of %s percent' % (status, self.cloud_pct))


def pvoutput(inv, owm=False):
    url_status = 'http://pvoutput.org/service/r2/addstatus.jsp'
    url_output = 'http://pvoutput.org/service/r2/addoutput.jsp'
    headers = {'X-Pvoutput-Apikey': APIKEY, 'X-Pvoutput-SystemId': SYSTEMID}

    # add status
    payload = {
        'd': inv.date.strftime('%Y%m%d'),
        't': inv.date.strftime('%H:%M'),
        'v2': inv.ac_power,
        'v6': inv.pv_volts,
        'v8': inv.ac_volts,
        'v9': inv.temp,
        'v10': inv.wh_total,
        'c1': 0,
        'm1': inv.cmo_str
    }
    # Only report total energy if it has changed since last upload
    if (pvoutput.wh_today_last > inv.wh_today) or \
       (pvoutput.wh_today_last < inv.wh_today):
        # wh_today increased or reset (should not but...) since last read
        pvoutput.wh_today_last = inv.wh_today
        payload['v1'] = inv.wh_today

    # temperature report only if available
    if owm and owm.fresh:
        payload['v5'] = owm.temperature
        payload['m1'] = payload['m1'] + ' - ' + owm.cmo_str

    r = requests.post(url_status, headers=headers, data=payload)
    print r.status_code

    # add output
#    payload = {
#        'd': inv.date.strftime('%Y%m%d'),
#        'g': inv.wh_today,
#        'cm': inv.cmo_str + ' - ' + owm.cmo_str
#    }
#    r = requests.post(url_output, headers=headers, data=payload)
#    print r.status_code, r.url
pvoutput.wh_today_last = 0


def main_loop():
    # init
    inv = Inverter(0x1, '/dev/ttyUSB0')
    inv.version()
    if OWMKey:
        owm = Weather(OWMKey, OWMLat, OWMLon)
        owm.fresh = False
    else:
        owm = False

    # start and stop monitoring (hour of the day)
    shStart = 5
    shStop = 21
    # Loop until end of universe
    while True:
        if shStart <= localnow().hour < shStop:
            # get fresh temperature from OWM
            if owm:
                try:
                    owm.get()
                    owm.fresh = True
                except Exception as e:
                    print "Error: %s".format(e)
                    owm.fresh = False

            # get readings from inverter, if success send  to pvoutput
            inv.read_inputs()
            if inv.status != -1:
                pvoutput(inv, owm)
                sleep(300)  # 5 minutes
            else:
                # some error
                sleep(60)  # 1 minute before try again
        else:
            # it is too late or too early, let's sleep until next shift
            hour = localnow().hour
            minute = localnow().minute
            if 24 > hour >= shStop:
                # before midnight
                snooze = (((shStart - hour) + 24) * 60) - minute
            elif shStart > hour <= 0:
                # after midnight
                snooze = ((shStart - hour) * 60) - minute
            print localnow().strftime('%Y-%m-%d %H:%M') + ' - Next shift starts in ' + \
                str(snooze) + ' minutes'
            sys.stdout.flush()
            snooze = snooze * 60  # seconds
            sleep(snooze)


if __name__ == '__main__':
    try:
        main_loop()
    except KeyboardInterrupt:
        print >> sys.stderr, '\nExiting by user request.\n'
        sys.exit(0)
