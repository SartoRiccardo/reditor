import threading
import time
from random import randint
import modules.exporter
import backend.database
from backend.paths import DOWNLOAD_PATH
from datetime import datetime, timedelta
import os
from modules.logger import Logger
from backend.youtube import upload, UploadDetailException
from backend.requests import download_image
import traceback


class Uploader(threading.Thread):
    UPLOAD_EVERY_DAYS = 1
    UPLOAD_HOUR = 21 - 1  # UTC+000, I live in UTC+001
    UPLOAD_MINUTE = 50

    def __init__(self):
        super().__init__()
        self.last_loop = datetime.now()
        self.adjust_last_loop()
        self.active = True

    def adjust_last_loop(self):
        self.last_loop = self.last_loop.replace(hour=Uploader.UPLOAD_HOUR, minute=Uploader.UPLOAD_MINUTE,
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
                self.active:
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

        Logger.log(f"Uploading {video_data['title']}", Logger.INFO)
        video = {
            "title": video_data["title"],
            "description": f"{video_data['thread_title']}\n"
                           "We ask this question to r/AskReddit, "
                           "let's see which replies derive from this! Enjoy! "
                           "Subscribe for more memes and stuff that's hopefully funny "
                           "(it is trust me on this one)." + "\n\n"
                           "#askreddit #funny",
            "tags": "meme,memes,meme compilation,memes compilation,meme compilations,"
                    "memes compilations,based,cringe,funny,reddit,soy,soyboy,zoomer,boomer,"
                    "wojak,pepe,wojack,4chan,4channel,askreddit,r/askreddit,ask reddit,"
                    "r ask reddit",
            "category": "22",
            "privacy": "public",
            "file": f"{to_upload['path']}/{to_upload['id']}.mp4"
        }
        download_image(video_data["thumbnail"], f"{to_upload['path']}/thumbnail.png")
        try:
            video_id = upload(video, f"{to_upload['path']}/thumbnail.png", f"{to_upload['path']}/subtitles.srt")
            url = f"https://www.youtube.com/watch?v={video_id}"

            backend.database.confirm_video_upload(to_upload["id"], url)
            Logger.log(f"Uploaded {video_data['title']} to {url}", Logger.SUCCESS)
            if os.path.exists(to_upload['path']):
                os.remove(f"{to_upload['path']}/thumbnail.png")
                os.remove(f"{to_upload['path']}/subtitles.srt")
                os.remove(f"{to_upload['path']}/{to_upload['id']}.mp4")
                os.rmdir(to_upload['path'])
        except UploadDetailException as exc:
            url = f"https://www.youtube.com/watch?v={exc.uploaded_id}"
            backend.database.confirm_video_upload(to_upload["id"], url)
            Logger.log(f"Uploaded {video_data['title']} to {url}", Logger.SUCCESS)
            Logger.log(f"```\n{traceback.format_exc()[:1900]}\n```", Logger.ERROR)
        except Exception as exc:
            Logger.log(f"```\n{traceback.format_exc()[:1900]}\n```", Logger.ERROR)

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
