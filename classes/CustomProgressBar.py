from proglog import TqdmProgressBarLogger


class CustomProgressBar(TqdmProgressBarLogger):
    def __init__(self, total_frames=0, gui_callback=None, fps=25):
        super().__init__(bars=None, ignored_bars=None, logged_bars='all',
                         min_time_interval=0, ignore_bars_under=0)
        self.total_frames = total_frames
        self.started_video = False
        self.gui_callback = gui_callback
        if self.gui_callback:
            self.gui_callback({"started": True, "percentage": 0})
        self.prev_percentage = 100
        self.fps = fps

    def set_total_frames(self, frames):
        self.total_frames = frames

    def bars_callback(self, bar, attr, value, old_value):
        super().bars_callback(bar, attr, value, old_value)
        if self.started_video and self.gui_callback:
            percentage = (value+1)/self.total_frames*100
            percentage = CustomProgressBar.trunc_half(percentage)
            if percentage > 100:
                percentage = 100
            if percentage != self.prev_percentage:
                self.gui_callback({"percentage": percentage})
                self.prev_percentage = percentage

    @staticmethod
    def trunc_half(num):
        return num - (int(num * 10) % 3) / 10

    def callback(self, **changes):
        super().callback(**changes)

        if "message" in changes:
            msg = changes["message"]
            if "Writing video" in msg:
                vidlen = self.total_frames / self.fps
                m = int(vidlen/60)
                s = int(vidlen % 60)

                self.started_video = True
                self.prev_percentage = 100
                self.gui_callback({"status": "video"})
            elif "Writing audio" in msg:
                if self.gui_callback:
                    self.gui_callback({"status": "audio"})
            elif "video ready" in msg:
                if self.gui_callback:
                    self.gui_callback({"finished": True})
