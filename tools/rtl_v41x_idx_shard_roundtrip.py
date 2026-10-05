#!/usr/bin/env python3
"""Source-pinned writer/bridge/timed-HBM/reader compact-index roundtrip."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [ROOT / path for path in (
    "rtl/hdc/v41x/ot_hdc_v41x_idx_pool_kwr.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_pool_hbm_bridge.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_shard_addr.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_shard_reader.sv",
    "rtl/test/tb_hdc_v41x_idx_shard_roundtrip.sv",
)]
OUT = ROOT / "results/rtl/hdc_v41x_idx_shard_roundtrip.json"
SCAN = re.compile(r"ROUNDTRIP n=(\d+) keys=(\d+) sectors=(\d+) cycles=(\d+)")
PASS = re.compile(r"V41X_SHARD_ROUNDTRIP_PASS rows=(\d+) records=(\d+) writes=(\d+) stalls=(\d+)")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="v41-shard-roundtrip-") as tmp:
        binary = Path(tmp) / "sim.vvp"
        subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_v41x_idx_shard_roundtrip",
                        "-o", str(binary), *map(str, SOURCES)], check=True, cwd=ROOT)
        run = subprocess.run(["vvp", str(binary)], check=True, capture_output=True,
                             text=True, timeout=120, cwd=ROOT)
    scans = [tuple(map(int, m.groups())) for m in SCAN.finditer(run.stdout)]
    assert [row[0] for row in scans] == [1, 40, 65], run.stdout
    assert all(keys == n and sectors == 2 * n + (n + 7) // 8 and cycles > sectors
               for n, keys, sectors, cycles in scans), scans
    passed = PASS.search(run.stdout)
    assert passed, run.stdout
    rows, records, writes, stalls = map(int, passed.groups())
    assert (rows, records, writes) == (65, 65, 195) and stalls > 0
    script = Path(__file__).resolve()
    rec = {
        "schema": "opentallas.hdc-v41x-idx-shard-roundtrip.v1", "status": "pass",
        "rows_encoded": rows, "writer_records_committed": records,
        "hbm_sector_writes_committed": writes, "read_after_write_stall_cycles": stalls,
        "scans": [{"keys": n, "sectors_read": sectors, "cycles": cycles}
                  for n, _, sectors, cycles in scans],
        "coverage": "SHARDED K32 writer through write arbiter and four timed HBM3E simulation stacks to compact reader; distinct key scales, all code/scale bytes, quarter valid/last/refusal, Qs mod16=8, global rows63/64, and read issued before write commit.",
        "limitation": "Small-shape correctness gate. Serial one-outstanding-sector reader and behavioural HBM; no pooled-adapter token integration, modeled-bandwidth claim or physical closure.",
        "input_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in [*SOURCES, script]},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=2) + "\n")
    print(run.stdout.strip())


if __name__ == "__main__":
    main()
