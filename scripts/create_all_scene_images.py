import os
import json
import firebase_admin

from firebase_admin import credentials, firestore

from create_scene_image import create_scene_image


# ==========================================
# Firebase
# ==========================================

service_account = json.loads(
    os.environ["FIREBASE_SERVICE_ACCOUNT"]
)

cred = credentials.Certificate(
    service_account
)

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()


# ==========================================
# Find generated episode
# ==========================================

episodes = (
    db.collection("episodes")
    .where("status", "==", "generated")
    .limit(1)
    .stream()
)

episode_data = None

for doc in episodes:
    episode_data = doc.to_dict()
    break


if episode_data is None:
    print("No generated episode found.")
    exit(0)


story = episode_data.get(
    "story",
    ""
)


# ==========================================
# Extract scenes
# ==========================================

scenes = []

for block in story.split("SCENE ")[1:]:

    lines = block.strip().splitlines()

    if not lines:
        continue

    number = lines[0].split(":")[0].strip()

    text = "\n".join(
        lines[1:]
    ).strip()

    if text:

        scenes.append(
            (
                number,
                text
            )
        )


scenes = scenes[:10]

print(
    "Creating",
    len(scenes),
    "scene visuals..."
)


# ==========================================
# Generate images
# ==========================================

for number, text in scenes:

    create_scene_image(
        int(number),
        text
    )


print()
print("================================")
print("ALL SCENE IMAGES CREATED")
print("================================")
