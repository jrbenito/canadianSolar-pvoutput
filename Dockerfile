FROM python:2.7-alpine
LABEL maintainer="Josenivaldo Benito Jr. <SvenDowideit@home.org.au>"

ADD requirements.txt .
RUN pip install --no-cache-dir  -r requirements.txt
