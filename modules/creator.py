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
        sleep_time = 10
        while self.active:
            try:
                self.task()
                sleep_time = max(int(sleep_time/2), 10)
            except:
                Logger.log(f"`Creator` thread: ```\n{traceback.format_exc()[:1900]}\n```", Logger.ERROR)
                sleep_time *= 1.5
            time.sleep(sleep_time)

    def task(self):
        self.error_exporting = False
        if not self.active:
            return
        self.last_loop = datetime.now()

        videos = backend.database.get_videos()
        for vid in videos:
            if vid["document_id"] is not None:
                continue

            # Create all videos with a thumbnail.
            # If there is at least one video exported or created, don't create anything.
            if not vid["thumbnail"] and \
                    (len(backend.editor.get_files()) > 0 or len(Exporter.get_video_backlog()) > 0):
                continue

            title = vid["title"] if vid["title"] else vid["thread_title"]
            Logger.log(f"Creating **{title}**", Logger.INFO)
            document = backend.editor.make_askreddit_video(vid["thread"])
            backend.database.confirm_video_creation(vid["thread"], document.id)
            Logger.log(f"Created **{title}**", Logger.SUCCESS)

            self.notify_bot_creation(vid["thread"], document)

        shorts = backend.database.get_videos(with_thumbnail=True, shorts=True)
        bgm_dir = backend.database.config("rdt_bgmdir")
        for short in shorts:
            if short["document_id"] is not None:
                continue
            title = short["title"]
            Logger.log(f"Creating **{title}** *__#short__*", Logger.INFO)
            document = backend.editor.make_askreddit_video(short["thread"], max_duration=50, comment_depth=1,
                                                           bgm_dir=bgm_dir)
            document.delete_intro()
            document.delete_outro()
            backend.database.confirm_video_creation(short["thread"], document.id)
            Logger.log(f"Created #short **{title}** *__#short__*", Logger.SUCCESS)

    @staticmethod
    def notify_bot_creation(thread_id, document):
        scenes = document.get_scenes()
        scenes = [{"id": scene.id, "media": scene.get_media_path()} for scene in scenes]
        payload = {"thread_id": thread_id, "video_id": document.id, "scenes": scenes}
        backend.server.send_to_discord_bot("VIDEO_CREATED", payload)

    def stop(self):
        self.active = False
