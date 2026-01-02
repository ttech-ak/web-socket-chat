#!/usr/bin/env python3
import asyncio
import logging
import sqlalchemy.ext.asyncio as asa
from websockets.asyncio.server import serve, broadcast
from collections import defaultdict
import argparse
import json
import history

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

async def parse_msg(message: str) -> tuple[dict[str, str], bool]:
    msg: dict[str, str] = {}
    ok: bool = True
    def invalid(reason):
        nonlocal ok
        msg["reason"] = reason
        ok = False
    try:
        m = json.loads(message)
        msg["action"] = m["action"]
        match m["action"]:
            case 'privmsg':
                msg["message"] = m["message"]
                msg["channel"] = m["channel"]
            case 'join':
                msg["channel"] = m["channel"]
            case 'leave':
                msg["channel"] = m["channel"]
            case 'nick':
                msg["nick"] = m["nick"]
        for key in ["action", "channel", "nick"]:
            try:
                v = m[key]
                if not isinstance(v, str):
                    invalid(f"invalid format, '{key}' must be a string")
                    break
                if not v.isidentifier():
                    invalid(f"invalid format, '{key}' must be an identifier")
                    break
            except KeyError:
                    pass
    except ValueError as e:
        invalid(f"invalid format: {e}")
    except KeyError as e:
        invalid(f"invalid format, key not found: {e}")        
    except Exception as e:
        invalid(f"unknown error: {e}")
    logger.info(f"parsing finished, results: ({msg},{ok})")
    return (msg, ok)

users: dict = {}
nicks: dict = {}
channels: defaultdict[str, set] = defaultdict(set)

async def do_action(websocket,
                    con: asa.AsyncSession,
                    action: str, params: dict[str, str]) -> tuple[bool, str]:
    if websocket not in users and action != "nick":
        return False, "must have a nick"
    if action == "nick":
        wanted_nick = params["nick"]
        if not wanted_nick.isidentifier():
            return False, "nick must be an identifier"
        if wanted_nick in nicks:
            return False, "nick already exists."
        logger.info(f"setting nick to {wanted_nick}")
        users[websocket] = {"nick": wanted_nick}
        nicks[wanted_nick] = websocket
        await history.add_nick(con, wanted_nick)
        return True, ""

    user = users[websocket]
    nick = user['nick']

    if "channel" in params:
        # ensured above all needed messages actually have this key, and is an identifier
        chan = params["channel"]
    match action:
        case 'privmsg':
            chan, pmsg = params["channel"], params["message"]
            if len(channels[chan]) == 0:
                return False, f"no such channel: {chan}"
            broadcast(channels[chan], f"{chan}	{nick}: {pmsg}")
            await history.add_log(con, chan, nick, pmsg)
        case 'join':
            channels[chan].add(websocket)
            bl = await history.get_backlog(con, chan)
            for log in bl:
                await websocket.send(f"{log.timestamp}\t{log.nick}: {log.msg}")
            return True, f"joined {chan}"
        case 'leave':
            channels[chan].discard(websocket)
            return True, f"removed from {chan}"
    return True, ""


async def handler(websocket, sess: asa.async_sessionmaker[asa.AsyncSession]):
    async for message in websocket:
        msg, ok = await parse_msg(message)
        logger.info(f"got msg: {msg}")
        if not ok:
            await websocket.send(f"error: {msg["reason"]}")
            continue
        async with sess.begin() as con:
            ok, err = await do_action(websocket, con, msg["action"], msg)
            if not ok:
                await websocket.send(f"error: {err}")
                await con.rollback()
                continue
    for chan in channels.values():
        chan.discard(websocket)
    try:
        nick = users[websocket]["nick"]
        del nicks[nick]
        del users[websocket]
        logger.info(f"deleted nick {nick}")
    except KeyError:
        pass # no nick was defined.

async def main(host, port):
    engine, sess = await history.NewEngine(args.db)
    logger.info(f"listening on {port}")

    async def my_handler(websocket):
        await handler(websocket, sess)
    
    try:
        stop = asyncio.get_event_loop().create_future()
        async with serve(my_handler, host, port):
            await stop
    except asyncio.exceptions.CancelledError:
        await engine.dispose()
        logger.info("cancelled main!")

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='chat-websocket',
        description='A server to chat among multiple channels using websockets',
    )
    parser.add_argument('-p', '--port', default=8001, type=int)
    parser.add_argument('-H', '--host', default="")
    parser.add_argument('-d', '--db', default="sqlite+aiosqlite:///db.db")
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    # wlgr = logging.getLogger("websockets")
    # wlgr.setLevel(logging.DEBUG)
    args = parse_args()
    asyncio.run(main(host=args.host, port=args.port))

