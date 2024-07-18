from queue import Queue
import time
from typing import List
import os
import numpy as np
import pandas as pd
from core.database.DatabaseManager import DatabaseManager, TrainingData
from core.utils.dotBluetoothManager import DotBluetoothManager
from core.utils.dotUsbManager import DotUsbManager
from front.RecordPage import RecordPage
from xdpchandler import *
import asyncio
if os.name == 'nt':
    from winrt.windows.devices import radios

class DotManager:
    def __init__(self, db_manager) -> None:
        self.db_manager = db_manager
        self.bluetooth = DotBluetoothManager(db_manager)
        self.usb = DotUsbManager(db_manager)
    
    def initialise(self):
        self.usb.firstUsbConnection()
        self.bluetooth.firstConnection()
    
    def checkFirstConnection(self):
        if self.bluetooth.getConnectedBluetoothDots() == [] or self.usb.getConnectedUsbDots() == []:
            return True
        else:
            return set(self.bluetooth.getConnectedBluetoothDotsId()) != set(self.usb.getConnectedUsbDotsId())

    def getBluetoothFromUsb(self, usb_device : XsDotUsbDevice) -> XsDotDevice:
        for bluetooth_device in self.bluetooth.getConnectedBluetoothDots():
            if usb_device.deviceId() == bluetooth_device.deviceId():
                return bluetooth_device
        return None