import sys
from machine import Pin, PWM
import utime
from utime import sleep
import functions
from functions import turn_on_call_light, turn_all_off


LED1 = Pin(0, Pin.
LED2 = Pin(15, Pin.OUT)
ALL_LED = Pin(0, Pin.OUT)
buzzer = PWM(Pin(22))


bed1 = Pin(1, Pin.IN, Pin.PULL_UP)
bed2 = Pin(26, Pin.IN, Pin.PULL_UP)
bth1 = Pin(14, Pin.IN, Pin.PULL_UP)
off_all = Pin(4, Pin.IN, Pin.PULL_UP)
led = Pin(25, Pin.OUT)

led.toggle ()

while True:
    
#Bed 1 uses Blue and Blue/White (Blue/White is Ground)
    turn_on_call_light(bed1, LED1, buzzer)
    
#Bed 2 uses Orange and Orange/White (Orange/White is Ground)    
    turn_on_call_light(bed2, LED1, buzzer)
 
#Bathroom uses Green and Green/White (Green/White is Ground)
    turn_on_call_light(bth1, LED2, buzzer)
             
#Off All uses Brown and Brown/White (Brown/White is Ground)
    turn_all_off(off_all, LED1, LED2, buzzer)

