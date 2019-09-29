##############################################################
# File name: run_experiments.py
# Function:  Grab the program file from the ftp server and 
#            generate a preparation csv file.
# Version:   1.0
# Author:    Xiaoyuan Ma (maxy@sari.ac.cn)
# Date:      20190906 
##############################################################

#!/usr/bin/env python3
import os
import sys
import csv
import ftplib
import datetime
from datetime import timezone

# Variables on paths
CURRENT_PATH = os.path.split(os.path.realpath(__file__))[0]
PROGRAM_AND_PARA_PATH = CURRENT_PATH + '/../program_and_parameter'

# Variables on FTP
FTP_ADDRESS = '106.14.190.177'
FTP_PORT = 21
FTP_PASSIVE_MODE = 0
FTP_USER = 'testbed'
FTP_PASSWORD = 'ewsn0987'

# Variables on experiments (Here, we just initialize the variables.)
# preparation_time is in second.
preparation_time = 50
# experiment_duration is in minute.
experiment_duration = 2
# experiment_platform = experiment_config_platform
experiment_platform = 1
# experiment_name = experiment_config_name
experiment_name = 'hello_world'

# Get a file from the ftp server. (This function should be called after the observer has been connected to the ftp server.)
# filename_in_ftp: the file in the ftp server
# filename_local: the file which is saved as in the local observer
# ftp: the handler of the ftp
def grab_file_from_ftp(filename_in_ftp, filename_local, ftp):
  localfile = open(filename_local, 'wb')
  ftp.retrbinary('RETR ' + filename_in_ftp, localfile.write, 1024)
  localfile.close()

#############################################################################################################
############Useless Area (The variables and functions are not used in this file)#############################
#############################################################################################################
# The path is only used when upload a file for verification. (This is not used any more)
DATA_PATH = CURRENT_PATH + '/../testbed_data'

# Functions which was just used for verification, is not called in this file.
# Upload a file to the ftp server. (This function should be called after the observer has been connected to the ftp server.)
# filename_in_ftp: the file which is saved as in the ftp server
# filename_local: the file in the local observer
# ftp: the handler of the ftp
def upload_file_to_ftp(filename_local, filename_in_ftp, ftp):
  localfile = open(filename_local, 'rb')
  ftp.storbinary('STOR ' + filename_in_ftp, localfile, 1024)
  localfile.close()

# Generate ID based on time and the current FTP user name.
# Return: the ID (a string).
def tid_maker():
  return '{0:%Y%m%d%H%M%S%f}'.format(datetime.datetime.now()) + FTP_USER
#############################################################################################################
################################################Useless Area End#############################################
#############################################################################################################


def main(experiment_config_name, experiment_config_duration, exp_program, experiment_config_number):

  # 0. Prepare the parameters.
  experiment_name = experiment_config_name
  experiment_duration = int(experiment_config_duration)
  ftp_filename = exp_program
  #experiment_number = tid_maker()
  experiment_number = experiment_config_number
  username = ''.join([x for x in experiment_config_number if x.isalpha()])
    
  # 1. Establish a path to restore the program.
  if not os.path.exists(PROGRAM_AND_PARA_PATH):
    os.makedirs(PROGRAM_AND_PARA_PATH)

  # 2. Check ftp and get the program file.
  with ftplib.FTP() as ftp:
    ftp.set_pasv(FTP_PASSIVE_MODE)
    ftp.connect(FTP_ADDRESS, FTP_PORT)
    # print(ftp.getwelcome())
    try:
      ftp.login(FTP_USER, FTP_PASSWORD)
      ftp.cwd('/home/' + FTP_USER + '/' + username + '/' + experiment_name + '/config/')
      program_size = ftp.size(ftp_filename)
      if(program_size > 0):
        grab_file_from_ftp(ftp_filename, PROGRAM_AND_PARA_PATH + '/test.bin', ftp)
    except ftplib.all_errors as e:
      print('FTP error: ', e)

  # 3. Generate the parameter file, a simple csv.
  date_time_now = datetime.datetime.now()
  # Compute time plus the delta of preparation.
  time_now = date_time_now.time()
  timestamp_now = date_time_now.replace(tzinfo = None).timestamp()
  timestamp_actural_now = timestamp_now + preparation_time
  experiment_start_time = datetime.datetime.fromtimestamp(timestamp_actural_now)
  experiment_start_time = experiment_start_time.replace(microsecond = 0)
  experiment_start_time_timestamp = experiment_start_time.replace(tzinfo = None).timestamp()
  
  experiment_end_time_timestamp = experiment_start_time_timestamp + experiment_duration * 60
  experiment_end_time = datetime.datetime.fromtimestamp(experiment_end_time_timestamp)
  experiment_end_time = experiment_end_time.replace(microsecond = 0)


  with open(PROGRAM_AND_PARA_PATH + '/parameter.csv', mode='w') as parameter_file:
    parameter_writer = csv.writer(parameter_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    parameter_writer.writerow(['experiment_number', experiment_number])
    parameter_writer.writerow(['experiment_name', experiment_name])
    parameter_writer.writerow(['experiment_platform', experiment_platform])
    parameter_writer.writerow(['experiment_duration', experiment_duration])
    parameter_writer.writerow(['experiment_start_time', experiment_start_time])
    parameter_writer.writerow(['experiment_end_time', experiment_end_time])

  # Here is a demo to verify whether we can upload a file to the ftp.
  # with ftplib.FTP() as ftp:
  #     ftp.set_pasv(FTP_PASSIVE_MODE)
  #     ftp.connect(FTP_ADDRESS, FTP_PORT)
  #     # print(ftp.getwelcome())
  #     try:
  #         ftp.login(FTP_USER, FTP_PASSWORD)
  #         ftp.cwd('/home/' + FTP_USER + '/')
  #         upload_file_to_ftp(DATA_PATH + '/20190710_18-56-53_target_msg.csv', 'testdata.csv', ftp)
  #     except ftplib.all_errors as e:
  #         print('FTP error: ', e)


if __name__ == "__main__":
  if len(sys.argv) != 5:
    print("Parameters error!")
    print("para_1: experiment name.")
    print("para_2: duration of an experiment.")
    print("para_3: program_file.")
    print("para_4: experiment number.")
    exit(1)
  main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
