#!/usr/bin/env python3
import asyncio
import contextlib
import json
import logging
import os

import websockets


BUFFER_SIZE = 65536


async def forward_websocket_to_tcp(websocket, writer):
    try:
        async for message in websocket:
            if isinstance(message, str):
                data = message.encode("utf-8")
            else:
                data = message
            if data:
                writer.write(data)
                await writer.drain()
    finally:
        writer.close()
        await writer.wait_closed()


async def forward_tcp_to_websocket(reader, websocket):
    while True:
        data = await reader.read(BUFFER_SIZE)
        if not data:
            break
        await websocket.send(data)


async def handle_tunnel(websocket, path):
    if path != "/tunnel":
        await websocket.close(code=1008, reason="Unsupported path")
        return

    try:
        handshake = await websocket.recv()
    except websockets.exceptions.ConnectionClosed:
        return

    if isinstance(handshake, bytes):
        handshake = handshake.decode("utf-8")

    try:
        payload = json.loads(handshake)
        host = payload["host"]
        port = int(payload["port"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        logging.warning("Invalid handshake: %s", exc)
        await websocket.close(code=1008, reason="Invalid handshake")
        return

    try:
        reader, writer = await asyncio.open_connection(host, port)
    except OSError as exc:
        logging.warning("Failed to connect to %s:%s: %s", host, port, exc)
        await websocket.close(code=1011, reason="Upstream connection failed")
        return

    logging.info("Tunnel established to %s:%s", host, port)

    to_tcp = asyncio.create_task(forward_websocket_to_tcp(websocket, writer))
    to_ws = asyncio.create_task(forward_tcp_to_websocket(reader, websocket))

    done, pending = await asyncio.wait(
        {to_tcp, to_ws}, return_when=asyncio.FIRST_COMPLETED
    )
    for task in pending:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    logging.info("Tunnel closed for %s:%s", host, port)


async def main():
    host = os.getenv("WS_TUNNEL_HOST", "0.0.0.0")
    port = int(os.getenv("WS_TUNNEL_PORT", "8080"))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    async with websockets.serve(handle_tunnel, host, port, max_size=None):
        logging.info("WebSocket tunnel server listening on %s:%s", host, port)
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
