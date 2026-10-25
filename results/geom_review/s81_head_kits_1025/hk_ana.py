"""S81-HEAD/KITS placed-kit census: reg->reg > 405 (names), pin->reg, nearest clock-tap sinks, interior M7 pins vs PDN straps."""
import sys, re, json
src = sys.argv[1]
W = H = 0; I = []; P = []
for ln in open(src):
    p = ln.rstrip("\n").split("\t")
    if p[0] == "DIE": W, H = float(p[1]), float(p[2])
    elif p[0] == "I": I.append((p[1], p[2], *map(float, p[3:7])))
    elif p[0] == "P": P.append((p[1], float(p[2]), float(p[3])))
rr = [(float(l.split("\t")[2]), l.split("\t")[1]) for l in open(src + ".hops") if l.startswith("RR")]
pr = [(float(l.split("\t")[2]), l.split("\t")[1]) for l in open(src + ".hops") if l.startswith("PR")]
rr.sort(reverse=True); prv = sorted([x for x in pr if x[0] >= 0], reverse=True)
out = dict(outline=[W, H], rr_n=len(rr), rr_max=rr[0] if rr else None, rr_gt405=sum(x[0] > 405 for x in rr),
           rr_top=[f"{d:.1f} {n}" for d, n in rr[:8]], pin_reg_max=prv[:3], pins_noflop=sum(x[0] < 0 for x in pr))
ff = [((x0 + x1) / 2, (y0 + y1) / 2) for n, m, x0, y0, x1, y1 in I if "DFF" in m or "DHL" in m]
taps = {}
for n, x, y in P:
    if re.match(r"^clk(_t\d+)?$", n): taps[n] = (x, y)
cnt = {t: 0 for t in taps}
for fx, fy in ff:
    if taps:
        t = min(taps, key=lambda k: abs(taps[k][0] - fx) + abs(taps[k][1] - fy)); cnt[t] += 1
inp=[x for x in prv if not re.search(r"(_o\b|_o\[|^clk|^rst_o|^start_o)", x[1])]
out["in_pin_reg_max"] = inp[:3]
out["flops"] = len(ff); out["tap_sinks_nearest"] = cnt
out["tap_zero"] = [t for t, c in cnt.items() if c == 0]
# interior pins (> 1 um from every face) vs kit PDN M7 pair [8.304, 8.976] + k*8.64 (pin half width 0.016)
bad = []
for n, x, y in P:
    if min(x, y, W - x, H - y) > 1.0:
        cx = x + 0.016   # P lines give bbox xMin
        ph = (cx - 8.304) % 8.64
        if ph < 0.672 + 0.016 + 0.05 or ph > 8.64 - 0.016 - 0.05: bad.append(f"{n}@{x:.3f},{y:.3f}")
out["interior_pins_on_strap"] = bad
print(json.dumps(out))
