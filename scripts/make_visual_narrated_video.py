import os
import re
import subprocess
import tempfile
import shutil

import firebase_admin
from firebase_admin import credentials, firestore

import torch
import soundfile as sf
from transformers import AutoTokenizer, VitsModel


# ============================================================
# EASYDUBBER — CINEMATIC TAGALOG VIDEO V2
# ============================================================
#
# Features:
# - Reads NARRATION: lines from Firestore
# - Uses scene_01.png ... scene_10.png
# - Generates Tagalog TTS
# - Creates one independent video clip per scene
# - Slow cinematic zoom
# - Each image stays on screen for its narration
# - Uses FFmpeg concat FILTER instead of stream-copy concat
# - Prevents the "one image for whole video" problem
# - 1080x1920 vertical video
# - H.264 + AAC
#
# Output:
# output/easydubber_visual_tagalog_episode.mp4
# ============================================================


OUTPUT_VIDEO = "output/easydubber_visual_tagalog_episode.mp4"
IMAGE_DIR = "output/images"
AUDIO_DIR = "output/audio"
SCENE_DIR = "output/scene_clips"

MODEL_NAME = "facebook/mms-tts-tgl"
SAMPLE_RATE = 16000

WIDTH = 1080
HEIGHT = 1920

FPS = 30

# Small padding at the end of each narration.
# This helps avoid cutting the final word.
END_PADDING = 0.20


# ============================================================
# FIREBASE
# ============================================================

if not firebase_admin._apps:
    service_account_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT")

    if not service_account_json:
        raise RuntimeError(
            "FIREBASE_SERVICE_ACCOUNT environment variable is missing."
        )

    import json

    service_account_info = json.loads(service_account_json)

    cred = credentials.Certificate(service_account_info)

    firebase_admin.initialize_app(cred)


db = firestore.client()


# ============================================================
# HELPERS
# ============================================================

def run_command(command):
    print()
    print("Running:")
    print(" ".join(command))
    print()

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    print(result.stdout)

    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed with exit code {result.returncode}"
        )

    return result.stdout


def get_audio_duration(path):
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            path
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Could not read audio duration: {path}"
        )

    return float(result.stdout.strip())


def safe_filename(text):
    text = re.sub(r"[^a-zA-Z0-9_-]+", "_", text)
    return text[:100]


# ============================================================
# FIND GENERATED EPISODE
# ============================================================

print()
print("========================================")
print("EASYDUBBER CINEMATIC VIDEO V2")
print("========================================")
print()

episodes = (
    db.collection("episodes")
    .where("status", "==", "generated")
    .limit(1)
    .stream()
)

episode_doc = None

for doc in episodes:
    episode_doc = doc
    break


if episode_doc is None:
    raise RuntimeError(
        "No generated episode found in Firestore."
    )


episode = episode_doc.to_dict()

title = episode.get("title", "EasyDubber Episode")

story = episode.get("story", "")


print("Episode:", title)
print()


# ============================================================
# PARSE NARRATION LINES
# ============================================================

blocks = re.split(
    r"\n\s*\n",
    story.strip()
)

narrations = []


for block in blocks:

    match = re.search(
        r"NARRATION:\s*(.+)",
        block,
        re.IGNORECASE
    )

    if not match:
        continue

    narration = match.group(1).strip()

    if narration:
        narrations.append(narration)


print("Narration scenes found:", len(narrations))
print()


if len(narrations) == 0:
    raise RuntimeError(
        "No NARRATION lines were found in the episode story."
    )


# ============================================================
# CHECK SCENE IMAGES
# ============================================================

visuals = []

for index in range(1, len(narrations) + 1):

    image_path = os.path.join(
        IMAGE_DIR,
        f"scene_{index:02d}.png"
    )

    if not os.path.exists(image_path):
        raise RuntimeError(
            f"Missing scene image: {image_path}"
        )

    visuals.append(image_path)


print("Scene images found:", len(visuals))
print()


# ============================================================
# PREPARE DIRECTORIES
# ============================================================

os.makedirs("output", exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)

if os.path.exists(SCENE_DIR):
    shutil.rmtree(SCENE_DIR)

os.makedirs(SCENE_DIR)


# ============================================================
# LOAD TAGALOG TTS
# ============================================================

print("Loading Tagalog TTS...")

device = "cuda" if torch.cuda.is_available() else "cpu"

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_NAME
)

model = VitsModel.from_pretrained(
    MODEL_NAME
)

model = model.to(device)

model.eval()

print()
print("Tagalog TTS loaded.")
print()


# ============================================================
# GENERATE EACH SCENE
# ============================================================

scene_clips = []

for index, narration in enumerate(narrations, start=1):

    print("================================")
    print(f"SCENE {index}")
    print("================================")
    print()

    print("Narration:", narration)
    print()

    # --------------------------------------------------------
    # AUDIO
    # --------------------------------------------------------

    audio_path = os.path.join(
        AUDIO_DIR,
        f"audio_{index:02d}.wav"
    )

    inputs = tokenizer(
        narration,
        return_tensors="pt"
    )

    inputs = {
        key: value.to(device)
        for key, value in inputs.items()
    }

    with torch.no_grad():

        output = model(**inputs)

    waveform = output.waveform

    waveform = waveform.detach().cpu().numpy()

    if waveform.ndim > 1:
        waveform = waveform.squeeze()

    sf.write(
        audio_path,
        waveform,
        SAMPLE_RATE
    )

    # --------------------------------------------------------
    # AUDIO DURATION
    # --------------------------------------------------------

    duration = get_audio_duration(audio_path)

    duration += END_PADDING

    print(
        f"Audio duration: {duration:.2f}s"
    )

    # --------------------------------------------------------
    # IMAGE
    # --------------------------------------------------------

    image_path = visuals[index - 1]

    # --------------------------------------------------------
    # SCENE VIDEO
    # --------------------------------------------------------

    clip_path = os.path.join(
        SCENE_DIR,
        f"scene_{index:02d}.mp4"
    )

    # --------------------------------------------------------
    # CINEMATIC ZOOM
    #
    # Each scene gets its own independent video stream.
    #
    # zoompan:
    # - starts around 1.00x
    # - slowly moves toward 1.08x
    #
    # The image itself is never replaced by another image
    # inside this clip.
    # --------------------------------------------------------

    frames = max(
        1,
        int(duration * FPS)
    )

    zoom_expression = (
        "min(zoom+0.0008,1.08)"
    )

    vf = (
        f"scale={WIDTH}:{HEIGHT}:"
        f"force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},"
        f"zoompan="
        f"z='{zoom_expression}':"
        f"x='iw/2-(iw/zoom/2)':"
        f"y='ih/2-(ih/zoom/2)':"
        f"d={frames}:"
        f"s={WIDTH}x{HEIGHT}:"
        f"fps={FPS}"
    )

    command = [
        "ffmpeg",
        "-y",

        "-loop",
        "1",

        "-i",
        image_path,

        "-i",
        audio_path,

        "-vf",
        vf,

        "-t",
        f"{duration:.3f}",

        "-map",
        "0:v:0",

        "-map",
        "1:a:0",

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "20",

        "-pix_fmt",
        "yuv420p",

        "-r",
        str(FPS),

        "-c:a",
        "aac",

        "-b:a",
        "128k",

        "-ar",
        "44100",

        "-ac",
        "2",

        "-shortest",

        "-movflags",
        "+faststart",

        clip_path
    ]

    run_command(command)

    if not os.path.exists(clip_path):
        raise RuntimeError(
            f"Scene clip was not created: {clip_path}"
        )

    scene_clips.append(clip_path)

    print()
    print("Scene video created.")
    print()


# ============================================================
# CONCATENATE SCENES
# ============================================================

print()
print("========================================")
print("COMBINING ALL SCENES")
print("========================================")
print()


if not scene_clips:
    raise RuntimeError(
        "No scene clips were generated."
    )


# Create concat list.
concat_file = os.path.join(
    SCENE_DIR,
    "concat.txt"
)

with open(
    concat_file,
    "w",
    encoding="utf-8"
) as f:

    for clip in scene_clips:

        absolute_path = os.path.abspath(
            clip
        )

        # FFmpeg concat demuxer requires escaped paths.
        escaped = absolute_path.replace(
            "'",
            "'\\''"
        )

        f.write(
            f"file '{escaped}'\n"
        )


# ------------------------------------------------------------
# IMPORTANT:
#
# We DO NOT use:
#
# -c copy
#
# because that caused the timestamp warnings.
#
# Instead we decode/re-encode the combined stream.
#
# Every scene therefore keeps its own video frames.
# ------------------------------------------------------------

run_command(
    [
        "ffmpeg",
        "-y",

        "-f",
        "concat",

        "-safe",
        "0",

        "-i",
        concat_file,

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "20",

        "-pix_fmt",
        "yuv420p",

        "-r",
        str(FPS),

        "-c:a",
        "aac",

        "-b:a",
        "128k",

        "-ar",
        "44100",

        "-ac",
        "2",

        "-movflags",
        "+faststart",

        OUTPUT_VIDEO
    ]
)


# ============================================================
# VERIFY OUTPUT
# ============================================================

if not os.path.exists(OUTPUT_VIDEO):

    raise RuntimeError(
        "Final video was not created."
    )


print()
print("========================================")
print("VERIFYING FINAL VIDEO")
print("========================================")
print()


probe = subprocess.run(
    [
        "ffprobe",
        "-v",
        "error",

        "-show_entries",
        "stream=index,codec_type,codec_name,width,height,duration",

        "-of",
        "json",

        OUTPUT_VIDEO
    ],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)


print(probe.stdout)


if probe.returncode != 0:
    raise RuntimeError(
        "Final video verification failed."
    )


# ============================================================
# FIRESTORE UPDATE
# ============================================================

episode_doc.reference.update(
    {
        "video_status": "completed",
        "video_file": OUTPUT_VIDEO
    }
)


# ============================================================
# COMPLETE
# ============================================================

print()
print("========================================")
print("EASYDUBBER TAGALOG VIDEO COMPLETE")
print("========================================")
print()
print(OUTPUT_VIDEO)
print()
print("Scenes:", len(scene_clips))
print("Resolution:", f"{WIDTH}x{HEIGHT}")
print("FPS:", FPS)
print()
print("Video + Audio successfully combined.")
print()
