#!/usr/bin/env python3
"""W11 streaming-domain record: the V4.1 indexer element (ot_hdc_v41x_idx_chunk, ot_hdc_v41x_idx_tail) and the
attention tile (ot_hdc_v41x_attn_tile) deepened to the 1.2 GHz clock (0.833 ns) at the SS corner.

Collects the routed physical records (tools/run_abi3_physical.py, ORFS corner WC = SS setup, hold at WC + BC = FF,
60 ps setup / 25 ps hold uncertainty, yosys Kogge-Stone adders) of the hardening vehicles named on the command
line, copies each physical.json under results/physical_abi3/asap7/hdc/v41x/w11_stream/<run>/, and writes
w11_stream_summary.json with the SS fmax, area, the latency of every unit against the as-built LAT-3 engine, and
the bit-exactness gates run at the deep latencies (JSON files from the campaign tools, passed with --gate).

    python3 tools/w11_stream_record.py --run st_tail7=/path/physical.json ... --gate idx_reduced=/path/rec.json ...
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results/physical_abi3/asap7/hdc/v41x/w11_stream"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# -- latency model of the RTL (every formula is a localparam in the named file) ------------------------------
def idx_chunk_lat(fpl, fml, ql, nb=4):
    """ot_hdc_v41x_idx_chunk LAT (+ in/out registers = the engine's LAT_C)."""
    return 1 + ql + fpl * (nb - 1) + 1 + fml + fpl * 7 + 1


def idx_tail_lat(fpl, nch=4):
    return 1 + fpl * int(math.log2(nch)) + 1


def idx_engine_lat(fpl, fml, ql, nb=4, ih=32):
    """ot_hdc_v41x_idx_engine key beat -> tail output register (the bench's lat_min is this + 1 output reg)."""
    return idx_chunk_lat(fpl, fml, ql, nb) + idx_tail_lat(fpl, ih // 8)


def attn_tile_lat(fpl, fml, td=32):
    """ot_hdc_v41x_attn_tile input -> ov (the engine's TLAT)."""
    return 3 + fml + fpl * (7 + int(math.log2(td // 8)))


def attn_guard_q(fpl):
    return 6 * fpl + 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", default=[], help="name=physical.json")
    ap.add_argument("--gate", action="append", default=[], help="name=gate.json (bit-exactness evidence)")
    ap.add_argument("--note", action="append", default=[], help="name=text")
    ap.add_argument("--claim", action="append", default=[], help="run claimed closed (the test checks it)")
    a = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for spec in a.run:
        name, path = spec.split("=", 1)
        rec = json.loads(Path(path).read_text())
        d = rec["design"]
        m = rec.get("place_and_route", {}).get("metrics", {})
        dst = OUT_DIR / name / "physical.json"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(json.dumps(rec, indent=1) + "\n")
        argv = rec["runner"]["argv"]
        params = {argv[i + 1].split("=")[0]: int(argv[i + 1].split("=")[1]) for i, x in enumerate(argv)
                  if x == "--param"}
        rows.append(dict(
            run=name, top=d["block"], params=params, status=rec["status"], closed=d.get("closed"),
            target_period_ns=d.get("clock_period_ns"), ss_fmax_mhz=round(d["fmax_hz"] / 1e6, 1) if d.get("fmax_hz") else None,
            setup_wns_ns=d.get("setup_wns_ns"), hold_wns_ns=d.get("hold_wns_ns"),
            cell_area_um2=d.get("area_um2"), die_area_um2=m.get("die_area_um2"),
            drc=m.get("drc_errors"), max_slew_violations=m.get("max_slew_violations"),
            max_cap_violations=m.get("max_cap_violations"),
            hold_corners=[argv[i + 1] for i, x in enumerate(argv) if x == "--hold-corners"][0].split(","),
            primary_corner=[argv[i + 1] for i, x in enumerate(argv) if x == "--orfs-corner"],
            routing_layers=[argv[i + 1:i + 3] for i, x in enumerate(argv) if x == "--routing-layers"] or "default (M2-M9)",
            false_path_io="--false-path-io" in argv,
            git_commit=rec["git"]["commit"], worktree_dirty=rec["git"]["worktree_dirty"],
            record=str(dst.relative_to(ROOT))))
    gates = {}
    for spec in a.gate:
        name, path = spec.split("=", 1)
        g = json.loads(Path(path).read_text())
        gates[name] = g
    base = dict(idx_engine=idx_engine_lat(3, 3, 3) + 1, idx_chunk=idx_chunk_lat(3, 3, 3),
                idx_tail=idx_tail_lat(3), attn_tile=attn_tile_lat(3, 3), attn_guard_q=attn_guard_q(3))
    deep = dict(idx_engine=idx_engine_lat(7, 5, 5) + 1, idx_chunk=idx_chunk_lat(7, 5, 5),
                idx_tail=idx_tail_lat(7), attn_tile=attn_tile_lat(7, 6), attn_guard_q=attn_guard_q(7))
    srcs = ["rtl/hdc/v41x/ot_hdc_v41x_idx.sv", "rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv",
            "rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv", "rtl/hdc/v41x/ot_hdc_v41x_attn.sv",
            "rtl/hdc/v41x/ot_hdc_v41x_idx_score_slice.sv", "rtl/hdc/v41x/ot_hdc_v41x_idx_array.sv",
            "rtl/hdc/v41x/ot_hdc_v41x_w11s_tops.sv", "rtl/hdc/ot_hdc_fastfp.sv", "rtl/hdc/ot_hdc_fp32_add_lat.sv",
            "rtl/hdc/ot_hdc_delay.sv", "tools/w11_stream_record.py"]
    summary = dict(
        schema="opentallas.w11.stream_units.v1",
        claim="V4.1 streaming-domain units at 0.833 ns (1.2 GHz): ORFS primary corner WC (SS setup), hold repaired "
              "and checked at WC and BC (FF), 60 ps setup / 25 ps hold uncertainty, yosys Kogge-Stone adders "
              "(ADDER_MAP_FILE empty, the asap7 default since 006001b1); fmax is the routed finish fmax at SS",
        latency_parameters=dict(
            FPL="binary32 add latency: 3 = ot_hdc_fp32_add_fast (as built), 7 = ot_hdc_fp32_add_lat (closes 1,261 MHz "
                "SS, results/physical_abi3/asap7/hdc/w11_fp/w11_fp_latency_sweep.json)",
            FML="product latency: indexer ot_hdc_v41x_bmul (3..5), attention ot_hdc_v41x_attn_bmul (3..6)",
            QL="indexer block dot ot_hdc_v41x_q4dot (3..5)",
            default="FPL = FML = QL = 3 is the as-built RTL, cycle for cycle",
            streaming_build=dict(indexer=dict(FPL=7, FML=5, QL=5), attention=dict(FPL=7, FML=6))),
        latency_cycles=dict(as_built=base, streaming=deep,
                            added={k: deep[k] - base[k] for k in base},
                            note="idx_engine is key beat -> score beat valid (the campaign's lat_min; 48 as built at "
                                 "NB=4 IH=32). attn_tile is tile input -> ov (the engine's TLAT). Throughput stays "
                                 "II = 1: the sequential chunk sums are recurrences only along one key / one beat."),
        units=rows, claimed_closed=a.claim, gates=gates, notes=dict(n.split("=", 1) for n in a.note),
        source_sha256={p: sha(ROOT / p) for p in srcs})
    (OUT_DIR / "w11_stream_summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps(dict(units=[(r["run"], r["ss_fmax_mhz"], r["closed"]) for r in rows],
                          added=summary["latency_cycles"]["added"]), indent=1))


if __name__ == "__main__":
    main()
