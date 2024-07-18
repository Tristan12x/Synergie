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

class DotUsbManager:
    def __init__(self, db_manager : DatabaseManager):
        self.db_manager = db_manager
        self.portInfoArray = []
        self.usbXdpcHandler = XdpcHandler()
        if not self.usbXdpcHandler.initialize():
            self.usbXdpcHandler.cleanup()
            exit(-1)

    def firstUsbConnection(self) -> None:
        asyncio.run(bluetooth_power(False))
        if not self.usbXdpcHandler.initialize():
            self.usbXdpcHandler.cleanup()
            exit(-1)
        self.usbXdpcHandler.resetConnectedDots()
        self.usbXdpcHandler.detectUsbDevices()
        self.portInfoArray = self.usbXdpcHandler.detectedDots()

        while len(self.usbXdpcHandler.connectedUsbDots()) < len(self.usbXdpcHandler.detectedDots()):
            self.usbXdpcHandler.connectDots()

    def checkUsbConnection(self) -> tuple[List[str], List[str]]:
        usbDevices = np.vectorize(lambda x : x.deviceId(), otypes=[str])(self.usbXdpcHandler.connectedUsbDots())
        if not self.usbXdpcHandler.initialize():
            self.usbXdpcHandler.cleanup()
            exit(-1)
        self.usbXdpcHandler.resetConnectedDots()
        self.usbXdpcHandler.reconnectUsbDot(self.portInfoArray)
        lastConnected = []
        lastDisconnected = []

        newConnected = np.vectorize(lambda x : x.deviceId(), otypes=[str])(self.usbXdpcHandler.connectedUsbDots())

        if len(newConnected)>len(usbDevices):
            for device in newConnected:
                if device not in usbDevices:
                    lastConnected.append(device)
        else:
            for device in usbDevices:
                if device not in newConnected:
                    lastDisconnected.append(device)

        return lastConnected,lastDisconnected
    
    def export_data(self, lastConnected: List[XsDotDevice]):
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
                trainings = self.db_manager.find_training(dateRecord, str(device.deviceId()))
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
                        while not self.usbXdpcHandler.exportDone() and movelladot_pc_sdk.XsTimeStamp_nowMs() - startTime <= 10000:
                            time.sleep(0.1)

                        if self.usbXdpcHandler.exportDone():
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
        self.usbXdpcHandler.cleanup()

    def getConnectedUsbDots(self) -> List[XsDotUsbDevice]:
        return self.usbXdpcHandler.connectedUsbDots()
    
    def getConnectedUsbDotsId(self) -> List[str]:
        return np.vectorize(lambda x : x.deviceId(),otypes=[str])(self.usbXdpcHandler.connectedUsbDots())

    def showExportData(self, devicesId : List[str]):
        for device in self.usbXdpcHandler.connectedUsbDots():
            if device.deviceId in devicesId:
                print(f"There are {device.recordingCount()} trainings saved")
                for index in range(1, device.recordingCount()+1):
                    print(f"Export {index}")
                    estimated_time = round(device.getRecordingInfo(index).storageSize()/(237568*8),0) + 1 
                    print(f"Estimated exporting time : {estimated_time} min")
