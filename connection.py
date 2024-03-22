import uasyncio as asyncio
import secrets
import network
from mqtt_as import MQTTClient, config

wlan = network.WLAN(network.STA_IF)
wlan_ip = wlan.ifconfig()
client = MQTTClient(config)

class Connection:
    def __init__(self):
        self.status = 'down'

    def dprint(self, msg, *args):
        if self.status == 'on':
            print(msg % args)

    def main_conn_status(self, current_status):
        if current_status in ('up', 'down'):
            self.status = current_status
            return True
        else:
            return False
    def up_status(self, current_status):
        return current_status

    async def down(self, client):
        while True:
            await client.down.wait()
            client.down.clear()
            print(client.isconnected())
            # await log.post(f'Outages: {o.outages_count} Initial Outages: {o.init_outages_count}')
            self.main_conn_status('down')
            # o.update_outages(False, 1)
            # self.dprint('Outages: %d  Initial Outages: %d ', o.outages_count, o.init_outages_count)
            self.dprint('%s', self.status)
            await asyncio.sleep(0)

    async def up(self, client):
        while True:
            await client.up.wait()
            client.up.clear()
            self.dprint('%s', wlan.ifconfig())
            self.main_conn_status('up')
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
            
