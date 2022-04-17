from __init__ import *
import unittest
import os
import moviepy.editor as mpy
import gizeh


class MPYTest(TestCaseExtended):
    def test_gizeh(self):
        """
        Test that the Gizeh library works properly.
        """
        def make_frame(t):
            surface = gizeh.Surface(128, 128)  # width, height
            radius = 100 * (1 + (t * (2 - t)) ** 2) / 6  # the radius varies over time
            circle = gizeh.circle(radius, xy=(64, 64), fill=(1, 0, 0))
            circle.draw(surface)
            return surface.get_npimage()  # returns a 8-bit RGB array

        clip = mpy.VideoClip(make_frame, duration=2)  # 2 seconds
        clip.write_gif("./test-gif.gif", fps=15)
        self.assertFileExists("./test-gif.gif")
        os.remove("./test-gif.gif")

    def test_moviepy_text(self):
        """
        Test that Moviepy is able to render text.
        """
        def make_frame(t):
            surface = gizeh.Surface(128, 128)  # width, height
            radius = 100 * (1 + (t * (2 - t)) ** 2) / 6  # the radius varies over time
            circle = gizeh.circle(radius, xy=(64, 64), fill=(1, 0, 0))
            circle.draw(surface)
            return surface.get_npimage()  # returns a 8-bit RGB array

        clip = mpy.VideoClip(make_frame, duration=2)  # 2 seconds

        txt_clip = mpy.TextClip("TEST", fontsize=75, color='black')
        txt_clip = txt_clip.set_position('center').set_duration(10)

        video = mpy.CompositeVideoClip([clip, txt_clip])
        video.write_videofile("./test-text.mp4", fps=1)
        self.assertFileExists("./test-text.mp4")
        os.remove("./test-text.mp4")


if __name__ == '__main__':
    unittest.main()
