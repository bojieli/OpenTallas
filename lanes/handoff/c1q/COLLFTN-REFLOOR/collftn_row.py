#!/usr/bin/env python3
"""QC-COLLFTN-REFLOOR row (C1q): coll_ftn outline 786.24 -> 432.00 um wide (origin kept), right part declared a die
channel, clock root/glue tap + count straps moved over the strip.  No partition moves; no partner pin/type change."""
import json, sys, hashlib
src, dst = sys.argv[1], sys.argv[2]
p = json.load(open(src))
T = p["partition_types"]["coll_ftn"]
W_OLD, H = T["outline_um"]
W_NEW = 432.0                       # 50 x 8.64 grid
DX = -259.2                         # 30 x 8.64: tap 388.8 -> 129.6 (strip centre of the 0-245 um bus columns)
assert abs(W_OLD - 786.24) < 1e-6 and abs(H - 648.0) < 1e-6
parts = [q for q in p["partitions"] if q["type"] == "coll_ftn"]
assert [q["name"] for q in parts] == ["coll_f5"], parts
o = parts[0]["origin_um"]; assert parts[0]["orient"] == "R0"
# content guard: every slot window / reg / site and every start-stage node of coll_f5 stays inside the new outline
xs = []
for s in T["ft_slots"]:
    xs += list(s.get("out_window_um") or [])
    xs += [r[0] for r in s.get("regs_um") or []]
    for b in s.get("bit_sites_um") or []:
        xs += [st[0] for st in b]
for n in p["clock"]["landing_network"]["start_tree"]["provider"]["nodes"]:
    if n.get("clock_region") == "coll_f5":
        xs += [n["rect_um"][0] - o[0], n["rect_um"][2] - o[0]]
for e in T["clock"].get("edge_clocks", []):
    xs.append(e["tap_um"][0])
assert max(xs) < W_NEW - 20.0, max(xs)
T["outline_um"] = [W_NEW, H]
c = T["clock"]
c["tap_um"] = [round(c["tap_um"][0] + DX, 4), c["tap_um"][1]]
# glue tap stays on START node b914 (die 1175.04,12562.4 = frame 397.44,302.4); only its distance to the moved root changes
for t in c.get("taps", []):
    assert t["name"] == "glue" and abs(t["xy"][0] - 397.44) < 1e-6, t
    t["from_root_um"] = round(abs(t["xy"][0] - c["tap_um"][0]) + abs(t["xy"][1] - c["tap_um"][1]), 3)
T["reset"]["tap_um"] = [round(T["reset"]["tap_um"][0] + DX, 4), T["reset"]["tap_um"][1]]
for s in T.get("count_straps", []):
    s["sites_um"] = [[round(x + DX, 4), y] for x, y in s["sites_um"]]
T["note"] += (" | QC-COLLFTN-REFLOOR C1q 11-25 (FABLE rev3 coll_ftn): outline 786.24 -> 432.00 wide, origin kept; "
              "x 432-786 freed as die channel (no logic; carries only the coll_f5<->sl_W5_fw cland monitor seam, gap "
              "354.24 um < 405 hop); clock/reset root 388.8 -> 129.6 over the bus strip (glue tap stays on START node b914 at 397.44, from_root 8.6 -> 267.84), count straps moved "
              "with the tap; bus pins already x-aligned per bus (crec_rx 4.3-118.7 N=S, crec_tx 119.6-233.6 S=N, fltk/fltv "
              "233-239), stations already in-column (rx x61, tx x177, flt x234-238, y 216/432): unchanged. Not 250 um: "
              "the die start-stage spine nodes r914_0/b914 sit at x 395.3-399.6 and the cland monitor to sl_W5_fw "
              "needs E-face gap <= ~380 um; a 250-wide form needs spine re-route + monitor retarget (types slw_fw_v3/coll_ftc)")
x0 = o[0] + W_NEW; x1 = o[0] + W_OLD
for q in p["partitions"]:          # the new channel must be empty
    if q["name"] == "coll_f5": continue
    w, h = p["partition_types"][q["type"]]["outline_um"]
    if q["orient"] in ("R90", "R270", "MXR90", "MYR90"): w, h = h, w
    qx, qy = q["origin_um"]
    assert not (qx < x1 - 1e-6 and qx + w > x0 + 1e-6 and qy < o[1] + H - 1e-6 and qy + h > o[1] + 1e-6), q["name"]
p["die"]["channels"].append({"rect_um": [round(x0, 4), o[1], round(x1, 4), o[1] + H],
    "reason": "QC-COLLFTN-REFLOOR C1q: east part of the old coll_f5 (coll_ftn) slot; coll column width is set by the "
              "786.24 um coll stack, coll_ftn feedthrough content is 0-245 um (+ start-stage spine at 395-400). "
              "Decap/bump field, no logic; die-level route only (coll_f5 cland monitor 3 nets to sl_W5_fw.W)"})
s = json.dumps(p, separators=(",", ":"))
open(dst, "w").write(s)
print("ROW", hashlib.sha256(open(dst, "rb").read()).hexdigest(), "base", hashlib.sha256(open(src, "rb").read()).hexdigest(), "maxx", max(xs))
