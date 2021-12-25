#!/bin/env python3

import RPi.GPIO as GPIO
import time
import os
import threading
import serial  # pyserial

class Poti:

    def __init__(self,
            a_pin=18,
            b_pin=23,
            poti_min=10,
            poti_max=1250,
            scale_min=10,
            scale_max=180,
            intervall=0.5):
        GPIO.setmode(GPIO.BCM)
        self.a_pin = a_pin
        self.b_pin = b_pin
        self.poti_min = poti_min
        self.poti_max = poti_max
        self.scale_min = scale_min
        self.scale_max = scale_max
        self.intervall = intervall
        self.value = 0
        threading.Thread(target=self.measure).start()

    def get_value(self):
        return self.value

    def discharge(self):
        GPIO.setup(self.a_pin, GPIO.IN)
        GPIO.setup(self.b_pin, GPIO.OUT)
        GPIO.output(self.b_pin, False)
        time.sleep(0.005)

    def charge_time(self):
        GPIO.setup(self.b_pin, GPIO.IN)
        GPIO.setup(self.a_pin, GPIO.OUT)
        count = 0
        GPIO.output(self.a_pin, True)
        while not GPIO.input(self.b_pin):
            count += 1
            if count > self.poti_max:
                break
        return count

    def analog_read(self):
        self.discharge()
        return self.charge_time()

    def scale_signal(self, x):
        lower = self.scale_min
        upper = self.scale_max
        return max((
            lower,
            min((
                upper,
                (upper - lower) * (x - self.poti_min) / (self.poti_max - self.poti_min) + lower
            ))
        ))

    def measure(self):
        while True:
            self.value = self.scale_signal(self.analog_read())
            time.sleep(self.intervall)


class TCodeControler:

    def __init__(self, upper=99, lower=0):
        self.poti = Poti()
        self.upper = upper
        self.lower = lower
        self.strokes_per_minute = 10
        self.serial_device = None
        threading.Thread(target=self.run).start()

    def set_position(self, position, interval=250):
        if self.serial_device is not None and self.serial_device.isOpen():
            position = max((0, min((99, position))))
            self.serial_device.write(
                    bytes('L0' + str(position % 100).zfill(2) + '5I' + str(interval) + '\r\n', 'utf-8')
                )

    def update_stroke_per_minute(self):
        self.strokes_per_minute = self.poti.get_value()

    def run(self):
        while True:
            try:
                self.serial_device = serial.Serial(
                    port= '/dev/ttyACM1' if os.path.exists('/dev/ttyACM1') else '/dev/ttyACM0',
                    baudrate=115200,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    bytesize=serial.EIGHTBITS
                )
                try:
                    self.serial_device.open()
                except:
                    pass

                while True:
                    self.update_stroke_per_minute()
                    self.set_position(
                            position=self.upper,
                            interval=round(float(60)/self.strokes_per_minute*1000/2)
                            )
                    self.update_stroke_per_minute()
                    time.sleep(60/self.strokes_per_minute/2)
                    self.set_position(
                            position=self.lower,
                            interval=round(float(60)/self.strokes_per_minute*1000/2),
                            )
                    time.sleep(60/self.strokes_per_minute/2)
            except Exception as e:
                print(e)
                self.serial_device = None
                time.sleep(1)

controler = TCodeControler()
while True:
    time.sleep(1)
