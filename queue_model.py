from peewee import *
import configparser

db = SqliteDatabase('QueuesDB.db')

class QueueModel(Model):
    id = IntegerField()
    camera_url = CharField()
    mask_path = CharField()
    number_of_people = IntegerField()
    last_update_time = IntegerField()

    class Meta:
        database = db

def update_info(qid:int, n:int, t:int):
    queue = QueueModel.get(QueueModel.id == qid)
    queue.number_of_people = n
    queue.last_update_time = t
    queue.save()
    
if __name__ == '__main__':
    QueueModel.create_table()