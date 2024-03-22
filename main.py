import utime as time
time.sleep_ms(2500)

from mqtt_as import MQTTClient, config
import uasyncio as asyncio
import machine
from machine import Pin, PWM, WDT
from neopixel import Neopixel
import network
import gc
import secrets
import uos as os
# from debug import MemoryResetCount, Outages
from buttons import ButtonController
from logging import Logging
from ota import OTAUpdater
import json
from connections import Connections

gc.collect()
bed1_btn = Pin(20,Pin.IN,Pin.PULL_UP)
bed1_prev_state = bed1_btn.value()
bed2_btn = Pin(18,Pin.IN,Pin.PULL_UP) #PCB layout reverses bed2 & off buttons
bed2_prev_state = bed2_btn.value()
bed3_btn = Pin(17,Pin.IN,Pin.PULL_UP)
bed3_prev_state = bed3_btn.value()
bed4_btn = Pin(16,Pin.IN,Pin.PULL_UP)
bed4_prev_state = bed4_btn.value()
bth_btn = Pin(19,Pin.IN,Pin.PULL_UP)
bth_prev_state = bth_btn.value()
off_btn = Pin(21,Pin.IN,Pin.PULL_UP) #PCB layout reverses bed2 & off buttons
off_prev_state = off_btn.value()
onboard_led = Pin('LED', Pin.OUT)

# Network
wlan = network.WLAN(network.STA_IF)
wlan_ip = wlan.ifconfig()

async def led_flash():
    while True:
        onboard_led.toggle()
        await asyncio.sleep(.15)

async def watchdog_timer(timeout):
    while True:
        await asyncio.sleep(timeout)
        machine.WDT(timeout=8388)
        await asyncio.sleep(0)


async def main(client):
    asyncio.create_task(b.button_handler("1", bed1_btn, bed1_prev_state))
    asyncio.create_task(b.button_handler("2", bed2_btn, bed2_prev_state))
    asyncio.create_task(b.button_handler(secrets.BATHROOM, bth_btn, bth_prev_state))
    if secrets.NUMBER_OF_BEDS > 2:
        asyncio.create_task(b.button_handler("3", bed3_btn, bed3_prev_state))
        asyncio.create_task(b.button_handler("4", bed4_btn, bed4_prev_state))
    asyncio.create_task(b.off_handler(off_btn, off_prev_state))
    asyncio.create_task(c.network_status())
    asyncio.create_task(led_flash())
    asyncio.create_task(b.test_values())
    try:
        await client.connect()
    except OSError as e:
        client.dprint("Connection Failed! OSError: %s", e)
        # o.update_outages(False, 0)
        # log.dprint('1Init Outage: %d', o.init_outages_count)
        await watchdog_timer(2) # Shutoff timer when OSError is returned.
        return
    for task in (c.up, c.down, c.messages):
        asyncio.create_task(task(client))
    while True:
        await asyncio.sleep_ms(0)

# Define configuration
config['clean'] = False

# Set up classes. Enable optional debug statements.
MQTTClient.DEBUG = True
client = MQTTClient(config)
b = ButtonController()
c = Connections()
log = Logging()

try:
    asyncio.run(main(client))
    print('Main Running')
finally:  # Prevent LmacRxBlk:1 errors.
    client.close()
    asyncio.new_event_loop()