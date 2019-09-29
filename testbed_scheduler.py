##############################################################
# File name: testbed_scheduler.py
# Function:  A scheduler running in the server to schedule 
#            experiments. This file is implemented mainly  
#            based on the apscheduler.
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
import ftplib
from apscheduler.schedulers.blocking import BlockingScheduler

# Variables on paths
CURRENT_PATH = os.path.split(os.path.realpath(__file__))[0]
TESTBED_TMP_PATH = CURRENT_PATH + '/../testbed_tmp/'

# Variables on FTP
#FTP_ADDRESS = '106.14.190.177'
FTP_ADDRESS = '127.0.0.1'
FTP_PORT = 21
FTP_PASSIVE_MODE = 0
FTP_USER = 'testbed'
FTP_PASSWORD = 'ewsn0987'

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
client = mqtt.Client()

# Variables on experiments (Here, we just initialize the variables.)
batch_file = ""
# preparation_time is in second.
preparation_time = 40
# experiment_duration is in minute.
experiment_duration = 2
experiment_gap = 120
timestamp_previous_end = 0 # Restore the stop time which was posted in the previous "batch post".

# Variabls on scheduler
scheduler = BlockingScheduler()

# Variables on the experiments list
class exp_time:
  def __init__(self):
    self.name = ''
    self.experiment_id = ''
    self.start = datetime.datetime.now()
    self.end = datetime.datetime.now()
exp_time_list = []

# Get a file from the ftp server. (This function should be called after the observer has been connected to the ftp server.)
# filename_in_ftp: the file in the ftp server
# filename_local: the file which is saved as in the local observer
# ftp: the handler of the ftp
def grab_file_from_ftp(filename_in_ftp, filename_local, ftp):
  localfile = open(filename_local, 'wb')
  ftp.retrbinary('RETR ' + filename_in_ftp, localfile.write, 1024)
  localfile.close()

# Generate ID based on time and the current FTP user name.
# Return: the ID (a string).
def tid_maker(username):
  return '{0:%Y%m%d%H%M%S%f}'.format(datetime.datetime.now()) + username

# Post a new experiment at a pre-scheduled time.
def testbed_scheduler_function(para):
  global exp_time_list, client
  
  # This part is for debugging.
  now = datetime.datetime.now()
  ts = now.strftime('%Y-%m-%d %H:%M:%S')
  print("do at time: " + ts) # The call time
  print(para) # The mqtt call command
  
  client.publish(MQTT_TOPIC, para[0] + ' ' + para[1])
  
  original_length = len(exp_time_list) # for debugging
  for element in exp_time_list:
    if(para[1] == element.experiment_id):
      exp_time_list.remove(element)
  print("The length of exp_time_list reduce from " + str(original_length) + " to " + str(len(exp_time_list)))

# Check whether there is new message in the subscribed topic periodically.
def mqtt_timer_function():
  global client
  client.loop(.1)

# MQTT Callback function: on_connect
def on_connect(client, userdata, flags, rc):
  # Subscribe the topic once the connection has been established.
  print("Connected with result code " + str(rc))
  if(rc == 0):
    client.subscribe([(MQTT_TOPIC, 2)])

# MQTT Callback function: on_message
def on_message(client, userdata, msg):
  global timestamp_previous_end, scheduler
  
  # Split the mqtt message into a word list.
  mqtt_msg = msg.payload.decode()
  mqtt_msg_wordlist = mqtt_msg.split()
  print(mqtt_msg_wordlist)
  
  if mqtt_msg_wordlist[0] == MQTT_POST_EXPS:
    batch_file = mqtt_msg_wordlist[1]
    username = mqtt_msg_wordlist[2]
        
    # Get the batch file from ftp
    with ftplib.FTP() as ftp:
      ftp.set_pasv(FTP_PASSIVE_MODE)
      ftp.connect(FTP_ADDRESS, FTP_PORT)
      print(ftp.getwelcome())
      try:
        ftp.login(FTP_USER, FTP_PASSWORD)
        ftp.cwd('/home/' + FTP_USER + '/' + username + '/')
        print(batch_file)
        file_size = ftp.size(batch_file)
        if(file_size > 0):
          grab_file_from_ftp(batch_file, TESTBED_TMP_PATH + '/batch_file.txt', ftp)
          f = open(TESTBED_TMP_PATH + '/batch_file.txt', "r")
          batch_list = f.readlines()   
          f.close()
          
          if(len(exp_time_list) == 0):
            date_time_now = datetime.datetime.now()
            time_now = date_time_now.time()
            timestamp_now = date_time_now.replace(tzinfo = None).timestamp()
            if(timestamp_now > (timestamp_previous_end + experiment_gap)):
              timestamp_previous_end = timestamp_now
          print(timestamp_previous_end)
          for tasks in batch_list:
            tasks_wl = tasks.split()
            experiment_duration = int(tasks_wl[2])
            print(tasks_wl) 
            
            # Compute time plus the delta of preparation.
            timestamp_actural_start = timestamp_previous_end + preparation_time
            experiment_start_time = datetime.datetime.fromtimestamp(timestamp_actural_start)
            experiment_start_time = experiment_start_time.replace(microsecond = 0)
            
            # Compute the experiment ID and schedule it.
            exp_id = tid_maker(username)
            print(exp_id)
            scheduler.add_job(testbed_scheduler_function, 'date', run_date = experiment_start_time, args = [[tasks, exp_id]], id = exp_id)
            print(experiment_start_time)
           
            # Compute end time of the experiment
            experiment_start_time_timestamp = experiment_start_time.replace(tzinfo = None).timestamp()
            experiment_end_time_timestamp = experiment_start_time_timestamp + experiment_duration * 60
            timestamp_previous_end = experiment_end_time_timestamp + experiment_gap
            experiment_end_time = datetime.datetime.fromtimestamp(experiment_end_time_timestamp)
            experiment_end_time = experiment_end_time.replace(microsecond = 0)
            
            # Generate and new element in the exp_time_list and append it.
            exp_t = exp_time()
            exp_t.name = tasks_wl[1]
            exp_t.experiment_id = exp_id
            exp_t.start = experiment_start_time_timestamp
            exp_t.end = experiment_end_time_timestamp
            exp_time_list.append(exp_t)
            print(exp_t)
                                    
          print(scheduler.get_jobs())                      
      except ftplib.all_errors as e:
        print('FTP error: ', e)        
#  client.disconnect()

def main():
  global scheduler, client
  
  #Prepare mqtt client
  client.username_pw_set(username = "computer_testbed_server", password = "123456")
  client.connect(MQTT_BROKER_ADDRESS, MQTT_BROKER_PORT, 60)
  
  client.on_connect = on_connect
  client.on_message = on_message

  # Every 5 seconds, the routine checks the subsribed topic in mqtt.
  scheduler.add_job(mqtt_timer_function, 'interval', seconds = 5, id = 'testbed_scheduler')
  
  # Establish a path to restore the batch file.
  if not os.path.exists(TESTBED_TMP_PATH):
    os.makedirs(TESTBED_TMP_PATH)

  scheduler.start()

if __name__ == "__main__": 
  main()