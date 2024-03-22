import uasyncio as asyncio
from mqtt_as import MQTTClient, config
import secrets
import uos as os
import gc
import json
import machine

client = MQTTClient(config)

class Logging:

    pending_post = []

    def __init__(self):
        self.status = 'off'

    async def init_async(self):
        await asyncio.sleep(5)  # Delay for 5 seconds
        self.status = await self.read_debug_status()

    def debugger(self, DEBUG_status):
        if DEBUG_status in ("on", "off"):
            self.status = DEBUG_status
            return True
        else:
            return False

    async def read_debug_status(self):
        file_path = 'debug.txt'
        try:
            with open(file_path, 'r') as file:
                content = file.read().strip()
                if content == 'debug = on':
                    return 'on'
                elif content == 'debug = off':
                    return 'off'
                else:
                    client.dprint('Invalid content in %s. Defaulting to debug mode off.', file_path)
                    return 'off'
        except OSError as e:
            client.dprint('Error reading %s: %s', file_path, e)
            await asyncio.sleep(0)
            return 'off'
            
    async def post(self, comment=""):
        async def send(comment):
            self.pending_post.append(comment)
            client.dprint('Connection Status: %s, Debug Status: %s', client.isconnected(), self.status)
            client.dprint('2RAM free %d alloc %d', gc.mem_free(), gc.mem_alloc())
            try:
                if client.isconnected() == True and self.status == 'on':
                    await self.send_logs()  # Send logs if client is connected
                elif client.isconnected() == False and self.status == 'on':
                    print('Client is not connected but logs are on')
                    try:
                        with open('offline_logs.txt', 'a') as file:
                            file.write(comment + '\n')  # Write logs to offline_logs.txt
                    except OSError as e:
                        client.dprint('Error writing to offline_logs.txt: %s', e)
            except OSError as e:
                print('Error writing to offline_logs.txt: %s', e)

        asyncio.create_task(send(comment))

    async def send_logs(self):
        logs = '\n'.join(self.pending_post)
        await client.publish(f'Room {secrets.ROOM_NUMBER} Logs', logs, qos=0)
        client.dprint('Logs sent successfully')
        self.pending_post.clear()

    async def send_offline_logs(self):
        if os.path.exists('offline_logs.txt'):
            try:
                with open('offline_logs.txt', 'r') as file:
                    logs = file.read()
                await client.publish(f'Room {secrets.ROOM_NUMBER} Logs', logs, qos=0)
                client.dprint('Offline logs sent successfully')
                os.remove('offline_logs.txt')  # Delete offline logs file
            except OSError as e:
                client.dprint('Error sending offline logs: %s', e)

    def memory_reset_count(self):   # This will check to see if file exists and reads the count.
                                    # If not, it is passed to update_ram_count to create the file. That file then keeps the count of how many times RAM was reset.
        if 'ram_status.json' in os.listdir():
            with open('ram_status.json') as f:
                data = json.load(f)
                self.ram_clear_count = data.get('ram_reset_count', 0)
            print(f'Cleared RAM x{self.ram_clear_count}')
        
        else:
            self.ram_clear_count = 0
            self.update_ram_count(0)
    
    def update_ram_count(self, increment=1):
        self.ram_clear_count += increment
        with open('ram_status.json', 'w') as f:
            json.dump({'ram_reset_count': self.ram_clear_count}, f)

    def outages_file(self): # This is basically the same as memory_reset_count, but deals with two types of outages.

        if 'outages.json' in os.listdir(): # Checks to see if file is there, if so, reads the count.
            with open('outages.json') as f:
                data = json.load(f)
                self.outages_count = data.get('outages_count', 0)
                self.init_outages_count = data.get('init_outages_count', 0)  # Use .get() to provide a default value
            print(f'Init Outages: {self.init_outages_count} Outages: {self.outages_count}')

        else: # If not, set values to 0 and passes to update_outage to create file.
            self.outages_count = 0
            self.init_outages_count = 0
            self.update_outages(True, 0) # Passes the type of outage
            self.update_outages(True, 1)
    
    def update_outages(self, init, outage_type, increment=1):
        if init: # If a init value was passed, then set outages to 0. ## Init outage is the first outage before wifi connect. (Could mean device has restarted and WIFI and/or MQTT broker isn't reachable)
            self.outages_count = 0
            self.init_outages_count = 0
        elif outage_type == 0: # If type 0 (Init) then +1 to count.
            self.init_outages_count += increment
        elif outage_type == 1: # Vice versa  ## This second type of outage is if WIFI/MQTT was established and was disconnected for some reason. (Typical type of outage)
            self.outages_count += increment
            pass

        with open('outages.json', 'w') as f: # Creates file with 'w' or updates count
            json.dump({'outages_count': self.outages_count, 'init_outages_count': self.init_outages_count}, f)


    async def logging_action_mapping(self, decoded_msg):
        print(decoded_msg)
        action_mapping = {
            f'Room {secrets.ROOM_NUMBER} Reset': lambda: self.handle_reset(),
            f"Room {secrets.ROOM_NUMBER} Pin Status": lambda: self.return_status(),
            f"Room {secrets.ROOM_NUMBER} debug enable": lambda: self.debug_enable(),
            f"Room {secrets.ROOM_NUMBER} debug disable": lambda: self.debug_disable(),
        }
        if decoded_msg in action_mapping:
            await action_mapping[decoded_msg]()  # Execute the corresponding function
            await asyncio.sleep(0)

    async def handle_reset(self):
        machine.reset()

    async def return_status(self):
        status_bytes = str(b.status).encode('utf-8')
        await client.publish(f'{secrets.ROOM_NUMBER} off status', status_bytes, qos=1)
        await asyncio.sleep(0)

    async def debug_enable(self): 
        self.debugger('on')
        file_path = 'debug.txt'
        try:
            with open(file_path, 'w') as file:
                file.write('debug = on\n')
            client.dprint('Successfully updated %s', file_path)
        except OSError as e:
            client.dprint('Error updating %s: %s', file_path, e)

    async def debug_disable(self): 
        self.debugger('off')
        file_path = 'debug.txt'
        try:
            with open(file_path, 'w') as file:
                file.write('debug = off\n')
            client.dprint('Successfully updated %s', file_path)
        except OSError as e:
            client.dprint('Error updating %s: %s', file_path, e)