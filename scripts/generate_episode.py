import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

# Firebase connection
service_account = json.loads(
    os.environ["FIREBASE_SERVICE_ACCOUNT"]
)

cred = credentials.Certificate(service_account)

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Find one pending episode
episodes = (
    db.collection("episodes")
    .where("status", "==", "pending")
    .limit(1)
    .stream()
)

episode_doc = None
episode_data = None

for doc in episodes:
    episode_doc = doc
    episode_data = doc.to_dict()
    break

if episode_doc is None:
    print("No pending episodes.")
    exit(0)

title = episode_data.get("title", "Untitled")
prompt = episode_data.get("prompt", "")

print("================================")
print("EASYDUBBER EPISODE GENERATOR")
print("================================")
print("Title:", title)
print("Idea:", prompt)
print()

# Temporary story generation
story = f"""
EPISODE: {title}

STORY IDEA:
{prompt}

SCENE 1:
Opening shot establishes the main character and the mysterious situation.

SCENE 2:
The main character notices something unusual.

SCENE 3:
A mysterious event changes everything.

SCENE 4:
The main character discovers a hidden secret.

SCENE 5:
A new character appears and creates tension.

SCENE 6:
The main character faces an unexpected challenge.

SCENE 7:
The hidden technology or secret becomes more powerful.

SCENE 8:
The main character makes an important decision.

SCENE 9:
A surprising revelation changes the situation.

SCENE 10:
CLIFFHANGER:
Something unexpected appears, leading directly into the next episode.

ENDING CTA:
Like, follow, and subscribe for the next episode.
"""

print(story)

# Save generated story back to Firebase
episode_doc.reference.update({
    "status": "generated",
    "story": story
})

print()
print("Episode generated successfully!")
