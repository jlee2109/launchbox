#!/usr/bin/env python
import sys
from datetime import datetime
# import RPi.GPIO as GPIO
import time
import traceback
import json
import urllib2
import dateutil.parser
import pytz

from Adafruit_CharLCD.Adafruit_CharLCD import Adafruit_CharLCDPlate

# sys.path.append("/home/pi/Desktop/launchbox/Adafruit_CharLCD")


ROW_NUM = 2  # number of rows on the led screen
COL_NUM = 16  # number of columns on the led screen
DATA_REFRESH_INTERVAL = 20  # seconds
ROW_2_SWITCH_INTERVAL = 30  # seconds


def handle_message(message):
    # use a fancy string slicing trick to get the name to scroll on each line individually
    # TODO: more complicated scrollStart so that scrolling pauses in between each pass
    if len(message) > COL_NUM:
        shifted_message = message[scrollStart % (len(message) - COL_NUM + 1): scrollStart % len(message) + COL_NUM]
        return shifted_message[:COL_NUM]
    else:
        return message


def write_lcd_line_1(message):
    message = handle_message(message)
    lcd.set_cursor(0, 0)
    lcd.message(message)


def write_lcd_line_2(message):
    message = handle_message(message)
    lcd.set_cursor(0, 1)
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
    lcd = Adafruit_CharLCDPlate(cols=COL_NUM, lines=ROW_NUM)
    # lcd.begin(16, 2)

    scrollStart = 0
    loopCount = 0

    write_lcd_line_1("Retrieving launch")
    write_lcd_line_2("data...")

    time_last_data_refresh = 0
    time_line_2_loop = 0

    while 1:
        try:
            # get current time
            current_time = time.time()  # time in unix seconds
            current_datetime = datetime.utcnow().replace(tzinfo=pytz.utc)  # UIC datetime object
            current_timestr = current_datetime.strftime("%m/%d/%y %H:%M:%SUTC")

            # get launch data
            if current_time - time_last_data_refresh > DATA_REFRESH_INTERVAL:
                print 'fetching new launch data at ' + current_timestr
                response = json.load(urllib2.urlopen("https://launchlibrary.net/1.2/launch/next/1"))
                launchName = response["launches"][0]["name"]
                launchTime = dateutil.parser.parse(response["launches"][0]["windowstart"])
                time_last_data_refresh = current_time
                lcd.clear()

            diff = launchTime - current_datetime
            hours = int(diff.seconds / 3600) % 24
            minutes = int(diff.seconds / 60) % 60
            seconds = diff.seconds % 60


            # launchName = 'short_test'
            # if len(launchName) > COL_NUM:
            #     launchNameText = launchName[scrollStart % (len(launchName) - COL_NUM):
            #                                 scrollStart % len(launchName) + COL_NUM]
            # else:
            #     launchNameText = launchName
            write_lcd_line_1(launchName)
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
        except Exception as e:
            write_lcd_line_1("Exception occurred")
            # traceback.print_exc()  # should only be turned on for debugging

        time.sleep(1)

except KeyboardInterrupt:
    sys.exit()
