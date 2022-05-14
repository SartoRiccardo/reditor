import csv
import os
import shutil
import backend.paths
import backend.video
import classes.video
import traceback
from random import randint
from typing import Union
p = backend.paths.p


class Document:
    EMPTY_SCRIPT = ("[intro]" + "\n"
                    "[ost]00001;" + "\n"
                    "[outro]")
    EMPTY_CONFIG = ("next-scene-id 1" + "\n"
                    "next-soundtrack-id 2")

    def __init__(self, document_id: Union[str, int], name: str = "", load=False):
        self.id = document_id
        if isinstance(self.id, str):
            self.id = int(self.id)
        self.path = p(f"/saves/{self.id:05d}")

        self.name = name
        self.script = []
        self.has_intro = False
        self.has_outro = False

        if load:
            self.load()

    @staticmethod
    def new(name: str):
        finfo_r = open(p("/saves/index.csv"), "r")
        reader = csv.reader(finfo_r, delimiter=";", quotechar="\"")

        # Find a new ID for the document
        last_id = -1
        for row in reader:
            last_id = int(row[0])

        finfo_r.close()
        new_id = last_id + 1
        created_document = Document(new_id, name)

        # Write new document onto the index
        finfo_a = open(p("/saves/index.csv"), "a")
        writer = csv.writer(finfo_a, delimiter=";", quotechar="\"")
        writer.writerow([created_document.id, created_document.name])
        finfo_a.close()

        # Create necessary files and directories
        path = created_document.path
        if os.path.exists(path):
            shutil.rmtree(path)

        os.mkdir(path)
        os.mkdir(path + "/soundtrack")
        os.mkdir(path + "/scenes")
        fscript = open(path + "/script.txt", "w")
        fscript.write(Document.EMPTY_SCRIPT)
        fscript.close()
        fconfig = open(path + "/config.txt", "w")
        fconfig.write(Document.EMPTY_CONFIG)
        fconfig.close()

        return created_document

    @staticmethod
    def list():
        finfo = open(p("/saves/index.csv"), "r")
        reader = csv.reader(finfo, delimiter=";", quotechar="\"")

        ret = []
        for row in reader:
            ret.append(Document(row[0], row[1]))

        finfo.close()
        return ret

    def get_duration(self, rate_limit_max_time=-1, rate_limit_max_chars=-1):
        self.load()
        duration = 0
        try:
            for scene in self.script:
                if duration >= rate_limit_max_time > 0:
                    break
                if isinstance(scene, classes.video.Scene):
                    backend.video.download_audios_for(scene, self.get_cache_dir())
                    duration += scene.get_duration()
        except Exception as exc:
            print("\n"*2, exc, "\n"*2)
            return None

        print(f"{duration=}, {rate_limit_max_time=}")
        return duration

    def set_song(self, soundtrack_id: int, name, payload, is_path=False):
        if name.endswith(".mp3"):
            name = name[:-4]

        soundtrack = self.get_soundtrack(soundtrack_id)
        if is_path:
            soundtrack.set_from_path(payload)
        else:
            soundtrack.set_from_base64(payload)
        soundtrack.set_name(name)

        return soundtrack

    def truncate_duration(self, max_duration=10*60):
        self.get_duration(rate_limit_max_time=max_duration)  # Downloads audios and loads the duration

        total_duration = 0
        for i in range(len(self.script)):
            s = self.script[i]
            if not isinstance(s, classes.video.Scene):
                continue

            s_len = s.get_duration()
            # Deletes every scene that would make the video too long
            if total_duration+s_len > max_duration:
                for _ in range(len(self.script)-i):
                    self.delete_scene(i+1)
                break
            total_duration += s_len

    def delete_scene(self, idx):
        script_path = f"{self.path}/script.txt"

        fscript = open(script_path)
        script = []
        i = 0
        for ln in fscript:
            if i != idx:
                script.append(ln.strip())
            i += 1
        fscript.close()

        fscript = open(script_path, "w")
        for line in script:
            fscript.write(line + "\n")
        fscript.close()

        if i in range(0, len(self.script)):
            to_delete = self.script.pop(idx)
            to_delete.delete()

    def add_soundtracks(self, soundtrack_dir, max_duration=4*60):
        self.load()

        # Fetches all possible soundtracks.
        duration = 0
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
        self.set_song(soundtrack_number, song_name, chosen_soundtrack, is_path=True)

        new_song_idxs = []
        for i in range(len(self.script)):
            s = self.script[i]
            if not isinstance(s, classes.video.Scene):
                continue

            s_len = s.get_duration()
            # If the current segment of scenes exceedes the max segment length,
            # add a transition and a soundtrack immediately after the previously analyzed
            # scene.
            if duration+s_len >= max_duration or duration+s_len >= soundtrack_len-10:
                self.add_empty_scenes(classes.video.Transition, classes.video.Soundtrack)
                soundtrack_number += 1
                rand_i = randint(0, len(soundtracks)-1)
                chosen_soundtrack = soundtracks.pop(rand_i)
                soundtrack_len = backend.utils.get_audio_length(chosen_soundtrack)["total"]
                song_name = chosen_soundtrack.split("/")[-1][:-4]
                self.set_song(soundtrack_number, song_name, chosen_soundtrack, is_path=True)
                duration = 0
                new_song_idxs.append(i)  # Keep track of the index the song is supposed to be in

                prev_scene = self.script[i-1]
                part_to_change = prev_scene.script[-1]
                part_to_change.wait = 4
                prev_scene.change_part(len(prev_scene.script)-1, part_to_change)

            duration += s_len
            script_len += 1

        script_len += len(new_song_idxs)*2  # Each added item is a song + a transition
        # Puts songs in the correct places
        for i in range(len(new_song_idxs)):
            new_song_i = new_song_idxs[i]+i*2
            song_to_relocate = script_len - (len(new_song_idxs)-i)*2 + 2
            self.relocate_scene(song_to_relocate, new_song_i)
            self.relocate_scene(song_to_relocate, new_song_i)

    def get_cache_dir(self) -> str:
        directory = self.path + "/cache"
        if not os.path.exists(directory):
            os.mkdir(directory)
        return directory

    def load(self) -> bool:
        """
        Loads detailed document information into the instance.
        :return: True if the information was loaded correctly
        """
        self.script = []
        self.name = ""

        finfo = open(p("/saves/index.csv"), "r")
        reader = csv.reader(finfo, delimiter=";", quotechar="\"")

        exists = False
        for row in reader:
            if int(row[0]) == self.id:
                exists = True
                self.name = row[1]
                break
        finfo.close()

        if not (os.path.exists(self.path) and exists):
            return False

        fscript = open(self.path+"/script.txt", "r")

        components = 0
        scenes = 0
        for ln in fscript:
            ln = ln.strip()
            if ln.startswith("["):
                parts = ln.split("]")
                command = parts[0][1:]
                if command == "ost" and len(parts) > 1:
                    parts = parts[:1] + "]".join(parts[1:]).split(";")
                    soundtrack_id = int(parts[1])
                    self.script.append(classes.video.Soundtrack(self, soundtrack_id, ";".join(parts[2:])))
                elif command == "transition":
                    self.script.append(classes.video.Transition(self))
                elif command == "intro":
                    self.has_intro = True
                elif command == "outro":
                    self.has_outro = True
            else:
                scenes += 1
                new_scene = classes.video.Scene(self, int(ln))
                new_scene.load()
                self.script.append(new_scene)

            if ln not in ["[intro]", "[outro]"]:
                components += 1
        fscript.close()

        return True

    def delete(self):
        finfo = open(p("/saves/index.csv"), "r")
        reader = csv.reader(finfo, delimiter=";", quotechar="\"")

        new_index = []
        for row in reader:
            if int(row[0]) != self.id:
                new_index.append(row)

        finfo.close()

        finfo = open(p("/saves/index.csv"), "w")
        writer = csv.writer(finfo, delimiter=";", quotechar="\"")
        for row in new_index:
            writer.writerow(row)

        finfo.close()

        if os.path.exists(self.path):
            shutil.rmtree(self.path)

    def export(self, export_dir, log_callback=None, size="720"):
        self.load()
        if os.path.exists(export_dir):
            shutil.rmtree(export_dir)
        os.mkdir(export_dir)

        try:
            backend.video.export_video(
                self, export_dir,
                gui_callback=log_callback if log_callback else lambda x: x,
                video_name=f"{self.name}.mp4",
                size=size
            )
        except Exception:
            fout = open("./error.txt", "w")
            fout.write(traceback.format_exc())
            fout.close()

    def add_empty_scenes(self, *scenes):
        fscript = open(self.path + "/script.txt")

        # Load current script and last soundtrack number
        script = []
        last_soundtrack_number = 1
        for ln in fscript:
            if "[ost]" in ln:
                last_soundtrack_number += 1
            script.append(ln)
        fscript.close()

        # Create new empty scenes
        new_scenes = []
        for t in scenes:
            if t == classes.video.Soundtrack:
                new_ost_id = int(self.get_config("next-soundtrack-id"))
                new_script_str = f"[ost]{new_ost_id:05d};"
                new_item = classes.video.Soundtrack(self, new_ost_id)
                self.write_config("next-soundtrack-id", new_ost_id+1)

            elif t == classes.video.Scene:
                new_scene_id = int(self.get_config("next-scene-id"))
                new_script_str = f"{new_scene_id:05d}"
                new_item = classes.video.Scene(self, new_scene_id)
                new_item.initialize()
                self.write_config("next-scene-id", new_scene_id+1)

            else:
                new_script_str = "[transition]"
                new_item = classes.video.Transition(self)

            new_scenes.append(new_item)
            self.script.insert(-1, new_item)
            script.insert(-1, new_script_str+"\n")

        # Update script
        fscript = open(self.path + "/script.txt", "w")
        for ln in script:
            fscript.write(ln)
        fscript.close()

        return new_scenes

    def relocate_scene(self, old_idx: int, new_idx: int):
        script_path = self.path + "/script.txt"
        fscript = open(script_path)
        script = [ln.strip() for ln in fscript]
        fscript.close()

        script.insert(new_idx+1, script.pop(old_idx+1))  # Index starts at 1 because [intro] doesn't count

        # Update file
        fscript = open(script_path, "w")
        for line in script:
            fscript.write(line + "\n")
        fscript.close()

        # Update instance
        if new_idx < len(self.script) and old_idx < len(self.script):
            self.script.insert(new_idx, self.script.pop(old_idx))
        else:
            self.load()

    def get_config(self, key: str):
        config = open(self.path + "/config.txt")
        ret = None
        for ln in config:
            parts = ln.strip().split(" ")
            if parts[0] == key:
                ret = " ".join(parts[1:])
                break
        config.close()
        return ret

    def write_config(self, key: str, value):
        config_path = self.path + "/config.txt"

        config = open(config_path)
        file = []
        found = False
        for ln in config:
            parts = ln.strip().split(" ")
            if parts[0] == key:
                found = True
                if value is not None:
                    file.append(f"{key} {value}\n")
            else:
                file.append(ln)
        config.close()

        if not found:
            file.append(f"{key} {value}\n")

        config = open(config_path, "w")
        [config.write(ln) for ln in file]
        config.close()

    def get_scene_amount(self):
        amount = 0
        for component in self.script:
            if isinstance(component, classes.video.Scene):
                amount += 1
        return amount

    def get_scene(self, scene_id):
        for scene in self.script:
            if not isinstance(scene, classes.video.Scene):
                continue
            if scene.id == scene_id:
                return scene

        scene = classes.video.Scene(self, scene_id)
        loaded = scene.load()
        return scene if loaded else None

    def get_soundtrack(self, soundtrack_id):
        for soundtrack in self.script:
            if not isinstance(soundtrack, classes.video.Soundtrack):
                continue
            if soundtrack.soundtrack_id == soundtrack_id:
                return soundtrack

        soundtrack = classes.video.Soundtrack(self, soundtrack_id)
        return soundtrack

    def get_component_amount(self):
        return len(self.script)

    def get_scenes(self):
        scenes = []
        for scene in self.script:
            if isinstance(scene, classes.video.Scene):
                scenes.append(scene)
        return scenes

    def add_intro(self):
        self._raw_change_part("[intro]", place="first")
        self.has_intro = True

    def delete_intro(self):
        self._raw_change_part("[intro]", action="remove")
        self.has_intro = False

    def add_outro(self):
        self._raw_change_part("[outro]", place="last")
        self.has_outro = True

    def delete_outro(self):
        self._raw_change_part("[outro]", action="remove")
        self.has_outro = False

    def _raw_change_part(self, part, place="first", action="add"):
        script_path = self.path + "/script.txt"
        fscript = open(script_path)
        lines = []
        for ln in fscript:
            if part in ln:
                continue
            lines.append(ln)
        fscript.close()

        fscript = open(script_path, "w")
        if place == "first" and action == "add":
            fscript.write(f"{part}\n")
        for ln in lines:
            fscript.write(ln)
        if place == "last" and action == "add":
            fscript.write(f"{part}\n")
        fscript.close()

        self.has_intro = True

    def set_background(self, path: str):
        self.write_config("background", path)

