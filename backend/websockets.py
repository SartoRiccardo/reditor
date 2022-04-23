import asyncio
import websockets


PORT_BASE = 529000
PORT_REDITOR = PORT_BASE + 1
PORT_DISCORD = PORT_BASE + 2


async def receive(websocket):
    async for message in websocket:
        pass


async def server():
    async with websockets.serve(receive, "localhost", PORT_REDITOR):
        await asyncio.Future()  # run forever


def send_to_discord_bot(action, payload):
    async def send():
        async with websockets.connect(f"ws://localhost:{PORT_DISCORD}") as websocket:
            await websocket.send({"action": action, "body": payload})
    asyncio.run(send())
