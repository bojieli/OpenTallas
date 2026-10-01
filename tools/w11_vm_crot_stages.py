#!/usr/bin/env python3
"""W11: C_rotate VM register stages from W18b's measured hub floorplan (root ruling 2026-10-01).

Geometry: W18b's compact C_rotate hub (claude/w18-die-assembly 32155a8f,
results/physical_abi3/asap7/chip/v41_w18/shrink_crot_interim/floorplan.json `hub`): SU_W (HUB_SU_VECTOR) | VM strip
(HUB_VM) | SU_E (HUB_SU_VECTOR_E), all the full hub height; lane-group tiles 433 x 433 um (8 lanes each, 64 a side
in 4 columns x 16 rows); the strip holds the bank array, the rotate networks (one a side, 512 lanes x 32 b), the
controller, the reducer and the VM port.  Distances are Manhattan and rectangle-bound (no pin plan inside the strip),
as W18b states them.

THE ROTATE SPAN.  A unit-stride vector at base b puts element b + l on lane l: element slot p = e mod 1,024 (its bank
row band is fixed) goes to lane (p - b) mod 1,024.  For every (slot, lane) pair some base realises it, so the
worst read path of a fixed pipeline is the farthest bank -> farthest lane-tile distance of the hub, whatever the
lane numbering or the rotate network's placement (a compact rotator at the strip centre gives the same sum:
bank -> centre -> lane).  Row-aligned bases (b = 0 mod 1,024) only cross from the bank's band to the tile edge;
a fixed-latency strip (the ruling: no per-op class decision) pays the worst case on every op.

Stages at the serial domain's 1.111 ns SS (W15's measured reach 748 um a stage, tools/uarch_model.SS_REACH_UM) and
the hardened rotate network's 7 mux levels a stage (results/physical_abi3/asap7/chip/w11_vm_rot/su_wc_lps7):
  CR_LEAD  controller (strip centre) -> farthest bank row: the address broadcast
  CR_RD    1 (the macros' output register, SS clock-to-q 511 ps: VM-H RDREG) + wire(farthest bank -> farthest lane)
           + ceil(10 levels / 7) rotate mux stages
  CR_WR    wire(farthest lane -> farthest bank) + ceil(10 / 7) (the write rotate; the macro's input register is the
           last stage)
  CR_GX    ceil(19 / 7) - ceil(10 / 7): the permutation network's extra stages for a gathered A
  CR_RES   reducer (strip centre) -> farthest bank
  X_GATHER_STAGES     1 (macro output register) + wire(farthest bank -> the strip centre's x root)
  RET_SCATTER_STAGES  wire(the strip centre's result sink -> farthest bank)
  COLL_WRITE_STAGES   wire(collective centre -> strip centre -> farthest bank)
Variants: a controller pair at 1/4 and 3/4 height (W18b: about 1,800 + 1,050 um).

Writes results/floorplan/v41_vm_crot_stages.json.
    python3 tools/w11_vm_crot_stages.py [--floorplan PATH]
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import uarch_model as U                    # noqa: E402

OUT = ROOT / "results/floorplan/v41_vm_crot_stages.json"
FP_REF = ("claude/w18-die-assembly", "32155a8ffe8714d3fc98387acf0bb96e9d6cec9d",
          "results/physical_abi3/asap7/chip/v41_w18/shrink_crot_interim/floorplan.json")
ROT_REC = "results/physical_abi3/asap7/chip/w11_vm_rot/su_wc_lps7/physical.json"
TILE_UM = 433.0
N, NG = 1024, 128
ROT_LEVELS, BENES_LEVELS, LPS = 10, 19, 7
PERIOD_NS = 1.111


def load_fp(path: str | None):
    if path:
        text = Path(path).read_text()
        src = dict(path=path)
    else:
        text = subprocess.run(["git", "show", f"{FP_REF[1]}:{FP_REF[2]}"], cwd=ROOT, capture_output=True, text=True,
                              check=True).stdout
        src = dict(branch=FP_REF[0], commit=FP_REF[1], path=FP_REF[2])
    src["sha256"] = hashlib.sha256(text.encode()).hexdigest()
    return json.loads(text), src


SQ_REF = ("claude/w18-die-assembly", "dfce8d40", "results/physical_abi3/asap7/chip/v41_w18/hub_square/plus/floorplan.json")


def load_ref(ref):
    text = subprocess.run(["git", "show", f"{ref[1]}:{ref[2]}"], cwd=ROOT, capture_output=True, text=True,
                          check=True).stdout
    return json.loads(text), dict(branch=ref[0], commit=ref[1], path=ref[2],
                                  sha256=hashlib.sha256(text.encode()).hexdigest())


def square_geometry(fp):
    """Worst distances of a hub whose lanes are the SU_VECTOR* parts around the VM part (any arrangement): lane-tile
    centres on a TILE_UM grid inside each lane part, bank = any point of the VM part (its corners bound it)."""
    parts = fp["hub"]["parts"]
    V = parts["HUB_VM"]
    lanes = []
    for k, r in parts.items():
        if r["kind"].startswith("SU_VECTOR"):
            nx, ny = max(1, int(r["w"] // TILE_UM)), max(1, int(r["h"] // TILE_UM))
            for i in range(nx):
                for j in range(ny):
                    lanes.append((r["x"] + TILE_UM * (i + 0.5), r["y"] + TILE_UM * (j + 0.5)))
    corners = [(V["x"], V["y"]), (V["x"] + V["w"], V["y"]), (V["x"], V["y"] + V["h"]), (V["x"] + V["w"], V["y"] + V["h"])]
    c = (V["x"] + V["w"] / 2, V["y"] + V["h"] / 2)
    md = lambda p, q: abs(p[0] - q[0]) + abs(p[1] - q[1])
    co = parts.get("HUB_COLLECTIVE")
    cc = (co["x"] + co["w"] / 2, co["y"] + co["h"] / 2) if co else c
    ctrl = max(md(c, k) for k in corners)
    return dict(bank_um=[round(V["w"], 1), round(V["h"], 1)], lane_tiles=len(lanes),
                worst_bank_to_lane_um=round(max(md(k, t) for k in corners for t in lanes), 1),
                controller_to_farthest_bank_um=round(ctrl, 1),
                controller_to_farthest_tile_um=round(max(md(c, t) for t in lanes), 1),
                collective_to_farthest_bank_um=round(md(cc, c) + ctrl, 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--floorplan", default=None)
    ap.add_argument("--square-floorplan", default=None)
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    fp, src = load_fp(a.floorplan)
    parts = fp["hub"]["parts"]
    W, V, E = parts["HUB_SU_VECTOR"], parts["HUB_VM"], parts["HUB_SU_VECTOR_E"]
    reach = U.SS_REACH_UM[0.9e9]
    st = lambda um: math.ceil(um / reach)
    mux = lambda lv: math.ceil(lv / LPS)

    # lane-group tiles: 4 x 16 a side, against the strip
    def tiles(r, east):
        nx, ny = int(r["w"] // TILE_UM), int(r["h"] // TILE_UM)
        out = []
        for j in range(16):
            for i in range(4):
                x = (r["x"] + TILE_UM * (i + 0.5)) if east else (r["x"] + r["w"] - TILE_UM * (i + 0.5))
                out.append((x, r["y"] + TILE_UM * (j + 0.5)))
        return out, (nx, ny)
    tw, fitw = tiles(W, False)
    te, fite = tiles(E, True)
    lanes = tw + te
    sx0, sy0, sx1, sy1 = V["x"], V["y"], V["x"] + V["w"], V["y"] + V["h"]
    cx, cy = (sx0 + sx1) / 2, (sy0 + sy1) / 2
    corners = [(sx0, sy0), (sx0, sy1), (sx1, sy0), (sx1, sy1)]
    md = lambda p, q: abs(p[0] - q[0]) + abs(p[1] - q[1])
    worst_bank_lane = max(md(c, t) for c in corners for t in lanes)
    # row-aligned (base = 0 mod 1,024): tile -> the strip edge it faces, in its own band
    aligned = max(min(abs(t[0] - sx0), abs(t[0] - sx1)) for t in lanes)
    ctrl_bank = max(md((cx, cy), c) for c in corners)
    ctrl_tile = max(md((cx, cy), t) for t in lanes)
    pair_bank = (sx1 - sx0) / 2 + (sy1 - sy0) / 4          # a controller at 1/4 (3/4) height -> its half's far corner
    coll = parts["HUB_COLLECTIVE"]
    coll_c = (coll["x"] + coll["w"] / 2, coll["y"] + coll["h"] / 2)
    coll_um = md(coll_c, (cx, cy)) + ctrl_bank
    geo = dict(strip_um=[round(V["w"], 1), round(V["h"], 1)], su_half_um=[round(W["w"], 1), round(W["h"], 1)],
               tiles_per_side=len(tw), tile_um=TILE_UM, tile_grid_fits=dict(west=fitw, east=fite),
               worst_bank_to_lane_um=round(worst_bank_lane, 1), row_aligned_tile_to_strip_um=round(aligned, 1),
               controller_to_farthest_bank_um=round(ctrl_bank, 1), controller_to_farthest_tile_um=round(ctrl_tile, 1),
               controller_pair_to_farthest_bank_um=round(pair_bank, 1),
               strip_centre_to_farthest_bank_um=round(ctrl_bank, 1),
               collective_centre_to_strip_centre_um=round(md(coll_c, (cx, cy)), 1),
               collective_to_farthest_bank_um=round(coll_um, 1))
    rot_mux, ben_mux = mux(ROT_LEVELS), mux(BENES_LEVELS)
    p = dict(CR_LEAD=st(ctrl_bank), CR_RD=1 + st(worst_bank_lane) + rot_mux, CR_GX=ben_mux - rot_mux,
             CR_WR=st(worst_bank_lane) + rot_mux, CR_RES=st(ctrl_bank),
             X_GATHER_STAGES=1 + st(ctrl_bank), RET_SCATTER_STAGES=st(ctrl_bank), COLL_WRITE_STAGES=st(coll_um))
    variants = dict(
        controller_pair=dict(p, CR_LEAD=st(pair_bank)),
        row_aligned_only=dict(note="NOT a fixed pipeline: the stages a base = 0 mod 1,024 op would need; the "
                                   "ruling's fixed-latency strip pays the worst case on every op",
                              CR_RD=1 + st(aligned) + rot_mux, CR_WR=st(aligned) + rot_mux))
    # the 481 um a stage figure W18b / W16b quote for the hub (an M5-bound reach); the RTL uses W15's 748
    r481 = lambda um: math.ceil(um / 481.0)
    variants["reach_481um"] = dict(CR_LEAD=r481(ctrl_bank), CR_RD=1 + r481(worst_bank_lane) + rot_mux, CR_GX=ben_mux - rot_mux,
                                   CR_WR=r481(worst_bank_lane) + rot_mux, CR_RES=r481(ctrl_bank),
                                   X_GATHER_STAGES=1 + r481(ctrl_bank), RET_SCATTER_STAGES=r481(ctrl_bank),
                                   COLL_WRITE_STAGES=r481(coll_um),
                                   note="481 um a stage (W18b commit 32155a8f / W16b); not used for the RTL")
    # the SQUARE (plus) hub W18b placed after root approved it as a free fix (claude/w18-die-assembly dfce8d40): the
    # bank square at the centre, a lane arm on each side, collective / gather / HC pieces in the corners
    sq_fp, sq_src = load_fp(a.square_floorplan) if a.square_floorplan else load_ref(SQ_REF)
    sq = square_geometry(sq_fp)
    variants["square_hub"] = dict(
        CR_LEAD=st(sq["controller_to_farthest_bank_um"]), CR_RD=1 + st(sq["worst_bank_to_lane_um"]) + rot_mux,
        CR_GX=ben_mux - rot_mux, CR_WR=st(sq["worst_bank_to_lane_um"]) + rot_mux,
        CR_RES=st(sq["controller_to_farthest_bank_um"]), X_GATHER_STAGES=1 + st(sq["controller_to_farthest_bank_um"]),
        RET_SCATTER_STAGES=st(sq["controller_to_farthest_bank_um"]),
        COLL_WRITE_STAGES=st(sq["collective_to_farthest_bank_um"]), floorplan=sq_src, geometry=sq,
        note="root-approved square (plus) hub; stage parameters only, the RTL is unchanged")
    su_extra = p["CR_LEAD"] + p["CR_RD"] + p["CR_WR"]
    rec = dict(
        schema="opentallas.floorplan.w11_vm_crot_stages.v1",
        generated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        floorplan=src, rotate_record=ROT_REC,
        basis=dict(period_ns=PERIOD_NS, clock="SU / VM serial domain 0.9 GHz, SS setup / FF hold, 60/25 ps",
                   wire_reach_um=reach, wire_reach_source="tools/uarch_model.SS_REACH_UM (W15 measured, 1.111 ns SS)",
                   rotate_levels=ROT_LEVELS, permutation_levels=BENES_LEVELS, mux_levels_per_stage=LPS,
                   distances="Manhattan, rectangle-bound (W18b): no pin plan inside the strip; M1-M5 in the strip, "
                             "M1-M7 in the SU halves; the reach is W15's routed figure, not re-measured on M5",
                   rotate_span=("every (bank slot, lane) pair is realised by some base, so the fixed pipeline pays "
                                "the hub's farthest bank -> farthest lane distance on every op")),
        geometry=geo, rtl_parameters=p, variants=variants,
        design_keys=dict(control_broadcast=p["CR_LEAD"], control_word_to_lanes=st(ctrl_tile),
                         operand_read=p["CR_RD"], gather_read=p["CR_RD"] + p["CR_GX"], element_write=p["CR_WR"],
                         reduce_result=p["CR_RES"], x_gather=p["X_GATHER_STAGES"], ret_scatter=p["RET_SCATTER_STAGES"],
                         coll_write=p["COLL_WRITE_STAGES"], rotate_mux_levels=ROT_LEVELS, rotate_mux_stages=rot_mux,
                         benes_mux_levels=BENES_LEVELS, benes_mux_stages=ben_mux,
                         note=("control_broadcast is controller -> strip (the address); the control word to the "
                               "lanes (control_word_to_lanes) rides in parallel, inside control_broadcast + "
                               "operand_read")),
        per_su_op=dict(element_op_extra_cycles=su_extra,
                       reduce_op_extra_cycles=p["CR_LEAD"] + p["CR_RD"] + p["CR_RES"],
                       gathered_op_extra_cycles=su_extra + p["CR_GX"],
                       basis="emit -> strip read (CR_LEAD) -> lanes (CR_RD) ... lanes -> strip (CR_WR | CR_RES); "
                             "the controller -> lane control word (controller_to_farthest_tile) rides in parallel"),
        compared_to_priced=dict(record="results/uarch/w11_vm_options.json C_rotate",
                                compact_assumption="every lane within ~3,850 um of the strip: 8 stages each way, "
                                                   "su_op_extra ~21",
                                finding=("the 3,850 um framing bounds the lane -> strip-edge leg only; the rotate moves "
                                         "data along the strip's full height, so the worst bank -> lane leg is the hub's "
                                         f"{worst_bank_lane:,.0f} um")),
        source_sha256={s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest()
                       for s in ("tools/w11_vm_crot_stages.py", "tools/uarch_model.py")})
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(geometry=geo, rtl_parameters=p, per_su_op=rec["per_su_op"]), indent=1))


if __name__ == "__main__":
    main()
