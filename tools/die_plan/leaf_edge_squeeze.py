#!/usr/bin/env python3
# S81-LEAF-PLAN B5: edge ft squeeze per leaf type: bits of N<->S ft slots with a register within 60 um of the W/E edge,
# and the narrowest edge strip (edge -> first core, cores overlapping the y span of those registers).  PLAN [TYPES_FILE]
import json, sys
P = json.load(open(sys.argv[1]))["partition_types"]
only = set(open(sys.argv[2]).read().split()) if len(sys.argv) > 2 else None


def ext(h):
    o = h["origin_um"]; d = h["outline_um"]; r = h.get("orient", "R0")
    w, hh = (d[1], d[0]) if r in ("R90", "R270", "MXR90", "MYR90") else d
    return o[0], o[1], o[0] + w, o[1] + hh


out = {}
for tn, t in P.items():
    if only is not None and tn not in only:
        continue
    if not tn.startswith(("ot_s81sl_leaf__", "ot_s81sl_kv_leaf__")) or not t.get("hard_cores"):
        continue
    W = t["outline_um"][0]
    for face in "WE":
        e = (lambda x: x) if face == "W" else (lambda x: W - x)
        bits, ys = 0, []
        for f in t.get("ft_slots") or []:
            rr = [r for r in f.get("regs_um") or [] if e(r[0]) < 60]
            if f["in_face"] in "NS" and rr:
                bits += int(f["width"]); ys += [r[1] for r in rr]
        if not bits:
            continue
        y0, y1 = min(ys), max(ys)
        strip = min([(c[0] if face == "W" else W - c[2]) for c in map(ext, t["hard_cores"]) if c[1] < y1 and c[3] > y0] or [W])
        out[(tn, face)] = (bits, round(strip, 1), round(bits / max(strip, 1e-3), 1))
for k, v in sorted(out.items(), key=lambda kv: -kv[1][2]):
    print("%-36s %s bits %5d strip %6.1f  %6.1f bits/um" % (k[0], k[1], *v))
