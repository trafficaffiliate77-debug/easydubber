import os
import requests
from urllib.parse import quote

WIDTH = 1080
HEIGHT = 1920

STYLE = """
cinematic anime, futuristic technology, consistent characters,
dramatic lighting, ultra detailed, vertical portrait, 9:16,
high quality, no text, no watermark
"""

def create_scene_image(scene_number, scene_text):
    os.makedirs("output/images", exist_ok=True)

    prompt = f"{STYLE}. {scene_text}"

    url = (
        "https://image.pollinations.ai/prompt/"
        + quote(prompt)
        + "?width=1080&height=1920&model=flux"
    )

    output = f"output/images/scene_{scene_number:02d}.png"

    r = requests.get(url, timeout=300)
    r.raise_for_status()

    with open(output, "wb") as f:
        f.write(r.content)

    print("Created:", output)
    return output
