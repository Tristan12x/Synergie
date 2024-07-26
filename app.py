import time
import ttkbootstrap as ttkb
import threading

from core.data_treatment.data_generation.exporter import export
from core.database.DatabaseManager import *
from core.utils.dotManager import DotManager
from front.StartingPage import StartingPage
from front.StopingPage import StopingPage
from front.MainPage import MainPage

class App:

    def __init__(self, root):
        self.db_manager = DatabaseManager()
        self.dot_manager = DotManager(self.db_manager)
        self.root = root

        self.mainPage = MainPage([], self.dot_manager, self.db_manager, self.root)

        threading.Thread(target=self.initialise, daemon=True).start()

    def initialise(self):
        while self.dot_manager.checkFirstConnection():
            self.dot_manager.initialise()

        self.mainPage.dotsConnected = self.dot_manager.bluetooth.getConnectedBluetoothDots()
        self.mainPage.make_dot_page()

        usb_detection_thread = threading.Thread(target=self.checkUsbDots, args=())
        usb_detection_thread.daemon = True
        usb_detection_thread.start()

    def checkUsbDots(self):
        while True:
            checkUsb = self.dot_manager.usb.checkUsbConnection()
            lastConnected = checkUsb[0]
            lastDisconnected = checkUsb[1]
            if lastConnected:
                print("Connection")
                unconnectedDots = self.dot_manager.bluetooth.findUnconnectedDotsId(lastConnected)
                self.dot_manager.bluetooth.reconnectDots(unconnectedDots)
                for deviceId in lastConnected:
                    event = threading.Event()
                    StopingPage(deviceId, self.dot_manager, self.db_manager, event)
                    event.wait()
            if lastDisconnected:
                print("Deconnection")
                unconnectedDots = self.dot_manager.bluetooth.findUnconnectedDotsId(lastDisconnected)
                self.dot_manager.bluetooth.reconnectDots(unconnectedDots) 
                for deviceId in lastDisconnected:
                    event = threading.Event()
                    StartingPage(deviceId, self.dot_manager, self.db_manager, event)
                    event.wait()
            time.sleep(0.2)

root = ttkb.Window(title="Synergie", themename="minty")
myapp = App(root)
width= root.winfo_screenwidth()               
height= root.winfo_screenheight()               
root.geometry("%dx%d" % (width, height))
root.mainloop()