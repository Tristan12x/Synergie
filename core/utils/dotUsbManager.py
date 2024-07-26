from threading import Event, Thread
import time
from typing import List
import os
import numpy as np
import pandas as pd

from core.data_treatment.data_generation.exporter import export
from core.database.DatabaseManager import DatabaseManager, JumpData
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

class DotUsbManager:
    def __init__(self, db_manager : DatabaseManager):
        self.db_manager = db_manager
        self.portInfoArray = []
        self.usbExporting = []
        self.usbDevices = []
        self.exporting = []
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
        self.usbDevices = np.vectorize(lambda x : str(x.deviceId()), otypes=[str])(self.usbXdpcHandler.connectedUsbDots())

    def checkUsbConnection(self) -> tuple[List[str], List[str]]:
        if not self.usbXdpcHandler.initialize():
            self.usbXdpcHandler.cleanup()
            exit(-1)
        self.usbXdpcHandler.resetConnectedDots()
        self.usbXdpcHandler.reconnectUsbDot(self.portInfoArray)
        lastConnected = []
        lastDisconnected = []

        for deviceId in self.exporting:
            self.usbExporting.remove(deviceId)
            self.exporting.remove(deviceId)
        newConnected = np.vectorize(lambda x : str(x.deviceId()), otypes=[str])(self.usbXdpcHandler.connectedUsbDots())
        newConnected = np.concatenate([newConnected,self.usbExporting], dtype = str)

        if len(newConnected)>len(self.usbDevices):
            for device in newConnected:
                if device not in self.usbDevices:
                    lastConnected.append(device)
        elif len(newConnected)<len(self.usbDevices):
            for device in self.usbDevices:
                if device not in newConnected:
                    lastDisconnected.append(device)
        else:
            pass
        
        self.usbDevices = newConnected
        return lastConnected,lastDisconnected
    
    def export_data_thread(self, deviceId : str, extractEvent : Event):
        self.usbExporting.append(deviceId)
        self.usbXdpcHandler.reconnectUsbDot(self.portInfoArray)
        device = None
        for d in self.usbXdpcHandler.connectedUsbDots():
            if str(d.deviceId()) == deviceId:
                device = d
                break
        if device is None:
            print("Error : device not found")
        else:
            export_thread = Thread(target=self.export_data, args=([device, extractEvent]))
            export_thread.daemon = True
            export_thread.start()
    
    def export_data(self, device: XsDotUsbDevice, extractEvent : Event):
        print("Exporting data")

        portInfo = device.portInfo()
        deviceXsId = device.deviceId()
        nbRecords = device.recordingCount()
        self.usbXdpcHandler.disconnecteUsbDot(device)

        if nbRecords <= 0 :
            print("No record to export")
        else :
            print(f"{nbRecords} records available")

        for recordingIndex in range(1, nbRecords+1):
            print(f"Exporting record {recordingIndex}")
            self.usbXdpcHandler.disconnecteUsbDotFromId(deviceXsId)
            exportXdpcHandler = XdpcHandler()
            if not exportXdpcHandler.initialize():
                exportXdpcHandler.cleanup()
                exit(-1)
            while len(exportXdpcHandler.connectedUsbDots()) < 1:
                self.usbXdpcHandler.disconnecteUsbDot(device)
                exportXdpcHandler.reconnectUsbDot([portInfo])
            device = exportXdpcHandler.connectedUsbDots()[0]
            recInfo = device.getRecordingInfo(recordingIndex)
            if recInfo.empty():
                print(f'Could not get recording info. Reason: {device.lastResultText()}')

            dateRecord = recInfo.startUTC()
            trainings = self.db_manager.find_training(dateRecord, str(device.deviceId()))
            if len(trainings) > 0:
                exportData = movelladot_pc_sdk.XsIntArray()
                exportData.push_back(movelladot_pc_sdk.RecordingData_Timestamp)
                exportData.push_back(movelladot_pc_sdk.RecordingData_Euler)
                exportData.push_back(movelladot_pc_sdk.RecordingData_Acceleration)
                exportData.push_back(movelladot_pc_sdk.RecordingData_AngularVelocity)
                training = trainings[0]

                if not device.selectExportData(exportData):
                    print(f'Could not select export data. Reason: {device.lastResultText()}')
                elif not device.startExportRecording(recordingIndex):
                    print(f'Could not export recording. Reason: {device.lastResultText()}')
                else:
                    while not exportXdpcHandler.exportDone():
                        time.sleep(0.1)
                    print('File export finished!')
                    df = pd.DataFrame.from_records(exportXdpcHandler.packetsReceived(), columns=["PacketCounter","SampleTimeFine","Euler_X","Euler_Y","Euler_Z","Acc_X","Acc_Y","Acc_Z","Gyr_X","Gyr_Y","Gyr_Z"])

            self.predict_training(training.id, training.get('skater_id'), df)
            exportXdpcHandler.resetConnectedDots()
            exportXdpcHandler.cleanup()

        self.usbXdpcHandler.disconnecteUsbDotFromId(deviceXsId)

        eraseXdpcHandler = XdpcHandler()
        if not eraseXdpcHandler.initialize():
            eraseXdpcHandler.cleanup()
            exit(-1)
        while len(eraseXdpcHandler.connectedUsbDots()) < 1:
            self.usbXdpcHandler.disconnecteUsbDot(device)
            eraseXdpcHandler.reconnectUsbDot([portInfo])
        device = eraseXdpcHandler.connectedUsbDots()[0]
        device.eraseFlash()
        print("You can disconnect the dot")
        eraseXdpcHandler.resetConnectedDots()
        eraseXdpcHandler.cleanup()

        self.exporting.append(str(deviceXsId))
        extractEvent.set()

    def predict_training(self, training_id, skater_id, df : pd.DataFrame):
        df = export(skater_id, df)
        print("End of process")
        for iter,row in df.iterrows():
            jump_time_min, jump_time_sec = row["videoTimeStamp"].split(":")
            jump_time = '{:02d}:{:02d}'.format(int(jump_time_min), int(jump_time_sec))
            val_rot = float(row["rotations"])
            if row["type"] != 5:
                val_rot = np.ceil(val_rot)
            else:
                val_rot = np.ceil(val_rot-0.5)+0.5
            jump_data = JumpData(0, training_id, int(row["type"]), val_rot, bool(row["success"]), jump_time, float(row["rotation_speed"]), float(row["length"]))
            self.db_manager.save_jump_data(jump_data)

    def getConnectedUsbDots(self) -> List[XsDotUsbDevice]:
        return self.usbXdpcHandler.connectedUsbDots()
    
    def getConnectedUsbDotsId(self) -> List[str]:
        return np.vectorize(lambda x : str(x.deviceId()),otypes=[str])(self.usbXdpcHandler.connectedUsbDots())

    def getExportEstimatedTime(self, deviceId : str) -> int:
        device = 0
        for d in self.usbXdpcHandler.connectedUsbDots():
            if str(d.deviceId()) == deviceId:
                device = d
        estimatedTime = 0
        for index in range(1, device.recordingCount()+1):
            estimatedTime = estimatedTime + round(device.getRecordingInfo(index).storageSize()/(237568*8),0) 
        estimatedTime = estimatedTime + 1
        return estimatedTime
