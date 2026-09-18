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

cred = credentials.Certificate(service_account)

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
    "A mysterious futuristic adventure."
)


print("================================")
print("EASYDUBBER STORY GENERATOR")
print("================================")
print("Title:", title)
print("Idea:", prompt)


# ==========================================
# Story structure
# ==========================================

story = f"""
SCENE 1
VISUAL: Opening shot based on this story idea: {prompt}. Establish the main character, location, atmosphere, and mystery.
NARRATION: Sa simula ng kuwentong ito, isang misteryosong pangyayari ang magbabago sa buhay ng pangunahing tauhan.

SCENE 2
VISUAL: The main character discovers something unusual connected to the story idea: {prompt}. Show a strong visual mystery.
NARRATION: Hindi niya alam kung ano ang tunay na kahulugan ng kanyang natuklasan, ngunit alam niyang may malaking panganib na paparating.

SCENE 3
VISUAL: A powerful futuristic or mysterious event happens. The main character reacts with surprise while the environment changes dramatically.
NARRATION: Biglang nagbago ang lahat. Isang kakaibang pangyayari ang nagpakita ng kapangyarihang hindi niya kailanman nakita.

SCENE 4
VISUAL: The main character investigates the mystery. Show close-up expressions, dramatic lighting, and important clues.
NARRATION: Sinimulan niyang hanapin ang katotohanan habang unti-unting lumalabas ang mga lihim.

SCENE 5
VISUAL: Introduce an important supporting character connected to the main mystery. Create emotional tension between the characters.
NARRATION: Ngunit hindi siya nag-iisa. May isang taong biglang dumating na tila alam ang higit pa sa kanyang nalalaman.

SCENE 6
VISUAL: The main character and the supporting character face an unexpected threat together.
NARRATION: Bago pa nila maintindihan ang buong sitwasyon, dumating ang isang hindi inaasahang banta.

SCENE 7
VISUAL: Reveal a major secret connected to the original story idea. Use dramatic cinematic lighting and a powerful visual reveal.
NARRATION: At doon niya nalaman ang isang lihim na maaaring magbago sa buong mundo.

SCENE 8
VISUAL: The main character activates a new ability, technology, weapon, or mysterious power related to the story.
NARRATION: Sa unang pagkakataon, ginamit niya ang kapangyarihang matagal nang nakatago sa kanyang harapan.

SCENE 9
VISUAL: Powerful enemies appear in the distance while the main character prepares for the coming confrontation.
NARRATION: Ngunit may mas makapangyarihang mga kalaban na naghihintay. At ngayon, wala nang atrasan.

SCENE 10
VISUAL: End with a dramatic cliffhanger based on the story idea: {prompt}. The main character faces an unknown future.
NARRATION: Hindi pa tapos ang laban. Sa susunod na kabanata, malalaman natin kung ano ang tunay na kapangyarihan sa likod ng misteryong ito.

CTA
VISUAL: Dramatic colorful cinematic ending with glowing particles and the title appearing on screen.
NARRATION: Kung gusto mong makita ang susunod na episode, i-like, i-follow, at mag-subscribe para hindi mo ito mapalampas.
"""


# ==========================================
# Save
# ==========================================

episode_doc.reference.update({
    "story": story.strip(),
    "status": "generated"
})


print()
print("================================")
print("EPISODE GENERATED SUCCESSFULLY")
print("================================")
print("Title:", title)
print("Status: generated")
