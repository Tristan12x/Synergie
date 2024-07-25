import threading
import time
from tkinter.font import BOLD, Font
import ttkbootstrap as ttkb
import tkinter as tk

from core.database.DatabaseManager import DatabaseManager

class ExtractingPage:
    def __init__(self,deviceId : str, db_manager : DatabaseManager, event : threading.Event) -> None:
        self.deviceId = deviceId
        self.db_manager = db_manager
        self.event = event
        self.window = ttkb.Toplevel(title="Confirmation", size=(400,200))
        self.window.grid_columnconfigure(0, weight=1)
        self.window.grid_rowconfigure(0, weight=1)
        self.text = tk.StringVar(self.window, value = f"Extracting data from sensor {self.db_manager.get_tag(self.deviceId)} \nDo not disconnect this sensor")
        self.label = tk.Label(self.window, textvariable=self.text, font=Font(self.window, size=10, weight=BOLD))
        self.label.grid(row=0,column=0)
        self.checkFinish()

    def checkFinish(self):
        if self.event.is_set():
            self.text.set("Extraction finish")
            self.label.update()
            time.sleep(1)
            self.window.destroy()
        self.window.after(1000, self.checkFinish)