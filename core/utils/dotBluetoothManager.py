import time
from typing import List
import os
import numpy as np
from core.database.DatabaseManager import DatabaseManager
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
        self.val = 0
        self.usbDevices = []
        self.connectedDots = []
        self.db_manager = db_manager

        self.portInfoArray = []
        self.btXdpcHandler = XdpcHandler()
        if not self.btXdpcHandler.initialize():
            self.btXdpcHandler.cleanup()
            exit(-1)

    def export_data(self, deviceId : str, db_manager: DatabaseManager):
        exportData = movelladot_pc_sdk.XsIntArray()
        exportData.push_back(movelladot_pc_sdk.RecordingData_Timestamp)
        exportData.push_back(movelladot_pc_sdk.RecordingData_Euler)
        exportData.push_back(movelladot_pc_sdk.RecordingData_Acceleration)
        exportData.push_back(movelladot_pc_sdk.RecordingData_AngularVelocity)

        device = 0
        for d in self.btXdpcHandler.connectedDots():
            if d.deviceId() == deviceId:
                device = d

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
                    while not self.btXdpcHandler.exportDone() and movelladot_pc_sdk.XsTimeStamp_nowMs() - startTime <= 10000:
                        time.sleep(0.1)

                    if self.btXdpcHandler.exportDone():
                        print('File export finished!')
                    else:
                        print('Done sleeping, aborting export for demonstration purposes.')
                        if not device.stopExportRecording():
                            print(f'Device stop export failed. Reason: {device.lastResultText()}')
                        else:
                            print('Device export stopped')

                device.disableLogging()
                """ df = pd.read_csv(f"{csvFilename}")
                new_df = df[["SampleTimeFine","Euler_X","Euler_Y","Euler_Z","Acc_X","Acc_Y","Acc_Z","Gyr_X","Gyr_Y","Gyr_Z"]]
                new_name  = f"data/new/{csvFilename.split('/')[-1]}"
                new_df.to_csv(new_name,index=True, index_label="PacketCounter") """
        device.eraseFlash()
        print("You can disconnect the dot")

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
        return np.vectorize(lambda x : str(x.deviceId()),otypes=[str])(self.btXdpcHandler.connectedDots())

    def findUnconnectedDotsId(self, devices : List[str]) -> List[str]:
        unconnectedDots = []
        for device in devices:
            if device not in self.getConnectedBluetoothDotsId():
                unconnectedDots.append(device)
        return unconnectedDots

    def startRecordDots(self, deviceIdList : List[str]) -> bool:
        for device in self.btXdpcHandler.connectedDots():
            if str(device.deviceId()) in deviceIdList:
                print(f"Start Recording {device.deviceTagName()}")
                return device.startRecording()
        return False 

    def stopRecordDots(self, deviceIdList : List[str]) -> bool:
        for device in self.btXdpcHandler.connectedDots():
            if str(device.deviceId()) in deviceIdList:
                print(f"Stop Recording {device.deviceTagName()}")
                recordStopped = device.stopRecording()
                current_record = self.db_manager.get_current_record(str(device.deviceId()))
                self.db_manager.set_training_date(current_record, device.getRecordingInfo(device.recordingCount()).startUTC())
                self.db_manager.set_current_record(str(device.deviceId()), "0")
                return recordStopped
        return False
