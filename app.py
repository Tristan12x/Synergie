import time
import tkinter as tk
import threading
import os

from core.data_treatment.data_generation.exporter import export
from core.database.DatabaseManager import *
from front.MainPage import MainPage
from core.utils.dotBluetoothManager import *

class App:

    def __init__(self, master):
        self.db_manager = DatabaseManager()
        self.bluetoothEvent = threading.Event()
        MainPage(self.db_manager, self.bluetoothEvent, master)
        self.dot_connection_manager = DotBluetoothManager()

        self.bluetoothDevices = self.dot_connection_manager.firstConnection()

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
        while True:
            if not self.bluetoothEvent.is_set():
                self.dot_connection_manager.dotConnection(self.db_manager)
            time.sleep(1)

root = tk.Tk()
myapp = App(root)
root.geometry("1000x400")
root.mainloop()