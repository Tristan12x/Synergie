import threading
from tkinter.font import BOLD, Font
from typing import List
import ttkbootstrap as ttkb

from core.utils.DotDevice import DotDevice
from core.database.DatabaseManager import DatabaseManager
from core.utils.DotManager import DotManager
from front.DotPage import DotPage

from front.ExtractingPage import ExtractingPage

class MainPage:
    def __init__(self, dotsConnected : List[DotDevice], dot_manager : DotManager, db_manager : DatabaseManager, root :ttkb.Window = None) -> None:
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
        labelFont = Font(self.root, size=15, weight=BOLD)
        ttkb.Button(self.buttonFrame, text='Scan for dots', style="my.TButton", command=self.no).grid(row=0, column=0)
        self.buttonFrame.grid(row=0,column=0)
        self.waiting_label = ttkb.Label(self.frame, text="Waiting for connection", font=labelFont)
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
        self.estimatedTime = self.dot_manager.getExportEstimatedTime()
        ttkb.Button(self.frame, text=f'Export data from all dots, estimated time : {round(self.estimatedTime,0)} min', style="my.TButton", command=self.export_all_dots).grid(row=2, column=0, sticky="s")
        self.saveFile = ttkb.Checkbutton(self.frame, text="Save extract in a file (for research)")
        self.saveFile.state(['!alternate'])
        self.saveFile.grid(row=3,column=0,sticky="s")

    def export_all_dots(self):
        for device in self.dotsConnected:
            if device.btDevice.recordingCount() > 0:
                extractEvent = threading.Event()
                if device.exportDataThread(self.saveFile.instate(["selected"]),extractEvent):
                    ExtractingPage(device, self.estimatedTime, extractEvent)

    def run_periodic_background_func(self):
        self.dotPage.make_dot_connection_page(self.dotsConnected)
        self.root.after(1000,self.run_periodic_background_func)