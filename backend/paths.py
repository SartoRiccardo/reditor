import os

# TODO some refactoring from the util.io file


DATA_PATH = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "..",
    "data"
)
DOWNLOAD_PATH = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "..",
    "exports",
)
LOG_PATH = os.path.join(
    DATA_PATH,
    "logs"
)


def p(path):
    return os.path.join(DATA_PATH, *(path[1:].split("/")))


def get_project_dir(id):
    return p(f"/saves/{id:05d}")


def get_scene_dir(project_id, scene_id):
    return p(f"/saves/{project_id:05d}/scenes/{scene_id:05d}")
