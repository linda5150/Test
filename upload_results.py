##############################################################
# File name: upload_results.py
# Function:  Check whether there is a result .csv file need 
#            to be uploaded and upload it to the corresponding 
#            directory of the ftp server.
# Version:   1.0
# Author:    Xiaoyuan Ma (maxy@sari.ac.cn)
# Date:      20190906 
##############################################################

#!/usr/bin/env python3
import os
import sys
import glob
import time
import csv
import ftplib
import datetime
from datetime import timezone

# Variables on paths
CURRENT_PATH = os.path.split(os.path.realpath(__file__))[0]
DATA_PATH = CURRENT_PATH + '/../testbed_data'

# Variables on FTP
FTP_ADDRESS = '106.14.190.177'
FTP_PORT = 21
FTP_PASSIVE_MODE = 0
FTP_USER = 'testbed'
FTP_PASSWORD = 'ewsn0987'

# Upload a file to the ftp server. (This function should be called after the observer has been connected to the ftp server.)
# filename_in_ftp: the file which is saved as in the ftp server
# filename_local: the file in the local observer
# ftp: the handler of the ftp
def upload_file_to_ftp(filename_local, filename_in_ftp, ftp):
  localfile = open(filename_local, 'rb')
  ftp.storbinary('STOR ' + filename_in_ftp, localfile, 1024)
  localfile.close()

# Check whether a directory exists in the ftp server. (This function should be called after the observer has been connected to the ftp server.)
# dir: The given directory
# ftp: the handler of the ftp
# return: True if the directory exists. Otherwise, False.
def directory_exists_in_ftp(dir, ftp):
  filelist = []
  ftp.retrlines('LIST', filelist.append)
  for f in filelist:
    if f.split()[-1] == dir and f.upper().startswith('D'):
      return True
  return False


def main(force, exp_name):
  # 1. Check msg csv files in testbed_data/.
  files = []
  create_file_time = []
  files = glob.glob(DATA_PATH + '/*msg*.csv')
    
  # 2. When force is "normal": If there are more than one msg csv file, upload the older one and remove it.
  # When force is "force": Upload the rest one and remove it.
  if((len(files) > 1) and (force == "normal")) or ((len(files) > 0) and (len(files) <= 1) and (force == "force")):
    # Generate a list of create time.
    for f in files:
      t = datetime.datetime.strptime(time.ctime(os.path.getctime(f)), "%a %b %d %H:%M:%S %Y")
      create_file_time.append(t.timestamp())
    
    t_min_index = create_file_time.index(min(create_file_time))
    file_name_in_ftp = os.path.basename(files[t_min_index])
    file_name_in_ftp_wl = file_name_in_ftp.split('_')
    exp_num = file_name_in_ftp_wl[0]
    username = ''.join([x for x in exp_num if x.isalpha()])
    
    # Upload the result file to the given directory, i.e., the corresponding experiment name and experiment id.       
    with ftplib.FTP() as ftp:
      ftp.set_pasv(FTP_PASSIVE_MODE)
      ftp.connect(FTP_ADDRESS, FTP_PORT)
      # print(ftp.getwelcome())
      try:
        ftp.login(FTP_USER, FTP_PASSWORD)
        ftp.cwd('/home/' + FTP_USER + '/' + username + '/' + exp_name + '/')
        if directory_exists_in_ftp(exp_num, ftp) is False:
          ftp.mkd('/home/' + FTP_USER + '/' + username + '/' + exp_name + '/' + exp_num +'/')
        ftp.cwd(exp_num)
        upload_file_to_ftp(files[t_min_index], file_name_in_ftp, ftp)
        os.remove(files[t_min_index])
      except ftplib.all_errors as e:
        print('FTP error: ', e)
    
  # 3. Check FPGA csv files in testbed_data/.
  files = []
  create_file_time = []
  files = glob.glob(DATA_PATH + '/*FPGA*.csv')
    
  # 4. When force is "normal": If there are more than one FPGA csv file, upload the older one and remove it.
  # When force is "force": Upload the rest one and remove it.
  if((len(files) > 1) and (force == "normal")) or ((len(files) > 0) and (len(files) <= 1) and (force == "force")):
    # Generate a list of create time.
    for f in files:
      t = datetime.datetime.strptime(time.ctime(os.path.getctime(f)), "%a %b %d %H:%M:%S %Y")
      create_file_time.append(t.timestamp())
    
    t_min_index = create_file_time.index(min(create_file_time))
    file_name_in_ftp = os.path.basename(files[t_min_index])
    file_name_in_ftp_wl = file_name_in_ftp.split('_')
    exp_num = file_name_in_ftp_wl[0]
    username = ''.join([x for x in exp_num if x.isalpha()])
    
    # Upload the result file to the given directory, i.e., the corresponding experiment name and experiment id.       
    with ftplib.FTP() as ftp:
      ftp.set_pasv(FTP_PASSIVE_MODE)
      ftp.connect(FTP_ADDRESS, FTP_PORT)
      # print(ftp.getwelcome())
      try:
        ftp.login(FTP_USER, FTP_PASSWORD)
        ftp.cwd('/home/' + FTP_USER + '/' + username + '/' + exp_name + '/')
        if directory_exists_in_ftp(exp_num, ftp) is False:
          ftp.mkd('/home/' + FTP_USER + '/' + username + '/' + exp_name + '/' + exp_num +'/')
        ftp.cwd(exp_num)
        upload_file_to_ftp(files[t_min_index], file_name_in_ftp, ftp)
        os.remove(files[t_min_index])
      except ftplib.all_errors as e:
        print('FTP error: ', e)

if __name__ == "__main__":
  if len(sys.argv) != 3:
    print("Parameters error!")
    print("para_1: force or normal.")
    print("para_2: experiment name.")
    exit(1)
  
  main(sys.argv[1], sys.argv[2])
