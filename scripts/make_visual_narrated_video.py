import os
import re
import json
import shutil
import subprocess

import firebase_admin
from firebase_admin import credentials, firestore

import torch
import soundfile as sf
from transformers import AutoTokenizer, VitsModel


# ============================================================
# EASYDUBBER — FINAL SCENE RENDERER
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

    service_account_info = json.loads(service_account_json)

    cred = credentials.Certificate(service_account_info)

    firebase_admin.initialize_app(cred)


db = firestore.client()


# ============================================================
# COMMAND RUNNER
# ============================================================

def run_command(command):

    print()
    print("RUNNING:")
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
            "Command failed with exit code "
            + str(result.returncode)
        )

    return result.stdout


# ============================================================
# AUDIO DURATION
# ============================================================

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
            "Could not read audio duration: " + path
        )

    value = result.stdout.strip()

    if not value:
        raise RuntimeError(
            "FFprobe returned no duration: " + path
        )

    return float(value)


# ============================================================
# FIND GENERATED EPISODE
# ============================================================

print()
print("==============================================")
print("EASYDUBBER FINAL SCENE RENDERER")
print("==============================================")
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

title = episode.get(
    "title",
    "EasyDubber Episode"
)

story = episode.get(
    "story",
    ""
)


print("Episode:", title)
print()


if not story.strip():
    raise RuntimeError(
        "Episode story is empty."
    )


# ============================================================
# PARSE SCENES
# ============================================================

blocks = re.split(
    r"\n\s*\n",
    story.strip()
)


scenes = []


for block in blocks:

    scene_match = re.search(
        r"^\s*SCENE\s+(\d+)",
        block,
        re.IGNORECASE
    )

    narration_match = re.search(
        r"NARRATION:\s*(.+)",
        block,
        re.IGNORECASE
    )

    if not scene_match:
        continue

    if not narration_match:
        print(
            "WARNING: Scene has no narration:",
            scene_match.group(1)
        )
        continue

    number = int(
        scene_match.group(1)
    )

    narration = narration_match.group(1).strip()

    if not narration:
        continue

    scenes.append(
        {
            "number": number,
            "narration": narration
        }
    )


scenes.sort(
    key=lambda x: x["number"]
)


print(
    "Scenes found:",
    len(scenes)
)


if not scenes:
    raise RuntimeError(
        "No valid scenes found."
    )


# ============================================================
# VERIFY IMAGES
# ============================================================

print()
print("==============================================")
print("VERIFYING SCENE IMAGES")
print("==============================================")
print()


for scene in scenes:

    number = scene["number"]

    image_path = os.path.join(
        IMAGE_DIR,
        f"scene_{number:02d}.png"
    )

    print(
        f"Scene {number}: {image_path}"
    )

    if not os.path.isfile(image_path):

        raise RuntimeError(
            f"Missing image for Scene {number}: "
            f"{image_path}"
        )

    scene["image"] = image_path


print()
print("ALL SCENE IMAGES FOUND")
print()


# ============================================================
# PREPARE DIRECTORIES
# ============================================================

os.makedirs(
    "output",
    exist_ok=True
)

os.makedirs(
    IMAGE_DIR,
    exist_ok=True
)

os.makedirs(
    AUDIO_DIR,
    exist_ok=True
)

if os.path.exists(SCENE_DIR):

    shutil.rmtree(
        SCENE_DIR
    )

os.makedirs(
    SCENE_DIR
)


# ============================================================
# LOAD TAGALOG TTS
# ============================================================

print()
print("==============================================")
print("LOADING TAGALOG TTS")
print("==============================================")
print()


device = (
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)


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
# CREATE INDIVIDUAL SCENE CLIPS
# ============================================================

scene_clips = []


for scene in scenes:

    number = scene["number"]

    narration = scene["narration"]

    image_path = scene["image"]


    print()
    print("----------------------------------------------")
    print(f"CREATING SCENE {number}")
    print("----------------------------------------------")
    print()

    print(
        "IMAGE:",
        image_path
    )

    print(
        "NARRATION:",
        narration
    )

    print()


    # --------------------------------------------------------
    # TTS
    # --------------------------------------------------------

    audio_path = os.path.join(
        AUDIO_DIR,
        f"audio_{number:02d}.wav"
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

        output = model(
            **inputs
        )


    waveform = (
        output.waveform
        .detach()
        .cpu()
        .numpy()
    )


    if waveform.ndim > 1:

        waveform = waveform.squeeze()


    sf.write(
        audio_path,
        waveform,
        SAMPLE_RATE
    )


    audio_duration = get_audio_duration(
        audio_path
    )


    scene_duration = (
        audio_duration
        + END_PADDING
    )


    print(
        f"Audio duration: "
        f"{audio_duration:.2f}s"
    )

    print(
        f"Scene duration: "
        f"{scene_duration:.2f}s"
    )


    # --------------------------------------------------------
    # SCENE VIDEO
    # --------------------------------------------------------

    clip_path = os.path.join(
        SCENE_DIR,
        f"scene_{number:02d}.mp4"
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

        (
            f"scale={WIDTH}:{HEIGHT}:"
            f"force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{HEIGHT},"
            f"format=yuv420p"
        ),

        "-t",
        f"{scene_duration:.3f}",

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

        clip_path
    ]


    run_command(
        command
    )


    if not os.path.isfile(
        clip_path
    ):

        raise RuntimeError(
            f"Scene clip missing: "
            f"{clip_path}"
        )


    scene_clips.append(
        clip_path
    )


    print(
        f"SCENE {number} COMPLETE"
    )


# ============================================================
# VERIFY CLIPS
# ============================================================

print()
print("==============================================")
print("VERIFYING SCENE CLIPS")
print("==============================================")
print()


for clip in scene_clips:

    if not os.path.isfile(clip):

        raise RuntimeError(
            f"Missing scene clip: {clip}"
        )

    print(
        "OK:",
        clip
    )


# ============================================================
# CREATE CONCAT FILE
# ============================================================

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

        absolute_path = (
            absolute_path
            .replace("\\", "/")
        )

        escaped = (
            absolute_path
            .replace("'", "'\\''")
        )

        f.write(
            f"file '{escaped}'\n"
        )


print()
print("==============================================")
print("COMBINING SCENES")
print("==============================================")
print()


# ============================================================
# FINAL CONCAT
# ============================================================

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
# FINAL VERIFICATION
# ============================================================

print()
print("==============================================")
print("VERIFYING FINAL VIDEO")
print("==============================================")
print()


if not os.path.isfile(
    OUTPUT_VIDEO
):

    raise RuntimeError(
        "Final video was not created."
    )


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


if probe.returncode != 0:

    print(
        probe.stderr
    )

    raise RuntimeError(
        "Final video verification failed."
    )


print(
    probe.stdout
)


data = json.loads(
    probe.stdout
)


streams = data.get(
    "streams",
    []
)


has_video = any(
    s.get("codec_type") == "video"
    for s in streams
)


has_audio = any(
    s.get("codec_type") == "audio"
    for s in streams
)


if not has_video:

    raise RuntimeError(
        "Final video has no video stream."
    )


if not has_audio:

    raise RuntimeError(
        "Final video has no audio stream."
    )


print()
print("VIDEO STREAM: OK")
print("AUDIO STREAM: OK")
print()


# ============================================================
# UPDATE FIRESTORE
# ============================================================

episode_doc.reference.update(
    {
        "video_status": "completed",
        "video_file": OUTPUT_VIDEO
    }
)


print()
print("==============================================")
print("EASYDUBBER VIDEO COMPLETE")
print("==============================================")
print()

print(
    "Output:",
    OUTPUT_VIDEO
)

print(
    "Scenes:",
    len(scene_clips)
)

print(
    "Resolution:",
    f"{WIDTH}x{HEIGHT}"
)

print(
    "FPS:",
    FPS
)

print()
print("ALL SCENES RENDERED SUCCESSFULLY")
print()
