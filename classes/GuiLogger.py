
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