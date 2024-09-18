#!/bin/bash

source activate python3
#python ./main.py
gunicorn -w 2 --threads=12 --worker-class=gthread -b 0.0.0.0:5000 \
--timeout 120 --max-requests 500 --max-requests-jitter 100 --graceful-timeout 120 main:app \
--access-logfile /app/logs/access.log
