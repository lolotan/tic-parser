"""
TIC Parser (téléinfo)
Python script intended to be used with an electronic adapter to usb serial device.
Only standard mode is currently supported (not legacy one).
Usage: python tic_parser (optional serial device)
"""

import serial
import json
import sys
import paho.mqtt.client as mqtt


STX = '\x02'
ETX = '\x03'
HT = '\x09'
LF = '\x0A'
CR = '\x0D'

VERSION_MAJOR = "1"
VERSION_MINOR = "0"
VERSION = VERSION_MAJOR + "." + VERSION_MINOR

DEFAULT_SERIAL = "/dev/ttyACM0"


def verify_checksum(data, checksum):
    """
    Checksum computation and verify function:
    data: str containing raw data to check.
    checksum: str containing raw checksum from frame.
    returns True if checksum is valid, False if not.
    """
    s1_val = 0
    for s_val in data[:-1]:
        s1_val += int.from_bytes(bytearray(s_val, encoding='ascii'),'big')
    s1_val &= 0x3f
    s1_val += 0x20
    return s1_val == int.from_bytes(bytearray(checksum, encoding='ascii'),'big')


# Beginning of the script
print("Starting tic_parser version ", VERSION)

# MQTT configuration
client = mqtt.Client()
client.connect("localhost", 1883, 60)

client.loop_start()

# Serial configuration
serial_device = DEFAULT_SERIAL
if len(sys.argv) == 2:
    serial_device = sys.argv[1]

print("Opening ", serial_device, "serial device")
tic_serial = serial.Serial(port=serial_device,
                           baudrate=9600,
                           bytesize=7,
                           parity=serial.PARITY_EVEN)    

conf_tag = None
try:
    with open("tags.json") as conf_tag_file:
        conf_tag = json.load(conf_tag_file)
        print("Tags configuration found with following values: ", json.dumps(conf_tag))
except FileNotFoundError:
    print("No Tags configuration found, publishing all tags")

while True:
    data_bytes = tic_serial.read_until(expected=bytearray(ETX, encoding="ascii"))
    # Test if valid frame, starting with STX
    if data_bytes[0] == int.from_bytes(bytearray(STX, encoding="ascii"),'big'):
        # Convert to string and remove STX/ETX
        data_str = data_bytes.decode('ascii')
        data_str = data_str.replace(STX,'') \
                           .replace(ETX,'')
        # Split datasets
        data_set_list = data_str.split(CR)
        for data_set in data_set_list:
            # Valid dataset ?
            if len(data_set) > 2 and data_set[0] == LF: # 2 because LF and one byte minimum
                data_set = data_set.replace(LF, '')
                data = data_set.split(HT)
                if verify_checksum(data_set, data_set[-1]):
                    message = {}
                    tag = data[0].replace("+", "plus")
                    if conf_tag is None or tag in conf_tag:
                        topic = "tic_raw/" + tag
                        if len(data) == 3:
                            # Without timestamp
                            message["data"] = data[1]
                        elif len(data) == 4:
                            # With timestamp
                            message["timestamp"] = data[1]
                            message["data"] = data[2]
                        else:
                            print("Error in dataset length:", data)

                        if len(message):
                            client.publish(topic, payload=json.dumps(message), qos=0, retain=False)
                else:
                    print("Bad checksum: ", data_set)
