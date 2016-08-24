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
import atexit

from Adafruit_CharLCD.Adafruit_CharLCD import Adafruit_CharLCDPlate
from Adafruit_CharLCD.Adafruit_CharLCD import LEFT, RIGHT

# USER PREFERENCES
ROW_NUM = 2  # number of rows on the led screen
COL_NUM = 16  # number of columns on the led screen
DATA_REFRESH_INTERVAL = 5 * 60  # seconds
ROW_2_SWITCH_INTERVAL = 30  # seconds

SHORT_TIMESTAMP = True

LOOP_DELAY = 0.1  # sec; minimum amount of time between loops
SCROLL_DELAY = 0.6  # sec; delay to scroll line


# CALCULATED CONSTANTS
SCROLL_LOOP_INTERVAL = int(SCROLL_DELAY / LOOP_DELAY)


def program_end(lcd):
    print 'powering down launchbox...'
    lcd.clear()
    lcd.enable_display(False)
    lcd.set_backlight(0)


def generate_scroll_list(message):
    # list of strings for "scrolling" action
    if len(message) < COL_NUM:
        return [message + ' ' * (COL_NUM - len(message))]
    out = [message[i:i + COL_NUM] for i in range(0, len(message) - COL_NUM + 1)]
    out = [out[0]] * 1 + out + [out[-1]] * 1
    return out


def select_scroll_item(scroll_list):
    return scroll_list[scrollStart % len(scroll_list)]


def write_lcd_line(row, scroll_list, old_message=''):
    # row count starts at row = 1
    if not isinstance(scroll_list, list):
        raise TypeError("scroll list must be a list type: %s" % scroll_list)
    message = select_scroll_item(scroll_list)
    if message != old_message:
        lcd.set_cursor(0, row - 1)
        lcd.message(message)
    return message


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
    print "running launchbox..."

    # initialize LCD
    lcd = Adafruit_CharLCDPlate(cols=COL_NUM, lines=ROW_NUM)
    atexit.register(program_end, lcd)
    # lcd.begin(16, 2)

    scrollStart = 0
    loopCount = 0
    line_2_mode = 0
    launch_num = 1
    launch_name_scroll = []

    old_msg_1 = write_lcd_line(1, ["LAUNCHBOX"])
    old_msg_2 = write_lcd_line(2, ["Initializing..."])

    time_last_data_refresh = 0
    time_line_2_loop = time.time()
    time_last_scroll = time.time()

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
                launchTime = dateutil.parser.parse(response["launches"][0]["net"])
                time_last_data_refresh = current_time
                launch_name_scroll = generate_scroll_list(launchName)
                lcd.clear()
                # scrollStart = len(launchName)

            # calculations
            diff = launchTime - current_datetime
            # TODO: handle when diff.days ia negative, indicating this rocket already launched
            hours = int(diff.seconds / 3600) % 24
            minutes = int(diff.seconds / 60) % 60
            seconds = diff.seconds % 60

            # line 1
            old_msg_1 = write_lcd_line(1, launch_name_scroll, old_msg_1)

            # line 2
            if current_time - time_line_2_loop > ROW_2_SWITCH_INTERVAL:
                if line_2_mode == 0:
                    line_2_mode = 1
                elif line_2_mode == 1:
                    line_2_mode = 0
                time_line_2_loop = current_time
                write_lcd_line(2, [' ' * (COL_NUM + 1)])
            if line_2_mode == 0:
                if SHORT_TIMESTAMP:
                    write_lcd_line(2, generate_scroll_list(launchTime.strftime("%m/%d %H:%M:%S")), old_msg_2)
                else:
                    write_lcd_line(2, generate_scroll_list(launchTime.strftime("%m/%d/%y %H:%M:%SUTC")), old_msg_2)
            elif line_2_mode == 1:
                if SHORT_TIMESTAMP:
                    write_lcd_line(2, generate_scroll_list(
                        "{0}d {1}h {2}m {3}s".format(diff.days, hours, minutes, seconds)), old_msg_2)
                else:
                    write_lcd_line(2, generate_scroll_list(
                        "T- {0}d {1}h {2}m {3}s".format(diff.days, hours, minutes, seconds)), old_msg_2)
            else:
                raise ValueError('line_2_mode invalid: %s' % line_2_mode)

            # check for button presses
            if lcd.is_pressed(LEFT):
                print 'LEFT pressed'
            if lcd.is_pressed(RIGHT):
                print 'RIGHT pressed'

            # cleanup the loop
            if current_time - time_last_scroll > SCROLL_DELAY:
                scrollStart += 1
                time_last_scroll = current_time
            loopCount += 1
            # this would take forever to happen, but handle it just in case
            if scrollStart == sys.maxint or loopCount == sys.maxint:
                scrollStart = 0
                loopCount = 0

            loop_time = time.time() - current_time  # time taken to pass through the loop
            # print 'Elapsed time: %1.5f sec' % loop_time
            time.sleep(max(0, LOOP_DELAY - loop_time))

        except Exception as e:
            lcd.clear()
            write_lcd_line(1, ["Exception occurred"])
            traceback.print_exc()  # should only be turned on for debugging
            time.sleep(5)  # wait period before trying again

except KeyboardInterrupt:
    sys.exit()
