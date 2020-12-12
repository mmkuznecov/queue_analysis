from flask import Flask, render_template, url_for, abort, request
from queue_model import *
import logging
import os
import time

config = configparser.ConfigParser()
config.read("config.ini")
port  = config['Server']['port']
debug = config['Server']['debug'].strip() == 'True'
name  = config['Server']['name']

app = Flask(name)

@app.route('/')
def index():
    s = QueueModel.select()
    return render_template('index.html', Camera1=s[0].id, Camera2=s[1].id, Camera3=s[3].id,
                          Number1=s[0].number_of_people, Number2=s[1].number_of_people,
                          Number3=s[3].number_of_people)

#Возвратит кол-во людей в данной очереди
@app.route('/home/PeopleNumber/<int:number>', methods=['GET'])
def getNearshop(number):
    for i in QueueModel.select():
        if number == i.id:
            amount = i.number_of_people

    return(f"В данной очереди в настоящий момент находится {amount} человек")

if __name__ == '__main__':
    app.run(port=port, debug=debug, host='0.0.0.0')