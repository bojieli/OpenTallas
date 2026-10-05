#!/usr/bin/env python3
"""HA1 (R1b) full-die boundary measurement at the floorplan's distances (results/floorplan/hbm_gpu/v41_hbm_die.json).

Stage counts: every wire segment registered at the routed SS reach per 1.2 GHz stage (504 um, W15 measurement, the
constant tools/uarch_model.py barrier_network() uses).  The tree uses the floorplan's max leaf/trunk distances exactly
as results/rtl/gpu_supply_barrier.json did (62 cycles); the tx-count point-to-point links use every SM pair's own
Manhattan distance between tile centres (each pair as short as the floorplan allows, which favours R1b).
Runs rtl/hbm_accel/txcount/tb_txcount_die.sv (Icarus) for the four variants and writes the record.

    python3 tools/hbm_accel/run_ha1_die.py --out results/rtl/hbm_accel_ha1_20261004/die_boundary.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FP = "results/floorplan/hbm_gpu/v41_hbm_die.json"
REACH_UM = 504.0
SRC = ["rtl/gpu/ot_gpu_barrier_node.sv", "rtl/hdc/ot_hdc_delay.sv", "rtl/hbm_accel/txcount/ot_hbm_txcount_arrival.sv",
       "rtl/hbm_accel/txcount/tb_txcount_die.sv"]
VARIANTS = {0: "tree + x broadcast (ablation boundary)", 1: "tx-count point-to-point arrival counters, sync only (R1b as priced)",
            2: "tree, sync only (the measured 62-cycle barrier)", 3: "tx-count on the x data (hub forwards on landing, per-SM beat counters)"}


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def stages(um):
    return max(1, math.ceil(um / REACH_UM))


def geometry():
    fp = json.loads((ROOT / FP).read_text())
    sms = {int(r["name"][2:]): (r["x"] + r["w"] / 2, r["y"] + r["h"] / 2) for r in fp["regions"] if r["kind"] == "sm"}
    order = [s for q in sorted(fp["quadrants"], key=int) for s in fp["quadrants"][q]]   # tb SM index -> floorplan SM
    bn = fp["barrier_network"]
    pair_um = [[abs(sms[a][0] - sms[b][0]) + abs(sms[a][1] - sms[b][1]) for b in order] for a in order]
    stg = [[stages(pair_um[i][j]) if i != j else 1 for j in range(32)] for i in range(32)]
    return fp, bn, pair_um, stg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--nbar", type=int, default=200)
    a = ap.parse_args()
    fp, bn, pair_um, stg = geometry()
    d_leaf, d_trunk = stages(bn["max_leaf_um"]), stages(bn["max_trunk_um"])
    # x data: up = the arrival path's wire stages without the two AND-node registers (favours tx-count);
    # down = the release path's wire stages and its two branch registers (root, quadrant), as the release.
    d_up, d_dn = d_leaf + d_trunk, d_leaf + d_trunk + 2
    flat = [stg[i][j] for i in range(32) for j in range(32)]
    runs = []
    with tempfile.TemporaryDirectory() as td:
        inc = Path(td) / "ha1_die_stages.svh"
        inc.write_text(f"localparam integer D_LEAF = {d_leaf}, D_TRUNK = {d_trunk}, D_UP = {d_up}, D_DN = {d_dn};\n"
                       "localparam [N*N*8-1:0] STG = {" + ", ".join("8'd%d" % x for x in reversed(flat)) + "};\n")
        for v in VARIANTS:
            exe = Path(td) / f"v{v}"
            subprocess.run(["iverilog", "-g2012", "-I", td, "-o", str(exe), f"-Ptb_txcount_die.VARIANT={v}",
                            f"-Ptb_txcount_die.NBAR={a.nbar}"] + [str(ROOT / s) for s in SRC], check=True, cwd=ROOT)
            out = subprocess.run(["vvp", "-n", str(exe)], check=True, capture_output=True, text=True).stdout
            m = re.search(r"HA1_DIE .*", out).group(0)
            kv = dict(re.findall(r"(\w+)=(\d+)", m))
            r = dict(variant=v, desc=VARIANTS[v], min=int(kv["last_finish_to_all_start_min"]),
                     max=int(kv["max"]), mean=int(kv["mean_x100"]) / 100, early_start_errors=int(kv["early_start_errors"]),
                     barriers=int(kv["barriers"]))
            print(r, flush=True)
            runs.append(r)
    by = {r["variant"]: r for r in runs}
    sum_stages = sum(flat) - 32
    rec = dict(schema="opentallas.hbm_accel.ha1_die_boundary.v1", tool="tools/hbm_accel/run_ha1_die.py",
               floorplan=FP, clock_hz=1.2e9, stage_reach_um=REACH_UM,
               tree=dict(max_leaf_um=bn["max_leaf_um"], max_trunk_um=bn["max_trunk_um"], d_leaf=d_leaf, d_trunk=d_trunk),
               x_data=dict(d_up=d_up, d_dn=d_dn, beats=16, basis="H_X_TAIL_B 4096 B / X_BCAST_BPC 256 B (tools/uarch_model.py)"),
               pair=dict(max_um=round(max(max(r) for r in pair_um), 1), max_stages=max(flat),
                         links=32 * 31, link_stage_flops=sum_stages,
                         tree_stage_flops=32 * 2 * d_leaf + 4 * 2 * d_trunk),
               runs=runs,
               boundary_cycles=dict(ablation_with_x=by[0]["max"], txcount_x=by[3]["max"],
                                    tree_sync=by[2]["max"], txcount_a2a_sync=by[1]["max"]),
               saved_cycles_per_boundary=dict(with_x_data=by[0]["max"] - by[3]["max"],
                                              sync_only=by[2]["max"] - by[1]["max"]),
               priced=dict(boundary_cycles=78, target_cycles=47, saved_cycles=31),
               source_sha256={p: sha(p) for p in SRC + [FP, "tools/hbm_accel/run_ha1_die.py"]})
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(rec["boundary_cycles"]), json.dumps(rec["saved_cycles_per_boundary"]), json.dumps(rec["pair"]))


if __name__ == "__main__":
    main()
