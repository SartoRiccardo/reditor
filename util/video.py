import imageio
try:
    from moviepy.video.VideoClip import ImageClip
    from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
    from moviepy.video.io.VideoFileClip import VideoFileClip
    from moviepy.audio.io.AudioFileClip import AudioFileClip
    from moviepy.audio.fx.audio_normalize import audio_normalize
    from moviepy.audio.AudioClip import CompositeAudioClip

    from moviepy.video.VideoClip import VideoClip
    from moviepy.video.fx.resize import resize
    from moviepy.video.fx.loop import loop
    from moviepy.video.fx.fadein import fadein
    from moviepy.video.fx.fadeout import fadeout
    from moviepy.video.fx.crop import crop
    VideoClip.loop = loop
    VideoClip.resize = resize
    VideoClip.fadein = fadein
    VideoClip.fadeout = fadeout
    CompositeVideoClip.fadeout = fadeout
    VideoClip.crop = crop

    from moviepy.audio.AudioClip import AudioClip
    from moviepy.audio.fx.audio_fadeout import audio_fadeout
    from moviepy.audio.fx.volumex import volumex
    AudioClip.audio_fadeout = audio_fadeout
    AudioClip.volumex = volumex
except imageio.core.fetching.NeedDownloadError:
    imageio.plugins.ffmpeg.download()
import util.io
import util.requests
import PIL
import os
from proglog import TqdmProgressBarLogger


WHITE = (255, 255, 255)
SIZES = {
    720: (1280, 720),
    1080: (1920, 1080),
}
VIDEO_SIZE = SIZES[720]
SOUNDTRACK_FADE_TIME = 1
VIDEO_FADE_TIME = 1
FPS = 30
BR = "\n"


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
        return f"{Subtitle.time_to_str(self.start)} --> {Subtitle.time_to_str(self.end)}" + BR + \
            f"{self.text}" + BR


class CustomProgressBar(TqdmProgressBarLogger):
    def __init__(self, total_frames=0, gui_callback=None):
        super().__init__(bars=None, ignored_bars=None, logged_bars='all',
                         min_time_interval=0, ignore_bars_under=0)
        self.total_frames = total_frames
        self.started_video = False
        self.gui_callback = gui_callback
        if self.gui_callback:
            self.gui_callback({"message": "Started exporting", "percentage": 0})
        self.prev_percentage = 100

    def set_total_frames(self, frames):
        self.total_frames = frames

    def bars_callback(self, bar, attr, value, old_value):
        super().bars_callback(bar, attr, value, old_value)
        if self.started_video and self.gui_callback:
            percentage = int((value+1)/self.total_frames*100)
            percentage = CustomProgressBar.trunc_half(percentage)
            if percentage != self.prev_percentage:
                self.gui_callback({"percentage": percentage})
                self.prev_percentage = percentage

    @staticmethod
    def trunc_half(num):
        return num - (int(num * 10) % 5) / 10

    def callback(self, **changes):
        super().callback(**changes)

        if "message" in changes:
            msg = changes["message"]
            if "Writing video" in msg:
                self.started_video = True
                self.prev_percentage = 100
                self.gui_callback({"message": "Exporting video..."})
            elif "Writing audio" in msg:
                if self.gui_callback:
                    self.gui_callback({"message": "Creating audio..."})
            elif "video ready" in msg:
                if self.gui_callback:
                    self.gui_callback({"message": "Video ready!", "finished": True})


def export_video(file_id, out_dir, gui_callback=None):
    """
    Pieces together the video with all the info found in the document's directory.
    :param file_id: int: The numerical ID of the file.
    :param out_dir: str: A path pointing to a new directory.
    :param gui_callback: function: A function called every time the state changes.
    """
    document = util.io.get_file_info(file_id)
    cache_dir = util.io.get_cache_dir(file_id)
    logger = CustomProgressBar(gui_callback=gui_callback)

    transition = VideoFileClip(util.io.DATA_PATH + "/assets/transition.mp4")
    intro = VideoFileClip(util.io.DATA_PATH + "/assets/intro.mp4")
    outro = VideoFileClip(util.io.DATA_PATH + "/assets/outro.mp4")

    if os.path.exists(util.io.DATA_PATH + "/assets/background.mp4"):
        background = VideoFileClip(util.io.DATA_PATH + "/assets/background.mp4"). \
            set_position(("center", "center")). \
            loop()
    else:
        background = ImageClip(util.io.DATA_PATH + "/assets/background.png"). \
            set_position(("center", "center"))
    if background.w/background.h <= 16/9:
        background = background.resize(width=VIDEO_SIZE[0])
    else:
        background = background.resize(height=VIDEO_SIZE[1])
    background = background. \
        fadein(VIDEO_FADE_TIME)

    t = intro.duration
    clips = [intro, background.set_start(t)]
    t += VIDEO_FADE_TIME
    audios = [intro.audio]
    subtitles = []
    part_soundtrack = None
    for i in range(len(document["script"])):
        s = document["script"][i]
        if s["type"] == "soundtrack":
            part_soundtrack = AudioFileClip(s["path"]). \
                set_start(t). \
                fx(audio_normalize). \
                volumex(0.2)

        elif s["type"] == "transition":
            if part_soundtrack:
                part_start = part_soundtrack.start
                part_end = t-SOUNDTRACK_FADE_TIME
                if part_end > part_start+part_soundtrack.duration:
                    part_end = part_start + part_soundtrack.duration
                part_soundtrack = part_soundtrack. \
                    set_end(part_end). \
                    audio_fadeout(SOUNDTRACK_FADE_TIME)
                audios.append(part_soundtrack)
            part_soundtrack = None

            clips.append(transition.
                         set_start(t))
            audios.append(transition.audio.
                          set_start(t))
            t += transition.duration

        if s["type"] == "scene":
            scenes_left = 0
            for j in range(i+1, len(document["script"])):
                if document["script"][j]["type"] == "scene":
                    scenes_left += 1

            scene = util.io.get_scene_info(s["number"], file_id)
            scene_clips, part_subtitles, t = get_scene_clips(t, scene, cache_dir, scenes_left == 0)
            subtitles += part_subtitles
            for c in scene_clips:
                if isinstance(c, ImageClip) or isinstance(c, CompositeVideoClip):
                    clips.append(c)
                elif isinstance(c, AudioFileClip):
                    audios.append(c)

    clips[1] = clips[1]. \
        set_end(t). \
        fadeout(VIDEO_FADE_TIME). \
        fadein(VIDEO_FADE_TIME)

    if part_soundtrack:
        part_start = part_soundtrack.start
        part_end = t - SOUNDTRACK_FADE_TIME
        if part_end > part_start + part_soundtrack.duration:
            part_end = part_start + part_soundtrack.duration
        part_soundtrack = part_soundtrack. \
            set_end(part_end). \
            audio_fadeout(SOUNDTRACK_FADE_TIME)
        audios.append(part_soundtrack)

    clips.append(outro.set_start(t))
    audios.append(outro.audio.set_start(t))
    t += outro.duration

    audios = CompositeAudioClip(audios). \
        set_duration(t)
    video = CompositeVideoClip(clips, size=VIDEO_SIZE). \
        on_color(color=WHITE, col_opacity=1). \
        set_audio(audios). \
        set_duration(t)

    fsub = open(out_dir+"/subtitles.srt", "w")
    for i in range(len(subtitles)):
        s = subtitles[i]
        fsub.write(f"{i+1}\n")
        fsub.write(str(s))
        if i != len(subtitles)-1:
            fsub.write("\n")
    fsub.close()

    logger.set_total_frames(t*FPS)
    video.write_videofile(out_dir+"/video.mp4", fps=FPS, audio_codec="aac", logger=logger)


def get_scene_clips(t, scene, cache_dir, is_last=False):
    """
    Creates audio and image clips with the given scene
    :param t: int: The time the scene will start at.
    :param scene: Scene: The scene to convert to clips.
    :param cache_dir: str: A directory in which to put downloaded temporary audio files.
    :param is_last: boolean: Whether it's the last scene. If it is, it fades out to black.
    :return: [Clip[], Subtitle[], int]: A list of clips, subtitle and the time at which the scene ends.
    """
    clips = []
    audios = []
    subtitles = []

    img_path = scene["image_path"]
    img_w, img_h = PIL.Image.open(img_path).size
    new_h = VIDEO_SIZE[1]*0.9
    new_w = new_h * img_w / img_h
    img_raw = ImageClip(img_path). \
        resize(height=new_h)

    for i in range(len(scene["script"])):
        part = scene["script"][i]
        wait_length = t + part["wait"]
        if part["text"]:
            audio_path = cache_dir+f"/{scene['number']:05d}-{i:05d}.mp3"
            if not os.path.exists(audio_path) or os.path.getmtime(audio_path) <= scene["last_change"]:
                print(f"DL {part['text']}")
                faud = open(audio_path, "wb")
                faud.write(util.requests.get_tts_audio(part["text"], part["voice"]))
                faud.close()
            audio_length = util.io.get_audio_length(audio_path)
            wait_length += audio_length["m"]*60 + audio_length["s"] + audio_length["ms"]

            part_audio = AudioFileClip(audio_path). \
                set_start(t). \
                volumex(1.8)
            audios.append(part_audio)
            subtitles.append(Subtitle(part["text"], t, t+part_audio.duration))

        crop = part["crop"]
        x = int(new_w*crop["x"]/100)
        y = int(new_h*crop["y"]/100)
        w = int(new_w*crop["w"]/100)
        h = int(new_h*crop["h"]/100)
        part_image = img_raw.crop(x1=x, y1=y, width=w, height=h)
        if is_last:
            part_image = CompositeVideoClip([part_image])
        part_image = part_image. \
            set_position((
                (VIDEO_SIZE[0] - new_w) / 2 + x,
                (VIDEO_SIZE[1] - new_h) / 2 + y
            )). \
            set_start(t)

        clips.append(part_image)
        t = wait_length

    if is_last:
        clips = [c.set_end(t+VIDEO_FADE_TIME).fadeout(VIDEO_FADE_TIME) for c in clips]
        t += VIDEO_FADE_TIME
    else:
        clips = [c.set_end(t) for c in clips]
    clips += audios
    return [clips, subtitles, t]
