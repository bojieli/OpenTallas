import json, sys
d = json.load(open(sys.argv[1])); T = d["partition_types"]
used = {p["type"] for p in d["partitions"]}
def R(c): x, y = c["origin_um"]; w, h = c["outline_um"]; return (x, y, x + w, y + h)
def ov(a, b): return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
def inside(p, r, e=0.5): return r[0] + e < p[0] < r[2] - e and r[1] + e < p[1] < r[3] - e
tot = {"hh": 0, "out": 0, "st_in_hard": 0, "ft_in_hard": 0, "sh": 0}
for tn in sorted(used):
    t = T[tn]; W, H = t["outline_um"]
    hc = [(c["inst"], R(c)) for c in t.get("hard_cores", [])]
    sc = [(c["inst"], R(c)) for c in t.get("contents", []) if "origin_um" in c and "outline_um" in c and c.get("status") != "hard"]
    hh = [(a[0], b[0], round(ov(a[1], b[1]))) for i, a in enumerate(hc) for b in hc[i + 1:] if ov(a[1], b[1]) > 1]
    out = [n for n, r in hc if r[0] < -0.5 or r[1] < -0.5 or r[2] > W + 0.5 or r[3] > H + 0.5]
    hnames = {n for n, _ in hc}
    sh = [(s[0], h[0], round(ov(s[1], h[1]))) for s in sc if s[0] not in hnames for h in hc if ov(s[1], h[1]) > 100]
    sti = sum(1 for s in t.get("internal_stations", []) for p in s.get("regs_um", []) if any(inside(p, r) for _, r in hc))
    fti = sum(1 for s in t.get("ft_slots", []) for p in s.get("regs_um", []) if any(inside(p, r) for _, r in hc))
    ha = sum((r[2] - r[0]) * (r[3] - r[1]) for _, r in hc)
    ymax = max([r[3] for _, r in hc] + [0]); ymin = min([r[1] for _, r in hc] + [H])
    xmax = max([r[2] for _, r in hc] + [0]); xmin = min([r[0] for _, r in hc] + [W])
    flag = []
    if hh: flag.append(f"HARD-OVERLAP {len(hh)} e.g. {hh[:2]}")
    if out: flag.append(f"OUTSIDE {out[:3]}")
    if sh: flag.append(f"SOFT/HARD overlap {len(sh)} e.g. {sh[:2]}")
    if sti: flag.append(f"stations in hard {sti}")
    if fti: flag.append(f"ft regs in hard {fti}")
    print(f"{tn:10s} {W:8.1f}x{H:8.1f} hard {len(hc):3d} fill {ha/(W*H):.2f} bbox x[{xmin:.0f},{xmax:.0f}] y[{ymin:.0f},{ymax:.0f}] cells {t.get('cells')} " + " | ".join(flag))
    tot["hh"] += len(hh); tot["out"] += len(out); tot["sh"] += len(sh); tot["st_in_hard"] += sti; tot["ft_in_hard"] += fti
print(tot)
