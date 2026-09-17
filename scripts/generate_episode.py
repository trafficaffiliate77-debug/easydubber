import os
import json
import firebase_admin

from firebase_admin import credentials, firestore


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
# Find pending episode
# ==========================================

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
    print("No pending episode found.")
    exit(0)


title = episode_data.get(
    "title",
    "EasyDubber Episode"
)

prompt = episode_data.get(
    "prompt",
    ""
)


print("Generating episode:")
print(title)
print()
print("Idea:")
print(prompt)


# ==========================================
# Story
# ==========================================

story = f"""
SCENE 1
VISUAL: A mysterious young man stands alone outside a futuristic city at night, surrounded by glowing holographic technology.
NARRATION: Sa isang lungsod na puno ng makabagong teknolohiya, isang misteryosong binata ang tahimik na nakatayo.

SCENE 2
VISUAL: The young man discovers a strange black technological core glowing inside an abandoned laboratory.
NARRATION: Sa isang lumang laboratoryo, natuklasan niya ang isang kakaibang itim na core na kumikinang.

SCENE 3
VISUAL: The black core floats in front of him and projects a giant blue holographic interface.
NARRATION: Biglang lumutang ang core at nagpakita ng isang napakalaking holographic system.

SCENE 4
VISUAL: Hundreds of holographic screens surround the young man as mysterious information appears around him.
NARRATION: Napalibutan siya ng daan-daang holographic screen na naglalaman ng mga lihim na impormasyon.

SCENE 5
VISUAL: The young man touches the holographic interface and the entire laboratory begins transforming.
NARRATION: Nang hawakan niya ang sistema, nagsimulang magbago ang buong laboratoryo.

SCENE 6
VISUAL: A beautiful mysterious woman appears inside the holographic system and looks directly at him.
NARRATION: Ngunit isang magandang misteryosang babae ang biglang lumitaw sa loob ng sistema.

SCENE 7
VISUAL: The woman warns him about powerful enemies watching from the shadows.
NARRATION: Binalaan siya ng babae tungkol sa makapangyarihang mga kaaway na nagmamasid mula sa dilim.

SCENE 8
VISUAL: The young man looks toward the city as massive holographic towers activate in the distance.
NARRATION: Tumingin siya sa lungsod habang isa-isang nag-activate ang malalaking holographic tower.

SCENE 9
VISUAL: Dark figures watch the glowing city from a hidden control room.
NARRATION: Samantala, may mga misteryosong tao sa isang lihim na silid na nagmamasid sa kanya.

SCENE 10
VISUAL: The young man smiles confidently as the black core floats beside him and the city lights up behind him.
NARRATION: Ngumiti siya at sinabi, "Kung gusto nila akong subukan, handa na ako."

CTA
VISUAL: The holographic system fills the screen with glowing futuristic symbols.
NARRATION: Kung gusto mong malaman ang susunod na mangyayari, i-like, i-follow, at mag-subscribe para sa Episode 2.
"""


# ==========================================
# Save to Firestore
# ==========================================

episode_doc.reference.update({

    "story": story.strip(),

    "status": "generated"

})


print()
print("================================")
print("EPISODE GENERATED")
print("================================")
print(title)
