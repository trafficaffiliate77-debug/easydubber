import os
import subprocess
import textwrap

os.makedirs("output", exist_ok=True)

# Create a simple 30-second vertical video.
# This is only our first rendering test.

video_path = "output/easydubber_test.mp4"

command = [
    "ffmpeg",
    "-y",
    "-f", "lavfi",
    "-i",
    "color=c=black:s=1080x1920:r=30",
    "-t", "30",
    "-vf",
    "drawtext="
    "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
    "text='EasyDubber Episode 1':"
    "fontcolor=white:"
    "fontsize=70:"
    "x=(w-text_w)/2:"
    "y=(h-text_h)/2",
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    video_path
]

subprocess.run(command, check=True)

print("================================")
print("VIDEO CREATED")
print("================================")
print(video_path)
