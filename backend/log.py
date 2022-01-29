import csv
import backend
import time
from datetime import datetime


def __log(log_path, row):
    row = [] + row
    row.insert(0, time.time())
    fout = open(log_path, "a+")
    writer = csv.writer(fout, delimiter=";")
    writer.writerow(row)
    fout.close()


def tts(text, voice):
    log_path = backend.paths.p("/logs/text-to-speech.csv")
    __log(log_path, [text, voice])


def get_monthly_characters():
    ret = {}
    log_path = backend.paths.p("/logs/text-to-speech.csv")
    fout = open(log_path, "r")
    reader = csv.reader(fout, delimiter=";")

    for timestamp, text, voice in reader:
        timestamp = float(timestamp)
        log_time = datetime.fromtimestamp(timestamp)
        key = f"{log_time.year}-{log_time.month}"
        if key not in ret:
            ret[key] = len(text)
        else:
            ret[key] += len(text)

    fout.close()
    return ret


def export_start(file_id):
    log_path = backend.paths.p("/logs/export.csv")
    __log(log_path, ["START", file_id, None])


def export_end(file_id):
    log_path = backend.paths.p("/logs/export.csv")
    __log(log_path, ["FINISH", file_id, None])


def export_err(file_id, error):
    log_path = backend.paths.p("/logs/export.csv")
    __log(log_path, ["ERROR", file_id, error])
