#!/usr/bin/env python3

import os
import sys
import time
import random
import http.client as httplib
import httplib2
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import argparse
from pathlib import Path

THUMBNAIL_PATH = Path("files") / "youtube" / "thumbnail.png"

# HTTP settings
httplib2.RETRIES = 1
MAX_RETRIES = 10
RETRIABLE_EXCEPTIONS = (
    httplib2.HttpLib2Error, IOError, httplib.NotConnected,
    httplib.IncompleteRead, httplib.ImproperConnectionState,
    httplib.CannotSendRequest, httplib.CannotSendHeader,
    httplib.ResponseNotReady, httplib.BadStatusLine
)
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

# API config
CLIENT_SECRETS_FILE = "./client_secrets.json"
YOUTUBE_UPLOAD_SCOPE = ["https://www.googleapis.com/auth/youtube.upload"]
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")


def get_authenticated_service(game):

    if game == 'BATTLEFIELD 6':
        creds = None
        token_file = "bf6_token.pickle"
    if game == 'League of Legends':
        creds = None
        token_file = "lol_token.pickle"

    if os.path.exists(token_file):
        with open(token_file, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, YOUTUBE_UPLOAD_SCOPE)
            creds = flow.run_local_server(port=0)
        with open(token_file, 'wb') as token:
            pickle.dump(creds, token)

    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=creds)

def upload_thumbnail(self, video_id, file_path):
        print('Uploading thumbnail...')
        request = self.youtube.thumbnails().set(
            videoId=video_id,
            media_body=file_path
        )
        response = request.execute()
        print(response)

def initialize_upload(youtube, options, filepath):
    tags = options.keywords.split(",") if options.keywords else None

    body = dict(
        snippet=dict(
            title=options.title,
            description=options.description,
            tags=tags,
            categoryId=options.category_id
        ),
        status=dict(
            privacyStatus=options.privacy_status
        )
    )

    insert_request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=MediaFileUpload(filepath, chunksize=-1, resumable=True)
    )

    # Upload video and get video ID
    video_id = resumable_upload(insert_request, youtube)

    # Upload thumbnail
    if THUMBNAIL_PATH.exists():
        print("Uploading thumbnail...")
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=str(THUMBNAIL_PATH)
        ).execute()
        print("✅ Thumbnail uploaded!")
    else:
        print(f"Thumbnail file not found at {THUMBNAIL_PATH}")

    return video_id

def resumable_upload(insert_request,youtube):
    response = None
    error = None
    retry = 0

    while response is None:
        try:
            print("Uploading file...")
            status, response = insert_request.next_chunk()
            if response is not None:
                if 'id' in response:
                    print(f"Video id '{response['id']}' was successfully uploaded.")
                    return response['id']

                    
                else:
                    sys.exit(f"The upload failed with an unexpected response: {response}")
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                error = f"A retriable HTTP error {e.resp.status} occurred:\n{e.content}"
            else:
                raise
        except RETRIABLE_EXCEPTIONS as e:
            error = f"A retriable error occurred: {e}"

        if error is not None:
            print(error)
            retry += 1
            if retry > MAX_RETRIES:
                sys.exit("No longer attempting to retry.")

            max_sleep = 2 ** retry
            sleep_seconds = random.random() * max_sleep
            print(f"Sleeping {sleep_seconds:.1f} seconds and then retrying...")
            time.sleep(sleep_seconds)
            error = None

def upload(args, filepath, game):
    youtube = get_authenticated_service(game)
    try:
        initialize_upload(youtube, args, filepath)
    except HttpError as e:
        print(f"An HTTP error {e.resp.status} occurred:\n{e.content}")
    
    


def upload_short(self, video_file, game, title="Short Video", description="", tags="#Shorts, #Gaming,Viral,viral shorts , for your, league of legends,lol,pentakill"):
    youtube = get_authenticated_service(game)

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags.split(","),
            "categoryId": "20"  # Gaming category
        },
        "status": {
            "privacyStatus": "public"
        }
    }

    media = MediaFileUpload(video_file)
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )
    response = request.execute()
    print(f"Uploaded Short: {response['id']}")
    return response
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Video file to upload")
    parser.add_argument("--title", help="Video title", default="Test Title")
    parser.add_argument("--description", help="Video description", default="Test Description")
    parser.add_argument("--category", default="22",
                        help="Numeric video category. See https://developers.google.com/youtube/v3/docs/videoCategories/list")
    parser.add_argument("--keywords", help="Video keywords, comma separated", default="")
    parser.add_argument("--privacyStatus", choices=VALID_PRIVACY_STATUSES,
                        default=VALID_PRIVACY_STATUSES[0], help="Video privacy status.")
    args = parser.parse_args()

    if not os.path.exists(args.file):
        sys.exit("Please specify a valid file using the --file= parameter.")

    youtube = get_authenticated_service()
    try:
        initialize_upload(youtube, args, args.file)
    except HttpError as e:
        print(f"An HTTP error {e.resp.status} occurred:\n{e.content}")
