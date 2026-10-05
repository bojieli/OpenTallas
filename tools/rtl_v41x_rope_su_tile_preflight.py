#!/usr/bin/env python3
"""Bounded lint of the full-shape tile's production RoPE SU cache port."""
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

OUT = ROOT / "results/rtl/v41x_rope_su_tile_preflight.json"
BRIDGE = ROOT / "rtl/hdc/v41x/ot_hdc_v41x_idx_pool_hbm_bridge.sv"
ROPE = ROOT / "rtl/chip/ot_chip_v41x_rope_su_word.sv"
WINDOW = ROOT / "rtl/hdc/v41x/ot_hdc_v41x_window_kv_blocks.sv"
QROM = ROOT / "rtl/hdc/v41x/ot_hdc_v41x_qrom_compact_word.sv"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def cap() -> None:
    n = 24 * 1024**3
    resource.setrlimit(resource.RLIMIT_AS, (n, n))


def main() -> None:
    # The disabled pooled-index bridge crashes Verilator 5.050 internally at
    # V3Gate.cpp:986 when parsed alongside the tile. A port-identical blackbox
    # removes only that unrelated implementation from this bounded lint.
    with tempfile.TemporaryDirectory(prefix="v41_rope_tile_lint_") as td:
        stub = Path(td) / BRIDGE.name
        lines = BRIDGE.read_text().splitlines()
        terminator = lines.index(");")
        stub.write_text("\n".join(lines[:terminator+1]) + "\nendmodule\n")
        sources = [p for p in D.sources("rtl") if p != BRIDGE] + [stub, ROPE, WINDOW, QROM]
        verilator = str(Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator")
        cmd = [verilator, "--lint-only", "-Wno-fatal", "-Wno-TIMESCALEMOD",
               "--top-module", "ot_chip_v41x_tile", "-GFULL_SHAPE=1",
               "-GX_ATT=0", "-GX_IDX=0", "-GX_SEL=0", "-GX_EG=0",
               "-GWROM_AW=8", "-GHROM_AW=8", "-GEROM_AW=8",
               "-GPROG_AW=8", "-GVM_AW=12", "-GCROM_AW=8",
               f"-I{D.core.SVH.parent}", *map(str, sources)]
        result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                                timeout=180, preexec_fn=cap)
        if result.returncode:
            raise RuntimeError("tile lint failed:\n" + result.stderr[-4000:])
    source_paths = sorted(set([p for p in D.sources("rtl") if p != BRIDGE] +
                              [BRIDGE, ROPE, WINDOW, QROM, Path(__file__)]))
    record = {
        "schema": "opentallas.rtl.v41x_rope_su_tile_preflight.v1",
        "status": "pass",
        "claim_scope": "Full-width tile elaboration with RoPE tagged X_SU cache reads; attention, indexer, select and Engram engines disabled; pooled-index bridge port-identical lint stub; no full layer or die arbiter claim.",
        "memory_cap_bytes": 24*1024**3,
        "bridge_stub_source_sha256": sha(BRIDGE),
        "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in source_paths},
    }
    OUT.write_text(json.dumps(record,indent=2)+"\n")
    print(json.dumps({"status":"pass","sources":len(source_paths)}))


if __name__ == "__main__":
    main()
