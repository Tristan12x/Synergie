import time
from PIL import Image, ImageTk
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

        threading.Thread(target=self.initialize, daemon=True).start()

    def initialize(self):
        self.dot_manager.firstConnection()

        self.mainPage.dotsConnected = self.dot_manager.getDevices()
        self.mainPage.make_dot_page()

        usb_detection_thread = threading.Thread(target=self.checkUsbDots, args=())
        usb_detection_thread.daemon = True
        usb_detection_thread.start()

    def checkUsbDots(self):
        while True:
            checkUsb = self.dot_manager.checkDevices()
            lastConnected = checkUsb[0]
            lastDisconnected = checkUsb[1]
            if lastConnected:
                print("Connection")
                for device in lastConnected:
                    event = threading.Event()
                    StopingPage(device, event)
                    event.wait()
            if lastDisconnected:
                print("Deconnection")
                for device in lastDisconnected:
                    event = threading.Event()
                    StartingPage(device, self.db_manager, event)
                    event.wait()
            time.sleep(0.2)

root = ttkb.Window(title="Synergie", themename="minty")
myapp = App(root)
width= root.winfo_screenwidth()               
height= root.winfo_screenheight()               
root.geometry("%dx%d" % (width, height))
ico = Image.open('Logo_synergie.png')
photo = ImageTk.PhotoImage(ico)
root.wm_iconphoto(False, photo)
root.mainloop()
