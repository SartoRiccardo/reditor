import os
import csv
import shutil
import base64
import urllib3
import backend.requests
import backend.utils
from backend.paths import DATA_PATH, DOWNLOAD_PATH, LOG_PATH, p, get_project_dir, get_scene_dir
import time
import traceback
from PIL import Image
import pytesseract
import re
from random import randint, choice
pytesseract.pytesseract.tesseract_cmd = r"/usr/local/bin/tesseract"


# GLOBAL VARIABLES
EMPTY_SOUNDTRACK = {
    "type": "soundtrack",
    "duration": {"m": 0, "s": 0},
    "name": None,
    "path": None,
    "number": 1
}
EMPTY_SCRIPT = """
[intro]
[ost]00001;
[outro]
"""[1:-1]
EMPTY_CONFIG = """
next-scene-id 1
next-soundtrack-id 2
"""[1:]
EMPTY_GLOBAL_CONFIG = """
last-bgm-path /
last-thumbnail-image-path /
"""[1:]
open_file_id = None
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


def get_config(project_id, variable):
    if project_id == NO_PROJECT:
        config_path = p("/config.txt")
    else:
        config_path = get_project_dir(project_id) + "/config.txt"
    config = open(config_path)
    ret = None
    for ln in config:
        parts = ln.strip().split(" ")
        if parts[0] == variable:
            ret = " ".join(parts[1:])
            break
    config.close()
    return ret


def write_config(project_id, variable, newval):
    if project_id == NO_PROJECT:
        config_path = p("/config.txt")
    else:
        config_path = get_project_dir(project_id) + "/config.txt"
    config = open(config_path)
    file = []
    for ln in config:
        parts = ln.strip().split(" ")
        if parts[0] == variable:
            file.append(f"{variable} {newval}\n")
        else:
            file.append(ln)
    config.close()

    config = open(config_path, "w")
    [config.write(ln) for ln in file]
    config.close()


def get_cache_dir(file_id=open_file_id):
    ret = get_project_dir(file_id) + "/cache"
    if not os.path.exists(ret):
        os.mkdir(ret)
    return ret


def get_scene_duration(scene, file=None):
    """
    Gets the duration in seconds of the currently loaded audios of a scene.
    :param scene: int: The number of the scene
    :param file: int: The number of the file (defaults to the value of open_file_id)
    :return: float: The duration (in seconds) of the scene.
    """
    if file is None:
        file = open_file_id

    scene_dir = None
    if isinstance(scene, dict):
        script = scene["script"]
    else:
        scene_dir = get_scene_dir(file, scene)
        fscript = open(scene_dir+"/script.txt")
        script = backend.utils.parse_script(fscript)
        fscript.close()

    cache_dir = get_cache_dir(file)
    duration = 0
    if scene_dir:
        if os.path.exists(scene_dir+"/media.mp4"):
            duration += backend.utils.get_video_length(scene_dir+"/media.mp4")["total"]
        elif os.path.exists(scene_dir+"/media.gif"):
            duration += backend.utils.get_gif_length(scene_dir+"/media.gif")["total"]

    for i in range(len(script)):
        part = script[i]
        if part["text"]:
            aud_path = cache_dir + f"/{scene:05d}-{i:05d}.mp3"
            if os.path.exists(aud_path):
                duration += backend.utils.get_audio_length(aud_path)["total"]
            else:
                duration = None
                break
        duration += part["wait"]

    return duration


def make_automatic_video(document_name, image_urls, options):
    """
    Creates a video automatically with the given arguments
    :param document_name: str: the name of the document to create.
    :param image_urls: List<ImageLink>: a collection of images.
    :param options.maxDuration: int: the max duration of the video, in seconds.
    :param options.bgmDir: str: a path to a folder that contains MP3 files and/or subfolders containing the former.
    """
    file = create_file(document_name)
    for i in range(len(image_urls)):
        path = image_urls[i].path
        if os.path.exists(path+".txt"):
            scene = add_to_script("scene", document=file["id"])
            scene_dir = get_scene_dir(file["id"], scene[0]["number"])
            shutil.move(path, scene_dir+"/media.png")
            shutil.move(path+".txt", scene_dir+"/script.txt")

    load_video_duration(document=file["id"])
    add_soundtracks_and_truncate(file, options)


# REQUEST HANDLERS
def get_file_info(id):
    """
    Returns info about the file with given ID.
    :param id: int: the ID of the file to analyze.
    :return: dict: The file data, as following:
        {
            "path": str: Absolute path to the file document
            "scenes": int: No. of scenes
            "components": int: No. of components
            "script": List<Union[transition, soundtrack, scene]>
        }

        All components of "script" have a `type` field that describes what they are.
        Soundtracks are defined as following:
        {
            "name": str: the file name of the soundtrack.
            "duration": dict: the duration, can be extracted with keys `m`, `s`, `ms`, and `total`.
            "path": str: the full path of the file.
            "number": int: the internal ID of the soundtrack in the file.
        }

        Scenes are defined as the following:
        {
            "duration": int: the duration, in seconds, of the scene.
            "number": int: the internal ID of the scene in the file.
        }
    """
    finfo = open(p("/saves/index.csv"), "r")
    reader = csv.reader(finfo, delimiter=";", quotechar="\"")

    ret = None
    for row in reader:
        if int(row[0]) == id:
            ret = {
                "id": id,
                "name": row[1]
            }

    finfo.close()

    if not ret:
        return None

    ret["path"] = p(f"/saves/{id:05d}")
    fscript = open(ret["path"]+"/script.txt", "r")

    components = 0
    scenes = 0
    script = []
    for ln in fscript:
        ln = ln.strip()
        if ln.startswith("["):
            parts = ln.split("]")
            command = parts[0][1:]
            if command == "ost" and len(parts) > 1:
                parts = parts[:1] + "]".join(parts[1:]).split(";")
                soundtrack_id = int(parts[1])
                audio_path = ret["path"]+f"/soundtrack/{soundtrack_id:05d}.mp3"
                script.append({
                    "type": "soundtrack",
                    "name": ";".join(parts[2:]),
                    "duration": backend.utils.get_audio_length(audio_path),
                    "path": audio_path,
                    "number": soundtrack_id,
                })
            elif command == "transition":
                script.append({"type": "transition"})
        else:
            scenes += 1
            script.append({
                "type": "scene",
                "number": int(ln),
                "duration": get_scene_duration(int(ln), id)
            })

        if ln not in ["[intro]", "[outro]"]:
            components += 1
    fscript.close()

    ret = {
        **ret,
        "scenes": scenes,
        "components": components,
        "script": script,
    }

    return ret


def get_files():
    """
    Gets a list of the available files.
    :return: List<file>: A list of files.
        Files being defined as following:
        {
            "id": int: The internal ID of the file.
            "name": str: The name of the file.
        }
    """
    finfo = open(p("/saves/index.csv"), "r")
    reader = csv.reader(finfo, delimiter=";", quotechar="\"")

    ret = []
    for row in reader:
        ret.append({
            "id": int(row[0]), "name": row[1]
        })

    finfo.close()
    return ret


def create_file(name):
    """
    Creates a file and returns it.
    :return: file: The newly created file.
        Files being defined as following:
        {
            "id": int: The internal ID of the file.
            "name": str: The name of the file.
        }
    """
    finfo_r = open(p("/saves/index.csv"), "r")
    reader = csv.reader(finfo_r, delimiter=";", quotechar="\"")

    last_id = -1
    for row in reader:
        last_id = int(row[0])

    finfo_r.close()
    new_id = last_id+1
    ret = {
        "id": new_id,
        "name": name,
    }
    finfo_a = open(p("/saves/index.csv"), "a")
    writer = csv.writer(finfo_a, delimiter=";", quotechar="\"")
    writer.writerow([ret["id"], ret["name"]])
    finfo_a.close()

    path = p(f"/saves/{new_id:05d}")
    if os.path.exists(path):
        shutil.rmtree(path)

    os.mkdir(path)
    os.mkdir(path + "/soundtrack")
    os.mkdir(path + "/scenes")
    fscript = open(path + "/script.txt", "w")
    fscript.write(EMPTY_SCRIPT)
    fscript.close()
    fconfig = open(path + "/config.txt", "w")
    fconfig.write(EMPTY_CONFIG)
    fconfig.close()

    return ret


def open_file(id):
    global open_file_id
    open_file_id = id


def close_file():
    global open_file_id
    open_file_id = None


def add_to_script(type, document=None):
    if document is None:
        document = open_file_id
    fscript = open(get_project_dir(document)+"/script.txt")

    script = []
    last_soundtrack_number = 1
    for ln in fscript:
        if "[ost]" in ln:
            last_soundtrack_number += 1
        script.append(ln)

    fscript.close()

    if not isinstance(type, list):
        type = [type]

    ret = []
    for t in type:
        if t == "soundtrack":
            new_ost_id = int(get_config(document, "next-soundtrack-id"))
            to_insert = f"[ost]{new_ost_id:05d};"
            new_soundtrack = {**EMPTY_SOUNDTRACK}
            new_soundtrack["number"] = new_ost_id
            ret.append(new_soundtrack)
            write_config(document, "next-soundtrack-id", new_ost_id+1)

        elif t == "scene":
            new_scene_id = int(get_config(document, "next-scene-id"))
            to_insert = f"{new_scene_id:05d}"
            ret.append({"type": "scene", "number": new_scene_id, "duration": 0})
            scene_path = get_scene_dir(document, new_scene_id)
            if os.path.exists(scene_path):
                shutil.rmtree(scene_path)
            os.mkdir(scene_path)
            open(scene_path+"/script.txt", "w").close()
            write_config(document, "next-scene-id", new_scene_id+1)

        else:
            to_insert = "[transition]"
            ret.append({"type": "transition"})
        script.insert(-1, to_insert+"\n")

    fscript = open(get_project_dir(document)+"/script.txt", "w")
    for ln in script:
        fscript.write(ln)
    fscript.close()

    return ret


def delete_file(id):
    finfo = open(p("/saves/index.csv"), "r")
    reader = csv.reader(finfo, delimiter=";", quotechar="\"")

    new_file = []
    for row in reader:
        if int(row[0]) != id:
            new_file.append(row)

    finfo.close()

    finfo = open(p("/saves/index.csv"), "w")
    writer = csv.writer(finfo, delimiter=";", quotechar="\"")
    for row in new_file:
        writer.writerow(row)

    finfo.close()

    if os.path.exists(get_project_dir(id)):
        shutil.rmtree(get_project_dir(id))


def change_scene_info(scene, script_index, new_script, document=None):
    if document is None:
        document = open_file_id

    fscene = open(get_scene_dir(document, scene)+"/script.txt")

    parts = backend.utils.parse_script(fscene)
    for i in range(len(parts)):
        p = parts[i]
        ScenePart.object_to_text(p)
    fscene.close()

    if len(parts) > script_index >= 0:
        parts[script_index] = new_script
    else:
        parts.append(new_script)

    fscene = open(get_scene_dir(document, scene)+"/script.txt", "w")
    for i in range(len(parts)):
        p = parts[i]
        fscene.write(ScenePart.object_to_text(p))
        if i < len(parts):
            fscene.write("\n\n")
    fscene.close()

    return True


def get_scene_info(scene, file=None):
    if file is None:
        file = open_file_id
    scene_dir = get_scene_dir(file, scene)
    fscript = open(scene_dir+"/script.txt")
    script = backend.utils.parse_script(fscript)
    fscript.close()

    duration = get_scene_duration(scene, file)

    media = None
    media_path = scene_dir+"/media.png"
    if os.path.exists(scene_dir+"/media.png"):
        imagebin = open(scene_dir+"/media.png", "rb")
        media = "data:image/png;base64," + base64.b64encode(imagebin.read()).decode()
        imagebin.close()
    elif os.path.exists(scene_dir+"/media.jpeg"):
        imagebin = open(scene_dir+"/media.jpeg", "rb")
        media_path = scene_dir+"/media.jpeg"
        media = "data:image/jpeg;base64," + base64.b64encode(imagebin.read()).decode()
        imagebin.close()
    elif os.path.exists(scene_dir+"/media.mp4"):
        media_path = scene_dir+"/media.mp4"
        media = "data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="
    elif os.path.exists(scene_dir+"/media.gif"):
        media_path = scene_dir+"/media.gif"
        media = "data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="

    return {
        "number": scene,
        "image": media,
        "media_path": media_path,
        "script": script,
        "last_change": os.path.getmtime(scene_dir+"/script.txt"),
        "duration": duration
    }


def relocate_scene(old_i, new_i, document=None):
    if document is None:
        document = open_file_id

    script_path = get_project_dir(document)+"/script.txt"
    fscript = open(script_path)
    script = [ln.strip() for ln in fscript]
    fscript.close()

    script.insert(new_i, script.pop(old_i))

    fscript = open(script_path, "w")
    for line in script:
        fscript.write(line + "\n")
    fscript.close()


def delete_script_part(scene, part_i):
    script_file = get_scene_dir(open_file_id, scene) + "/script.txt"
    fscript = open(script_file)
    script = backend.utils.parse_script(fscript)
    fscript.close()

    script.pop(part_i)

    fscript = open(script_file, "w")
    for i in range(len(script)):
        part = script[i]
        fscript.write(ScenePart.object_to_text(part))
        if i < len(script):
            fscript.write("\n\n")
    fscript.close()

    return True


def delete_scene(scene_i, document=None):
    if document is None:
        document = open_file_id

    script_path = get_project_dir(document)+"/script.txt"
    fscript = open(script_path)

    script = []
    to_delete = None
    i = 0
    for ln in fscript:
        if i != scene_i:
            script.append(ln.strip())
        else:
            to_delete = ln

        if ln.startswith("[ost]") and i == scene_i:
            soundtrack_id = int(ln[5:].split(";")[0])
        i += 1

    fscript.close()

    fscript = open(script_path, "w")
    for line in script:
        fscript.write(line + "\n")
    fscript.close()

    if to_delete:
        if "[" not in to_delete:
            scene_id = int(to_delete)
            scene_path = get_scene_dir(document, scene_id)
            if os.path.exists(scene_path):
                shutil.rmtree(scene_path)
        elif to_delete.startswith("[ost]"):
            ost_path = get_project_dir(document)+f"/soundtrack/{soundtrack_id:05d}.mp3"
            if os.path.exists(ost_path):
                os.remove(ost_path)


def set_image(scene, image):
    image_path = get_scene_dir(open_file_id, scene) + "/image."

    config, data = image.split(",")
    config = config.split(";")
    ext = "png"
    for c in config:
        if "data:image/" in c and "jpeg" in c:
            ext = "jpg"
    image_path += ext

    fimage = open(image_path, "wb")
    fimage.write(base64.b64decode(data.encode("ascii")))
    fimage.close()

    return True


def set_song(number, name, song_b64, is_path=False, document=None):
    if document is None:
        document = open_file_id
    if name.endswith(".mp3"):
        name = name[:-4]

    song_path = get_project_dir(document) + f"/soundtrack/{number:05d}.mp3"

    if is_path:
        shutil.copy(song_b64, song_path)
    else:
        config, data = song_b64.split(",")
        fsong = open(song_path, "wb")
        fsong.write(base64.b64decode(data.encode("ascii")))
        fsong.close()

    script_dir = get_project_dir(document) + "/script.txt"
    fscript = open(script_dir)

    new_script = []
    for ln in fscript:
        if ln.startswith("[ost]"):
            soundtrack_id = int(ln[5:].split(";")[0])
            if number == soundtrack_id:
                new_script.append(f"[ost]{soundtrack_id:05d};{name}\n")
            else:
                new_script.append(ln)
        else:
            new_script.append(ln)

    fscript.close()
    fscript = open(script_dir, "w")
    [fscript.write(ln) for ln in new_script]
    fscript.close()

    return {
        "type": "soundtrack",
        "duration": backend.utils.get_audio_length(song_path),
        "name": name,
        "path": song_path,
        "number": number,
    }


def export_file(document=None, log_callback=None):
    if document is None:
        document = open_file_id
    files = get_files()
    file_name = None
    for f in files:
        if f["id"] == document:
            file_name = f["name"]
            break

    if file_name is None:
        return

    export_dir = DOWNLOAD_PATH + f"/{file_name}-export"
    if os.path.exists(export_dir):
        shutil.rmtree(export_dir)
    os.mkdir(export_dir)
    try:
        if log_callback is None:
            log_callback = lambda x: x
        backend.video.export_video(document, export_dir,
                                   gui_callback=log_callback,
                                   video_name=file_name+".mp4"
        )
    except Exception as exc:
        fout = open("./err.txt", "w")
        fout.write(traceback.format_exc())
        fout.close()


def export_multiple(files):
    for f in files:
        export_file(f)


def download_images(platform, target, options={}):
    """
    Downloads images from a platform. Will generate a video automatically if some
    conditions are met.
    :param platform: Union["reddit", "twitter", "askreddit", "reddit-media"]
    :param target: str: The username or subreddit to target.
    :param options.isSelfpostVideo: bool: Whether the video is only made of reddit text posts.
    :param options.bgmDir: str: The directory containing MP3 files or subfolders with MP3 files.
    """
    image_urls = []
    if platform == "reddit":
        image_urls = backend.requests.subreddit_image_posts(target, only_selfposts=options["isSelfpostVideo"])
    elif platform == "twitter":
        image_urls = backend.requests.twitter_user_images(target)
    elif platform == "askreddit":
        if "http" in target:
            id_re = r"comments\/(.+?)\/"
            target = re.search(id_re, target).group(1)
        image_urls = backend.requests.post_comments(target)

    if len(image_urls) == 0 and platform != "reddit-media":
        return False

    tmp_dir = DATA_PATH + "/tmp"
    dl_dir = tmp_dir + "/download"
    if os.path.exists(dl_dir):
        shutil.rmtree(dl_dir)
    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)
    os.mkdir(dl_dir)

    automatic = (platform == "reddit" and options["isSelfpostVideo"]
                 or platform == "askreddit"
                 or platform == "reddit-media") \
                and options["bgmDir"]

    if not automatic:
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
    else:
        document_name = f"{target}"
        if platform == "reddit-media":
            media_posts = backend.requests.media_submissions(target)
            make_automatic_media_video(document_name, media_posts, options)
        else:
            make_automatic_video(document_name, image_urls, options)

    return True


def make_automatic_media_video(document_name, media_posts, options):
    """
    Creates a video made of media automatically with the given arguments
    :param document_name: str: the name of the document to create.
    :param image_urls: List<MediaPost>: a list of MediaPosts.
    :param options.maxDuration: int: the max duration of the video, in seconds.
    :param options.bgmDir: str: a path to a folder that contains MP3 files and/or subfolders containing the former.
    """
    file = create_file(document_name)
    tmp_path = DATA_PATH + "/tmp/"
    reactions = ["think", "joy", "shrug", "smug"]

    sorted_scenes = []
    for i in range(len(media_posts)):
        media_posts[i].path = backend.requests.download_resource(media_posts[i].url, tmp_path+"media", True)
        if not media_posts[i].path:
            continue

        media_ext = backend.utils.get_extension(media_posts[i].path)
        scene = add_to_script("scene", document=file["id"])

        # Detect scene media duration.
        if media_ext == "mp4":
            media_duration = backend.utils.get_video_length(media_posts[i].path)["total"]
        elif media_ext == "gif":
            media_duration = backend.utils.get_gif_length(media_posts[i].path)["total"]
        else:
            media_duration = 0

        # Sort the scene (ASC) based on its media duration
        # (only keeping track. Real sorting happens later).
        duration_obj = {"scene_number": scene[0]["number"], "t": media_duration}
        for j in range(len(sorted_scenes)):
            sort_sc = sorted_scenes[j]
            if j == len(sorted_scenes)-1 and sort_sc["t"] <= media_duration:
                sorted_scenes.append(duration_obj)
                break
            elif j == 0 and sort_sc["t"] > media_duration or \
                    sorted_scenes[j - 1]["t"] <= media_duration < sort_sc["t"]:
                sorted_scenes.insert(j, duration_obj)
                break

        if len(sorted_scenes) == 0:
            sorted_scenes.append(duration_obj)

        # Create the script for the scene and write it
        voice = backend.image.get_voice_for_scene()
        script = [
            {
                "written": media_posts[i].title,
                "text": media_posts[i].title,
                "voice": voice,
                "wait": 1.0,
            },
            {
                "crop": {"x": 0, "y": 0, "w": 100, "h": 100},
                "text": "",
                "voice": voice,
                "wait": 0 if media_ext in ["mp4", "gif"] else 5,
            },
        ]
        if media_posts[i].comment:
            voice = backend.image.get_voice_for_scene()
            script.append({
                "reaction": choice(reactions),
                "text": media_posts[i].comment,
                "voice": voice,
                "wait": 1.0,
            })
        fscript = open(media_posts[i].path+".txt", "w")
        fscript.write("\n\n".join(
            [ScenePart.object_to_text(sc) for sc in script]
        ))
        fscript.close()

        scene_dir = get_scene_dir(file["id"], scene[0]["number"])
        shutil.move(media_posts[i].path, scene_dir + f"/media.{media_ext}")
        shutil.move(media_posts[i].path+".txt", scene_dir+"/script.txt")

    # Reorder scenes, now sorted
    for i in range(len(sorted_scenes)):
        scene_dir_from = get_scene_dir(file["id"], sorted_scenes[i]["scene_number"])
        scene_dir_to = get_scene_dir(file["id"], i+1)
        shutil.move(scene_dir_from, scene_dir_to+"-sorting")
    for i in range(len(sorted_scenes)):
        scene_dir = get_scene_dir(file["id"], i+1)
        shutil.move(scene_dir+"-sorting", scene_dir)

    add_soundtracks_and_truncate(file, options)


def add_soundtracks_and_truncate(file, options):
    """
    Adds soundtracks to a file and cuts scenes if the length would make it overflow.
    :param file: file: A project file.
    :param options.maxDuration: int: the max duration of the video, in seconds.
    :param options.bgmDir: str: a path to a folder that contains MP3 files and/or subfolders containing the former.
        Files being defined as following:
        {
            "id": int: The internal ID of the file.
            "name": str: The name of the file.
        }
    """
    max_file_duration = options["maxDuration"] if "maxDuration" in options else 11*60

    load_video_duration(document=file["id"])
    file_info = get_file_info(file["id"])

    # Fetches all possible soundtracks
    duration = 0
    total_duration = 0
    max_duration = 4 * 60
    soundtrack_dir = options["bgmDir"]
    soundtracks = []
    for root, _, files in os.walk(soundtrack_dir):
        for f in files:
            if f.endswith(".mp3"):
                soundtracks.append(os.path.join(root, f))

    i = randint(0, len(soundtracks)-1)
    soundtrack_number = 1
    script_len = 1
    chosen_soundtrack = soundtracks.pop(i)
    soundtrack_len = backend.utils.get_audio_length(chosen_soundtrack)["total"]
    song_name = chosen_soundtrack.split("/")[-1][:-4]
    set_song(soundtrack_number, song_name, chosen_soundtrack, is_path=True, document=file["id"])
    new_song_ids = []
    for i in range(len(file_info["script"])):
        s = file_info["script"][i]
        if s["type"] != "scene":
            continue

        s_len = s["duration"]
        # Deletes every scene that would make the video too long
        if total_duration+s_len > max_file_duration:
            for _ in range(len(file_info["script"])-i):
                delete_scene(i+1, document=file["id"])
            break

        # If the current segment of scenes exceedes the max segment length,
        # add a transition and a soundtrack immediately after the previously analyzed
        # scene.
        if duration+s_len >= max_duration or duration+s_len >= soundtrack_len-10:
            add_to_script("transition", document=file["id"])
            add_to_script("soundtrack", document=file["id"])
            soundtrack_number += 1
            rand_i = randint(0, len(soundtracks)-1)
            chosen_soundtrack = soundtracks.pop(rand_i)
            soundtrack_len = backend.utils.get_audio_length(chosen_soundtrack)["total"]
            song_name = chosen_soundtrack.split("/")[-1][:-4]
            set_song(soundtrack_number, song_name, chosen_soundtrack, is_path=True, document=file["id"])
            duration = 0
            new_song_ids.append(i) # Keep track of the index the song is supposed to be in

            prev_scene = file_info["script"][i-1]
            prev_part = get_scene_info(prev_scene["number"], file=file["id"])["script"]
            prev_i = len(prev_part) - 1
            prev_part = prev_part[-1]
            prev_part["wait"] = 4
            change_scene_info(prev_scene["number"], prev_i, prev_part, document=file["id"])

        duration += s_len
        total_duration += s_len
        script_len += 1

    script_len += len(new_song_ids)*2  # Each added item is a song + a transition
    # Puts songs in the correct places
    for i in range(len(new_song_ids)):
        new_song_i = new_song_ids[i]+i*2 + 1
        song_to_relocate = script_len - (len(new_song_ids)-i)*2 + 2
        relocate_scene(song_to_relocate, new_song_i, document=file["id"])
        relocate_scene(song_to_relocate, new_song_i, document=file["id"])


def load_video_duration(document=None, max_time=-1, max_chars=-1):
    """
    Loads the duration of a video.
    :param document: int: The number of the video to load the duration of.
    :param max_time: float: The max duration that can be downloaded. Useful for API limits.
    :param max_chars: int: The max number of characters that can be synthesized. Useful for API limits.
    :return: float: The duration, or None if an exception occurred.
    """
    if document is None:
        document = open_file_id

    file_info = get_file_info(document)
    total_duration = 0
    try:
        for s in file_info["script"]:
            if total_duration >= max_time > 0:
                break
            if s["type"] == "scene":
                backend.video.download_audios_for(s, get_cache_dir(document), document=document)
                total_duration += get_scene_duration(s["number"], document)
    except Exception as exc:
        print("\n"*2, exc, "\n"*2)
        return None

    return total_duration


def detect_text(scene, crop, document=None, substitute=True):
    """
    Detects text in an image thanks to tesseract, prettifies it, and returns it,
    :param scene: Union[int, dict]: The internal ID of the scene to analize.
    :param crop: dict: Crops the image to only focus on the text. Params are `x`, `y`, `w`, and `h`.
    :param document: int: The internal ID of the document the scene belongs to.
    :return: str: The detected text.
    """
    if document is None:
        document = open_file_id

    img_path = get_scene_dir(document, scene) + "/image.png"
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


init()
