import threading
import tkinter as tk
from typing import List

from core.database.DatabaseManager import DatabaseManager, TrainingData
from core.utils.dotBluetoothManager import DotBluetoothManager
from movelladot_pc_sdk.movelladot_pc_sdk_py39_64 import XsDotDevice

class DotPage(tk.Frame):
    def __init__(self, parent, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        self.frame = tk.Frame()

    def make_dot_connection_page(self, dotsconnected : List[XsDotDevice]) -> None:
        self.frame.destroy()
        self.frame = tk.Frame()
        for i,device in enumerate(dotsconnected):
            tk.Label(self.frame, text=device.deviceTagName()).grid(row=1, column=i)
            tk.Label(self.frame, text=device.isCharging()).grid(row=2, column=i)
            tk.Label(self.frame, text=device.batteryLevel()).grid(row=3, column=i)
        self.frame.grid()
