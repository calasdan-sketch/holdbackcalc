#!/usr/bin/env python3
"""Re-runnable benchmark: rule coverage, citation coverage and batch throughput.

    python tools/bench.py [rows]      # default 10000 rows (the batch row cap)
"""
import csv
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from holdbackcalc import batch  # noqa: E402
from holdbackcalc.rules import REGISTRY, UNVERIFIED  # noqa: E402


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else batch.MAX_ROWS
    cmds = batch.BATCH_COMMANDS
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "jobs.csv")
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["project", "command", "date", "certificate", "registered", "sector"])
            for i in range(n):
                w.writerow([f"Job {i}", cmds[i % len(cmds)], f"20{26 + i % 20}-{1 + i % 12:02d}-{1 + i % 28:02d}", "", "", ""])
        t0 = time.perf_counter()
        rows = batch.read_rows(path)
        dt_s = time.perf_counter() - t0
    deadlines = sum(len(r[2]) for r in rows)
    print(f"verified, cited rules in registry : {len(REGISTRY)}")
    print(f"rules listed as NOT encoded       : {len(UNVERIFIED)}")
    print(f"batch commands                    : {len(cmds)}")
    print(f"batch: {len(rows)} jobs -> {deadlines} deadlines in {dt_s:.3f}s ({len(rows) / dt_s:,.0f} jobs/s)")


if __name__ == "__main__":
    main()
