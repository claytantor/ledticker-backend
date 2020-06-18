
import sys, os
import requests
import json
import yaml
import argparse
import schedule
import time
import math
import datetime
import pytz
import hashlib
import uuid

from senders import FlashlexMessageSender

def getWeatherInfo(zip, url, appid): 
    params_model = {'zip': zip, 'APPID': appid}
    r = requests.get(url, params=params_model)

    response_model = {}
    if r.status_code == 200:
        response_model = r.json()

    return r.status_code, response_model

def Kelvin2Fahrenheit(temp_kelvin):
    return int(math.ceil(((temp_kelvin-273.15)*9.0/5.0)+32.0))

def elapsed_hours_readable(seconds_elapsed):
    hours, rem = divmod(seconds_elapsed, 3600)
    return '{0} hours'.format(int(math.ceil(hours)))

def weather(builder_config, sender_config, cache, tz):    
    print('running weather job')

    status_code, response_model = getWeatherInfo(
        builder_config['zip'], 
        builder_config['data_url'],  
        builder_config['appid'])

    if status_code == 200:
        condition = ' & '.join(list(map(lambda x: x['main'], response_model['weather'])))

        temperature = int(math.ceil(Kelvin2Fahrenheit(response_model['main']['temp'])))

        print ("got weather: {0} {1}".format(condition, temperature))
        # {"body": "Rain & Mist|42|F", "color": "#aa00ff", "elapsed": 20.0, "behavior": "current", "type": "weather"}
        messageModel = {
            'body':'{0}|{1}|F'.format(condition, temperature),
            'type':'weather',
            'behavior': 'current',
            'color':"#eebb00",
            'elapsed': 20.0
        }
    
        if(sender_config['type'] == "FlashlexSender"):
            sender = FlashlexMessageSender(sender_config, cache)
            sender.send(messageModel)


def forecast(builder_config, sender_config, cache, tz):
    print("running forecast job.")


    status_code, response_model = getWeatherInfo(
        builder_config['zip'], 
        builder_config['data_url'],  
        builder_config['appid'])

    forcast24_delta = datetime.timedelta(days=1)
    current_time_utc = datetime.datetime.utcnow()
    forcast_24_time = current_time_utc + forcast24_delta

    temp_max_k = 0
    temp_min_k = 400

    if status_code == 200:

        weather_items = []

        for item in response_model['list']:
            if item['dt'] > 0 and datetime.datetime.utcfromtimestamp(item['dt']) < forcast_24_time:

                current_time_utc = datetime.datetime.utcfromtimestamp(item['dt'])
                utc_tz = pytz.timezone('UTC')
                la_tz = pytz.timezone('America/Los_Angeles')
                current_time_pst = utc_tz.localize(current_time_utc).astimezone(la_tz)

                if item['main']['temp_min']<temp_min_k:
                    temp_min_k = item['main']['temp_min']

                if item['main']['temp_max']>temp_max_k:
                    temp_max_k = item['main']['temp_max']

                weather_items.extend(list(map(lambda x: x['main'], item['weather'])))

        set_weather = set(weather_items)
        condition = ' & '.join(set_weather)

        messageModel = {
            'body':'{0}|{1}|{2}|F|{3}'.format(
                condition,
                Kelvin2Fahrenheit(temp_max_k),
                Kelvin2Fahrenheit(temp_min_k),
                elapsed_hours_readable(forcast24_delta.total_seconds())),
            'type':'weather',
            'behavior': 'forecast',
            'color':"#cc00ff",
            'elapsed': 20.0 
        }

        if(sender_config['type'] == "FlashlexSender"):
            sender = FlashlexMessageSender(sender_config, cache)
            sender.send(messageModel)

    