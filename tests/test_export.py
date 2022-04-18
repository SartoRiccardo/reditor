from __init__ import *
import unittest
import shutil
import os
import classes.video
import backend.editor
import backend.requests
import backend.video


class TestExport(TestCaseExtended):
    data_path = "./data"
    zip_path = f"{data_path}/saves.zip"
    saves_path = f"{data_path}/saves"
    saves_path_tmp = f"{saves_path}-tmp"
    export_path = "./tests-export"

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(cls.zip_path):
            backend.requests.download_resource("https://www.riccardosartori.it/cdn/saves.zip", cls.zip_path)
        if os.path.exists(cls.saves_path):
            shutil.move(cls.saves_path, cls.saves_path_tmp)
        shutil.unpack_archive(cls.zip_path, cls.data_path, "zip")
        if os.path.exists(f"{cls.data_path}/__MACOSX"):
            shutil.rmtree(f"{cls.data_path}/__MACOSX")

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.saves_path_tmp):
            if os.path.exists(cls.saves_path):
                shutil.rmtree(cls.saves_path)
            shutil.move(cls.saves_path_tmp, cls.saves_path)

        if os.path.exists(cls.zip_path):
            os.remove(cls.zip_path)

        if os.path.exists(cls.export_path):
            shutil.rmtree(cls.export_path)

    def test_export_video(self):
        backend.video.FPS = 1

        document = classes.video.Document(0)
        document.export(self.export_path, lambda x: x)
        self.assertFileExists(f"{self.export_path}/nonononoyes-auto.mp4")
        self.assertFileExists(f"{self.export_path}/subtitles.srt")


if __name__ == '__main__':
    unittest.main(exit=False)
