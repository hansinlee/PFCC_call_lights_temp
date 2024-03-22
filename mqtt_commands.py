from connection import Connection
import secrets
import json
from ota import OTAUpdater
b = Connection()
c = Connection

class MqttUpdater:        

    async def execute_mqtt_commands(self):
        while True:
            if b.decoded_msg.startswith(f'Room {secrets.ROOM_NUMBER} Update'):
                        try:
                            update_info = json.loads(c.decoded_msg.split(".", 1)[1])

                            for url, filename in update_info.items():
                                print(url, filename)
                                ota = OTAUpdater(url, filename)
                                ota.download_and_install_update_if_available()
                                print('success!')
                        except Exception as e:
                            print(f"Error updating files: {e}")

                # action_mapping = {
                #     f"Room {secrets.ROOM_NUMBER}-1 has been pressed": lambda: self.handle_room_pressed(0, 0, orange),
                #     f"Room {secrets.ROOM_NUMBER}-2 has been pressed": lambda: self.handle_room_pressed(1, 1, magenta),
                #     f"Room {secrets.ROOM_NUMBER}-3 has been pressed": lambda: self.handle_room_pressed(2, 2, blue),
                #     f"Room {secrets.ROOM_NUMBER}-4 has been pressed": lambda: self.handle_room_pressed(3, 3, green),
                #     f"Bathroom {secrets.BATHROOM} has been pressed": lambda: self.handle_room_pressed(0, 3, red),
                #     f'Room {secrets.ROOM_NUMBER} Reset': lambda: self.handle_reset(),
                #     f"Room {secrets.ROOM_NUMBER} has been answered": lambda: self.handle_answered(),
                #     f"Room {secrets.ROOM_NUMBER} Pin Status": lambda: self.return_status(),
                #     f"Room {secrets.ROOM_NUMBER} debug enable": lambda: self.debug_enable(),
                #     f"Room {secrets.ROOM_NUMBER} debug disable": lambda: self.debug_disable(),
                # }
                # if c.decoded_msg in action_mapping:
                #     await action_mapping[c.decoded_msg]()
                #     await asyncio.sleep(0)  # Call the corresponding function

    # async def handle_room_pressed(self, pixel_line, pixel_index, color):
    #     pixels.set_pixel_line(pixel_line, pixel_index, color)
    #     pixels.show()
    #     buzzer.freq(buzz_freq)
    #     buzzer.duty_u16(buzz_duty)
    #     await asyncio.sleep(0)
        
    # async def handle_reset(self):
    #     machine.reset()

    # async def return_status(self):
    #     status_bytes = str(b.status).encode('utf-8')
    #     await client.publish(f'{secrets.ROOM_NUMBER} off status', status_bytes, qos=1)
    #     await asyncio.sleep(0)

    # async def handle_answered(self):
    #     await b.turn_off_all_beds()
    #     await asyncio.sleep(0)

    # async def debug_enable(self): 
    #     log.debugger('on')
    #     file_path = 'debug.txt'
    #     try:
    #         with open(file_path, 'w') as file:
    #             file.write('debug = on\n')
    #         log.dprint('Successfully updated %s', file_path)
    #     except OSError as e:
    #         log.dprint('Error updating %s: %s', file_path, e)

    # async def debug_disable(self): 
    #     log.debugger('off')
    #     file_path = 'debug.txt'
    #     try:
    #         with open(file_path, 'w') as file:
    #             file.write('debug = off\n')
    #         log.dprint('Successfully updated %s', file_path)
    #     except OSError as e:
    #         log.dprint('Error updating %s: %s', file_path, e)
