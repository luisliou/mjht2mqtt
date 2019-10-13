import time

from bluepy import btle
import yaml
import re
import paho.mqtt.client as mqtt

connected = False
polling_interval = 10


class MJHTDelegate(object):
    def __init__(self):
        self.temperature = None
        self.humidity = None
        self.received = False

    def handleNotification(self, handle, data):
        if handle == 14:
            m = re.search('T=([\d\.]*)\s+?H=([\d\.]*)', ''.join(map(chr, data)))
            self.temperature = m.group(1)
            self.humidity = m.group(2)
            self.received = True


class XiaoMiHTLoader():
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


def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    global connected
    connected = True


def on_disconnect(client, userdata, rc):
    print("Disconnected " + str(rc))
    global connected
    connected = False


if __name__ == '__main__':
    file_path = "./config.yaml"
    f = open(file_path)
    config_file = yaml.safe_load(f)
    mac_add = config_file.get("sensor_mac")
    max_retry = config_file.get("max_retry")
    topic = config_file.get("topic")
    interval = config_file.get("polling_interval")
    if interval is not None:
        polling_interval = interval
    mqtt_cfg = config_file.get("mqtt")
    host = mqtt_cfg.get("host")
    port = mqtt_cfg.get("port")
    user = mqtt_cfg.get("user")
    pwd = str(mqtt_cfg.get("password"))
    loader = None
    if max_retry is None:
        max_retry = 5
    if host is None:
        print("mqtt host is not defined")
        exit(-1)
    if port is None:
        port = 1883
    if mac_add:
        loader = XiaoMiHTLoader(mac_add)
    else:
        exit(-1)
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    if user is not None:
        client.username_pw_set(username=user, password=pwd)
    client.connect(host, port, 60)
    client.loop_start()

    while True:
        if connected:
            try:
                loader.load_info(max_retry)
                result = {
                    "battery": int(loader.battery),
                    "temperature": float(loader.temperature),
                    "humidity": float(loader.humidity)
                }
                json_str = str(result).replace('\'', '\"')
                client.publish(topic=topic, payload=json_str)
                print(json_str)
            except Exception as e:
                print(e)
        time.sleep(polling_interval)
