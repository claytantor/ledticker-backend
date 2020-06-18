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

from datetime import datetime, timedelta
# >>> from pytz import timezone

import hashlib
import uuid

from expiringdict import ExpiringDict
from lxml import etree, html

from builders import openweathermap, electionbettingodds, wikicovid

from utils import loadConfig

cache = ExpiringDict(max_len=20, max_age_seconds=1000)


def empty_job(builder_config, sender_config, tz):
    pass


def make_job(builder_config, sender_config, cache, tz):
    if('openweathermap.weather' in builder_config['builder']):
        return openweathermap.weather(builder_config, sender_config, cache, tz) 
    elif('openweathermap.forecast' in builder_config['builder']):
        return openweathermap.forecast(builder_config, sender_config, cache, tz)
    elif('electionbettingodds.next_president' in builder_config['builder']):
        return electionbettingodds.next_president(builder_config, sender_config, cache, tz) 
    elif('wikicovid.covid_us_summary' in builder_config['builder']):
        return wikicovid.covid_us_summary(builder_config, sender_config, cache, tz)
    else:
        return empty_job(builder_config, sender_config, tz)   

# ======================================  
def main(argv):
    print("starting ledticker backend with flashlex. ")

    # Read in command-line parameters
    parser = argparse.ArgumentParser()

    parser.add_argument("-c", "--config", action="store", required=True, dest="config", help="the YAML configuration file")

    args = parser.parse_args()
    configFile = args.config

    config = loadConfig(args.config)['ledtickerbe']

    local_tz = pytz.timezone(config['timezone'])

    for job_item in config['jobs']:

        if(job_item['rate_type'] == 'day'):
            schedule_gmt = convert_localtime_to_gmt(job_item['rate_value'], local_tz).strftime("%H:%M")
            schedule.every().day.at(schedule_gmt).do(make_job, builder_config=job_item, sender_config=config['sender'], cache=cache, tz=local_tz )
        elif(job_item['rate_type'] == 'hours'):
            schedule.every(job_item['rate_value']).hours.do(make_job, builder_config=job_item, sender_config=config['sender'], cache=cache,tz=local_tz )
        elif(job_item['rate_type'] == 'minutes'):
            schedule.every(job_item['rate_value']).minutes.do(make_job, builder_config=job_item, sender_config=config['sender'], cache=cache,tz=local_tz )    
        else:
            pass
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main(sys.argv[1:])
