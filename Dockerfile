FROM python:3.8-alpine
LABEL maintainer="Josenivaldo Benito Jr. <SvenDowideit@home.org.au>"

COPY requirements.txt .
RUN pip install --no-cache-dir  -r requirements.txt
