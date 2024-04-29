import utime as time
time.sleep_ms(250)

from mqtt_as import MQTTClient, config
import uasyncio as asyncio
import machine
from neopixel import Neopixel
import network
import gc
import secrets
from buttons import ButtonController
from logging import Logging, Outages, RamStatus
import json
from ota import OTAUpdater
from config import (
    magenta, orange, green, blue, red,
    bed1_btn, bed1_prev_state,
    bed2_btn, bed2_prev_state,
    bed3_btn, bed3_prev_state,
    bed4_btn, bed4_prev_state,
    bth_btn, bth_prev_state,
    off_btn, off_prev_state,
    onboard_led
)

gc.collect()

# Network
wlan = network.WLAN(network.STA_IF)
wlan_ip = wlan.ifconfig()

async def led_flash():
    while True:
        onboard_led.toggle()
        await asyncio.sleep(.15)

def custom_print(*args, **kwargs):
    # Custom print function to redirect output to logging
    msg = ' '.join(map(str, args))
    log.custom_print(msg)

async def watchdog_timer(timeout):
    while True:
        await asyncio.sleep(timeout)
        machine.WDT(timeout=8388)
        await asyncio.sleep(0)

async def down(client):
    while True:
        await client.down.wait()
        client.down.clear()
        client.dprint("client %s", client.isconnected())
        o.update_outages(False, 1)
        client.dprint('Outages: %d  Initial Outages: %d ', o.outages_count, o.init_outages_count)
        await asyncio.sleep(0)

async def up(client):
    while True:
        await client.up.wait()
        client.up.clear()
        client.dprint('%s', wlan.ifconfig())
        client.dprint(f"Client Status: {client.isconnected()}")
        await log.post(f'Wifi or Broker is up! Outages: {o.outages_count} Initial Outages: {o.init_outages_count}\n\n\n\n')
        await log.send_offline_logs()
        await client.publish(f"Room {secrets.ROOM_NUMBER} Outages", f"Room {secrets.ROOM_NUMBER} outage: {o.outages_count}, Initial Outages: {o.init_outages_count}", qos = 1)
        await asyncio.sleep_ms(0)
        await client.subscribe(f'Room {secrets.ROOM_NUMBER}', 0)

async def network_status():
    mac_reformat = ''
    mac_address = wlan.config('mac')
    await o.count_brown_out()
    print(o.brown_out_count)
    for digit in range(6):
        mac_reformat += f'{mac_address[digit]:02X}'
        if digit < 5:
            mac_reformat += ':'
    await client.publish(f'Room {secrets.ROOM_NUMBER} MAC', mac_reformat, qos = 1)
    await client.publish(f'Room {secrets.ROOM_NUMBER} IP', str(wlan.ifconfig()), qos = 1)
    await client.publish(f'Room {secrets.ROOM_NUMBER} Logs', f'Room {secrets.ROOM_NUMBER}, Power Cycle Count: {o.brown_out_count}\n\n\n', qos = 1)
    while True:
        await client.publish(f'Room {secrets.ROOM_NUMBER}', f'Room {secrets.ROOM_NUMBER} Connected! Outages: {o.outages_count} Initial Outages: {o.init_outages_count} Power Cycles: {o.brown_out_count}', qos=1)
        await asyncio.sleep(300)

async def messages(client):
    async for topic, msg, retained in client.queue:
        decoded_msg = msg.decode('utf-8')
        print('Topic: "%s" Message: "%s" Retained: "%s"', topic.decode(), decoded_msg, retained)
        
        if decoded_msg.startswith(f'Room Update'):
            try:
                update_info = json.loads(decoded_msg.split("|", 1)[1])
                for url, info in update_info.items():
                    filename = info.get('filename')
                    if client.isconnected():
                        OTAUpdater(url, filename).download_and_install_update_if_available()
                        await client.publish(f'Room {secrets.ROOM_NUMBER}', f'Room {secrets.ROOM_NUMBER} has been updated! Please reset device.')
            except Exception as e:
                print(f"Error updating files: {e}")

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
            f"Room {secrets.ROOM_NUMBER} button status": lambda: b.return_status(),
            f"Room {secrets.ROOM_NUMBER} outages status": lambda: o.outages_return(),
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
    asyncio.create_task(log.read_debug_status())

    try:
        await client.connect()
    except OSError as e:
        print("Connection Failed! OSError: %s", e)
        o.update_outages(False, 0)
        print('Init Outage: %d', o.init_outages_count)
        await watchdog_timer(300) # Shutoff timer when OSError is returned.
        return
    for task in (up, down, messages):
        asyncio.create_task(task(client))
    while True:
        await asyncio.sleep_ms(0)

# Define configuration
config['clean'] = False

# Set up classes. Enable optional debug statements.
client = MQTTClient(config)
log = Logging(client)
o = Outages(log)
r = RamStatus()
b = ButtonController(log, r)

try:
    asyncio.run(main(client))
finally:  # Prevent LmacRxBlk:1 errors.
    client.close()
    asyncio.new_event_loop()
