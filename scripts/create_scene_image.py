from PIL import Image, ImageDraw, ImageFont
import os
import hashlib


WIDTH = 1080
HEIGHT = 1920


def create_scene_image(scene_number, scene_text):

    os.makedirs("output/images", exist_ok=True)

    # Create a deterministic color from the scene text
    digest = hashlib.md5(
        scene_text.encode("utf-8")
    ).hexdigest()

    r = int(digest[0:2], 16)
    g = int(digest[2:4], 16)
    b = int(digest[4:6], 16)

    # Make the colors brighter/cinematic
    r = min(255, r + 60)
    g = min(255, g + 60)
    b = min(255, b + 60)

    image = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        (r, g, b)
    )

    draw = ImageDraw.Draw(image)

    # Add large cinematic circles
    draw.ellipse(
        (-250, 200, 700, 1150),
        fill=(255, 255, 255)
    )

    draw.ellipse(
        (500, 900, 1300, 1900),
        fill=(30, 30, 30)
    )

    # Add a dark transparent-style panel
    draw.rectangle(
        (70, 1350, 1010, 1800),
        fill=(15, 15, 25)
    )

    # Font
    font_path = (
        "/usr/share/fonts/truetype/dejavu/"
        "DejaVuSans-Bold.ttf"
    )

    title_font = ImageFont.truetype(
        font_path,
        70
    )

    scene_font = ImageFont.truetype(
        font_path,
        42
    )

    # Title
    draw.text(
        (80, 90),
        "EASYDUBBER",
        font=title_font,
        fill="white"
    )

    draw.text(
        (80, 180),
        f"SCENE {scene_number}",
        font=scene_font,
        fill="white"
    )

    # Short visual description
    clean_text = scene_text.replace(
        "\n",
        " "
    )

    if len(clean_text) > 180:
        clean_text = clean_text[:180] + "..."

    draw.text(
        (110, 1450),
        clean_text,
        font=scene_font,
        fill="white",
        spacing=15
    )

    # Decorative cinematic lines
    draw.line(
        (80, 1270, 1000, 1270),
        fill="white",
        width=5
    )

    draw.line(
        (80, 1840, 1000, 1840),
        fill="white",
        width=3
    )

    output_file = (
        f"output/images/scene_{scene_number:02d}.png"
    )

    image.save(
        output_file,
        quality=95
    )

    print(
        "Created visual:",
        output_file
    )

    return output_file


if __name__ == "__main__":

    create_scene_image(
        1,
        "A mysterious young man discovers a glowing black technology core."
    )
