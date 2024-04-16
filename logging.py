import uasyncio as asyncio
import secrets
import uos as os
import gc
import json
import machine

async def logging_action_mapping(decoded_msg):
    print(decoded_msg)
    action_mapping = {

    }
    if decoded_msg in action_mapping:
        await action_mapping[decoded_msg]()  # Execute the corresponding function
        await asyncio.sleep(0)

class Logging:

    pending_post = []
    
    def __init__(self, client):
        self.status = 'off'
        self.client = client
        self.ram_status = RamStatus()
        
    async def init_async(self):
        await self.read_debug_status()

    def dprint(self, msg, *args):
        if self.status == 'on':
            print(msg % args)

    def debugger(self, DEBUG_status):
        if DEBUG_status in ("on", "off"):
            self.status = DEBUG_status
            print(self.status)
            return True
        else:
            return False

    async def read_debug_status(self):
        if 'debug.json' in os.listdir():
            with open('debug.json') as f:
                self.status = json.load(f)['debug_mode']
            self.dprint('Debug Mode: %s', self.status)
            self.debugger('on')
            await asyncio.sleep(0)
        else:
            await self.debug_disable()

    async def debug_enable(self): 
        self.debugger('on')
        file_path = 'debug.json'
        try:
            with open(file_path, 'w') as f:
                json.dump({'debug_mode': 'on'}, f)
            self.dprint('Successfully updated %s', file_path)
            await asyncio.sleep(0)
        except OSError as e:
            self.dprint('Error updating %s: %s', file_path, e)

    async def debug_disable(self): 
        await asyncio.sleep(0)
        self.debugger('off')
        file_path = 'debug.json'
        try:
            with open(file_path, 'w') as f:
                json.dump({'debug_mode': 'off'}, f)
            self.dprint('Successfully updated %s', file_path)
        except OSError as e:
            self.dprint('Error updating %s: %s', file_path, e)
    
    async def post(self, comment=""):
        async def send(comment):
            self.pending_post.append(comment)
            self.dprint("Debug Mode: %s Client Status: %s", self.status, self.client.isconnected())
            self.dprint('5Connection Status: %s, Debug Status: %s', self.client.isconnected(), self.status)
            self.dprint('5RAM free %d alloc %d', gc.mem_free(), gc.mem_alloc())
            try:
                if self.client.isconnected() == True and self.status == True:
                    await self.send_logs()
                    print('logs are being sent.')  # Send logs if client is connected
                elif self.client.isconnected() == False and self.status == True:
                    print('Client is not connected but logs are on')
                    try:
                        with open('offline_logs.txt', 'a') as file:
                            file.write(comment + '\n')  # Write logs to offline_logs.txt
                    except OSError as e:
                        self.dprint('Error writing to offline_logs.txt: %s', e)
            except OSError as e:
                print('Error writing to offline_logs.txt: %s', e)

        asyncio.create_task(send(comment))

    async def send_logs(self):
        logs = '\n'.join(self.pending_post)
        await self.client.publish(f'Room {secrets.ROOM_NUMBER} Logs', logs, qos=0)
        self.dprint('Logs sent successfully')
        self.pending_post.clear()

    async def send_offline_logs(self):
        if os.path.exists('offline_logs.txt'):
            try:
                with open('offline_logs.txt', 'r') as file:
                    logs = file.read()
                await self.client.publish(f'Room {secrets.ROOM_NUMBER} Logs', logs, qos=0)
                self.dprint('Offline logs sent successfully')
                os.remove('offline_logs.txt')  # Delete offline logs file
            except OSError as e:
                self.dprint('Error sending offline logs: %s', e)

    async def handle_reset(self):
        machine.reset()

class Outages:

    def __init__(self):
        self.outages_count = 0
        self.init_outages_count = 0

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


class RamStatus:
    def __init__(self):
        self.status = 0

    def ram_count_file(self):   # This will check to see if file exists and reads the count.
                                # If not, it is passed to update_ram_count to create the file. That file then keeps the count of how many times RAM was reset.
        if 'ram_status.json' in os.listdir():
            with open('ram_status.json') as f:
                data = json.load(f)
                self.status = data.get('ram_reset_count', 0)
                print(f'Cleared RAM x{self.ram_clear_count}')
        else:
            self.ram_clear_count = 0
            self.update_ram_count(0)

    def update_ram_count(self, increment=1):
        self.status += increment
        with open('ram_status.json', 'w') as f:
            json.dump({'ram_reset_count': self.status}, f)

