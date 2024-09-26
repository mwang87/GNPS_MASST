#!/bin/bash

source activate python3
celery -A tasks worker -l info -c 2 -Q worker --max-tasks-per-child 10 --loglevel INFO

