##############################################################
# File name: mqtt4testbed_observer.py
# Function:  Subscribe the mqtt topic and parse the command.
# Version:   1.0
# Author:    Xiaoyuan Ma (maxy@sari.ac.cn)
# Date:      20190906 
##############################################################

#!/usr/bin/env python3
import os
from subprocess import Popen, PIPE
import paho.mqtt.client as mqtt
import time
import datetime

# log
log = open('log.txt', 'a')
log.write('some text, as header of the file\n')
log.flush()  # <-- here's something not to forget!

# Variables on paths
CURRENT_PATH = os.path.split(os.path.realpath(__file__))[0]
CFG_TXT_FILE = CURRENT_PATH + '/../testbed_data/cfg.txt'

# Variables on MQTT
MQTT_BROKER_ADDRESS = "106.14.190.177"
MQTT_BROKER_PORT = 1883
MQTT_TOPIC = "testbed"
# MQTT Commands
MQTT_POST_EXP = "post_an_experiment_by_a_user"
MQTT_POST_EXPS = "post_experiments_by_a_user"
MQTT_STOP_EXP = "stop_an_experiment_by_a_user"
MQTT_EXP_START_NOTIFICATION = "an_experiment_started_notification"
MQTT_EXP_STOP_NOTIFICATION = "an_experiment_stopped_notification"
MQTT_EXP_STOP_ABNORMALLY_NOTIFICATION = "an_experiment_stopped_abnormally"

# Counters
cnt = 0
cnt_upload = 0
# The period of checking whether there is a file need to be uploaded (in S). 
UPLOAD_CHECK_PERIOD = 240

# The global variable representing the name of the current running experiment. 
exp_name = ""

# MQTT Callback function: on_connect
def on_connect(client, userdata, flags, rc):
  # Subscribe the topic once the connection has been established.
  print("Connected with result code " + str(rc))
  if(rc == 0):
    client.subscribe([(MQTT_TOPIC, 2)])

# MQTT Callback function: on_message
def on_message(client, userdata, msg):
  global exp_name 
    
  # Split the mqtt message into a word list.
  mqtt_msg = msg.payload.decode()
  mqtt_msg_wordlist = mqtt_msg.split()
  print(mqtt_msg_wordlist) 
    
  if mqtt_msg_wordlist[0] == MQTT_POST_EXP:
    exp_name = mqtt_msg_wordlist[1]
    exp_duration = mqtt_msg_wordlist[2]
    exp_program = mqtt_msg_wordlist[3]
    exp_id = mqtt_msg_wordlist[4]
    
    # Generate the preparation file and grab the program file from the ftp server.
    log.write('Call run_experiments.py at ' + str(datetime.datetime.now()) + '\n')
    log.flush()  # <-- here's something not to forget!
    process = Popen(['python3', CURRENT_PATH + '/run_experiments.py', exp_name, exp_duration, exp_program, exp_id], stdout = log, stderr = log)
    # These two sentences are used to block until the command has been completed.
    process.communicate()
    process.wait()
    
    # Start to run and observe the experiment.
    log.write('Call host-rpi3_V21.py at ' + str(datetime.datetime.now()) + '\n')
    log.flush()  # <-- here's something not to forget!
    process = Popen(['python3', CURRENT_PATH + '/host-rpi3_V21.py'], stdout = log, stderr = log)
    
    print(MQTT_POST_EXP)
  if msg.payload.decode() == MQTT_STOP_EXP:
    print(MQTT_STOP_EXP)
  if msg.payload.decode() == MQTT_EXP_START_NOTIFICATION:
    print(MQTT_EXP_START_NOTIFICATION)
  if msg.payload.decode() == MQTT_EXP_STOP_NOTIFICATION:
    print(MQTT_EXP_STOP_NOTIFICATION)
  if msg.payload.decode() == MQTT_EXP_STOP_ABNORMALLY_NOTIFICATION:
    print(MQTT_EXP_STOP_ABNORMALLY_NOTIFICATION)
  if mqtt_msg_wordlist[0] == MQTT_POST_EXPS:
    print(MQTT_POST_EXPS)
# client.disconnect()

# Check whether there is a result file need to be upload periodically.
def timer_function(para):
  global exp_name
  
  # This part is for debugging.
  now = datetime.datetime.now()
  ts = now.strftime('%Y-%m-%d %H:%M:%S')
  print("do at time: " + ts) # The call time
  print('python3 ' + CURRENT_PATH + '/upload_results.py ' + para + ' ' + exp_name) # The call command
  
  process = Popen(['python3', CURRENT_PATH + '/upload_results.py', para, exp_name], stdout = log, stderr = log)
  # These two sentences are used to block until the command has been completed.
  process.communicate() 
  process.wait()  

def main():
  global cnt, cnt_upload
  log.write('mqtt4testbed_observer.py was running at ' + str(datetime.datetime.now()) + '\n')
  log.flush()  # <-- here's something not to forget!

  #Prepare mqtt client
  client = mqtt.Client()
  client.username_pw_set(username = "computer_testbed_server", password = "123456")
  client.connect(MQTT_BROKER_ADDRESS, MQTT_BROKER_PORT, 60)  
  
  client.on_connect = on_connect
  client.on_message = on_message

  while True:
    print(str(cnt) + " " + str(cnt_upload))
    client.loop(.1)
    time.sleep(1)
    
    cnt = cnt + 1
    if(cnt >= 1000):
      cnt = 0
    cnt_upload = cnt_upload + 1
      
    if(cnt % 20 == 0):    
      if(os.path.isfile(CFG_TXT_FILE)):
        # Monitor the status in cfg.txt
        f = open(CFG_TXT_FILE, "r")
        cfg_txt = f.readlines()
        f.close()
        
        # Read the 7th line in the cfg.txt
        if(len(cfg_txt) >= 7):
          print(cfg_txt[7 - 1])
          wordlist = cfg_txt[7 - 1].split()
          print(wordlist)
          if(wordlist[0] == "status"):
            if(wordlist[1] == "running"):
              if(cnt_upload == UPLOAD_CHECK_PERIOD):
                cnt_upload = 0
                print("call upload")
                timer_function("normal")
            else:
              if(wordlist[1] == "idle"):
                cnt_upload = 0
                print("call final upload")     
                timer_function("force")

if __name__ == "__main__":
  main()