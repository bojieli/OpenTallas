#!/usr/bin/env python3
"""Source-pinned runtime RoPE HBM region boundary gate."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [ROOT / name for name in (
    "rtl/chip/ot_chip_v41x_rope_region_guard.sv",
    "rtl/test/tb_chip_v41x_rope_region_guard.sv",
)]
OUT = ROOT / "results/rtl/v41x_rope_region_guard.json"


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="v41_rope_region_") as td:
        binary = Path(td) / "region.vvp"
        build = subprocess.run(["iverilog", "-g2012", "-s",
                                "tb_chip_v41x_rope_region_guard", "-o", str(binary),
                                *map(str, SOURCES)], cwd=ROOT, capture_output=True,
                               text=True, timeout=30, check=True)
        assert not build.stderr, build.stderr
        sim = subprocess.run(["vvp", str(binary)], cwd=ROOT,
                             capture_output=True, text=True, timeout=30, check=True)
        match = re.search(r"ROPE_REGION_PASS checks=(\d+)", sim.stdout)
        if not match or int(match.group(1)) != 7:
            raise RuntimeError(sim.stdout + sim.stderr)
    paths = [*SOURCES, Path(__file__)]
    record = {
        "schema": "opentallas.rtl.v41x_rope_region_guard.v1",
        "status": "pass",
        "claim_scope": "Seven runtime per-stack region boundary cases for 1M plain and YaRN tables under the 0.9 HBM capacity reserve; no full die token claim.",
        "checks": 7,
        "source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in paths},
    }
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print("PASS: 7 RoPE HBM region checks")


if __name__ == "__main__":
    main()
