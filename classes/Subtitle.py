
class Subtitle:
    def __init__(self, text, start, end):
        self.start = start
        self.end = end
        self.text = text

    @staticmethod
    def time_to_str(time):
        m = int(time/60)
        s = int(time % 60)
        ms = round(time % 1, 3)
        ms_str = f"{ms:.3f}"[2:]
        return f"00:{m:02d}:{s:02d},{ms_str}"

    def __str__(self):
        return (f"{Subtitle.time_to_str(self.start)} --> {Subtitle.time_to_str(self.end)}" + "\n"
                f"{self.text}" + "\n")
