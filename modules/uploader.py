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
    UPLOAD_HOUR = 21 - 2  # UTC+000, I live in UTC+002
    UPLOAD_MINUTE = 50

    SHORT_UPLOAD_EVERY_DAYS = 1
    SHORT_UPLOAD_HOUR = 15 - 2  # UTC+000, I live in UTC+002
    SHORT_UPLOAD_MINUTE = 50

    def __init__(self):
        super().__init__()
        self.last_loop = datetime.now()
        self.short_last_loop = datetime.now()
        self.adjust_last_loop()
        self.adjust_last_loop(shorts=True)
        self.active = True

    def adjust_last_loop(self, shorts=False):
        if not shorts:
            self.last_loop = self.last_loop.replace(
                hour=Uploader.UPLOAD_HOUR,
                minute=Uploader.UPLOAD_MINUTE,
                second=0, microsecond=0
            )
            if self.last_loop > datetime.now():
                self.last_loop -= timedelta(days=1)
        else:
            self.short_last_loop = self.short_last_loop.replace(
                hour=Uploader.SHORT_UPLOAD_HOUR,
                minute=Uploader.SHORT_UPLOAD_MINUTE,
                second=0, microsecond=0
            )
            if self.short_last_loop > datetime.now():
                self.short_last_loop -= timedelta(days=1)

    def run(self):
        sleep_time = 10
        while self.active:
            try:
                self.task()
                self.task_shorts()
                sleep_time = max(sleep_time/2, 10)
            except:
                Logger.log(f"`Uploader` thread:\n```\n{traceback.format_exc()[:1900]}\n```", Logger.ERROR)
                sleep_time *= 1.5
            time.sleep(sleep_time)

    def task(self):
        while datetime.now() < self.last_loop + timedelta(days=Uploader.UPLOAD_EVERY_DAYS) or \
                not self.active:
            return
        self.last_loop = datetime.now()
        self.adjust_last_loop()

        videos = self.get_uploadable_videos()
        if len(videos) == 0:
            Logger.log("No videos to upload!", Logger.ERROR)
            return
        to_upload = self.choose_video(videos)
        video_data = backend.database.get_video(to_upload["id"])
        self.upload_video(to_upload, video_data)

    def task_shorts(self):
        while datetime.now() < self.short_last_loop + timedelta(days=Uploader.SHORT_UPLOAD_EVERY_DAYS) or \
                not self.active:
            return
        self.short_last_loop = datetime.now()
        self.adjust_last_loop(shorts=True)

        shorts = self.get_uploadable_videos(shorts=True)
        if len(shorts) == 0:
            Logger.log("No shorts to upload!", Logger.WARN)
            return
        to_upload = self.choose_video(shorts)
        video_data = backend.database.get_video(to_upload["id"])

        if backend.database.config("rdt_server-debug") == "true":
            Logger.log(f"UPLOADING SHORT:\n```\n{video_data=}\n```\n```\n{to_upload=}\n```", Logger.DEBUG)
        else:
            self.upload_video(to_upload, video_data, short=True)

    def upload_video(self, video, video_data, short=False):
        short_log_str = "*__#short__*" if short else ""
        Logger.log(f"Uploading {video_data['title']} {short_log_str}", Logger.INFO)

        title_safe = self.turn_to_path(video_data["title"])
        video_path = f"{video['path']}/{title_safe}.mp4"
        if not os.path.exists(video_path):
            os.rename(f"{video['path']}/{video['id']}-auto.mp4", video_path)

        youtube_video = {
            "title": video_data["title"] + (' #short' if short else ''),
            "description": f"{video_data['thread_title']}\n"
                           "We ask this question to r/AskReddit, "
                           "let's see which replies derive from this! Enjoy! "
                           "Subscribe for more memes and stuff that's hopefully funny "
                           "(it is trust me on this one)." + "\n\n"
                           f"#askreddit #funny{' #short' if short else ''}",
            "tags": "meme,memes,meme compilation,memes compilation,meme compilations,"
                    "memes compilations,based,cringe,funny,reddit,soy,soyboy,zoomer,boomer,"
                    "wojak,pepe,wojack,4chan,4channel,askreddit,r/askreddit,ask reddit,"
                    "r ask reddit",
            "category": "22",
            "privacy": "public",
            "file": video_path
        }
        download_image(video_data["thumbnail"], f"{video['path']}/thumbnail.png")
        video_id = None
        try:
            video_id = upload(youtube_video, f"{video['path']}/thumbnail.png", f"{video['path']}/subtitles.srt")
            url = f"https://www.youtube.com/watch?v={video_id}"

            backend.database.confirm_video_upload(video["id"], url)
            Logger.log(f"Uploaded {video_data['title']} {short_log_str} to {url}", Logger.SUCCESS)
            if os.path.exists(video['path']):
                os.remove(f"{video['path']}/thumbnail.png")
                os.remove(f"{video['path']}/subtitles.srt")
                os.remove(video_path)
                os.rmdir(video['path'])
        except UploadDetailException as exc:
            url = f"https://www.youtube.com/watch?v={exc.uploaded_id}"
            backend.database.confirm_video_upload(video["id"], url)
            Logger.log(f"Uploaded {video_data['title']} {short_log_str} to {url}", Logger.SUCCESS)
            Logger.log(f"```\n{traceback.format_exc()[:1900]}\n```", Logger.ERROR)
        except Exception as exc:
            if video_id:
                url = f"https://www.youtube.com/watch?v={video_id}"
                Logger.log(f"Uploaded {video_data['title']} {short_log_str} to {url}", Logger.SUCCESS)
            Logger.log(f"```\n{traceback.format_exc()[:1900]}\n```", Logger.ERROR)

    def stop(self):
        self.active = False

    @staticmethod
    def get_uploadable_videos(shorts=False):
        ret = []

        shorts_path = "/shorts" if shorts else ""
        videos = backend.database.get_complete_videos(shorts)
        for v in videos:
            if os.path.exists(f"{DOWNLOAD_PATH}{shorts_path}/{v['thread']}-auto-export"):
                ret.append({
                    "path": f"{DOWNLOAD_PATH}{shorts_path}/{v['thread']}-auto-export",
                    "id": v["thread"],
                })

        return ret

    @staticmethod
    def choose_video(videos):
        return videos[randint(0, len(videos)-1)]

    @staticmethod
    def turn_to_path(text):
        allowed = "qwertyuiopasdfghjklzxcvbnm1234567890"
        ret = ""
        for char in text.lower():
            if char in allowed:
                ret += char
            elif char == " ":
                ret += "_"
        return ret[:100]
