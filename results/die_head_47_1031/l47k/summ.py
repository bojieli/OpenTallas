"""DIE-HEAD-47: per-region routed (DRT + OpenRCX) vs GRT clock spread and routed/Manhattan detour ratio.
Spread = max-min of tap RISE late arrivals inside the region (nominal, no OCV / no spice factor: OWNER 12.24b)."""
import json, sys, statistics
R = "/srv/opentallas-scratch2/claude/die-head-47/drt"; REC = "/srv/opentallas-scratch2/claude/die-head-46/clk"
out = {}
def arr(f):
    d = {}
    for l in open(f):
        x = l.split()
        if x and x[0] == "T": d[x[1]] = (float(x[2]), float(x[4]))
    return d
for r in ("tW3b5", "tW1o1", "tW1o8"):
    D = f"{R}/r6_{r}"; o = {}
    for C in ("TT", "FF"):
        rec = arr(f"{REC}/out_l46aa405_{C}/arr_{C}.txt")
        g = arr(f"{D}/out/arr_GRT_TT.txt") if C == "TT" else None
        try: x = arr(f"{D}/out/arr_RCX_{C}.txt")
        except FileNotFoundError: x = None
        taps = sorted(k for k in (x or g or {}) if k.startswith("t_"))
        e = {}
        rr = [rec[t][0] for t in taps]; e["record_grt_spread"] = round(max(rr) - min(rr), 2)
        if g: gg = [g[t][0] for t in taps]; e["crop_grt_spread"] = round(max(gg) - min(gg), 2)
        if x:
            xx = [x[t][0] for t in taps]; e["routed_rcx_spread"] = round(max(xx) - min(xx), 2)
            hi = max(taps, key=lambda t: x[t][0]); lo = min(taps, key=lambda t: x[t][0]); e["worst_pair"] = [hi, lo]
            e["routed_max_slew"] = round(max(x[t][1] for t in taps), 1)
            e["routed_minus_crop_grt_mean_ps"] = round(statistics.mean(x[t][0] for t in taps) - statistics.mean(g[t][0] for t in taps), 2) if g else None
        o[C] = e
    L = [l.split() for l in open(f"{D}/out/len_DRT2.txt")] if __import__("os").path.exists(f"{D}/out/len_DRT2.txt") else []
    if L:
        rows = [(n, int(p), float(h) / 1000, float(w) / 1000) for _, n, p, h, w in L if float(h) > 0 and float(w) > 0]
        rat = sorted(w / h for _, _, h, w in rows)
        o["detour"] = dict(nets=len(rows), sum_routed_um=round(sum(w for *_, w in rows), 1), sum_manhattan_um=round(sum(h for _, _, h, _ in rows), 1),
                           ratio_total=round(sum(w for *_, w in rows) / sum(h for _, _, h, _ in rows), 3),
                           ratio_p50=round(rat[len(rat) // 2], 3), ratio_p90=round(rat[int(len(rat) * .9)], 3), ratio_max=round(rat[-1], 3),
                           worst=sorted(rows, key=lambda x: -x[3] / x[2])[:3])
    try:
        o["drc"] = sum(1 for l in open(f"{D}/out/drt_drc.rpt") if l.startswith("violation") or "violation type" in l)
    except FileNotFoundError: o["drc"] = None
    out[r] = o
print(json.dumps(out, indent=1))
json.dump(out, open(f"{R}/summary.json", "w"), indent=1)
