import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

service_account = json.loads(
    os.environ["FIREBASE_SERVICE_ACCOUNT"]
)

cred = credentials.Certificate(service_account)

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

episodes = (
    db.collection("episodes")
    .where("status", "==", "pending")
    .limit(1)
    .stream()
)

found = False

for episode in episodes:
    found = True
    data = episode.to_dict()

    print("=== EasyDubber Queue ===")
    print("Document:", episode.id)
    print("Title:", data.get("title"))
    print("Prompt:", data.get("prompt"))
    print("Status:", data.get("status"))

if not found:
    print("No pending episodes found.")
