import classes.Part
import classes.ScriptComponent
import os
import shutil
import backend.utils
import traceback
from backend.paths import p
import base64


class Scene(classes.ScriptComponent.ScriptComponent):
    def __init__(self, document, scene_id):
        super().__init__(document)
        self.id = scene_id
        self.path = f"{self.document.path}/scenes/{self.id:05d}"
        self.script = []

    def get_duration(self, download_if_missing=True):
        duration = 0
        if not os.path.exists(self.path):
            return duration

        if os.path.exists(self.path + "/media.mp4"):
            duration += backend.utils.get_video_length(self.path + "/media.mp4")["total"]
        elif os.path.exists(self.path + "/media.gif"):
            duration += backend.utils.get_gif_length(self.path + "/media.gif")["total"]

        if download_if_missing:
            backend.video.download_audios_for(self, self.document.get_cache_dir())

        for i in range(len(self.script)):
            part = self.script[i]
            if part.text:
                aud_path = self.document.get_cache_dir() + f"/{self.id:05d}-{i:05d}.mp3"
                if os.path.exists(aud_path):
                    duration += backend.utils.get_audio_length(aud_path)["total"]
            duration += part.wait

        return duration

    def initialize(self):
        if os.path.exists(self.path):
            shutil.rmtree(self.path)
        os.mkdir(self.path)
        open(self.path + "/script.txt", "w").close()

    def load(self) -> bool:
        if not os.path.exists(self.path):
            return False

        self.script = []
        fscript = open(f"{self.path}/script.txt")

        temp_parts = []
        chunk_size = 4
        skip_next_line = False
        for ln in fscript:
            if skip_next_line:
                skip_next_line = False
                continue

            temp_parts.append(ln)
            if len(temp_parts) == chunk_size:
                try:
                    self.script.append(classes.Part("".join(temp_parts)))
                except Exception as ex:
                    print(traceback.format_exc())
                    raise ex
                temp_parts = []
                skip_next_line = True

        fscript.close()
        return True

    def get_media_path(self):
        possible_paths = [
            f"{self.path}/media.png",
            f"{self.path}/media.jpeg",
            f"{self.path}/media.mp4",
            f"{self.path}/media.gif",
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path

    def get_media_as_base64(self):
        media_path = self.get_media_path()
        media_format = media_path.split(".")[-1]
        binary = open(media_path, "rb")
        encoded = f"data:image/{media_format};base64," + base64.b64encode(binary.read()).decode()
        return encoded

    def set_media_as_base64(self, payload):
        image_path = f"{self.path}/image."

        config, data = payload.split(",")
        config = config.split(";")
        ext = "png"
        for c in config:
            if "data:image/" in c:
                ext = c[11:]
        image_path += ext

        fimage = open(image_path, "wb")
        fimage.write(base64.b64decode(data.encode("ascii")))
        fimage.close()

    def set_media_as_path(self, path):
        ext = backend.utils.get_extension(path)
        shutil.copy(path, f"{self.path}/media.{ext}")

    def delete_part(self, part_idx):
        self.load()
        self.script.pop(part_idx)

        fscript = open(f"{self.path}/script.txt", "w")
        fscript.write("\n\n".join([str(part) for part in self.script]))
        fscript.close()

    def get_last_changed(self):
        return os.path.getmtime(f"{self.path}/script.txt")

    def write_scene(self):
        fscene = open(f"{self.path}/script.txt", "w")
        fscene.write("\n\n".join([str(part) for part in self.script]))
        fscene.close()

    def change_part(self, part_idx: int, new_part: classes.Part):
        self.load()
        if len(self.script) > part_idx >= 0:
            self.script[part_idx] = new_part
        else:
            self.script.append(new_part)
        self.write_scene()

    def delete(self):
        if os.path.exists(self.path):
            shutil.rmtree(self.path)

    def add_parts(self, *parts):
        for part in parts:
            self.script.append(part)

    def set_script(self, source, is_file=True):
        if is_file:
            shutil.move(source, f"{self.path}/script.txt")
        else:
            fout = open(f"{self.path}/script.txt", "w")
            fout.write(source)
            fout.close()

    @staticmethod
    def get_path(document_id: int, scene_id: int):
        document = classes.Document(document_id)
        return Scene(document, scene_id).path
