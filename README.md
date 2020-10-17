[![Codacy Badge](https://api.codacy.com/project/badge/Grade/1a8b27961c904e8093f5adaa40ca8e8f)](https://app.codacy.com/app/jrbenito/canadianSolar-pvoutput?utm_source=github.com&utm_medium=referral&utm_content=jrbenito/canadianSolar-pvoutput&utm_campaign=Badge_Grade_Dashboard)

= Canadina Solar

This code reads registers from Canadian Solar invernter via modbus protocol over a RS-232 interface. 
I only tested it on a CSI-3K-TL witch is much similar (probably a clone altough I have no written evidence)
of Growatt inverters. Besides very similar hardware and display interface look and feel, modbus protocol are identical
(exception to some unimplemented features like clock).

Although there is a function to synchronize inverter's clock based on comments posted to the Steffen blog, this function 
was never tested since Canadian opted to not implement clock features into CSI-3K-TL.

== pvoutput

Values read from inverter are upload to [pvoutput.org](https://pvoutput.org) and this code assumes the account has "donantion" features enabled.
If you do not want to donate just remove extra features (v7~v12 paramenters).

Optionally this code reads local temperature from [OpenWheatherMap](https://openweathermap.org)

== Usage

=== Docker
 
For portability and also for simplify development, I run this code into a docker container. Dockerfile is very simple and provided.

To build docker image just run `docker build -t canadian-pvoutput .`

To run in docker create a container with `docker run --restart always --name="pvoutput" -d -i --device=/dev/ttyUSB0 --net=host -v /home/jrbenito/canadian-pvoutput:/app -w /app jrbenito/canadian-pvoutput ./pvoutput.sh`. Script `pvoutput.sh` is a wrapper to run python script continuously if it fails. Docker will automaticaly restart this container in case of computer reboot or container fails.

=== Direct (no docker)

```
$ pip install -r requirements.txt
$ ./pvoutput.sh
```
