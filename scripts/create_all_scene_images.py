import os
import re
import firebase_admin
from firebase_admin import credentials, firestore

from create_scene_image import create_scene_image


# ============================================================
# EASYDUBBER — CREATE ALL SCENE IMAGES
# ============================================================
# Creates one image for EVERY scene found in the story.
# No hard 10-scene limit.
# ============================================================


def initialize_firebase():

    service_account = os.environ.get(
        "FIREBASE_SERVICE_ACCOUNT"
    )

    if not service_account:
        raise RuntimeError(
            "FIREBASE_SERVICE_ACCOUNT environment variable is missing."
        )

    import json

    service_account_info = json.loads(service_account)

    cred = credentials.Certificate(
        service_account_info
    )

    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)

    return firestore.client()


def get_generated_episode(db):

    episodes_ref = db.collection("episodes")

    docs = (
        episodes_ref
        .where("status", "==", "generated")
        .limit(1)
        .stream()
    )

    for doc in docs:
        return doc

    return None


def parse_scenes(story):

    lines = story.splitlines()

    scenes = []

    current_number = None
    current_visual = ""

    for line in lines:

        line = line.strip()

        # ----------------------------------------------------
        # Detect scene number
        # Supports:
        # SCENE 1
        # SCENE 2
        # SCENE 11
        # ----------------------------------------------------

        scene_match = re.match(
            r"^SCENE\s+(\d+)",
            line,
            re.IGNORECASE
        )

        if scene_match:

            # Save previous scene first
            if current_number is not None and current_visual:

                scenes.append(
                    (
                        current_number,
                        current_visual
                    )
                )

            current_number = int(
                scene_match.group(1)
            )

            current_visual = ""

            continue

        # ----------------------------------------------------
        # Get VISUAL line
        # ----------------------------------------------------

        if line.upper().startswith("VISUAL:"):

            visual = line.split(
                ":",
                1
            )[1].strip()

            current_visual = visual

    # --------------------------------------------------------
    # Save final scene
    # --------------------------------------------------------

    if current_number is not None and current_visual:

        scenes.append(
            (
                current_number,
                current_visual
            )
        )

    return scenes


def main():

    print()
    print("==============================================")
    print("EASYDUBBER — CREATE ALL SCENE IMAGES")
    print("==============================================")
    print()

    db = initialize_firebase()

    episode_doc = get_generated_episode(db)

    if not episode_doc:

        print("No generated episode found.")
        print()

        return

    episode = episode_doc.to_dict()

    title = episode.get(
        "title",
        "Untitled Episode"
    )

    story = episode.get(
        "story",
        ""
    )

    print("Episode:", title)
    print()

    if not story.strip():

        raise RuntimeError(
            "Episode has no story."
        )

    # --------------------------------------------------------
    # Parse ALL scenes
    # --------------------------------------------------------

    scenes = parse_scenes(story)

    print(
        "Scenes found:",
        len(scenes)
    )
    print()

    if not scenes:

        raise RuntimeError(
            "No scenes with VISUAL lines were found."
        )

    # --------------------------------------------------------
    # Create output directory
    # --------------------------------------------------------

    output_dir = "output/images"

    os.makedirs(
        output_dir,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Create EVERY scene image
    # --------------------------------------------------------

    for number, visual in scenes:

        print()
        print("----------------------------------------------")
        print(
            f"Creating Scene {number}"
        )
        print("----------------------------------------------")
        print()

        if not visual:

            print(
                f"WARNING: Scene {number} has no visual."
            )

            continue

        print("Visual:")
        print(visual)
        print()

        try:

            create_scene_image(
                number,
                visual
            )

            print()
            print(
                f"Scene {number} image created successfully."
            )

        except Exception as e:

            print()
            print(
                f"ERROR creating Scene {number}:"
            )
            print(e)
            print()

            raise

    # --------------------------------------------------------
    # Verify all images exist
    # --------------------------------------------------------

    print()
    print("==============================================")
    print("VERIFYING SCENE IMAGES")
    print("==============================================")
    print()

    missing = []

    for number, visual in scenes:

        image_path = os.path.join(
            output_dir,
            f"scene_{number:02d}.png"
        )

        if os.path.exists(image_path):

            size = os.path.getsize(
                image_path
            )

            print(
                f"Scene {number}: OK "
                f"({size:,} bytes)"
            )

        else:

            print(
                f"Scene {number}: MISSING"
            )

            missing.append(
                number
            )

    print()

    if missing:

        raise RuntimeError(
            "Missing scene images: "
            + ", ".join(
                str(x)
                for x in missing
            )
        )

    print("==============================================")
    print("ALL SCENE IMAGES CREATED")
    print("==============================================")
    print()

    print(
        f"Total scene images: {len(scenes)}"
    )

    print()


if __name__ == "__main__":
    main()
