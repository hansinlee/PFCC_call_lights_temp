import utime
utime.sleep_ms(250)

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
from connection import Connection
from mqtt_commands import MqttUpdater

gc.collect()

pixels = Neopixel(4, 0, 27, "GRB")

magenta = (255,0,255)
orange = (255, 50, 0)
green = (0, 255, 0)
blue = (0, 0, 255)
red = (255, 0, 0)

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

# Buzzer
buzzer = PWM(Pin(28))
buzz_freq = 250
buzz_duty = 10000

class Logging:
    pending_post = []

    def __init__(self):
        self.status = 'off'

    def dprint(self, msg, *args):
        if self.status == 'on':
            print(msg % args)

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
                    self.dprint('Invalid content in %s. Defaulting to debug mode off.', file_path)
                    return 'off'
        except OSError as e:
            self.dprint('Error reading %s: %s', file_path, e)
            await asyncio.sleep(0)
            return 'off'
            
    async def post(self, comment=""):
        async def send(comment):
            self.pending_post.append(comment)
            self.dprint('Connection Status: %s, Debug Status: %s', client.isconnected(), self.status)
            self.dprint('2RAM free %d alloc %d', gc.mem_free(), gc.mem_alloc())
            try:
                if client.isconnected() == True and self.status == 'on':
                    await self.send_logs()  # Send logs if client is connected
                elif client.isconnected() == False and self.status == 'on':
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
        await client.publish(f'Room {secrets.ROOM_NUMBER} Logs', logs, qos=0)
        self.dprint('Logs sent successfully')
        self.pending_post.clear()

    async def send_offline_logs(self):
        if os.path.exists('offline_logs.txt'):
            try:
                with open('offline_logs.txt', 'r') as file:
                    logs = file.read()
                await client.publish(f'Room {secrets.ROOM_NUMBER} Logs', logs, qos=0)
                self.dprint('Offline logs sent successfully')
                os.remove('offline_logs.txt')  # Delete offline logs file
            except OSError as e:
                self.dprint('Error sending offline logs: %s', e)

class ButtonController:
    def __init__(self):
        self.status = {'1': 'off', '2': 'off', '3': 'off', '4': 'off', secrets.BATHROOM: 'off'}

    def get_button_status(self, bed):
        return self.status.get(bed, 'off')

    def button_status(self, bed, current_status):
        if bed in self.status and current_status in ('on', 'off'):
            self.status[bed] = current_status
            return True
        else:
            return False

    async def button_handler(self, bed, button, previous_state):
        while True:
            await asyncio.sleep(0)
            if not button.value() and not previous_state:
                if bed != secrets.BATHROOM:
                    await log.post(f"{secrets.ROOM_NUMBER}-{bed} pre-debounce triggered")
                else:
                    await log.post(f'Bathroom {secrets.BATHROOM} pre-debounce triggered')
                utime.sleep_ms(250)
                if not button.value() and not previous_state:
                    previous_state = True
                    await self.button_pressed(bed)
                    self.button_status(bed, 'on')
                    if bed != secrets.BATHROOM:
                        await log.post(f"{secrets.ROOM_NUMBER}-{bed} post-debounce triggered")
                    else:
                        await log.post(f'Bathroom {secrets.BATHROOM} post-debounce triggered')
            elif button.value() and previous_state:
                previous_state = False
                if bed != secrets.BATHROOM:
                    await log.post(f"{secrets.ROOM_NUMBER}-{bed} button released")
                else:
                    await log.post(f"Bathroom {secrets.BATHROOM} button released")
                await log.post(f'{self.status}')
                await gc_clear()
                await asyncio.sleep(0)
            await asyncio.sleep_ms(0)

    async def button_pressed(self, bed):
        await self.pixel_buzzer_on(bed)

    async def pixel_buzzer_on(self, bed):
        await asyncio.sleep_ms(0)
        if bed == "1":
            pixels.set_pixel_line(0, 0, orange)
        elif bed == "2":
            pixels.set_pixel_line(1, 1, magenta)
        elif bed == "3":
            pixels.set_pixel_line(2, 2, blue)
        elif bed == "4":
            pixels.set_pixel_line(3, 3, green)
        elif bed == secrets.BATHROOM:
            pixels.set_pixel_line(0, 3, red)
        pixels.show()
        buzzer.freq(buzz_freq)
        buzzer.duty_u16(buzz_duty)
        await log.post(f'{secrets.ROOM_NUMBER}-{bed} buzzer and light are on')
        await asyncio.sleep(0)

    async def off_handler(self, button, previous_state):
        while True:
            await asyncio.sleep(0)
            if not button.value() and not previous_state:
                await log.post(f'{secrets.ROOM_NUMBER}-off button pre-debounce triggered')
                utime.sleep_ms(250)
                if not button.value() and not previous_state:
                    previous_state = True
                    await self.turn_off_all_beds()
                    await self.keep_on_if_still_pressed("1", bed1_btn.value())
                    await self.keep_on_if_still_pressed("2", bed2_btn.value())
                    await self.keep_on_if_still_pressed(secrets.BATHROOM, bth_btn.value())
                    if secrets.NUMBER_OF_BEDS > 2:
                        await self.keep_on_if_still_pressed("3", bed3_btn.value())
                        await self.keep_on_if_still_pressed("4", bed4_btn.value())
                    await log.post(f'{secrets.ROOM_NUMBER}-off button post-debounce triggered')
            elif button.value() and previous_state:
                previous_state = False
                await log.post(f'{secrets.ROOM_NUMBER}-off button released')
                await gc_clear()
                await asyncio.sleep(0)
            await asyncio.sleep_ms(0)

    async def turn_off_all_beds(self):
        pixels.clear()
        pixels.show()
        buzzer.duty_u16(0)
        for bed in self.status:
            self.button_status(bed, 'off')
            await log.post(f'{secrets.ROOM_NUMBER} all lights and buzzers are turned off')

    async def keep_on_if_still_pressed(self, bed, prev):
        if prev == False:
            await self.pixel_buzzer_on(bed)
            await log.post(f'{secrets.ROOM_NUMBER}-{bed} button still pressed')

async def test_values():
    beds_to_check = ['1', '2', '3', '4', secrets.BATHROOM]
    previous_statuses = {bed: None for bed in beds_to_check}  # type: dict[str, Optional[str]]
    mqtt_sent_flags = {bed: False for bed in beds_to_check}  # Flag to track if MQTT message has been sent

    while True:
        for bed_to_check in beds_to_check:
            current_status = b.get_button_status(bed_to_check)

            if current_status != previous_statuses[bed_to_check]:

                if current_status == "on" and not mqtt_sent_flags[bed_to_check]:
                    await publish_mqtt_if_connected("on", bed_to_check)
                    mqtt_sent_flags[bed_to_check] = True
                elif current_status == "off" and mqtt_sent_flags[bed_to_check]:
                    await publish_mqtt_if_connected("off")
                    mqtt_sent_flags[bed_to_check] = False  # Reset the flag when status is "off"
                previous_statuses[bed_to_check] = current_status 
        await asyncio.sleep_ms(0)

async def publish_mqtt_if_connected(status, bed=None):
    retries = 10
    retry_count = 0

    if client.isconnected() == True:
        await asyncio.sleep(0)
        try:
            if status == "on":
                if bed == secrets.BATHROOM:
                    await client.publish(f'Bathroom {secrets.BATHROOM}', f'Bathroom {secrets.BATHROOM} has been pressed', qos=1)
                else:
                    await client.publish(f'{secrets.ROOM_NUMBER}-{bed}', f'Room {secrets.ROOM_NUMBER}-{bed} has been pressed', qos=1)
            elif status == 'off':
                await client.publish(f'{secrets.ROOM_NUMBER}-Off', f'Room {secrets.ROOM_NUMBER} has been answered', qos=1)
        except Exception as e:
            # Handle the exception here
            log.dprint('Error publishing message: %s', e)
    else:
        while client.isconnected() == False and retry_count < retries:
            try:
                if status == "on":
                    if bed == secrets.BATHROOM:
                        await client.publish(f'Bathroom {secrets.BATHROOM}', f'Bathroom {secrets.BATHROOM} has been pressed', qos=1)
                    else:
                        await client.publish(f'{secrets.ROOM_NUMBER}-{bed}', f'Room {secrets.ROOM_NUMBER}-{bed} has been pressed', qos=1)
                elif status == 'off':
                    await client.publish(f'{secrets.ROOM_NUMBER}-Off', f'Room {secrets.ROOM_NUMBER} has been answered', qos=1)
                retry_count += 1
            except Exception as e:
                # Handle the exception here
                log.dprint('Error publishing message: %s', e)
        # log.dprint('Outages Detected: %s', o.outages_count)
        await asyncio.sleep_ms(0)

async def led_flash():
    while True:
        onboard_led.toggle()
        await asyncio.sleep(.15)

async def watchdog_timer(timeout):
    while True:
        await asyncio.sleep(timeout)
        machine.WDT(timeout=8388)
        await asyncio.sleep(0)

async def gc_clear():
    if gc.mem_free() <= 30000:
        gc.collect()
        # m.update_ram_count()
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
    asyncio.create_task(test_values())

    try:
        await client.connect()
    except OSError as e:
        log.dprint("Connection Failed! OSError: %s", e)
        # o.update_outages(False, 0)
        # log.dprint('1Init Outage: %d', o.init_outages_count)
        await watchdog_timer(200) # Shutoff timer when OSError is returned.
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
c = Connection()
b = ButtonController()
log = Logging()
# m = MemoryResetCount()
# o = Outages()
m = MqttUpdater()

try:
    asyncio.run(main(client))
    print('Main Running')
finally:  # Prevent LmacRxBlk:1 errors.
    client.close()
    asyncio.new_event_loop()