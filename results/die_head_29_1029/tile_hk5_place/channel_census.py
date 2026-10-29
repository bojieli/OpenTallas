"""DIE-HEAD-29: std-cell census per region of an AUTO-GEOM dump (geom.tsv).  usage: channel_census.py GEOM_TSV"""
import collections, re, sys
cells = []
for l in open(sys.argv[1]):
    if l.startswith("C\t"):
        f = l.rstrip("\n").split("\t")
        cells.append((f[2], f[3], *map(float, f[4:8]), f[8]))
tot = sum(1 for c in cells if c[0] != "M")
grp = lambda nm: "(anon comb)" if nm.startswith("_") else ".".join(re.sub(r"\[\d+\]", "[]", nm.replace("\\", "")).split(".")[:3])
reg = {"channel y700-735": (0, 700, 708, 735), "Wband x<216 y>735": (0, 735, 216, 1036), "Eband x>500 y>735": (500, 735, 708, 1036),
       "vstreet x345-385 y<700": (345, 0, 385, 700), "midstreet y325-382": (0, 325, 708, 382)}
for rn, (a, b, cc, d) in reg.items():
    sel = [c for c in cells if c[0] != "M" and a <= (c[2] + c[4]) / 2 < cc and b <= (c[3] + c[5]) / 2 < d]
    area = sum((c[4] - c[2]) * (c[5] - c[3]) for c in sel)
    print(f"{rn}: cells {len(sel)} ({len(sel)/tot:.1%}) ff {sum("DFF" in c[1] for c in sel)} area {area:.0f} um2 "
          f"util {area/((cc-a)*(d-b)):.3f}", collections.Counter(grp(c[6]) for c in sel).most_common(5))
