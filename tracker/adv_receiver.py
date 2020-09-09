import asyncio
import json
import logging
from pathlib import Path
from typing import Optional
import os
from dataclasses import dataclass
import base64


@dataclass(frozen=True, eq=True)
class ENData:
    address: str
    prox_id: bytes
    metadata: bytes
    rssi: int


class Receiver:
    def __init__(self, sock: Path, q: asyncio.Queue):
        self._sock: Path = sock
        self._log = logging.getLogger(self.__class__.__name__)
        self._server: Optional[asyncio.Server] = None
        self._q = q

    async def listen(self):
        if self._sock.exists():
            os.remove(self._sock)

        self._server = await asyncio.start_unix_server(self.connected, path=self._sock)
        await self._server.start_serving()

    async def close(self):
        if not self._server:
            return
        try:
            self._server.close()
            await self._server.wait_closed()
        except Exception:
            self._log.exception("Exception while closing server")
        finally:
            self._server = None

    async def connected(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        self._log.info("UNIX socket connected")
        del writer  # never used

        while True:
            line = await reader.readline()
            if not line:
                self._log.info("EOF from reader, stopping reader")
                break
            try:
                data = json.loads(line)
                self._log.debug("received %s", repr(data))
                addr = data.get("device", {}).get("address")
                if not addr:
                    self._log.warning("Malformed JSON data from bluewalker")
                    continue
                rssi = data.get("rssi", 0)
                prox = None
                metadata = None
                data = data.get("data", [])
                for d in data:
                    # Find the exposure notification service data
                    t = d.get("type", 0)
                    if t == 22:
                        raw = base64.b64decode(d.get("data", ""))
                        if len(raw) < 22:
                            # not the data we are looking for
                            continue
                        if raw[0] == 0x6F and raw[1] == 0xFD:
                            # starts with EN UUID 0xfd6f (in little endian)
                            prox = raw[2:18]  # proximity identifier: 16 bytes
                            metadata = raw[18:]  # encrypted metadtaa, 4 bytes
                            self._log.info("Found EN data")
                            break

                if prox is not None and metadata is not None:
                    en = ENData(
                        address=addr, prox_id=prox, metadata=metadata, rssi=rssi
                    )
                    self._q.put_nowait(en)
            except Exception as ex:
                self._log.warning("Unexpected exception in JSON reader: %s", str(ex))
