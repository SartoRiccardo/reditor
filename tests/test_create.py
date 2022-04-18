from __init__ import *
import unittest
import os
import backend.editor
import backend.requests
import backend.video
import shutil


class TestCreation(TestCaseExtended):
    @classmethod
    def setUpClass(cls):
        urls = [
            "https://cdn.discordapp.com/attachments/924255725390270474/964970335512436756/Littleroot_Town.mp3",
            "https://cdn.discordapp.com/attachments/924255725390270474/964970336011563108/Oldale_Town.mp3",
            "https://cdn.discordapp.com/attachments/924255725390270474/964970336552640592/Professor_Birchs_Laboratory.mp3",
            "https://cdn.discordapp.com/attachments/924255725390270474/964970337173373048/Trick_House.mp3",
            "https://cdn.discordapp.com/attachments/924255725390270474/964970375098290176/Accumula_Town.mp3",
            "https://cdn.discordapp.com/attachments/924255725390270474/964970375660335194/Anville_Town.mp3",
            "https://cdn.discordapp.com/attachments/924255725390270474/964970376255914014/Castelia_City.mp3",
            "https://cdn.discordapp.com/attachments/924255725390270474/964970376683724830/Dreamyard.mp3",
            "https://cdn.discordapp.com/attachments/924255725390270474/964970377333837834/Skyarrow_Bridge.mp3",
        ]
        if not os.path.exists("./tests-music"):
            os.mkdir("./tests-music")
        for i in range(len(urls)):
            if not os.path.exists(f"./tests-music/song-{i}.mp3"):
                backend.requests.download_resource(urls[i], f"./tests-music/song-{i}.mp3")

    @classmethod
    def tearDownClass(cls):
        paths_to_remove = ["./tests-music"]
        for path in paths_to_remove:
            if os.path.exists(path):
                shutil.rmtree(path)

    def test_askreddit_video_created(self):
        document = backend.editor.make_askreddit_video("o76lzv", "./tests-music")
        document.delete()

    def test_media_video_created(self):
        self.to_export = backend.editor.make_media_video("nonononoyes", "./tests-music")


if __name__ == '__main__':
    unittest.main(exit=False)
