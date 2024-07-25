import threading
import time
from tkinter.font import BOLD, Font
import ttkbootstrap as ttkb

from core.database.DatabaseManager import DatabaseManager, TrainingData
from core.utils.dotManager import DotManager

class StartingPage:
    def __init__(self, deviceId : str, dot_manager : DotManager, db_manager : DatabaseManager, event : threading.Event) -> None:
        self.deviceId = deviceId
        self.db_manager = db_manager
        self.dot_manager = dot_manager
        self.deviceTag = self.db_manager.get_tag(self.deviceId)
        self.event = event
        self.skaters = db_manager.get_all_skaters()
        self.window = ttkb.Toplevel(title="Confirmation", size=(1000,400))
        self.window.grid_rowconfigure(0, weight = 1)
        self.window.grid_columnconfigure(0, weight = 1)
        self.frame = ttkb.Frame(self.window)
        self.frame.grid_rowconfigure(0, weight = 0)
        self.frame.grid_rowconfigure(1, weight = 1)
        self.frame.grid_rowconfigure(2, weight = 1)
        label = ttkb.Label(self.frame, text=f"Starting a training on sensor {self.deviceTag}", font=Font(self.window, size=20, weight=BOLD))
        label.grid(row=0,column=0,columnspan=len(self.skaters),pady=20)
        skater_per_column = len(self.skaters)//2 + len(self.skaters)%2
        for i in range(skater_per_column):
            self.frame.grid_columnconfigure(i, weight = 1)
        buttonStyle = ttkb.Style()
        buttonStyle.configure('my.TButton', font=Font(self.frame, size=15, weight=BOLD))
        for i,skater in enumerate(self.skaters):
            button = ttkb.Button(self.frame, text=skater.skater_name, style="my.TButton", command=lambda : self.startRecord(skater.skater_id))
            button.grid(row=i//skater_per_column+1,column=i%skater_per_column,sticky="nsew",padx=10,pady=10)
        self.frame.grid(sticky="nswe")
        self.window.grid()

    def startRecord(self ,skaterId: str):
        new_training = TrainingData(0, skaterId, 0, self.deviceId)
        self.db_manager.set_current_record(self.deviceId, self.db_manager.save_training_data(new_training))
        recordStarted = self.dot_manager.bluetooth.startRecordDots(self.deviceId)
        self.event.set()
        self.frame.destroy()
        self.frame = ttkb.Frame(self.window)
        if recordStarted :
            message = f"Record started on sensor {self.deviceTag}"
        else : 
            message = "Error during process, cannot start the recording"
        label = ttkb.Label(self.frame, text=message, font=Font(self.window, size=20, weight=BOLD))
        label.grid()
        self.frame.grid()
        self.window.update()
        time.sleep(1)
        self.window.destroy()