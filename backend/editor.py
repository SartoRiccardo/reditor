import os
import shutil
import urllib3
import backend.requests
import backend.utils
import backend.image
from backend.paths import DATA_PATH, DOWNLOAD_PATH, p
import time
from PIL import Image
import pytesseract
import re
from random import choice
from classes.video import Document, Scene, Transition, Soundtrack, Part
pytesseract.pytesseract.tesseract_cmd = r"/usr/local/bin/tesseract"


# GLOBAL VARIABLES
EMPTY_GLOBAL_CONFIG = """
last-bgm-path /
last-thumbnail-image-path /
"""[1:]
pool = urllib3.PoolManager()


# ENUMS
NO_PROJECT = -1


# CLASSES

class ScenePart:
    @staticmethod
    def part_to_object(lines):
        lines = lines.split("\n")
        wait = float(lines[3]) if backend.utils.is_number(lines[3]) else 1
        ob = {
            "text": lines[1],
            "voice": lines[2],
            "wait": wait,
        }
        if lines[0].startswith("["):
            regex = r"\[(\S+?)=([^]]+?)]"
            match = re.findall(regex, lines[0])
            for field_name, field_value in match:
                ob[field_name] = field_value
        else:
            coords = lines[0].split(";")
            ob["crop"] = {
                "x": float(coords[0]),
                "y": float(coords[1]),
                "w": float(coords[2]),
                "h": float(coords[3]),
            }
        return ob

    @staticmethod
    def object_to_text(scene: dict):
        standard_keys = ["crop", "text", "voice", "wait"]
        fields = []
        for key in scene.keys():
            if key not in standard_keys:
                fields.append(f"[{key}={scene[key]}]")

        if len(fields) == 0:
            first_line = f"{scene['crop']['x']};{scene['crop']['y']};{scene['crop']['w']};{scene['crop']['h']}"
        else:
            first_line = "".join(fields)

        return (
            first_line + "\n" +
            scene["text"] + "\n" +
            scene["voice"] + "\n" +
            str(scene["wait"])
        )


# METHODS
def init():
    if not os.path.exists(DATA_PATH):
        os.mkdir(DATA_PATH)
    if not os.path.exists(DOWNLOAD_PATH):
        os.mkdir(DOWNLOAD_PATH)

    required_dirs = ["/assets", "/saves", "/saves/index.csv", "/logs", "/config.txt"]

    for d in required_dirs:
        if not os.path.exists(p(d)):
            if "." in d:
                f = open(p(d), "w")
                if d == "/config.txt":
                    f.write(EMPTY_GLOBAL_CONFIG)
                f.close()
            else:
                os.mkdir(p(d))
                if d == "/assets":
                    init_assets(p(d))


def init_assets(base_path):
    files = {
        "/background.mp4": "https://cdn.discordapp.com/attachments/924255725390270474/924255906345140234/background.mp4",
        "/intro.mp4": "https://cdn.discordapp.com/attachments/924255725390270474/924255934602149909/intro.mp4",
        "/outro.mp4": "https://cdn.discordapp.com/attachments/924255725390270474/924255975391760424/outro.mp4",
        "/transition.mp4": "https://cdn.discordapp.com/attachments/924255725390270474/924255991745376256/transition.mp4",
        "/thumbnail": {
            "/thumbnail-font-bold.ttf": "https://cdn.discordapp.com/attachments/924255725390270474/924256041695330344/thumbnail-font-bold.ttf",
            "/thumbnail-font-regular.ttf": "https://cdn.discordapp.com/attachments/924255725390270474/924256058875211837/thumbnail-font-regular.ttf",
            "/watermark.png": "https://cdn.discordapp.com/attachments/924255725390270474/924256073114877962/watermark.png",
        }
    }
    download_assets(base_path, files)


def download_assets(base_path, files):
    for key in files:
        if type(files[key]) == str:
            backend.requests.download_resource(files[key], base_path+key)
        else:
            os.mkdir(base_path+key)
            download_assets(base_path+key, files[key])


def get_config(document_id, key):
    if document_id != NO_PROJECT:
        return Document(document_id).get_config(key)

    config_path = p("/config.txt")
    config = open(config_path)
    ret = None
    for ln in config:
        parts = ln.strip().split(" ")
        if parts[0] == key:
            ret = " ".join(parts[1:])
            break
    config.close()
    return ret


def write_config(document_id, key, value):
    if document_id != NO_PROJECT:
        Document(document_id).write_config(key, value)

    config_path = p("/config.txt")
    config = open(config_path)
    file = []
    for ln in config:
        parts = ln.strip().split(" ")
        if parts[0] == key:
            file.append(f"{key} {value}\n")
        else:
            file.append(ln)
    config.close()

    config = open(config_path, "w")
    [config.write(ln) for ln in file]
    config.close()


def get_cache_dir(file_id):
    return Document.get_cache_dir(file_id)


# REQUEST HANDLERS
def get_file_info(document_id):
    return Document(document_id, load=True)


def get_files():
    return Document.list()


def create_file(name: str):
    return Document.new(name)


def add_to_script(document_id: str, *scenes):
    scene_types = []
    for sc in scenes:
        if sc == "soundtrack":
            scene_types.append(Soundtrack)
        elif sc == "soundtrack":
            scene_types.append(Scene)
        else:
            scene_types.append(Transition)
    return Document(document_id).add_empty_scenes(*scene_types)


def delete_file(document_id):
    return Document(document_id).delete()


def change_scene_info(document_id, scene_id, part_idx, new_part):
    return Document(document_id).get_scene(scene_id).change_part(part_idx, new_part)


def get_scene_info(document_id, scene_id):
    scene = Document(document_id).get_scene(scene_id)
    return scene


def relocate_scene(document_id: int, old_idx: int, new_idx: int):
    return Document(document_id).relocate_scene(old_idx, new_idx)


def delete_script_part(document_id: int, scene_id: int, part_idx):
    return Document(document_id).get_scene(scene_id).delete_part(part_idx)


def delete_scene(document_id, scene_idx):
    return Document(document_id).delete_scene(scene_idx)


def set_media(document_id: int, scene_id: int, media):
    return Document(document_id).get_scene(scene_id).set_media_as_base64(media)


def set_song(document_id: int, soundtrack_id: int, name: str, payload, is_path=False):
    return Document(document_id).set_song(soundtrack_id, name, payload, is_path)


def export_file(document_id, log_callback=None, export_dir=None):
    document = Document(document_id)
    document.load()
    if export_dir is None:
        export_dir = DOWNLOAD_PATH + f"/{document.name}-export"
    return document.export(export_dir, log_callback)


def export_multiple(document_ids):
    for doc in document_ids:
        export_file(doc)


def download_images(platform, target, options={}):
    """
    Downloads images from a platform.
    :param platform: Union["reddit", "twitter", "askreddit", "reddit-media"]
    :param target: str: The username or subreddit to target.
    :param options.isSelfpostVideo: bool: Whether the video is only made of reddit text posts.
    """
    image_urls = []
    if platform == "reddit":
        image_urls = backend.requests.subreddit_image_posts(target, only_selfposts=options["isSelfpostVideo"])
    elif platform == "twitter":
        image_urls = backend.requests.twitter_user_images(target)

    if len(image_urls) == 0:
        return False

    tmp_dir = DATA_PATH + "/tmp"
    dl_dir = tmp_dir + "/download"
    if os.path.exists(dl_dir):
        shutil.rmtree(dl_dir)
    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)
    os.mkdir(dl_dir)

    for i in range(len(image_urls)):
        url = image_urls[i].path
        is_url = image_urls[i].is_url
        if is_url:
            backend.requests.download_image(url, dl_dir + f"/{i:05d}.png")
        else:
            shutil.move(url, dl_dir+f"/{i:05d}.png")

    shutil.make_archive(tmp_dir+f"/{target}", "zip", dl_dir)
    zip_path = tmp_dir+f"/{target}.zip"
    shutil.move(zip_path, DOWNLOAD_PATH+f"/{target}-{int(time.time())}.zip")

    return True


def load_video_duration(document_id: int, max_time=-1, max_chars=-1):
    """
    Loads the duration of a video.
    :param document_id: int: The number of the video to load the duration of.
    :param max_time: float: The max duration that can be downloaded. Useful for API limits.
    :param max_chars: int: The max number of characters that can be synthesized. Useful for API limits.
    :return: float: The duration, or None if an exception occurred.
    """
    return Document(document_id).get_duration(max_time, max_chars)


def detect_text(document_id: int, scene_id: int, crop: dict, substitute=True) -> str:
    """
    Detects text in an image thanks to tesseract, prettifies it, and returns it,
    :param scene_id: The internal ID of the scene to analize.
    :param crop: Crops the image to only focus on the text. Params are `x`, `y`, `w`, and `h`.
    :param document_id: The internal ID of the document the scene belongs to.
    :param substitute: Whether to substitute internet lingo with its meaning (e.g. "mfw" -> "my face when")
    :return: The detected text.
    """

    img_path = Document(document_id).get_scene(scene_id) + "/image.png"
    image = Image.open(img_path)
    width, height = image.size
    start_x = int(width*crop["x"] / 100)
    start_y = int(height*crop["y"] / 100)
    end_x = start_x + int(width*crop["w"] / 100)
    end_y = start_y + int(height*crop["h"] / 100)
    image = image.crop((start_x, start_y, end_x, end_y))

    text = pytesseract.image_to_string(image, lang="eng", config="--psm 11") \
        .replace("\n", " ")

    substitutions = [
        (" +", " "), ("(?:\*|”|\"|“|—|>|~)", ""), (":", "."), ("\|", "I"),
        ("qt", "cutie"), ("3\.14", "pie"), ("mfw", "my face when"), ("tfw", "that feel when"),
        ("https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)", "this link")
    ] if substitute else []
    for pre, sub in substitutions:
        text = re.sub(pre, sub, text)

    return text.strip()


# AUTOMATED

def make_media_video(target: str, bgm_dir: str, max_duration=10*60):
    posts = backend.requests.media_submissions(target)

    name = f"{target}-auto"
    document = Document.new(name)
    tmp_path = DATA_PATH + "/tmp/"
    reactions = ["think", "joy", "shrug", "smug"]

    sorted_scenes = []
    for i in range(len(posts)):
        posts[i].path = backend.requests.download_resource(posts[i].url, tmp_path+"media", True)
        if not posts[i].path:
            continue

        media_ext = backend.utils.get_extension(posts[i].path)
        scene = document.add_empty_scenes(Scene)[0]

        # Detect scene media duration.
        if media_ext == "mp4":
            media_duration = backend.utils.get_video_length(posts[i].path)["total"]
        elif media_ext == "gif":
            media_duration = backend.utils.get_gif_length(posts[i].path)["total"]
        else:
            media_duration = 0

        # Sort the scene (ASC) based on its media duration
        # (only keeping track. Real sorting happens later).
        duration_data = {"scene_number": scene.id, "t": media_duration}
        for j in range(len(sorted_scenes)):
            sort_sc = sorted_scenes[j]
            if j == len(sorted_scenes)-1 and sort_sc["t"] <= media_duration:
                sorted_scenes.append(duration_data)
                break
            elif j == 0 and sort_sc["t"] > media_duration or \
                    sorted_scenes[j - 1]["t"] <= media_duration < sort_sc["t"]:
                sorted_scenes.insert(j, duration_data)
                break

        if len(sorted_scenes) == 0:
            sorted_scenes.append(duration_data)

        # Create the script for the scene and write it
        voice = backend.image.get_voice_for_scene()
        script = [
            Part({
                "text": posts[i].title,
                "voice": voice,
                "wait": 1.0,
                "fields": {"written": posts[i].title},
            }),
            Part({
                "crop": {"x": 0, "y": 0, "w": 100, "h": 100},
                "text": "",
                "voice": voice,
                "wait": 0 if media_ext in ["mp4", "gif"] else 5,
            }),
        ]
        if posts[i].comment:
            voice = backend.image.get_voice_for_scene()
            script.append(Part({
                "text": posts[i].comment,
                "voice": voice,
                "wait": 1.0,
                "fields": {"reaction": choice(reactions)},
            }))
        scene.add_parts(*script)
        scene.set_media_as_path(posts[i].path)
        scene.write_scene()

    # Reorder scenes, now sorted
    for i in range(len(sorted_scenes)):
        scene_dir_from = Scene.get_path(document.id, sorted_scenes[i]["scene_number"])
        scene_dir_to = Scene.get_path(document.id, i+1)
        shutil.move(scene_dir_from, scene_dir_to+"-sorting")
    for i in range(len(sorted_scenes)):
        scene_dir = Scene.get_path(document.id, i+1)
        shutil.move(scene_dir+"-sorting", scene_dir)

    document.load()
    document.truncate_duration(max_duration)
    document.add_soundtracks(bgm_dir)
    return document


def make_askreddit_video(target, bgm_dir=None, max_duration=10*60, comment_depth=5):
    name = f"{target}-auto"
    document = Document.new(name)

    posts = backend.requests.post_comments(target, max_comments_per_tree=comment_depth)
    for i in range(len(posts)):
        path = posts[i].path
        if os.path.exists(path+".txt"):
            scene = document.add_empty_scenes(Scene)[0]
            scene.set_media_as_path(path)
            scene.set_script(f"{path}.txt", is_file=True)

    document.load()
    document.truncate_duration(max_duration)
    if bgm_dir:
        document.add_soundtracks(bgm_dir)
    return document


init()
