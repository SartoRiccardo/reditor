from __init__ import *
import unittest
import shutil
import os
import classes.video
import backend.editor
import backend.requests
import backend.video


class TestCreation(TestCaseExtended):
    zip_path = "./data/saves.zip"
    saves_path = "./data/saves"
    saves_path_tmp = f"{saves_path}-tmp"

    @classmethod
    def setUpClass(cls):
        backend.requests.download_resource("https://www.riccardosartori.it/cdn/saves.zip", cls.zip_path)
        if os.path.exists(cls.saves_path):
            shutil.move(cls.saves_path, cls.saves_path_tmp)
        shutil.unpack_archive(cls.zip_path)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.saves_path_tmp):
            if os.path.exists(cls.saves_path):
                shutil.rmtree(cls.saves_path)
            shutil.move(cls.saves_path_tmp, cls.saves_path)

        if os.path.exists(cls.zip_path):
            os.remove(cls.zip_path)

    def test_export_video(self):
        return
        backend.video.FPS = 1

        document = classes.video.Document(0)
        document.export("./tests-export", lambda x: x)
        self.assertFileExists("./tests-export/video.mp4")
        self.assertFileExists("./tests-export/subtitles.srt")

        shutil.move("./data/saves", "./data/saves-tmp")


if __name__ == '__main__':
    unittest.main(exit=False)
