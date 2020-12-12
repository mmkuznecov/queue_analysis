from flask import Flask, render_template, url_for
import requests
from flask import abort
from peewee import *


db = SqliteDatabase('AnalisDB.sq')

class CamerasAndQueues(Model):
    id = IntegerField()
    queuesid = IntegerField()
    camerasip = CharField()
    numberofpeople = IntegerField()
    lastupdatetime = CharField()

    class Meta:
        database = db


app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

#Возвратит кол-во людей в данной очереди
@app.route('/home/PeopleNumber/<int:number>', methods=['GET'])
def getNearshop(number):
    for i in CamerasAndQueues.select():
        if number == i.queuesid:
            amount = i.numberofpeople

    return(f"В данной очереди в настоящий момент находится {amount} человек")

if __name__ == '__main__':
    app.run(port=8080, debug = True)
