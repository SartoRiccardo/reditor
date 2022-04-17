from classes.ScriptComponent import ScriptComponent
import backend.utils
import shutil
import os
import base64


class Soundtrack(ScriptComponent):
    def __init__(self, document, soundtrack_id, name=None):
        super().__init__(document)
        self.soundtrack_id = soundtrack_id
        self.path = f"{self.document.path}/soundtrack/{self.soundtrack_id:05d}.mp3"
        self.name = name

    def set_from_base64(self, payload):
        config, data = payload.split(",")
        fsong = open(self.path, "wb")
        fsong.write(base64.b64decode(data.encode("ascii")))
        fsong.close()

    def set_from_path(self, path):
        shutil.copy(path, self.path)

    def get_duration(self):
        return backend.utils.get_audio_length(self.path)

    def set_id(self, soundtrack_id):
        self.soundtrack_id = soundtrack_id
        self.path = f"{self.document.path}/soundtrack/{self.soundtrack_id:05d}.mp3"

    def set_name(self, name):
        script_dir = f"{self.document.path}/script.txt"
        fscript = open(script_dir)

        new_script = []
        for ln in fscript:
            if ln.startswith("[ost]"):
                soundtrack_id = int(ln[5:].split(";")[0])
                if self.soundtrack_id == soundtrack_id:
                    new_script.append(f"[ost]{soundtrack_id:05d};{name}\n")
                else:
                    new_script.append(ln)
            else:
                new_script.append(ln)

        fscript.close()
        fscript = open(script_dir, "w")
        [fscript.write(ln) for ln in new_script]
        fscript.close()

    def delete(self):
        if os.path.exists(self.path):
            os.remove(self.path)
