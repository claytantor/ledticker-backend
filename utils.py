import yaml


def loadConfig(configFile):
 
    # # Read in command-line parameters
    # parser = argparse.ArgumentParser()

    # parser.add_argument("-c", "--config", action="store", required=True, dest="config", help="the YAML configuration file")

    # args = parser.parse_args()
    # configFile = args.config
    # # config = loadConfig(args.config)['ledtickerbe']

    cfg = None
    with open(configFile, 'r') as ymlfile:
        cfg = yaml.load(ymlfile, Loader=yaml.FullLoader)
    return cfg