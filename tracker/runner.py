import asyncio
from typing import Optional, List
from pathlib import Path
import logging

SOCKET_PATH = "/tmp/bluewalker.sock"


class Runner:
    def __init__(self, executable: Path, hci_devname: str = "hci0"):
        self._proc: Optional[asyncio.Process] = None
        self._exe: Path = executable
        self._hci_device = hci_devname
        self._log = logging.getLogger(self.__class__.__name__)
        # collect output from bluewalker
        self._output: List[str] = []

    async def _read(self, rd: asyncio.StreamReader):
        while True:
            try:
                l = await rd.readline()
                if not l:
                    break
                self._output.append(l.decode("utf-8"))
                self._log.debug("Bluewalker-out: %s", l)
            except Exception:
                self._log.exception("Exception while reading")
        self._log.info("Bluewalker reader stopped")

    async def start(self):

        args = [
            self._exe.absolute().as_posix(),
            "-duration",
            "-1",
            "-device",
            self._hci_device,
            "-json",
            "-unix",
            SOCKET_PATH,
            "-observer",
            "-filter-addata",
            "0x03,0x6ffd;0x16,0x6ffd",
        ]

        self._proc = await asyncio.create_subprocess_exec(
            *args,
            stdin=None,
            stderr=asyncio.subprocess.STDOUT,
            stdout=asyncio.subprocess.PIPE,
        )
        asyncio.create_task(self._read(self._proc.stdout))

    def check(self) -> Optional[int]:
        if self._proc is None:
            # bluewalker has been stopped and is no longer running
            return None
        return self._proc.returncode

    def get_output(self) -> List[str]:
        return self._output.copy()

    async def stop(self):
        if self._proc is None:
            return

        if self._proc.returncode is not None:
            # already terminated
            self._log.info(
                "Process has been terminated with return code %d", self._proc.returncode
            )
        else:
            self._proc.terminate()
            self._log.info("Terminated bluewalker")
            await self._proc.wait()
        self._proc = None
        self._log.info("Terminated")
