#!/usr/bin/env python3
"""Bounded full-shape tile lint for the external compact QE ROM boundary."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import resource
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_chip_v41x_die_smoke as D  # noqa: E402

OUT = ROOT / "results/rtl/hdc_v41x_qrom_source_tile.json"
BRIDGE = ROOT / "rtl/hdc/v41x/ot_hdc_v41x_idx_pool_hbm_bridge.sv"
EXTRA = [ROOT / p for p in (
    "rtl/chip/ot_chip_v41x_rope_su_word.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_window_kv_blocks.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_qrom_compact_word.sv",
)]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cap() -> None:
    n = 12 * 1024**3
    resource.setrlimit(resource.RLIMIT_AS, (n, n))


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="v41_qrom_tile_lint_") as td:
        stub = Path(td) / BRIDGE.name
        lines = BRIDGE.read_text().splitlines()
        stub.write_text("\n".join(lines[:lines.index(");")+1]) + "\nendmodule\n")
        sources = [p for p in D.sources("rtl") if p != BRIDGE] + [stub, *EXTRA]
        verilator = str(Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator")
        cmd = [verilator, "--lint-only", "-Wno-fatal", "-Wno-TIMESCALEMOD",
               "--top-module", "ot_chip_v41x_tile", "-GFULL_SHAPE=1",
               "-GW_HBM=0", "-GX_ATT=0", "-GX_IDX=0", "-GX_SEL=0", "-GX_EG=0",
               "-GWROM_AW=8", "-GHROM_AW=8", "-GEROM_AW=8", "-GPROG_AW=8",
               "-GVM_AW=12", "-GCROM_AW=8", f"-I{D.core.SVH.parent}",
               *map(str, sources)]
        result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                                timeout=180, preexec_fn=cap)
        if result.returncode:
            raise RuntimeError("tile lint failed:\n" + result.stderr[-4000:])
    paths = sorted(set([p for p in D.sources("rtl") if p != BRIDGE] +
                       [BRIDGE, *EXTRA, Path(__file__)]))
    record = {
        "schema": "opentallas.rtl.v41x_qrom_source_tile.v1",
        "status": "pass",
        "claim_scope": "Full-shape W_HBM=0 tile port elaboration with external compact QE ROM service. Attention, indexer, select and Engram disabled; pooled-index bridge header stubbed. No full-layer token, qtile spatial mapping, rate or route claim.",
        "memory_cap_bytes": 12 * 1024**3,
        "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in paths},
    }
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print("PASS: full-shape W_HBM=0 QE ROM tile boundary lint")


if __name__ == "__main__":
    main()
