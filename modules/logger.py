import backend.database
import requests
from datetime import datetime, timedelta
import time


last_log = datetime.now()


class Logger:
    INFO = 2001125
    SUCCESS = 4431943
    ERROR = 12986408
    WARN = 16772696

    @staticmethod
    def log(message, severity):
        global last_log
        if datetime.now() < last_log+timedelta(seconds=3):
            time.sleep(3)
        last_log = datetime.now()

        title = "Info"
        if severity == Logger.SUCCESS:
            title = "Success"
        elif severity == Logger.ERROR:
            title = "Error"
        elif severity == Logger.WARN:
            title = "Warning"

        webhook_url = backend.database.config("rdt_logger")
        embed = {"embeds": [{
            "title": title,
            "color": severity,
            "description": message
        }]}
        requests.post(webhook_url, json=embed)
