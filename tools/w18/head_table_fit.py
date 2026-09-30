#!/usr/bin/env python3
"""W18: floorplan-level fit of the V4.1 HEAD die (lm_head + embedding + DSpark MTP drafter) and the Engram TABLE
die, with ASAP7 macro/tile geometry, against W16's analytical counts (root 2026-09-30).

HEAD die: the layer-die frame (hub, PHY bands, links kept: the drafter runs attention), its ROM field tiled with
W10's measured 1.2 GHz q pair tile (476 x 126.9 um: two slots of two 4096m8 macros, ping-pong reads = the bytes of
one 8192m8 pair), abutment pins (no pin channel).  Tiles needed = W16's MAC-bearing macros / 2 (lm_head + drafter,
8192m8 equivalents) + the embedding rows (a row table without MACs), placed conservatively in full tiles.  The
slot count is derated by W16's overhead rule (12.5% of the die less the ring credit, then fill 0.9).
TABLE die: ROM macros only (8192m8, 274-bit words) on an 815 mm2 die with the links on two edges, gather slices
and the 12.5% overhead; crossing = farthest macro to the nearest link edge.

    python3 tools/w18/head_table_fit.py --w16 /tmp/claude-1000/wt/w16 --output results/physical_abi3/asap7/chip/v41_w18/head_table_fit.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REACH = 504.0
DIE_W, DIE_H = 31799.952, 25628.4
MACRO = (125.712, 119.34)          # ot_rom_8192x274_m8
ADDR_GAP, VHALO = 8.64, 1.62       # W1 pack: address-side gap, vertical halo
MACRO_B = 8192 * 274 / 8


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--w16", type=Path, required=True, help="W16 worktree (its uarch_model.py, uncommitted state)")
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args(argv)
    code = ("import sys, json; sys.path.insert(0, 'tools'); import uarch_model as U\n"
            "b = U._V41_PLACE['bytes']\n"
            "m = (b['head'] + b['mtp']) / 4 * U._cons_busiest_macros(28) / U.cons_stage_plan(28)['payload_per_die_B']\n"
            "per = (b['head'] + b['mtp']) / 4\n"
            "print(json.dumps(dict(bytes=b, mac_macros=m, mac_bytes=per, embed_bytes=b['embed'] / 4,"
            " usable=U.cons_field_usable_mm2(), geom=U.CONS_GEOM['w10_refit'], cons=U.CONS,"
            " head_need_8192=U._cons_need(m / 2, per + b['embed'] / 4, 'analytical', 'w10_q_1p2', 0, '8192m8'),"
            " head_dies_8192=U.cons_head_dies('analytical', None, 'ring', 'w10_refit', 'w10_q_1p2', '8192m8'),"
            " head_dies_4096=U.cons_head_dies('analytical', None, 'ring', 'w10_refit', 'w10_q_1p2', '4096m8'),"
            " table=U.cons_table_dies('analytical'), table_asap7=U.cons_table_dies('asap7'))))\n")
    w16 = json.loads(subprocess.run([sys.executable, "-c", code], cwd=a.w16, capture_output=True, text=True,
                                    check=True).stdout.strip().splitlines()[-1])
    w16_sha = sha(a.w16 / "tools/uarch_model.py")
    # ---- head die ----
    per_macro_B = w16["mac_bytes"] / w16["mac_macros"]
    mac_tiles = math.ceil(w16["mac_macros"] / 2)
    embed_tiles = math.ceil(w16["embed_bytes"] / per_macro_B / 2)
    need = mac_tiles + embed_tiles
    lef = ROOT / "results/physical_abi3/asap7/chip/v41_w18/head_die/q_tile_1p2.lef"
    fp_out = ROOT / "results/physical_abi3/asap7/chip/v41_w18/head_die/die_floorplan_head.json"
    subprocess.run([sys.executable, str(ROOT / "tools/w18/die_floorplan.py"), "--pack",
                    str(ROOT / "results/floorplan/v41_pack_refit_w18_e8p5.json"), "--pair-lef", str(lef),
                    "--row-channel-um", "0", "--col-gap-um", "0", "--pairs-needed", str(need), "--output", str(fp_out)],
                   check=True, capture_output=True)
    fp = json.loads(fp_out.read_text())
    G = w16["geom"]
    o = w16["cons"]["overhead"] * 815.0
    derate = w16["cons"]["fill"] * (G["field_mm2"] - max(0.0, o - G["ring_free_mm2"] - G["core_gap_mm2"])) / G["field_mm2"]
    slots = fp["capacity"]["pair_slots"]
    usable_slots = int(slots * derate)
    far = fp["crossings"]["vm_to_farthest_cluster"]["L_um"]
    head = dict(tile_um=[476.0, 126.9], tile_pitch_um=fp["pair"]["pitch_um"], tiles_needed=need,
                mac_tiles=mac_tiles, embed_tiles_conservative=embed_tiles, slots=slots, overhead_fill_derate=round(derate, 4),
                usable_slots=usable_slots, margin_pct=round(100 * (usable_slots - need) / need, 1),
                fits_one_quarter=usable_slots >= need, dies=4 if usable_slots >= need else 8,
                vm_to_farthest_tile=dict(L_um=far, cycles=math.ceil(far / REACH)),
                w16_analytical=dict(need_mm2=round(w16["head_need_8192"], 1), usable_mm2=round(w16["usable"], 1),
                                    head_dies_8192m8=w16["head_dies_8192"], head_dies_4096m8=w16["head_dies_4096"]),
                floorplan=dict(record=str(fp_out.relative_to(ROOT)), sha256=sha(fp_out)),
                basis="ASAP7 tile geometry, TP-4 head group: per die (lm_head + drafter)/4 MAC-bearing, embedding/4 as "
                      "full tiles (conservative)")
    # ---- table die ----
    link_edge = 1043.28                               # UCIe/SerDes strip depth on each of two edges
    keep = 21.6
    fw, fh = DIE_W - 2 * (link_edge + keep), DIE_H - 2 * keep
    px, py = MACRO[0] + ADDR_GAP / 2, MACRO[1] + VHALO
    raw = int(fw // px) * int(fh // py)
    gather_mm2 = 1.0 + 0.8055
    ov = w16["cons"]["overhead"] * 815.0 + gather_mm2
    usable = int((raw - ov * 1e6 / (px * py)) * w16["cons"]["fill"])
    per_die_B = usable * MACRO_B
    tb = w16["table"]["table_bytes"]
    n = math.ceil(tb / per_die_B)
    n += n % 2
    far_t = fw / 2 + fh / 2
    table = dict(macro="ot_rom_8192x274_m8", macro_pitch_um=[round(px, 3), round(py, 3)], raw_slots=raw,
                 usable_macros=usable, bytes_per_die_GB=round(per_die_B / 1e9, 2), table_bytes_GB=round(tb / 1e9, 2),
                 dies_asap7_geometry=n, dies_w16_analytical=w16["table"]["dies"], dies_w16_asap7=w16["table_asap7"]["dies"],
                 farthest_macro_to_link_edge=dict(L_um=round(far_t, 1), cycles=math.ceil(far_t / REACH),
                                                  basis="links on the east and west edges; a gather tree registers every "
                                                        "504 um; the switched table->layer path is inter-die (rack record)"),
                 note="ASAP7 macro geometry holds 274 raw bits a word; W16's analytical density is the product basis")
    rec = dict(schema="opentallas.v41.w18_head_table_fit.v1", head_die=head, table_die=table,
               w16=dict(worktree=str(a.w16), uarch_model_sha256=w16_sha, state="W16 worktree, uncommitted"),
               tool_sha256=sha(Path(__file__)))
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(rec, indent=1)[:3000])


if __name__ == "__main__":
    main()
