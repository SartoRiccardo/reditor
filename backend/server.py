import asyncio
import websockets
import inspect
import modules.logger


PORT_BASE = 52900
PORT_REDITOR = PORT_BASE + 1
PORT_DISCORD = PORT_BASE + 2


actions = {}
try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()


async def receive(websocket):
    async for message in websocket:
        callback = message["action"]
        if callable(callback):
            if inspect.isawaitable(callback):
                await callback(message["body"])
            else:
                callback(message["body"])


def connect(action, callback):
    actions[action] = callback


async def start():
    async with websockets.serve(receive, "localhost", PORT_REDITOR):
        await asyncio.Future()  # run forever


def send_to_discord_bot(action, payload, response=False):
    async def send():
        try:
            websocket = await websockets.connect(f"ws://localhost:{PORT_DISCORD}")
            await websocket.send({"action": action, "body": payload})
            if response:
                return await websocket.recv()
            websocket.close()
        except OSError:
            modules.logger.Logger.log("Discord bot server not online", modules.logger.Logger.WARN)

    return loop.run_until_complete(send())
