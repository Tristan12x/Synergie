from queue import Queue
import time
from typing import List
import os
import numpy as np
import pandas as pd
from core.database.DatabaseManager import DatabaseManager, TrainingData
from front.RecordPage import RecordPage
from xdpchandler import *
import asyncio
if os.name == 'nt':
    from winrt.windows.devices import radios

from movelladot_pc_sdk.movelladot_pc_sdk_py39_64 import XsDotDevice

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

class DotBluetoothManager:
    def __init__(self, db_manager : DatabaseManager):
        self.xdpcHandler = XdpcHandler()
        self.val = 0
        self.usbDevices = []
        self.connectedDots = []
        self.db_manager = db_manager
        self.recordHandler = XdpcHandler()
        if not self.xdpcHandler.initialize():
            self.xdpcHandler.cleanup()
            exit(-1)
        if not self.recordHandler.initialize():
            self.recordHandler.cleanup()
            exit(-1)

        self.portInfoArray = []
        self.usbXdpcHandler = XdpcHandler()
        if not self.usbXdpcHandler.initialize():
            self.usbXdpcHandler.cleanup()
            exit(-1)
        self.btXdpcHandler = XdpcHandler()
        if not self.btXdpcHandler.initialize():
            self.btXdpcHandler.cleanup()
            exit(-1)

    def connectToDots(self):
        asyncio.run(bluetooth_power(True))
        self.resetRecordHandler()
        self.recordHandler.scanForDots()
        maxTry = 0
        while len(self.recordHandler.connectedDots()) < len(self.recordHandler.detectedDots()) and maxTry <= 100:
            self.recordHandler.connectDots()
            maxTry += 1
        for x in self.recordHandler.connectedDots():
            print(x.deviceId())
        dots = []
        for device in self.recordHandler.connectedDots():
            dots.append(device)
        return dots

    def resetRecordHandler(self):
        self.recordHandler.cleanup()
        self.recordHandler.resetWaitingConnection()
        self.recordHandler.resetConnectedDots()
        self.recordHandler = XdpcHandler()
        if not self.recordHandler.initialize():
            self.recordHandler.cleanup()
            exit(-1)

    def newStartRecord(self, device : XsDotDevice):
        device.startRecording()

    def startrecord(self, lastDisconnected, skater_id, db_manager : DatabaseManager):
        xdpcHandler = XdpcHandler()
        if not xdpcHandler.initialize():
            xdpcHandler.cleanup()
            exit(-1)
        bluetooth_address = db_manager.get_bluetooth_address(lastDisconnected)
        xdpcHandler.scanOneDots(bluetooth_address)
        while len(xdpcHandler.connectedDots()) != len(xdpcHandler.detectedDots()):
            xdpcHandler.connectOneDot(bluetooth_address)
        for device in xdpcHandler.connectedDots():
            if str(device.deviceId()) in lastDisconnected:
                print("Starting onboard recording")
                device.startRecording()
                new_training = TrainingData(0, skater_id[0].id, 0, str(device.deviceId()))
                db_manager.set_current_record(str(device.deviceId()), db_manager.save_training_data(new_training))
            else : 
                print("Not the correct dot")
        xdpcHandler.cleanup()
        xdpcHandler.resetWaitingConnection()

    def stoprecord(self, lastConnected : List[XsDotDevice], db_manager : DatabaseManager):
        xdpcHandler = XdpcHandler()
        if not xdpcHandler.initialize():
            xdpcHandler.cleanup()
            exit(-1)
        bluetooth_address = db_manager.get_bluetooth_address(lastConnected)
        xdpcHandler.scanOneDots(bluetooth_address)
        while len(xdpcHandler.connectedDots()) != len(xdpcHandler.detectedDots()):
            xdpcHandler.connectOneDot(bluetooth_address)
        for device in xdpcHandler.connectedDots():
            print(device.deviceId())
            if str(device.deviceId()) in lastConnected:
                print("Stoping onboard recording")
                device.stopRecording()
                current_record = db_manager.get_current_record(str(device.deviceId()))
                db_manager.set_training_date(current_record, device.getRecordingInfo(device.recordingCount()).startUTC())
                db_manager.set_current_record(str(device.deviceId()), "0")
            else : 
                print("Not the correct dot")    
        xdpcHandler.cleanup()
        xdpcHandler.resetWaitingConnection()

    def detectUsbDots(self):
        self.xdpcHandler.detectUsbDevices()
        if len(self.xdpcHandler.detectedDots())-self.val != 0:
            self.val = len(self.xdpcHandler.detectedDots())
        self.xdpcHandler.resetConnectedDots()
        self.xdpcHandler.cleanup()

    def dotConnection(self, db_manager: DatabaseManager):
        lastConnected = []
        lastDisconnected = []
        asyncio.run(bluetooth_power(False))
        self.xdpcHandler.detectUsbDevices()
        if len(self.xdpcHandler.detectedDots())-self.val > 0:
            print("Connected, extracting data")
            self.xdpcHandler.connectDots()
            connectedUsb = []
            isRecording = False
            for usb in self.xdpcHandler.connectedUsbDots():
                if not str(usb.deviceId()) in self.usbDevices and usb.recordingCount() != 0:
                    lastConnected.append(usb)
                connectedUsb.append(str(usb.deviceId()))
                isRecording += (usb.recordingCount()==-1)
            self.usbDevices = connectedUsb
            if len(lastConnected) > 0:
                if isRecording:
                    asyncio.run(bluetooth_power(True))
                    self.stoprecord(np.vectorize(lambda x : str(x.deviceId()), otypes=[str])(lastConnected), db_manager)
                    asyncio.run(bluetooth_power(False))
                self.export_data(lastConnected, db_manager)
            else : 
                print("No available dots for data extraction, all are empty")
        elif len(self.xdpcHandler.detectedDots())-self.val < 0:
            print("Disconnected dot")
            self.xdpcHandler.connectDots()
            connectedUsb = []
            for usb in self.xdpcHandler.connectedUsbDots():
                connectedUsb.append(str(usb.deviceId()))
            for usb in self.usbDevices:
                if not usb in connectedUsb:
                    lastDisconnected.append(usb)
            self.usbDevices = connectedUsb
            infoqueue = Queue()
            RecordPage(db_manager, infoqueue).createPage()
            name = infoqueue.get()
            skater_id = db_manager.get_skater_id_from_name(name)
            if len(skater_id) > 0:
                asyncio.run(bluetooth_power(True))
                time.sleep(1)
                self.startrecord(lastDisconnected, skater_id, db_manager)
                asyncio.run(bluetooth_power(False))
            else:
                print("Unknown skater")
        self.val = len(self.xdpcHandler.detectedDots())
        self.xdpcHandler.resetConnectedDots()
        self.xdpcHandler.cleanup()

    def export_data(self, lastConnected: List[XsDotDevice], db_manager):
        exportData = movelladot_pc_sdk.XsIntArray()
        exportData.push_back(movelladot_pc_sdk.RecordingData_Timestamp)
        exportData.push_back(movelladot_pc_sdk.RecordingData_Euler)
        exportData.push_back(movelladot_pc_sdk.RecordingData_Acceleration)
        exportData.push_back(movelladot_pc_sdk.RecordingData_AngularVelocity)

        for device in lastConnected:
            for recordingIndex in range(1, device.recordingCount()+1):
                recInfo = device.getRecordingInfo(recordingIndex)
                if recInfo.empty():
                    print(f'Could not get recording info. Reason: {device.lastResultText()}')

                dateRecord = recInfo.startUTC()
                trainings = db_manager.find_training(dateRecord, str(device.deviceId()))
                if len(trainings) > 0:
                    training = trainings[0]
                    csvFilename = f"data/raw/{training.id}_{training.get('skater_id')}_{dateRecord}.csv"

                    if not device.selectExportData(exportData):
                        print(f'Could not select export data. Reason: {device.lastResultText()}')
                    elif not device.enableLogging(csvFilename):
                        print(f'Could not open logfile for data export. Reason: {device.lastResultText()}')
                    elif not device.startExportRecording(recordingIndex):
                        print(f'Could not export recording. Reason: {device.lastResultText()}')
                    else:
                        # Sleeping for max 10 seconds...
                        startTime = movelladot_pc_sdk.XsTimeStamp_nowMs()
                        while not self.xdpcHandler.exportDone() and movelladot_pc_sdk.XsTimeStamp_nowMs() - startTime <= 10000:
                            time.sleep(0.1)

                        if self.xdpcHandler.exportDone():
                            print('File export finished!')
                        else:
                            print('Done sleeping, aborting export for demonstration purposes.')
                            if not device.stopExportRecording():
                                print(f'Device stop export failed. Reason: {device.lastResultText()}')
                            else:
                                print('Device export stopped')

                    device.disableLogging()
                    df = pd.read_csv(f"{csvFilename}")
                    new_df = df[["SampleTimeFine","Euler_X","Euler_Y","Euler_Z","Acc_X","Acc_Y","Acc_Z","Gyr_X","Gyr_Y","Gyr_Z"]]
                    new_name  = f"data/new/{csvFilename.split('/')[-1]}"
                    new_df.to_csv(new_name,index=True, index_label="PacketCounter")
            device.eraseFlash()
            print("You can disconnect the dot")
        self.xdpcHandler.cleanup()

    def firstConnection(self) -> None:
        asyncio.run(bluetooth_power(True))
        if not self.btXdpcHandler.initialize():
            self.btXdpcHandler.cleanup()
            exit(-1)
        self.btXdpcHandler.resetConnectedDots()
        self.btXdpcHandler.scanForDots()
        while len(self.btXdpcHandler.connectedDots()) < len(self.btXdpcHandler.detectedDots()):
            self.btXdpcHandler.connectDots()

    def reconnectDots(self, device_list : List[str]) -> None:
        bluetooth_address = self.db_manager.get_bluetooth_address(device_list)
        nbConnected = len(self.btXdpcHandler.connectedDots()) + len(device_list)
        while len(self.btXdpcHandler.connectedDots()) < nbConnected:
            self.btXdpcHandler.reconnectBtDot(bluetooth_address)

    def getConnectedBluetoothDots(self) -> List[XsDotDevice]:
        return self.btXdpcHandler.connectedDots()

    def getConnectedBluetoothDotsId(self) -> List[str]:
        return np.vectorize(lambda x : x.deviceId(),otypes=[str])(self.btXdpcHandler.connectedDots())

    def findUnconnectedDotsId(self, devices : List[str]) -> List[str]:
        unconnectedDots = []
        for device in devices:
            if device not in self.getConnectedBluetoothDotsId():
                unconnectedDots.append(str(device.deviceId()))
        return unconnectedDots

    def startRecordDots(self, deviceIdList : List[str]):
        for device in self.btXdpcHandler.connectedDots():
            if str(device.deviceId()) in deviceIdList:
                print(f"Start Recording {device.deviceTagName()}")
                device.startRecording()

    def stopRecordDots(self, deviceIdList : List[str]):
        for device in self.btXdpcHandler.connectedDots():
            if str(device.deviceId()) in deviceIdList:
                print(f"Stop Recording {device.deviceTagName()}")
                device.stopRecording()
