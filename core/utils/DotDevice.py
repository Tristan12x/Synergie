from threading import Event, Thread
import time
from movelladot_pc_sdk.movelladot_pc_sdk_py39_64 import XsDotDevice, XsDotUsbDevice, XsDotConnectionManager, XsDotCallback, XsPortInfo, XsDataPacket
import movelladot_pc_sdk
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont, ImageTk

from core.data_treatment.data_generation.exporter import export
from core.database.DatabaseManager import DatabaseManager, JumpData

class DotDevice(XsDotCallback):
    def __init__(self, portInfoUsb : XsPortInfo, portInfoBt : XsPortInfo, db_manager : DatabaseManager):
        XsDotCallback.__init__(self)
        self.portInfoUsb = portInfoUsb
        self.portInfoBt = portInfoBt
        self.db_manager = db_manager

        self.usbManager = XsDotConnectionManager()
        while self.usbManager is None:
            self.usbManager = XsDotConnectionManager()
        self.usbManager.addXsDotCallbackHandler(self)

        self.btManager = XsDotConnectionManager()
        while self.btManager is None:
            self.btManager = XsDotConnectionManager()

        self.usbDevice : XsDotUsbDevice = None
        self.btDevice : XsDotDevice = None
        self.initializeUsb()
        self.initializeBt()
        self.loadImages()
        self.currentImage = self.imageActive

        self.count = 0
        self.packetsReceived = []
        self.exportDone = False

    def initializeBt(self):
        self.btManager.closePort(self.portInfoBt)
        checkDevice = False
        while not checkDevice:
            self.btManager.closePort(self.portInfoBt)
            if not self.btManager.openPort(self.portInfoBt):
                print(f"Connection to Device {self.portInfoBt.bluetoothAddress()} failed")
                checkDevice = False
            else:
                device : XsDotDevice = self.btManager.device(self.portInfoBt.deviceId())
                if device is None:
                    checkDevice = False
                else:
                    time.sleep(1)
                    checkDevice = (device.deviceTagName() != '') and (device.batteryLevel() != 0)
        self.btDevice = device
    
    def initializeUsb(self):
        self.usbManager.closePort(self.portInfoUsb)
        device = None
        while device is None:
            self.usbManager.openPort(self.portInfoUsb)
            device = self.usbManager.usbDevice(self.portInfoUsb.deviceId())
        self.usbDevice = device
    
    def loadImages(self):
        fontTag = ImageFont.truetype(font="arialbd.ttf",size=60)
        imgActive = Image.open(f"img/Dot_active.png")
        d = ImageDraw.Draw(imgActive)
        text = self.deviceTagName()
        x = 0
        if len(text) == 1:
            x = 93
        else:
            x = 75
        d.text( (x,65), text,font=fontTag, fill="black")
        imgActive = imgActive.resize((116, 139))
        self.imageActive = ImageTk.PhotoImage(imgActive)

        imgInactive = Image.open(f"img/Dot_inactive.png")
        d = ImageDraw.Draw(imgInactive)
        text = self.deviceTagName()
        x = 0
        if len(text) == 1:
            x = 93
        else:
            x = 75
        d.text( (x,65), text,font=fontTag, fill="black")
        imgInactive = imgInactive.resize((116, 139))
        self.imageInactive = ImageTk.PhotoImage(imgInactive)
    
    def checkConnection(self):
        print(f"Connected to dot with ID : {self.usbDevice.deviceId()}")
        print(f"and Tag : {self.btDevice.deviceTagName()}")
    
    def startRecord(self):
        if not self.btDevice.startRecording():
            self.initializeBt()
            return self.btDevice.startRecording()
        return True

    def stopRecord(self):
        if not self.btDevice.stopRecording():
            self.initializeBt()
            return self.btDevice.stopRecording()
        return True
    
    def exportDataThread(self, extractEvent : Event) -> bool:
        self.exporting = True
        self.currentImage = self.imageInactive
        self.initializeUsb()
        export_thread = Thread(target=self.exportData, args=([extractEvent]))
        export_thread.daemon = True
        export_thread.start()
        return True

    def exportData(self, extractEvent : Event):
        self.exportDone = False
        self.packetsReceived = []
        self.count = 0
        exportData = movelladot_pc_sdk.XsIntArray()
        exportData.push_back(movelladot_pc_sdk.RecordingData_Timestamp)
        exportData.push_back(movelladot_pc_sdk.RecordingData_Euler)
        exportData.push_back(movelladot_pc_sdk.RecordingData_Acceleration)
        exportData.push_back(movelladot_pc_sdk.RecordingData_AngularVelocity)

        for recordingIndex in range(1, self.usbDevice.recordingCount()+1):
            recInfo = self.usbDevice.getRecordingInfo(recordingIndex)
            if recInfo.empty():
                print(f'Could not get recording info. Reason: {self.usbDevice.lastResultText()}')

            dateRecord = recInfo.startUTC()
            trainingId = self.db_manager.get_current_record(self.deviceId())
            self.db_manager.set_training_date(trainingId, dateRecord)
            skaterId = self.db_manager.get_skater_from_training(trainingId)
            if not self.usbDevice.selectExportData(exportData):
                print(f'Could not select export data. Reason: {self.usbDevice.lastResultText()}')
            elif not self.usbDevice.startExportRecording(recordingIndex):
                print(f'Could not export recording. Reason: {self.usbDevice.lastResultText()}')
            else:
                while not self.exportDone:
                    time.sleep(0.1)
                print('File export finished!')
                df = pd.DataFrame.from_records(self.packetsReceived, columns=["PacketCounter","SampleTimeFine","Euler_X","Euler_Y","Euler_Z","Acc_X","Acc_Y","Acc_Z","Gyr_X","Gyr_Y","Gyr_Z"])

            self.predict_training(trainingId, skaterId, df)
        
        self.usbDevice.eraseFlash()
        print("You can disconnect the dot")
        
        extractEvent.set()
        self.exporting = False
        self.currentImage = self.imageActive

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
        
    def onRecordedDataAvailable(self, device, packet : XsDataPacket):
        self.count += 1
        euler = packet.orientationEuler()
        captor = packet.calibratedData()
        data = np.concatenate([[int(self.count), packet.sampleTimeFine(), euler.x(), euler.y(), euler.z()], captor.m_acc, captor.m_gyr])
        self.packetsReceived.append(data)
    
    def onRecordedDataDone(self, device):
        self.exportDone = True

    def checkState(self):
        if self.btDevice.batteryLevel()==0:
            self.btManager.closePort(self.portInfoBt)
            self.initializeBt()
    
    def __eq__(self, device) -> bool:
        return (self.usbDevice == device.usbDevice) and (self.btDevice == device.btDevice)
    
    def getExportEstimatedTime(self) -> int:
        estimatedTime = 0
        for index in range(1,self.usbDevice.recordingCount()+1):
            estimatedTime = estimatedTime + round(self.usbDevice.getRecordingInfo(index).storageSize()/(237568*8),1)
        return estimatedTime + 1

    def deviceTagName(self) -> str:
        return str(self.btDevice.deviceTagName())
    
    def deviceId(self) -> str:
        return str(self.usbDevice.deviceId())

    def isCharging(self) -> bool:
        return self.btDevice.isCharging()
    
    def batteryLevel(self) -> int:
        return self.btDevice.batteryLevel()
    
    def recordingCount(self) -> int:
        return self.btDevice.recordingCount() 
