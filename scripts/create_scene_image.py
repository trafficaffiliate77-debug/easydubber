from PIL import Image, ImageDraw, ImageFont
import os
import hashlib


WIDTH = 1080
HEIGHT = 1920


def create_scene_image(scene_number, scene_text):

    os.makedirs("output/images", exist_ok=True)

    digest = hashlib.md5(
        scene_text.encode("utf-8")
    ).hexdigest()

    r = min(255, int(digest[0:2], 16) + 60)
    g = min(255, int(digest[2:4], 16) + 60)
    b = min(255, int(digest[4:6], 16) + 60)

    image = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        (r, g, b)
    )

    draw = ImageDraw.Draw(image)

    # Cinematic background shapes
    draw.ellipse(
        (-300, 100, 700, 1100),
        fill=(255, 255, 255)
    )

    draw.ellipse(
        (450, 850, 1350, 1950),
        fill=(25, 25, 35)
    )

    # Main cinematic panel
    draw.rounded_rectangle(
        (70, 1320, 1010, 1810),
        radius=35,
        fill=(10, 10, 20)
    )

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

    small_font = ImageFont.truetype(
        font_path,
        34
    )

    draw.text(
        (80, 80),
        "EASYDUBBER",
        font=title_font,
        fill="white"
    )

    draw.text(
        (80, 175),
        f"SCENE {scene_number}",
        font=small_font,
        fill="white"
    )

    clean_text = scene_text.replace(
        "\n",
        " "
    )

    if len(clean_text) > 220:
        clean_text = clean_text[:220] + "..."

    draw.text(
        (110, 1410),
        clean_text,
        font=scene_font,
        fill="white",
        spacing=18
    )

    draw.line(
        (80, 1260, 1000, 1260),
        fill="white",
        width=5
    )

    draw.text(
        (80, 1840),
        "COLORFUL CINEMATIC STORY",
        font=small_font,
        fill="white"
    )

    output_file = (
        f"output/images/scene_{scene_number:02d}.png"
    )

    image.save(output_file)

    print("Created:", output_file)

    return output_file
