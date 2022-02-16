from PIL import Image, ImageFont, ImageDraw
import backend
import os
import re
import json
import shutil
from html2image import Html2Image
import pytesseract
import random
from credentials import Tesseract
import traceback
if len(Tesseract.path) > 0:
    pytesseract.pytesseract.tesseract_cmd = Tesseract.path


FONT = None
WATERMARK_PATH = backend.paths.DATA_PATH + "/assets/thumbnail/watermark.png"
FONT_COLOR = (255, 255, 255)
STROKE_WIDTH = 8
STROKE_COLOR = (26, 35, 126)
THUMB_SIZE = (1280, 720)

BLACK = (0, 0, 0, 255)
hti = None
html_template_post = None
css_post = None
html_template_comment = None
css_comment = None
video_voices_config = None


def init():
    global FONT
    FONT = ImageFont.truetype(backend.paths.DATA_PATH + "/assets/thumbnail/thumbnail-font-bold.ttf", 100)


def make_thumbnail(text, image_path, save_path, max_chars_per_line=20):
    base = Image.new("RGBA", THUMB_SIZE, color=BLACK)
    base_canvas = ImageDraw.Draw(base)

    words = text.split(" ")
    text_multi = ""
    for w in words:
        current_line = text_multi.split("\n")[-1]
        if len(current_line)+len(w)+1 > max_chars_per_line:
            text_multi += "\n"
        text_multi += " " + w
    text = text_multi

    watermark = Image.open(WATERMARK_PATH)
    wm_w, wm_h = watermark.size

    background = Image.open(image_path)
    width, height = background.size
    if width/height > 16/9:
        bg_h = THUMB_SIZE[1]
        bg_w = int(bg_h*width/height)
        background = background.resize((bg_w, bg_h))
    else:
        bg_w = THUMB_SIZE[0]
        bg_h = int(bg_w*height/width)
        background = background.resize((bg_w, bg_h))
    background.putalpha(int(255*0.7))

    bg_x = int((THUMB_SIZE[0]-bg_w)/2)
    bg_y = int((THUMB_SIZE[1]-bg_h)/2)
    base.alpha_composite(background, (bg_x, bg_y))

    base_canvas.multiline_text((int(THUMB_SIZE[0]/2), int(THUMB_SIZE[1]/2)),
                text.upper(), fill=FONT_COLOR, font=FONT, anchor="mm", align="center",
                stroke_fill=STROKE_COLOR, stroke_width=STROKE_WIDTH)
    base.paste(watermark, (0, THUMB_SIZE[1]-wm_h), watermark)
    # base.show()
    base.save(save_path)


def init_hti(tmp_dir, dl_dir):
    global hti
    if not hti:
        hti = Html2Image(temp_path=dl_dir,
                         custom_flags=["--log-level=OFF", "--disable-gpu", "--default-background-color=0"])
        if os.path.exists(dl_dir):
            shutil.rmtree(dl_dir)
        if not os.path.exists(tmp_dir):
            os.mkdir(tmp_dir)
        os.mkdir(dl_dir)

        hti.output_path = dl_dir


def init_voices_config():
    global video_voices_config
    fin = open("video-voices.json")
    video_voices_config = json.loads(fin.read())
    fin.close()


def get_voice_for_scene():
    if video_voices_config is None:
        init_voices_config()

    chances = []
    for voice in video_voices_config["voices"]:
        chances += [voice["name"]] * voice["weight"]
    return random.choice(chances)


def reddit_comment_to_image(forest):
    global hti, html_template_comment, css_comment
    init_voices_config()
    tmp_dir = backend.paths.DATA_PATH + "/tmp"
    dl_dir = tmp_dir + "/download-selfposts"
    init_hti(tmp_dir, dl_dir)

    if not html_template_comment:
        fin = open("./assets/reddit-comment-template.html")
        html_template_comment = fin.read()
        fin.close()
    if not css_comment:
        fin = open("./assets/reddit-comment.css")
        css_comment = fin.read()
        fin.close()

    forest = backend.utils.polish_comments(forest)
    filename = backend.utils.randstr(10) + ".png"
    html = html_template_comment.replace("{comment-json-inject}", json.dumps(forest))
    hti.screenshot(html_str=html, css_str=css_comment, save_as=filename)

    full_path = dl_dir + "/" + filename
    image = Image.open(full_path).convert("RGBA")
    width, height = image.size
    y = 1
    for y in range(1, height):
        if image.getpixel((int(width/2), y))[3] != 0:
            break
    scene = image.crop((0, 0, 498, height))
    image = image.crop((498, y, 1818, height-y))
    image.save(full_path)

    text = pytesseract.image_to_string(scene, lang="eng", config="--psm 11")
    if "FALSE" in text:
        return None
    raw_scene = [row.split("-") for row in re.split("\n{2,}", text)]

    script = backend.utils.get_script_comment(forest)
    build_script(full_path, raw_scene, script)

    return full_path


def reddit_to_image(submission, subreddit_name):
    global hti, html_template_post, css_post
    init_voices_config()
    tmp_dir = backend.paths.DATA_PATH + "/tmp"
    dl_dir = tmp_dir + "/download-selfposts"
    init_hti(tmp_dir, dl_dir)

    if not html_template_post:
        fin = open("./assets/reddit-post-template.html")
        html_template_post = fin.read()
        fin.close()
    if not css_post:
        fin = open("./assets/reddit-post.css")
        css_post = fin.read()
        fin.close()

    replacements = [
        ("\\.\\s+\"", ".\""), ("!\\s+\"", ".\""), ("\\?\\s+\"", ".\""),
        ("https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)",
         "this link")
    ]

    filename = backend.utils.randstr(10) + ".png"
    body = submission.selftext
    for pre, after in replacements:
        body = re.sub(pre, after, body)
    body = body.split("\n\n")
    for i in range(len(body)):
        body[i] = "<p>" + body[i].replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>") + "</p>"
    body = "\n".join(body)

    score = submission.score
    if score >= 1000:
        score = f"{int(score/1000)}.{int(score/100)%10}k"
    else:
        score = str(score)

    html = html_template_post.replace("{upvotes}", score) \
            .replace("{author}", submission.author.name) \
            .replace("{sub-name}", subreddit_name) \
            .replace("{post-title}", submission.title) \
            .replace("{post-text}", body) \
            .replace("{upvote-ratio}", str(int(submission.upvote_ratio*100))) \
            .replace("{num-comments}", str(submission.num_comments)) \
            .replace("{sub-icon-url}", submission.subreddit.icon_img)

    hti.screenshot(html_str=html, css_str=css_post, save_as=filename)

    full_path = dl_dir + "/" + filename
    image = Image.open(full_path).convert("RGBA")
    width, height = image.size
    for y in range(1, height):
        if image.getpixel((int(width/2), y))[3] != 0:
            break
    scene = image.crop((0, 0, 512, height))
    image = image.crop((512, y, 1792, height-y))
    image.save(full_path)

    text = pytesseract.image_to_string(scene, lang="eng", config="--psm 11")
    if "FALSE" in text:
        return None
    raw_scene = [row.split("-") for row in re.split("\n{2,}", text)]

    script = backend.utils.get_script(submission.selftext)
    script.insert(0, submission.title)
    build_script(full_path, raw_scene, script)

    return full_path


def build_script(full_path, raw_scene, script):
    script_i = 0
    try:
        raw_script = []
        for s in raw_scene:
            if script_i >= len(script):
                break

            s = [float(num) for num in s]
            x, y, w, h, wait = s
            scene_obj = {
                "text": "" if wait == 0 else script[script_i],
                "voice": get_voice_for_scene(),
                "crop": {"x": x, "y": y, "w": w, "h": h},
                "wait": wait,
            }
            if wait > 0:
                script_i += 1
            raw_script.append(backend.editor.ScenePart.object_to_text(scene_obj))
        raw_script = "\n\n".join(raw_script)

        fout = open(full_path+".txt", "w")
        fout.write(raw_script)
        fout.close()
    except IndexError:
        print(script_i)
        print(script)
        print(raw_scene)
        exit(0)
    except:
        print(traceback.format_exc())


init()
