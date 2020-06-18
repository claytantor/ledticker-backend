import sys, os
import argparse
import pytz

from expiringdict import ExpiringDict

from utils import loadConfig
from builders import wikicovid

cache = ExpiringDict(max_len=20, max_age_seconds=1000)

def main(argv):
    parser = argparse.ArgumentParser()

    parser.add_argument("-c", "--config", action="store", required=True, dest="config", help="the YAML configuration file")

    args = parser.parse_args()
    configFile = args.config

    config = loadConfig(args.config)['ledtickerbe']

    local_tz = pytz.timezone(config['timezone'])

    covid_us_summary_config = list(filter(lambda x: 'wikicovid.covid_us_summary' in x['builder'], config['jobs']))

    wikicovid.covid_us_summary(covid_us_summary_config[0],config['sender'], cache, local_tz)



if __name__ == "__main__":
    main(sys.argv[1:])

