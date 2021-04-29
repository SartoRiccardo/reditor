from credentials import Reddit, Amazon, Twitter
import json
import urllib3
import urllib.parse
import hashlib
import hmac
import datetime
import praw
import twitter


http = urllib3.PoolManager()
VOICES = {
    "male-2": "Joey",
    "male-1": "Matthew",
    "female-1": "Kendra",
    "female-2": "Kimberly",
}
MAX_RATIO = 3/2
MIN_RATIO = 1/MAX_RATIO


def subreddit_image_posts(sub):
    """
    Fetches a subreddit's top submissions.
    :param sub: str: The name of the subreddit.
    :return: str[]: A list of URLs leading to the images.
    """
    reddit = praw.Reddit(
        client_id=Reddit.client_id,
        client_secret=Reddit.client_secret,
        user_agent=Reddit.user_agent
    )
    reddit.read_only = True

    try:
        submissions = reddit.subreddit(sub).top()

        ret = []
        for s in submissions:
            if hasattr(s, "post_hint") and s.post_hint == "image" and not s.stickied and \
                    not s.over_18:
                source = s.preview["images"][0]["source"]
                image_url = s.preview["images"][0]["source"]["url"]
                if MIN_RATIO <= source["width"]/source["height"] <= MAX_RATIO and image_url not in ret:
                    ret.append(image_url)

        return ret

    except:
        return []


def twitter_user_images(user):
    """
    Fetches a twitter account's top submissions.
    :param user: str: The name of the twitter user.
    :return: str[]: A list of URLs leading to the images.
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
                ret.append(photo.media_url_https)
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
        "OutputFormat": "mp3",
        "TextType": "text",
        "SampleRate": "22050",
        "Text": text,
        "VoiceId": VOICES[voice],
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

