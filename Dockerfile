FROM ubuntu:latest
MAINTAINER Mingxun Wang "mwang87@gmail.com"

RUN apt-get update -y
RUN apt-get install -y python-pip python-dev build-essential

RUN pip install ftputil
RUN pip install flask
RUN pip install gunicorn
RUN pip install requests

COPY . /app
WORKDIR /app
