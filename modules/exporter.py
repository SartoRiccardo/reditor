import threading
import time
from random import randint
import backend.database
from datetime import datetime, timedelta
import backend.editor


class Exporter(threading.Thread):
    # UPLOAD_EVERY = 60*60*24
    UPLOAD_EVERY = 3

    def __init__(self):
        super().__init__()
        self.last_loop = datetime.now()
        self.active = True

    def run(self):
        while self.active:
            while datetime.now() < self.last_loop + timedelta(seconds=Exporter.UPLOAD_EVERY) and \
                    self.active:
                time.sleep(10)
            if not self.active:
                return
            self.last_loop = datetime.now()

            videos = backend.database.get_videos()
            if len(videos) == 0:
                continue
            chosen = Exporter.choose_video(videos)

            bgm_dir = backend.database.config("rdt_bgmdir")
            # backend.editor.download_images("askreddit", chosen["thread"], {"bgmDir": bgm_dir})

            files = backend.editor.get_files()
            if len(files) == 0:
                continue
            to_export = files[0]["id"]
            # backend.editor.export_file(to_export)
            backend.database.confirm_export(chosen["thread"])
            # backend.editor.delete_file(to_export)

    def stop(self):
        self.active = False

    @staticmethod
    def choose_video(videos):
        ready_count = 0
        while ready_count < len(videos):
            if videos[ready_count]["thumbnail"] is None:
                break
            ready_count += 1

        if ready_count > 0:
            return videos[randint(0, ready_count-1)]
        return videos[randint(0, len(videos)-1)]
