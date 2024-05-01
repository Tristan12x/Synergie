import tkinter as tk
import numpy as np

from core.database.DatabaseManager import DatabaseManager, SkaterData
from front.TrainingPage import TrainingPage

class SkaterPage:
    def __init__(self, skaters : list[SkaterData], db_manager : DatabaseManager):
        self.db_manager = db_manager
        self.skaters = skaters
        self.frame = tk.Frame()
        tk.Label(self.frame, text='Page 1').grid(row=2, column=10)
        tk.Button(self.frame, text='Go to Main Page',
                  command=self.return_main_page).grid(row=2, column=10)
        
    def create_page(self, main):
        self.main = main
        self.create_skater_button()
        self.frame.grid()

    def return_main_page(self):
        self.frame.grid_forget()
        self.main.grid()

    def create_skater_button(self):
        n = len(self.skaters)
        sep = n//2 + n%2
        for i,skater in enumerate(self.skaters):
            SkaterButton(self.frame, skater, i//sep, i%sep, self.db_manager)


class SkaterButton:
    def __init__(self, frame, skater : SkaterData, row : int, column : int, db_manager : DatabaseManager):
        self.db_manager = db_manager
        tk.Button(frame, text=skater.skater_name, command=lambda : self.change_page(frame, skater.skater_id)).grid(row=row, column=column, padx=5)

    def change_page(self, frame, skater_id : int):
        frame.grid_forget()
        trainings = self.db_manager.load_skater_data(skater_id)
        TrainingPage(trainings, self.db_manager).create_page(frame)