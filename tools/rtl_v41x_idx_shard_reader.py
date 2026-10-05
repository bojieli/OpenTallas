#!/usr/bin/env python3
"""Run the compact four-stack V4.1 index-key read correctness gate."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [ROOT / path for path in (
    "rtl/hdc/v41x/ot_hdc_v41x_idx_shard_addr.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_shard_reader.sv",
    "rtl/test/tb_hdc_v41x_idx_shard_reader.sv",
)]
OUT = ROOT / "results/rtl/hdc_v41x_idx_shard_reader.json"
SCAN = re.compile(r"SCAN n=(\d+) keys=(\d+) sectors=(\d+) beats=(\d+) ref=(\d+) cycles=(\d+)")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="v41-shard-reader-") as tmp:
        binary = Path(tmp) / "sim.vvp"
        subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_v41x_idx_shard_reader",
                        "-o", str(binary), *map(str, SOURCES)], check=True, cwd=ROOT)
        run = subprocess.run(["vvp", str(binary)], check=True, capture_output=True,
                             text=True, timeout=120, cwd=ROOT)
    scans = [tuple(map(int, m.groups())) for m in SCAN.finditer(run.stdout)]
    assert len(scans) == 13 and "V41X_SHARD_READER_PASS scans=13" in run.stdout, run.stdout
    for n, keys, sectors, _, refs, cycles in scans:
        assert keys == n and sectors == 2 * n + (n + 7) // 8
        assert refs == int(n > 7)
        assert cycles > sectors
    largest = next(row for row in scans if row[0] == 1040)
    script = Path(__file__).resolve()
    rec = {
        "schema": "opentallas.hdc-v41x-idx-shard-reader.v1", "status": "pass",
        "scans": len(scans), "keys_checked": sum(row[1] for row in scans),
        "sectors_read": sum(row[2] for row in scans),
        "largest_complete_scan_keys": max(row[0] for row in scans),
        "serial_policy_1040_keys": {"cycles": largest[5], "sectors": largest[2],
                                    "sectors_per_cycle": round(largest[2] / largest[5], 6)},
        "coverage": "Exact quarter-order 64-key beats across 16-key stack stripes and 1024-key local superblock boundary; code, scale, valid, last and refusal checked for every key; request and output backpressure; no duplicate sector reads.",
        "limitation": "Correctness-rate one-outstanding-sector reader with short-latency response fixture. Cycle count measures this serial fixture only, excludes timed HBM and full token, and cannot substantiate modeled bandwidth.",
        "input_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in [*SOURCES, script]},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=2) + "\n")
    print(run.stdout.strip())


if __name__ == "__main__":
    main()
