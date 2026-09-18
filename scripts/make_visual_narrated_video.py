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


story = episode_data.get(
    "story",
    ""
)

title = episode_data.get(
    "title",
    "EasyDubber Episode"
)

print("Episode:", title)


# ==========================================
# Extract narration
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

    narration = ""

    for line in lines:

        if line.startswith("NARRATION:"):

            narration = line.replace(
                "NARRATION:",
                "",
                1
            ).strip()

    if narration:

        scenes.append(
            (number, narration)
        )


scenes = scenes[:10]

print(
    "Narration scenes found:",
    len(scenes)
)


# ==========================================
# Directories
# ==========================================

os.makedirs(
    "output/audio",
    exist_ok=True
)

os.makedirs(
    "output/video_scenes",
    exist_ok=True
)


# ==========================================
# Load Tagalog TTS
# ==========================================

print("Loading Tagalog TTS...")

model_name = "facebook/mms-tts-tgl"

tokenizer = AutoTokenizer.from_pretrained(
    model_name
)

model = VitsModel.from_pretrained(
    model_name
)

print("Tagalog TTS loaded.")


scene_files = []


# ==========================================
# Process scenes
# ==========================================

for number, narration in scenes:

    print()
    print("================================")
    print("SCENE", number)
    print("================================")

    print(
        "Narration:",
        narration
    )


    # ======================================
    # TTS
    # ======================================

    inputs = tokenizer(
        narration,
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
        f"output/audio/"
        f"audio_{number:02d}.wav"
    )

    sf.write(
        audio_file,
        audio,
        16000
    )


    # ======================================
    # Get duration
    # ======================================

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

    duration += 0.20


    # ======================================
    # Image
    # ======================================

    image_file = (
        f"output/images/"
        f"scene_{number:02d}.png"
    )

    if not os.path.exists(image_file):

        print(
            "Missing image:",
            image_file
        )

        continue


    # ======================================
    # Cinematic movement
    # ======================================

    video_file = (
        f"output/video_scenes/"
        f"scene_{number:02d}.mp4"
    )

    zoom_filter = (
        "scale=1200:2133,"
        "zoompan="
        "z='min(zoom+0.0008,1.12)':"
        "x='iw/2-(iw/zoom/2)':"
        "y='ih/2-(ih/zoom/2)':"
        "d=1:"
        "s=1080x1920:"
        "fps=30,"
        "trim=duration="
        + str(duration)
    )


    command = [

        "ffmpeg",
        "-y",

        "-loop",
        "1",

        "-i",
        image_file,

        "-i",
        audio_file,

        "-vf",
        zoom_filter,

        "-t",
        str(duration),

        "-map",
        "0:v:0",

        "-map",
        "1:a:0",

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "23",

        "-c:a",
        "aac",

        "-b:a",
        "128k",

        "-pix_fmt",
        "yuv420p",

        "-shortest",

        video_file
    ]


    subprocess.run(
        command,
        check=True
    )


    scene_files.append(
        video_file
    )


    print(
        "Scene video created."
    )


# ==========================================
# Concat
# ==========================================

concat_file = (
    "output/video_concat.txt"
)

with open(
    concat_file,
    "w"
) as f:

    for filename in scene_files:

        f.write(
            "file '"
            + os.path.abspath(filename)
            + "'\n"
        )


# ==========================================
# Final video
# ==========================================

final_video = (
    "output/"
    "easydubber_visual_tagalog_episode.mp4"
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
print("========================================")
print("EASYDUBBER TAGALOG VIDEO COMPLETE")
print("========================================")
print(final_video)
