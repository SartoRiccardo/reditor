import os

# TODO some refactoring from the util.io file


DATA_PATH = os.path.join(
    os.path.expanduser("~"),
    "Library",
    "Application Support",
    "it.riccardosartori.reditor"
)
DOWNLOAD_PATH = os.path.join(
    os.path.expanduser("~"),
    "Downloads",
)


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def p(path):
    return DATA_PATH+path


def get_project_dir(id):
    return p(f"/saves/{id:05d}")


def get_scene_dir(project_id, scene_id):
    return p(f"/saves/{project_id:05d}/scenes/{scene_id:05d}")
