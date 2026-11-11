#!/usr/bin/env python3
"""CPL-HBM-2 (DO_NOT_COUNT): hand-designed clean-slate arrangements for the HBM SU families (seed for core_place.py).
SU-B (q_su2x/q_su3x): 16 ot_hbm_su_pg_lane1_core in 4 abutted quads (760.32 x 311.04, pins N ~4300 / S ~3750 on M5),
  optional pretree (164.16 x 241.92). Two rows of two quads; outer margins sized from the outer-face pin channel need
  (x1.3), the rest of the height is ONE middle street (the soft/glue area, facing the face windows); all x slack is a
  corridor on the dominant data side (E or W, from netlist face bits) so S/N-margin wires turn to the face windows
  without crossing a quad; pretree in the middle street on the dominant side.
SU-A (q_su0x/q_su1x): 8 lane_exp_x+sfu_s pairs (449.28 x 207.36, pins N ~700 / S ~1000 / side 525), 2 abutted
  lane1p columns (440.64 x 449.28, pins E ~3500 / W ~4500), optional pretree. Data goes mostly to the S face (netlist):
  lane1p columns + pretree sit on the S band under the S face windows (column gap = the E/W channel need x1.2);
  the pairs in rows of up to 4 above them (row street 43.2, pair gap 34.56), rows centred on the S-window centroid.
usage: templates.py PLAN OUT_SEED.json TYPE..."""
import collections
import json
import re
import sys

PIN = 0.048 / (4 * 0.7)
G = 4.32
snap = lambda v: round(round(v / G) * G, 4)
plan, out = sys.argv[1], sys.argv[2]
P = json.load(open(plan))
cc = json.load(open(plan.rsplit("/", 1)[0] + "/core_conns.json"))
seeds = {}


def face_bits(tn, t):
    bus = {b["name"]: b for b in t["buses"]}
    fb = collections.Counter()
    wx = collections.defaultdict(float)
    for inst, ports in (cc.get(tn) or {}).items():
        for pb, tl in ports.items():
            for x in tl:
                if x.startswith("bus:") and x[4:] in bus:
                    b = bus[x[4:]]
                    fb[b["face"]] += 1
                    wn = b.get("window_um") or [0, 0]
                    wx[b["face"]] += (wn[0] + wn[1]) / 2
    cen = {f: wx[f] / fb[f] for f in fb}
    return fb, cen


for tn in sys.argv[3:]:
    t = P["partition_types"][tn]
    W, H = t["outline_um"]
    HC = t["hard_cores"]
    fb, cen = face_bits(tn, t)
    S = {}
    pre = [h for h in HC if "pretree" in h["inst"]]
    if any(h["module"] == "ot_hbm_su_pg_lane1_core" for h in HC):
        quads = collections.OrderedDict()
        for h in HC:
            if h["module"] == "ot_hbm_su_pg_lane1_core":
                quads.setdefault(re.sub(r"__p\d+$", "", h["inst"]), []).append(h)
        qn = list(quads)
        side = "E" if fb["E"] >= fb["W"] else "W"
        qw, qh = 760.32, 311.04
        top_m = snap(4308 * PIN * 1.3 + 8)
        bot_m = snap(3756 * PIN * 1.3 + 8)
        far = 34.56
        inner = 34.56
        x_far = far if side == "E" else snap(W - far - 2 * qw - inner)
        xs = [x_far, snap(x_far + qw + inner)]
        ys = [bot_m, snap(H - top_m - qh)]
        # quad order: keep each quad's members in its own order; the base orient of each member is kept per row
        k = 0
        for r, y in enumerate(ys):
            for c, x in enumerate(xs):
                q = quads[qn[k]]; k += 1
                q = sorted(q, key=lambda h: h["origin_um"][0])
                for j, h in enumerate(q):
                    S[h["inst"]] = dict(origin_um=[snap(x + j * 190.08), y], orient=h.get("orient", "R0"))
        for h in pre:
            pw, ph = h["outline_um"]
            px = snap(W - 34.56 - pw - 60) if side == "E" else snap(34.56 + 60)
            S[h["inst"]] = dict(origin_um=[px, snap(H / 2 - ph / 2)], orient=h.get("orient", "R0"))
        seeds[tn] = dict(cores=S, side=side, face_bits=dict(fb))
        continue
    # SU-A
    pairs = collections.OrderedDict()
    cols = collections.OrderedDict()
    for h in HC:
        if "lane_exp" in h["inst"]:
            pairs.setdefault(re.sub(r"__[ls]$", "", h["inst"]), []).append(h)
        elif "lanes_plain" in h["inst"]:
            cols.setdefault(re.sub(r"__p\d+$", "", h["inst"]), []).append(h)
    sec = "E" if fb["E"] >= fb["W"] else "W"
    scx = cen.get("S", W / 2)
    cw, ch = 440.64, 449.28
    colgap = snap(8064 * PIN * 1.2)
    blk_w = 2 * cw + colgap
    cx0 = min(max(snap(scx - blk_w / 2), snap(4544 * PIN * 1.3)), snap(W - blk_w - 3520 * PIN * 1.3))
    y0 = 60.48
    for c, (nm, mem) in enumerate(cols.items()):
        mem = sorted(mem, key=lambda h: h["origin_um"][1])
        x = snap(cx0 + c * (cw + colgap))
        for j, h in enumerate(mem):
            S[h["inst"]] = dict(origin_um=[x, snap(y0 + j * 112.32)], orient=h.get("orient", "R0"))
    for h in pre:
        pw, ph = h["outline_um"]
        # pretree beside the columns on the secondary-face side
        px = snap(cx0 + blk_w + 60.48) if sec == "E" else snap(cx0 - 60.48 - pw)
        px = min(max(px, 34.56), snap(W - 34.56 - pw))
        S[h["inst"]] = dict(origin_um=[px, y0], orient=h.get("orient", "R0"))
    pw_, ph_ = 449.28, 207.36
    per = max(1, min(4, int((W - 2 * 34.56 + 34.56) // (pw_ + 34.56))))
    rows = [list(pairs.items())[i:i + per] for i in range(0, len(pairs), per)]
    y = snap(y0 + ch + 60.48)
    for row in rows:
        rw = len(row) * pw_ + (len(row) - 1) * 34.56
        x = min(max(snap(scx - rw / 2), 34.56), snap(W - 34.56 - rw))
        for nm, mem in row:
            l = next(h for h in mem if h["inst"].endswith("__l"))
            s_ = next(h for h in mem if h["inst"].endswith("__s"))
            # keep the pair's internal arrangement (sfu on the exp's pin-free side) by translating the pair rigidly
            bx = min(h["origin_um"][0] for h in mem); by = min(h["origin_um"][1] for h in mem)
            for h in mem:
                S[h["inst"]] = dict(origin_um=[snap(x + h["origin_um"][0] - bx), snap(y + h["origin_um"][1] - by)],
                                    orient=h.get("orient", "R0"))
            x = snap(x + pw_ + 34.56)
        y = snap(y + ph_ + 43.2)
    seeds[tn] = dict(cores=S, sec=sec, s_centroid=round(scx, 1), face_bits=dict(fb))
json.dump({k: v["cores"] for k, v in seeds.items()}, open(out, "w"), indent=1)
for k, v in seeds.items():
    print(k, {x: y for x, y in v.items() if x != "cores"}, len(v["cores"]))
