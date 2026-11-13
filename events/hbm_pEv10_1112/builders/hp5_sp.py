"""DIE-HBM-101 hp5b: 0-cycle respace of the turnaround slots' out leg.  Keeps regs[0..1] and the station count;
places regs[2..] evenly along the path regs[1] -> (horizontal at the row y) -> out pin (vertical last), so the
last-station -> out-pin hop no longer exceeds reach.  Bit-site groups follow their station by translation.
usage: hp5_sp.py IN OUT 'type:slot,...'"""
import json, sys
src, dst, spec = sys.argv[1:4]
D = json.load(open(src)); T = D["partition_types"]


def pin(t, face, w):
    W, H = t["outline_um"]; c = (w[0] + w[1]) / 2
    return {"N": [c, H], "S": [c, 0.0], "E": [W, c], "W": [0.0, c]}[face]


for it in spec.split(","):
    tn, sl = it.split(":"); t = T[tn]; s = next(x for x in t["ft_slots"] if x["name"] == sl)
    regs = s["regs_um"]; o = pin(t, s["out_face"], s["out_window_um"]); a = regs[1]; ry = a[1]
    hx = abs(o[0] - a[0]); vy = abs(o[1] - ry); L = hx + vy; n = len(regs) - 1  # hops regs[1]->...->pin
    sx = 1 if o[0] >= a[0] else -1; sy = 1 if o[1] >= ry else -1
    bs = s.get("bit_sites_um"); old = [list(p) for p in regs]
    for k in range(2, len(regs)):
        d = L * (k - 1) / n
        q = [a[0] + sx * d, ry] if d <= hx else [o[0], ry + sy * (d - hx)]
        regs[k] = [round(v, 4) for v in q]
        if bs is not None and len(bs) == len(regs) - 1:
            dx, dy = regs[k][0] - old[k][0], regs[k][1] - old[k][1]
            bs[k - 1] = [[round(r[0] + dx, 4), round(r[1] + dy, 4)] for r in bs[k - 1]]
    if bs is not None and len(bs) != len(regs) - 1:
        for kk in [kk for kk in s if kk.startswith("bit_site")]: s.pop(kk)
    s["note"] = s.get("note", "") + " | DIE-HBM-101 hp5b: out leg respaced evenly (0 cycles)"
    print(tn, sl, "leg", round(L), "/", n, "=", round(L / n))
D["die"]["label"] = D["die"].get("label", "") + " | DIE-HBM-101 hp5b: 0-cycle out-leg respace on %d turnarounds" % len(spec.split(","))
json.dump(D, open(dst, "w"), indent=1); open(dst, "a").write("\n")
