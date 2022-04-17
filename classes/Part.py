from backend.utils import is_number
import re


class Part:
    def __init__(self, payload=None):
        self.text = ""
        self.voice = ""
        self.wait = 1.0
        self.crop = {"x": 0.0, "y": 0.0, "w": 0.0, "h": 0.0}
        self.fields = {}

        if isinstance(payload, str):
            self.init_from_str(payload)
        elif isinstance(payload, dict):
            self.init_from_dict(payload)

    def init_from_str(self, raw_text):
        lines = raw_text.split("\n")

        self.text = lines[1]
        self.voice = lines[2]
        self.wait = float(lines[3]) if is_number(lines[3]) else 1.0

        if lines[0].startswith("["):
            regex = r"\[(\S+?)=([^]]+?)]"
            match = re.findall(regex, lines[0])
            for field_name, field_value in match:
                self.fields[field_name] = field_value
        else:
            coords = lines[0].split(";")
            self.crop = {
                "x": float(coords[0]),
                "y": float(coords[1]),
                "w": float(coords[2]),
                "h": float(coords[3]),
            }

    def init_from_dict(self, data):
        self.text = data["text"]
        self.voice = data["voice"]
        self.wait = float(data["wait"]) if is_number(data["wait"]) else 1.0

        if "crop" in data:
            self.crop = data["crop"]

        if "fields" in data:
            self.fields = data["fields"]

    def is_crop_empty(self):
        return not bool(self.crop["w"] and self.crop["h"])

    def __str__(self):
        if len(self.fields.keys()) == 0:
            first_line = f"{self.crop['x']};{self.crop['y']};{self.crop['w']};{self.crop['h']}"
        else:
            first_line = "".join([f"[{key}={self.fields[key]}]" for key in self.fields.keys()])

        return (
            first_line + "\n" +
            self.text + "\n" +
            self.voice + "\n" +
            str(self.wait)
        )
