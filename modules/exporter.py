import json
import threading
import time
from random import randint
import backend.database
import backend.server
from datetime import datetime, timedelta
import backend.editor
import os
import gc
from backend.paths import DOWNLOAD_PATH
from classes.video.Document import Document
from modules.logger import Logger
import traceback


class Exporter(threading.Thread):
    EXPORT_EVERY = 60*60*12
    SHORTS_EXPORT_EVERY = 60*60*12
    MAX_EXPORTED_BACKLOG = 1
    SHORTS_MAX_EXPORTED_BACKLOG = 10

    def __init__(self):
        super().__init__()
        self.last_loop = datetime.now() - timedelta(seconds=Exporter.EXPORT_EVERY*10)
        self.shorts_last_loop = datetime.now() - timedelta(seconds=Exporter.SHORTS_EXPORT_EVERY*10)
        self.active = True
        self.error_exporting = False

    def run(self):
        sleep_time = 10
        while self.active:
            try:
                self.task_export_videos()
                self.task_export_shorts()
                sleep_time = max(int(sleep_time/2), 10)
            except:
                Logger.log(f"`Exporter` thread:\n```\n{traceback.format_exc()[:1900]}\n```", Logger.ERROR)
                sleep_time *= 1.5
            time.sleep(sleep_time)

    def task_export_videos(self):
        self.error_exporting = False
        while datetime.now() < self.last_loop + timedelta(seconds=Exporter.EXPORT_EVERY) or \
                len(Exporter.get_video_backlog()) >= Exporter.MAX_EXPORTED_BACKLOG or \
                not self.active:
            return

        videos = backend.database.get_videos(created=True)
        if len(videos) == 0:
            return

        self.last_loop = datetime.now()

        chosen = Exporter.choose_video(videos)
        self.export_video(chosen)

    def task_export_shorts(self):
        while datetime.now() < self.shorts_last_loop + timedelta(seconds=Exporter.SHORTS_EXPORT_EVERY) or \
                len(Exporter.get_shorts_backlog()) >= Exporter.SHORTS_MAX_EXPORTED_BACKLOG or \
                not self.active:
            return

        shorts = backend.database.get_videos(created=True, shorts=True)
        if len(shorts) == 0:
            return

        self.shorts_last_loop = datetime.now()

        chosen = Exporter.choose_video(shorts)
        self.export_video(chosen, video_type="short", delete_afterwards=False)

        document = Document(chosen["document_id"])
        document.set_background(self.get_random_video_background())
        self.export_video(chosen, video_type="tiktok")

    def export_video(self, video, video_type=None, delete_afterwards=True):
        short_str = ""
        if video_type == "tiktok":
            short_str = "__*for TikTok*__"
        elif video_type == "short":
            short_str = "__*#short*__"

        title = video["title"] if video["title"] else video["thread_title"]
        Logger.log(f"Adding soundtracks for **{title}** {short_str}", Logger.DEBUG)
        bgm_dir = backend.database.config("rdt_bgmdir")
        document = Document(video["document_id"])
        document.add_soundtracks(bgm_dir)

        Logger.log(f"Exporting **{title}** {short_str}", Logger.INFO)
        if not video["title"]:
            Logger.log(f"No title or thumbnail for **{video['thread_title']}** {short_str}", Logger.WARN)

        self.notify_bot_export_start(document)

        if not os.path.exists(DOWNLOAD_PATH):
            os.mkdir(DOWNLOAD_PATH)
        export_path = f"{DOWNLOAD_PATH}/{document.name}-export"
        if video_type == "short":
            export_path = self.special_export_path("shorts", document)
        elif video_type == "tiktok":
            export_path = self.special_export_path("tiktoks", document)
        document.export(export_path, log_callback=self.check_errors,
                        size=("1080-v" if video_type in ["tiktok", "short"] else "720"))

        if not self.error_exporting:
            backend.database.confirm_export(video["thread"])
        if delete_afterwards:
            document.delete()
        Logger.log(f"Exported **{title}** {short_str}", Logger.SUCCESS)
        gc.collect()

    @staticmethod
    def special_export_path(subdir, document):
        export_path = f"{DOWNLOAD_PATH}/{subdir}/{document.name}-export"
        if not os.path.exists(f"{DOWNLOAD_PATH}/{subdir}"):
            os.mkdir(f"{DOWNLOAD_PATH}/{subdir}")
        return export_path

    def stop(self):
        self.active = False

    def check_errors(self, evt):
        if "error_msg" not in evt:
            return
        self.error_exporting = True
        # Log somewhere
        Logger.log(evt["error_msg"], Logger.ERROR)

    @staticmethod
    def get_video_backlog():
        ret = []

        _, dirs, __ = next(os.walk(DOWNLOAD_PATH))
        for d in dirs:
            _, __, files = next(os.walk(f"{DOWNLOAD_PATH}/{d}"))
            if "-export" not in d:
                continue
            if len(files) == 0:
                os.rmdir(f"{DOWNLOAD_PATH}/{d}")
            else:
                ret.append(d.split("-")[0])

        return ret

    @staticmethod
    def get_shorts_backlog():
        ret = []
        if not os.path.exists(f"{DOWNLOAD_PATH}/shorts"):
            return ret

        _p, dirs, _f = next(os.walk(f"{DOWNLOAD_PATH}/shorts"))
        for d in dirs:
            _p, _d, files = next(os.walk(f"{DOWNLOAD_PATH}/shorts/{d}"))
            if len(files) == 0:
                os.rmdir(f"{DOWNLOAD_PATH}/shorts/{d}")
            else:
                ret.append(d.split("-")[0])

        return ret

    @staticmethod
    def notify_bot_export_start(document):
        backend.server.send_to_discord_bot("EXPORT", document.id)

    @staticmethod
    def choose_video(videos):
        ready_count = 0
        while ready_count < len(videos):
            if videos[ready_count]["thumbnail"] is None:
                break
            ready_count += 1

        if ready_count > 0:
            return videos[randint(0, ready_count-1)]

        if len(videos) == 0:
            Logger.log("No videos created!", Logger.WARN)
        else:
            Logger.log("No videos currently have title/thumbnail set!", Logger.WARN)
        return videos[randint(0, len(videos)-1)]

    @staticmethod
    def get_random_video_background():
        fconfig = open("video-config.json")
        backgrounds = json.loads(fconfig.read())["backgrounds"]
        chosen = backgrounds[randint(0, len(backgrounds)-1)]
        fconfig.close()
        return chosen
