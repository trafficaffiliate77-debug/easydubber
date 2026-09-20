import os
import json

import firebase_admin
from firebase_admin import credentials, firestore

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


VIDEO_PATH = "output/easydubber_visual_tagalog_episode.mp4"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload"
]


# ============================================================
# FIREBASE
# ============================================================

service_account_json = os.environ.get(
    "FIREBASE_SERVICE_ACCOUNT"
)

if not service_account_json:
    raise RuntimeError(
        "FIREBASE_SERVICE_ACCOUNT is missing."
    )

service_account_info = json.loads(
    service_account_json
)

if not firebase_admin._apps:
    cred = credentials.Certificate(
        service_account_info
    )

    firebase_admin.initialize_app(
        cred
    )

db = firestore.client()


# ============================================================
# GET COMPLETED EPISODE
# ============================================================

episodes = (
    db.collection("episodes")
    .where(
        "video_status",
        "==",
        "completed"
    )
    .limit(1)
    .stream()
)

episode_doc = None

for doc in episodes:
    episode_doc = doc
    break


if episode_doc is None:
    raise RuntimeError(
        "No completed episode found."
    )


episode = episode_doc.to_dict()

title = episode.get(
    "title",
    "EasyDubber Episode"
)

description = episode.get(
    "description",
    "A cinematic Tagalog-dubbed episode created automatically by EasyDubber."
)


# ============================================================
# YOUTUBE CREDENTIALS
# ============================================================

client_id = os.environ["YOUTUBE_CLIENT_ID"]

client_secret = os.environ["YOUTUBE_CLIENT_SECRET"]

refresh_token = os.environ["YOUTUBE_REFRESH_TOKEN"]


credentials = Credentials(
    token=None,
    refresh_token=refresh_token,
    token_uri="https://oauth2.googleapis.com/token",
    client_id=client_id,
    client_secret=client_secret,
    scopes=SCOPES
)


youtube = build(
    "youtube",
    "v3",
    credentials=credentials
)


# ============================================================
# UPLOAD
# ============================================================

print()
print("==============================================")
print("UPLOADING TO YOUTUBE")
print("==============================================")
print()

print("Title:", title)

print("Video:", VIDEO_PATH)

print()


request = youtube.videos().insert(
    part="snippet,status",

    body={
        "snippet": {
            "title": title,

            "description": description,

            "tags": [
                "EasyDubber",
                "Tagalog",
                "TagalogDub",
                "Anime",
                "Manga",
                "Shorts"
            ],

            "categoryId": "22"
        },

        "status": {
            "privacyStatus": "private",

            "selfDeclaredMadeForKids": False
        }
    },

    media_body=MediaFileUpload(
        VIDEO_PATH,

        chunksize=-1,

        resumable=True
    )
)


response = None


while response is None:

    status, response = request.next_chunk()

    if status:

        print(
            "Upload progress:",
            int(status.progress() * 100),
            "%"
        )


# ============================================================
# SUCCESS
# ============================================================

video_id = response["id"]

video_url = (
    "https://www.youtube.com/watch?v="
    + video_id
)


print()
print("==============================================")
print("YOUTUBE UPLOAD SUCCESS")
print("==============================================")
print()

print("VIDEO ID:", video_id)

print()

print("VIDEO URL:", video_url)

print()

print("Privacy: PRIVATE")

print()
