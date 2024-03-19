import json
import os

class MemoryResetCount:
    def __init__(self):

        if 'ram_status.json' in os.listdir():
            with open('ram_status.json') as f:
                data = json.load(f)
                self.ram_clear_count = data.get('ram_reset_count', 0)
            print(f'3Cleared RAM x{self.ram_clear_count}')
        
        else:
            self.ram_clear_count = 0
            self.update_ram_count(0)
    
    
    def update_ram_count(self, increment=1):
        self.ram_clear_count += increment
        with open('ram_status.json', 'w') as f:
            json.dump({'ram_reset_count': self.ram_clear_count}, f)

class Outages:
    def __init__(self):

        if 'outages.json' in os.listdir():
            with open('outages.json') as f:
                data = json.load(f)
                self.outages_count = data.get('outages_count', 0)
                self.init_outages_count = data.get('init_outages_count', 0)  # Use .get() to provide a default value
            print(f'8Init Outages: {self.init_outages_count} Outages: {self.outages_count}')

        else:
            self.outages_count = 0
            self.init_outages_count = 0
            self.update_outages(True, 0)
            self.update_outages(True, 1)
    
    def update_outages(self, init, outage_type, increment=1):
        if init:
            self.outages_count = 0
            self.init_outages_count = 0
        elif outage_type == 0:
            self.init_outages_count += increment
        elif outage_type == 1:
            self.outages_count += increment
            pass

        with open('outages.json', 'w') as f:
            json.dump({'outages_count': self.outages_count, 'init_outages_count': self.init_outages_count}, f)
