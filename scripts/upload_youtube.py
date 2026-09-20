import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

VIDEO_PATH = "output/easydubber_visual_tagalog_episode.mp4"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload"
]

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

request = youtube.videos().insert(
    part="snippet,status",
    body={
        "snippet": {
            "title": "EasyDubber Tagalog Episode",
            "description": (
                "A cinematic Tagalog-dubbed episode "
                "created automatically by EasyDubber."
            ),
            "tags": [
                "EasyDubber",
                "Tagalog",
                "TagalogDub",
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

print()
print("======================================")
print("YOUTUBE UPLOAD SUCCESS")
print("======================================")
print()
print("VIDEO ID:", response["id"])
print()
print("https://www.youtube.com/watch?v=" + response["id"])
