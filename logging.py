import uasyncio as asyncio
import secrets
import uos as os
import gc
import json
import machine
import ntptime
import time

gc.collect()

class Logging:

    logs_pending_post = []
    off_pending_post = []
    
    def __init__(self, client):
        self.status = 'off'
        self.client = client
        self.count = 0

        self.timezone_offset_hours = -6
        self.current_time = time.localtime(time.mktime(time.localtime()) + self.timezone_offset_hours*3600)
        self.formatted_time = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d} {:s}{:02d}{:02d}".format(
            self.current_time[0],  # year
            self.current_time[1],  # month
            self.current_time[2],  # day
            self.current_time[3],  # hour
            self.current_time[4],  # minute
            self.current_time[5],  # second
            '+' if self.timezone_offset_hours >= 0 else '-',  # sign of the timezone offset
            abs(self.timezone_offset_hours),  # absolute value of the timezone offset
            0  # minutes part of the timezone offset (always 00 in this case)
        )

    def status_return(self):
        if self.status == 'on':
            return True
        if self.status == 'off':
            return False
        
    def dprint(self, msg, *args):
        if self.status == 'on':
            print(msg % args)
    
    def custom_print(self, msg):
        print(msg)

    async def rtc_config(self):
        try:
            ntptime.settime()
            print("Formatted time:", self.formatted_time)
        except Exception as e:
            self.formatted_time = str(e)
            print(e)

    async def read_debug_status(self):
        if 'debug.json' in os.listdir():
            try:
                with open('debug.json') as f:
                    debug_data = json.load(f)
                    self.status = debug_data.get('debug_mode', 'off')  # Default to 'off' if 'debug_mode' is not found
                    self.dprint('Debug Mode: %s', self.status)
                    self.client.DEBUG = self.status_return()
            except Exception as e:
                print("Error reading debug status:", e)
                self.status = 'off'
        else:
            await self.debug_disable()

    async def debug_enable(self): 
        self.status = 'on'
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
        self.status = 'off'
        file_path = 'debug.json'
        try:
            with open(file_path, 'w') as f:
                json.dump({'debug_mode': 'off'}, f)
            self.dprint('Successfully updated %s', file_path)
        except OSError as e:
            self.dprint('Error updating %s: %s', file_path, e)
            
    async def post(self, comment={}, type=None):
        async def send(comment):
            if type is None:
                self.logs_pending_post.append(comment)
                try:
                    if self.client.isconnected() == True and self.status == 'on':
                        await self.send_logs()
                        gc.collect()
                    elif self.client.isconnected() == False and self.status == 'on':
                        try:
                            with open('offline_logs.txt', 'a') as file:
                                self.count += 1
                                file.write(f'\nOffline: {self.count} [Pico-time]: {self.formatted_time}\n' + comment + ' Offline end\n')  # Write logs to offline_logs.txt
                                await asyncio.sleep(0)
                        except OSError as e:
                            self.dprint('Error writing to offline_logs.txt: %s', e)
                    else:
                        self.dprint('Client: %s', self.client.isconnected())
                except OSError as e:
                    print('Error Posting: %s', e)

            elif type == 'off':
                self.off_pending_post.append(comment)
                try:
                    if self.client.isconnected() == True and self.status == 'on':
                        await self.send_logs("off")
                        gc.collect()
                    elif self.client.isconnected() == False and self.status == 'on':
                        try:
                            with open('offline_logs.txt', 'a') as file:
                                self.count += 1
                                file.write(f'\nOffline: {self.count} [Pico-time]: {self.formatted_time}\n' + comment + ' Offline end\n')  # Write logs to offline_logs.txt
                                await asyncio.sleep(0)
                        except OSError as e:
                            self.dprint('Error writing to offline_logs.txt: %s', e)
                    else:
                        self.dprint('Client: %s', self.client.isconnected())
                except OSError as e:
                    print('Error Posting: %s', e)
        asyncio.create_task(send(comment))

    async def send_logs(self, type=None):
        if type == None:
            logs = '\n'.join(self.logs_pending_post)
            try:
                if gc.mem_free() < 50000:
                    gc.collect()
                    self.logs_pending_post.clear()
                    raise Exception('Not enough memory')
                else:
                    await self.client.publish(f'Room {secrets.ROOM_NUMBER} Logs', logs, qos=0)
                    self.dprint('Logs sent successfully')
                    self.logs_pending_post.clear()
            except Exception as e:
                self.dprint('Error sending logs: %s', e)
        if type == 'off':
            off_logs = '\n'.join(self.off_pending_post)
            try:
                if gc.mem_free() < 50000:
                    gc.collect()
                    self.logs_pending_post.clear()
                    raise Exception('Not enough memory')
                else:
                    await self.client.publish(f'Room {secrets.ROOM_NUMBER}-Off', off_logs, qos=0)
                    self.dprint('Off Logs sent successfully')
                    self.off_pending_post.clear()
            except Exception as e:
                self.dprint('Error sending logs: %s', e)

    async def send_offline_logs(self):
        if 'offline_logs.txt' in os.listdir():
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
    def __init__(self, log, r):
        self.outages_count = 0
        self.init_outages_count = 0
        self.outages_file()
        self.log = log
        self.brown_out_count = 0
        self.r = r

    async def count_brown_out(self):
        file_path = 'brown_out.json'
        try:
            # Read current brown-out count from file
            if file_path in os.listdir():
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    self.brown_out_count = int(data.get('brown_out_count', 0))

            # Increment brown-out count
            self.brown_out_count += 1

            # Save updated count to file
            with open(file_path, 'w') as f:
                json.dump({'brown_out_count': self.brown_out_count}, f)
            self.log.dprint('Successfully updated %s', file_path)
            await asyncio.sleep(0)
        except OSError as e:
            self.log.dprint('Error updating %s: %s', file_path, e)
        
    
    async def outages_return(self):
        self.log.client.publish(f"Room {secrets.ROOM_NUMBER}", f"Init Outages: {self.init_outages_count}, Reg Outgaes: {self.outages_count}, Ram Reset: {self.r.status}", qos = 1)
        print("Outages Status Sent Successfully!")
        await asyncio.sleep(0)
        
    def outages_file(self): # This is basically the same as memory_reset_count, but deals with two types of outages.

        if 'outages.json' in os.listdir(): # Checks to see if file is there, if so, reads the count.
            with open('outages.json') as f:
                data = json.load(f)
                self.outages_count = data.get('outages_count', 0)
                self.init_outages_count = data.get('init_outages_count', 0)  # Use .get() to provide a default value
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
        self.ram_clear_count = 0
        self.ram_count_file()

    def ram_count_file(self):   # This will check to see if file exists and reads the count.
                                # If not, it is passed to update_ram_count to create the file. That file then keeps the count of how many times RAM was reset.
        if 'ram_status.json' in os.listdir():
            with open('ram_status.json') as f:
                data = json.load(f)
                self.status = data.get('ram_reset_count', 0)
        else:
            self.ram_clear_count = 0
            self.update_ram_count(0)

    def update_ram_count(self, increment=1):
        self.status += increment
        with open('ram_status.json', 'w') as f:
            json.dump({'ram_reset_count': self.status}, f)
