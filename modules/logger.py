import backend.database
import requests
from datetime import datetime, timedelta
import time


last_log = datetime.now()


class Logger:
    DEBUG = 14938877
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
        if severity == Logger.DEBUG:
            title = "Debug"
        elif severity == Logger.SUCCESS:
            title = "Success"
        elif severity == Logger.ERROR:
            title = "Error"
        elif severity == Logger.WARN:
            title = "Warning"

        webhook_url, debug = backend.database.config(["rdt_logger", "rdt_logger_debug"])
        if not (bool(debug) or debug is None) and severity == Logger.DEBUG:
            return

        embed = {"embeds": [{
            "title": title,
            "color": severity,
            "description": message,
            "footer": {"text": "reditor-server"}
        }]}
        requests.post(webhook_url, json=embed)
