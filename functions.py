import sys
from machine import Pin, PWM
import machine
import utime
from utime import sleep


def turn_on_call_light(bed_button, led, sound):
    if bed_button.value() == 0:
        print("1") 
        utime.sleep_ms(300)
        if bed_button.value() == 0:
            led.value(1)
            sound.freq(300)
            sound.duty_u16(60000)
            
def turn_all_off(off_button, led1, led2, sound):
    if off_button.value() == 0:
        print ("All Off")
        led1.value(0)
        led2.value(0)
        sound.duty_u16(0)
        utime.sleep(7)
        if off_button.value() == 0:
            print("reset")
            for i in range(5):
                led1.high()
                led2.high()
                sound.freq(300)
                sound.duty_u16(60000)
                utime.sleep_ms(500)
                led1.low()
                led2.low()
                sound.duty_u16(0)
                utime.sleep_ms(500)
            machine.reset()