#!/usr/bin/env python
import sys
from datetime import datetime
# import RPi.GPIO as GPIO
import time
import json
import urllib2
import dateutil.parser
import pytz

from Adafruit_CharLCD.Adafruit_CharLCD import Adafruit_CharLCD

# sys.path.append("/home/pi/Desktop/launchbox/Adafruit_CharLCD")


def write_lcd_line_1(message):
    lcd.setCursor(0, 0)
    lcd.message(message)


def write_lcd_line_2(message):
    lcd.setCursor(0, 1)
    lcd.message(message)

# current screen only has 2 lines

# def write_lcd_line_3(message):
#     lcd.setCursor(0, 2)
#     lcd.message(message)
#
#
# def write_lcd_line_4(message):
#     lcd.setCursor(0, 3)
#     lcd.message(message)


def send_links():
    # this sends a list of streaming video links as a note to
    # your pushbullet account
    global response
    links = response["launches"][0]["vidURLs"]

    linkstring = ""
    for link in links:
        linkstring = linkstring + link + "\r\n"

    # write_lcd_line_4("Sending links...")
    time.sleep(1)
    # write_lcd_line_4("Links sent!     ")
    time.sleep(5)
    # write_lcd_line_4("                ")


# setup input pin to detect button push
# GPIO.setmode(GPIO.BCM)
# GPIO.setup(18, GPIO.IN, pull_up_down=GPIO.PUD_UP)
# GPIO.add_event_detect(18, GPIO.FALLING, callback=send_links, bouncetime=200)

try:
    print "running countdown..."

    # initialize LCD
    lcd = Adafruit_CharLCD()
    lcd.begin(20, 4)

    write_lcd_line_1("Retrieving launch")
    write_lcd_line_2("data...")

    scrollStart = 0
    loopCount = 0
    while 1:
        try:
            # get launch data
            if loopCount == 0:
                response = json.load(urllib2.urlopen("https://launchlibrary.net/1.2/launch/next/1"))
                launchName = response["launches"][0]["name"]
                launchTime = dateutil.parser.parse(response["launches"][0]["windowstart"])
                lcd.clear()

            currentTime = datetime.utcnow().replace(tzinfo=pytz.utc)
            diff = launchTime - currentTime
            hours = int(diff.seconds / 3600) % 24
            minutes = int(diff.seconds / 60) % 60
            seconds = diff.seconds % 60

            # use a fancy string slicing trick to get the name to scroll
            # note the magic number 20 because the display has 20 columns
            launchNameText = launchName[scrollStart % (len(launchName) - 20): scrollStart % len(launchName) + 20]
            write_lcd_line_1(launchNameText[:20])
            write_lcd_line_2(launchTime.strftime("%m/%d/%y %H:%M:%SUTC"))
            # write_lcd_line_3("{0}d {1}h {2}m {3}s ".format(diff.days, hours, minutes, seconds))
            scrollStart += 1
            loopCount += 1

            # this would take forever to happen, but handle it just in case
            if scrollStart == sys.maxint:
                scrollStart = 0

            # this controls the web callout, making it happen every 600 seconds
            if loopCount == 600:
                loopCount = 0
        except:
            write_lcd_line_1("Exception occured")

        time.sleep(1)

except KeyboardInterrupt:
    sys.exit()
