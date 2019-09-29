#! /bin/bash
echo "FPGA start work!"
echo "raspberry" | sudo -S echo "I had root"
sudo gcc /home/pi/testbed/code/adc.c -lbcm2835 -o adc

sudo /home/pi/testbed/code/adc
echo "FPGA done!"
