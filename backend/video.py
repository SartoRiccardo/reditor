from __future__ import annotations

import shutil
import traceback
from typing import TYPE_CHECKING
import imageio
if TYPE_CHECKING:
    import classes.video
import classes.export
import gizeh
import gc
import classes
try:
    from moviepy.video.VideoClip import ImageClip, TextClip
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
import backend.log
import PIL
import os


WHITE = (255, 255, 255)
SIZES = {
    "720": (1280, 720),
    "1080": (1920, 1080),
    "720-v": (720, 1280),
    "1080-v": (1080, 1920),
}
SOUNDTRACK_FADE_TIME = 1
VIDEO_FADE_TIME = 1
FPS = 25
BR = "\n"
REACTIONS_PATH = os.path.join("assets", "reactions")

CAPTION_TEXT_COLOR = "gray13"  # (33, 33, 33)
CAPTION_BG_COLOR = (236, 239, 241)
CAPTION_MARGIN_Y = 10
CAPTION_TEXT_SIZE = 42


def export_video_deco(export_func):
    """
    Encloses everything in a try-except function without messing up the code.
    """
    def inner(document, *args, gui_callback=None, **kwargs):
        logger = classes.export.GuiLogger(gui_callback)
        logger.log({"status": "download-audio"})
        try:
            backend.log.export_start(document.id)
            export_func(document, *args, logger=logger, **kwargs)
            backend.log.export_end(document.id)
        except Exception as exc:
            print(traceback.format_exc())
            backend.log.export_err(document.id, str(exc))
            logger.log({"error": True, "error_msg": str(exc)})
            raise exc
    return inner


@export_video_deco
def export_video(
        document: classes.video.Document,
        out_dir: str,
        video_name: str = "video.mp4",
        logger=None,
        size="720"):
    """
    Pieces together the video with all the info found in the document's directory.
    :param document: The document to export.
    :param out_dir: A path pointing to a new directory.
    :param video_name: The name of the videofile.
    :param logger: An objects that forwards status updates to the GUI.
    :param size: The resolution of the video.
    """
    video_size = SIZES[size]
    document.load()
    cache_dir = document.get_cache_dir()

    chunks = 1
    for s in document.script:
        if isinstance(s, classes.video.Transition):
            chunks += 1
        elif isinstance(s, classes.video.Scene):
            download_audios_for(s, document.get_cache_dir())
    logger.set_chunks(chunks)

    chunk_logger = classes.export.CustomProgressBar(gui_callback=logger.log)

    transition = VideoFileClip(backend.editor.DATA_PATH + "/assets/transition.mp4")

    if os.path.exists(backend.editor.DATA_PATH + "/assets/background.mp4"):
        background = VideoFileClip(backend.editor.DATA_PATH + "/assets/background.mp4"). \
            set_position(("center", "center")). \
            loop()
    else:
        background = ImageClip(backend.editor.DATA_PATH + "/assets/background.png"). \
            set_position(("center", "center"))
    if background.w/background.h <= video_size[0]/video_size[1]:
        background = background.resize(width=video_size[0])
    else:
        background = background.resize(height=video_size[1])

    clips = []
    audios = []
    t = 0
    if document.has_intro:
        intro = VideoFileClip(backend.editor.DATA_PATH + "/assets/intro.mp4")
        clips.append(intro)
        audios.append(intro.audio)
        t += intro.duration
        clips.append(background.set_start(t).fadein(VIDEO_FADE_TIME))
        background_idx = 1
        t += VIDEO_FADE_TIME
    else:
        clips.append(background.set_start(t))
        background_idx = 0
    subtitles = []
    part_soundtrack = None
    temp_video_paths = []
    temp_video_durations = []
    has_transitioned_once = False

    for i in range(len(document.script)):
        s = document.script[i]
        if isinstance(s, classes.video.Soundtrack):
            part_soundtrack = AudioFileClip(s.path). \
                set_start(t). \
                fx(audio_normalize). \
                volumex(0.1)

        elif isinstance(s, classes.video.Transition):
            # Splits the file at every transition to avoid memory issues
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
            video = CompositeVideoClip(clips, size=video_size). \
                on_color(color=WHITE, col_opacity=1). \
                set_audio(audio_clip). \
                set_duration(t)

            chunk_logger.set_total_frames(FPS * t)
            temp_video_path = cache_dir + f"/tmp-{len(temp_video_paths)}.mp4"
            temp_audio_path = cache_dir + f"/tmp-{len(temp_video_paths)}-aud.mp4"
            video.write_videofile(temp_video_path, fps=FPS, audio_codec="aac", logger=chunk_logger,
                                  temp_audiofile=temp_audio_path, codec="libx264")
            temp_video_paths.append(temp_video_path)

            temp_video_durations.append(t)
            t = 0
            chunk_logger = classes.export.CustomProgressBar(gui_callback=logger.log)
            for c in clips:
                c.close()
            clips = [background]
            background_idx = 0
            for a in audios:
                a.close()
            audios = []
            audio_clip.close()
            video.close()

        elif isinstance(s, classes.video.Scene):
            scenes_left = 0
            for j in range(i+1, len(document.script)):
                if isinstance(document.script[j], classes.video.Scene):
                    scenes_left += 1

            scene_clips, part_subtitles, t = get_scene_clips(
                t, s, fade_out=(scenes_left == 0 and document.has_outro),
                complete_video_t=sum(temp_video_durations),
                video_size=video_size
            )
            subtitles += part_subtitles
            for c in scene_clips:
                if isinstance(c, AudioFileClip):
                    audios.append(c)
                else:
                    clips.append(c)

        gc.collect()

    clips[background_idx] = clips[background_idx]. \
        set_end(t)
    if document.has_outro:
        clips[background_idx] = clips[background_idx].fadeout(VIDEO_FADE_TIME)

    if part_soundtrack:
        part_start = part_soundtrack.start
        part_end = t - SOUNDTRACK_FADE_TIME
        if part_end > part_start + part_soundtrack.duration:
            part_end = part_start + part_soundtrack.duration
        part_soundtrack = part_soundtrack. \
            set_end(part_end). \
            audio_fadeout(SOUNDTRACK_FADE_TIME)
        audios.append(part_soundtrack)

    if document.has_outro:
        outro = VideoFileClip(backend.editor.DATA_PATH + "/assets/outro.mp4")
        clips.append(outro.set_start(t))
        audios.append(outro.audio.set_start(t))
        t += outro.duration
    temp_video_durations.append(t)

    audio_clip = CompositeAudioClip(audios). \
        set_duration(t)
    video = CompositeVideoClip(clips, size=video_size). \
        on_color(color=WHITE, col_opacity=1). \
        set_audio(audio_clip). \
        set_duration(t)
    chunk_logger.set_total_frames(FPS * t)
    temp_video_path = cache_dir + f"/tmp-{len(temp_video_paths)}.mp4"
    temp_audio_path = cache_dir + f"/tmp-{len(temp_video_paths)}-aud.mp4"
    video.write_videofile(temp_video_path, fps=FPS, audio_codec="aac", logger=chunk_logger,
                          temp_audiofile=temp_audio_path, codec="libx264")
    temp_video_paths.append(temp_video_path)

    for c in clips:
        c.close()
    for a in audios:
        a.close()
    audio_clip.close()
    video.close()
    background.close()

    fsub = open(out_dir+"/subtitles.srt", "w")
    for i in range(len(subtitles)):
        s = subtitles[i]
        fsub.write(f"{i+1}\n")
        fsub.write(str(s))
        if i != len(subtitles)-1:
            fsub.write("\n")
    fsub.close()

    if len(temp_video_paths) > 1:
        chunk_logger = classes.export.CustomProgressBar(gui_callback=logger.log, fps=FPS)
        composite_videos(temp_video_paths, f"{out_dir}/{video_name}", chunk_logger)
        for tmp_vid in temp_video_paths:
            os.remove(tmp_vid)
    elif len(temp_video_paths) == 1:
        shutil.move(temp_video_paths[0], f"{out_dir}/{video_name}")


def get_scene_clips(
        t: int,
        scene,
        fade_out=False,
        complete_video_t=None,
        video_size=SIZES["720"]
    ):
    """
    Creates audio and image clips with the given scene
    :param t: The time the scene will start at.
    :param scene: The scene to convert to clips.
    :param fade_out: If true, fade out to black at the end.
    :param complete_video_t: The overall time the clip starts at. Useful if the video
                                  is being split for memory issues.
    :param video_size: The resolution of the video.
    :return: [Clip[], Subtitle[], int]: A list of clips, subtitle and the time at which the scene ends.
    """
    cache_dir = scene.document.get_cache_dir()
    if complete_video_t is None:
        complete_video_t = t

    has_caption = False
    for part in scene.script:
        if "written" in part.fields:
            has_caption = True
            break

    clips = []
    captions = []
    reactions = []
    audios = []
    subtitles = []

    media_path = scene.get_media_path()
    if media_path[-4:] in [".png", "jpeg", ".jpg", ".gif"]:
        media_w, media_h = PIL.Image.open(media_path).size
        if media_w/media_h <= video_size[0]/video_size[1]:
            new_h = video_size[1]*0.9
            media_raw = ImageClip(media_path). \
                resize(height=new_h)
        else:
            new_w = video_size[0]*0.9
            media_raw = ImageClip(media_path). \
                resize(width=new_w)
    elif media_path[-4:] in [".mp4"]:
        media_raw = VideoFileClip(media_path)
        media_w = media_raw.w
        media_h = media_raw.h
        if media_w/media_h <= video_size[0]/video_size[1]:
            new_h = video_size[1]*0.9
            media_raw = media_raw.resize(height=new_h)
        else:
            new_w = video_size[0]*0.9
            media_raw = media_raw.resize(width=new_w)
    else:
        return [[], [], 0]

    for i in range(len(scene.script)):
        part = scene.script[i]
        wait_length = t + part.wait
        if part.text:
            audio_path = cache_dir+f"/{scene.id:05d}-{i:05d}.mp3"
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
            subtitles.append(classes.export.Subtitle(part.text, complete_video_t+t, complete_video_t+t+part_audio.duration))
            wait_length += part_audio.duration

        if not part.is_crop_empty():
            media_clip = get_media_clips(t, media_raw, part.crop, fade_out=fade_out, has_caption=has_caption,
                                         video_size=video_size)
            clips.append(media_clip)

            if isinstance(media_raw, VideoFileClip):
                wait_length += media_raw.duration

        if "reaction" in part.fields:
            reactions.append(get_reaction_clip(t, part.fields['reaction'], video_size=video_size))

        if "written" in part.fields:
            captions += get_caption_clips(t, part.fields["written"], video_size=video_size)

        t = wait_length

    clips += captions + reactions
    if fade_out:
        clips = [c.set_end(t+VIDEO_FADE_TIME).fadeout(VIDEO_FADE_TIME) for c in clips]
        t += VIDEO_FADE_TIME
    else:
        clips = [c.set_end(t) for c in clips]
    clips += audios
    return [clips, subtitles, t]


def composite_videos(paths, out_file, logger="bar"):
    clips = []

    t = 0
    for i in range(len(paths)):
        p = paths[i]
        vc = VideoFileClip(p).set_start(t)
        clips.append(vc)
        t += vc.duration

    if isinstance(logger, classes.export.CustomProgressBar):
        logger.set_total_frames(FPS * t)
    video = CompositeVideoClip(clips). \
        set_duration(t)
    temp_audio_path = out_file[:-4]+"-aud.mp4"
    video.write_videofile(out_file, fps=FPS, audio_codec="aac", logger=logger,
                          temp_audiofile=temp_audio_path, codec="libx264")
    video.close()
    for clip in clips:
        clip.close()
    gc.collect()


def download_audios_for(scene: classes.video.Scene, download_dir: str):
    """
    Downloads all audios for a specific scene.
    :param scene: The scene to download the audios for
    :param download_dir: The directory that will contained the genrated audios
    :return:
    """
    for i in range(len(scene.script)):
        part = scene.script[i]
        if part.text:
            audio_path = f"{download_dir}/{scene.id:05d}-{i:05d}.mp3"
            if not os.path.exists(audio_path) or os.path.getmtime(audio_path) <= scene.get_last_changed():
                faud = open(audio_path, "wb")
                audio = None
                tries = 3
                while tries:
                    try:
                        audio = backend.requests.get_tts_audio(part.text, part.voice)
                        tries = 0
                    except:
                        tries -= 1
                if not audio:
                    raise Exception(f"Could not download audio {scene.id:05d}-{i:05d}")
                faud.write(audio)
                faud.close()


def get_media_clips(t, media, crop_data, fade_out=False, has_caption=False, video_size=SIZES["720"]):
    x = int(media.w*crop_data["x"]/100)
    y = int(media.h*crop_data["y"]/100)
    w = int(media.w*crop_data["w"]/100)
    h = int(media.h*crop_data["h"]/100)

    part_media = media.crop(x1=x, y1=y, width=w, height=h)
    if fade_out:
        part_media = CompositeVideoClip([part_media])

    align_y = (video_size[1] - media.h) / 2 + y
    if has_caption:
        align_y = 0

    part_media = part_media. \
        set_position((
            (video_size[0] - media.w) / 2 + x,
            align_y
        )). \
        set_start(t)
    return part_media


def get_caption_clips(t, text, video_size=SIZES["720"]):
    part_text = TextClip(text, font="Roboto", fontsize=CAPTION_TEXT_SIZE,
                         color=CAPTION_TEXT_COLOR, align="center", method="caption",
                         size=(int(video_size[0]*0.9), None))
    part_text = part_text \
        .set_position((
            (video_size[0] - part_text.w) / 2,
            video_size[1] - part_text.h - CAPTION_MARGIN_Y
        )) \
        .set_start(t)
    backdrop_height = part_text.h + CAPTION_MARGIN_Y*2
    part_background = create_rectangle(video_size[0], backdrop_height, color=CAPTION_BG_COLOR) \
        .set_position((0, video_size[1] - backdrop_height)) \
        .set_start(t)
    return [part_background, part_text]


def get_reaction_clip(t, reaction, video_size=SIZES["720"]):
    reaction_path = os.path.join(REACTIONS_PATH, f"{reaction}.png")
    part_react = ImageClip(reaction_path).resize(height=int(0.5*video_size[1]))
    if part_react.w > video_size[0]:
        part_react = part_react.resize(width=video_size[0])
    part_react = part_react \
        .set_position((
            video_size[0] - part_react.w,
            video_size[1] - part_react.h
        )) \
        .set_start(t)
    return part_react


def create_rectangle(width, height, color=(33, 33, 33)):
    color = tuple([c/255 for c in color])

    def make_frame(_t):
        surface = gizeh.Surface(width, height, bg_color=color)
        return surface.get_npimage()

    return VideoClip(make_frame)
