#!/usr/bin/env python3
from modules import *


if __name__ == '__main__':
    up = modules.uploader.Uploader()
    up.start()
    exp = modules.exporter.Exporter()
    # exp.start()
    up.join()
    exp.join()
