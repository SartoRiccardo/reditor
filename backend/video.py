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
import backend.editor
import backend.requests
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
FPS = 25
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
            self.gui_callback({"started": True, "percentage": 0})
        self.prev_percentage = 100

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
                vidlen = self.total_frames / FPS
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


class GuiLogger:
    def __init__(self, callback, chunks=0):
        self.callback = callback
        self.chunks = chunks+1
        self.current_chunk = 0

    def set_chunks(self, chunks):
        self.chunks = chunks+1

    def log(self, evt):
        # to_send = {}
        # if "started" in evt and evt["started"]:
        #     self.current_chunk += 1
        #     if self.current_chunk == self.chunks:
        #         to_send["message"] = f"Exporting final..."
        #     else:
        #         to_send["message"] = f"Exporting chunk... ({self.current_chunk}/{self.chunks})"
        #     to_send["subtitle"] = ""
        #
        # if "status" in evt:
        #     if evt["status"] == "audio":
        #         to_send["subtitle"] = "Creating audio..."
        #     elif evt["status"] == "video":
        #         to_send["subtitle"] = "Creating video..."
        #     elif evt["status"] == "download-audio":
        #         to_send["subtitle"] = "Generating TTS audios..."
        #
        # if "percentage" in evt:
        #     to_send["percentage"] = evt["percentage"]
        # if "finished" in evt and self.current_chunk == self.chunks:
        #     to_send["finished"] = evt["finished"]
        #
        # if "error" in evt:
        #     to_send["subtitle"] = "Something went wrong: " + evt["error_msg"]
        #     to_send["error"] = evt["error_msg"]

        if self.callback:
            self.callback(evt)
            # self.callback(to_send)


def export_video(file_id, out_dir, gui_callback=None, video_name="video.mp4"):
    """
    A wrapper for an easier time trying and excepting.
    :param file_id: int: The numerical ID of the file.
    :param out_dir: str: A path pointing to a new directory.
    :param gui_callback: function: A function called every time the state changes.
    :param video_name: str: The name of the file.
    """
    logger = GuiLogger(gui_callback)
    logger.log({"status": "download-audio"})
    try:
        backend.log.export_start(file_id)
        export_video_wrapped(file_id, out_dir, video_name, logger=logger)
        backend.log.export_end(file_id)
    except Exception as exc:
        backend.log.export_err(file_id, str(exc))
        print(logger)
        logger.log({"error": True, "error_msg": str(exc)})
        raise exc


def export_video_wrapped(file_id, out_dir, video_name, logger=None):
    """
    Pieces together the video with all the info found in the document's directory.
    :param file_id: int: The numerical ID of the file.
    :param out_dir: str: A path pointing to a new directory.
    :param video_name: str: The name of the videofile.
    :param logger: GuiLogger: An objects that forwards status updates to the GUI.
    """
    document = backend.editor.get_file_info(file_id)
    cache_dir = backend.editor.get_cache_dir(file_id)

    chunks = 1
    for s in document["script"]:
        if s["type"] == "transition":
            chunks += 1
        elif s["type"] == "scene":
            download_audios_for(s, cache_dir, document=file_id)
    logger.set_chunks(chunks)

    chunk_logger = CustomProgressBar(gui_callback=logger.log)

    transition = VideoFileClip(backend.editor.DATA_PATH + "/assets/transition.mp4")
    intro = VideoFileClip(backend.editor.DATA_PATH + "/assets/intro.mp4")
    outro = VideoFileClip(backend.editor.DATA_PATH + "/assets/outro.mp4")

    if os.path.exists(backend.editor.DATA_PATH + "/assets/background.mp4"):
        background = VideoFileClip(backend.editor.DATA_PATH + "/assets/background.mp4"). \
            set_position(("center", "center")). \
            loop()
    else:
        background = ImageClip(backend.editor.DATA_PATH + "/assets/background.png"). \
            set_position(("center", "center"))
    if background.w/background.h <= 16/9:
        background = background.resize(width=VIDEO_SIZE[0])
    else:
        background = background.resize(height=VIDEO_SIZE[1])

    t = intro.duration
    clips = [intro, background.set_start(t).fadein(VIDEO_FADE_TIME)]
    t += VIDEO_FADE_TIME
    audios = [intro.audio]
    subtitles = []
    part_soundtrack = None
    temp_video_paths = []
    temp_video_durations = []
    has_transitioned_once = False

    for i in range(len(document["script"])):
        s = document["script"][i]
        if s["type"] == "soundtrack":
            part_soundtrack = AudioFileClip(s["path"]). \
                set_start(t). \
                fx(audio_normalize). \
                volumex(0.1)

        elif s["type"] == "transition":
            has_transitioned_once = True
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

            clips.append(transition.set_start(t))
            audios.append(transition.audio.set_start(t))
            t += transition.duration

            audio_clip = CompositeAudioClip(audios). \
                set_duration(t)
            video = CompositeVideoClip(clips, size=VIDEO_SIZE). \
                on_color(color=WHITE, col_opacity=1). \
                set_audio(audio_clip). \
                set_duration(t)

            chunk_logger.set_total_frames(FPS * t)
            temp_video_path = cache_dir + f"/tmp-{len(temp_video_paths)}.mp4"
            temp_audio_path = cache_dir + f"/tmp-{len(temp_video_paths)}-aud.mp4"
            video.write_videofile(temp_video_path, fps=FPS, audio_codec="aac", logger=chunk_logger,
                                  temp_audiofile=temp_audio_path)
            temp_video_paths.append(temp_video_path)

            temp_video_durations.append(t)
            t = 0
            chunk_logger = CustomProgressBar(gui_callback=logger.log)
            for c in clips:
                c.close()
            clips = [background]
            for a in audios:
                a.close()
            audios = []
            audio_clip.close()
            video.close()

        elif s["type"] == "scene":
            scenes_left = 0
            for j in range(i+1, len(document["script"])):
                if document["script"][j]["type"] == "scene":
                    scenes_left += 1

            scene = backend.editor.get_scene_info(s["number"], file_id)
            scene_clips, part_subtitles, t = get_scene_clips(
                t, scene, cache_dir, is_last=scenes_left == 0, complete_video_t=sum(temp_video_durations)
            )
            subtitles += part_subtitles
            for c in scene_clips:
                if isinstance(c, ImageClip) or isinstance(c, CompositeVideoClip):
                    clips.append(c)
                elif isinstance(c, AudioFileClip):
                    audios.append(c)

    bg_i = 0 if has_transitioned_once else 1
    clips[bg_i] = clips[bg_i]. \
        set_end(t). \
        fadeout(VIDEO_FADE_TIME)

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
    temp_video_durations.append(t)

    audio_clip = CompositeAudioClip(audios). \
        set_duration(t)
    video = CompositeVideoClip(clips, size=VIDEO_SIZE). \
        on_color(color=WHITE, col_opacity=1). \
        set_audio(audio_clip). \
        set_duration(t)
    chunk_logger.set_total_frames(FPS * t)
    temp_video_path = cache_dir + f"/tmp-{len(temp_video_paths)}.mp4"
    temp_audio_path = cache_dir + f"/tmp-{len(temp_video_paths)}-aud.mp4"
    video.write_videofile(temp_video_path, fps=FPS, audio_codec="aac", logger=chunk_logger,
                          temp_audiofile=temp_audio_path)
    temp_video_paths.append(temp_video_path)

    for c in clips:
        c.close()
    for a in audios:
        a.close()
    audio_clip.close()
    video.close()

    background.close()
    intro.close()
    outro.close()

    fsub = open(out_dir+"/subtitles.srt", "w")
    for i in range(len(subtitles)):
        s = subtitles[i]
        fsub.write(f"{i+1}\n")
        fsub.write(str(s))
        if i != len(subtitles)-1:
            fsub.write("\n")
    fsub.close()

    chunk_logger = CustomProgressBar(gui_callback=logger.log)
    composite_videos(temp_video_paths, f"{out_dir}/{video_name}", chunk_logger)
    for tmp_vid in temp_video_paths:
        os.remove(tmp_vid)


def get_scene_clips(t, scene, cache_dir, is_last=False, complete_video_t=None):
    """
    Creates audio and image clips with the given scene
    :param t: int: The time the scene will start at.
    :param scene: Scene: The scene to convert to clips.
    :param cache_dir: str: A directory in which to put downloaded temporary audio files.
    :param is_last: boolean: Whether it's the last scene. If it is, it fades out to black.
    :param complete_video_t: int: The overall time the clip starts at. Useful if the video
                                  is being split for memory issues.
    :return: [Clip[], Subtitle[], int]: A list of clips, subtitle and the time at which the scene ends.
    """
    if complete_video_t is None:
        complete_video_t = t

    clips = []
    audios = []
    subtitles = []

    img_path = scene["image_path"]
    img_w, img_h = PIL.Image.open(img_path).size
    if img_w/img_h <= 16/9:
        new_h = VIDEO_SIZE[1]*0.9
        new_w = new_h * img_w / img_h
        img_raw = ImageClip(img_path). \
            resize(height=new_h)
    else:
        new_w = VIDEO_SIZE[0]*0.9
        new_h = new_w * img_h / img_w
        img_raw = ImageClip(img_path). \
            resize(width=new_w)

    for i in range(len(scene["script"])):
        part = scene["script"][i]
        wait_length = t + part["wait"]
        if part["text"]:
            audio_path = cache_dir+f"/{scene['number']:05d}-{i:05d}.mp3"
            # if not os.path.exists(audio_path) or os.path.getmtime(audio_path) <= scene["last_change"]:
            #     faud = open(audio_path, "wb")
            #     faud.write(util.requests.get_tts_audio(part["text"], part["voice"]))
            #     faud.close()
            part_audio = AudioFileClip(audio_path). \
                set_start(t). \
                volumex(2.3)
            part_audio = part_audio.set_end(t + part_audio.duration - 0.05)
                # audio_fadeout(0.1)
            audios.append(part_audio)
            subtitles.append(Subtitle(part["text"], complete_video_t+t, complete_video_t+t+part_audio.duration))
            wait_length += part_audio.duration

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


def composite_videos(paths, out_file, logger="bar"):
    clips = []
    print(out_file)

    t = 0
    for i in range(len(paths)):
        p = paths[i]
        vc = VideoFileClip(p).set_start(t)
        clips.append(vc)
        t += vc.duration

    if isinstance(logger, CustomProgressBar):
        logger.set_total_frames(FPS * t)
    video = CompositeVideoClip(clips). \
        set_duration(t)
    temp_audio_path = out_file[:-4]+"-aud.mp4"
    video.write_videofile(out_file, fps=FPS, audio_codec="aac", logger=logger,
                          temp_audiofile=temp_audio_path)


def download_audios_for(s, cache_dir, document=None):
    scene = backend.editor.get_scene_info(s["number"], file=document)
    for i in range(len(scene["script"])):
        part = scene["script"][i]
        if part["text"]:
            audio_path = cache_dir+f"/{scene['number']:05d}-{i:05d}.mp3"
            if not os.path.exists(audio_path) or os.path.getmtime(audio_path) <= scene["last_change"]:
                faud = open(audio_path, "wb")
                audio = None
                tries = 3
                while tries:
                    try:
                        audio = backend.requests.get_tts_audio(part["text"], part["voice"])
                        tries = 0
                    except:
                        tries -= 1
                if not audio:
                    raise Exception(f"Could not download audio {scene['number']:05d}-{i:05d}")
                faud.write(audio)
                faud.close()
