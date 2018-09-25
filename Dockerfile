FROM resin/raspberrypi-python:2.7
LABEL maintainer="Josenivaldo Benito Jr. <SvenDowideit@home.org.au>"

ADD requirements.txt .
RUN pip install --no-cache-dir  -r requirements.txt
