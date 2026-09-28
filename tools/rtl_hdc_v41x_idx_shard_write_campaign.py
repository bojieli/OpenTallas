#!/usr/bin/env python3
"""Source-pinned boundary and HBM read-after-write gate for striped index keys."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / "rtl/hdc/v41x/ot_hdc_v41x_idx_pool_kwr.sv"
BRIDGE = ROOT / "rtl/hdc/v41x/ot_hdc_v41x_idx_pool_hbm_bridge.sv"
HBM = ROOT / "rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv"
TB_WRITER = ROOT / "rtl/test/tb_hdc_v41x_idx_pool_kwr_sharded.sv"
TB_BRIDGE = ROOT / "rtl/test/tb_hdc_v41x_idx_pool_bridge_sharded.sv"
OUT = ROOT / "results/rtl/hdc_v41x_idx_shard_write.json"


def run_bench(tmp: Path, top: str, sources: list[Path], expected: str) -> str:
    binary = tmp / f"{top}.vvp"
    subprocess.run(["iverilog", "-g2012", "-s", top, "-o", str(binary), *map(str, sources)], check=True)
    run = subprocess.run(["vvp", str(binary)], capture_output=True, text=True, check=True)
    if not re.search(expected, run.stdout):
        raise RuntimeError(run.stdout + run.stderr)
    return run.stdout.strip()


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="v41_idx_shard_write_") as d:
        tmp = Path(d)
        writer = run_bench(tmp, "tb_hdc_v41x_idx_pool_kwr_sharded", [RTL, TB_WRITER],
                           r"V41XPOOLKWRSHARD checked=14 errors=0 keys=14")
        bridge = run_bench(tmp, "tb_hdc_v41x_idx_pool_bridge_sharded", [BRIDGE, HBM, TB_BRIDGE],
                           r"V41XPOOLBRIDGESHARD records=4 writes=12 reads=8 errors=0")
    src = [RTL, BRIDGE, HBM, TB_WRITER, TB_BRIDGE, Path(__file__).resolve()]
    record = {
        "schema": "opentallas-v41x-index-shard-write-v1",
        "status": "pass",
        "scope": "writer address/mask and one-hot HBM bridge; read scheduler and full token not covered",
        "layout": "16-key groups round-robin over 4 stacks, compact local groups, 68 B/key/stack placement",
        "writer_cases": 14,
        "bridge_records": 4,
        "bridge_sector_writes": 12,
        "bridge_reads": 8,
        "writer_stdout": writer,
        "bridge_stdout": bridge,
        "sources": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in src},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=2) + "\n")
    print(writer)
    print(bridge)


if __name__ == "__main__":
    main()
