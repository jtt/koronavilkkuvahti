import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Optional, Dict
import argparse

import time
from tracker.adv_receiver import ENData, Receiver
from tracker.runner import SOCKET_PATH, Runner
from tracker.view import Element, UI


class ENObserver:
    def __init__(self, bluew_exe: str = "./bluewalker", hcidev: str = "hci0"):
        self._log = logging.getLogger(self.__class__.__name__)
        self._bluewalker = bluew_exe
        self._hcidev = hcidev
        self._runner: Optional[Runner] = None
        self._receiver: Optional[Receiver] = None
        self._collector: Optional[asyncio.Task] = None
        self._ids: Dict[str, Element] = {}
        self._sig: asyncio.Event = asyncio.Event()
        self._stop: bool = False

    async def exp_notif_collector(self, q: asyncio.Queue):
        log = logging.getLogger("exposure-lgger")
        while True:
            en = await q.get()
            self._log.info("from %s: Prox ID: %s", en.address, en.prox_id.hex())
            prox = en.prox_id.hex()
            if prox not in self._ids:
                self._ids[prox] = Element(address=en.address, rssi=en.rssi)
                self._sig.set()
            else:
                el = self._ids[prox]
                el.rssi = en.rssi
                if el.address != en.address:
                    self._log.warning(
                        "Same proximity id %s sent from two addresses %s, %s",
                        prox,
                        el.address,
                        en.address,
                    )
                    el.address = en.address
                el.last_ts = time.time()

    async def run(self):
        bw_path = Path(self._bluewalker)
        if not bw_path.exists():
            self._log.warning("Executable %s does not exist", bw_path.as_posix())
            return

        # Create handler task
        q = asyncio.Queue()
        self._collector = asyncio.create_task(self.exp_notif_collector(q))

        self._runner = Runner(bw_path, self._hcidev)
        self._receiver = Receiver(Path(SOCKET_PATH), q)

        # start the UNIX socket listener
        await self._receiver.listen()
        # Start bluewalker process
        await self._runner.start()

        ui = UI()

        while not self._stop:
            try:
                await asyncio.wait_for(self._sig.wait(), 10)
                self._sig.clear()
            except asyncio.TimeoutError:
                pass

            now = time.time()
            aged = []
            for k, v in self._ids.items():
                if int(now - v.last_ts) > 30:
                    aged.append(k)
            for k in aged:
                v = self._ids.pop(k)
            ui.show(self._ids)
        ui.fin()

    async def stop(self):
        if self._runner is not None:
            self._log.info("Stopping runner")
            await self._runner.stop()
            self._runner = None
        if self._receiver is not None:
            self._log.info("Stopping server")
            await self._receiver.close()
            self._receiver = None
        if self._collector is not None:
            self._log.info("Canceling collector")
            self._collector.cancel()
            self._collector = None
        self._stop = True
        self._sig.set()


if __name__ == "__main__":

    args_p = argparse.ArgumentParser()
    args_p.add_argument(
        "--bluewalker",
        action="store",
        help="Path to bluewalker binary to use",
        default="./bluewalker",
    )
    args_p.add_argument(
        "--hcidev", action="store", help="Name of the HCI device to use", default="hci0"
    )
    args_p.add_argument(
        "--debug", action="store_true", help="Enable debug messages", default=False
    )
    args = args_p.parse_args()

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(name)s::%(levelname)s - %(message)s")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    if args.debug:
        handler.setLevel(logging.DEBUG)
    else:
        handler.setLevel(logging.WARN)
    root_logger.addHandler(handler)

    observer = ENObserver(args.bluewalker, args.hcidev)

    def sighandler(sig, frame):
        asyncio.create_task(observer.stop())

    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)

    asyncio.get_event_loop().run_until_complete(observer.run())
