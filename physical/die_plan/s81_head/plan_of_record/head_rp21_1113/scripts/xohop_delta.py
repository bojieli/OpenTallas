#!/usr/bin/env python3
"""HEAD-97 F1c RTL realization (COORD 11-13 item 3): apply to a plan that already carries the R-REACH-2 chain
internal_stations conn 'reg:x_q|reg:u_xo/q' on hd_tile (reach_rules.py fix --rules 2 on reach_pairs x_xo).

  * hd_tile contents u_core params XO_HOP = len(chain regs_um) (2): ot_s81hd_tile_native g_xoh[k].u_xoh (kept 512-b
    x stage) + g_xoh[k].go_h / xv_h (go / xv forwarded with x), branch claude/head-97-xohop-1113
  * relay_sites: every stage-k register at chain regs_um[k] (k = 0 nearest x_q), FIRM like the other relay stacks
    (keys g_xoh[k].u_xoh/q[b], g_xoh[k].go_h, g_xoh[k].xv_h)
  * the chain note records the realization (u_core.XO_HOP, u_core.g_xoh[k].u_xoh); no schema keys added
Lanes: NOT changed.  The stages are inside the tile core (like BST / CMP_STAGES), between the tile's own pin flops;
lane fixed_cycles would be landed by the bind as face pads (kit_istations / bind lane_pad) = 2 more stages.  Price:
the x / go hop a tile grows 2 -> 4 cycles, but the chain best hop a tile is longer, so the tile's own result is never the
critical input: measured on the 2-tile bench at the hd_tile plan params XO_HOP 0/2/4/6 = 8442/8442/8442/8443 cycles
(go -> spr), so 0 cycles a position and 0 per token for XO_HOP 2 on the 22-tile row pair (slack is per tile, constant).
Only the x stream at the row pair's return lane (chE*_r, unused x) is 44 cycles later.
usage: xohop_delta.py IN_PLAN OUT_PLAN [--report R.json]"""
import argparse, json, hashlib
from pathlib import Path
CONN = "reg:x_q|reg:u_xo/q"
ap = argparse.ArgumentParser(); ap.add_argument("inp"); ap.add_argument("out"); ap.add_argument("--report")
a = ap.parse_args()
P = json.loads(Path(a.inp).read_text()); t = P["partition_types"]["hd_tile"]
ch = [e for e in t.get("internal_stations") or [] if e.get("conn") == CONN]
assert len(ch) == 1, "expected one %s chain, got %d" % (CONN, len(ch))
ch = ch[0]; regs = ch["regs_um"]; k = len(regs); bits = int(ch.get("bits", 512)); assert bits == 512, bits
uc = [c for c in t["contents"] if c.get("inst") == "u_core"]; assert len(uc) == 1
old = uc[0]["params"].get("XO_HOP"); assert old in (None, str(k)), old
uc[0]["params"]["XO_HOP"] = str(k)
rs = t["relay_sites"]; added = 0
for j, (x, y) in enumerate(regs):
    xy = [round(x, 3), round(y, 3)]
    for b in range(bits):
        rs["g_xoh[%d].u_xoh/q[%d]" % (j, b)] = list(xy); added += 1
    rs["g_xoh[%d].go_h" % j] = list(xy); rs["g_xoh[%d].xv_h" % j] = list(xy); added += 2
ch["note"] = ch.get("note", "") + " | realized in RTL: u_core.XO_HOP=%d, stages u_core.g_xoh[k].u_xoh (+ go_h / xv_h), HEAD-97 11-13" % k
txt = json.dumps(P, indent=1) + "\n"; Path(a.out).write_text(txt)
rep = dict(xo_hop=k, relay_sites_added=added, stage_sites=regs, out_sha256=hashlib.sha256(txt.encode()).hexdigest(),
           tile_i_to_o_cycles=[2, 2 + k], per_row_pair_tiles=22,
           per_position_added_cycles=0, x_at_return_lane_added=22 * k,
           bench_plan_params_cycles={"XO_HOP0": 8442, "XO_HOP2": 8442, "XO_HOP4": 8442, "XO_HOP6": 8443},
           lanes_changed=0)
if a.report: Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
print(json.dumps(rep))
