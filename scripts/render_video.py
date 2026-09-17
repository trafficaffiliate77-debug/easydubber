import os
import subprocess
import json
import firebase_admin
from firebase_admin import credentials, firestore

# -----------------------------
# Firebase
# -----------------------------

service_account = json.loads(
    os.environ["FIREBASE_SERVICE_ACCOUNT"]
)

cred = credentials.Certificate(service_account)

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

# -----------------------------
# Find generated episode
# -----------------------------

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

title = episode_data.get("title", "EasyDubber Episode")
story = episode_data.get("story", "")

print("Episode:", title)

# -----------------------------
# Extract scenes
# -----------------------------

scenes = []

for block in story.split("SCENE ")[1:]:
    lines = block.strip().splitlines()

    if not lines:
        continue

    number = lines[0].split(":")[0].strip()

    text = "\n".join(lines[1:]).strip()

    if text:
        scenes.append(
            f"SCENE {number}\n{text}"
        )

# Limit to 10 scenes
scenes = scenes[:10]

if not scenes:
    print("No scenes found.")
    exit(1)

print("Scenes found:", len(scenes))

# -----------------------------
# Render scenes
# -----------------------------

os.makedirs("output", exist_ok=True)

scene_files = []

for i, text in enumerate(scenes):

    filename = f"output/scene_{i:02d}.mp4"

    scene_files.append(filename)

    # Make text safer for FFmpeg
    safe_text = (
        text
        .replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace(":", "\\:")
        .replace("\n", "\\n")
    )

    command = [
        "ffmpeg",
        "-y",
        "-f", "lavfi",
        "-i",
        "color=c=black:s=1080x1920:r=30",
        "-t", "3",
        "-vf",
        (
            "drawtext="
            "fontfile=/usr/share/fonts/truetype/dejavu/"
            "DejaVuSans-Bold.ttf:"
            f"text='{safe_text}':"
            "fontcolor=white:"
            "fontsize=48:"
            "x=(w-text_w)/2:"
            "y=(h-text_h)/2:"
            "line_spacing=18"
        ),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        filename
    ]

    subprocess.run(command, check=True)

# -----------------------------
# Combine scenes
# -----------------------------

concat_file = "output/concat.txt"

with open(concat_file, "w") as f:

    for filename in scene_files:

        f.write(
            f"file '{os.path.abspath(filename)}'\n"
        )

final_video = "output/easydubber_episode_01.mp4"

subprocess.run([
    "ffmpeg",
    "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", concat_file,
    "-c", "copy",
    final_video
], check=True)

print()
print("================================")
print("EASYDUBBER EPISODE CREATED")
print("================================")
print(final_video)
