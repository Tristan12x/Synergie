import time
import tkinter as tk
import threading
import os
import numpy as np

from core.data_treatment.data_generation.exporter import export
from core.database.DatabaseManager import *
from core.utils.dotManager import DotManager
from core.utils.dotUsbManager import DotUsbManager
from front.MainPage import MainPage
from core.utils.dotBluetoothManager import DotBluetoothManager

from movelladot_pc_sdk.movelladot_pc_sdk_py39_64 import XsDotUsbDevice, XsDotDevice

class App:

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.dot_manager = DotManager(self.db_manager)
        while self.dot_manager.checkFirstConnection():
            self.dot_manager.initialise()

        usb_detection_thread = threading.Thread(target=self.checkUsbDots, args=())
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
                #TODO Ouvrir fenêtre de confirmation pour lancer un record
                self.dot_manager.bluetooth.stopRecordDots(lastConnected)
                self.dot_manager.usb.showExportData(lastConnected)
            if lastDisconnected:
                print("Deconnection")
                unconnectedDots = self.dot_manager.bluetooth.findUnconnectedDotsId(lastDisconnected)
                self.dot_manager.bluetooth.reconnectDots(unconnectedDots) 
                #TODO Ouvrir fenêtre de confirmation pour arrêter un record
                #TODO Ouvrir fenêtre de confirmation pour exporter les données
                """Ouvrir une fenêtre avec tag du dot et boutons pour chaque skater, lors de l'appui, la fenêtre renvoie un
                lien entre dot et skater
                """
                self.dot_manager.bluetooth.startRecordDots(lastDisconnected)
            time.sleep(1)

""" root = tk.Tk()
myapp = App(root)
root.geometry("1000x400")
root.mainloop() """

App()