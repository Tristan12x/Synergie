import threading
import time
from tkinter.font import BOLD, Font
import ttkbootstrap as ttkb

from DotDevice import DotDevice
from front.ExtractingPage import ExtractingPage

class StopingPage:
    def __init__(self, device : DotDevice, event : threading.Event) -> None:
        self.device = device
        self.deviceTag = self.device.deviceTagName()
        self.event = event
        self.window = ttkb.Toplevel(title="Confirmation", size=(1000,400))
        self.window.grid_rowconfigure(0, weight = 1)
        self.window.grid_columnconfigure(0, weight = 1)
        self.frame = ttkb.Frame(self.window)
        self.frame.grid_rowconfigure(0, weight = 0)
        self.frame.grid_rowconfigure(1, weight = 1)
        self.frame.grid_rowconfigure(2, weight = 1)
        self.frame.grid_columnconfigure(0, weight = 1)
        label = ttkb.Label(self.frame, text=f"Stoping a training on sensor {self.deviceTag}", font=Font(self.window, size=20, weight=BOLD))
        label.grid(row=0,column=0,pady=20)
        buttonStyle = ttkb.Style()
        buttonStyle.configure('my.TButton', font=Font(self.frame, size=15, weight=BOLD))
        ttkb.Button(self.frame, text="Stop", style="my.TButton", command=self.stopRecord).grid(row=1,column=0,sticky="nsew",pady=20)
        self.estimatedTime = self.device.getExportEstimatedTime()
        ttkb.Button(self.frame, text=f"Stop and extract data \n Estimated time : {round(self.estimatedTime,0)} min", style="my.TButton", command=self.stopRecordAndExtract).grid(row=2,column=0,sticky="nsew")
        self.frame.grid(sticky ="nswe")
        self.window.grid()

    def stopRecord(self):
        recordStopped = self.device.stopRecord()
        self.event.set()
        self.frame.destroy()
        self.frame = ttkb.Frame(self.window)
        if recordStopped :
            message = f"Record stopped on sensor {self.deviceTag}"
        else : 
            message = "Error during process, cannot stop the recording"
        label = ttkb.Label(self.frame, text=message, font=Font(self.window, size=20, weight=BOLD))
        label.grid()
        self.frame.grid()
        self.window.update()
        time.sleep(1)
        self.window.destroy()
    
    def stopRecordAndExtract(self):
        recordStopped = self.device.stopRecord()
        self.event.set()
        self.frame.destroy()
        self.frame = ttkb.Frame(self.window)
        if recordStopped :
            message = f"Record stopped on sensor {self.deviceTag}"
        else : 
            message = "Error during process, cannot stop the recording"
        label = ttkb.Label(self.frame, text=message, font=Font(self.window, size=20, weight=BOLD))
        label.grid()
        self.frame.grid()
        self.window.update()
        time.sleep(1)
        if recordStopped :
            extractEvent = threading.Event()
            if self.device.exportDataThread(extractEvent):
                ExtractingPage(self.device, self.estimatedTime, extractEvent)
        self.window.destroy()
