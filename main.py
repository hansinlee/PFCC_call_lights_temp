import utime
utime.sleep_ms(250)

from mqtt_as import MQTTClient, config
import uasyncio as asyncio
from asyncio import Event
from machine import Pin, PWM, WDT
from neopixel import Neopixel
import network
from ota import OTAUpdater
import gc
import secrets
from json import dumps as json_encode, loads as json_decode



gc.collect()

ota_updater = OTAUpdater(secrets.FIRMWARE_URL, "main.py")
pixels = Neopixel(4, 0, 27, "GRB")

magenta = (255,0,255)
orange = (255, 50, 0)
green = (0, 255, 0)
blue = (0, 0, 255)
red = (255, 0, 0)

pixels.brightness(150)

outages = 0
buzzer = PWM(Pin(28))

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

# Network
wlan = network.WLAN(network.STA_IF)
wlan_ip = wlan.ifconfig()

# MQTT Client
client = MQTTClient(config)

buzz_freq = 250
buzz_duty = 10000

onboard_led = Pin('LED', Pin.OUT)

class Connection:
    def __init__(self):
        self.status = 'down'
    def main_conn_status(self, current_status):
        if current_status in ('up', 'down'):
            self.status = current_status
            return True
        else:
            return False
    def up_status(self, current_status):
        return current_status

    async def down(self, client):
        global outages
        while True:
            await client.down.wait()
            client.down.clear()
            post('Wifi or Broker is down')
            self.main_conn_status('down')
            outages += 1
            print(self.status)
            await asyncio.sleep(0)

    async def up(self, client):
        while True:
            await client.up.wait()
            client.up.clear()
            print(wlan.ifconfig())
            self.main_conn_status('up')
            (self.status)
            await asyncio.sleep_ms(2)
            await client.subscribe(f'Room {secrets.ROOM_NUMBER}', 0)

    async def room_status(self):
        global outages
        mac_reformat = ''
        mac_address = wlan.config('mac')
        for digit in range(6):
            mac_reformat += f'{mac_address[digit]:02X}'
            if digit < 5:
                mac_reformat += ':'
        await client.publish(f'Room {secrets.ROOM_NUMBER} MAC', mac_reformat, qos = 1)
        await client.publish(f'Room {secrets.ROOM_NUMBER} IP', str(wlan.ifconfig()), qos = 1)
        while True:
            await client.publish(f'Room {secrets.ROOM_NUMBER}', f'Room {secrets.ROOM_NUMBER} Connected! Outages: {outages}', qos=0)
            await asyncio.sleep(30)

    async def publish_mqtt_if_connected(self, status, bed=None):
        await asyncio.sleep(0)
        if self.status == 'up':
            try:
                if status == "on":
                    if bed == secrets.BATHROOM:
                        print(f'Bathroom {secrets.BATHROOM}', f'Bathroom {secrets.BATHROOM} has been pressed')
                        await client.publish(f'Bathroom {secrets.BATHROOM}', f'Bathroom {secrets.BATHROOM} has been pressed', qos=1)
                    else:
                        print(f'{secrets.ROOM_NUMBER}-{bed}', f'Room {secrets.ROOM_NUMBER}-{bed} has been pressed')
                        await client.publish(f'{secrets.ROOM_NUMBER}-{bed}', f'Room {secrets.ROOM_NUMBER}-{bed} has been pressed', qos=1)
                elif status == 'off':
                    print(f'{secrets.ROOM_NUMBER}-Off', f'Room {secrets.ROOM_NUMBER} has been answered')
                    await client.publish(f'{secrets.ROOM_NUMBER}-Off', f'Room {secrets.ROOM_NUMBER} has been answered', qos=1)
            except Exception as e:
                # Handle the exception here
                print(f'Error publishing message: {e}')
        else:
            print(f'Outages Detected: {outages}')
        await asyncio.sleep_ms(250)

    async def messages(self, client):
        async for topic, msg, retained in client.queue:
            decoded_msg = msg.decode('utf-8')
            print(f'{b_control.status} 5Topic: "{topic.decode()}" Message: "{decoded_msg}" Retained: {retained}')

            action_mapping = {
                f"Room {secrets.ROOM_NUMBER}-1 has been pressed": lambda: self.handle_room_pressed(0, 0, orange),
                f"Room {secrets.ROOM_NUMBER}-2 has been pressed": lambda: self.handle_room_pressed(1, 1, magenta),
                f"Room {secrets.ROOM_NUMBER}-3 has been pressed": lambda: self.handle_room_pressed(2, 2, blue),
                f"Room {secrets.ROOM_NUMBER}-4 has been pressed": lambda: self.handle_room_pressed(3, 3, green),
                f"Bathroom {secrets.BATHROOM} has been pressed": lambda: self.handle_room_pressed(0, 3, red),
                f'Room {secrets.ROOM_NUMBER} Reset': lambda: self.handle_reset(),
                f'Room {secrets.ROOM_NUMBER} Update': lambda: self.handle_update(),
                f"Room {secrets.ROOM_NUMBER} has been answered": lambda: self.handle_answered(),
                f"Room {secrets.ROOM_NUMBER} Pin Status": lambda: self.return_status(),
            }
            if decoded_msg in action_mapping:
                await action_mapping[decoded_msg]()
                await asyncio.sleep(0)  # Call the corresponding function

    async def handle_room_pressed(self, pixel_line, pixel_index, color):
        print('1incoming handler')
        pixels.set_pixel_line(pixel_line, pixel_index, color)
        pixels.show()
        buzzer.freq(buzz_freq)
        buzzer.duty_u16(buzz_duty)
        await asyncio.sleep(0)

    async def handle_reset(self):
        print('machine.reset handler')
        machine.reset()
        await asyncio.sleep(0)
    
    async def return_status(self):
        status_bytes = str(b_control.status).encode('utf-8')
        print('2Returning status')
        await client.publish(f'{secrets.ROOM_NUMBER} off status', status_bytes, qos=1)
        await asyncio.sleep(0)

    async def handle_update(self):
        ota_updater.download_and_install_update_if_available()
        print('OTA handler')
        if self.status == 'up':
            await client.publish(f'Room {secrets.ROOM_NUMBER}', f'Room {secrets.ROOM_NUMBER} has been updated! Please reset device.')
            post(f"Room {secrets.ROOM_NUMBER} has been successfully updated")
            await asyncio.sleep(0)

    async def handle_answered(self):
        print('pixel clear handler')
        await b_control.turn_off_all_beds()
        await asyncio.sleep(0)
connect = Connection()

class logging:
    pending_post = []

def post(comment=""):
    async def send(comment):
        if connect.status == 'up':
            logging.pending_post = []
            await client.publish(f"Room {secrets.ROOM_NUMBER} Logs", comment, qos=0)
            print(comment)
        
            print("1RAM free %d alloc %d" % (gc.mem_free(), gc.mem_alloc()))
            logging.pending_post.append(comment)
            if len(logging.pending_post) > 1:
                return
        else:
            gc.collect()
    asyncio.create_task(send(comment))

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
                    print('test2')
                    post(f"{secrets.ROOM_NUMBER}-{bed} pre-debounce triggered")
                else:
                    post(f'Bathroom {secrets.BATHROOM} pre-debounce triggered')
                utime.sleep_ms(250)
                if not button.value() and not previous_state:
                    previous_state = True
                    await self.button_pressed(bed)
                    self.button_status(bed, 'on')
                    print(self.status[bed])
                    print("RAM free %d alloc %d" % (gc.mem_free(), gc.mem_alloc()))
                    if bed != secrets.BATHROOM:
                        post(f"{secrets.ROOM_NUMBER}-{bed} post-debounce triggered")
                    else:
                        post(f'Bathroom {secrets.BATHROOM} post-debounce triggered')
            elif button.value() and previous_state:
                previous_state = False
                if bed != secrets.BATHROOM:
                    post(f"{secrets.ROOM_NUMBER}-{bed} button released")
                else:
                    post(f"Bathroom {secrets.BATHROOM} button released")
                post(f'{self.status}')
                await asyncio.sleep(0)
            await asyncio.sleep_ms(0)

    async def pixel_buzzer_on(self, bed):
        await asyncio.sleep_ms(250)
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
        post(f'{secrets.ROOM_NUMBER}-{bed} buzzer and light are on')
        # self.button_status(bed, 'on')
        await asyncio.sleep(0)

    async def button_pressed(self, bed):
        await self.pixel_buzzer_on(bed)

    async def keep_on_if_still_pressed(self, bed, prev):
        if prev == False:
            await self.pixel_buzzer_on(bed)
            post(f'{secrets.ROOM_NUMBER}-{bed} button still pressed')

    async def start_timer(self, duration, bed):
        await asyncio.sleep(duration)
        # Check if the button is still off after the timer duration
        if self.get_button_status(bed) == 'on':
            print(f"Button for Bed {bed} was off for less than {duration} seconds")

    async def off_handler(self, button, previous_state):
        while True:
            if not button.value() and not previous_state:
                post(f'{secrets.ROOM_NUMBER}-off button pre-debounce triggered')
                utime.sleep_ms(250)
                if not button.value() and not previous_state:
                    previous_state = True
                    post(f'{secrets.ROOM_NUMBER}-off button post-debounce triggered')
                    await self.turn_off_all_beds()
                    await self.keep_on_if_still_pressed("1", bed1_btn.value())
                    await self.keep_on_if_still_pressed("2", bed2_btn.value())
                    await self.keep_on_if_still_pressed(secrets.BATHROOM, bth_btn.value())
                    if secrets.NUMBER_OF_BEDS > 2:
                        await self.keep_on_if_still_pressed("3", bed3_btn.value())
                        await self.keep_on_if_still_pressed("4", bed4_btn.value())
            elif button.value() and previous_state:
                previous_state = False
                post(f'{secrets.ROOM_NUMBER}-off button released')
            await asyncio.sleep_ms(0)

    async def turn_off_all_beds(self):
        pixels.clear()
        pixels.show()
        buzzer.duty_u16(0)
        post(f'{secrets.ROOM_NUMBER} buzzer and lights turned off')
        for bed in self.status:
            self.button_status(bed, 'off')
        await asyncio.sleep(0)

b_control = ButtonController()

async def test_values():
    beds_to_check = ['off', '1', '2', '3', '4', secrets.BATHROOM]
    previous_statuses = {bed: None for bed in beds_to_check}  # type: dict[str, Optional[str]]
    mqtt_sent_flags = {bed: False for bed in beds_to_check}  # Flag to track if MQTT message has been sent

    while True:
        for bed_to_check in beds_to_check:
            current_status = b_control.get_button_status(bed_to_check)

            if current_status != previous_statuses[bed_to_check]:

                if current_status == "on" and not mqtt_sent_flags[bed_to_check]:
                    await connect.publish_mqtt_if_connected("on", bed_to_check)
                    mqtt_sent_flags[bed_to_check] = True
                elif current_status == "off" and mqtt_sent_flags[bed_to_check]:
                    await connect.publish_mqtt_if_connected("off")
                    mqtt_sent_flags[bed_to_check] = False  # Reset the flag when status is "off"
                previous_statuses[bed_to_check] = current_status
        await asyncio.sleep_ms(150)

async def led_flash():
    while True:
        onboard_led.toggle()
        await asyncio.sleep(1)

async def watchdog_timer(timeout):
    while True:
        await asyncio.sleep(timeout)
        machine.WDT(timeout=8388)
        await asyncio.sleep_ms(250)

async def main(client):
    asyncio.create_task(b_control.button_handler("1", bed1_btn, bed1_prev_state))
    asyncio.create_task(b_control.button_handler("2", bed2_btn, bed2_prev_state))
    asyncio.create_task(b_control.button_handler(secrets.BATHROOM, bth_btn, bth_prev_state))
    if secrets.NUMBER_OF_BEDS > 2:
        asyncio.create_task(b_control.button_handler("3", bed3_btn, bed3_prev_state))
        asyncio.create_task(b_control.button_handler("4", bed4_btn, bed4_prev_state))
    asyncio.create_task(b_control.off_handler(off_btn, off_prev_state))
    asyncio.create_task(connect.room_status())
    asyncio.create_task(led_flash())
    asyncio.create_task(test_values())
    try:
        await client.connect()
    except OSError as e:
        print("Connection Failed! OSError:", e)
        await watchdog_timer(300) # Shutoff timer when OSError is returned.
        return
    for task in (connect.up, connect.down, connect.messages):
        asyncio.create_task(task(client))
    while True:
        await asyncio.sleep_ms(250)

# Set up client. Enable optional debug statements.
MQTTClient.DEBUG = True
client = MQTTClient(config)

try:
    asyncio.run(main(client))
finally:  # Prevent LmacRxBlk:1 errors.
    client.close()
    asyncio.new_event_loop()