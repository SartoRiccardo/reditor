import eel
import util.io


class Application:
    def __init__(self):
        eel.init("gui")
        eel.start("index.html")


if __name__ == '__main__':
    Application()
