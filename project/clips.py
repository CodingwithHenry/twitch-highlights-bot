import time
import requests
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from project.twitch_api import TwitchAPI
from project.utils import client_id, client_secret, prev_week_saturday_rfc, prev_week_sunday_rfc, safe_filename
from project.twitch_ids_box_art import games_id
from project.clipSelector import classify_clip
import re





api = TwitchAPI()
api.auth(client_id, client_secret)



class ClipContent:
    def __init__(self, url, broadcaster_id, broadcaster_name, game_id, title, thumbnail_url, duration, view_count, path):
        self.url = url
        self.broadcaster_id = broadcaster_id
        self.broadcaster_name = broadcaster_name
        self.game_id = game_id
        self.title = title
        self.thumbnail_url = thumbnail_url
        self.duration = duration
        self.view_count = view_count
        self.path = path
    
    def __str__(self):
        return f'url: {self.url}\nbroadcaster_id: {self.broadcaster_id}\nbroadcaster_name: {self.broadcaster_name}\ngame_id: {self.game_id}\ntitle: {self.title}\nthumbnail_url: {self.thumbnail_url}'

class ClipsExtractor:
    def __init__(self):
        self.clips_content = []
        self.by_game = None
        
    def bannedStreamer(streamerName: str):
        if streamerName in ['k4sen', 'fps_shaka']:
            return False
        return True

    def get_clips(self, quantity = 10, broadcaster_id = None, game_id = None, languages = []):
        self.by_game = True if game_id else False
        self.languages = languages
        params = {
            'broadcaster_id' : broadcaster_id,
            'game_id' : game_id,
            'first' : quantity,
            'started_at' : prev_week_sunday_rfc,
            'ended_at' : prev_week_saturday_rfc,
            'after' : None
        }

        while len(self.clips_content) < quantity:
            response = requests.get('https://api.twitch.tv/helix/clips', params=params, headers=api.headers).json()
            for clip in response['data']:
                if (clip['language'] in languages or languages == []) and ClipsExtractor.bannedStreamer(clip['broadcaster_name']):
                    self.clips_content.append(ClipContent(
                        clip['url'],
                        clip['broadcaster_id'],
                        clip['broadcaster_name'],
                        clip['game_id'],
                        clip['title'],
                        clip['thumbnail_url'],
                        clip['duration'],
                        clip["view_count"],
                        f'files/clips/{safe_filename(clip["title"])}.mp4'
                    ))
                    if len(self.clips_content) == quantity: break
            params['after'] = response['pagination']['cursor']

class ClipsDownloader():
    def __init__(self):
        pass

    def download_clip_driver(self, clip):
        option = Options()
        option.add_argument("--headless=new")          # headless mode
        option.add_argument("--no-sandbox")            # required on Linux
        option.add_argument("--disable-dev-shm-usage") # avoid /dev/shm issues
 
        option.add_argument("--disable-gpu")  # already in your options
        option.add_argument("--enable-unsafe-swiftshader")  # optional, safe to add
        # Use a temporary user data directory to avoid conflicts
       
        if os.path.exists(clip.path):
           return  # Skip download if file already exists

        driver = webdriver.Chrome(options=option)
        driver.get(clip.url)
        time.sleep(1)  # Allow the page to load

        clip_url = WebDriverWait(driver, 10).until( EC.presence_of_element_located((By.TAG_NAME, "video"))).get_property("src")
        driver.quit()
        r = requests.get(clip_url)

        if r.headers['Content-Type'] == 'binary/octet-stream' or r.headers['Content-Type'] == 'video/mp4':
            if not os.path.exists('files/clips'):
                os.makedirs('files/clips')

            with open(clip.path, 'wb') as f:
                f.write(r.content)
            
                
        else:
            print(f'Failed to download clip from thumb: {clip.thumbnail_url}')

    def download_clip_thumb(self, clip):
        index = clip.thumbnail_url.find('-preview')
        clip_url = clip.thumbnail_url[:index] + '.mp4'

        r = requests.get(clip_url)
        if r.headers['Content-Type'] == 'binary/octet-stream':
            if not os.path.exists('files/clips'): os.makedirs('files/clips')
            with open(f'files/thumbnails/{safe_filename(clip.title)}.jpg', 'wb') as f:
                f.write(r.content)
        else:
            print(f'Failed to download clip from thumb: {clip.thumbnail_url}')
    
    def download_top_clips(self, clips):
        for i in range(len(clips)):
            print(f'Downloading clip {i+1}/{len(clips)}')
            clip = clips[i]
            if clip.thumbnail_url.find('clips-media-assets2.twitch.tv') != -1:
                self.download_clip_thumb(clip)
            else:
                self.download_clip_driver(clip)
                
        for clip in clips:
                if os.path.exists(clip.path):
                    classification = classify_clip('clip_classifier_3d.pth', clip.path, 20)
                    if classification == 0:
                        print(f'Removed clip: {clip.title} (not interesting)')
                        os.remove(clip.path)
                        clips.remove(clip)
            #Not needed right now
            #self.download_thumbnail(clip)
    
    def download_thumbnail(self, clip):
        r = requests.get(clip.thumbnail_url)
        if not os.path.exists('files/thumbnails'): os.makedirs('files/thumbnails')
        try:
            with open(f'files/thumbnails/{safe_filename(clip.title)}.jpg', 'wb') as f:
                f.write(r.content)
        except:
            print(f'Failed to download thumbnail: {clip.thumbnail_url}')