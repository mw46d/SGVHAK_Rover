#!/usr/bin/python3

#
# https://learn.adafruit.com/adafruit-128x64-oled-bonnet-for-raspberry-pi/usage
#

import board
import busio
from digitalio import DigitalInOut, Direction, Pull
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306
import subprocess
import sys
import time

# Create the I2C interface.
i2c = busio.I2C(board.SCL, board.SDA)
# Create the SSD1306 OLED class.
disp = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c)



# Input pins:
button_B = DigitalInOut(board.D6)
button_B.direction = Direction.INPUT
button_B.pull = Pull.UP

ip = subprocess.check_output('ifconfig wlan0 | awk \'$1 == "inet" { print $2}\'', shell = True).decode('utf-8').strip()
content = None
ssid = ""
ssid_pw = ""
with open("/etc/hostapd/hostapd.conf") as f:
    content = f.readlines()
for l in content:
    a = l.strip().split('=')
    # print(a)
    if a[0] == 'ssid':
        ssid = a[1]
    elif a[0] == 'wpa_passphrase':
        ssid_pw = a[1]

# Clear display.
disp.fill(0)
disp.show()

# Create blank image for drawing.
# Make sure to create image with mode '1' for 1-bit color.
width = disp.width
height = disp.height
image = Image.new('1', (width, height))

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

# Draw a black filled box to clear the image.
draw.rectangle((0, 0, width, height), outline=0, fill=0)

font = ImageFont.load_default()

draw.text((0,  0), ' WiFi: %s' % ssid, font = font, fill = 1)
draw.text((0, 12), '   %s' % ssid_pw, font = font, fill = 1)
draw.text((0, 24), ' IP:   %s' % ip, font = font, fill = 1)
draw.text((0, 36), ' http://<ip>:5000/', font = font, fill = 1)
draw.text((0, 54), ' Shutdown: Btn     #6', font = font, fill = 1)

disp.image(image)
disp.show()

while True:
    if not button_B.value:
        disp.fill(0)
        disp.show()
        subprocess.call([ "/usr/bin/sudo", "/sbin/shutdown", "-h", "now" ])

    time.sleep(0.5)
