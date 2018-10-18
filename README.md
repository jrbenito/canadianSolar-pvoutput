# Canadina Solar / Growatt

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/1a8b27961c904e8093f5adaa40ca8e8f)](https://app.codacy.com/app/jrbenito/canadianSolar-pvoutput?utm_source=github.com&utm_medium=referral&utm_content=jrbenito/canadianSolar-pvoutput&utm_campaign=Badge_Grade_Dashboard)

This code reads registers from Canadian Solar and Growatt inverters via modbus protocol over a RS-232 or RS-485 interface.
I developed it to work with a Canadian Solar CSI-3K-TL (uses Growatt modbus protocol), after some other members of pvouput community joined and tested on other models (see below). This might work with any Growatt based inverter that follows modbus protocol but is tested on:

* Canadian Solar CSI-3K-TL
* Growatt 1500-S (thanks @bobboulby)
* Growatt 33000TL3-HE (thanks @lampra)

## pvoutput

Values read from inverter are upload to [pvoutput.org](https://pvoutput.org) and this code assumes the account has "donantion" features enabled.
If you do not want to donate just remove extra features (v7~v12 paramenters).

Optionally this code reads local temperature from [OpenWheatherMap](https://openweathermap.org)

## Usage

### Configuration

There is a configuration template you need to copy/rename and edit:

```bash
cp pvoutput.conf.rename pvoutput.conf
```

Edit `pvoutput.conf` with your preferred text editor. All commented lines are optional, but other shall have values. Please notice that some options are lists (i.e. systemID and addresses), those lists are represented as comma separated values (val1, val2, val3). At least pvoutput credentials (`systemID` and `APIKEY`) must be supplied since there are no reasonable defaults to it.

Work with date and time can be tricky. Most system report their date into local time, a few servers use UTC in order to make log matches simpler with other servers around the globe. I personaly use docker to make this code easier to deploy and portable between my PC and the ARM processor at RPi (same docker image runs on both and same docker image can be used to development). Docker images do not mirror their hosts locale and hence inside the container the date is reported UTC. On top of this, every year someone in somewhere decides that daylight saving at that specific "somwhere" place on the globe will change from the last friday of November to the first Tuesday of September just on that year... Well, this sometimes happens here in my place due to all sort of political excuses. To avoid this nightmare, pytz library comes to the rescue. BE AWARE tha config file defaults to UTC, you SHALL provide your correct timezone or configure pvoutput webservice as UTC. Otherwise your report will be shifted in time.

### Docker

For portability and also for simplify development, I run this code into a docker container. Dockerfile is very simple and provided.

To build docker image just run `docker build -t canadian-pvoutput .`

To run in docker create a container with `docker run --restart always --name="pvoutput" -d -i --device=/dev/ttyUSB0 --net=host -v /home/jrbenito/canadian-pvoutput:/app -w /app canadian-pvoutput ./pvoutput.sh`. Script `pvoutput.sh` is a wrapper to run python script continuasly if it fails. Docker will automaticaly restart this container in case of computer reboot or container fails.

### Direct (no docker)

```bash
$ pip install -r requirements.txt
[...]
$ ./pvoutput.sh
```

## Credits

This code was inspired by [Steffen Nyeland](http://fixedbycode.blogspot.com/2014/04/how-to-upload-data-from-growatt.html) blog post and extensive help from [pvoutput.org community](https://forum.pvoutput.org/t/help-required-uploading-growatt-inverter-to-pvoutput/552) whose users where kind enough to test, feedback, suggest features and point out a lot of bugs. Thank you all for your patience and support.

Also, I need to thank engineers from Growatt and Canadian Solar who where kind enough to provide documentation and solve confusion about versions of modbus protocol. Thanks to Mr. Denilson and Mr. Hugo from Canadian Solar Brazilian branch office and Mr. Darren Song from Growatt China.