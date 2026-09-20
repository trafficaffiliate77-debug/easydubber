import os
import re
import subprocess
import shutil
import json

import firebase_admin
from firebase_admin import credentials, firestore

import torch
import soundfile as sf
from transformers import AutoTokenizer, VitsModel


# ============================================================
# EASYDUBBER — CINEMATIC TAGALOG VIDEO V3
# ============================================================
#
# Features:
# - Supports ANY number of scenes
# - Matches Scene 1 -> scene_01.png
# - Matches Scene 11 -> scene_11.png
# - Reads NARRATION from Firestore
# - Generates Tagalog TTS
# - One independent video clip per scene
# - Slow cinematic zoom
# - No image skipping
# - No hard 10-scene limit
# - No stream-copy concatenation
# - H.264 + AAC
# - 1080x1920 vertical video
#
# Output:
# output/easydubber_visual_tagalog_episode.mp4
# ============================================================


OUTPUT_VIDEO = (
    "output/easydubber_visual_tagalog_episode.mp4"
)

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

    service_account_json = os.environ.get(
        "FIREBASE_SERVICE_ACCOUNT"
    )

    if not service_account_json:
        raise RuntimeError(
            "FIREBASE_SERVICE_ACCOUNT environment variable is missing."
        )

    service_account_info = json.loads(
        service_account_json
    )

    cred = credentials.Certificate(
        service_account_info
    )

    firebase_admin.initialize_app(
        cred
    )


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
            "Command failed with exit code "
            + str(result.returncode)
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

    value = result.stdout.strip()

    if not value:

        raise RuntimeError(
            f"FFprobe returned no duration for: {path}"
        )

    return float(value)


# ============================================================
# FIND GENERATED EPISODE
# ============================================================

print()
print("========================================")
print("EASYDUBBER CINEMATIC VIDEO V3")
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
#
# Expected format:
#
# SCENE 1
# VISUAL: ...
# NARRATION: ...
#
# SCENE 2
# VISUAL: ...
# NARRATION: ...
#
# SCENE 11
# VISUAL: ...
# NARRATION: ...
#
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
            "Warning: Scene has no NARRATION:",
            scene_match.group(1)
        )
        continue

    scene_number = int(
        scene_match.group(1)
    )

    narration = narration_match.group(1).strip()

    if not narration:
        continue

    scenes.append(
        {
            "number": scene_number,
            "narration": narration
        }
    )


# ============================================================
# SORT SCENES
# ============================================================

scenes.sort(
    key=lambda item: item["number"]
)


print(
    "Narration scenes found:",
    len(scenes)
)

print()


if not scenes:

    raise RuntimeError(
        "No valid scenes with NARRATION were found."
    )


# ============================================================
# CHECK IMAGE FOR EVERY SCENE
# ============================================================

print()
print("========================================")
print("CHECKING SCENE IMAGES")
print("========================================")
print()


for scene in scenes:

    number = scene["number"]

    image_path = os.path.join(
        IMAGE_DIR,
        f"scene_{number:02d}.png"
    )

    print(
        f"Scene {number}:",
        image_path
    )

    if not os.path.isfile(image_path):

        raise RuntimeError(
            f"Missing scene image for Scene {number}: "
            f"{image_path}"
        )

    scene["image"] = image_path


print()
print(
    "All required scene images are present."
)
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
print("========================================")
print("LOADING TAGALOG TTS")
print("========================================")
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
# GENERATE SCENE CLIPS
# ============================================================

scene_clips = []


for scene in scenes:

    number = scene["number"]
    narration = scene["narration"]
    image_path = scene["image"]

    print()
    print("================================")
    print(f"SCENE {number}")
    print("================================")
    print()

    print(
        "Image:",
        image_path
    )

    print()

    print(
        "Narration:",
        narration
    )

    print()

    # --------------------------------------------------------
    # GENERATE AUDIO
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

    waveform = output.waveform

    waveform = (
        waveform
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


    # --------------------------------------------------------
    # AUDIO DURATION
    # --------------------------------------------------------

    audio_duration = get_audio_duration(
        audio_path
    )

    duration = (
        audio_duration
        + END_PADDING
    )


    print(
        f"Audio duration: {audio_duration:.2f}s"
    )

    print(
        f"Scene duration: {duration:.2f}s"
    )


    # --------------------------------------------------------
    # CREATE VIDEO CLIP
    # --------------------------------------------------------

    clip_path = os.path.join(
        SCENE_DIR,
        f"scene_{number:02d}.mp4"
    )


    # --------------------------------------------------------
    # CINEMATIC ZOOM
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


    run_command(
        command
    )


    if not os.path.isfile(
        clip_path
    ):

        raise RuntimeError(
            f"Scene clip was not created: {clip_path}"
        )


    scene_clips.append(
        clip_path
    )


    print()
    print(
        f"Scene {number} video created."
    )
    print()


# ============================================================
# VERIFY CLIPS
# ============================================================

print()
print("========================================")
print("VERIFYING SCENE CLIPS")
print("========================================")
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


print()


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
print(
    "Concat file created:"
)
print(
    concat_file
)
print()


# ============================================================
# COMBINE ALL SCENES
# ============================================================
#
# IMPORTANT:
#
# We intentionally DO NOT use:
#
# -c copy
#
# We re-encode the final video so every scene's
# video frames are preserved correctly.
#
# ============================================================

print()
print("========================================")
print("COMBINING ALL SCENES")
print("========================================")
print()


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
# VERIFY FINAL VIDEO
# ============================================================

print()
print("========================================")
print("VERIFYING FINAL VIDEO")
print("========================================")
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


# ============================================================
# CHECK VIDEO + AUDIO
# ============================================================

try:

    probe_data = json.loads(
        probe.stdout
    )

except json.JSONDecodeError:

    raise RuntimeError(
        "Could not read FFprobe JSON."
    )


streams = probe_data.get(
    "streams",
    []
)


has_video = any(
    stream.get("codec_type") == "video"
    for stream in streams
)


has_audio = any(
    stream.get("codec_type") == "audio"
    for stream in streams
)


if not has_video:

    raise RuntimeError(
        "Final video does not contain a video stream."
    )


if not has_audio:

    raise RuntimeError(
        "Final video does not contain an audio stream."
    )


print()
print(
    "Video stream: OK"
)

print(
    "Audio stream: OK"
)

print()


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
print(
    "Video + Audio successfully combined."
)
print()
