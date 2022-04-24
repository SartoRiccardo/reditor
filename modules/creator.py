import threading
from modules.exporter import Exporter
import backend.editor
import time
import backend.database
import backend.server
from datetime import datetime, timedelta
import backend.editor
from modules.logger import Logger
import traceback


class Creator(threading.Thread):
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
        if not self.active:
            return
        self.last_loop = datetime.now()

        videos = backend.database.get_videos()
        for vid in videos:
            if vid["document_id"]:
                continue

            # Create all videos with a thumbnail. If there are none, create only the first,
            # but only if there are no videos currently created.
            if not vid["thumbnail"] and len(backend.editor.get_files()) > 0:
                break

            title = vid["title"] if vid["title"] else vid["thread_title"]
            Logger.log(f"Creating **{title}**", Logger.INFO)
            document = backend.editor.make_askreddit_video(vid["thread"])
            backend.database.confirm_video_creation(vid["thread"], document.id)
            Logger.log(f"Created **{title}**", Logger.SUCCESS)

            self.notify_bot_creation(vid["thread"], document)

        time.sleep(10)

    @staticmethod
    def notify_bot_creation(thread_id, document):
        scenes = document.get_scenes()
        scenes = [{"id": scene.id, "media": scene.get_media_path()} for scene in scenes]
        payload = {"thread_id": thread_id, "video_id": document.id, "scenes": scenes}
        backend.server.send_to_discord_bot("VIDEO_CREATED", payload)

    def stop(self):
        self.active = False
