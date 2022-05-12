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
    SHORTS_MAX_EXPORTED_BACKLOG = 3

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
                time.sleep(sleep_time)
                sleep_time = max(int(sleep_time/2), 10)
            except:
                Logger.log(f"`Exporter` thread:\n```\n{traceback.format_exc()[:1900]}\n```", Logger.ERROR)
                sleep_time *= 1.5

    def task_export_videos(self):
        self.error_exporting = False
        while (datetime.now() < self.last_loop + timedelta(seconds=Exporter.EXPORT_EVERY) or
                len(Exporter.get_video_backlog()) > Exporter.MAX_EXPORTED_BACKLOG) and self.active:
            return

        if not self.active:
            return
        self.last_loop = datetime.now()

        videos = backend.database.get_videos(created=True)
        if len(videos) == 0:
            return

        chosen = Exporter.choose_video(videos)
        self.export_video(chosen)

    def task_export_shorts(self):
        while (datetime.now() < self.shorts_last_loop + timedelta(seconds=Exporter.SHORTS_EXPORT_EVERY) or
                len(Exporter.get_shorts_backlog()) >= Exporter.SHORTS_MAX_EXPORTED_BACKLOG) and self.active:
            return

        if not self.active:
            return
        self.last_loop = datetime.now()

        shorts = backend.database.get_videos(created=True, shorts=True)
        if len(shorts) == 0:
            return

        chosen = Exporter.choose_video(shorts)
        self.export_video(chosen, short=True)

    def export_video(self, video, short=False):
        short_str = "*__#short__*" if short else ""

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
        if short:
            export_path = f"{DOWNLOAD_PATH}/shorts/{document.name}-export"
            if not os.path.exists(f"{DOWNLOAD_PATH}/shorts"):
                os.mkdir(f"{DOWNLOAD_PATH}/shorts")
        document.export(export_path, log_callback=self.check_errors,
                        size=("720" if not short else "1080-v"))

        if not self.error_exporting:
            backend.database.confirm_export(video["thread"])
        document.delete()
        Logger.log(f"Exported **{title}** {short_str}", Logger.SUCCESS)
        gc.collect()

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
            _p, _d, files = next(os.walk(f"{DOWNLOAD_PATH}/{d}"))
            if len(files) == 0:
                os.rmdir(f"{DOWNLOAD_PATH}/{d}")
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
