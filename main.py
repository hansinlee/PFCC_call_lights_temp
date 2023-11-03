#two bed with shared bathroom main.py
#neopixel version

from mqtt_as import MQTTClient, config
import uasyncio as asyncio
from machine import Pin, PWM
from neopixel import Neopixel
import utime
import network
from ota import OTAUpdater
import gc
import secrets

gc.collect()

ota_updater = OTAUpdater(secrets.FIRMWARE_URL, "main.py")

pixels = Neopixel(4, 0, 0, "GRB")
 
yellow = (255, 100, 0)
orange = (255, 50, 0)
green = (0, 255, 0)
blue = (0, 0, 255)
red = (255, 0, 0)

pixels.brightness(100)

outages = 0
buzzer = PWM(Pin(22)) #New PCB rev. 3 uses Pin(28)

bed1_btn = Pin(1,Pin.IN,Pin.PULL_DOWN)
bed1_prev_state = bed1_btn.value()
bed2_btn = Pin(14,Pin.IN,Pin.PULL_DOWN)
bed2_prev_state = bed2_btn.value()
bed3_btn = Pin(27,Pin.IN,Pin.PULL_DOWN)
bed3_prev_state = bed3_btn.value()
bed4_btn = Pin(17,Pin.IN,Pin.PULL_DOWN)
bed4_prev_state = bed4_btn.value()
bth_btn = Pin(21,Pin.IN,Pin.PULL_DOWN)
bth_prev_state = bth_btn.value()
off_btn = Pin(4,Pin.IN,Pin.PULL_DOWN)
off_prev_state = off_btn.value()

# Network
wlan = network.WLAN(network.STA_IF)
wlan_ip = wlan.ifconfig()

# MQTT Client
client = MQTTClient(config)

# Button Handlers

async def publish_mqtt_if_connected(status, bed=None):
    if client._has_connected:
        if status == "on":
            if bed == {secrets.BATHROOM}:
                print(f'Bathroom {secrets.BATHROOM}', f'Bathroom {secrets.BATHROOM} has been pressed')
                await client.publish(f'Bathroom {secrets.BATHROOM}', f'Bathroom {secrets.BATHROOM} has been pressed', qos = 1)
            else:
                print(f'{secrets.ROOM_NUMBER}-{bed}', f'Room {secrets.ROOM_NUMBER}-{bed} has been pressed')
                await client.publish(f'{secrets.ROOM_NUMBER}-{bed}', f'Room {secrets.ROOM_NUMBER}-{bed} has been pressed', qos = 1)
        elif status == 'off':
            print(f'{secrets.ROOM_NUMBER}-Off', f'Room {secrets.ROOM_NUMBER} has been answered')
            await client.publish(f'{secrets.ROOM_NUMBER}-Off', f'Room {secrets.ROOM_NUMBER} has been answered', qos = 1)   

def button_pressed(bed):
    if bed == "1":
        pixels.set_pixel_line(0, 0, yellow)
    elif bed == "2":
        pixels.set_pixel_line(1, 1, orange)
    elif bed == "3":
        pixels.set_pixel_line(2, 2, green)
    elif bed == "4":
        pixels.set_pixel_line(3, 3, blue)
    elif bed == {secrets.BATHROOM}:
        pixels.set_pixel_line(0, 3, red)
    pixels.show()
    buzzer.freq(300)
    buzzer.duty_u16(60000)
            

async def button_handler(bed, button, previous_state):
    while True:
        await asyncio.sleep_ms(10)
        if button.value() and not previous_state:
            utime.sleep_ms(250)
            if button.value() and not previous_state:
                previous_state = True
                button_pressed(bed)
                await publish_mqtt_if_connected("on", bed)
        elif not button.value() and previous_state:
            previous_state = False
        await asyncio.sleep_ms(10)

def keep_on_if_still_pressed(bed, previous_state):
    if previous_state == True:
        if bed == "1":
            pixels.set_pixel_line(0, 0, yellow)
        elif bed == "2":
            pixels.set_pixel_line(1, 1, orange)
        elif bed == "3":
            pixels.set_pixel_line(2, 2, green)
        elif bed == "4":
            pixels.set_pixel_line(3, 3, blue)
        elif bed == secrets.BATHROOM:
            pixels.set_pixel_line(0, 3, red)
        pixels.show()
        buzzer.freq(300)
        buzzer.duty_u16(60000)
        print(f"{bed} is held pressed")

def turn_off():
    pixels.clear()
    pixels.show()
    buzzer.duty_u16(0)
    print('lights and buzzer triggered off')

async def off_handler(button, previous_state):
    while True:
        await asyncio.sleep_ms(10)
        if button.value() and not previous_state:
            utime.sleep_ms(250)
            if button.value() and not previous_state:
                previous_state = True
                turn_off()
                keep_on_if_still_pressed("1", bed1_btn.value())
                keep_on_if_still_pressed("2", bed2_btn.value())
                keep_on_if_still_pressed(secrets.BATHROOM, bth_btn.value())
                if secrets.NUMBER_OF_BEDS > 2:
                    keep_on_if_still_pressed("3", bed3_btn.value())
                    keep_on_if_still_pressed("4", bed4_btn.value())
                await publish_mqtt_if_connected("off")
#                 if client._has_connected:
#                     await client.publish(f'{secrets.ROOM_NUMBER}-Off', f'Room {secrets.ROOM_NUMBER} has been answered', qos = 1)
        elif not button.value() and previous_state:
            previous_state = False
        await asyncio.sleep_ms(10)

async def messages(client):
    async for topic, msg, retained in client.queue:
        print(f'Topic: "{topic.decode()}" Message: "{msg.decode()}" Retained: {retained}')
        msg = msg.decode('utf-8')
        print(msg)
        if msg == f"Room {secrets.ROOM_NUMBER}-1 has been pressed":
            pixels.set_pixel_line(0, 0, yellow)
            pixels.show()
            buzzer.freq(300)
            buzzer.duty_u16(60000)
        if msg == f"Room {secrets.ROOM_NUMBER}-2 has been pressed":
            pixels.set_pixel_line(1, 1, orange)
            pixels.show()
            buzzer.freq(300)
            buzzer.duty_u16(60000)
        if msg == f"Room {secrets.ROOM_NUMBER}-3 has been pressed":
            pixels.set_pixel_line(2, 2, orange)
            pixels.show()
            buzzer.freq(300)
            buzzer.duty_u16(60000)
        if msg == f"Room {secrets.ROOM_NUMBER}-4 has been pressed":
            pixels.set_pixel_line(3, 3, orange)
            pixels.show()
            buzzer.freq(300)
            buzzer.duty_u16(60000)
        if msg == f"Bathroom {secrets.BATHROOM} has been pressed":
            pixels.set_pixel_line(0, 3, red)
            pixels.show()
            buzzer.freq(300)
            buzzer.duty_u16(60000)
        if msg == f'Room {secrets.ROOM_NUMBER} Reset':
            machine.reset()
        if msg == f'Room {secrets.ROOM_NUMBER} Update':
            ota_updater.update_and_install()
            if client._has_connected:
                await client.publish(f'Room {secrets.ROOM_NUMBER}', f'Room {secrets.ROOM_NUMBER} has been updated! Please reset device.')
        if msg == f"Room {secrets.ROOM_NUMBER} has been answered":
            pixels.clear()
            pixels.show()
            buzzer.duty_u16(0)
            await asyncio.sleep_ms(10)
           
async def down(client):
    global outages
    while True:
        await client.down.wait()
        client.down.clear()
        outages += 1

async def up(client):
    while True:
        await client.up.wait()
        client.up.clear()
        print(wlan.ifconfig())
        await asyncio.sleep_ms(2)
        await client.subscribe(f'Room {secrets.ROOM_NUMBER}', 1)


async def room_status():
    mac_reformat = ''
    mac_address = wlan.config('mac')
    for digit in range(6):
        mac_reformat += f'{mac_address[digit]:02X}'
        if digit < 5:
            mac_reformat += ':'
    await client.publish(f'Room {secrets.ROOM_NUMBER} MAC', mac_reformat, qos = 1)

    while True:
        await client.publish(f'Room {secrets.ROOM_NUMBER} IP', str(wlan.ifconfig()), qos = 1)
    await asyncio.sleep(480)
       
async def main(client):
    asyncio.create_task(button_handler("1", bed1_btn, bed1_prev_state, yellow))

    asyncio.create_task(button_handler("2", bed2_btn, bed2_prev_state, orange))
       
    asyncio.create_task(button_handler(secrets.BATHROOM, bth_btn, bth_prev_state, red))

    if secrets.NUMBER_OF_BEDS > 2:
        asyncio.create_task(button_handler("3", bed3_btn, bed3_prev_state, green))
       
        asyncio.create_task(button_handler("4", bed4_btn, bed4_prev_state, blue))
   
    asyncio.create_task(off_handler(off_btn, off_prev_state))

    asyncio.create_task(room_status())
   
    try:
        await client.connect()
    except OSError:
        print('Connection failed.')
   
    for task in (up, down, messages):
        asyncio.create_task(task(client))
       
    while True:
        await asyncio.sleep_ms(10)

# Set up client. Enable optional debug statements.

client = MQTTClient(config)

try:
    asyncio.run(main(client))
finally:  # Prevent LmacRxBlk:1 errors.
    client.close()
    asyncio.new_event_loop()

