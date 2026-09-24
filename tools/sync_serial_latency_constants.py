#!/usr/bin/env python3
"""Copy the hardwired datapath's measured depths into configs/hardware/technology.json.

The per-token operator graph (src/opentallas/critical_path.py) prices every ROM
operator with ``technology.json`` ``serial_latency.rom_datapath``.  Those values
are copies of this repository's RTL timing model and routed results:

* ``tools/hdc_timing.py`` ``K`` (sequencer gap, matrix-engine latency and tree,
  stream-unit depths, reducer tail, barrier idle) and ``tools/hdc_isa.py``
  ``INTERLEAVE``;
* the slowest routed fmax among the token path's units, and the routed stream
  lane area (results/physical_abi3/asap7/hdc/).

They are copied rather than read at run time on purpose: every roofline artifact
pins ``technology.json`` by digest, so a changed constant must change that file
and be followed by a regeneration, never move a committed result silently.

    python3 tools/sync_serial_latency_constants.py          # rewrite the copies
    python3 tools/sync_serial_latency_constants.py --check  # exit 1 if any drifted
    python3 tools/regenerate_roofline.py                    # then regenerate

tests/test_decode_critical_path.py runs ``--check``.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import hdc_isa as I  # noqa: E402
import hdc_timing  # noqa: E402

TECH = ROOT / "configs" / "hardware" / "technology.json"
PHYS = ROOT / "results" / "physical_abi3" / "asap7" / "hdc"
CLOCK_BLOCKS = ("ot_hdc_matvec", "ot_hdc_stream", "v41/ot_hdc_softplus", "v41/ot_hdc_select_k512",
                "v41/ot_hdc_blockdot", "v41/ot_hdc_actquant", "v41/ot_hdc_fp4qdq")
REGEN = "python3 tools/sync_serial_latency_constants.py && python3 tools/regenerate_roofline.py"


def _design(block: str) -> dict:
    return json.loads((PHYS / block / "physical.json").read_text())["design"]


def expected() -> dict[str, float]:
    K = hdc_timing.K
    su = K["su_depth"]
    clocks = {b: _design(b)["fmax_hz"] for b in CLOCK_BLOCKS}
    slowest = min(clocks, key=clocks.get)
    return {
        "clock_hz": clocks[slowest],
        "sequencer_gap_cycles": K["seq_gap"],
        "barrier_idle_cycles": K["idle_reg"],
        "matrix_engine_latency_cycles": K["me_lat"],
        "matrix_engine_tree_cycles_per_level": K["me_tree"],
        "matrix_engine_interleave": I.INTERLEAVE,
        "reducer_tail_cycles": K["red_tail"],
        "stream_depth_none_cycles": su[I.SFU_NONE],
        "stream_depth_exp_cycles": su[I.SFU_EXP],
        "stream_depth_recip_cycles": su[I.SFU_RECIP],
        "stream_depth_rsqrt_cycles": su[I.SFU_RSQRT],
        "stream_depth_sigmoid_cycles": su[I.SFU_SIGM],
        "stream_lane_area_um2": _design("ot_hdc_stream")["area_um2"],
    }


def drift(raw: dict) -> dict[str, tuple[float, float]]:
    rom = raw["serial_latency"]["rom_datapath"]
    return {k: (rom[k]["value"], v) for k, v in expected().items() if float(rom[k]["value"]) != float(v)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    raw = json.loads(TECH.read_text())
    moved = drift(raw)
    if args.check:
        for k, (old, new) in moved.items():
            print(f"serial_latency.rom_datapath.{k}: technology.json {old} != RTL {new}")
        if moved:
            print(f"stale: run `{REGEN}` and commit the regenerated artifacts")
            return 1
        print("serial_latency.rom_datapath matches the RTL timing model")
        return 0
    for k, (_old, new) in moved.items():
        raw["serial_latency"]["rom_datapath"][k]["value"] = new
        print(f"serial_latency.rom_datapath.{k} -> {new}")
    if moved:
        TECH.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n")
        print("now regenerate: python3 tools/regenerate_roofline.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
