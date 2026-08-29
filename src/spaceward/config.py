from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .util import expand

DEFAULT_ROOTS = ["~", "~/Library", "~/Downloads"]


@dataclass
class Config:
    threshold_pct: float = 10.0
    watch_interval_s: int = 300
    max_scan_seconds: int = 90
    scan_min_size_mb: int = 8
    candidate_min_size_mb: int = 32
    growth_min_mb: int = 32
    provider: str = "auto"
    state_dir: Path = field(default_factory=lambda: expand("~/.spaceward"))
    quarantine_dir: Path = field(default_factory=lambda: expand("~/.spaceward/quarantine"))
    roots: list[str] = field(default_factory=lambda: list(DEFAULT_ROOTS))

    @property
    def manifests_dir(self) -> Path:
        return self.state_dir / "manifests"

    @property
    def reports_dir(self) -> Path:
        return self.state_dir / "reports"

    @property
    def trajectories_dir(self) -> Path:
        return self.state_dir / "trajectories"

    @classmethod
    def load(cls, overrides: dict | None = None) -> "Config":
        cfg = cls()
        path = cfg.state_dir / "config.toml"
        try:
            data = tomllib.loads(path.read_text())
        except (OSError, tomllib.TOMLDecodeError):
            data = {}
        for key in ("threshold_pct", "watch_interval_s", "max_scan_seconds",
                    "scan_min_size_mb", "candidate_min_size_mb", "growth_min_mb",
                    "provider", "state_dir", "quarantine_dir"):
            if key in data:
                setattr(cfg, key, data[key])
        if "roots" in data and isinstance(data["roots"], list):
            cfg.roots = [str(r) for r in data["roots"]]
        if overrides:
            for key, value in overrides.items():
                if value is not None:
                    setattr(cfg, key, value)
        cfg.state_dir = expand(cfg.state_dir)
        cfg.quarantine_dir = expand(cfg.quarantine_dir)
        return cfg
