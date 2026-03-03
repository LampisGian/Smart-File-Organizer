from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime
import json

#This class is responsible for keeping a history of all the file movements that have been made by the program.
@dataclass
class MoveRecord:
    src: str
    dst: str
    timestamp: str

#This class manages the history of file movements, allowing you to append new moves and undo the last move if needed.
class HistoryManager:
    def __init__(self, history_file: Path):
        self.history_file = history_file
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.history_file.exists():
            self._write([])

    def _read(self) -> list[dict]:
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            self._write([])
            return []

    def _write(self, items: list[dict]) -> None:
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2, ensure_ascii=False)

    def append_move(self, src: Path, dst: Path) -> None:
        items = self._read()
        record = MoveRecord(
            src=str(src),
            dst=str(dst),
            timestamp=datetime.now().isoformat(timespec="seconds"),
        )
        items.append(asdict(record))
        self._write(items)

    def pop_last(self) -> MoveRecord | None:
        items = self._read()
        if not items:
            return None
        last = items.pop()
        self._write(items)
        return MoveRecord(**last)

    def has_moves(self) -> bool:
        return len(self._read()) > 0