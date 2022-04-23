import threading
import time
from random import randint
import backend.database
import backend.websockets
from datetime import datetime, timedelta
import backend.editor
import os
import gc
from backend.paths import DOWNLOAD_PATH
from classes.video.Document import Document
import requests
from modules.logger import Logger
import traceback


class Exporter(threading.Thread):
    EXPORT_EVERY = 60*60*12

    def __init__(self):
        super().__init__()
        self.last_loop = datetime.now() - timedelta(seconds=Exporter.EXPORT_EVERY*10)
        self.active = True
        self.error_exporting = False

    def run(self):
        while self.active:
            try:
                self.task()
            except:
                Logger.log(f"```\n{traceback.format_exc()[:1900]}\n```", Logger.ERROR)

    def task(self):
        self.error_exporting = False
        while (datetime.now() < self.last_loop + timedelta(seconds=Exporter.EXPORT_EVERY) or
                len(Exporter.get_video_backlog()) > 3) and self.active:
            time.sleep(10)
        if not self.active:
            return
        self.last_loop = datetime.now()

        videos = backend.database.get_videos()
        if len(videos) == 0:
            return

        print(videos)
        chosen = Exporter.choose_video(videos)
        print(f"CHOSEN: {chosen}")
        title = chosen["title"] if chosen["title"] else chosen["thread_title"]

        Logger.log(f"Adding soundtracks for **{title}**", Logger.DEBUG)
        bgm_dir = backend.database.config("rdt_bgmdir")
        document = Document(chosen["document_id"])
        document.add_soundtracks(bgm_dir)

        Logger.log(f"Exporting **{title}**", Logger.INFO)
        if not chosen["title"]:
            Logger.log(f"No title or thumbnail for **{chosen['thread_title']}**", Logger.WARN)

        self.notify_bot_export_start(document)
        document.export(f"{DOWNLOAD_PATH}/{document.name}-export", log_callback=self.check_errors)
        if not self.error_exporting:
            backend.database.confirm_export(chosen["thread"])
        document.delete()
        Logger.log(f"Exported **{title}**", Logger.SUCCESS)
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
    def notify_bot_export_start(document):
        backend.websockets.send_to_discord_bot("EXPORT", document.id)

    @staticmethod
    def choose_video(videos):
        ready_count = 0
        while ready_count < len(videos):
            if videos[ready_count]["thumbnail"] is None:
                break
            ready_count += 1

        if ready_count > 0:
            return videos[randint(0, ready_count-1)]

        Logger.log("No videos currently have title/thumbnail set!", Logger.WARN)
        return videos[randint(0, len(videos)-1)]
