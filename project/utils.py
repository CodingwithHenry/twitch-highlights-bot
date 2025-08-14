import os
from dotenv import load_dotenv
import datetime as dt
load_dotenv()
import re
client_id = os.environ['CLIENT_ID']
client_secret = os.environ['CLIENT_SECRET']

def safe_filename(title):
    # Replace any non-alphanumeric or underscore/dash with underscore
    filename = re.sub(r'[^A-Za-z0-9_\-]', '_', title)
    # Optionally limit length to avoid OS path limits
    return filename[:100].lower()


def parsetime_rfc(datetime_object):
    return dt.datetime.strftime(datetime_object, '%Y-%m-%dT%H:%M:%SZ')

def parsetime_dBY(datetime_object):
    return dt.datetime.strftime(datetime_object, '%d %B, %Y')

prev_week_saturday_rfc = parsetime_rfc(dt.datetime.today().replace(hour=22, minute=0, second=0))
prev_week_sunday_rfc = parsetime_rfc((dt.datetime.today()- dt.timedelta(0)).replace(hour = 10, minute = 0, second= 0))

prev_week_saturday_dBY = parsetime_dBY(dt.datetime.today().replace(hour=22, minute=0, second=0))
prev_week_sunday_dBY = parsetime_dBY((dt.datetime.today() - dt.timedelta(0)).replace(hour=10, minute=0, second=0))