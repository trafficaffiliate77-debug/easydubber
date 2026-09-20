import os
import base64
import requests

WIDTH = 1080
HEIGHT = 1920

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

STYLE = """
Ultra cinematic anime, detailed characters,
consistent protagonist, dramatic lighting,
vertical 9:16, high quality, no text,
no watermark, expressive faces.
"""

def create_scene_image(scene_number, scene_text):

    os.makedirs("output/images", exist_ok=True)

    prompt = f"""
{STYLE}

Scene {scene_number}

{scene_text}

Camera: cinematic composition, vertical portrait.
"""

    response = requests.post(
        "https://api.openai.com/v1/images/generations",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "gpt-image-1",
            "size": "1024x1792",
            "prompt": prompt,
        },
        timeout=300,
    )

    response.raise_for_status()

    image_b64 = response.json()["data"][0]["b64_json"]

    output = f"output/images/scene_{scene_number:02d}.png"

    with open(output, "wb") as f:
        f.write(base64.b64decode(image_b64))

    print("Created:", output)

    return output
