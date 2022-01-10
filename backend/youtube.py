import http.client
import httplib2
import os
import random
import time
from PIL import Image

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

# References:
# https://developers.google.com/youtube/v3/guides/uploading_a_video
# https://github.com/SteBurz/youtube-uploader

# Explicitly tell the underlying HTTP transport library not to retry, since
# we are handling retry logic ourselves.
httplib2.RETRIES = 1

# Maximum number of times to retry before giving up.
MAX_RETRIES = 10

# Always retry when these exceptions are raised.
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, http.client.NotConnected,
                        http.client.IncompleteRead, http.client.ImproperConnectionState,
                        http.client.CannotSendRequest, http.client.CannotSendHeader,
                        http.client.ResponseNotReady, http.client.BadStatusLine)

# Always retry when an apiclient.errors.HttpError with one of these status
# codes is raised.
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

CLIENT_SECRETS_FILE = os.path.join(
    os.path.abspath(os.path.dirname(__file__)),
    "..",
    "credentials-youtube.json"
)

SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.force-ssl',
]
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'

VALID_PRIVACY_STATUSES = ('public', 'private', 'unlisted')


class UploadDetailException(Exception):
    def __init__(self, message, uploaded_id):
        super().__init__(message)
        self.uploaded_id = uploaded_id


def get_authenticated_service():
        credential_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'credentials.json')
        store = Storage(credential_path)
        credentials = store.get()
        try:
            credentials.refresh(httplib2.Http())
        except:
            pass

        if not credentials or credentials.invalid:
                flow = client.flow_from_clientsecrets(CLIENT_SECRETS_FILE, SCOPES)
                credentials = tools.run_flow(flow, store)
        return build(API_SERVICE_NAME, API_VERSION, credentials=credentials)


def initialize_upload(youtube, options):
    body = {
        "snippet": {
            "title": options['title'],
            "description": options['description'],
            "tags": options['tags'].split(","),
            "categoryId": options['category']
        },
        "status": {
            "privacyStatus": options['privacy']
        }
    }

    # Call the API's videos.insert method to create and upload the video.
    insert_request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=MediaFileUpload(options["file"], chunksize=-1, resumable=True)
    )

    return resumable_upload(insert_request)


# This method implements an exponential backoff strategy to resume a
# failed upload.
def resumable_upload(insert_request):
    response = None
    error = None
    retry = 0
    while response is None:
        try:
            print("Uploading file...")
            status, response = insert_request.next_chunk()
            if response is not None:
                if 'id' in response:
                    return response["id"]
                else:
                    raise Exception(f"The upload failed with an unexpected response: {response}")
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                error = f"A retriable HTTP error {e.resp.status} occurred:\n{e.content}"
            else:
                raise
        except RETRIABLE_EXCEPTIONS as e:
            error = f"A retriable error occurred: {e}"

        if error is not None:
            print(error)
            retry += 1
            if retry > MAX_RETRIES:
                exit("No longer attempting to retry.")

            max_sleep = 2 ** retry
            sleep_seconds = random.random() * max_sleep
            print("Sleeping %f seconds and then retrying..." % sleep_seconds)
            time.sleep(sleep_seconds)


# https://github.com/youtube/api-samples/blob/master/python/upload_thumbnail.py
def add_thumbnail(youtube, uploaded_id, thumbnail):
    youtube.thumbnails().set(
        videoId=uploaded_id,
        media_body=thumbnail
    ).execute()


# https://github.com/youtube/api-samples/blob/master/python/captions.py
def add_captions(youtube, uploaded_id, captions):
    youtube.captions().insert(
        part="snippet",
        body={
            "snippet": {
                "videoId": uploaded_id,
                "language": "en",
                "name": "Closed Captions",
                "isDraft": False,
            }
        },
        media_body=captions
    ).execute()


def upload(video, thumbnail, captions):
    youtube = get_authenticated_service()
    try:
        uploaded_id = initialize_upload(youtube, video)
    except HttpError as e:
        raise Exception("An HTTP error %d occurred:\n%s" % (e.resp.status, e.content))

    try:
        # YT thumbnails can't be > 2mb
        while os.stat(thumbnail).st_size > 2000000:
            thumb = Image.open(thumbnail)
            width, height = thumb.size
            thumb = thumb.resize((int(width*0.9), int(height*0.9)), Image.ANTIALIAS)
            thumb.save(thumbnail)
            thumb.close()
        add_thumbnail(youtube, uploaded_id, thumbnail)

        add_captions(youtube, uploaded_id, captions)
    except HttpError as e:
        raise UploadDetailException("An HTTP error %d occurred:\n%s" % (e.resp.status, e.content), uploaded_id)

    return uploaded_id


if __name__ == '__main__':
    get_authenticated_service()
