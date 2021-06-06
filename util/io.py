import os
import eel
import csv
import shutil
import base64
from mutagen.mp3 import MP3
import urllib3
import util.requests
import util.utils
import time
import traceback
from PIL import Image
import pytesseract
import re
from html2image import Html2Image
from random import randint
from tkinter import filedialog, Tk
import json
pytesseract.pytesseract.tesseract_cmd = r"/usr/local/bin/tesseract"


DATA_PATH = os.path.join(
    os.path.expanduser("~"),
    "Library",
    "Application Support",
    "it.riccardosartori.reditor"
)
DOWNLOAD_PATH = os.path.join(
    os.path.expanduser("~"),
    "Downloads",
)
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
open_file_id = None
pool = urllib3.PoolManager()

hti = None
html_template_post = None
css_post = None
html_template_comment = None
css_comment = None


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def p(path):
    return DATA_PATH+path


def get_project_dir(id):
    return p(f"/saves/{id:05d}")


def get_scene_dir(project_id, scene_id):
    return p(f"/saves/{project_id:05d}/scenes/{scene_id:05d}")


def parse_script(file):
    ret = []
    temp_parts = []
    chunk_size = 4
    skip_next_line = False
    for ln in file:
        if skip_next_line:
            skip_next_line = False
            continue

        temp_parts.append(ln)
        if len(temp_parts) == chunk_size:
            try:
                ret.append(ScenePart.part_to_object("".join(temp_parts)))
            except Exception as ex:
                print("\n"*5)
                print(ex)
                print(ln, file.name)
                raise ex
            temp_parts = []
            skip_next_line = True
    return ret


def init():
    if not os.path.exists(DATA_PATH):
        os.mkdir(DATA_PATH)

    required_dirs = ["/assets", "/saves", "/saves/index.csv"]

    for d in required_dirs:
        if not os.path.exists(p(d)):
            if "." in d:
                f = open(p(d), "w")
                f.close()
            else:
                os.mkdir(p(d))


def get_config(project_id, variable):
    config_dir = get_project_dir(project_id) + "/config.txt"
    config = open(config_dir)
    ret = None
    for ln in config:
        parts = ln.strip().split(" ")
        if parts[0] == variable:
            ret = parts[1]
            break
    config.close()
    return ret


def write_config(project_id, variable, newval):
    config_dir = get_project_dir(project_id) + "/config.txt"
    config = open(config_dir)
    file = []
    for ln in config:
        parts = ln.strip().split(" ")
        if parts[0] == variable:
            file.append(f"{variable} {newval}\n")
        else:
            file.append(ln)
    config.close()

    config = open(config_dir, "w")
    [config.write(ln) for ln in file]
    config.close()


def get_audio_length(path):
    if os.path.exists(path):
        audio = MP3(path)
        length = audio.info.length
        return {"m": int(length/60), "s": int(length % 60), "ms": length % 1, "total": length}
    return {"m": 0, "s": 0, "ms": 0, "total": 0}


def get_cache_dir(file_id=open_file_id):
    ret = get_project_dir(file_id) + "/cache"
    if not os.path.exists(ret):
        os.mkdir(ret)
    return ret


class ScenePart:
    @staticmethod
    def part_to_object(lines):
        lines = lines.split("\n")
        coords = lines[0].split(";")
        wait = float(lines[3]) if is_number(lines[3]) else 1
        ob = {
            "crop": {
                "x": float(coords[0]),
                "y": float(coords[1]),
                "w": float(coords[2]),
                "h": float(coords[3]),
            },
            "text": lines[1],
            "voice": lines[2],
            "wait": wait,
        }
        return ob

    @staticmethod
    def object_to_text(scene):
        return (
            f"{scene['crop']['x']};{scene['crop']['y']};{scene['crop']['w']};{scene['crop']['h']}" + "\n" +
            scene["text"] + "\n" +
            scene["voice"] + "\n" +
            str(scene["wait"])
        )


@eel.expose
def get_file_info(id):
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
                    "duration": get_audio_length(audio_path),
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


@eel.expose
def get_files():
    finfo = open(p("/saves/index.csv"), "r")
    reader = csv.reader(finfo, delimiter=";", quotechar="\"")

    ret = []
    for row in reader:
        ret.append({
            "id": int(row[0]), "name": row[1]
        })

    finfo.close()
    return ret


@eel.expose
def create_file(name):
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


@eel.expose
def open_file(id):
    global open_file_id
    open_file_id = id


@eel.expose
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


@eel.expose
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


@eel.expose
def change_scene_info(scene, script_index, new_script, document=None):
    if document is None:
        document = open_file_id

    fscene = open(get_scene_dir(document, scene)+"/script.txt")

    parts = parse_script(fscene)
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


@eel.expose
def get_scene_info(scene, file=None):
    if file is None:
        file = open_file_id
    scene_dir = get_scene_dir(file, scene)
    fscript = open(scene_dir+"/script.txt")
    script = parse_script(fscript)
    fscript.close()

    duration = get_scene_duration(scene, file)

    image = None
    img_path = scene_dir+"/image.png"
    if os.path.exists(scene_dir+"/image.png"):
        imagebin = open(scene_dir+"/image.png", "rb")
        image = "data:image/png;base64," + base64.b64encode(imagebin.read()).decode()
        imagebin.close()
    elif os.path.exists(scene_dir+"/image.jpg"):
        imagebin = open(scene_dir+"/image.jpg", "rb")
        img_path = scene_dir+"/image.jpg"
        image = "data:image/jpeg;base64," + base64.b64encode(imagebin.read()).decode()
        imagebin.close()

    return {
        "number": scene,
        "image": image,
        "image_path": img_path,
        "script": script,
        "last_change": os.path.getmtime(scene_dir+"/script.txt"),
        "duration": duration
    }


def get_scene_duration(scene, file=None):
    if file is None:
        file = open_file_id

    if isinstance(scene, dict):
        script = scene["script"]
    else:
        scene_dir = get_scene_dir(file, scene)
        fscript = open(scene_dir+"/script.txt")
        script = parse_script(fscript)
        fscript.close()

    cache_dir = get_cache_dir(file)
    duration = 0
    for i in range(len(script)):
        part = script[i]
        if part["text"]:
            aud_path = cache_dir + f"/{scene:05d}-{i:05d}.mp3"
            if os.path.exists(aud_path):
                duration += get_audio_length(aud_path)["total"]
            else:
                duration = None
                break
        duration += part["wait"]

    return duration


@eel.expose
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


@eel.expose
def delete_script_part(scene, part_i):
    script_file = get_scene_dir(open_file_id, scene) + "/script.txt"
    fscript = open(script_file)
    script = parse_script(fscript)
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


@eel.expose
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


@eel.expose
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


@eel.expose
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
        "duration": get_audio_length(song_path),
        "name": name,
        "path": song_path,
        "number": number,
    }


@eel.expose
def export_file():
    files = get_files()
    file_name = None
    for f in files:
        if f["id"] == open_file_id:
            file_name = f["name"]
            break

    if file_name is None:
        return

    export_dir = DOWNLOAD_PATH + f"/{file_name}-export"
    if os.path.exists(export_dir):
        shutil.rmtree(export_dir)
    os.mkdir(export_dir)
    try:
        util.video.export_video(open_file_id, export_dir, gui_callback=eel.gui_callback)
    except Exception as exc:
        fout = open("/Users/riccardosartori/Desktop/err.txt", "w")
        fout.write(traceback.format_exc())
        fout.close()


def download_image(url, file_path):
    stdout = open(file_path, "wb")
    response = pool.request("GET", url, preload_content=False)
    for chunk in response.stream(1024):
        stdout.write(chunk)
    response.release_conn()

    if response.status == 404:
        os.remove(file_path)
        return None


@eel.expose
def download_images(platform, target, options={}):
    image_urls = []
    if platform == "reddit":
        image_urls = util.requests.subreddit_image_posts(target, only_selfposts=options["isSelfpostVideo"])
    elif platform == "twitter":
        image_urls = util.requests.twitter_user_images(target)
    elif platform == "askreddit":
        if "http" in target:
            id_re = r"comments\/(.+?)\/"
            target = re.search(id_re, target).group(1)
        image_urls = util.requests.post_comments(target)

    if len(image_urls) == 0:
        return False

    tmp_dir = DATA_PATH + "/tmp"
    dl_dir = tmp_dir + "/download"
    if os.path.exists(dl_dir):
        shutil.rmtree(dl_dir)
    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)
    os.mkdir(dl_dir)

    automatic = (platform == "reddit" and options["isSelfpostVideo"]
                 or platform == "askreddit") \
                 and options["bgmDir"]

    if not automatic:
        for i in range(len(image_urls)):
            url = image_urls[i].path
            is_url = image_urls[i].is_url
            if is_url:
                download_image(url, dl_dir+f"/{i:05d}.png")
            else:
                shutil.move(url, dl_dir+f"/{i:05d}.png")

        shutil.make_archive(tmp_dir+f"/{target}", "zip", dl_dir)
        zip_path = tmp_dir+f"/{target}.zip"
        shutil.move(zip_path, DOWNLOAD_PATH+f"/{target}-{int(time.time())}.zip")
    else:
        document_name = f"{target}-auto"
        file = create_file(document_name)
        for i in range(len(image_urls)):
            path = image_urls[i].path
            if os.path.exists(path+".txt"):
                scene = add_to_script("scene", document=file["id"])
                scene_dir = get_scene_dir(file["id"], scene[0]["number"])
                shutil.move(path, scene_dir+"/image.png")
                shutil.move(path+".txt", scene_dir+"/script.txt")

        load_video_duration(document=file["id"])
        file_info = get_file_info(file["id"])

        duration = 0
        total_duration = 0
        max_duration = 4 * 60
        max_file_duration = options["maxDuration"] if options["maxDuration"] else 11*60
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
        soundtrack_len = get_audio_length(chosen_soundtrack)["total"]
        song_name = chosen_soundtrack.split("/")[-1][:-4]
        set_song(soundtrack_number, song_name, chosen_soundtrack, is_path=True, document=file["id"])
        new_song_ids = []
        for i in range(len(file_info["script"])):
            s = file_info["script"][i]
            if s["type"] == "scene":
                s_len = s["duration"]
                if total_duration+s_len > max_file_duration:
                    for _ in range(len(file_info["script"])-i):
                        delete_scene(i+1, document=file["id"])
                    break

                if duration+s_len >= max_duration or duration+s_len >= soundtrack_len-10:
                    add_to_script("transition", document=file["id"])
                    add_to_script("soundtrack", document=file["id"])
                    soundtrack_number += 1
                    rand_i = randint(0, len(soundtracks)-1)
                    chosen_soundtrack = soundtracks.pop(rand_i)
                    soundtrack_len = get_audio_length(chosen_soundtrack)["total"]
                    song_name = chosen_soundtrack.split("/")[-1][:-4]
                    set_song(soundtrack_number, song_name, chosen_soundtrack, is_path=True, document=file["id"])
                    duration = 0
                    new_song_ids.append(i)

                    prev_scene = file_info["script"][i-1]
                    prev_part = get_scene_info(prev_scene["number"], file=file["id"])["script"]
                    prev_i = len(prev_part) - 1
                    prev_part = prev_part[-1]
                    prev_part["wait"] = 4
                    change_scene_info(prev_scene["number"], prev_i, prev_part, document=file["id"])

                duration += s_len
                total_duration += s_len
                script_len += 1

        script_len += len(new_song_ids)*2
        for i in range(len(new_song_ids)):
            new_song_i = new_song_ids[i]+i*2 + 1
            song_to_relocate = script_len - (len(new_song_ids)-i)*2 + 2
            print(f"> RELOCATE {song_to_relocate} TO {new_song_i}")
            relocate_scene(song_to_relocate, new_song_i, document=file["id"])
            relocate_scene(song_to_relocate, new_song_i, document=file["id"])

    return True


@eel.expose
def load_video_duration(document=None):
    if document is None:
        document = open_file_id

    file_info = get_file_info(document)
    try:
        for s in file_info["script"]:
            if s["type"] == "scene":
                util.video.download_audios_for(s, get_cache_dir(document), document=document)
    except Exception as exc:
        print("\n"*2, exc, "\n"*2)
        return False

    return True


@eel.expose
def detect_text(scene, crop, document=None):
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
    ]
    for pre, sub in substitutions:
        text = re.sub(pre, sub, text)

    return text.strip()


def reddit_to_image(submission, subreddit_name):
    global hti, html_template_post, css_post

    tmp_dir = DATA_PATH + "/tmp"
    dl_dir = tmp_dir + "/download-selfposts"
    if not hti:
        hti = Html2Image(custom_flags="--log-level=OFF")
        if os.path.exists(dl_dir):
            shutil.rmtree(dl_dir)
        if not os.path.exists(tmp_dir):
            os.mkdir(tmp_dir)
        os.mkdir(dl_dir)

        hti.output_path = dl_dir
    if not html_template_post:
        fin = open("./assets/reddit-post-template.html")
        html_template_post = fin.read()
        fin.close()
    if not css_post:
        fin = open("./assets/reddit-post.css")
        css_post = fin.read()
        fin.close()

    replacements = [
        ("\\.\\s+\"", ".\""), ("!\\s+\"", ".\""), ("\\?\\s+\"", ".\""),
        ("https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)",
         "this link")
    ]

    filename = util.utils.randstr(10) + ".png"
    body = submission.selftext
    for pre, after in replacements:
        body = re.sub(pre, after, body)
    body = body.split("\n\n")
    for i in range(len(body)):
        body[i] = "<p>" + body[i].replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>") + "</p>"
    body = "\n".join(body)

    score = submission.score
    if score >= 1000:
        score = f"{int(score/1000)}.{int(score/100)%10}k"
    else:
        score = str(score)

    html = html_template_post.replace("{upvotes}", score) \
            .replace("{author}", submission.author.name) \
            .replace("{sub-name}", subreddit_name) \
            .replace("{post-title}", submission.title) \
            .replace("{post-text}", body) \
            .replace("{upvote-ratio}", str(int(submission.upvote_ratio*100))) \
            .replace("{num-comments}", str(submission.num_comments)) \
            .replace("{sub-icon-url}", submission.subreddit.icon_img)

    hti.screenshot(html_str=html, css_str=css_post, save_as=filename)

    full_path = dl_dir + "/" + filename
    image = Image.open(full_path).convert("RGBA")
    width, height = image.size
    for y in range(1, height):
        if image.getpixel((int(width/2), y))[3] != 0:
            break
    scene = image.crop((0, 0, 512, height))
    image = image.crop((512, y, 1792, height-y))
    image.save(full_path)

    text = pytesseract.image_to_string(scene, lang="eng", config="--psm 11")
    if "FALSE" in text:
        return None
    raw_scene = [row.split("-") for row in re.split("\n{2,}", text)]

    script = get_script(submission.selftext)
    script.insert(0, submission.title)
    script_i = 0
    try:
        raw_script = []
        for s in raw_scene:
            s = [float(num) for num in s]
            x, y, w, h, wait = s
            scene_obj = {
                "text": "" if wait == 0 else script[script_i],
                "voice": "male-1",
                "crop": {"x": x, "y": y, "w": w, "h": h},
                "wait": wait,
            }
            if wait > 0:
                script_i += 1
            raw_script.append(ScenePart.object_to_text(scene_obj))
        raw_script = "\n\n".join(raw_script)

        fout = open(full_path+".txt", "w")
        fout.write(raw_script)
        fout.close()
    except:
        pass

    return full_path


def reddit_comment_to_image(forest):
    global hti, html_template_comment, css_comment

    tmp_dir = DATA_PATH + "/tmp"
    dl_dir = tmp_dir + "/download-selfposts"
    if not hti:
        hti = Html2Image(custom_flags="--log-level=OFF")
        if os.path.exists(dl_dir):
            shutil.rmtree(dl_dir)
        if not os.path.exists(tmp_dir):
            os.mkdir(tmp_dir)
        os.mkdir(dl_dir)

        hti.output_path = dl_dir
    if not html_template_comment:
        fin = open("./assets/reddit-comment-template.html")
        html_template_comment = fin.read()
        fin.close()
    if not css_comment:
        fin = open("./assets/reddit-comment.css")
        css_comment = fin.read()
        fin.close()

    forest = polish_comments(forest)
    filename = util.utils.randstr(10) + ".png"
    html = html_template_comment.replace("{comment-json-inject}", json.dumps(forest))
    hti.screenshot(html_str=html, css_str=css_comment, save_as=filename)

    full_path = dl_dir + "/" + filename
    image = Image.open(full_path).convert("RGBA")
    width, height = image.size
    for y in range(1, height):
        if image.getpixel((int(width/2), y))[3] != 0:
            break
    scene = image.crop((0, 0, 498, height))
    image = image.crop((498, y, 1818, height-y))
    image.save(full_path)

    text = pytesseract.image_to_string(scene, lang="eng", config="--psm 11")
    if "FALSE" in text:
        return None
    raw_scene = [row.split("-") for row in re.split("\n{2,}", text)]

    script = get_script_comment(forest)
    script_i = 0
    try:
        raw_script = []
        for s in raw_scene:
            s = [float(num) for num in s]
            x, y, w, h, wait = s
            scene_obj = {
                "text": "" if wait == 0 else script[script_i],
                "voice": "male-1",
                "crop": {"x": x, "y": y, "w": w, "h": h},
                "wait": wait,
            }
            if wait > 0:
                script_i += 1
            raw_script.append(ScenePart.object_to_text(scene_obj))
        raw_script = "\n\n".join(raw_script)

        fout = open(full_path+".txt", "w")
        fout.write(raw_script)
        fout.close()
    except:
        pass

    return full_path


def replace_with_group(match):
    return match.group(1)


def polish_comments(forest):

    def repl_markdown(mark):
        def ret(match):
            if mark == "bi":
                return f"<b><i>{match.group(1)}</i></b>"
            if mark == "b":
                return f"<b>{match.group(1)}</b>"
            if mark == "i":
                return f"<i>{match.group(1)}</i>"
            return match.group(1)
        return ret

    replacements = [
        ("\\.\\s+\"", ".\""), ("!\\s+\"", ".\""), ("\\?\\s+\"", ".\""),
        ("\\[(.+?)\\]\\(.+?\\)", replace_with_group), ("\\. \\. \\.", "..."),
        (r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))",
         "[some URL]"),
        ("\\*\\*\\*(.*?)\\*\\*\\*", repl_markdown("bi")), ("___(.*?)___", repl_markdown("bi")),
        ("\\*\\*(.*?)\\*\\*", repl_markdown("b")), ("__(.*?)__", repl_markdown("b")),
        ("\\*(.*?)\\*", repl_markdown("i")), ("_(.*?)_", repl_markdown("i")),
    ]
    for pre, after in replacements:
        forest["body"] = re.sub(pre, after, forest["body"])
    for i in range(len(forest["replies"])):
        forest["replies"][i] = polish_comments(forest["replies"][i])
    return forest


def get_script_comment(forest):
    ret = get_script(forest["body"])
    for rep in forest["replies"]:
        ret += get_script_comment(rep)
    return ret


def get_script(text):
    replacements = [
        ("ftw", "for the win"), ("mfw", "my face when"), ("tfw", "that feel when"),
        ("qt", "cutie"), ("3\\.14", "pi"), ("<i>(.*?)<\\/i>", replace_with_group),
        ("<b>(.*?)<\\/b>", replace_with_group), (">", ""),
    ]
    text = de_emojify(text)
    for pre, after in replacements:
        text = re.sub(pre, after, text, flags=re.IGNORECASE)
    text = re.split("\n{2,}", text)
    split_at = [". ", "? ", "! "]
    for c in split_at:
        length = len(text)
        for i_neg in range(length):
            i = length - 1 - i_neg
            text[i] = text[i].split(c)
            for j in range(len(text[i])):
                if j != len(text[i]) - 1:
                    text[i][j] += c
            text = text[:i] + text[i] + text[i + 1:]

    text_tmp = []
    for t in text:
        if len(t.strip()) > 0:
            text_tmp.append(t.replace("\n", ""))
    return text_tmp


@eel.expose
def get_full_path():
    root = Tk()
    root.withdraw()
    root.wm_attributes('-topmost', 1)
    folder = filedialog.askdirectory(title="Select BGM folder")
    root.update()
    return folder


@eel.expose
def get_image_path():
    root = Tk()
    root.withdraw()
    root.wm_attributes('-topmost', 1)
    folder = filedialog.askopenfilename(title="Select image", filetypes=[('PNG FILES', '*.png'), ('JPG FILES', '*.jpg')])
    root.update()
    return folder


@eel.expose
def generate_thumbnail(thumb_text, thumb_source_type, thumb_source):
    thumb_dl_dir = DOWNLOAD_PATH + f"/thumbnail-{int(time.time())}.png"
    thumb_tmp_file = None
    source_path = thumb_source
    if thumb_source_type == "url":
        thumb_tmp_file = DATA_PATH + "/tmp/" + util.utils.randstr(10) + ".png"
        download_image(thumb_source, thumb_tmp_file)
        source_path = thumb_tmp_file

    util.image.make_thumbnail(thumb_text, source_path, thumb_dl_dir)

    if thumb_tmp_file is not None:
        os.remove(thumb_tmp_file)


# https://stackoverflow.com/questions/33404752/removing-emojis-from-a-string-in-python
def de_emojify(text):
    regrex_pattern = re.compile(pattern="["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                           "]+", flags=re.UNICODE)
    return regrex_pattern.sub(r'', text)


init()
