from random import randint
import re
import backend
from mutagen.mp3 import MP3, HeaderNotFoundError
from moviepy.video.io.VideoFileClip import VideoFileClip
from PIL import Image
import os


def randstr(length):
    ret = ""
    pool = "qwertyuioplkjhgfdsazxcvbnmQWERTYUIOPLKJHGFDSAZXCVBNM1234567890"
    for _ in range(length):
        ret += pool[randint(0, len(pool)-1)]
    return ret


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


# https://stackoverflow.com/questions/33404752/removing-emojis-from-a-string-in-python
def de_emojify(text):
    regrex_pattern = re.compile(pattern="["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                           "]+", flags=re.UNICODE)
    return regrex_pattern.sub(r'', text)


def replace_with_group(match):
    return match.group(1)


def repl_markdown(mark):
    def ret(match):
        if mark == "bi":
            return f"<b><i>{match.group(1)}</i></b>"
        if mark == "b":
            return f"<b>{match.group(1)}</b>"
        if mark == "i":
            return f"<i>{match.group(1)}</i>"
        return match.group(1)
    return ret


__POLISH_COMMENTS_REPL = [
    ("\\.\\s+\"", ".\""), ("!\\s+\"", ".\""), ("\\?\\s+\"", ".\""),
    ("\\[(.+?)\\]\\(.+?\\)", replace_with_group), ("\\. \\. \\.", "..."),
    (r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))",
     "[some URL]"),
    ("\\*\\*\\*(.*?)\\*\\*\\*", repl_markdown("bi")), ("___(.*?)___", repl_markdown("bi")),
    ("\\*\\*(.*?)\\*\\*", repl_markdown("b")), ("__(.*?)__", repl_markdown("b")),
    ("\\*(.*?)\\*", repl_markdown("i")), ("_(.*?)_", repl_markdown("i")), ("\r", "\n"),
]


def polish_comment(comment):
    for pre, after in __POLISH_COMMENTS_REPL:
        comment = re.sub(pre, after, comment)
    return comment


def polish_comments(forest):
    for pre, after in __POLISH_COMMENTS_REPL:
        forest["body"] = re.sub(pre, after, forest["body"])
    for i in range(len(forest["replies"])):
        forest["replies"][i] = polish_comments(forest["replies"][i])
    return forest


def get_script_comment(forest):
    ret = get_script(forest["body"])
    for rep in forest["replies"]:
        ret += get_script_comment(rep)
    return ret


def get_script(text):
    replacements = [
        ("ftw", "for the win"), ("mfw", "my face when"), ("tfw", "that feel when"),
        ("qt", "cutie"), ("3\\.14", "pi"), ("<i>(.*?)<\\/i>", replace_with_group),
        ("<b>(.*?)<\\/b>", replace_with_group), (">", ""),
    ]
    text = de_emojify(text)
    for pre, after in replacements:
        text = re.sub(pre, after, text, flags=re.IGNORECASE)
    text = re.split("\n{2,}", text)
    text = [t.replace("\n", "") for t in text]
    split_at = [". ", "? ", "! "]
    for c in split_at:
        length = len(text)
        for i_neg in range(length):
            i = length - 1 - i_neg
            text[i] = text[i].split(c)
            for j in range(len(text[i])):
                if j != len(text[i]) - 1:
                    text[i][j] += c
            text = text[:i] + text[i] + text[i + 1:]

    text_tmp = []
    for t in text:
        if len(t.strip()) > 0:
            text_tmp.append(t.replace("\n", ""))
    return text_tmp


def parse_script(file):
    ret = []
    temp_parts = []
    chunk_size = 4
    skip_next_line = False
    for ln in file:
        if skip_next_line:
            skip_next_line = False
            continue

        temp_parts.append(ln)
        if len(temp_parts) == chunk_size:
            try:
                ret.append(backend.editor.ScenePart.part_to_object("".join(temp_parts)))
            except Exception as ex:
                print("\n"*5)
                print(ex)
                print(ln, file.name)
                raise ex
            temp_parts = []
            skip_next_line = True
    return ret


def get_extension(path):
    regex = r"\.([^\.]*)$"
    return re.findall(regex, path)[0]


def get_audio_length(path):
    if os.path.exists(path):
        try:
            audio = MP3(path)
            length = audio.info.length
            return {"m": int(length/60), "s": int(length % 60), "ms": length % 1, "total": length}
        except HeaderNotFoundError as exc:
            print(f"Audio file {path} is most likely corrupted.")
            raise exc
    return {"m": 0, "s": 0, "ms": 0, "total": 0}


def get_video_length(path):
    if os.path.exists(path):
        vid = VideoFileClip(path)
        length = vid.duration
        vid.close()
        return {"m": int(length/60), "s": int(length % 60), "ms": length % 1, "total": length}
    return {"m": 0, "s": 0, "ms": 0, "total": 0}


# https://www.codespeedy.com/find-the-duration-of-gif-image-in-python
def get_gif_length(path):
    if os.path.exists(path):
        img_obj = Image.open(path)
        img_obj.seek(0)  # move to the start of the gif, frame 0
        tot_duration = 0
        # run a while loop to loop through the frames
        while True:
            try:
                frame_duration = img_obj.info['duration']  # returns current frame duration in milli sec.
                tot_duration += frame_duration
                # now move to the next frame of the gif
                img_obj.seek(img_obj.tell() + 1)  # image.tell() = current frame
            except EOFError:
                length = tot_duration / 1000
                return {"m": int(length/60), "s": int(length % 60), "ms": length % 1, "total": length}

