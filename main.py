from bluepy import btle
import yaml
import re
import paho.mqtt.client as mqtt


class MJHTDelegate(object):
    def __init__(self):
        self.temperature = None
        self.humidity = None
        self.received = False

    def handleNotification(self, cHandle, data):
        if cHandle == 14:
            m = re.search('T=([\d\.]*)\s+?H=([\d\.]*)', ''.join(map(chr, data)))
            self.temperature = m.group(1)
            self.humidity = m.group(2)
            self.received = True

class XiaomiHTLoader():
    def __init__(self, mac_addr):
        self.mac_address = mac_addr
        self.delegate = None
        self.battery = None
        self.temperature = None
        self.humidity = None

    def load_info(self, retry_times):
        p = None
        for x in range(retry_times):
            try:
                p = btle.Peripheral(self.mac_address)
                break
            except btle.BTLEException as e:
                p = None
        if p is None:
            print("Failed")
            exit(0)

        battery = p.readCharacteristic(0x18)[0]
        self.battery = battery
        self.delegate = MJHTDelegate()
        p.withDelegate(self.delegate)
        p.writeCharacteristic(0x10, bytearray([1, 0]), True)
        while not self.delegate.received:
            p.waitForNotifications(5.0)
        self.temperature = self.delegate.temperature
        self.humidity = self.delegate.humidity

if __name__ == '__main__':
    file_path = "./config.yaml"
    f = open(file_path)
    config_file = yaml.safe_load(f)
    mac_add = config_file.get("sensor_mac")
    max_retry = config_file.get("max_retry")
    loader = None
    if max_retry is None:
        max_retry = 5
    if mac_add:
        loader = XiaomiHTLoader(mac_add)
    else:
        exit(0)
    loader.load_info(max_retry)
    print(loader.battery, loader.temperature, loader.humidity)
