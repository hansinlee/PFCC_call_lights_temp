import network
import uasyncio as asyncio
from mqtt_as import MQTTClient, config
from ota import OTAUpdater
import secrets
import json
from buttons import ButtonController
from logging import Logging

log = Logging()
b = ButtonController()
client = MQTTClient(config)
wlan = network.WLAN(network.STA_IF)
wlan_ip = wlan.ifconfig()

class Connections:
    async def down(self, client):
        while True:
            await client.down.wait()
            client.down.clear()
            print(client.isconnected())
            # o.update_outages(False, 1)
            # client.dprint('Outages: %d  Initial Outages: %d ', o.outages_count, o.init_outages_count)
            await asyncio.sleep(0)

    async def up(self, client):
        while True:
            await client.up.wait()
            client.up.clear()
            client.dprint('%s', wlan.ifconfig())
            print(client.isconnected())
            # await log.post(f'Wifi or Broker is up! Outages: {o.outages_count} Initial Outages: {o.init_outages_count}')
            await asyncio.sleep_ms(0)
            await client.subscribe(f'Room {secrets.ROOM_NUMBER}', 0)

    async def network_status(self):
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

    async def messages(self, client):
        async for topic, msg, retained in client.queue:
            decoded_msg = msg.decode('utf-8')
            print('Topic: "%s" Message: "%s" Retained: "%s"', topic.decode(), decoded_msg, retained)
            

            if decoded_msg.startswith(f'Room {secrets.ROOM_NUMBER} Update'):
                try:
                    update_info = json.loads(decoded_msg.split(".", 1)[1])

                    for url, filename in update_info.items():
                        print(url, filename)
                        ota = OTAUpdater(url, filename)
                        ota.download_and_install_update_if_available()
                        print('success!')
                except Exception as e:
                    print(f"Error updating files: {e}")
            
            await b.button_action_mapping(decoded_msg)
            await log.logging_action_mapptin(decoded_msg)