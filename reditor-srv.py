#!/usr/bin/env python3
from modules import *
import time
import os


def should_stop():
    return os.path.exists("./STOP")


def remove_stop():
    return os.remove("./STOP")


if __name__ == '__main__':
    up = modules.uploader.Uploader()
    up.start()
    exp = modules.exporter.Exporter()
    exp.start()
    c = modules.nohupclearer.NoHupClearer()
    c.start()

    while not should_stop():
        time.sleep(10)
    remove_stop()
    up.stop()
    exp.stop()
    c.stop()

    up.join()
    exp.join()
    c.join()
