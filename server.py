#!/usr/bin/env python3
import asyncio
import logging
from websockets.asyncio.server import serve, broadcast
from collections import defaultdict

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

async def parse_msg(msg: str) -> tuple[str, str]:
    try:
        action, m = msg.split(' ', maxsplit=1)
        
    except ValueError as e:
        action, m = "invalid", f"invalid format: no action: {e}"
    return action, m

users: dict = {}
nicks: dict = {}
channels: defaultdict[str, set] = defaultdict(set)

async def do_action(websocket, action: str, msg: str) -> tuple[bool, str]:
    if websocket not in users and action != "nick":
        return False, "must have a nick"
    if action == "nick":
        if not msg.isidentifier():
            return False, "nick must be an identifier"
        if msg in nicks:
            return False, "nick already exists."
        logger.info(f"setting nick to {msg}")
        users[websocket] = {"nick": msg}
        nicks[msg] = websocket
        return True, ""

    user = users[websocket]
    nick = user['nick']

    match action:
        case 'privmsg':
            try:
                chan, pmsg = msg.split(' ', maxsplit=1)
                if len(channels[chan]) == 0:
                    return False, f"no such channel: {chan}"
                broadcast(channels[chan], f"{chan}	{nick}: {pmsg}")
            except ValueError:
                return False, "invalid syntax, must be: privmsv chan msg..."
        case 'join':
            if not msg.isidentifier():
                return False, "channel name must be an identifier"
            channels[msg].add(websocket)
            return True, f"joined {msg}"
        case 'leave':
            channels[msg].discard(websocket)
            return True, f"removed from {msg}"
        case 'invalid':
            return False, msg
    return True, ""


async def handler(websocket):
    async for message in websocket:
        action, msg = await parse_msg(message)
        logger.info(f"got msg: {msg}")
        ok, err = await do_action(websocket, action, msg)
        if not ok:
            await websocket.send(f"error: {err}")

async def main():
    port=8001
    logger.info(f"listening on {port}")
    try:
        stop = asyncio.get_event_loop().create_future()
        async with serve(handler, "", port):
            await stop
    except asyncio.exceptions.CancelledError:
        logger.info("cancelled main!")

if __name__ == "__main__":
    wlgr = logging.getLogger("websockets")
    wlgr.setLevel(logging.DEBUG)
    asyncio.run(main())

