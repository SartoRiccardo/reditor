import threading
import time
from datetime import datetime, timedelta


class Uploader(threading.Thread):
    UPLOAD_EVERY = 60*60*24

    def __init__(self):
        super().__init__()
        self.last_loop = datetime.now()
        self.active = True

    def run(self):
        while self.active:
            while datetime.now() < self.last_loop + timedelta(seconds=Uploader.UPLOAD_EVERY) and \
                    self.active:
                time.sleep(10)
            if not self.active:
                return
            self.last_loop = datetime.now()

            print("Uploader - TODO")

    def stop(self):
        self.active = False

    def get_uploadable_videos(self):
        pass

    def choose_video(self, videos):
        pass

    def upload(self):
        pass
