from typing import List
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import firebase_admin.firestore

from dataclasses import dataclass
from datetime import datetime

@dataclass
class JumpData:
    jump_id : int
    training_id : int
    jump_type : int
    jump_rotations : float
    jump_success : bool
    jump_time : int
    jump_max_speed : float
    jump_length : float

    def to_dict(self):
        return {"training_id" : self.training_id,
         "jump_type" : self.jump_type,
         "jump_rotations" : self.jump_rotations,
         "jump_success" : self.jump_success,
         "jump_time" : self.jump_time,
         "jump_max_speed" : self.jump_max_speed,
         "jump_length" : self.jump_length}

@dataclass
class TrainingData:
    training_id : int
    skater_id : int
    training_date : datetime
    dot_id : str

    def to_dict(self):
        return {"skater_id" : self.skater_id,
         "training_date" : self.training_date,
         "dot_id" : self.dot_id}

@dataclass
class SkaterData:
    skater_id : int
    skater_name : str

    def to_dict(self):
        return {"skater_name" : self.skater_name}

class DatabaseManager:
    def __init__(self):
        cred = credentials.Certificate('s2m-skating-firebase-adminsdk-3ofmb-8552d58146.json')
        try:
            firebase_admin.initialize_app(cred)
        except :
            pass
        self.db = firestore.client()

    def save_skater_data(self, data : SkaterData) -> int:
        add_time, new_ref = self.db.collection("skaters").add(data.to_dict())
        return new_ref.id
    
    def save_training_data(self, data : TrainingData) -> int:
        add_time, new_ref = self.db.collection("trainings").add(data.to_dict())
        return new_ref.id
    
    def save_jump_data(self, data : JumpData) -> int:
        add_time, new_ref = self.db.collection("jumps").add(data.to_dict())
        return new_ref.id

    def load_skater_data(self, skater_id : int) -> list[TrainingData]:
        data_trainings = []
        for training in self.db.collection("trainings").where(filter=firestore.firestore.FieldFilter("skater_id", "==", skater_id)).order_by("training_date").stream():
            data_trainings.append(TrainingData(training.id, training.get("skater_id"), training.get("training_date"), 0))
        return data_trainings

    def load_training_data(self, training_id : int) -> list[JumpData]:
        data_jumps = []
        for jump in self.db.collection("jumps").where(filter=firestore.firestore.FieldFilter("training_id", "==", training_id)).order_by("jump_time").stream():
            data_jumps.append(JumpData(jump.id, jump.get("training_id"), jump.get("jump_type"), jump.get("jump_rotations"), jump.get("jump_success"), jump.get("jump_time")))
        return data_jumps
    
    def get_skater_from_training(self, training_id : int) -> str:
        skater_id = self.db.collection("trainings").document(training_id).get().get("skater_id")
        return skater_id

    def get_skater_name_from_id(self, skater_id : str) -> str:
        skater_name = self.db.collection("skaters").document(skater_id).get().get("skater_name")
        return skater_name

    def get_skater_id_from_name(self, skater_name : str) -> str:
        skater_id  = self.db.collection("skaters").where(filter=firestore.firestore.FieldFilter("skater_name", "==", skater_name)).get()
        return skater_id
    
    def get_all_skaters(self) -> list[SkaterData]:
        data_skaters = []
        for skater in self.db.collection("skaters").stream():
            data_skaters.append(SkaterData(skater.id, skater.get("skater_name")))
        return data_skaters
    
    def delete_skater_data(self, skater_id : int) -> None:
        self.db.collection("skaters").document(skater_id).delete()
    
    def set_training_date(self, training_id, date) -> None:
        self.db.collection("trainings").document(training_id).update({"training_date" : date})

    def set_current_record(self, device_id, current_record) -> None:
        self.db.collection("dots").document(device_id).update({"current_record" : current_record})

    def get_current_record(self, device_id) -> str:
        return self.db.collection("dots").document(device_id).get().get("current_record")

    def get_bluetooth_address(self, device_list : List[str]) -> List[str]:
        bluetooth_list = []
        for device in device_list:
            bluetooth_list.append(self.db.collection("dots").document(device).get().get("bluetooth_address"))
        return bluetooth_list

    def get_tag(self, deviceId):
        return self.db.collection("dots").document(deviceId).get().get("tag_name")
    
    def get_dot_from_bluetooth(self, bluetoothAddress):
        dots =  self.db.collection("dots").where(filter=firestore.firestore.FieldFilter("bluetooth_address", "==", bluetoothAddress)).get()
        if len(dots) > 0:
            return dots[0]
        else:
            return None
        
    def save_dot_data(self, deviceId : str, bluetoothAddress : str, tagName : str) -> None:
        newDot = {"bluetooth_address" : bluetoothAddress,
                  "current_record" : "0",
                  "tag_name" : tagName}
        self.db.collection("dots").add(document_data=newDot, document_id=deviceId)