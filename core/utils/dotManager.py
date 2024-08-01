import os

import numpy as np
from DotDevice import DotDevice
from core.database.DatabaseManager import DatabaseManager
from xdpchandler import *
import asyncio
if os.name == 'nt':
    from winrt.windows.devices import radios

async def bluetooth_power(turn_on):
    if os.name == 'nt':
        all_radios = await radios.Radio.get_radios_async()
        for this_radio in all_radios:
            if this_radio.kind == radios.RadioKind.BLUETOOTH:
                if turn_on:
                    result = await this_radio.set_state_async(radios.RadioState.ON)
                else:
                    result = await this_radio.set_state_async(radios.RadioState.OFF)
    else:
        pass

class DotManager:
    def __init__(self, db_manager : DatabaseManager) -> None:
        self.db_manager = db_manager
        self.error = False
        self.devices : List[DotDevice] = []
        self.previousConnected : List[DotDevice] = []

    def firstConnection(self):
        check = False
        while not check:
            check = True
            asyncio.run(bluetooth_power(False))
            xdpcHandler = XdpcHandler()
            if not xdpcHandler.initialize():
                xdpcHandler.cleanup()
            xdpcHandler.detectUsbDevices()
            self.portInfoUsb = {}
            while len(xdpcHandler.connectedUsbDots()) < len(xdpcHandler.detectedDots()):
                xdpcHandler.connectDots()
            for device in xdpcHandler.connectedUsbDots():
                self.portInfoUsb[str(device.deviceId())] = device.portInfo()
            xdpcHandler.cleanup()

            asyncio.run(bluetooth_power(True))
            xdpcHandler = XdpcHandler()
            if not xdpcHandler.initialize():
                xdpcHandler.cleanup()
            xdpcHandler.scanForDots()
            self.portInfoBt = xdpcHandler.detectedDots()
            xdpcHandler.cleanup()

            for portInfoBt in self.portInfoBt:
                device = self.db_manager.get_dot_from_bluetooth(portInfoBt.bluetoothAddress())
                portInfoUsb = self.portInfoUsb.get(device.id, None)
                if portInfoUsb is not None:
                    self.devices.append(DotDevice(portInfoUsb, portInfoBt, self.db_manager))
                else:
                    print(f"Please plug sensor {device.get('tag_name')}")
                    time.sleep(5)
                    check = False

        self.previousConnected = self.devices
    
    def checkDevices(self) -> tuple[List[DotDevice], List[DotDevice]]:
        connected = []
        for device in self.devices:
            if device.btDevice.isCharging():
                connected.append(device)

        lastConnected = []
        lastDisconnected = []
        if len(self.previousConnected) > len(connected):
            for device in self.previousConnected:
                if device not in connected:
                    lastDisconnected.append(device)
        elif len(self.previousConnected) < len(connected):
            for device in connected:
                if device not in self.previousConnected:
                    lastConnected.append(device)
        else:
            pass

        self.previousConnected = connected
        return(lastConnected,lastDisconnected)

    def getExportEstimatedTime(self):
        estimatedTime = []
        for device in self.devices:
            estimatedTime.append(device.getExportEstimatedTime())
        return np.max(estimatedTime)

    def getDevices(self):
        return self.devices
