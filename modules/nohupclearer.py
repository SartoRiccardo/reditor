import threading
from datetime import datetime, timedelta
import time
import os


class NoHupClearer(threading.Thread):
    CLEAR_EVERY = 60*60*24 * 2

    def __init__(self):
        super().__init__()
        self.last_loop = datetime.now() - timedelta(days=1000)
        self.active = True

    def run(self):
        while self.active:
            self.task()

    def task(self):
        while datetime.now() < self.last_loop + timedelta(days=NoHupClearer.CLEAR_EVERY) and \
                self.active:
            time.sleep(10)

        self.last_loop = datetime.now()
        nohup_path = os.path.abspath(os.path.dirname(__file__)) + "../nohup.out"
        if os.path.exists(nohup_path):
            open(nohup_path, "w").close()

    def stop(self):
        self.active = False
