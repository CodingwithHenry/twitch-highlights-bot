import os
from dotenv import load_dotenv
import datetime as dt
load_dotenv()
import re
import json
import random
import platform

# Detect OS
if platform.system() == "Windows":
    UPLOADS = True
else:
    UPLOADS = True

client_id = os.environ['CLIENT_ID']
client_secret = os.environ['CLIENT_SECRET']


def get_description(twitchgame: str):

    gameconverter={'BATTLEFIELD 6':'bf','League of Legends':'lol'}
    
    game=gameconverter[twitchgame]

    description=''
    tags = set()
    title=''
    with open("description.json", "r", encoding="utf-8") as f:
        data = dict(json.load(f))
        
        # increases counter for video number
        data[game]['counter']+=1
        with open("description.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)


        
        description = data[game]['description'].replace('{n}', str(data[game]['counter']))
        tags = set(data[game]['tags'])
        return  description, tags


def getShortNumber(twitchgame: str):
    gameconverter={'BATTLEFIELD 6':'bf','League of Legends':'lol'}
    
    game=gameconverter[twitchgame]

    
    with open("description.json", "r", encoding="utf-8") as f:
        data = dict(json.load(f))
        
        # increases counter for video number
        data[game]['shortcounter']+=1
        with open("description.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    
    return data[game]['shortcounter']

def safe_filename(title):
    # Replace any non-alphanumeric or underscore/dash with underscore
    filename = re.sub(r'[^A-Za-z0-9_\-]', '_', title)
    # Optionally limit length to avoid OS path limits
    return filename[:100].lower()

def parsetime_rfc(datetime_object):
    return dt.datetime.strftime(datetime_object, '%Y-%m-%dT%H:%M:%SZ')

def parsetime_dBY(datetime_object):
    return dt.datetime.strftime(datetime_object, '%d %B, %Y')

prev_week_saturday_rfc = parsetime_rfc((dt.datetime.today()- dt.timedelta(0)).replace(hour = 9, minute = 00, second= 0))

prev_week_sunday_rfc = parsetime_rfc((dt.datetime.today()- dt.timedelta(3)).replace(hour = 9, minute = 00, second= 0))

prev_week_saturday_dBY = parsetime_dBY((dt.datetime.today()- dt.timedelta(0)).replace(hour=9, minute=00, second=0))
prev_week_sunday_dBY = parsetime_dBY((dt.datetime.today() - dt.timedelta(3)).replace(hour=9, minute=00, second=0))

