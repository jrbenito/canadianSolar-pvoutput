#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import requests
from datetime import datetime
from pytz import timezone
from time import sleep, time
from configobj import ConfigObj, ConfigObjError
from validate import Validator
from pyowm import OWM
from pymodbus.client.sync import ModbusSerialClient as ModbusClient

# Local time with timezone
def localnow():
    return datetime.now(tz=localnow.LocalTZ)


class Inverter(object):

    def __init__(self, address, port):
        """Return a Inverter object with port set to *port* and
        values set to their initial state."""
        self._inv = ModbusClient(method='rtu', port=port, baudrate=9600, stopbits=1,
                                 parity='N', bytesize=8, timeout=1)
        self._unit = address

        # Inverter properties
        self.date = timezone('UTC').localize(datetime(1970, 1, 1, 0, 0, 0))
        self.status = -1
        self.pv_power = 0.0
        self.pv_volts = 0.0
        self.ac_volts = 0.0
        self.ac_power = 0.0
        self.wh_today = 0
        self.wh_total = 0
        self.temp = 0.0
        self.firmware = ''
        self.control_fw = ''
        self.model_no = ''
        self.serial_no = ''
        self.dtc = -1
        self.cmo_str = ''

    def read_inputs(self):
        """Try read input properties from inverter, return true if succeed"""
        ret = False

        if self._inv.connect():
            # by default read first 45 registers (from 0 to 44)
            # they contain all basic information needed to report
            rr = self._inv.read_input_registers(0, 45, unit=self._unit)
            if not rr.isError():
                ret = True
                self.date = localnow()

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
            else:
                self.status = -1
                ret = False

            self._inv.close()
        else:
            print 'Error connecting to port'
            ret = False

        return ret

    def version(self):
        """Read firmware version"""
        ret = False

        if self._inv.connect():
            # by default read first 45 holding registers (from 0 to 44)
            # they contain more than needed data
            rr = self._inv.read_holding_registers(0, 45, unit=self._unit)
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

            self._inv.close()
        else:
            print 'Error connecting to port'
            ret = False

        return ret


class Weather(object):

    def __init__(self, API, lat, lon):
        self._API = API
        self._lat = float(lat)
        self._lon = float(lon)
        self._owm = OWM(self._API)

        self.temperature = 0.0
        self.cloud_pct = 0
        self.cmo_str = ''

    def get(self):
        obs = self._owm.weather_at_coords(self._lat, self._lon)
        w = obs.get_weather()
        status = w.get_detailed_status()
        self.temperature = w.get_temperature(unit='celsius')['temp']
        self.cloud_pct = w.get_clouds()
        self.cmo_str = ('%s with cloud coverage of %s percent' % (status, self.cloud_pct))


class PVOutputAPI(object):

    def __init__(self, API, system_id=None):
        self._API = API
        self._systemID = system_id
        self._wh_today_last = 0

    def add_status(self, payload, system_id=None):
        """Add live output data. Data should contain the parameters as described
        here: http://pvoutput.org/help.html#api-addstatus ."""
        sys_id = system_id if system_id is not None else self._systemID
        self.__call("https://pvoutput.org/service/r2/addstatus.jsp", payload, sys_id)

    def add_output(self, payload, system_id=None):
        """Add end of day output information. Data should be a dictionary with
        parameters as described here: http://pvoutput.org/help.html#api-addoutput ."""
        sys_id = system_id if system_id is not None else self._systemID
        self.__call("http://pvoutput.org/service/r2/addoutput.jsp", payload, sys_id)

    def __call(self, url, payload, system_id=None):
        headers = {
            'X-Pvoutput-Apikey': self._API,
            'X-Pvoutput-SystemId': system_id,
            'X-Rate-Limit': '1'
        }

        # Make tree attempts
        for i in range(3):
            try:
                r = requests.post(url, headers=headers, data=payload, timeout=10)
                reset = round(float(r.headers['X-Rate-Limit-Reset']) - time())
                if int(r.headers['X-Rate-Limit-Remaining']) < 10:
                    print("Only {} requests left, reset after {} seconds".format(
                        r.headers['X-Rate-Limit-Remaining'],
                        reset))
                if r.status_code == 403:
                    print("Forbidden: " + r.reason)
                    sleep(reset + 1)
                else:
                    r.raise_for_status()
                    break
            except requests.exceptions.HTTPError as errh:
                print(localnow().strftime('%Y-%m-%d %H:%M'), " Http Error:", errh)
            except requests.exceptions.ConnectionError as errc:
                print(localnow().strftime('%Y-%m-%d %H:%M'), "Error Connecting:", errc)
            except requests.exceptions.Timeout as errt:
                print(localnow().strftime('%Y-%m-%d %H:%M'), "Timeout Error:", errt)
            except requests.exceptions.RequestException as err:
                print(localnow().strftime('%Y-%m-%d %H:%M'), "OOps: Something Else", err)

            sleep(5)
        else:
            print(localnow().strftime('%Y-%m-%d %H:%M'),
                  "Failed to call PVOutput API after {} attempts.".format(i))

    def send_status(self, date, energy_gen=None, power_gen=None, energy_imp=None,
                    power_imp=None, temp=None, vdc=None, cumulative=False, vac=None,
                    temp_inv=None, energy_life=None, comments=None, power_vdc=None,
                    system_id=None):
        # format status payload
        payload = {
            'd': date.strftime('%Y%m%d'),
            't': date.strftime('%H:%M'),
        }

        # Only report total energy if it has changed since last upload
        # this trick avoids avg power to zero with inverter that reports
        # generation in 100 watts increments (Growatt and Canadian solar)
        if ((energy_gen is not None) and (self._wh_today_last != energy_gen)):
            self._wh_today_last = int(energy_gen)
            payload['v1'] = int(energy_gen)

        if power_gen is not None:
            payload['v2'] = float(power_gen)
        if energy_imp is not None:
            payload['v3'] = int(energy_imp)
        if power_imp is not None:
            payload['v4'] = float(power_imp)
        if temp is not None:
            payload['v5'] = float(temp)
        if vdc is not None:
            payload['v6'] = float(vdc)
        if cumulative is not None:
            payload['c1'] = 1
        if vac is not None:
            payload['v8'] = float(vac)
        if temp_inv is not None:
            payload['v9'] = float(temp_inv)
        if energy_life is not None:
            payload['v10'] = int(energy_life)
        if comments is not None:
            payload['m1'] = str(comments)[:30]
        # calculate efficiency
        if ((power_vdc is not None) and (power_vdc > 0) and (power_gen is not None)):
            payload['v12'] = float(power_gen) / float(power_vdc)

        # Send status
        self.add_status(payload, system_id)


def main_loop():

    # FIXME
    # this shall be delayed
    inv.version()

    # start and stop monitoring (hour of the day)
    shStart = 5
    shStop = 21
    # Loop until end of universe
    while True:
        if shStart <= localnow().hour < shStop:
            # get fresh temperature from OWM
            if owm is not None:
                try:
                    owm.get()
                    owm.fresh = True
                except Exception as e:
                    print 'Error getting weather: {}'.format(e)
                    owm.fresh = False

            # get readings from inverter, if success send  to pvoutput
            inv.read_inputs()
            if inv.status != -1:
                # pvoutput(inv, owm)
                # temperature report only if available
                temp = None
                if owm is not None and owm.fresh:
                    temp = owm.temperature

                pvo.send_status(date=inv.date, energy_gen=inv.wh_today,
                                power_gen=inv.ac_power, vdc=inv.pv_volts,
                                vac=inv.ac_volts, temp=temp,
                                temp_inv=inv.temp, energy_life=inv.wh_total,
                                power_vdc=inv.pv_power)
                # sleep until next multiple of 5 minutes
                min = 5 - localnow().minute % 5
                sleep(min*60 - localnow().second)
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
    # set objects
    try:
        config = ConfigObj("pvoutput.conf",
                            configspec="pvoutput-configspec.ini")
        validator = Validator()
        if not config.validate(validator):
            raise ConfigObjError
    except ConfigObjError:
        print('Could not read config or configspec file', ConfigObjError)

    # FIXME: is this the most pythonic code?
    localnow.LocalTZ = timezone(config['timezone'])

    # init clients
    inv = Inverter(config['inverters']['addresses'][0], config['inverters']['port'])

    if config['owm']['OWMKEY'] is not None:
        owm = Weather(config['owm']['OWMKEY'], config['owm']['latitude'], config['owm']['longitude'])
        owm.fresh = False
    else:
        owm = None

    if ((config['pvoutput']['APIKEY'] is not None) and
        (config['pvoutput']['systemID'] is not None)):
        pvo = PVOutputAPI(config['pvoutput']['APIKEY'], config['pvoutput']['systemID'])
    else:
        print('Need pvoutput APIKEY and systemID to work')

    try:
        main_loop()
    except KeyboardInterrupt:
        print >> sys.stderr, '\nExiting by user request.\n'
        sys.exit(0)
