#!/bin/bash
# wangjinde
# 08/11/2016

export PYTHONIOENCODING=utf-8
date_str="$(date +'%Y%m%d-%H%M%S')"
nohup python appointment.py > /mnt/appointment_logs/${date_str}.log 2>&1 &
