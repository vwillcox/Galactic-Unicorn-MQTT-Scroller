# Asynchronous mqtt client with clean session (C) Copyright Peter Hinch 2017-2019.
# Released under the MIT licence.
# Modified by Vincent Willcox 2023 to add 8-bit music when a message is displayed
# Also added an option to change colour of background by playing a known colour in front
# of the message that if reconised will get stripped out and used to set the colour


# Public brokers https://github.com/mqtt/mqtt.github.io/wiki/public_brokers

# The use of clean_session means that after a connection failure subscriptions
# must be renewed (MQTT spec 3.1.2.4). This is done by the connect handler.
# Note that publications issued during the outage will be missed. If this is
# an issue see unclean.py.

# red LED: ON == WiFi fail
# blue LED heartbeat: demonstrates scheduler is running.



#Import libraries - config.py sets up wifi and mqtt
import time
import math

from galactic import GalacticUnicorn, Channel
from picographics import PicoGraphics, DISPLAY_GALACTIC_UNICORN as DISPLAY


from mqtt_as import MQTTClient, config
from config import wifi_led, blue_led  # Local definitions
import uasyncio as asyncio
import machine
from machine import Pin, PWM, Timer
from time import sleep
import machine

machine.freq(200000000)

# constants for controlling scrolling text
PADDING = 2
MESSAGE_COLOUR = (255, 255, 255)
OUTLINE_COLOUR = (0, 0, 0)
MESSAGE = ""
BACKGROUND_COLOUR = (10, 0, 96) # Blue

#BACKGROUND_COLOUR = (255, 255, 0) # Yellow
HOLD_TIME = 2.0
STEP_TIME = 0.045 #Edit to slow down/speed up text - lower for faster scrolling

# create galactic object and graphics surface for drawing
gu = GalacticUnicorn()
graphics = PicoGraphics(DISPLAY)

width = GalacticUnicorn.WIDTH
height = GalacticUnicorn.HEIGHT

# state constants
STATE_PRE_SCROLL = 0
STATE_SCROLLING = 1
STATE_POST_SCROLL = 2

shift = 0
state = STATE_PRE_SCROLL

# set the font
graphics.set_font("bitmap8")

# calculate the message width so scrolling can happen
msg_width = graphics.measure_text(MESSAGE, 1)

last_time = time.ticks_ms()

### Sound

SONG_LENGTH = 384
HAT = 20000
BASS = 500
SNARE = 6000
SUB = 50

melody_notes = (
    147, 0, 0, 0, 0, 0, 0, 0, 175, 0, 196, 0, 220, 0, 262, 0, 247, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 0, 0, 0, 175, 0, 0, 0, 0, 0, 0, 0, 175, 0, 196, 0, 220, 0, 262, 0, 330, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 0, 0, 0, 349, 0, 0, 0, 0, 0, 0, 0, 349, 0, 330, 0, 294, 0, 220, 0, 262, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 0, 0, 0, 247, 0, 0, 0, 0, 0, 0, 0, 247, 0, 220, 0, 196, 0, 147, 0, 175, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 0, 0, 0,
    147, 0, 0, 0, 0, 0, 0, 0, 175, 0, 196, 0, 220, 0, 262, 0, 247, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 0, 0, 0, 175, 0, 0, 0, 0, 0, 0, 0, 175, 0, 196, 0, 220, 0, 262, 0, 330, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 0, 0, 0, 349, 0, 0, 0, 0, 0, 0, 0, 349, 0, 330, 0, 294, 0, 220, 0, 262, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 0, 0, 0, 247, 0, 0, 0, 0, 0, 0, 0, 247, 0, 220, 0, 196, 0, 147, 0, 175, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 0, 0, 0,
    147, 0, 0, 0, 0, 0, 0, 0, 175, 0, 196, 0, 220, 0, 262, 0, 247, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 0, 0, 0, 175, 0, 0, 0, 0, 0, 0, 0, 175, 0, 196, 0, 220, 0, 262, 0, 330, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 0, 0, 0, 349, 0, 0, 0, 0, 0, 0, 0, 349, 0, 330, 0, 294, 0, 220, 0, 262, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 0, 0, 0, 247, 0, 0, 0, 0, 0, 0, 0, 247, 0, 262, 0, 294, 0, 392, 0, 440, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

rhythm_notes = (
    294, 0, 440, 0, 587, 0, 440, 0, 294, 0, 440, 0, 587, 0, 440, 0, 294, 0, 440, 0, 587, 0, 440, 0, 294, 0, 440, 0, 587, 0, 440, 0, 294, 0, 440, 0, 587, 0, 440, 0, 294, 0, 440, 0, 587, 0, 440, 0, 392, 0, 523, 0, 659, 0, 523, 0, 392, 0, 523, 0, 659, 0, 523, 0, 698, 0, 587, 0, 440, 0, 587, 0, 698, 0, 587, 0, 440, 0, 587, 0, 523, 0, 440, 0, 330, 0, 440, 0, 523, 0, 440, 0, 330, 0, 440, 0, 349, 0, 294, 0, 220, 0, 294, 0, 349, 0, 294, 0, 220, 0, 294, 0, 262, 0, 247, 0, 220, 0, 175, 0, 165, 0, 147, 0, 131, 0, 98, 0,
    294, 0, 440, 0, 587, 0, 440, 0, 294, 0, 440, 0, 587, 0, 440, 0, 294, 0, 440, 0, 587, 0, 440, 0, 294, 0, 440, 0, 587, 0, 440, 0, 294, 0, 440, 0, 587, 0, 440, 0, 294, 0, 440, 0, 587, 0, 440, 0, 392, 0, 523, 0, 659, 0, 523, 0, 392, 0, 523, 0, 659, 0, 523, 0, 698, 0, 587, 0, 440, 0, 587, 0, 698, 0, 587, 0, 440, 0, 587, 0, 523, 0, 440, 0, 330, 0, 440, 0, 523, 0, 440, 0, 330, 0, 440, 0, 349, 0, 294, 0, 220, 0, 294, 0, 349, 0, 294, 0, 220, 0, 294, 0, 262, 0, 247, 0, 220, 0, 175, 0, 165, 0, 147, 0, 131, 0, 98, 0,
    294, 0, 440, 0, 587, 0, 440, 0, 294, 0, 440, 0, 587, 0, 440, 0, 294, 0, 440, 0, 587, 0, 440, 0, 294, 0, 440, 0, 587, 0, 440, 0, 294, 0, 440, 0, 587, 0, 440, 0, 294, 0, 440, 0, 587, 0, 440, 0, 392, 0, 523, 0, 659, 0, 523, 0, 392, 0, 523, 0, 659, 0, 523, 0, 698, 0, 587, 0, 440, 0, 587, 0, 698, 0, 587, 0, 440, 0, 587, 0, 523, 0, 440, 0, 330, 0, 440, 0, 523, 0, 440, 0, 330, 0, 440, 0, 349, 0, 294, 0, 220, 0, 294, 0, 349, 0, 294, 0, 220, 0, 294, 0, 262, 0, 247, 0, 220, 0, 175, 0, 165, 0, 147, 0, 131, 0, 98, 0)

drum_beats = (
    BASS, -1, 0, 0, 0, 0, 0, 0, SNARE, 0, -1, 0, 0, 0, BASS, -1, BASS, -1, 0, 0, 0, 0, 0, 0, SNARE, 0, -1, 0, 0, 0, 0, 0, BASS, -1, 0, 0, 0, 0, 0, 0, SNARE, 0, -1, 0, 0, 0, BASS, -1, BASS, -1, 0, 0, 0, 0, 0, 0, SNARE, 0, -1, 0, 0, 0, 0, 0, BASS, -1, 0, 0, 0, 0, 0, 0, SNARE, 0, -1, 0, 0, 0, BASS, -1, BASS, -1, 0, 0, 0, 0, 0, 0, SNARE, 0, -1, 0, 0, 0, 0, 0, BASS, -1, 0, 0, 0, 0, 0, 0, SNARE, 0, -1, 0, 0, 0, BASS, -1, BASS, -1, 0, 0, 0, 0, 0, 0, SNARE, 0, -1, 0, 0, 0, 0, 0,
    BASS, -1, 0, 0, 0, 0, 0, 0, SNARE, 0, -1, 0, 0, 0, BASS, -1, BASS, -1, 0, 0, 0, 0, 0, 0, SNARE, 0, -1, 0, 0, 0, 0, 0, BASS, -1, 0, 0, 0, 0, 0, 0, SNARE, 0, -1, 0, 0, 0, BASS, -1, BASS, -1, 0, 0, 0, 0, 0, 0, SNARE, 0, -1, 0, 0, 0, 0, 0, BASS, -1, 0, 0, 0, 0, 0, 0, SNARE, 0, -1, 0, 0, 0, BASS, -1, BASS, -1, 0, 0, 0, 0, 0, 0, SNARE, 0, -1, 0, 0, 0, 0, 0, BASS, -1, 0, 0, 0, 0, 0, 0, SNARE, 0, -1, 0, 0, 0, BASS, -1, BASS, -1, 0, 0, 0, 0, 0, 0, SNARE, 0, -1, 0, 0, 0, 0, 0,
    BASS, -1, 0, 0, 0, 0, 0, 0, SNARE, 0, -1, 0, 0, 0, BASS, -1, BASS, -1, 0, 0, 0, 0, 0, 0, SNARE, 0, -1, 0, 0, 0, 0, 0, BASS, -1, 0, 0, 0, 0, 0, 0, SNARE, 0, -1, 0, 0, 0, BASS, -1, BASS, -1, 0, 0, 0, 0, 0, 0, SNARE, 0, -1, 0, 0, 0, 0, 0, BASS, -1, 0, 0, 0, 0, 0, 0, SNARE, 0, -1, 0, 0, 0, BASS, -1, BASS, -1, 0, 0, 0, 0, 0, 0, SNARE, 0, -1, 0, 0, 0, 0, 0, BASS, -1, 0, 0, 0, 0, 0, 0, SNARE, 0, -1, 0, 0, 0, BASS, -1, BASS, -1, 0, 0, 0, 0, 0, 0, SNARE, 0, -1, 0, 0, 0, 0, 0)

hi_hat = (
    HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1,
    HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1,
    HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1, HAT, -1)

bass_notes = (
    SUB, -1, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, SUB, -1, SUB, -1, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 0, 0, SUB, -1, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, SUB, -1, SUB, -1, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 0, 0, SUB, -1, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, SUB, -1, SUB, -1, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 0, 0, SUB, -1, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, SUB, -1, SUB, -1, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 0, 0,
    SUB, -1, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, SUB, -1, SUB, -1, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 0, 0, SUB, -1, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, SUB, -1, SUB, -1, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 0, 0, SUB, -1, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, SUB, -1, SUB, -1, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 0, 0, SUB, -1, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, SUB, -1, SUB, -1, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 0, 0,
    SUB, -1, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, SUB, -1, SUB, -1, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 0, 0, SUB, -1, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, SUB, -1, SUB, -1, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 0, 0, SUB, -1, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, SUB, -1, SUB, -1, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 0, 0, SUB, -1, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, SUB, -1, SUB, -1, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 0, 0)

notes = [melody_notes, rhythm_notes, drum_beats, hi_hat, bass_notes]
channels = [gu.synth_channel(i) for i in range(len(notes))]


def gradient(r, g, b):
    for y in range(0, height):
        for x in range(0, width):
            graphics.set_pen(graphics.create_pen(int((r * x) / 52), int((g * x) / 52), int((b * x) / 52)))
            graphics.pixel(x, y)


def grid(r, g, b):
    for y in range(0, height):
        for x in range(0, width):
            if (x + y) % 2 == 0:
                graphics.set_pen(graphics.create_pen(r, g, b))
            else:
                graphics.set_pen(0)
            graphics.pixel(x, y)


def outline_text(text):
    ms = time.ticks_ms()

    graphics.set_font("bitmap8")
    v = int((math.sin(ms / 100.0) + 1.0) * 127.0)
    w = graphics.measure_text(text, 1)

    x = int(53 / 2 - w / 2 + 1)
    y = 2

    graphics.set_pen(0)
    graphics.text(text, x - 1, y - 1, -1, 1)
    graphics.text(text, x, y - 1, -1, 1)
    graphics.text(text, x + 1, y - 1, -1, 1)
    graphics.text(text, x - 1, y, -1, 1)
    graphics.text(text, x + 1, y, -1, 1)
    graphics.text(text, x - 1, y + 1, -1, 1)
    graphics.text(text, x, y + 1, -1, 1)
    graphics.text(text, x + 1, y + 1, -1, 1)

    graphics.set_pen(graphics.create_pen(v, v, v))
    graphics.text(text, x, y, -1, 1)


gu.set_brightness(0.5)

# Vars for storing button state
was_a_pressed = False
was_b_pressed = False
was_c_pressed = False
was_d_pressed = False
was_z_pressed = False

# The two frequencies to play
tone_a = 0
tone_b = 0

# The current synth beat
beat = 0


def next_beat():
    global beat
    for i in range(5):
        if notes[i][beat] > 0:
            channels[i].frequency(notes[i][beat])
            channels[i].trigger_attack()
        elif notes[i][beat] == -1:
            channels[i].trigger_release()

    beat = (beat + 1) % SONG_LENGTH


def tick(timer):
    next_beat()


timer = Timer(-1)

synthing = False

### end sound?
# MQTT Message Subscription and Display

def sub_cb(topic, msg, retained):
    #print(f'Topic: "{topic.decode()}" Message: "{msg.decode()}" Retained: {retained}')
    
    synthing = False    
    # state constants
    brightness = 0.5
    gu.set_brightness(brightness)
    STATE_PRE_SCROLL = 0
    STATE_SCROLLING = 1
    STATE_POST_SCROLL = 2

    shift = 0
    state = STATE_PRE_SCROLL
    timer.init(freq=10, mode=Timer.PERIODIC, callback=tick)
    def outline_text(text, x, y):
        graphics.set_pen(graphics.create_pen(int(OUTLINE_COLOUR[0]), int(OUTLINE_COLOUR[1]), int(OUTLINE_COLOUR[2])))
        graphics.text(text, x - 1, y - 1, -1, 1)
        graphics.text(text, x, y - 1, -1, 1)
        graphics.text(text, x + 1, y - 1, -1, 1)
        graphics.text(text, x - 1, y, -1, 1)
        graphics.text(text, x + 1, y, -1, 1)
        graphics.text(text, x - 1, y + 1, -1, 1)
        graphics.text(text, x, y + 1, -1, 1)
        graphics.text(text, x + 1, y + 1, -1, 1)

        graphics.set_pen(graphics.create_pen(int(MESSAGE_COLOUR[0]), int(MESSAGE_COLOUR[1]), int(MESSAGE_COLOUR[2])))
        graphics.text(text, x, y, -1, 1)
    
    DATA = (msg.decode('utf-8'))
    
    DATA2 = str(DATA)
    COLOUR = DATA2.partition(' ')[0]
    #DATA3 = DATA2.split(' ', 1)[1]
    print(COLOUR)
    print(DATA2)
    MESSAGE = 'NOTSET'
    
    if COLOUR.upper() == 'GREEN':
        BACKGROUND_COLOUR = (0,255,0)
        DATA3 = DATA2.split(' ', 1)[1]
        MESSAGE = "                " + DATA3 + "             "+ DATA3 + "             "
    elif COLOUR.upper() == 'RED':
        BACKGROUND_COLOUR = (255,0,0)
        DATA3 = DATA2.split(' ', 1)[1]
        MESSAGE = "                " + DATA3 + "             "+ DATA3 + "             "
    elif COLOUR.upper() == 'BLUE':
        BACKGROUND_COLOUR = (10, 0, 96)
        DATA3 = DATA2.split(' ', 1)[1]
        MESSAGE = "                " + DATA3 + "             "+ DATA3 + "             "
    elif COLOUR.upper() == 'YELLOW':
        BACKGROUND_COLOUR = (255, 255, 0)
        DATA3 = DATA2.split(' ', 1)[1]
        MESSAGE = "                " + DATA3 + "             "+ DATA3 + "             "
    elif COLOUR.upper() == 'BROWN':
        BACKGROUND_COLOUR = (61, 43, 31)
        DATA3 = DATA2.split(' ', 1)[1]
        MESSAGE = "                " + DATA3 + "             "+ DATA3 + "             "
    elif COLOUR.upper() == 'PINK':
        BACKGROUND_COLOUR = (255, 110, 199)
        DATA3 = DATA2.split(' ', 1)[1]
        MESSAGE = "                " + DATA3 + "             "+ DATA3 + "             "
    elif COLOUR.upper() == 'ORANGE':
        BACKGROUND_COLOUR = (255,127,0)
        DATA3 = DATA2.split(' ', 1)[1]
        MESSAGE = "                " + DATA3 + "             "+ DATA3 + "             "
    else:
        BACKGROUND_COLOUR = (255, 255, 0)
        
        MESSAGE = "                " + DATA2 + "             "+ DATA2 + "             "
    
    #MESSAGE = "                " + DATA3 + "             "+ DATA3 + "             "
    
# calculate the message width so scrolling can happen

    
    msg_width = graphics.measure_text(MESSAGE, 1)

    last_time = time.ticks_ms()
       

    #print (MESSAGE)
    #make a noise
    
    channels[0].configure(waveforms=Channel.TRIANGLE + Channel.SQUARE,
                                  attack=0.016,
                                  decay=0.168,
                                  sustain=0xafff / 65535,
                                  release=0.168,
                                  volume=10000 / 65535)
    channels[1].configure(waveforms=Channel.SINE + Channel.SQUARE,
                                  attack=0.038,
                                  decay=0.300,
                                  sustain=0,
                                  release=0,
                                  volume=12000 / 65535)
    channels[2].configure(waveforms=Channel.NOISE,
                                  attack=0.005,
                                  decay=0.010,
                                  sustain=16000 / 65535,
                                  release=0.100,
                                  volume=18000 / 65535)
    channels[3].configure(waveforms=Channel.NOISE,
                                  attack=0.005,
                                  decay=0.005,
                                  sustain=8000 / 65535,
                                  release=0.040,
                                  volume=8000 / 65535)
    channels[4].configure(waveforms=Channel.SQUARE,
                                  attack=0.010,
                                  decay=0.100,
                                  sustain=0,
                                  release=0.500,
                                  volume=12000 / 65535)

            # If the synth is not already playing, init the first beat
    if not synthing:
        beat = 0
        next_beat()
    gu.play_synth()
    synthing = True
    timer.init(freq=10, mode=Timer.PERIODIC, callback=tick)
    
    while True:
        time_ms = time.ticks_ms()

        if gu.is_pressed(GalacticUnicorn.SWITCH_BRIGHTNESS_UP):
            gu.adjust_brightness(+0.01)

        if gu.is_pressed(GalacticUnicorn.SWITCH_BRIGHTNESS_DOWN):
            gu.adjust_brightness(-0.01)

        if state == STATE_PRE_SCROLL and time_ms - last_time > HOLD_TIME * 1000:
            if msg_width + PADDING * 2 >= width:
                state = STATE_SCROLLING
            last_time = time_ms

        if state == STATE_SCROLLING and time_ms - last_time > STEP_TIME * 1000:
            shift += 1
            if shift >= (msg_width + PADDING * 2) - width - 1:
                state = STATE_POST_SCROLL
                brightness = 0
                gu.set_brightness(brightness)
                gu.update(graphics)
                break
            last_time = time_ms
           

        if state == STATE_POST_SCROLL and time_ms - last_time > HOLD_TIME * 1000:
            state = STATE_PRE_SCROLL
            shift = 0
            last_time = time_ms
            

        graphics.set_pen(graphics.create_pen(int(BACKGROUND_COLOUR[0]), int(BACKGROUND_COLOUR[1]), int(BACKGROUND_COLOUR[2])))
        graphics.clear()

        outline_text(MESSAGE, x=PADDING - shift, y=2)

        # update the display
        gu.update(graphics)

        # pause for a moment (important or the USB serial device will fail)
        time.sleep(0.001)
    tone_a = 0
    tone_b = 0
    gu.stop_playing()
    timer.deinit()
    synthing = False
    
    
    
# Demonstrate scheduler is operational.
async def heartbeat():
    s = True
    while True:
        await asyncio.sleep_ms(500)
        blue_led(s)
        s = not s

async def wifi_han(state):
    wifi_led(not state)
    print('Wifi is ', 'up' if state else 'down')
   # sweep()
    await asyncio.sleep(1)

# If you connect with clean_session True, must re-subscribe (MQTT spec 3.1.2.4)
async def conn_han(client):
    
# MQTT Subscirbe Topic   
    await client.subscribe('personal/#', 1)

async def main(client):
    try:
        await client.connect()
    except OSError:
        print('Connection failed.')
        machine.reset()
        return
    n = 0
    while True:
        await asyncio.sleep(5)
       # print('publish', n)
        # If WiFi is down the following will pause for the duration.
        #await client.publish('result', '{} {}'.format(n, client.REPUB_COUNT), qos = 1)
        n += 1

# Define configuration
config['subs_cb'] = sub_cb
config['wifi_coro'] = wifi_han
config['connect_coro'] = conn_han
config['clean'] = True

# Set up client
MQTTClient.DEBUG = True  # Optional
client = MQTTClient(config)

asyncio.create_task(heartbeat())


try:
    asyncio.run(main(client))
    

finally:
    client.close()  # Prevent LmacRxBlk:1 errors
    asyncio.new_event_loop()
