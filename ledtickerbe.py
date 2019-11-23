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

from expiringdict import ExpiringDict
from lxml import etree, html

cache = ExpiringDict(max_len=20, max_age_seconds=600)

def loadConfig():

    # Read in command-line parameters
    parser = argparse.ArgumentParser()

    parser.add_argument("-c", "--config", action="store", required=True, dest="config", help="the YAML configuration file")

    args = parser.parse_args()
    configFile = args.config
    # config = loadConfig(args.config)['ledtickerbe']

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
    
    # encoding using encode() 
    # then sending to md5() 
    md5_hash = hashlib.md5(json.dumps(messageModel).encode()) 
    
    # add identifiers, we need to remove these and
    # recompute hash on client side
    messageModel['_id'] = str(uuid.uuid4())
    messageModel['_hash'] = md5_hash.hexdigest()


    # check if its in the cache, if missing then send
    if(cache.get(messageModel['_hash']) == None):
        cache[messageModel['_hash']] = messageModel
        accessToken = getFlashLexToken(flashlexApiEndpoint, user, password)
        headers = {'Authorization': "Bearer {0}".format(accessToken), 'Content-Type':"application/jsom"}
        publish_response = requests.post(
            '{flashlexApiEndpoint}/things/{thingId}/publish'.format(flashlexApiEndpoint=flashlexApiEndpoint, thingId=thingId), 
            data=json.dumps(messageModel), 
            headers=headers)
        print("sending to thing:{0} message:{1} response from flashlex:{2}".format(thingId, json.dumps(messageModel), publish_response.status_code))
    else:
        print("found message in cache", messageModel['_hash'])


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

    config = loadConfig()['ledtickerbe']

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
            'color':"#eebb00",
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

    config = loadConfig()['ledtickerbe']

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



def handleRaceTable(table):
    tree = html.fromstring(etree.tostring(table, pretty_print=True).decode("utf-8"))
    pval = tree.xpath('//p[@style="font-size: 55pt; margin-bottom:-10px"]/text()')
    # print(pval)
    ival = tree.xpath('//img[@width="100"]/@src')
    # print(ival)

    items = []
    for i in range(len(ival)):
        name = ival[i].replace("/","").replace(".png","")
        percent = round(float(pval[i].replace("%",""))/100.0, 4)
        items.append({'name':name,'value':percent})
    
    return items


def filterDemocratic(bets): 
    if('Democratic' in bets['name']):
        return True
    else:
        return False
    # letters = ['a', 'e', 'i', 'o', 'u'] 
    # if (variable in letters): 
    #     return True
    # else: 
    #     return False

def parseRaces(tree):
    tables = tree.xpath('//div[@class="container"]/table')
    # print(tables)
    races = []
    for i in range(len(tables)):
        items = handleRaceTable(tables[i])
        if(i==0):
            races.append({"name":"Democratic Primary", "rankings": items})
        if(i==1):
            races.append({"name":"Presidential Election", "rankings": items})
        if(i==2):
            races.append({"name":"Republican Primary", "rankings": items})

    return races


def cronElectionBets():

    print('getting election bets')

    config = loadConfig()['ledtickerbe']

    page = requests.get(config['electionbettingods']['url_main'])
    tree = html.fromstring(page.content)
    races = parseRaces(tree)

    items = filter(filterDemocratic, races)

#    {
#       "name": "Republican Primary",
#       "rankings": [
#          {
#             "name": "Trump",
#             "value": 0.784
#          },
    for race in items:
        
        first = race['rankings'][0]
        name = first['name']
        percentage = "{:.0%}".format(first['value'])
        messageModel = {
                'body':'{0}|{1}|'.format(name, percentage),
                'type':'weather',
                'behavior': 'current',
                'color':"#4287f5",
                'elapsed': 20.0
            }

        sendFlashlexMessageToThing(
            config['flashlex']['thingId'], 
            messageModel, 
            config['flashlex']['apiEndpoint'],
            config['flashlex']['user'],
            config['flashlex']['password'])


# ======================================
def main(argv):
    print("starting ledticker backend with flashlex.")

    config = loadConfig()['ledtickerbe']
    
    schedule.every(config['jobs']['cronWeather']['rate']).minutes.do(cronWeather)
    schedule.every(config['jobs']['cronForecast']['rate']).minutes.do(cronForecast)
    schedule.every(config['jobs']['cronElectionBets']['rate']).minutes.do(cronElectionBets)

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main(sys.argv[1:])
