from tkinter.font import BOLD, Font
import ttkbootstrap as ttkb

from core.utils.DotDevice import DotDevice

class DotFrame(ttkb.Frame):
    def __init__(self, parent, device : DotDevice, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        self.parent = parent
        self.device = device
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.imageLabel = ttkb.Label(self, image=self.device.currentImage)
        self.imageLabel.grid(row=0, column=0)
        labelFont = Font(self, size=15, weight=BOLD)
        self.pluggedLabel = ttkb.Label(self, text=f"Plugged : {self.device.isPlugged}", font=labelFont)
        self.pluggedLabel.grid(row=1, column=0, sticky="w")
        self.batteryLabel = ttkb.Label(self, text=f"Battery : {self.device.batteryLevel}%", font=labelFont)
        self.batteryLabel.grid(row=2, column=0, sticky="w")
        if self.device.isRecording: 
            recording = "recording" 
        else: 
            recording = self.device.recordingCount
        self.recordsLabel = ttkb.Label(self, text=f"Records stocked : {recording}", font=labelFont)
        self.recordsLabel.grid(row=3, column=0, sticky="w")
        self.recordingLabel = ttkb.Label(self, text=f"Recording : {self.device.isRecording}", font=labelFont)
        self.recordingLabel.grid(row=4, column=0, sticky="w")
        self.grid(row=0, column=0)
    
    def updateDot(self):
        self.imageLabel.configure({"image" : self.device.currentImage})
        self.pluggedLabel.configure({"text" : f"Plugged : {self.device.isPlugged}"})
        self.batteryLabel.configure({"text" : f"Battery : {self.device.batteryLevel}%"})
        if self.device.isRecording:
            recording = "recording" 
        else: 
            recording = self.device.recordingCount
        self.recordsLabel.configure({"text" : f"Number of records : {recording}"})
        self.recordingLabel.configure({"text" : f"Recording : {self.device.isRecording}"})