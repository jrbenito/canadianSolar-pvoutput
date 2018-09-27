[![Codacy Badge](https://api.codacy.com/project/badge/Grade/1a8b27961c904e8093f5adaa40ca8e8f)](https://app.codacy.com/app/jrbenito/canadianSolar-pvoutput?utm_source=github.com&utm_medium=referral&utm_content=jrbenito/canadianSolar-pvoutput&utm_campaign=Badge_Grade_Dashboard)

# Canadina Solar / Growatt

This code reads registers from Canadian Solar inverter via modbus protocol over a RS-232 or RS-485 interface. 
I only tested it on a CSI-3K-TL witch is much similar (probably a clone altough I have no written evidence)
of Growatt inverters. Besides very similar hardware and display interface look and feel, modbus protocol are identical.

Although there is a function to synchronize inverter's clock based on comments posted to the Steffen blog, this function 
was never tested since Canadian opted to not implement clock features into CSI-3K-TL.

## pvoutput

Values read from inverter are upload to [pvoutput.org](https://pvoutput.org) and this code assumes the account has "donantion" features enabled.
If you do not want to donate just remove extra features (v7~v12 paramenters).

Optionally this code reads local temperature from [OpenWheatherMap](https://openweathermap.org)

## Usage

### Configuration

There is a configuration template you need to copy/rename and edit:

```
$ cp pvoutput.conf.rename pvoutput.conf
```

Edit `pvoutput.conf` with your preferred text editor. All commented lines are optional, but othere might have values. Please notice that some options are lists (i.e. systemID and addresses), those lists are represented as comma separated values (val1, val2, val3) but if only one value is being used, finalize the line with a comma (i.e. systemID=id1,).

### Docker
 
For portability and also for simplify development, I run this code into a docker container. Dockerfile is very simple and provided.

To build docker image just run `docker build -t canadian-pvoutput .`

To run in docker create a container with `docker run --restart always --name="pvoutput" -d -i --device=/dev/ttyUSB0 --net=host -v /home/jrbenito/canadian-pvoutput:/app -w /app canadian-pvoutput ./pvoutput.sh`. Script `pvoutput.sh` is a wrapper to run python script continuasly if it fails. Docker will automaticaly restart this container in case of computer reboot or container fails.

### Direct (no docker)

```
$ pip install -r requirements.txt
$ ./pvoutput.sh
```
