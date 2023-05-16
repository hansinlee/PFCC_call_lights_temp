from mqtt_as import MQTTClient
from mqtt_local import wifi_led, blue_led, config
import uasyncio as asyncio
from machine import Pin, PWM
import utime

TOPIC = 'Room 37'
outages = 0
LED1 = PWM(Pin(0))
LED2 = PWM(Pin(15))
buzzer = PWM(Pin(22))

bed1_btn = Pin(1,Pin.IN,Pin.PULL_DOWN)
bed1_prev_state = bed1_btn.value()
bed2_btn = Pin(14,Pin.IN,Pin.PULL_DOWN)
bed2_prev_state = bed2_btn.value()
bed3_btn = Pin(27,Pin.IN,Pin.PULL_DOWN)
bed3_prev_state = bed3_btn.value()
bed4_btn = Pin(17,Pin.IN,Pin.PULL_DOWN)
bed4_prev_state = bed4_btn.value()
bth_btn = Pin(21,Pin.IN,Pin.PULL_DOWN)
bth_prev_state = bth_btn.value()
off_btn = Pin(4,Pin.IN,Pin.PULL_DOWN)
off_prev_state = off_btn.value()


async def bed1_handler():
    global bed1_prev_state
    if (bed1_btn.value() == True) and (bed1_prev_state == False):
        utime.sleep_ms(350)
        if (bed1_btn.value() == True) and (bed1_prev_state == False):
            bed1_prev_state = True
    elif (bed1_btn.value() == False) and (bed1_prev_state == True):
         bed1_prev_state = False
         LED1.freq(600)
         LED1.duty_u16(10000)
         buzzer.freq(300)
         buzzer.duty_u16(60000)
         print("Bed 1 has been pressed")
         await client.publish('37-1', 'Room 37-1 has been pressed', qos = 1)
         
    
        
async def bed2_handler():
    global bed2_prev_state
    if (bed2_btn.value() == True) and (bed2_prev_state == False):
        utime.sleep_ms(250)
        if (bed2_btn.value() == True) and (bed2_prev_state == False):
            bed2_prev_state = True
        
    elif (bed2_btn.value() == False) and (bed2_prev_state == True):
        bed2_prev_state = False
        LED1.freq(600)
        LED1.duty_u16(10000)
        buzzer.freq(300)
        buzzer.duty_u16(60000)
        print("Bed 2 has been pressed")
        await client.publish('37-2', 'Room 37-2 has been pressed', qos = 1)

            
async def bth_handler():
    global bth_prev_state
    if (bth_btn.value() == True) and (bth_prev_state == False):
        utime.sleep_ms(250)
        if (bth_btn.value() == True) and (bth_prev_state == False):
            bth_prev_state = True
            LED2.freq(600)
            LED2.duty_u16(10000)
            buzzer.freq(300)
            buzzer.duty_u16(60000)
            print("Bathroom 37 has been pressed")
            await client.publish('Bathroom 37 & 39', 'Bathroom 37 & 39 has been pressed', qos = 1)
            
    elif (bth_btn.value() == False) and (bth_prev_state == True):
        bth_prev_state = False
        await asyncio.sleep_ms(25)


async def off_handler():
    global off_prev_state
    if (off_btn.value() == True) and (off_prev_state == False):
        utime.sleep_ms(250)
        if (off_btn.value() == True) and (off_prev_state == False):
            off_prev_state = True
            LED1.duty_u16(0)
            LED2.duty_u16(0)
            buzzer.duty_u16(0)
            await client.publish('37-Off', 'Room 37 has been answered', qos = 1)
            print("Room 37 has been answered")
            
    elif (off_btn.value() == False) and (off_prev_state == True):
        off_prev_state = False
        await asyncio.sleep_ms(25)


async def messages(client):
    async for topic, msg, retained in client.queue:
        print(f'Topic: "{topic.decode()}" Message: "{msg.decode()}" Retained: {retained}')
        msg = msg.decode('utf-8')
        print(msg)
        if msg == 'Room 37-1 has been pressed':
            LED1.freq(600)
            LED1.duty_u16(10000)
            buzzer.freq(300)
            buzzer.duty_u16(60000)

        if msg == 'Room 37-2 has been pressed':
            LED1.freq(600)
            LED1.duty_u16(10000)
            buzzer.freq(300)
            buzzer.duty_u16(60000)
            
        if msg == 'Bathroom 37 & 39 has been pressed':
            LED2.freq(600)
            LED2.duty_u16(10000)
            buzzer.freq(300)
            buzzer.duty_u16(60000)
            
        elif msg == 'Room 37 has been answered':
            LED1.duty_u16(0)
            LED2.duty_u16(0)
            buzzer.duty_u16(0)
            await asyncio.sleep_ms(10)
            
async def down(client):
    global outages
    while True:
        await client.down.wait()  # Pause until connectivity changes
        client.down.clear()
        wifi_led(False)
        outages += 1
        print('WiFi or broker is down.')

async def up(client):
    while True:
        await client.up.wait()
        client.up.clear()
        wifi_led(True)
        print('We are connected to broker.')
        await client.subscribe('Room 37', 1)

async def main(client):
    try:
        await client.connect()
    except OSError:
        print('Connection failed.')
    
    for task in (up, down, messages):
        asyncio.create_task(task(client))
        
    n = 0
    
    while True:
        
        await bed1_handler()
        await bed2_handler()
        await bth_handler()
        await off_handler()
        await asyncio.sleep_ms(10)

# Define configuration
config['will'] = (TOPIC, 'Room 37 connected!', False, 0)
config['keepalive'] = 120
config["queue_len"] = 1  # Use event interface with default queue

# Set up client. Enable optional debug statements.
MQTTClient.DEBUG = True
client = MQTTClient(config)

try:
    asyncio.run(main(client))
finally:  # Prevent LmacRxBlk:1 errors.
    client.close()
    blue_led(True)
    asyncio.new_event_loop()
