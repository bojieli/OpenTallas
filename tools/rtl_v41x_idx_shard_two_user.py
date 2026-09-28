#!/usr/bin/env python3
"""Exact two-user compact index-key isolation through four timed HBM stacks."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [ROOT / p for p in (
    "rtl/hdc/v41x/ot_hdc_v41x_idx_pool_kwr.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_pool_hbm_bridge.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_shard_addr.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_shard_reader.sv",
    "rtl/test/tb_hdc_v41x_idx_shard_two_user.sv",
    "tools/rtl_v41x_idx_shard_two_user.py",
)]
OUT = ROOT / "results/rtl/hdc_v41x_idx_shard_two_user.json"


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="v41_idx_two_user_") as d:
        binary = Path(d) / "two_user.vvp"
        subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_v41x_idx_shard_two_user",
                        "-o", str(binary), *map(str, SOURCES[:-1])], check=True)
        result = subprocess.run(["vvp", str(binary)], capture_output=True, text=True, check=True)
    pattern = r"V41X_SHARD_TWO_USER_PASS rows=(\d+) users=(\d+) records=(\d+) writes=(\d+) stalls=(\d+)"
    match = re.search(pattern, result.stdout)
    if not match:
        raise RuntimeError(result.stdout + result.stderr)
    rows, users, records, writes, stalls = map(int, match.groups())
    assert (rows, users, records, writes) == (32, 2, 32, 96) and stalls > 0
    scans = [tuple(map(int, m)) for m in re.findall(
        r"ROUNDTRIP n=(\d+) keys=(\d+) sectors=(\d+) cycles=(\d+)", result.stdout)]
    assert len(scans) == 2 and all((n, keys, sectors) == (16, 16, 34)
                                   for n, keys, sectors, _ in scans)
    record = {
        "schema": "opentallas-hdc-v41x-index-shard-two-user-v1",
        "status": "pass",
        "scope": "two compact key slices through writer, bridge, four timed HBM stacks and serial reader; no controller namespace or full-token gate",
        "user_base_sectors": [0, 2176],
        "rows_written": rows,
        "users": users,
        "bridge_records": records,
        "sector_writes": writes,
        "read_stall_cycles": stalls,
        "scans": [{"keys": n, "sectors": sectors, "cycles": cycles} for n, _, sectors, cycles in scans],
        "input_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCES},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=2) + "\n")
    print(result.stdout.strip())


if __name__ == "__main__":
    main()
