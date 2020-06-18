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

class FlashlexMessageSender:
    def __init__(self, config, cache):
        self.config = config
        self.cache = cache

    def getFlashLexToken(self, flashlexApiEndpoint, user, password):

        #print("get token", response_user, response_password)
        auth_response = requests.get('{flashlexApiEndpoint}/token'.format(flashlexApiEndpoint=flashlexApiEndpoint), 
            auth=(user, password))

        #print auth_response.json()
        if(auth_response.status_code == 200):        
            rmodel = auth_response.json()
            return rmodel['accessToken']
        else:
            raise ValueError("could not authenticate")

    def sendFlashlexMessageToThing(self, thingId, messageModel, flashlexApiEndpoint, user, password):
        
        # encoding using encode() 
        # then sending to md5() 
        md5_hash = hashlib.md5(json.dumps(messageModel).encode()) 
        
        # add identifiers, we need to remove these and
        # recompute hash on client side
        messageModel['_id'] = str(uuid.uuid4())
        messageModel['_hash'] = md5_hash.hexdigest()

        # check if its in the cache, if missing then send
        if(self.cache.get(messageModel['_hash']) == None):
            self.cache[messageModel['_hash']] = messageModel
            accessToken = self.getFlashLexToken(flashlexApiEndpoint, user, password)
            headers = {'Authorization': "Bearer {0}".format(accessToken), 'Content-Type':"application/jsom"}
            publish_response = requests.post(
                '{flashlexApiEndpoint}/things/{thingId}/publish'.format(flashlexApiEndpoint=flashlexApiEndpoint, thingId=thingId), 
                data=json.dumps(messageModel), 
                headers=headers)
            print("sending to thing:{0} message:{1} response from flashlex:{2}".format(thingId, json.dumps(messageModel), publish_response.status_code))
        else:
            print("found message in cache", messageModel['_hash'])

    def send(self, messageModel):
        self.sendFlashlexMessageToThing(
            self.config['thingId'], 
            messageModel, 
            self.config['apiEndpoint'],
            self.config['user'],
            self.config['password'])

