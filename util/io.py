import os
import eel
import csv
import shutil
import base64
from mutagen.mp3 import MP3
from pprint import pprint


DATA_PATH = os.path.join(
    os.path.expanduser("~"),
    "Library",
    "Application Support",
    "it.riccardosartori.reditor"
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
[ost]
[outro]
"""[1:-1]
EMPTY_CONFIG = """
next-scene-id 1
next-soundtrack-id 2
"""[1:]
open_file_id = None


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
            ret.append(ScenePart.part_to_object("".join(temp_parts)))
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
    audio = MP3(path)
    length = int(audio.info.length)
    return {"m": int(length/60), "s": length % 61}


class ScenePart:
    @staticmethod
    def part_to_object(lines):
        lines = lines.split("\n")
        coords = lines[0].split(";")
        object = {
            "crop": {
                "x": float(coords[0]),
                "y": float(coords[1]),
                "w": float(coords[2]),
                "h": float(coords[3]),
            },
            "text": lines[1],
            "voice": lines[2],
            "wait": float(lines[3]),
        }
        return object

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
                    "name": parts[2:],
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
def add_to_script(type):
    fscript = open(get_project_dir(open_file_id)+"/script.txt")

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
            new_ost_id = int(get_config(open_file_id, "next-soundtrack-id"))
            to_insert = f"[ost]{new_ost_id:05d};"
            new_soundtrack = {**EMPTY_SOUNDTRACK}
            new_soundtrack["number"] = new_ost_id
            ret.append(new_soundtrack)
            write_config(open_file_id, "next-soundtrack-id", new_ost_id+1)

        elif t == "scene":
            new_scene_id = int(get_config(open_file_id, "next-scene-id"))
            to_insert = f"{new_scene_id:05d}"
            ret.append({"type": "scene", "number": new_scene_id})
            scene_path = get_scene_dir(open_file_id, new_scene_id)
            if os.path.exists(scene_path):
                shutil.rmtree(scene_path)
            os.mkdir(scene_path)
            open(scene_path+"/script.txt", "w").close()
            write_config(open_file_id, "next-scene-id", new_scene_id+1)

        else:
            to_insert = "[transition]"
            ret.append({"type": "transition"})
        script.insert(-1, to_insert+"\n")

    fscript = open(get_project_dir(open_file_id)+"/script.txt", "w")
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
def change_scene_info(scene, script_index, new_script):
    fscene = open(get_scene_dir(open_file_id, scene)+"/script.txt")

    parts = parse_script(fscene)
    fscene.close()

    if len(parts) > script_index >= 0:
        parts[script_index] = new_script
    else:
        parts.append(new_script)

    fscene = open(get_scene_dir(open_file_id, scene)+"/script.txt", "w")
    for i in range(len(parts)):
        p = parts[i]
        fscene.write(ScenePart.object_to_text(p))
        if i < len(parts):
            fscene.write("\n\n")
    fscene.close()

    return True


@eel.expose
def get_scene_info(scene):
    scene_dir = get_scene_dir(open_file_id, scene)
    fscript = open(scene_dir+"/script.txt")
    script = parse_script(fscript)
    fscript.close()

    image = None
    if os.path.exists(scene_dir+"/image.png"):
        imagebin = open(scene_dir+"/image.png", "rb")
        image = "data:image/png;base64," + base64.b64encode(imagebin.read()).decode()
        imagebin.close()
    elif os.path.exists(scene_dir+"/image.jpg"):
        imagebin = open(scene_dir+"/image.jpg", "rb")
        image = "data:image/jpeg;base64," + base64.b64encode(imagebin.read()).decode()
        imagebin.close()

    return {
        "number": scene,
        "image": image,
        "script": script,
    }


@eel.expose
def relocate_scene(old_i, new_i):
    script_path = get_project_dir(open_file_id)+"/script.txt"
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
def delete_scene(scene_i):
    script_path = get_project_dir(open_file_id)+"/script.txt"
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
            scene_path = get_scene_dir(open_file_id, scene_id)
            if os.path.exists(scene_path):
                shutil.rmtree(scene_path)
        elif to_delete.startswith("[ost]"):
            ost_path = get_project_dir(open_file_id)+f"/soundtrack/{soundtrack_id:05d}.mp3"
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
def set_song(number, name, song_b64):
    if name.endswith(".mp3"):
        name = name[:-4]

    song_path = get_project_dir(open_file_id) + f"/soundtrack/{number:05d}.mp3"
    config, data = song_b64.split(",")

    fsong = open(song_path, "wb")
    fsong.write(base64.b64decode(data.encode("ascii")))
    fsong.close()

    script_dir = get_project_dir(open_file_id) + "/script.txt"
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


init()
