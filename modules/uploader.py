import threading
import time
from random import randint
import modules.exporter
import backend.database
from backend.paths import DOWNLOAD_PATH
from datetime import datetime, timedelta
import os
from modules.logger import Logger
from backend.youtube import upload
from backend.requests import download_image


class Uploader(threading.Thread):
    UPLOAD_EVERY_DAYS = 1
    UPLOAD_HOUR = 21
    UPLOAD_MINUTE = 50

    def __init__(self):
        super().__init__()
        self.last_loop = datetime.now()
        self.adjust_last_loop()
        self.active = True

    def adjust_last_loop(self):
        self.last_loop.replace(hour=Uploader.UPLOAD_HOUR, minute=Uploader.UPLOAD_MINUTE,
                               second=0, microsecond=0)
        if self.last_loop > datetime.now():
            self.last_loop -= timedelta(days=1)

    def run(self):
        while self.active:
            try:
                self.task()
            except Exception as exc:
                print(exc)

    def task(self):
        while datetime.now() < self.last_loop + timedelta(days=Uploader.UPLOAD_EVERY_DAYS) and \
                self.active and 0:
            time.sleep(10)
        if not self.active:
            return
        self.last_loop = datetime.now()
        self.adjust_last_loop()

        videos = self.get_uploadable_videos()
        if len(videos) == 0:
            Logger.log("No videos to upload!", Logger.ERROR)
            return
        to_upload = self.choose_video(videos)
        video_data = backend.database.get_video(to_upload["id"])

        video = {
            "title": video_data["title"] + " #askreddit #funny",
            "description": video_data["title"] + "\n"
                           "We ask this question to r/AskReddit, "
                           "let's see which replies derive from this! Enjoy! "
                           "Subscribe for more memes and stuff that's hopefully funny "
                           "(it is trust me on this one).",
            "tags": "meme,memes,meme compilation,memes compilation,meme compilations," \
                    "memes compilations,based,cringe,funny,reddit,soy,soyboy,zoomer,boomer," \
                    "wojak,pepe,wojack,4chan,4channel,askreddit,r/askreddit,ask reddit," \
                    "r ask reddit",
            "category": "22",
            "privacy": "public",
            "file": f"{to_upload['path']}/{to_upload['id']}.mp4"
        }
        download_image(video_data["thumbnail"], f"{to_upload['path']}/thumbnail.png")
        upload(video, f"{to_upload['path']}/thumbnail.png", f"{to_upload['path']}/subtitles.srt")

        self.active = False

    def stop(self):
        self.active = False

    @staticmethod
    def get_uploadable_videos():
        ret = []

        videos = backend.database.get_complete_videos()
        for v in videos:
            if os.path.exists(f"{DOWNLOAD_PATH}/{v['thread']}-export"):
                ret.append({
                    "path": f"{DOWNLOAD_PATH}/{v['thread']}-export",
                    "id": v["thread"]
                })

        return ret

    @staticmethod
    def choose_video(videos):
        return videos[randint(0, len(videos)-1)]

    def upload(self):
        pass
