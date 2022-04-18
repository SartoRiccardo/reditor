from credentials import Reddit, Amazon, Twitter
import json
import urllib3
from random import random
import traceback
import os
import re
import hashlib
import hmac
import datetime
import praw
import twitter
import backend.editor
from classes.misc import *


http = urllib3.PoolManager()
VOICES = {
    "male-2": {
        "id": "Joey",
        "engine": "standard"
    },
    "male-1": {
        "id": "Matthew",
        "engine": "standard"
    },
    "female-1": {
        "id": "Kendra",
        "engine": "standard"
    },
    "female-2": {
        "id": "Kimberly",
        "engine": "standard"
    },
    "male-2-neural": {
        "id": "Joey",
        "engine": "neural"
    },
    "male-1-neural": {
        "id": "Matthew",
        "engine": "neural"
    },
}
MAX_RATIO = 3/2
MIN_RATIO = 1/MAX_RATIO

COMMENT_CHANCE = 0.45


def get_reddit_instance():
    reddit = praw.Reddit(
        client_id=Reddit.client_id,
        client_secret=Reddit.client_secret,
        user_agent=Reddit.user_agent,
        check_for_updates="False",
        comment_kind="t1",
        message_kind="t4",
        redditor_kind="t2",
        submission_kind="t3",
        subreddit_kind="t5",
        trophy_kind="t6",
        oauth_url="https://oauth.reddit.com",
        reddit_url="https://www.reddit.com",
        short_url="https://redd.it"
    )
    reddit.read_only = True
    return reddit


def subreddit_image_posts(sub, only_selfposts=False, max_scenes=100000):
    """
    Fetches a subreddit's top submissions.
    :param sub: str: The name of the subreddit.
    :param only_selfposts: boolean: Whether to only get selfposts/comments.
    :param max_scenes: int: Max number of posts to download.
    :return: ImageLink[]: A list of URLs leading to the images.
    """
    reddit = get_reddit_instance()

    try:
        submission_lists = [reddit.subreddit(sub).top("week"), reddit.subreddit(sub).hot()]

        ret = []
        for submissions in submission_lists:
            for s in submissions:
                if len(ret) >= max_scenes:
                    break

                if s.over_18 or s.stickied:
                    continue

                if not only_selfposts and hasattr(s, "post_hint") and s.post_hint == "image":
                    source = s.preview["images"][0]["source"]
                    image_url = s.preview["images"][0]["source"]["url"]
                    if MIN_RATIO <= source["width"]/source["height"] <= MAX_RATIO and \
                            image_url not in ret:
                        ret.append(ImageLink(image_url, True))
                elif s.is_self:
                    image = backend.image.reddit_to_image(s, sub)
                    if image:
                        ret.append(ImageLink(image, False))

        return ret

    except Exception:
        print(traceback.format_exc())
        return []


def post_comments(thread_id):
    """
    Fetches a subreddit's top submissions.
    :param thread_id: str: The ID of the thread.
    :return: ImageLink[]: A list of URLs leading to the images.
    """
    reddit = get_reddit_instance()

    try:
        ret = []
        submission = reddit.submission(thread_id)
        path = backend.image.reddit_to_image(submission, submission.subreddit.id)
        if path:
            ret.append(ImageLink(path, is_url=False))

        comments = get_simplified_comments(submission.comments)
        for cmt in comments:
            path = backend.image.reddit_comment_to_image(cmt)
            if path:
                ret.append(ImageLink(path, is_url=False))
        return ret

    except Exception:
        print(traceback.format_exc())
        return []


def get_simplified_comments(forest, max_comment_roots=35, max_comments_per_tree=5):
    """
    Recursive function that returns a simplified version of a comment.
    :param forest: CommentForest: the forest to simplify.
    :param max_comment_roots: int: The max base comments.
    :param max_comments_per_tree: int: The max comments every tree can have.
                                        Includes branches, not only leaves.
                                        If none, equal to max_comment_roots.
    :return: dict
    """
    if max_comments_per_tree is None:
        max_comments_per_tree = max_comment_roots

    ret = []
    comments = 0
    for comment in forest:
        if isinstance(comment, praw.reddit.models.MoreComments) or \
                comment.body == "[removed]":
            continue

        if comments >= max_comment_roots:
            break

        comments += 1
        simplified = simplify_comment(comment)
        simplified["replies"] = get_simplified_nested_comments(
            comment.replies,
            max_comments_per_tree,
        )
        ret.append(simplified)

    return ret


def get_simplified_nested_comments(forest, max_comments, current_comments=IntVar(1)):
    ret = []
    for comment in forest:
        if isinstance(comment, praw.reddit.models.MoreComments) or \
                comment.body == "[removed]":
            continue

        if current_comments >= max_comments:
            break

        current_comments += 1
        simplified = simplify_comment(comment)
        simplified["replies"] = get_simplified_nested_comments(
            comment.replies,
            max_comments,
            current_comments=current_comments
        )
        ret.append(simplified)

    return ret


def simplify_comment(comment):
    name = "[deleted]"
    pfp = "https://upload.wikimedia.org/wikipedia/commons/c/c4/600_px_Transparent_flag.png"
    if comment.author:
        name = comment.author.name
        if hasattr(comment.author, "icon_img"):
            pfp = comment.author.icon_img
    return {
        "author": name,
        "author_pfp": pfp,
        "body": comment.body,
        "score": comment.score,
        "replies": []
    }


def media_submissions(sub: str, max_scenes=100000, comment_chars=range(30, 80)):
    """
    Fetches a subreddit's top submissions.
    :param sub: The name of the subreddit.
    :param max_scenes: Max number of posts to download.
    :param comment_chars: The range of character that the comments can have.
    :return: ImageLink[]: A list of URLs leading to the images.
    """
    reddit = get_reddit_instance()

    try:
        submission_lists = [reddit.subreddit(sub).top("week"), reddit.subreddit(sub).hot()]

        ret = []
        added_submissions = []
        for submissions in submission_lists:
            for s in submissions:
                if len(ret) >= max_scenes:
                    break

                if s.over_18 or s.stickied or not hasattr(s, "post_hint") or s.id in added_submissions:
                    continue

                post = None
                if s.post_hint == "hosted:video":
                    media_url = s.secure_media["reddit_video"]["fallback_url"]
                    post = MediaPost(media_url, s.title)
                elif s.post_hint == "rich:video":
                    try:
                        media_url = s.preview["reddit_video_preview"]["fallback_url"]
                        post = MediaPost(media_url, s.title)
                    except:
                        pass
                elif s.post_hint == "image":
                    source = s.preview["images"][0]["source"]
                    # Is a GIF
                    if "variants" in s.preview["images"][0].keys() \
                            and "mp4" in s.preview["images"][0]["variants"].keys():
                        source = s.preview["images"][0]["variants"]["mp4"]["source"]

                    image_url = source["url"]
                    if MIN_RATIO <= source["width"]/source["height"] <= MAX_RATIO and \
                            image_url not in ret:
                        post = MediaPost(image_url, s.title)

                if post:
                    if random() < COMMENT_CHANCE:
                        comment = load_first_comment(s.id, reddit,
                                                     lambda body: "\n" not in body and len(body) in comment_chars)
                        if comment:
                            comment = backend.utils.polish_comment(comment)
                            post.comment = comment
                    ret.append(post)
                    added_submissions.append(s.id)

        return ret

    except Exception:
        print(traceback.format_exc())
        return []


def load_first_comment(post_id, reddit=None, condition=None):
    if not reddit:
        reddit = get_reddit_instance()

    submission = reddit.submission(post_id)
    for comment in submission.comments:
        if comment.author and not comment.author.is_mod \
                and (not condition or condition(comment.body)):
            return comment.body


def twitter_user_images(user):
    """
    Fetches a twitter account's top submissions.
    :param user: str: The name of the twitter user.
    :return: ImageLink[]: A list of URLs leading to the images.
    """
    api = twitter.Api(
        consumer_key=Twitter.consumer_key,
        consumer_secret=Twitter.consumer_secret,
        access_token_key=Twitter.access_token_key,
        access_token_secret=Twitter.access_token_secret
    )

    try:
        statuses = api.GetUserTimeline(
            screen_name=user,
            include_rts=False,
            exclude_replies=True,
            count=200
        )
    except twitter.error.TwitterError:
        return []

    ret = []
    for s in statuses:
        if s.media and len(s.media) == 1 and s.media[0].type == "photo":
            photo = s.media[0]
            # original_url = f"https://twitter.com/{user}/status/{s.id_str}"
            ratio = None
            for size in photo.sizes:
                if size != "thumb":
                    ratio = photo.sizes[size]["w"] / photo.sizes[size]["h"]

            if ratio and MIN_RATIO <= ratio <= MAX_RATIO:
                ret.append(ImageLink(photo.media_url_https, True))
    return ret


def sign(key, msg):
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def get_signature_key(key, date_stamp, region_name, service_name):
    k_date = sign(('AWS4' + key).encode('utf-8'), date_stamp)
    k_region = sign(k_date, region_name)
    k_service = sign(k_region, service_name)
    k_signing = sign(k_service, 'aws4_request')
    return k_signing


def get_tts_audio(text, voice):
    t = datetime.datetime.utcnow()
    amz_date = t.strftime('%Y%m%dT%H%M%SZ')
    date_stamp = t.strftime('%Y%m%d')
    host = "polly.eu-west-1.amazonaws.com"
    region = "eu-west-1"
    service = "polly"
    endpoint = "https://polly.eu-west-1.amazonaws.com/v1/speech"

    method = "POST"
    canonical_uri = "/v1/speech"
    canonical_qstring = ""
    canonical_headers = 'content-type:application/json\n' + 'host:' + host + '\n' + 'x-amz-date:' + amz_date + '\n'
    signed_headers = "content-type;host;x-amz-date"

    body = {
        "Engine": VOICES[voice]["engine"],
        "OutputFormat": "mp3",
        "TextType": "text",
        "SampleRate": "22050",
        "Text": text,
        "VoiceId": VOICES[voice]["id"],
    }
    body = json.dumps(body)

    payload_hash = hashlib.sha256(body.encode('utf-8')).hexdigest()
    canonical_request = method + '\n' + canonical_uri + '\n' + canonical_qstring + '\n' + canonical_headers + '\n'\
        + signed_headers + '\n' + payload_hash

    # Step 2
    algorithm = 'AWS4-HMAC-SHA256'
    credential_scope = date_stamp + '/' + region + '/' + service + '/' + 'aws4_request'
    string_to_sign = algorithm + '\n' + amz_date + '\n' + credential_scope + '\n' + hashlib.sha256(
        canonical_request.encode('utf-8')).hexdigest()

    # Step 3
    signing_key = get_signature_key(Amazon.secret_key, date_stamp, region, service)
    signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
    authorization_header = algorithm + ' ' + 'Credential=' + Amazon.access_key + '/' + credential_scope +\
        ', ' + 'SignedHeaders=' + signed_headers + ', ' + 'Signature=' + signature

    backend.log.tts(text, voice)
    resp = http.request(
        "POST",
        endpoint,
        body=body.encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            'X-Amz-Date': amz_date,
            'Authorization': authorization_header
        }
    )

    return resp.data


def download_resource(url, file_path, auto_ext=False):
    return download_image(url, file_path, auto_ext=auto_ext)


def download_image(url, file_path, auto_ext=False):
    try:
        response = http.request("GET", url, preload_content=False)
        if auto_ext:
            content_type = response.headers['Content-Type']
            regex = r".+/(.+?)(?:$|;)"
            ext = re.findall(regex, content_type)[0]
            file_path += f".{ext}"

        stdout = open(file_path, "wb")
        for chunk in response.stream(1024):
            stdout.write(chunk)
        response.release_conn()

        if response.status == 404:
            os.remove(file_path)
            return None
        return file_path
    except:
        print(f"Error for {url}")
