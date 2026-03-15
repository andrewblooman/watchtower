from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class LogLine:
    file: str
    line: str


class LogTailer:
    def __init__(self, logs_dir: str):
        self._dir = Path(logs_dir)
        self._offsets: dict[str, int] = {}

    def poll(self) -> list[LogLine]:
        if not self._dir.exists():
            return []

        out: list[LogLine] = []
        for p in sorted(self._dir.glob("*.log")):
            key = str(p)
            last = self._offsets.get(key, 0)
            try:
                size = p.stat().st_size
            except FileNotFoundError:
                continue
            if size < last:
                last = 0

            with p.open("r", encoding="utf-8", errors="replace") as f:
                f.seek(last)
                for line in f:
                    line = line.rstrip("\n")
                    if line:
                        out.append(LogLine(file=p.name, line=line))
                self._offsets[key] = f.tell()
        return out

