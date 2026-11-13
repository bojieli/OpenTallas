"""DIE-HBM-101: post-nudge reach repair on named slots.  ft_nudge slides stations off macros (up to ~150 um), which
can push a respaced station-to-station hop over reach (G0 pEv2: L8300x3 490, L5076x4 441).  For every named slot:
walk in pin -> regs[1:] -> out pin in the type frame; any hop > LIM gets one station at its Manhattan midpoint
(vertical-then-horizontal), +1 cycle each, DECLARED via gen.py latency.  Bit sites: the group of the hop's far
station, translated to the new point.  Prints the number of inserts; 0 means the slot is clean.  Run, ft_nudge,
repeat until 0.
usage: hop_split.py IN OUT 'partition:slot,...' [LIM=395]"""
import json, sys
src, dst, spec = sys.argv[1:4]; LIM = float(sys.argv[4]) if len(sys.argv) > 4 else 395.0
D = json.load(open(src)); T = D["partition_types"]; P = {p["name"]: p for p in D["partitions"]}


def pin(t, face, w):
    W, H = t["outline_um"]; c = (w[0] + w[1]) / 2
    return {"N": [c, H], "S": [c, 0.0], "E": [W, c], "W": [0.0, c]}[face]


total = 0
for it in spec.split(","):
    pn, sl = it.split(":"); t = T[P[pn]["type"]]
    s = next(x for x in t["ft_slots"] if x["name"] == sl)
    a = pin(t, s["in_face"], s["in_window_um"]); o = pin(t, s["out_face"], s["out_window_um"])
    regs = s["regs_um"]; bs = s.get("bit_sites_um"); n = 0
    i = 1
    while i <= len(regs):                       # hop i: point(i-1) -> point(i); point(0) = in pin, point(len) = out
        p0 = a if i == 1 else regs[i - 1]
        p1 = o if i == len(regs) else regs[i]
        d = abs(p0[0] - p1[0]) + abs(p0[1] - p1[1])
        if d > LIM and i < len(regs):           # the last leg to the out pin is left to the cross-face check
            h = d / 2; vy = abs(p1[1] - p0[1]); sy = 1 if p1[1] >= p0[1] else -1; sx = 1 if p1[0] >= p0[0] else -1
            q = [p0[0], p0[1] + sy * h] if h <= vy else [p0[0] + sx * (h - vy), p1[1]]
            q = [round(v, 4) for v in q]
            if bs is not None and len(bs) == len(regs) - 1:
                g = bs[i - 1]; dx, dy = q[0] - p1[0], q[1] - p1[1]
                bs.insert(i - 1, [[round(b[0] + dx, 4), round(b[1] + dy, 4)] for b in g])
            regs.insert(i, q); n += 1
            print("  ", pn, sl, "hop", i, round(d), "-> 2 x", round(h))
            continue                            # re-check the first half
        i += 1
    if n:
        s["stations"] = s.get("stations", len(regs) - 1 - n) + n
        s["note"] = s.get("note", "") + " | DIE-HBM-101 hop_split: +%d station(s) after ft_nudge (DECLARED)" % n
    total += n
json.dump(D, open(dst, "w"), indent=1); open(dst, "a").write("\n")
print("inserted", total)
