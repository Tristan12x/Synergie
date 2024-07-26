import threading
from tkinter.font import BOLD, Font
from typing import List
import ttkbootstrap as ttkb

from core.database.DatabaseManager import DatabaseManager
from core.utils.dotManager import DotManager
from front.DotPage import DotPage

from movelladot_pc_sdk.movelladot_pc_sdk_py39_64 import XsDotDevice

from front.ExtractingPage import ExtractingPage

class MainPage:
    def __init__(self, dotsConnected : List[XsDotDevice], dot_manager : DotManager, db_manager : DatabaseManager, root :ttkb.Window = None) -> None:
        self.root = root
        self.dotsConnected = dotsConnected
        self.dot_manager = dot_manager
        self.db_manager = db_manager
        self.root.grid_columnconfigure(0, weight=1)
        self.frame = ttkb.Frame(root)
        self.frame.grid_rowconfigure(0,weight=1,pad=100)
        self.frame.grid_rowconfigure(1,weight=1, pad=100)
        self.frame.grid_rowconfigure(2,weight=1, pad=100)
        self.buttonFrame = ttkb.Frame(self.frame)
        self.buttonFrame.grid_columnconfigure(0,weight=1)
        buttonStyle = ttkb.Style()
        buttonStyle.configure('my.TButton', font=Font(self.frame, size=20, weight=BOLD))
        ttkb.Button(self.buttonFrame, text='Scan for dots', style="my.TButton", command=self.no).grid(row=0, column=0)
        self.buttonFrame.grid(row=0,column=0)
        self.waiting_label = ttkb.Label(self.frame, text="Waiting for connection", font=Font(self.root, size=15, weight=BOLD))
        self.waiting_label.grid(row=1,column=0)
        self.frame.grid()
        
    def no(self):
        print("no")
    
    def make_dot_page(self):
        self.waiting_label.destroy()
        self.dotFrame = ttkb.Frame(self.frame)
        self.dotPage = DotPage(self.dotFrame)
        self.dotFrame.grid(row=1,column=0)
        self.make_export_button()
        self.frame.update()
        self.run_periodic_background_func()
    
    def make_export_button(self):
        estimatedTime = 0
        for device in self.dotsConnected:
            deviceEstTime = self.dot_manager.usb.getExportEstimatedTime(str(device.deviceId()))
            if estimatedTime < deviceEstTime:
                estimatedTime = deviceEstTime
        ttkb.Button(self.frame, text=f'Export data from all dots, estimated time : {estimatedTime} min', style="my.TButton", command=self.export_all_dots).grid(row=2, column=0, sticky="s")

    def export_all_dots(self):
        for device in self.dotsConnected:
            if device.recordingCount() > 0:
                extractEvent = threading.Event()
                ExtractingPage(str(device.deviceId()), self.db_manager, extractEvent)
                self.dot_manager.usb.export_data_thread(str(device.deviceId()), extractEvent)

    def run_periodic_background_func(self):
        self.dotPage.make_dot_connection_page(self.dotsConnected)
        self.root.after(1000,self.run_periodic_background_func)