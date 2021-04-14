FROM continuumio/miniconda3:4.8.2
MAINTAINER Mingxun Wang "mwang87@gmail.com"

RUN pip install ftputil flask gunicorn requests

COPY . /app
WORKDIR /app
