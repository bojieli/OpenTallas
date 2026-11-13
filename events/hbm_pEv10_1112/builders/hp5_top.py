"""DIE-HBM-101 pE1wS2: y 11955.6 spread (b-row top / spt0 boundary).  The heavy word-width slots in the b-row run their
horizontal legs 8-20 um under the partition top edge, so they all land in the boundary gcell rows.  Here each named
slot gets its own die gcell row kb rows below the row holding the partition top edge: every station (regs_um[1:])
with local y > THR moves to that row's centre, 0 cycles; the final leg to an N/E pin becomes vertical.  Bit sites of
moved stages shift by the same dy.  Stations on macros are cleared afterwards by tools/die_plan/ft_nudge.py.
usage: hp5_top.py IN OUT 'partition:slot=kb,...' [THR_local_um=1505]   (partition = instance name, e.g. NW_su00)"""
import json, sys
src, dst, spec = sys.argv[1:4]; thr = float(sys.argv[4]) if len(sys.argv) > 4 else 1505.0
G = 32.4; R = 405.0; CROSS = 195.0
D = json.load(open(src)); T = D["partition_types"]; P = {p["name"]: p for p in D["partitions"]}


def pin(t, face, w):
    W, H = t["outline_um"]; c = (w[0] + w[1]) / 2
    return {"N": [c, H], "S": [c, 0.0], "E": [W, c], "W": [0.0, c]}[face]


worst = 0
for it in spec.split(","):
    k, v = it.split("="); pn, sl = k.split(":"); ronly = (v == "r"); kb = 0 if ronly else int(v)
    p = P[pn]; t = T[p["type"]]; H = t["outline_um"][1]; oy = p["origin_um"][1]
    assert p.get("orient", "R0") in ("R0", "MY"), (pn, p.get("orient"))   # y not flipped
    top_row = int((oy + H - 1e-6) // G); y = round((top_row - kb) * G + G / 2 - oy, 4)
    s = next(x for x in t["ft_slots"] if x["name"] == sl)
    if ronly:      # respace only (same lane family, upstream slot): L path at the E/W pin's y
        a0 = pin(t, s["in_face"], s["in_window_um"]); o0 = pin(t, s["out_face"], s["out_window_um"])
        y = o0[1] if s["out_face"] in ("E", "W") else (a0[1] if s["in_face"] in ("E", "W") else (a0[1] + o0[1]) / 2)
        top_row = int((oy + y) // G); kb = 0
    regs = s["regs_um"]; bs = s.get("bit_sites_um"); moved = 0
    for i in range(1, len(regs)):
        if not ronly and regs[i][1] > thr:
            dy = y - regs[i][1]; regs[i][1] = y; moved += 1
            if bs is not None and len(bs) == len(regs) - 1:
                bs[i - 1] = [[b[0], round(b[1] + dy, 4)] for b in bs[i - 1]]
    if bs is not None and len(bs) != len(regs) - 1:
        for kk in [kk for kk in s if kk.startswith("bit_site")]: s.pop(kk)
    a = pin(t, s["in_face"], s["in_window_um"]); o = pin(t, s["out_face"], s["out_window_um"])
    pts = [a] + regs[1:] + [o]
    hops = [abs(p1[0] - p2[0]) + abs(p1[1] - p2[1]) for p1, p2 in zip(pts, pts[1:])]
    # check.py measures the REAL bit: the first hop must leave room for the in-window span; on E/W outs the lane
    # continues into a neighbour, so the last hop leaves room for the out-window span too (G0 pE1wS2 v1 evidence)
    sp_in = abs(s["in_window_um"][1] - s["in_window_um"][0])
    sp_out = abs(s["out_window_um"][1] - s["out_window_um"][0]) if s["out_face"] in ("E", "W") else 0.0
    # every face crosses into a neighbour whose own hop shares the 405 budget ("via mandatory slot pins"):
    # this slot takes at most CROSS of it on each side (G0 pE1wS3: L5076 432, L8300m 426)
    f_max = min(R - 15 - sp_in, CROSS); l_max = min(R - 15 - sp_out, CROSS)
    if ronly or max(hops) > R - 10 or hops[0] > f_max or hops[-1] > l_max:
        # whole-path respace: in pin -> vertical to row y -> along row y -> vertical to out pin; stations evenly
        # spaced; add stations only if the path needs them (+cycles DECLARED via gen.py latency)
        legs = [(a, [a[0], y]), ([a[0], y], [o[0], y]), ([o[0], y], o)]
        L = sum(abs(p1[0] - p2[0]) + abs(p1[1] - p2[1]) for p1, p2 in legs)
        # hops: first <= f_max, last <= l_max, the middle evenly <= R - 15; keep the station count when it fits
        nh = len(regs)
        while True:
            even = L / nh
            d1 = min(even, f_max); dl = min(even, l_max)
            mid = (L - d1 - dl) / (nh - 2) if nh > 2 else 0.0
            if (nh > 2 and mid <= R - 15) or (nh == 2 and L - d1 <= l_max):
                break
            nh += 1
        add = nh - len(regs)
        cuts = [0.0, d1] + [d1 + mid * k for k in range(1, nh - 1)]   # distance of station k (k = 1..nh-1)

        def at(d):
            for p1, p2 in legs:
                l = abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])
                if d <= l + 1e-9:
                    f = d / l if l else 0
                    return [round(p1[0] + (p2[0] - p1[0]) * f, 4), round(p1[1] + (p2[1] - p1[1]) * f, 4)]
                d -= l
            return list(o)
        old = [list(r) for r in regs]
        new = [regs[0]] + [at(cuts[k]) for k in range(1, nh)]
        if bs is not None and len(bs) == len(old) - 1:
            nbs = []
            for k in range(1, nh):
                j = min(k, len(old) - 1)                        # template group: same stage, else the last one
                dx, dy = new[k][0] - old[j][0], new[k][1] - old[j][1]
                nbs.append([[round(b[0] + dx, 4), round(b[1] + dy, 4)] for b in bs[j - 1]])
            s["bit_sites_um"] = nbs
        s["regs_um"] = new; regs = new
        s["stations"] = s.get("stations", len(old) - 1) + add
        hops = [round(d1 + sp_in), round(mid), round(dl + sp_out)]
        s["note"] = s.get("note", "") + " | path respaced (in -> row -> out), +%d station(s) DECLARED" % add
        print("   respace", pn, sl, "path", round(L), "hops", nh, "+stations", add)
    worst = max(worst, max(hops))
    s["note"] = s.get("note", "") + " | DIE-HBM-101 pE1wS2: top-edge legs on die gcell row %d (local y %g), 0 cycles" % (top_row - kb, y)
    print(pn, p["type"], sl, "row", top_row - kb, "y", y, "moved", moved, "max hop", round(max(hops)), "OVER" if max(hops) > R else "")
D["die"]["label"] = D["die"].get("label", "") + " | DIE-HBM-101 pE1wS2: y 11955.6 spread (%d slots)" % len(spec.split(","))
json.dump(D, open(dst, "w"), indent=1); open(dst, "a").write("\n")
print("worst hop", round(worst))
