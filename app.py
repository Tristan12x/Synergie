from queue import Queue
import time
import tkinter as tk
import threading
import os

import pandas as pd

from front.DotPage import DotPage
from front.RecordPage import RecordPage
from xdpchandler import *
from core.data_treatment.data_generation.exporter import export
from core.database.DatabaseManager import *
from front.DevPage import DevPage
from front.MainPage import MainPage
from dotConnectionManager import *

class App:
    def __init__(self, master):
        self.db_manager = DatabaseManager()
        self.bluetoothEvent = threading.Event()
        MainPage(self.db_manager, self.bluetoothEvent, master)
        self.dot_connection_manager = DotConnectionManager()
        self.dico_device = {}

        #DevPage(master)
        detection_thread = threading.Thread(target=self.detectDots, args=())
        detection_thread.daemon = True
        detection_thread.start()

        treatment_thread = threading.Thread(target=self.run, args=())
        treatment_thread.daemon = True
        treatment_thread.start()

    def run(self):
        while True :
            list_file = os.listdir("data/new/")
            if len(list_file)>0:
                file = os.path.join("data/new/", list_file[0])
                new_file = os.path.join("data/processing/", list_file[0])
                os.replace(file, new_file)
                print("Processing")
                event = threading.Event()
                process_thread = threading.Thread(target=self.export_file, args=(new_file, event))
                process_thread.daemon = True
                process_thread.start()
                event.wait()
            time.sleep(1)
    
    def export_file(self, path, event : threading.Event):
        skater_id, df = export(path)
        print("End of process")
        os.remove(path)
        training_id = path.split("/")[-1].split("_")[0]
        for iter,row in df.iterrows():
            jump_time_min, jump_time_sec = row["videoTimeStamp"].split(":")
            jump_time = '{:02d}:{:02d}'.format(int(jump_time_min), int(jump_time_sec))
            val_rot = float(row["rotations"])
            if row["type"] != 5:
                val_rot = np.ceil(val_rot)
            else:
                val_rot = np.ceil(val_rot-0.5)+0.5
            jump_data = JumpData(0, training_id, int(row["type"]), val_rot, bool(row["success"]), jump_time)
            self.db_manager.save_jump_data(jump_data)
        event.set()

    def detectDots(self):
        self.xdpcHandler = XdpcHandler()
        self.usbDevices = []

        if not self.xdpcHandler.initialize():
            self.xdpcHandler.cleanup()
            exit(-1)
        self.val = 0
        while True:
            if not self.bluetoothEvent.is_set():
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
                            self.dot_connection_manager.stoprecord(np.vectorize(lambda x : str(x.deviceId()), otypes=[str])(lastConnected), self.db_manager)
                            asyncio.run(bluetooth_power(False))
                        self.export_data(lastConnected)
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
                    RecordPage(self.db_manager, infoqueue).createPage()
                    name = infoqueue.get()
                    skater_id = self.db_manager.get_skater_id_from_name(name)
                    if len(skater_id) > 0:
                        asyncio.run(bluetooth_power(True))
                        time.sleep(1)
                        self.dot_connection_manager.startrecord(lastDisconnected, skater_id, self.db_manager)
                        asyncio.run(bluetooth_power(False))
                    else:
                        print("Unknown skater")
                self.val = len(self.xdpcHandler.detectedDots())
                self.xdpcHandler.resetConnectedDots()
                self.xdpcHandler.cleanup()
            time.sleep(1)
    
    def export_data(self, lastConnected):
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

root = tk.Tk()
myapp = App(root)
root.geometry("1000x400")
root.mainloop()