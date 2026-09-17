import os
import subprocess

os.makedirs("output", exist_ok=True)

scenes = [
    "SCENE 1\nThe mysterious beginning",
    "SCENE 2\nSomething strange appears",
    "SCENE 3\nA hidden secret is discovered",
    "SCENE 4\nEverything suddenly changes",
    "SCENE 5\nA mysterious person arrives",
    "SCENE 6\nThe danger becomes real",
    "SCENE 7\nThe hidden power awakens",
    "SCENE 8\nA difficult decision must be made",
    "SCENE 9\nThe shocking truth is revealed",
    "SCENE 10\nTO BE CONTINUED..."
]

scene_files = []

for i, text in enumerate(scenes):
    filename = f"output/scene_{i:02d}.mp4"
    scene_files.append(filename)

    escaped = text.replace("'", "'\\\\''").replace("\n", "\\n")

    command = [
        "ffmpeg",
        "-y",
        "-f", "lavfi",
        "-i", "color=c=black:s=1080x1920:r=30",
        "-t", "3",
        "-vf",
        f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"text='{escaped}':"
        f"fontcolor=white:"
        f"fontsize=58:"
        f"x=(w-text_w)/2:"
        f"y=(h-text_h)/2:"
        f"line_spacing=20",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        filename
    ]

    subprocess.run(command, check=True)

# Create concat file
concat_file = "output/concat.txt"

with open(concat_file, "w") as f:
    for filename in scene_files:
        f.write(f"file '{os.path.abspath(filename)}'\n")

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

print("================================")
print("EASYDUBBER EPISODE CREATED")
print("================================")
print(final_video)
