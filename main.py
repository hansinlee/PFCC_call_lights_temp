from mqtt_as import MQTTClient, config
import uasyncio as asyncio
from machine import Pin, PWM, WDT
from neopixel import Neopixel
import utime
import network
from ota import OTAUpdater
import gc
import secrets


gc.collect()

ota_updater = OTAUpdater(secrets.FIRMWARE_URL, "main.py")
pixels = Neopixel(4, 0, 27, "GRB")

magenta = (255,0,255)
orange = (255, 50, 0)
green = (0, 255, 0)
blue = (0, 0, 255)
red = (255, 0, 0)

pixels.brightness(100)

outages = 1
buzzer = PWM(Pin(28))

bed1_btn = Pin(20,Pin.IN,Pin.PULL_UP)
bed1_prev_state = bed1_btn.value()
bed2_btn = Pin(21,Pin.IN,Pin.PULL_UP)
bed2_prev_state = bed2_btn.value()
bed3_btn = Pin(17,Pin.IN,Pin.PULL_UP)
bed3_prev_state = bed3_btn.value()
bed4_btn = Pin(16,Pin.IN,Pin.PULL_UP)
bed4_prev_state = bed4_btn.value()
bth_btn = Pin(19,Pin.IN,Pin.PULL_UP)
bth_prev_state = bth_btn.value()
off_btn = Pin(18,Pin.IN,Pin.PULL_UP)
off_prev_state = off_btn.value()

# Network
wlan = network.WLAN(network.STA_IF)
wlan_ip = wlan.ifconfig()

# MQTT Client
client = MQTTClient(config)

buzz_freq = 250
buzz_duty = 3000

onboard_led = Pin('LED', Pin.OUT)

async def led_flash():
    while True:
        onboard_led.toggle()
        await asyncio.sleep(1)

async def publish_mqtt_if_connected(status, bed=None):
    global outages
    await asyncio.sleep(0)
    if outages == 0:
        await asyncio.sleep(0)
        if status == "on":
            if bed == secrets.BATHROOM:
                print(f'Bathroom {secrets.BATHROOM}', f'Bathroom {secrets.BATHROOM} has been pressed')
                await asyncio.sleep(0)
                await client.publish(f'Bathroom {secrets.BATHROOM}', f'Bathroom {secrets.BATHROOM} has been pressed', qos = 0)
                await asyncio.sleep(0)
            else:
                print(f'{secrets.ROOM_NUMBER}-{bed}', f'Room {secrets.ROOM_NUMBER}-{bed} has been pressed')
                await asyncio.sleep(0)
                await client.publish(f'{secrets.ROOM_NUMBER}-{bed}', f'Room {secrets.ROOM_NUMBER}-{bed} has been pressed', qos = 0)
                await asyncio.sleep(0)
        elif status == 'off':
            print(f'{secrets.ROOM_NUMBER}-Off', f'Room {secrets.ROOM_NUMBER} has been answered')
            await asyncio.sleep(0)
            await client.publish(f'{secrets.ROOM_NUMBER}-Off', f'Room {secrets.ROOM_NUMBER} has been answered', qos = 0)
            await asyncio.sleep(0)
    else:
        await asyncio.sleep(0)

async def button_pressed(bed):
    await asyncio.sleep(0)
    if bed == "1":
        pixels.set_pixel_line(0, 0, blue)
    elif bed == "2":
        pixels.set_pixel_line(1, 1, orange)
    elif bed == "3":
        pixels.set_pixel_line(2, 2, green)
    elif bed == "4":
        pixels.set_pixel_line(3, 3, magenta)
    elif bed == secrets.BATHROOM:
        pixels.set_pixel_line(0, 3, red)
    pixels.show()
    buzzer.freq(buzz_freq)
    buzzer.duty_u16(buzz_duty)
    await asyncio.sleep(0)
            
async def button_handler(bed, button, previous_state):
    while True:
        await asyncio.sleep(0)
        if not button.value() and not previous_state:
            utime.sleep_ms(250)
            if not button.value() and not previous_state:
                previous_state = True
                await button_pressed(bed)
                if client._has_connected:
                    await asyncio.sleep(0)
                    await publish_mqtt_if_connected("on", bed)
                    await asyncio.sleep(0)
        elif button.value() and previous_state:
            previous_state = False
            await asyncio.sleep(0)
        await asyncio.sleep_ms(0)

async def keep_on_if_still_pressed(bed, previous_state):
    if previous_state == False:
        if bed == "1":
            pixels.set_pixel_line(0, 0, blue)
        elif bed == "2":
            pixels.set_pixel_line(1, 1, orange)
        elif bed == "3":
            pixels.set_pixel_line(2, 2, green)
        elif bed == "4":
            pixels.set_pixel_line(3, 3, magenta)
        elif bed == secrets.BATHROOM:
            pixels.set_pixel_line(0, 3, red)
        pixels.show()
        # if not client._has_connected:
        buzzer.freq(buzz_freq)
        buzzer.duty_u16(buzz_duty)
        print(f"{bed} is held pressed")

async def turn_off():
    pixels.clear()
    pixels.show()
    buzzer.duty_u16(0)
    print('lights and buzzer triggered off')
    await asyncio.sleep(0)

async def off_handler(button, previous_state):
    global outages
    while True:
        await asyncio.sleep(0)
        if not button.value() and not previous_state:
            utime.sleep_ms(250)
            if not button.value() and not previous_state:
                previous_state = True
                await turn_off()
                await keep_on_if_still_pressed("1", bed1_btn.value())
                await keep_on_if_still_pressed("2", bed2_btn.value())
                await keep_on_if_still_pressed(secrets.BATHROOM, bth_btn.value())
                if secrets.NUMBER_OF_BEDS > 2:
                    await keep_on_if_still_pressed("3", bed3_btn.value())
                    await keep_on_if_still_pressed("4", bed4_btn.value())
                if outages == 0:
                    await asyncio.sleep(0)
                    await publish_mqtt_if_connected("off")
                    await asyncio.sleep(0)
        elif button.value() and previous_state:
            previous_state = False
        await asyncio.sleep_ms(0)

async def messages(client):
    global outages
    async for topic, msg, retained in client.queue:
        print(f'Topic: "{topic.decode()}" Message: "{msg.decode()}" Retained: {retained}')
        msg = msg.decode('utf-8')
        print(msg)
        if msg == f"Room {secrets.ROOM_NUMBER}-1 has been pressed":
            pixels.set_pixel_line(0, 0, magenta)
            pixels.show()
            buzzer.freq(buzz_freq)
            buzzer.duty_u16(buzz_duty)
        if msg == f"Room {secrets.ROOM_NUMBER}-2 has been pressed":
            pixels.set_pixel_line(1, 1, orange)
            pixels.show()
            buzzer.freq(buzz_freq)
            buzzer.duty_u16(buzz_duty)
        if msg == f"Room {secrets.ROOM_NUMBER}-3 has been pressed":
            pixels.set_pixel_line(2, 2, orange)
            pixels.show()
            buzzer.freq(buzz_freq)
            buzzer.duty_u16(buzz_duty)
        if msg == f"Room {secrets.ROOM_NUMBER}-4 has been pressed":
            pixels.set_pixel_line(3, 3, orange)
            pixels.show()
            buzzer.freq(buzz_freq)
            buzzer.duty_u16(buzz_duty)
        if msg == f"Bathroom {secrets.BATHROOM} has been pressed":
            pixels.set_pixel_line(0, 3, red)
            pixels.show()
            buzzer.freq(buzz_freq)
            buzzer.duty_u16(buzz_duty)
        if msg == f'Room {secrets.ROOM_NUMBER} Reset':
            machine.reset()
        if msg == f'Room {secrets.ROOM_NUMBER} Update':
            ota_updater.download_and_install_update_if_available()
            if outages == 0:
                await client.publish(f'Room {secrets.ROOM_NUMBER}', f'Room {secrets.ROOM_NUMBER} has been updated! Please reset device.')
        if msg == f"Room {secrets.ROOM_NUMBER} has been answered":
            pixels.clear()
            pixels.show()
            buzzer.duty_u16(0)
            await asyncio.sleep_ms(0)

async def down(client):
    global outages
    while True:
        await client.down.wait()
        client.down.clear()
        print('Wifi or Broker is down')
        outages = 1
        await asyncio.sleep(0)


async def up(client):
    global outages
    while True:
        await client.up.wait()
        client.up.clear()
        print(wlan.ifconfig())
        outages = 0
        await asyncio.sleep_ms(2)
        await client.subscribe(f'Room {secrets.ROOM_NUMBER}', 0)

async def room_status():
    mac_reformat = ''
    mac_address = wlan.config('mac')
    for digit in range(6):
        mac_reformat += f'{mac_address[digit]:02X}'
        if digit < 5:
            mac_reformat += ':'
    await client.publish(f'Room {secrets.ROOM_NUMBER} MAC', mac_reformat, qos = 0)

    while True: 
        await client.publish(f'Room {secrets.ROOM_NUMBER} IP', str(wlan.ifconfig()), qos = 0)
        await asyncio.sleep(6000)

async def watchdog_timer(timeout):
    while True:
        await asyncio.sleep(timeout)
        machine.WDT(timeout=8388)

async def test():
    asyncio.create_task(button_handler("1", bed1_btn, bed1_prev_state))
    asyncio.create_task(button_handler("2", bed2_btn, bed2_prev_state))
    asyncio.create_task(button_handler(secrets.BATHROOM, bth_btn, bth_prev_state))
    if secrets.NUMBER_OF_BEDS > 2:
        asyncio.create_task(button_handler("3", bed3_btn, bed3_prev_state))
        asyncio.create_task(button_handler("4", bed4_btn, bed4_prev_state))
    asyncio.create_task(off_handler(off_btn, off_prev_state))
    asyncio.create_task(room_status())
    asyncio.create_task(led_flash())

async def wifi_disconnect():
    x = input()
    if x = 
    await asyncio.sleep(0)
    
async def main(client):
    await test()
    try:
        await client.connect()
    except OSError as e:
        print("Connection Failed! OSError:", e)
        await watchdog_timer(60)
        return
    for task in (up, down, messages):
        asyncio.create_task(task(client))
    n = 0
    while True:
        await asyncio.sleep(5)
        print('publish', n)
        # # If WiFi is down the following will pause for the duration.
        # await client.publish(secrets.TOPIC, '{} repubs: {} outages: {}'.format(n, client.REPUB_COUNT, outages), qos = 1)
        # n += 1
        await asyncio.sleep_ms(0)

# Set up client. Enable optional debug statements.
MQTTClient.DEBUG = True
client = MQTTClient(config)

try:
    asyncio.run(main(client))
finally:  # Prevent LmacRxBlk:1 errors.
    client.close()
    asyncio.new_event_loop()