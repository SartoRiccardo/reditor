from __future__ import annotations
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
    720: (1280, 720),
    1080: (1920, 1080),
}
VIDEO_SIZE = SIZES[720]
SOUNDTRACK_FADE_TIME = 1
VIDEO_FADE_TIME = 1
FPS = 25
BR = "\n"
REACTIONS_PATH = os.path.join("assets", "reactions")

CAPTION_TEXT_COLOR = "gray13"  # (33, 33, 33)
CAPTION_BG_COLOR = (236, 239, 241)
CAPTION_MARGIN_Y = 10
CAPTION_TEXT_SIZE = 42


def export_video(document: classes.video.Document, out_dir: str, gui_callback=None, video_name="video.mp4"):
    """
    A wrapper for an easier time trying and excepting.
    :param document: The document to export.
    :param out_dir: A path pointing to a new directory.
    :param gui_callback: A function called every time the state changes.
    :param video_name: The name of the file.
    """
    logger = classes.export.GuiLogger(gui_callback)
    logger.log({"status": "download-audio"})
    try:
        backend.log.export_start(document.id)
        export_video_wrapped(document, out_dir, video_name, logger=logger)
        backend.log.export_end(document.id)
    except Exception as exc:
        backend.log.export_err(document.id, str(exc))
        logger.log({"error": True, "error_msg": str(exc)})
        raise exc


def export_video_wrapped(document: classes.video.Document, out_dir: str, video_name: str, logger=None):
    """
    Pieces together the video with all the info found in the document's directory.
    :param document: The document to export.
    :param out_dir: A path pointing to a new directory.
    :param video_name: The name of the videofile.
    :param logger: An objects that forwards status updates to the GUI.
    """
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

    for i in range(len(document.script)):
        s = document.script[i]
        if isinstance(s, classes.video.Soundtrack):
            part_soundtrack = AudioFileClip(s.path). \
                set_start(t). \
                fx(audio_normalize). \
                volumex(0.1)

        elif isinstance(s, classes.video.Transition):
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
                                  temp_audiofile=temp_audio_path, codec="libx264")
            temp_video_paths.append(temp_video_path)

            temp_video_durations.append(t)
            t = 0
            chunk_logger = classes.export.CustomProgressBar(gui_callback=logger.log)
            for c in clips:
                c.close()
            clips = [background]
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
                t, s, is_last=scenes_left == 0, complete_video_t=sum(temp_video_durations)
            )
            subtitles += part_subtitles
            for c in scene_clips:
                if isinstance(c, AudioFileClip):
                    audios.append(c)
                else:
                    clips.append(c)

        gc.collect()

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
                          temp_audiofile=temp_audio_path, codec="libx264")
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

    chunk_logger = classes.export.CustomProgressBar(gui_callback=logger.log, fps=FPS)
    composite_videos(temp_video_paths, f"{out_dir}/{video_name}", chunk_logger)
    for tmp_vid in temp_video_paths:
        os.remove(tmp_vid)


def get_scene_clips(t: int, scene, is_last=False, complete_video_t=None):
    """
    Creates audio and image clips with the given scene
    :param t: The time the scene will start at.
    :param scene: The scene to convert to clips.
    :param is_last: Whether it's the last scene. If it is, it fades out to black.
    :param complete_video_t: The overall time the clip starts at. Useful if the video
                                  is being split for memory issues.
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
        if media_w/media_h <= 16/9:
            new_h = VIDEO_SIZE[1]*0.9
            media_raw = ImageClip(media_path). \
                resize(height=new_h)
        else:
            new_w = VIDEO_SIZE[0]*0.9
            media_raw = ImageClip(media_path). \
                resize(width=new_w)
    elif media_path[-4:] in [".mp4"]:
        media_raw = VideoFileClip(media_path)
        media_w = media_raw.w
        media_h = media_raw.h
        if media_w/media_h <= 16/9:
            new_h = VIDEO_SIZE[1]*0.9
            media_raw = media_raw.resize(height=new_h)
        else:
            new_w = VIDEO_SIZE[0]*0.9
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
            media_clip = get_media_clips(t, media_raw, part.crop, is_last=is_last, has_caption=has_caption)
            clips.append(media_clip)

            if isinstance(media_raw, VideoFileClip):
                wait_length += media_raw.duration

        if "reaction" in part.fields:
            reactions.append(get_reaction_clip(t, part.fields['reaction']))

        if "written" in part.fields:
            captions += get_caption_clips(t, part.fields["written"])

        t = wait_length

    clips += captions + reactions
    if is_last:
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
                    raise Exception(f"Could not download audio {scene['number']:05d}-{i:05d}")
                faud.write(audio)
                faud.close()


def get_media_clips(t, media, crop_data, is_last=False, has_caption=False):
    x = int(media.w*crop_data["x"]/100)
    y = int(media.h*crop_data["y"]/100)
    w = int(media.w*crop_data["w"]/100)
    h = int(media.h*crop_data["h"]/100)

    part_media = media.crop(x1=x, y1=y, width=w, height=h)
    if is_last:
        part_media = CompositeVideoClip([part_media])

    align_y = (VIDEO_SIZE[1] - media.h) / 2 + y
    if has_caption:
        align_y = 0

    part_media = part_media. \
        set_position((
            (VIDEO_SIZE[0] - media.w) / 2 + x,
            align_y
        )). \
        set_start(t)
    return part_media


def get_caption_clips(t, text):
    part_text = TextClip(text, font="Roboto", fontsize=CAPTION_TEXT_SIZE,
                         color=CAPTION_TEXT_COLOR, align="center", method="caption",
                         size=(int(VIDEO_SIZE[0]*0.9), None))
    part_text = part_text \
        .set_position((
            (VIDEO_SIZE[0] - part_text.w) / 2,
            VIDEO_SIZE[1] - part_text.h - CAPTION_MARGIN_Y
        )) \
        .set_start(t)
    backdrop_height = part_text.h + CAPTION_MARGIN_Y*2
    part_background = create_rectangle(VIDEO_SIZE[0], backdrop_height, color=CAPTION_BG_COLOR) \
        .set_position((0, VIDEO_SIZE[1] - backdrop_height)) \
        .set_start(t)
    return [part_background, part_text]


def get_reaction_clip(t, reaction):
    reaction_path = os.path.join(REACTIONS_PATH, f"{reaction}.png")
    part_react = ImageClip(reaction_path).resize(height=int(0.5*VIDEO_SIZE[1]))
    part_react = part_react \
        .set_position((
            VIDEO_SIZE[0] - part_react.w,
            VIDEO_SIZE[1] - part_react.h
        )) \
        .set_start(t)
    return part_react


def create_rectangle(width, height, color=(33, 33, 33)):
    color = tuple([c/255 for c in color])

    def make_frame(_t):
        surface = gizeh.Surface(width, height, bg_color=color)
        return surface.get_npimage()

    return VideoClip(make_frame)
