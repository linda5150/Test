# ###############################################################################################
# ##  Dan Li @ 2019/07/08                                                                      ##
# ##  Target Message is saved in ./testbed/testbed_data/xx-xx-xx_xx-xx-xx_target_msg.csv file  ##
# ##  Test config file is saved in ./testbed/testbed_data/cfg.txt                              ##
# ##  .c, .py and .sh file are all at ./testbed/code                                           ##
# ##  Add GPIO.input(FPGA_STATE). it is high, if the FPGA module is working.                   ##
# ##  The max size of the log file is 1 Mbytes                                                 ##
# ###############################################################################################
# !/usr/bin/python
import signal
from datetime import datetime
import time
import RPi.GPIO as GPIO
import serial as srl
import serial.tools.list_ports
import csv
import os
import sys
import subprocess
import pandas as pd
import socket
import math
import shutil

# log
LOG_PATH = 'log_host.txt'
log = open(LOG_PATH, 'a')
log_size = os.path.getsize(LOG_PATH)
if log_size > 1024*1024:
    os.remove(LOG_PATH)
    log = open(LOG_PATH, 'a')
    log.write('This a new file records the events of host-rpi3_V21.py. @' + str(datetime.now()) + '\n\n')
    log.flush()  # <-- here's something not to forget!
else:
    log.write('This the file records the events of host-rpi3_V21.py. @' + str(datetime.now()) + '\n\n')
    log.flush()     # <-- here's something not to forget!


# ---------- GPIO control ----------
TAR1_PWR = 2        # RPI output controls channel 1, default output 0
TAR2_PWR = 3        # RPI output controls channel 2, default output 0
TAR3_PWR = 4        # RPI output controls channel 3, default output 0
FPGA_nRST = 25      # RPI output resets FPGA module, default output 1
FPGA_STATE = 14     # RPI input is the state of FPGA module, default input
TIME_STAMP = 15     # RPI output is controls channel 2, default output 1
# TARGET_MSK = 0x01 << (3-1)  # | 0x01 << (2-1) |0x01 << (1-1)            # Default channel selection
WORKMINS = 2        # Default work duration
MINUTES_PER_FILE = 5.0                                                  # Default duration per file of each experiment
CURRENT_PATH = os.path.split(os.path.realpath(__file__))[0]             # Access the current folder of this code file
#  'home/pi/testbed/code'
# PARA_PATH = os.path.dirname(CURRENT_PATH) + '/program_and_parameter/parameter.csv' # 'home/pi/testbed'+ ...
PARA_PATH = CURRENT_PATH + '/../program_and_parameter/parameter.csv'    # Experiments Parameters location
# DATA_PATH = os.path.dirname(CURRENT_PATH) + '/testbed_data'
DATA_PATH = CURRENT_PATH + '/../testbed_data'                           # Experiments Data folder location
#  './testbed/testbed_data'
MY_TXT_NAME = 'cfg.txt'                                                 # Experiments Config file for FPGA module
MY_CSV_NAME = 'target_msg.csv'                                          # Experiments Serial event record
SH_FPGA_ST_PATH = CURRENT_PATH + '/start.sh'                            # Shell file runs .c code for FPGA module
# ./testbed/code/start.sh
SH_LORA_BT_PATH = CURRENT_PATH + '/*LoRa.sh'                            # Shell boot the firmware into the target board
# ./testbed/code/*LoRa.sh
MY_LORA = '/dev/ttyACM0'                                                # The target USB address
MY_TIMEOUT = 0.003                                                      # Default set for Serial port timeout
MY_LORA_BAUD = 115200                                                   # Default set for Serial port baud rate


def receive_signal(signum, stack):
    global state
    if signum == signal.SIGUSR1:
        state = 0
    if signum == signal.SIGUSR2:
        state = 1


def load_parameter(para_path):
    para_list = pd.read_csv(para_path,
                            index_col=0, usecols=[0, 1],
                            header=None, names=range(0, 2))
    exp_num = para_list.at['experiment_number', 1]
    # exp_num = int(exp_num)
    # exp_name = para_list.at['experiment_name', 1]
    exp_channel = para_list.at['experiment_platform', 1]
    # exp_channel = int(exp_channel)
    exp_dur = para_list.at['experiment_duration', 1]
    exp_dur = int(exp_dur)    # unit: min
    exp_begin = para_list.at['experiment_start_time', 1]
    exp_time1 = time.strptime(exp_begin, "%Y-%m-%d %H:%M:%S")
    time1 = datetime(exp_time1[0], exp_time1[1], exp_time1[2],
                     exp_time1[3], exp_time1[4], exp_time1[5])
    # exp_end = para_list.at['experiment_end_time', 1]
    # exp_time2 = time.strptime(exp_end, "%Y-%m-%d %H:%M:%S")
    # time2 = datetime(exp_time2[0], exp_time2[1], exp_time2[2],
    #                  exp_time2[3], exp_time2[4], exp_time2[5])
    return exp_num, exp_channel, exp_dur, time1


def get_ip():
    # noinspection PyBroadException
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('www.sari.ac.cn', 0))
        full_ip = s.getsockname()[0]
        ob_ip = full_ip.split(".")[3]  # string
    finally:
        s.close()
    return full_ip, ob_ip


def gpio_idle():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(TAR1_PWR, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(TAR2_PWR, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(TAR3_PWR, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(FPGA_nRST, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(TIME_STAMP, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(FPGA_STATE, GPIO.IN)


def gpio_init(io_state, target):  # timestamp line state
    if target == 1:
        GPIO.output(TAR1_PWR, GPIO.HIGH)  # turn on target1 channel
    if target == 2:
        GPIO.output(TAR2_PWR, GPIO.HIGH)  # turn on target2 channel
    if target == 3:
        GPIO.output(TAR3_PWR, GPIO.HIGH)  # turn on target3 channel
    GPIO.setup(FPGA_STATE, GPIO.IN)
    if io_state:
        GPIO.output(TIME_STAMP, GPIO.HIGH)
    else:
        GPIO.output(TIME_STAMP, GPIO.LOW)


def gpio_idle_again():
    GPIO.output(TAR1_PWR, GPIO.LOW)
    GPIO.output(TAR2_PWR, GPIO.LOW)
    GPIO.output(TAR3_PWR, GPIO.LOW)
    GPIO.output(FPGA_nRST, GPIO.HIGH)
    GPIO.output(TIME_STAMP, GPIO.HIGH)


def gpio_reverse(io_name, io_state):
    io_state = 1 - io_state
    GPIO.output(io_name, io_state)
    return io_state


def serial_init(serial_dev, baud, timeout):
    s = srl.Serial(serial_dev, baud, timeout=timeout)
    return s


def txt_new(txt_path, txt_name):
    name = txt_path + '/' + txt_name
    txt_file = open(name, 'w+', encoding='utf-8')  # new a .txt file
    return txt_file, name


def txt_cfg(txt_file, txt_datetime, test_time, exp_number, ip, exp_channel):
    cfg_time = txt_datetime.strftime('%Y%m%d %H:%M:%S')
    txt_file.write("%d\n" % test_time)
    txt_file.write("%s\n" % exp_number)
    txt_file.write("%s\n" % ip)
    txt_file.write("%s\n" % exp_channel)
    txt_file.write(";\n")
    txt_file.write(cfg_time + '\n')
    txt_file.write("status, idle")
    log.write('    The state is initial as Idle... @'
              + str(datetime.now()) + '\n')
    log.flush()  # <-- here's something not to forget
    txt_file.close()


def txt_status_modify(txt_path, line_number, new_status):
    f = open(txt_path, 'r+')
    flist = f.readlines()
    f.close()
    flist[line_number-1] = 'status ' + new_status + '\n'
    f = open(txt_path, 'w+')
    f.writelines(flist)
    f.close()


def csv_new(csv_path, exp_num, ob_ip, exp_channel, csv_slice):   # (str,str,str,str,int)
    name = csv_path + '/' + exp_num + '_' + ob_ip + '_' + exp_channel + '_' + 'msg' + str(csv_slice) + '.csv'
    csv_file = open(name, 'a+')  # new a .csv file
    return csv_file, name


def csv_head(csv_file):
    writer = csv.writer(csv_file, dialect='excel')
    writer.writerow(['Index', 'TimeStamp', 'Message'])
    return writer


def record_msg(msg_serial, rec_writer, dt_now, msg_n, rec_io, io_state):
    row = [0, '', '']
    if msg_serial.isOpen():
        row[2] = msg_serial.readline()
        row[2] = row[2].strip()    
        row[2] = row[2].decode('gb18030', 'ignore')
        if bool(row[2] != ''):
            io_state = gpio_reverse(rec_io, io_state)
            msg_n = msg_n + 1
            row[0] = msg_n
            row[1] = dt_now.strftime('%Y%m%d %H:%M:%S.%f')
            rec_writer.writerow(row)
            # log.write('10: Num.%d USB Message is recorded: %d, %s, %s\n'
            #           % (msg_n, row[0], row[1], row[2]))
            # log.flush()     # <-- here's something not to forget!
            # print("10: Num.%d USB Message is recorded: %d, %s, %s" % (msg_n, row[0], row[1], row[2]))
    return msg_n, io_state


def delta_seconds(begin, end):    # datetime.datetime
    delta_t = (end - begin).days * 86400 + (end - begin).seconds
    return delta_t


if __name__ == "__main__":
    pid = str(os.getpid())
    pidfile = "/tmp/logger.pid"
    if os.path.isfile(pidfile):
        os.remove(pidfile)
    open(pidfile, 'w').write(pid)  # You can check /tmp/logger.pid to daemonize process

    signal.signal(signal.SIGUSR1, receive_signal)
    signal.signal(signal.SIGUSR2, receive_signal)
    print(' 1: Progress is ready! /tmp/logger.pid')
    log.write(' 1: Progress is ready! /tmp/logger.pid. @' + str(datetime.now()) + '\n')
    log.flush()  # <-- here's something not to forget!
    gpio_idle()  # initial GPIO idle states
    # ---------- built data folder  ----------
    d_path = DATA_PATH
    if bool(1 - os.path.exists(d_path)):
        os.makedirs(d_path)
    else:
        shutil.rmtree(d_path)
        os.makedirs(d_path)
    print("    Data fold is %s" % d_path)
    log.write('    Data folder is %s @' % d_path + str(datetime.now()) + '\n')
    log.flush()  # <-- here's something not to forget!
    # ---------- load parameters  ----------
    p_path = PARA_PATH
    (e_num, e_chl, e_dur, e_bgn) = load_parameter(p_path)   # exp_num(string),
    #                                                         exp_channel(string),
    #                                                         exp_dur(int),
    #                                                         time1(datetime)
    (full_IP, observe_IP) = get_ip()    # string
    print(" 2: Experiment parameters are load in RPi.")
    log.write(' 2: Experiment parameters are load in RPi. @' + str(datetime.now()) + '\n')
    log.flush()  # <-- here's something not to forget!
    # ---------- GPIO control ----------
    gpio_state = True   # default time_stamp io state is 1
    if e_chl:
        gpio_init(gpio_state, int(e_chl))   # config GPIOs in this file
        print(" 3: GPIOs are initialized!")
        print("    Target channel %s is powered on!" % e_chl)
        log.write(' 3: GPIOs are initialized! @' + str(datetime.now()) + '\n')
        log.flush()  # <-- here's something not to forget!
        log.write('    And Target channel %s is powered on!' % e_chl + '\n')
        log.flush()  # <-- here's something not to forget!
    else:
        print(" 3: Error! Experiment channel is NULL!")
        log.write(' 3: Error! Experiment channel is NULL! @' + str(datetime.now()) + '\n')
        log.flush()  # <-- here's something not to forget!
    # ---------- Access experiment duration ----------
    # wt = WORKMINS  # the duration of this experiment, uint16_t wt
    if e_dur:
        wt = e_dur          # unit: minute
        print(" 4: This experiment will last %d minutes" % wt)
        log.write(' 4: This experiment will last %d minutes @' % wt + str(datetime.now()) + '\n')
        log.flush()  # <-- here's something not to forget!
    else:
        print(" 4: Error! Experiment duration is invalid!")
        log.write(' 4: Error! Experiment duration is invalid! @' + str(datetime.now()) + '\n')
        log.flush()  # <-- here's something not to forget!
    # ---------- test data is recorded in the csv_NUM csv files ----------
    csv_NUM = math.ceil(wt / MINUTES_PER_FILE)
    msg_number = 0
    delta_sec = 0
    print(" 5: ALL the target messages are sliced to %d csv files!" % csv_NUM)
    log.write(' 5: ALL the target messages are sliced to %d csv files! @' % csv_NUM
              + str(datetime.now()) + '\n')
    log.flush()  # <-- here's something not to forget!
    # ---------- config data to FPGA is recorded in the .txt file ----------
    dt_cfg = e_bgn
    txtName = MY_TXT_NAME
    (cfg_f, txtName) = txt_new(d_path, txtName)
    txt_cfg(cfg_f, dt_cfg, wt, e_num, observe_IP, e_chl)
    print(" 6: CFG file for FPGA is ready")
    log.write(' 6: CFG file for FPGA is ready @' + str(datetime.now()) + '\n')
    log.flush()  # <-- here's something not to forget!
    # ---------- USB serial port ----------
    port_list = list(serial.tools.list_ports.comports())
    while len(port_list) <= 1:
        port_list = list(serial.tools.list_ports.comports())
    msg_baud = MY_LORA_BAUD
    t_out = MY_TIMEOUT  # unit: s
    usb_dev = MY_LORA
    # ---------- Target Messages record ----------
    time_now = datetime.now()
    delta_sec = delta_seconds(time_now, e_bgn)  # unit: s
    if delta_sec > 6:
        while delta_sec > 6:
            time_now = datetime.now()
            delta_sec = delta_seconds(time_now, e_bgn)    # unit: s
        # ---------- call .c lib ----------
        subprocess.Popen('sh '+SH_FPGA_ST_PATH, shell=True)
        print(" 7: adc.c module is running! Config FPGA, reset FPGA, read and unpack data from FPGA.")
        log.write(' 7: Call start.sh! adc.c Config FPGA, reset FPGA, read and unpack data from FPGA. @'
                  + str(datetime.now()) + '\n')
        log.flush()  # <-- here's something not to forget!
        time_now = datetime.now()
        delta_sec = delta_seconds(time_now, e_bgn)
        log.write('    Begin to countdown @ %s' % str(time_now) + '\n'
                  + '    And there is %s s to start experiments\n' % str(delta_sec))
        log.flush()  # <-- here's something not to forget!
        if delta_sec > 0:
            while delta_sec > 0:
                time_now = datetime.now()
                delta_sec = delta_seconds(time_now, e_bgn)    # unit: s
            print("    Countdown1: %d s" % delta_sec)
            # ---------- burn .bin file ----------
            subprocess.Popen('sh '+SH_LORA_BT_PATH, shell=True)
            print(" 8: .bin file is burn into target.")
            log.write(' 8: .bin file is burn into target. @'
                      + str(datetime.now()) + '\n')
            log.flush()  # <-- here's something not to forget!
            txt_status_modify(txtName, 7, "programming")
            log.write('    Start programming... @' + str(datetime.now()) + '\n')
            log.flush()  # <-- here's something not to forget!
            # time.sleep(1)
            ser = serial_init(usb_dev, msg_baud, t_out)
            print(" 9: USB Serial is initialized!\n""    USB_DEV: %s\n""    Baud: %d" % (usb_dev, msg_baud))
            print("    Waiting for messages...")
            log.write(' 9: USB Serial is initialized! @'
                      + str(datetime.now()) + '\n'
                      + '    USB_DEV: %s\n' % usb_dev
                      + '    Baud: %d\n' % msg_baud
                      + '    Waiting for messages...\n'
                      )
            log.flush()  # <-- here's something not to forget!
            while delta_sec > 0:
                time_now = datetime.now()
                delta_sec = delta_seconds(time_now, e_bgn)
            print("    Countdown2: %d s" % delta_sec)
            time_now = datetime.now()
            delta_sec = delta_seconds(e_bgn, time_now)
            txt_status_modify(txtName, 7, "running")
            log.write('    Start running... @' + str(datetime.now()) + '\n')
            log.flush()  # <-- here's something not to forget!
            i = 0
            while (delta_sec <= wt*60) or GPIO.input(FPGA_STATE):
                (out, filename) = csv_new(d_path, e_num, observe_IP, e_chl, i)
                csv_writer = csv_head(out)
                while (delta_sec <= 5.0 * 60 * (i + 1)) & ((delta_sec <= wt * 60) or GPIO.input(FPGA_STATE)):
                    time_now = datetime.now()
                    delta_sec = delta_seconds(e_bgn, time_now)
                        
                    (msg_number, gpio_state) = \
                        record_msg(ser, csv_writer, time_now, msg_number, TIME_STAMP, gpio_state)
                out.close()
                i = i + 1
                time_now = datetime.now()
                delta_sec = delta_seconds(e_bgn, time_now)
            ser.close()
        print("11: This experiment is finished!")
        log.write('11: This experiment is finished! @' + str(datetime.now()) + '\n')
        log.flush()  # <-- here's something not to forget!
        print("    The total message number is %s" % msg_number)
        log.write('    The total message number is %s @' % msg_number + str(datetime.now()) + '\n')
        log.flush()  # <-- here's something not to forget!
    else:
        print("11: This experiment doesn't run!")
        log.write("11: This experiment doesn't run! @" + str(datetime.now()) + '\n')
        log.flush()  # <-- here's something not to forget
    #   GPIO.cleanup()
    gpio_idle_again()
    txt_status_modify(txtName, 7, "idle")
    log.write("    The state returns to idle... @" + str(datetime.now()) + '\n')
    log.flush()  # <-- here's something not to forget
    #time.sleep(2)  # delay 10s
    os.system('pkill -f "adc"')
    print("12: This adc process is killed!")
    log.write('12: This adc process is killed! @' + str(datetime.now()) + '\n')
    log.write('--------------------------------------------------------------------------------------'
              '-----------------------------\n')
    log.flush()  # <-- here's something not to forget!
    log.close()
    sys.exit(0)



