import utime as time
time.sleep_ms(250)

from mqtt_as import MQTTClient, config
import uasyncio as asyncio
import machine
from machine import Pin, PWM, WDT
from neopixel import Neopixel
import network
import gc
import secrets
import uos as os
from buttons import ButtonController
from logging import Logging, Outages
import json
from ota import OTAUpdater

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

magenta = (255,0,255)
orange = (255, 50, 0)
green = (0, 255, 0)
blue = (0, 0, 255)
red = (255, 0, 0)

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


async def down(client):
    while True:
        await client.down.wait()
        client.down.clear()
        print(client.isconnected())
        # o.update_outages(False, 1)
        # client.dprint('Outages: %d  Initial Outages: %d ', o.outages_count, o.init_outages_count)
        await asyncio.sleep(0)

async def up(client):
    while True:
        await client.up.wait()
        client.up.clear()
        client.dprint('%s', wlan.ifconfig())
        print(f"Client Status: {client.isconnected()}")
        await log.post(f'Wifi or Broker is up! Outages: {o.outages_count} Initial Outages: {o.init_outages_count}')
        await asyncio.sleep_ms(0)
        await client.subscribe(f'Room {secrets.ROOM_NUMBER}', 0)

async def network_status():
    mac_reformat = ''
    mac_address = wlan.config('mac')
    for digit in range(6):
        mac_reformat += f'{mac_address[digit]:02X}'
        if digit < 5:
            mac_reformat += ':'
    await client.publish(f'Room {secrets.ROOM_NUMBER} MAC', mac_reformat, qos = 1)
    await client.publish(f'Room {secrets.ROOM_NUMBER} IP', str(wlan.ifconfig()), qos = 1)
    while True:
        # await client.publish(f'Room {secrets.ROOM_NUMBER}', f'Room {secrets.ROOM_NUMBER} Connected! Outages: {o.outages_count} Initial Outages: {o.init_outages_count}', qos=0)
        await asyncio.sleep(300)

async def messages(client):
    async for topic, msg, retained in client.queue:
        decoded_msg = msg.decode('utf-8')
        print('1Topic: "%s" Message: "%s" Retained: "%s"', topic.decode(), decoded_msg, retained)
        

        if decoded_msg.startswith(f'Room {secrets.ROOM_NUMBER} Update'):
            try:
                update_info = json.loads(decoded_msg.split(".", 1)[1])

                for url, filename, action, new_filename in update_info.items():
                    print(url, filename, action, new_filename)
                    ota = OTAUpdater(url, filename)
                    ota.download_and_install_update_if_available(action, new_filename)
                    print('success!')
            except Exception as e:
                print(f"Error updating files: {e}")
        elif decoded_msg.startswith(f'Room {secrets.ROOM_NUMBER} Delete File'):
            try:
                update_info = json.loads(decoded_msg.split(".", 1)[1])
                
                for delete_file in update_info.items():
                    print(delete_file)
                    ota.delete_no_reset(delete_file)
            except Exception as e:
                print(f"Error deleting file: {e}")

        action_mapping = {
            f"Room {secrets.ROOM_NUMBER}-1 has been pressed": lambda: b.handle_room_pressed(0, 0, orange),
            f"Room {secrets.ROOM_NUMBER}-2 has been pressed": lambda: b.handle_room_pressed(1, 1, magenta),
            f"Room {secrets.ROOM_NUMBER}-3 has been pressed": lambda: b.handle_room_pressed(2, 2, blue),
            f"Room {secrets.ROOM_NUMBER}-4 has been pressed": lambda: b.handle_room_pressed(3, 3, green),
            f"Bathroom {secrets.BATHROOM} has been pressed": lambda: b.handle_room_pressed(0, 3, red),
            f"Room {secrets.ROOM_NUMBER} has been answered": lambda: b.handle_answered(),
            f"Room {secrets.ROOM_NUMBER} Pin Status": lambda: b.return_status(),
            f'Room {secrets.ROOM_NUMBER} Reset': lambda: log.handle_reset(),
            f"Room {secrets.ROOM_NUMBER} debug enable": lambda: log.debug_enable(),
            f"Room {secrets.ROOM_NUMBER} debug disable": lambda: log.debug_disable(),
        }
        if decoded_msg in action_mapping:
            await action_mapping[decoded_msg]()  # Execute the corresponding function
            await asyncio.sleep(0)


async def main(client):
    asyncio.create_task(b.button_handler("1", bed1_btn, bed1_prev_state))
    asyncio.create_task(b.button_handler("2", bed2_btn, bed2_prev_state))
    asyncio.create_task(b.button_handler(secrets.BATHROOM, bth_btn, bth_prev_state))
    if secrets.NUMBER_OF_BEDS > 2:
        asyncio.create_task(b.button_handler("3", bed3_btn, bed3_prev_state))
        asyncio.create_task(b.button_handler("4", bed4_btn, bed4_prev_state))
    asyncio.create_task(b.off_handler(off_btn, off_prev_state))
    asyncio.create_task(network_status())
    asyncio.create_task(led_flash())
    asyncio.create_task(b.test_values())
    asyncio.create_task(log.init_async())
    asyncio.create_task(network_status())
    # asyncio.create_task(b.network_status())
    # asyncio.create_task(log.network_status())

    try:
        await client.connect()
    except OSError as e:
        client.dprint("Connection Failed! OSError: %s", e)
        o.update_outages(False, 0)
        client.dprint('Init Outage: %d', o.init_outages_count)
        await watchdog_timer(300) # Shutoff timer when OSError is returned.
        return
    for task in (up, down, messages):
        asyncio.create_task(task(client))
    while True:
        await asyncio.sleep_ms(0)

# Define configuration
config['clean'] = False

# Set up classes. Enable optional debug statements.
MQTTClient.DEBUG = True
client = MQTTClient(config)
log = Logging(client)
o = Outages()
b = ButtonController(log)


try:
    asyncio.run(main(client))
finally:  # Prevent LmacRxBlk:1 errors.
    client.close()
    asyncio.new_event_loop()