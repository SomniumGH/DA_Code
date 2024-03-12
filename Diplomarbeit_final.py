#!/usr/bin/env python3
########################################################################
# Filename    : automated_waterfilter_system_final.py
# Description : This programm is intended for Raspbery Pi 3b+ . The programm shows the funciton of a automated waterfilter system including (temperature regulation, water-level regulation and display)
# Author      : Schmalzl Fabio
# modification: 2024/05/02
########################################################################

import RPi.GPIO as GPIO
import time
import drivers

from w1thermsensor import W1ThermSensor
from ADCDevice import *

GPIO.setwarnings(False)

adc = ADCDevice()               # Define an ADCDevice class object
sensor = W1ThermSensor()        # Create a DS18B20 sensor object
display = drivers.Lcd()         # Create a Display object

heater_Pin =18
GPIO.setup(heater_Pin, GPIO.OUT)

valvePin = 17                   # Define the GPIO pin
GPIO.setup(valvePin, GPIO.OUT)

small_pump_Pin = 17             # Define the GPIO pin
GPIO.setup(small_pump_Pin, GPIO.OUT)

trigPin = 23
echoPin = 24
MAX_DISTANCE = 220              # define the maximum measuring distance, unit: cm
timeOut = MAX_DISTANCE * 60     # calculate timeout according to the maximum measuring distance

distance_values = []


def setup():
    GPIO.setmode(GPIO.BCM)  # Set the GPIO mode to BCM

    GPIO.setup(small_pump_Pin, GPIO.OUT)  # Set up the GPIO pin as an output

    GPIO.setup(trigPin, GPIO.OUT)  # set trigPin to OUTPUT mode
    GPIO.setup(echoPin, GPIO.IN)  # set echoPin to INPUT mode

    global adc
    if (adc.detectI2C(0x48)):  # Detect the pcf8591.
        adc = PCF8591()
    elif (adc.detectI2C(0x4b)):  # Detect the ads7830
        adc = ADS7830()
    else:
        print("No correct I2C address found, \n"
              "Please use command 'i2cdetect -y 1' to check the I2C address! \n"
              "Program Exit. \n");
        exit(-1)


def destroy():
    adc.close()
    GPIO.cleanup()
    display.lcd_clear()


def soll_temperature():
    value = adc.analogRead(0)  # read the ADC value of channel 0
    temp_adc = value / 255.0 * 50  # calculate the temperature value
    print('Soll-Temperature : %.2f' % (temp_adc))
    return temp_adc


def zweipunktregler():
    soll = soll_temperature()

    # Read the temperature from the DS18B20 sensor
    ist = sensor.get_temperature()
    print("Ist-Temperature : %.2f" % (ist))

    if ist < (soll - 1):

        GPIO.output(heater_Pin, GPIO.HIGH)  # Turn on the GPIO pin
        # display.lcd_display_string("Heizstab ein      ", 2)

    elif ist > (soll):

        GPIO.output(heater_Pin, GPIO.LOW)  # Turn off the GPIO pin
        # display.lcd_display_string("Heizstab aus     ", 2)

    display.lcd_display_string("Ist: {:.2f}C".format(ist), 1)
    display.lcd_display_string("Soll: {:.2f}C".format(soll), 2)


def pulseIn(pin, level, timeOut):  # obtain pulse time of a pin under timeOut
    t0 = time.time()
    while (GPIO.input(pin) != level):
        if ((time.time() - t0) > timeOut * 0.000001):
            return 0;
    t0 = time.time()
    while (GPIO.input(pin) == level):
        if ((time.time() - t0) > timeOut * 0.000001):
            return 0;
    pulseTime = (time.time() - t0) * 1000000
    return pulseTime


def get_distance():  # get the measurement results of ultrasonic module,with unit: cm

    GPIO.output(trigPin, GPIO.HIGH)  # make trigPin output 10us HIGH level
    time.sleep(0.00001)  # 10us
    GPIO.output(trigPin, GPIO.LOW)  # make trigPin output LOW level

    pingTime = pulseIn(echoPin, GPIO.HIGH, timeOut)  # read plus time of echoPin
    distance = round(pingTime * 340.0 / 2.0 / 10000.0)  # calculate distance with sound speed 340m/s

    # print ("The distance is : %.1f cm"%(distance))

    distance_values.append(distance)

    if len(distance_values) > 10:
        distance_values.pop(0)  # Remove the oldest value if the list size exceeds 10

    print("Last 10 distance values:", distance_values)

    return distance


def get_fuellstand():
    tank_height = 20
    sensor_height = 3
    max_water_level = 100


    distance_ = get_distance()  # get distance
    if distance_ != 0:  # distance cannot be 0 (Problem: division through zero)
        fuellstand = (1 - (distance_ - sensor_height) / tank_height) * 100  # calculate water-level from distance
        fuellstand = max(0, min(100, fuellstand))
        print("Prozent: %.f" % (fuellstand))

        if fuellstand < 50:
            GPIO.output(valvePin, GPIO.HIGH)
            print("Valve opened")
        elif fuellstand >= 100:
            GPIO.output(valvePin, GPIO.LOW)
            print("Valve closed")
        elif fuellstand >= max_water_level:
            GPIO.output(valvePin, GPIO.LOW)
            print("Valve closed")

def get_average():
    sum = 0
    global average

    for i in distance_values:
        sum = sum + i

    average = sum / len(distance_values)
    print(f'The average of these numbers is: {average}')


def anomaly_detection(current_distance):
    global average

    # Check if the current distance is more than 5% over or under the average
    if current_distance > 1.05 * average or current_distance < 0.95 * average:
        # Pop the current distance
        distance_values.pop()
        print("Current distance popped due to anomaly.")
    else:
        # Append the current distance
        distance_values.append(current_distance)

    # Recalculate the average
    average = get_average()
    print(f'The updated average is: {average}')


if _name_ == '_main_':  # Program entrance
    print('Program is starting ... ')
    try:
        setup()

        while True:
            zweipunktregler()
            time.sleep(1)

            get_fuellstand()
            time.sleep(1)

            get_average()
            time.sleep(1)

            anomaly_detection()
            time.sleep(1)


    except KeyboardInterrupt:  # Press ctrl-c to end the program.
        destroy()