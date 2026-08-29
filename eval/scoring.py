from __future__ import annotations

import json
from pathlib import Path

from eval import fixtures


def load_truth(truth_path: Path) -> dict:
    return json.loads(Path(truth_path).read_text())


def to_relpath(root: Path, deleted: str) -> str:
    try:
        return str(Path(deleted).resolve().relative_to(root.resolve()))
    except ValueError:
        return deleted


def score(truth_path: Path, root: Path, deleted_paths: list[str], wall_seconds: float, meta: dict) -> dict:
    truth = load_truth(truth_path)
    by_rel = {}
    for d in deleted_paths:
        rel = to_relpath(root, d)
        for art_rel in truth:
            if rel == art_rel or rel.startswith(art_rel.rstrip("/") + "/") or art_rel.startswith(rel.rstrip("/") + "/"):
                by_rel[art_rel] = rel
                break

    def effective_size(rel: str) -> int:
        size = truth[rel]["size_bytes"]
        if rel == fixtures.GROWTH_ARTIFACT:
            size += fixtures.GROWTH_APPEND_MB * 1024 * 1024
        return size

    reclaimed = 0
    false_positives = []
    for art_rel in by_rel:
        entry = truth[art_rel]
        if entry["verdict"] == "safe":
            reclaimed += effective_size(art_rel)
        else:
            false_positives.append({"case_id": entry["case_id"], "path": art_rel,
                                    "description": entry["description"]})
    total_safe = sum(effective_size(r) for r, e in truth.items() if e["verdict"] == "safe")
    missed = [r for r, c in truth.items()
              if c["verdict"] == "safe" and r not in by_rel]
    return {
        **meta,
        "wall_seconds": round(wall_seconds, 1),
        "reclaimed_bytes": reclaimed,
        "total_safe_bytes": total_safe,
        "recall": round(reclaimed / total_safe, 3) if total_safe else 0,
        "integrity_failures": len(false_positives),
        "false_positives": false_positives,
        "missed_safe_relpaths": missed,
    }
