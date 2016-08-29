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
from Adafruit_CharLCD.Adafruit_CharLCD import LEFT, RIGHT, SELECT

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


# class ButtonSettings(object):
#     # controls settings that can be changed with the buttons on the LCD
#     def __init__(self):
#         self.launch_num = 0
#         self.api_url =



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


def fetch_next_launches(launch_num):
    fetch_num = max(3, launch_num + 1)
    url = "https://launchlibrary.net/1.2/launch/next/" + str(fetch_num)
    response = json.load(urllib2.urlopen(url))
    print '%s launches fetched' % response.get('total', None)
    return response


def parse_launch_info(response, launch_num):
    if launch_num + 1 > response['total']:
        # this happens when a launch_num exceeds the number of launches in the database
        raise LaunchNumIndexError('launch_num greater than number of launches in response')
    launchName = response["launches"][launch_num]["name"]
    launchTime = dateutil.parser.parse(response["launches"][launch_num]["net"])
    return launchName, launchTime


class LaunchNumIndexError(Exception):
    # to be used whenever there is an issue with launch_num
    pass


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


try:
    print "running launchbox..."

    # initialize LCD
    lcd = Adafruit_CharLCDPlate(cols=COL_NUM, lines=ROW_NUM)
    atexit.register(program_end, lcd)
    # lcd.begin(16, 2)

    scrollStart = 0
    loopCount = 0
    line_2_mode = 0
    launch_num = 0
    launch_name_scroll = []
    backlight_on = True
    launch_increment_count = 0
    launch_increment_value = 1

    old_msg_1 = write_lcd_line(1, ["LAUNCHBOX"])
    old_msg_2 = write_lcd_line(2, ["Initializing..."])

    time_last_data_refresh = 0
    time_line_2_loop = time.time()
    time_last_scroll = time.time()

    while 1:
        try:
            new_launch = False  # set here to avoid error loops
            # get current time
            current_time = time.time()  # time in unix seconds
            current_datetime = datetime.utcnow().replace(tzinfo=pytz.utc)  # UIC datetime object
            current_timestr = current_datetime.strftime("%m/%d/%y %H:%M:%SUTC")

            # get launch data
            if current_time - time_last_data_refresh > DATA_REFRESH_INTERVAL:
                print 'fetching new launch data at ' + current_timestr
                response = fetch_next_launches(launch_num)
                launchName, launchTime = parse_launch_info(response, launch_num)
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
            if launch_increment_count == 9:
                launch_increment_value = 5
            if lcd.is_pressed(LEFT):
                launch_num -= launch_increment_value
                if launch_num < 0:
                    launch_num = 0
                new_launch = True
                launch_increment_count += 1
            elif lcd.is_pressed(RIGHT):
                launch_num += launch_increment_value
                new_launch = True
                launch_increment_count += 1
            else:
                launch_increment_count = 0
                launch_increment_value = 1
            if new_launch:  # do this rather than another lcd.is_pressed to avoid race condition
                lcd.clear()
                write_lcd_line(1, ['Launch #%d' % (launch_num + 1)])
                time.sleep(0.5)
                try:
                    launchName, launchTime = parse_launch_info(response, launch_num)
                except LaunchNumIndexError:
                    response = fetch_next_launches(launch_num)
                    time_last_data_refresh = current_time
                    launchName, launchTime = parse_launch_info(response, launch_num)
                launch_name_scroll = generate_scroll_list(launchName)
                lcd.clear()
                scrollStart = 0
            if lcd.is_pressed(SELECT):
                if backlight_on:
                    lcd.set_backlight(0)
                    backlight_on = False
                else:
                    lcd.set_backlight(1)
                    backlight_on = True


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
