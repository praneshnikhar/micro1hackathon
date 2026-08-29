from __future__ import annotations

import argparse
import sys
import time

from .agent import run_pipeline
from .execute import restore
from .ledger import latest, load, save
from .memory import Memory
from .scout import build_manifest, disk_usage, top_records
from .util import fmt_bytes


def cmd_scan(args, cfg) -> int:
    records, stats = build_manifest(args.roots.split(",") if args.roots else cfg.roots, cfg)
    path = save(cfg, records, stats)
    total, free = disk_usage("/")
    print(f"disk: {fmt_bytes(free)} free of {fmt_bytes(total)} ({free / total * 100:.1f}%)")
    print(f"scan: {stats}")
    print(f"manifest: {path}")
    print("\ntop directories:")
    for r in top_records(records, 20):
        flag = " [landmark]" if r.landmark else ""
        print(f"  {fmt_bytes(r.size):>12}  {r.path}{flag}")
    return 0


def cmd_run(args, cfg) -> int:
    roots = args.roots.split(",") if args.roots else None
    return run_pipeline(cfg, simulate_threshold=args.simulate_threshold,
                        execute=args.execute, dry_run=args.dry_run,
                        yes_file=args.yes_file, roots=roots)


def cmd_watch(args, cfg) -> int:
    interval = args.interval or cfg.watch_interval_s
    print(f"watching: free space < {cfg.threshold_pct}% triggers the guardian; interval {interval}s")
    while True:
        total, free = disk_usage("/")
        pct = free / total * 100
        stamp = time.strftime("%H:%M:%S")
        if pct < cfg.threshold_pct:
            print(f"[{stamp}] threshold crossed ({pct:.1f}%) — running guardian")
            run_pipeline(cfg, simulate_threshold=False, execute=args.execute,
                         dry_run=args.dry_run, yes_file=args.yes_file)
        else:
            print(f"[{stamp}] healthy ({pct:.1f}% free)")
        time.sleep(interval)


def cmd_restore(args, cfg) -> int:
    print(restore(args.cid, cfg))
    return 0


def cmd_report(args, cfg) -> int:
    reports = sorted(cfg.reports_dir.glob("*.md"))
    if not reports:
        print("no reports yet; run: spaceward run --simulate-threshold --execute --yes-file ...")
        return 1
    print(reports[-1].read_text())
    return 0


def cmd_memory(args, cfg) -> int:
    memory = Memory(cfg.state_dir)
    if args.action == "show":
        rows = memory.summary()
        if not rows:
            print("memory is empty; verdicts appear after your first execute run")
            return 0
        print(f"{'pattern':<50} {'ok':>4} {'no':>4}  last")
        for pattern, ok, no, last in rows:
            print(f"{pattern:<50} {ok:>4} {no:>4}  {last or '-'}")
    elif args.action == "forget":
        n = memory.forget(args.pattern)
        print(f"forgot {n} entr{'y' if n == 1 else 'ies'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spaceward",
        description="Preventive disk guardian: investigates what changed, deletes nothing without approval, verifies nothing broke.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_scan = sub.add_parser("scan", help="read-only scan; prints top dirs, saves manifest")
    p_scan.add_argument("--roots", help="comma-separated roots overriding config")

    p_run = sub.add_parser("run", help="full guardian loop")
    p_run.add_argument("--simulate-threshold", action="store_true",
                       help="run even if free space is above threshold")
    p_run.add_argument("--dry-run", action="store_true", help="plan only, never prompts or deletes")
    p_run.add_argument("--execute", action="store_true",
                       help="act on approved candidates (requires a gate: tty or --yes-file)")
    p_run.add_argument("--yes-file", help="JSON: {\"approve\": [\"cand-001\"]} or {\"approve\": \"all\"}")
    p_run.add_argument("--roots", help="comma-separated roots overriding config")

    p_watch = sub.add_parser("watch", help="poll free space; run guardian below threshold")
    p_watch.add_argument("--interval", type=int, help="poll interval seconds")
    p_watch.add_argument("--dry-run", action="store_true")
    p_watch.add_argument("--execute", action="store_true")
    p_watch.add_argument("--yes-file")

    p_restore = sub.add_parser("restore", help="restore a quarantined candidate by id")
    p_restore.add_argument("cid")

    sub.add_parser("report", help="print the latest cleanup report")

    p_mem = sub.add_parser("memory", help="show or forget learned verdicts")
    p_mem.add_argument("action", choices=["show", "forget"])
    p_mem.add_argument("pattern", nargs="?", help="pattern to forget (omit = forget all)")

    return parser


def main(argv: list[str] | None = None) -> int:
    from .config import Config
    parser = build_parser()
    args = parser.parse_args(argv)
    cfg = Config.load()
    handlers = {"scan": cmd_scan, "run": cmd_run, "watch": cmd_watch,
                "restore": cmd_restore, "report": cmd_report, "memory": cmd_memory}
    return handlers[args.command](args, cfg)


if __name__ == "__main__":
    sys.exit(main())
