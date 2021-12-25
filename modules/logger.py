import backend.database
import requests


class Logger:
    INFO = 2001125
    SUCCESS = 4431943
    ERROR = 12986408
    WARN = 16772696

    @staticmethod
    def log(message, severity):
        webhook_url = backend.database.config("rdt_logger")
        embed = {"embeds": [{
            "title": "Error",
            "color": severity,
            "description": message
        }]}
        requests.post(webhook_url, json=embed)
