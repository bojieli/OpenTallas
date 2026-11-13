"""DIE-HBM-101 hp5a: one station on the in-pin -> stage-1 hop of the named slots (+1 cycle each, DECLARED via
gen.py latency).  Station 0 is the in pin (check.py); the new stage-1 sits at the Manhattan midpoint of pin -> old
stage 1 on a vertical-then-horizontal path.  Bit sites: the old stage-1 group translated to the new point.
usage: hp5_s1.py IN OUT 'type:slot,...'"""
import json, sys
src, dst, spec = sys.argv[1:4]
D = json.load(open(src)); T = D["partition_types"]


def pin(t, face, w):
    W, H = t["outline_um"]; c = (w[0] + w[1]) / 2
    return {"N": [c, H], "S": [c, 0.0], "E": [W, c], "W": [0.0, c]}[face]


for it in spec.split(","):
    tn, sl = it.split(":"); t = T[tn]; s = next(x for x in t["ft_slots"] if x["name"] == sl)
    regs = s["regs_um"]; a = pin(t, s["in_face"], s["in_window_um"]); b = regs[1]
    tot = abs(a[0] - b[0]) + abs(a[1] - b[1]); h = tot / 2; vy = abs(b[1] - a[1])
    sy = 1 if b[1] >= a[1] else -1; sx = 1 if b[0] >= a[0] else -1
    q = [a[0], a[1] + sy * h] if h <= vy else [a[0] + sx * (h - vy), b[1]]
    q = [round(v, 4) for v in q]
    bs = s.get("bit_sites_um")
    if bs is not None and len(bs) == len(regs) - 1:
        dx, dy = q[0] - b[0], q[1] - b[1]
        bs.insert(0, [[round(r[0] + dx, 4), round(r[1] + dy, 4)] for r in bs[0]])
    elif bs is not None:
        for kk in [kk for kk in s if kk.startswith("bit_site")]: s.pop(kk)
    regs.insert(1, q); s["stations"] = s.get("stations", len(regs) - 1) + 1
    s["note"] = s.get("note", "") + " | DIE-HBM-101 hp5a: +1 station on the in-pin hop (+1 cycle, DECLARED)"
    print(tn, sl, "hop", round(tot), "-> 2 x", round(h), "q", q)
D["die"]["label"] = D["die"].get("label", "") + " | DIE-HBM-101 hp5a: +1 station on %d turnaround in-pin hops" % len(spec.split(","))
json.dump(D, open(dst, "w"), indent=1); open(dst, "a").write("\n")
