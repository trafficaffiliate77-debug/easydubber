import os
import subprocess
import json
import firebase_admin

from firebase_admin import credentials, firestore
from transformers import AutoTokenizer, VitsModel
import torch
import soundfile as sf


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

title = episode_data.get("title", "EasyDubber Episode")
story = episode_data.get("story", "")

print("Episode:", title)


# ==========================================
# Extract scenes
# ==========================================

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

scenes = scenes[:10]

if not scenes:
    print("No scenes found.")
    exit(1)

print("Scenes:", len(scenes))


# ==========================================
# Output directory
# ==========================================

os.makedirs("output", exist_ok=True)


# ==========================================
# Load Tagalog TTS
# ==========================================

print("Loading Tagalog TTS...")

model_name = "facebook/mms-tts-tgl"

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = VitsModel.from_pretrained(model_name)

print("Tagalog TTS loaded.")


# ==========================================
# Generate scene videos
# ==========================================

scene_files = []


for i, scene in enumerate(scenes):

    print()
    print("Processing scene", i + 1)

    # Remove SCENE heading from spoken text
    parts = scene.split("\n", 1)

    if len(parts) == 2:
        spoken_text = parts[1]
    else:
        spoken_text = scene

    # --------------------------------------
    # TTS
    # --------------------------------------

    inputs = tokenizer(
        spoken_text,
        return_tensors="pt"
    )

    with torch.no_grad():

        output = model(
            **inputs
        ).waveform

    audio = (
        output
        .squeeze()
        .cpu()
        .numpy()
    )

    audio_file = (
        f"output/audio_{i:02d}.wav"
    )

    sf.write(
        audio_file,
        audio,
        16000
    )

    # --------------------------------------
    # Get audio duration
    # --------------------------------------

    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            audio_file
        ],
        capture_output=True,
        text=True,
        check=True
    )

    duration = float(
        probe.stdout.strip()
    )

    # Small safety padding
    duration += 0.15

    # --------------------------------------
    # Create scene video
    # --------------------------------------

    video_file = (
        f"output/scene_{i:02d}.mp4"
    )

    safe_text = (
        scene
        .replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace(":", "\\:")
        .replace("\n", "\\n")
    )

    command = [
        "ffmpeg",
        "-y",

        "-f",
        "lavfi",

        "-i",
        "color=c=black:s=1080x1920:r=30",

        "-i",
        audio_file,

        "-t",
        str(duration),

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

        "-map",
        "0:v:0",

        "-map",
        "1:a:0",

        "-c:v",
        "libx264",

        "-c:a",
        "aac",

        "-pix_fmt",
        "yuv420p",

        "-shortest",

        video_file
    ]

    subprocess.run(
        command,
        check=True
    )

    scene_files.append(video_file)


# ==========================================
# Create concat list
# ==========================================

concat_file = "output/concat.txt"

with open(
    concat_file,
    "w"
) as f:

    for filename in scene_files:

        f.write(
            f"file '{os.path.abspath(filename)}'\n"
        )


# ==========================================
# Combine
# ==========================================

final_video = (
    "output/easydubber_tagalog_episode.mp4"
)

subprocess.run(
    [
        "ffmpeg",
        "-y",

        "-f",
        "concat",

        "-safe",
        "0",

        "-i",
        concat_file,

        "-c",
        "copy",

        final_video
    ],
    check=True
)


print()
print("====================================")
print("EASYDUBBER TAGALOG VIDEO COMPLETE")
print("====================================")
print(final_video)
