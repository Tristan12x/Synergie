import tkinter as tk
import ttkbootstrap as ttkb
from tkinter.font import BOLD, Font
from typing import List

from core.utils.DotDevice import DotDevice

class DotPage(ttkb.Frame):
    def __init__(self, parent, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        self.parent = parent
        self.frame = ttkb.Frame(self.parent)

    def make_dot_connection_page(self, dotsconnected : List[DotDevice]) -> None:
        self.frame.destroy()
        self.frame = ttkb.Frame(self.parent)
        self.frame.grid_rowconfigure(0, weight=1)
        self.frame.grid_rowconfigure(1, weight=1)
        self.frame.grid_rowconfigure(2, weight=1)
        self.frame.grid_rowconfigure(3, weight=1)
        for i,device in enumerate(dotsconnected):
            self.frame.grid_columnconfigure(i, weight=1, pad=50)
            label = tk.Label(self.frame, image=device.currentImage)
            label.grid(row=0, column=i)
            if device.isCharging(): 
                charging = "Yes" 
            else: 
                charging = "No"
            labelFont = Font(self.frame, size=15, weight=BOLD)
            tk.Label(self.frame, text=f"Charging : {charging}", font=labelFont).grid(row=1, column=i, sticky="w")
            tk.Label(self.frame, text=f"Battery : {device.batteryLevel()}%", font=labelFont).grid(row=2, column=i, sticky="w")
            if device.recordingCount() == -1: 
                recording = "recording" 
            else: 
                recording = device.recordingCount()
            tk.Label(self.frame, text=f"Number of records : {recording}", font=labelFont).grid(row=3, column=i, sticky="w")
        self.frame.grid(sticky="nsew")
