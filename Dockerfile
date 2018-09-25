FROM resin/raspberrypi-python:2.7
LABEL maintainer="Josenivaldo Benito Jr. <SvenDowideit@home.org.au>"

RUN pip install --no-cache-dir pyowm configobj pymodbus pytz