import os
import eel


DATA_PATH = os.path.join(
    os.path.expanduser("~"),
    "Library",
    "Application Support",
    "it.riccardosartori.reditor"
)


def p(path):
    return DATA_PATH+path


def init():
    if not os.path.exists(DATA_PATH):
        os.mkdir(DATA_PATH)

    required_dirs = ["/assets", "/saves", "/saves/index.csv"]

    for d in required_dirs:
        if not os.path.exists(p(d)):
            if "." in d:
                f = open(p(d), "w")
                f.close()
            else:
                os.mkdir(p(d))


@eel.expose
def get_file_info(id):
    return {
        "name": "testvid001",
        "path": "/path/to/testvid001.rdt/",
        "scenes": 0,
        "components": 0,
        "script": [
          {
              "type": "soundtrack",
              "duration": {"m": 0, "s": 0},
              "name": None,
              "path": None,
              "number": 1
          },
        ]
      }


init()
