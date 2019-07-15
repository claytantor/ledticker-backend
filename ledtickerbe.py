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

config = {}

def loadConfig(configFile):
    cfg = None
    with open(configFile, 'r') as ymlfile:
        cfg = yaml.load(ymlfile, Loader=yaml.FullLoader)
    return cfg

def getFlashLexToken(flashlexApiEndpoint, user, password):

    #print("get token", response_user, response_password)
    auth_response = requests.get('{flashlexApiEndpoint}/token'.format(flashlexApiEndpoint=flashlexApiEndpoint), 
        auth=(user, password))

    #print auth_response.json()
    if(auth_response.status_code == 200):        
        rmodel = auth_response.json()
        return rmodel['accessToken']
    else:
        raise ValueError("could not authenticate")

def sendFlashlexMessageToThing(thingId, messageModel, flashlexApiEndpoint, user, password):
    accessToken = getFlashLexToken(flashlexApiEndpoint, user, password)
    headers = {'Authorization': "Bearer {0}".format(accessToken), 'Content-Type':"application/jsom"}
    publish_response = requests.post(
        '{flashlexApiEndpoint}/things/{thingId}/publish'.format(flashlexApiEndpoint=flashlexApiEndpoint, thingId=thingId), 
        data=json.dumps(messageModel), 
        headers=headers)
    print("sending to thing:{0} message:{1} response from flashlex:{2}".format(thingId, json.dumps(messageModel), publish_response.status_code))

def Kelvin2Fahrenheit(temp_kelvin):
    #return ((temp_kelvin-273.15)*9.0/5.0)+32.0
    return int(math.ceil(((temp_kelvin-273.15)*9.0/5.0)+32.0))

def elapsed_hours_readable(seconds_elapsed):
    hours, rem = divmod(seconds_elapsed, 3600)
    return '{0} hours'.format(int(math.ceil(hours)))

def getWeatherInfo(zip, url, appid):
    params_model = {'zip': zip, 'APPID': appid}
    r = requests.get(url, params=params_model)

    response_model = {}
    if r.status_code == 200:
        response_model = r.json()

    return r.status_code, response_model

# curl -X GET \
#   'http://api.openweathermap.org/data/2.5/weather?zip=97206,us&APPID=' \
#   -H 'cache-control: no-cache'
def cronWeather():

    print("getting the current weather.")
    print(json.dumps(config))
    print(json.dumps(config['weather']['zip']))
    status_code, response_model = getWeatherInfo(
        config['weather']['zip'], 
        config['weather']['url_weather'],  
        config['weather']['appid'])

    if status_code == 200:
        condition = ' & '.join(list(map(lambda x: x['main'], response_model['weather'])))

        temperature = int(math.ceil(Kelvin2Fahrenheit(response_model['main']['temp'])))

        print ("got weather: {0} {1}".format(condition, temperature))
        # {"body": "Rain & Mist|42|F", "color": "#aa00ff", "elapsed": 20.0, "behavior": "current", "type": "weather"}
        messageModel = {
            'body':'{0}|{1}|F'.format(condition, temperature),
            'type':'weather',
            'behavior': 'current',
            'color':"#3366ff",
            'elapsed': 20.0
        }

        # response = send_encoded_message(messageModel, config)
        # thingId, messageModel, flashlexApiEndpoint, user, password
        sendFlashlexMessageToThing(
            config['flashlex']['thingId'], 
            messageModel, 
            config['flashlex']['apiEndpoint'],
            config['flashlex']['user'],
            config['flashlex']['password'])

def cronForecast():

    print("getting the forcasted weather.")

    status_code, response_model = getWeatherInfo(
        config['weather']['zip'], 
        config['weather']['url_forecast'],  
        config['weather']['appid'])

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

        sendFlashlexMessageToThing(
            config['flashlex']['thingId'], 
            messageModel, 
            config['flashlex']['apiEndpoint'],
            config['flashlex']['user'],
            config['flashlex']['password'])

def main(argv):
    print("starting ledticker backend with flashlex.")

    # Read in command-line parameters
    parser = argparse.ArgumentParser()

    parser.add_argument("-c", "--config", action="store", required=True, dest="config", help="the YAML configuration file")

    args = parser.parse_args()
    config = loadConfig(args.config)['ledtickerbe']
    print(json.dumps(config))
    print(config['weather']['zip'])
    
    schedule.every(config['jobs']['cronWeather']['rate']).minutes.do(cronWeather)
    schedule.every(config['jobs']['cronForecast']['rate']).minutes.do(cronForecast)

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main(sys.argv[1:])
