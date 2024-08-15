import numpy as np
import pandas as pd

import constants
from constants import jumpType,jumpSuccess
import math

class Jump:
    def __init__(self, start: int, end: int, df: pd.DataFrame, jump_type: jumpType = jumpType.NONE, jump_success: jumpSuccess = jumpSuccess.NONE):
        """
        :param start: the frame index where the jump starts
        :param end: the frame index where the jump ends
        :param df: the dataframe containing the session where the jump is
        :param jump_type: the type of the jump (has to be set to NONE before annotation)
        """
        self.start = start
        self.end = end
        self.type = jump_type
        self.success = jump_success

        self.startTimestamp = (df['SampleTimeFine'][start] - df['SampleTimeFine'][0]) / 1000
        self.endTimestamp = (df['SampleTimeFine'][end] - df['SampleTimeFine'][0]) / 1000

        # timestamps are in microseconds, I want to have the lenghs in seconds
        self.length = round(np.longlong(df['ms'][end] - df['ms'][start]) / 1000,3)

        self.rotation = self.calculate_rotation(df[self.start:self.end].copy().reset_index())

        self.df = self.dynamic_resize(df)  # The dataframe containing the jump

        self.max_rotation_speed = round(df['Gyr_X_unfiltered'][start:end].abs().max()/360,1)

    def calculate_rotation(self, df):
        """
        calculates the rotation in degrees around the vertical axis, the initial frame is a frame where the skater is
        standing still
        :param df: the dataframe containing the jump
        :return: the absolute value of the rotation in degrees
        """
        # initial frame is the reference frame, I want to compute rotations around the "Euler_X" axis
        df_rots = df[["SampleTimeFine", "Gyr_X"]]
        def check(s):
            return math.isinf(s["Gyr_X"]) or np.abs(s["Gyr_X"]) > 1e6

        df_rots = df_rots.drop(df_rots[df_rots.apply(check,axis=1)].index)
        n = len(df_rots)

        tps = df_rots['SampleTimeFine'].to_numpy().reshape(1,n)[0]
        tps = tps - tps[0]
        difftps = np.diff(tps)/1e6
        vit = df_rots['Gyr_X'].to_numpy().reshape(1,n)[0][:-1]
        pos = np.nansum(np.array(vit)*np.array(difftps))
        total_rotation_x = np.abs(pos/360)
        return total_rotation_x

    def dynamic_resize(self, df: pd.DataFrame = None):
        """
        normalize the jump to a given time fram. I will need to resample the data so the take-off is at frame 200,
        and landing at frame 300
        :param df: the dataframe containing the session where the jump is
        :param length_between_takeoff_and_reception: the number of frames between the takeoff  and the reception
        The middle of the jump is the beginning (takeoff), middle + length_between_takeoff_and_reception is the reception
        The timeframe should be a resampled version of the original timeframe
        :return: the new dataframe
        """

        begin_df = self.start - 200
        end_df = self.end + 100
        timelapse = np.arange(begin_df,end_df)

        length_min = 100 - (self.end - self.start)
        if length_min > 0:
            resampled_df = df[begin_df:end_df+length_min].copy(deep=True)
        else:
            takeoff_df = df[begin_df:self.start +50].copy(deep=True)
            reception_df = df[self.end-50:end_df].copy(deep=True)
            resampled_df = pd.concat([takeoff_df,reception_df])

        return resampled_df

    def generate_csv(self, path: str):
        """
        exports the jump to a csv file
        :param path:
        :return:
        """
        self.df.to_csv(path, index=False)