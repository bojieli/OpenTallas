"""independent proxy for the ASAP7 M8/M9 wide-metal spacing row on drawn VSS shields: merged same-track-group VSS shields
(overlapping/touching across-axis, along overlap >= 1.8 um) of merged width >= 0.99975 and every OTHER-net clock metal within
1.0 um of that wide part (PRL >= 1.8). shields: off 1.14, half width 0.32, ext per seg; clock half width 0.32."""
import json, sys, collections
m = json.load(open(sys.argv[1])); OFF, HW, SW2 = 1.14, 0.32, 0.32
sh = collections.defaultdict(list); mt = collections.defaultdict(list)
for w in m["fixed_wires"]:
    n = len(w["segs"])
    for (L, x0, y0, x1, y1), mo, e in zip(w["segs"], w.get("shield_modes") or ["drawn"]*n, w.get("shield_ext") or [1.46]*n):
        e = 1.46 if e is None else e
        if L == "M8":   # horizontal: across = y
            c, a0, a1 = y0, min(x0, x1), max(x0, x1)
        else:
            c, a0, a1 = x0, min(y0, y1), max(y0, y1)
        mt[L].append((c - HW, c + HW, a0 - HW, a1 + HW, w["name"]))
        if mo == "drawn":
            for s in (-1, 1):
                sh[L].append((c + s*OFF - SW2, c + s*OFF + SW2, a0 - e, a1 + e))
bad = []; wide = collections.Counter()
for L in sh:
    S = sorted(sh[L])
    for i, a in enumerate(S):
        for b in S[i+1:]:
            if b[0] > a[1] + 1e-6: break
            if abs(b[0]-a[0]) < 1e-6 and abs(b[1]-a[1]) < 1e-6: continue
            lo, hi = max(a[2], b[2]), min(a[3], b[3])
            if hi - lo < 1.8: continue
            wdt = max(a[1], b[1]) - min(a[0], b[0])
            if wdt >= 0.99975 - 1e-9:
                wide[L] += 1; bad.append((L, round(min(a[0], b[0]), 3), round(max(a[1], b[1]), 3), round(lo, 2), round(hi, 2)))
# clock metal near wide part
M = {L: sorted(mt[L]) for L in mt}
viol = []
for L, c0, c1, lo, hi in bad:
    for t in M[L]:
        if t[0] > c1 + 1.0: break
        if t[1] < c0 - 1.0: continue
        gp = max(t[0]-c1, c0-t[1]); prl = min(hi, t[3]) - max(lo, t[2])
        if gp < 1.0 - 1e-6 and prl >= 1.8: viol.append((L, t[4], round(gp, 3), c0, c1, lo, hi))
print(json.dumps(dict(wide_vss_pairs=dict(wide), metal_viol=len(viol), viol_nets=sorted({v[1] for v in viol})[:20], sample=viol[:6])))
