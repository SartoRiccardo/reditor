import eel
import util


class Application:
    def __init__(self):
        eel.init("gui")
        eel.start("index.html", size=(1200, 700), position=(100, 100))


if __name__ == '__main__':
    Application()
