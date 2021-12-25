import threading
import time
from random import randint
import backend.database
from datetime import datetime, timedelta


class Exporter(threading.Thread):
    # UPLOAD_EVERY = 60*60*24
    UPLOAD_EVERY = 10

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
