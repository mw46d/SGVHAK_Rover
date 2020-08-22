#!/usr/bin/python

import time
import serial

s = serial.Serial('/dev/adafruit-display', 115200, timeout = 0.25)

while True:
    s.read(100)

    s.write("t3 Hello Alameda County Faire - Robot Day - RobotGarden.org\r")
    time.sleep(120.0)
    s.read(100)

    s.write("ff\r")
    time.sleep(10.0)
    s.read(100)

    s.write("fh\r")
    time.sleep(30.0)
    s.read(100)

    s.write("ewl\r")
    time.sleep(5.0)
    s.read(100)

    s.write("fh\r")
    time.sleep(30.0)
    s.read(100)
