from __future__ import annotations

import time
from pathlib import Path

from .util import read_json, write_json

REPEAT_REJECT_THRESHOLD = 2


class Memory:
    def __init__(self, state_dir: Path):
        self.path = state_dir / "memory.json"
        data = read_json(self.path, {})
        self.verdicts: dict = data if isinstance(data, dict) else {}

    def _entry(self, pattern: str) -> dict:
        return self.verdicts.setdefault(pattern, {"accepted": 0, "rejected": 0, "last": None})

    def should_skip(self, path: str, rule_key: str | None) -> bool:
        if path in self.verdicts and self.verdicts[path].get("rejected", 0) > 0:
            return True
        if rule_key:
            entry = self.verdicts.get(rule_key, {})
            if entry.get("rejected", 0) >= REPEAT_REJECT_THRESHOLD:
                return True
        return False

    def record(self, path: str, rule_key: str | None, decision: str) -> None:
        ts = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
        for pattern in {path, rule_key} if rule_key else {path}:
            entry = self._entry(pattern)
            entry[decision] = entry.get(decision, 0) + 1
            entry["last"] = ts

    def forget(self, pattern: str | None = None) -> int:
        if pattern is None:
            count = len(self.verdicts)
            self.verdicts = {}
        else:
            count = 1 if self.verdicts.pop(pattern, None) else 0
        self.save()
        return count

    def save(self) -> None:
        write_json(self.path, self.verdicts)

    def summary(self) -> list[tuple[str, int, int, str | None]]:
        return [(k, v.get("accepted", 0), v.get("rejected", 0), v.get("last"))
                for k, v in sorted(self.verdicts.items())]
