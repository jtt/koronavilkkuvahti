from rich.console import Console
from rich.table import Table
from rich.box import SQUARE
import time
from typing import Dict


class Element:
    def __init__(self, address: str, rssi: int):
        self.address = address
        self.first_ts = time.time()
        self.last_ts = time.time()
        self.rssi = rssi


class UI:
    def __init__(self):
        self._console = Console()
        self._console.show_cursor(False)
        self._console.clear()
        t = self._create_table()
        self._console.print(t)

    def _create_table(self) -> Table:
        table = Table(title="Active Proximity ID's", box=SQUARE)
        table.add_column("Proximity ID")
        table.add_column("Address")
        table.add_column("RSSI")
        table.add_column("Active")
        return table

    def show(self, data: Dict[str, Element]):
        t = self._create_table()
        for k, el in data.items():
            t.add_row(
                k,
                el.address,
                f"{str(el.rssi)}dBm",
                f"{str(int(el.last_ts - el.first_ts))}s",
            )

        self._console.clear()
        self._console.print(t)

    def fin(self):
        self._console.show_cursor(True)
