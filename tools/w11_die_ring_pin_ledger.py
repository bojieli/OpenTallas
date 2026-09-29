#!/usr/bin/env python3
"""Ledger of the records whose source pins the W11 die ring integration moved.

Wiring IDX_RING (opt-in, default 0) through ot_chip_v41x_die / _tile / ot_hdc_core_v41x /
ot_hdc_v41x_idx_pool_adapt changes those files' SHA-256, so every record that pinned their
pre-change content stops binding current sources.  This lists the records that were current on
those files at BASE, the digests before and after, and the evidence that the default path
(IDX_RING = 0) is unchanged: the die gate's replicated reference at position 7 runs cycle-identical
to the adopted die smoke record.  Writes results/rtl/w11_die_ring_pin_ledger.json.
"""
from __future__ import annotations

import glob
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/rtl/w11_die_ring_pin_ledger.json"
BASE = "4b1ac1dd"
FILES = ["rtl/chip/ot_chip_v41x_die.sv", "rtl/chip/ot_chip_v41x_tile.sv", "rtl/hdc/v41x/ot_hdc_core_v41x.sv",
         "rtl/hdc/v41x/ot_hdc_v41x_idx_pool_adapt.sv"]
DIE_GATE = "results/rtl/w11_die_idx_ring_gate.json"
SMOKE = "results/rtl/hdc_v41x_die_top_smoke.json"


def git_sha(f: str) -> str:
    return hashlib.sha256(subprocess.run(["git", "show", f"{BASE}:{f}"], capture_output=True, cwd=ROOT,
                                         check=True).stdout).hexdigest()


def pinned(x, out):
    if isinstance(x, dict):
        for k, v in x.items():
            if isinstance(v, str) and len(v) == 64 and any(k.endswith(f) for f in FILES):
                out.append((next(f for f in FILES if k.endswith(f)), v))
            else:
                pinned(v, out)
    elif isinstance(x, list):
        for v in x:
            pinned(v, out)


def build() -> dict:
    old = {f: git_sha(f) for f in FILES}
    new = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in FILES}
    moved = []
    for p in sorted(glob.glob(str(ROOT / "results/**/*.json"), recursive=True)):
        rel = str(Path(p).relative_to(ROOT))
        if rel in (str(OUT.relative_to(ROOT)), DIE_GATE):
            continue
        try:
            d = json.loads(Path(p).read_text())
        except Exception:
            continue
        pins = []
        pinned(d, pins)
        files = sorted({f for f, v in pins if v == old[f]})
        if files:
            moved.append({"record": rel, "moved_sources": files})
    gate = json.loads((ROOT / DIE_GATE).read_text())
    smoke = json.loads((ROOT / SMOKE).read_text())
    pos7 = next(c for c in gate["cases"] if c["image"] == "pos7")["replicated_reference"]["step"]
    return {
        "schema": "opentallas.w11-die-ring-pin-ledger.v1",
        "base_commit": BASE,
        "sources": {f: {"before": old[f], "after": new[f]} for f in FILES},
        "records_moved": moved,
        "label": "pins moved by an opt-in parameter (IDX_RING, default 0); not re-run",
        "default_path_evidence": {
            "gate": DIE_GATE,
            "replicated_reference_pos7_cycles": pos7["cycles"],
            "adopted_die_smoke_cycles": smoke["smoke"]["step"]["cycles"] if "step" in smoke["smoke"] else None,
            "cycle_identical": pos7["cycles"] == (smoke["smoke"]["step"]["cycles"] if "step" in smoke["smoke"] else -1),
            "token": pos7["next_token"]},
        "source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
                          for p in (DIE_GATE, SMOKE, "tools/w11_die_ring_pin_ledger.py")},
    }


def main() -> None:
    rec = build()
    if OUT.exists():
        raise SystemExit(f"{OUT} exists; records are never overwritten")
    OUT.write_text(json.dumps(rec, indent=2) + "\n")
    print(len(rec["records_moved"]), rec["default_path_evidence"])


if __name__ == "__main__":
    main()
