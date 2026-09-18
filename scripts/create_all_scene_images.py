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

cred = credentials.Certificate(service_account)

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

episode_doc = None
episode_data = None

for doc in episodes:
    episode_doc = doc
    episode_data = doc.to_dict()
    break


if episode_doc is None:
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

    number_text = lines[0].split(":")[0].strip()

    try:
        number = int(number_text)
    except ValueError:
        continue

    visual = ""

    for line in lines:

        if line.startswith("VISUAL:"):
            visual = line.replace(
                "VISUAL:",
                "",
                1
            ).strip()

    if visual:
        scenes.append(
            (number, visual)
        )


scenes = scenes[:10]

print(
    "Visual scenes found:",
    len(scenes)
)


# ==========================================
# Generate images
# ==========================================

for number, visual in scenes:

    print()
    print("Creating visual for scene", number)

    create_scene_image(
        number,
        visual
    )


print()
print("================================")
print("VISUAL GENERATION COMPLETE")
print("================================")
