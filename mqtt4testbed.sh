##############################################################
# File name: mqtt4testbed.sh
# Function:  This script is used to launch the mqtt server and
#            subscribe the topic "testbed"
# Version:   1.0
# Author:    Xiaoyuan Ma (maxy@sari.ac.cn)
# Date:      20190906 
##############################################################
#!/usr/bin/env bash

killall mosquitto

mosquitto -c /etc/mosquitto/mosquitto.conf &
#mosquitto_sub -t 'testbed' -u computer_testbed_server -P 123456
