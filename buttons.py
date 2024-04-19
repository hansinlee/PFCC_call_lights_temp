from neopixel import Neopixel
import secrets
import uasyncio as asyncio
import utime as time
import gc

from config import (
    buzzer, buzz_freq, buzz_duty, 
    pixels, magenta, orange, green, blue, red,
    bed1_btn, bed2_btn, bed3_btn, bed4_btn, bth_btn
)

gc.collect()

class ButtonController:
    def __init__(self, log, r):
        self.status = {'1': 'off', '2': 'off', '3': 'off', '4': 'off', secrets.BATHROOM: 'off'} # Initialize button state
        # self.client = client
        self.log = log
        self.r = r

    async def gc_clear(self):
        if gc.mem_free() <= 30000:
            gc.collect()
            self.r.update_ram_count()
            self.log.client.dprint("Ram Reset: %s", self.r.status)
            await asyncio.sleep(0)

    def get_button_status(self, bed):
        return self.status.get(bed, 'off')

    def button_status(self, bed, current_status): # Handles button status per bed/bathroom.
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
                    await self.log.post(f"{secrets.ROOM_NUMBER}-{bed} pre-debounce triggered") # Logs pre-debounce. If pre-debounce is triggered and not followed by post-debounce, adjust debounce_ms.
                else:
                    await self.log.post(f'Bathroom {secrets.BATHROOM} pre-debounce triggered')
                time.sleep_ms(250) # Adds debounce - adjust accordingly.
                if not button.value() and not previous_state:
                    previous_state = True
                    await self.button_pressed(bed)
                    self.button_status(bed, 'on')
                    if bed != secrets.BATHROOM:
                        await self.log.post(f"{secrets.ROOM_NUMBER}-{bed} post-debounce triggered")
                    else:
                        await self.log.post(f'Bathroom {secrets.BATHROOM} post-debounce triggered')
            elif button.value() and previous_state:
                previous_state = False
                if bed != secrets.BATHROOM:
                    await self.log.post(f"{secrets.ROOM_NUMBER}-{bed} button released")
                else:
                    await self.log.post(f"Bathroom {secrets.BATHROOM} button released")
                await self.log.post(f'{self.status}')
                await self.gc_clear()
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
        await self.log.post(f'{secrets.ROOM_NUMBER}-{bed} buzzer and light are on')
        await asyncio.sleep(0)

    async def off_handler(self, button, previous_state):
        while True:
            await asyncio.sleep(0)
            if not button.value() and not previous_state:
                await self.log.post(f'{secrets.ROOM_NUMBER}-off button pre-debounce triggered')
                time.sleep_ms(250)
                if not button.value() and not previous_state:
                    previous_state = True
                    await self.turn_off_all_beds()
                    await self.keep_on_if_still_pressed("1", bed1_btn.value())
                    await self.keep_on_if_still_pressed("2", bed2_btn.value())
                    await self.keep_on_if_still_pressed(secrets.BATHROOM, bth_btn.value())
                    if secrets.NUMBER_OF_BEDS > 2:
                        await self.keep_on_if_still_pressed("3", bed3_btn.value())
                        await self.keep_on_if_still_pressed("4", bed4_btn.value())
                    await self.log.post(f'{secrets.ROOM_NUMBER}-off button post-debounce triggered')
            elif button.value() and previous_state:
                previous_state = False
                await self.log.post(f'{secrets.ROOM_NUMBER}-off button released')
                await self.gc_clear()
                await asyncio.sleep(0)
            await asyncio.sleep_ms(0)

    async def turn_off_all_beds(self):
        pixels.clear()
        pixels.show()
        buzzer.duty_u16(0)
        for bed in self.status:
            self.button_status(bed, 'off')
            await self.log.post(f'{secrets.ROOM_NUMBER} all lights and buzzers are turned off')

    async def keep_on_if_still_pressed(self, bed, prev):
        if prev == False:
            await self.pixel_buzzer_on(bed)
            await self.log.post(f'{secrets.ROOM_NUMBER}-{bed} button still pressed')

    async def test_values(self):
        beds_to_check = ['1', '2', '3', '4', secrets.BATHROOM]
        previous_statuses = {bed: None for bed in beds_to_check}  # type: dict[str, Optional[str]]
        mqtt_sent_flags = {bed: False for bed in beds_to_check}  # Flag to track if MQTT message has been sent

        while True:
            for bed_to_check in beds_to_check:
                current_status = self.get_button_status(bed_to_check)

                if current_status != previous_statuses[bed_to_check]:

                    if current_status == "on" and not mqtt_sent_flags[bed_to_check]:
                        await self.publish_mqtt_if_connected("on", bed_to_check)
                        mqtt_sent_flags[bed_to_check] = True
                    elif current_status == "off" and mqtt_sent_flags[bed_to_check]:
                        await self.publish_mqtt_if_connected("off")
                        mqtt_sent_flags[bed_to_check] = False  # Reset the flag when status is "off"
                    previous_statuses[bed_to_check] = current_status 
            await asyncio.sleep_ms(0)

    async def publish_mqtt_if_connected(self, status, bed=None):
        retries = 10
        retry_count = 0

        if self.log.client.isconnected():
            await asyncio.sleep(0)
            try:
                if status == "on":
                    if bed == secrets.BATHROOM:
                        await self.log.client.publish(f'Bathroom {secrets.BATHROOM}', f'Bathroom {secrets.BATHROOM} has been pressed', qos=1)
                    else:
                        await self.log.client.publish(f'{secrets.ROOM_NUMBER}-{bed}', f'Room {secrets.ROOM_NUMBER}-{bed} has been pressed', qos=1)
                elif status == 'off':
                    await self.log.client.publish(f'{secrets.ROOM_NUMBER}-Off', f'Room {secrets.ROOM_NUMBER} has been answered', qos=1)
            except Exception as e:
                # Handle the exception here
                self.log.client.dprint('Error publishing message: %s', e)
        else:
            while self.log.client.isconnected() == False and retry_count < retries:
                try:
                    if status == "on":
                        if bed == secrets.BATHROOM:
                            await self.log.client.publish(f'Bathroom {secrets.BATHROOM}', f'Bathroom {secrets.BATHROOM} has been pressed', qos=1)
                        else:
                            await self.log.client.publish(f'{secrets.ROOM_NUMBER}-{bed}', f'Room {secrets.ROOM_NUMBER}-{bed} has been pressed', qos=1)
                    elif status == 'off':
                        await self.log.client.publish(f'{secrets.ROOM_NUMBER}-Off', f'Room {secrets.ROOM_NUMBER} has been answered', qos=1)
                    retry_count += 1
                except Exception as e:
                    # Handle the exception here
                    self.log.client.dprint('Error publishing message: %s', e)
            # self.log.client.dprint('Outages Detected: %s', o.outages_count)
            await asyncio.sleep_ms(0)
    async def handle_room_pressed(self, pixel_line, pixel_index, color):
        pixels.set_pixel_line(pixel_line, pixel_index, color)
        pixels.show()
        buzzer.freq(buzz_freq)
        buzzer.duty_u16(buzz_duty)
        await asyncio.sleep(0)
    
    async def handle_answered(self):
        await self.turn_off_all_beds()
        await asyncio.sleep(0)

    async def return_status(self):
        status_bytes = str(self.status).encode('utf-8')
        await self.log.client.publish(f'Room {secrets.ROOM_NUMBER} Button Status', status_bytes, qos=1)
        await asyncio.sleep(0)
