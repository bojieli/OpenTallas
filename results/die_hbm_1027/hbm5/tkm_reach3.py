#!/usr/bin/env python3
"""DIE-HBM-5 tkm tile_core reach estimate: per input-pin register (u_bin_<bus>/q[k]), flop sinks via buffer-transparent
net BFS on geom.tsv; reach now vs. with the pin moved to x = sink centroid (same face).  usage: tkm_reach2.py GEOM.tsv"""
import re, sys, collections, statistics as st
G = sys.argv[1]
cells, pins, nets, ofc = {}, {}, [], collections.defaultdict(list)
for ln in open(G):
    f = ln.rstrip("\n").split("\t")
    if f[0] == "C":
        cells[int(f[1])] = (f[2], f[-1], (float(f[4]) + float(f[6])) / 2, (float(f[5]) + float(f[7])) / 2)
    elif f[0] == "P":
        pins[f[2]] = (float(f[6]), float(f[7]))
    elif f[0] == "N" and f[1] == "SIGNAL":
        ids = [int(x[1:]) for x in f[2:] if x.startswith("i")]
        nets.append(ids)
for n, ids in enumerate(nets):
    for i in ids:
        ofc[i].append(n)
name2 = {v[1]: k for k, v in cells.items()}
H = 345.6
def sinks(c0):
    seen, q, out = {c0}, [(c0, 0)], []
    while q:
        c, lv = q.pop()
        if lv > 8: continue
        for n in ofc[c]:
            if len(nets[n]) > 64: continue          # reset / high-fanout nets: not the bit datapath
            for d in nets[n]:
                if d in seen: continue
                seen.add(d)
                if cells[d][0] == "S": out.append(d)
                else: q.append((d, lv + 1))
    return out
print("cell kinds", collections.Counter(v[0] for v in cells.values()))
for bus in ("tile_ins_b", "tile_up_in"):
    now, new, lat, cnt = [], [], [], 0
    for nm, (px, py) in pins.items():
        m = re.match(re.escape(bus) + r"\[(\d+)\]$", nm)
        if not m: continue
        k = m[1]; rn = f"u_bin_{bus}/q\\[{k}\\]$_DFF_P_"
        if rn not in name2: continue
        r = name2[rn]; _, _, rx, ry = cells[r]; S = [cells[s] for s in sinks(r) if s != r]
        if not S: continue
        cnt += 1
        cx = st.median(s[2] for s in S); fy = 0.0 if py < 1 else H
        now += [abs(rx - s[2]) + abs(ry - s[3]) for s in S]
        new += [abs(cx - s[2]) + abs(fy - s[3]) for s in S]
        lat.append(max(abs(s[2] - cx) for s in S))
    srt = lambda L: sorted(L)
    print(bus, "regs", cnt, "captures", len(now), "| now max", round(max(now), 1), ">405", sum(d > 405 for d in now),
          "| pin@sink-centroid max", round(max(new), 1), ">405", sum(d > 405 for d in new), "p99", round(srt(new)[int(.99 * len(new))], 1),
          "| sink lateral spread max", round(max(lat), 1))
