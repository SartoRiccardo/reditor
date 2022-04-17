

class MediaPost:
    def __init__(self, url, title, comment=None):
        self.url = url
        self.title = title
        self.comment = comment
        self.path = None

    def __str__(self):
        return f"<url={self.url} title='{self.title}' comment='{self.comment}'>"
