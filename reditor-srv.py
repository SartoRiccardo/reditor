#!/usr/bin/env python3
from modules import *
import time
import os


def should_stop():
    return os.path.exists("./STOP")


def remove_stop():
    return os.remove("./STOP")


if __name__ == '__main__':
    threads = [
        modules.uploader.Uploader(),
        modules.exporter.Exporter(),
        modules.creator.Creator(),
    ]
    c = modules.nohupclearer.NoHupClearer()
    
    c.start()
    time.sleep(1)
    [t.start() for t in threads]

    while not should_stop():
        time.sleep(10)
    remove_stop()
    [t.stop() for t in threads]
    c.stop()

    [t.join() for t in threads]
    c.join()
