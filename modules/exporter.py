import threading
import time
from random import randint
import backend.database
from datetime import datetime, timedelta
import backend.editor
import os
from backend.paths import DOWNLOAD_PATH
import requests


class Exporter(threading.Thread):
    UPLOAD_EVERY = 60*60*12

    def __init__(self):
        super().__init__()
        self.last_loop = datetime.now()
        self.active = True
        self.first_loop = True
        self.error_exporting = False

    def run(self):
        self.first_loop = True
        while self.active:
            try:
                self.task()
            except Exception as exc:
                print(exc)

    def task(self):
        self.error_exporting = False
        while (datetime.now() < self.last_loop + timedelta(seconds=Exporter.UPLOAD_EVERY) or
                len(Exporter.get_video_backlog()) > 3) and \
                self.active and not self.first_loop:
            time.sleep(10)
        self.first_loop = False
        if not self.active:
            return
        self.last_loop = datetime.now()

        videos = backend.database.get_videos()
        if len(videos) == 0:
            return
        chosen = Exporter.choose_video(videos)

        bgm_dir = backend.database.config("rdt_bgmdir")
        backend.editor.download_images("askreddit", chosen["thread"], {"bgmDir": bgm_dir})

        files = backend.editor.get_files()
        if len(files) == 0:
            return
        to_export = files[0]["id"]
        Exporter.log(f"Exporting **{chosen['title']}**")
        backend.editor.export_file(to_export, log_callback=self.check_errors)
        if not self.error_exporting:
            backend.database.confirm_export(chosen["thread"])
        backend.editor.delete_file(to_export)
        Exporter.log(f"Exported **{chosen['title']}**")

    def stop(self):
        self.active = False

    def check_errors(self, evt):
        if "error_msg" not in evt:
            return
        self.error_exporting = True
        # Log somewhere
        Exporter.log(evt["error_msg"], is_error=True)

    @staticmethod
    def log(message, is_error=False):
        webhook_url = backend.database.config("rdt_logger")
        embed = {"embeds": [{
            "title": "Error",
            "color": 12986408 if is_error else 4431943,
            "description": message
        }]}
        requests.post(webhook_url, json=embed)

    @staticmethod
    def get_video_backlog():
        ret = []

        _, dirs, __ = next(os.walk(DOWNLOAD_PATH))
        for d in dirs:
            _, __, files = next(os.walk(f"{DOWNLOAD_PATH}/{d}"))
            if len(files) == 0:
                os.rmdir(f"{DOWNLOAD_PATH}/{d}")
            else:
                ret.append(d.split("-")[0])

        return ret

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
