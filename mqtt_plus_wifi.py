import machine
from machine import Pin
from umqtt.simple import MQTTClient
import rp2
import network
import ubinascii
import urequests as requests
import time
import socket
rp2.country('US')

# Connect to network
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

mac = ubinascii.hexlify(network.WLAN().config('mac'),':').decode()
print('mac = ' + mac)

# Fill in your network name (ssid) and password here:
ssid = 'SSID'
password = 'PASSWORD'
wlan.connect(ssid, password)

# Wait for connection with 10 second timeout
timeout = 10
while timeout > 0:
    if wlan.status() < 0 or wlan.status() >= 3:
        break
    timeout -= 1
    print('Waiting for connection...')
    time.sleep(1)
    
# Define blinking function for onboard LED to indicate error codes    
def blink_onboard_led(num_blinks):
    led = machine.Pin('LED', machine.Pin.OUT)
    for i in range(num_blinks):
        led.on()
        time.sleep(.2)
        led.off()
        time.sleep(.2)
        
wlan_status = wlan.status()
blink_onboard_led(wlan_status)

if wlan_status != 3:
    raise RuntimeError('Wi-Fi connection failed')
else:
    print('Connected')
    status = wlan.ifconfig()
    print('ip = ' + status[0])

mqtt_server = '10.0.0.4'
client_id = ubinascii.hexlify(machine.unique_id())
topic_sub = b'Sub'
topic_pub = b'Pub'
topic_msg = b'Test Msg'

def mqtt_connect():
    client = MQTTClient(client_id, mqtt_server)
    client.connect()
    print ('Connected to %s MQTT Broker'%(mqtt_server))
    return client

def reconnect():
    print('Failed to connect to the MQTT Broker. Reconnecting...')
    time.sleep(5)
    machine.reset()
    
try:
    client = mqtt_connect()
except OSError as e:
    reconnect()
    
client.publish(topic_pub, topic_msg)