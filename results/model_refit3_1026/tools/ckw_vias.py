#!/usr/bin/env python3
"""MODEL-REFIT-3: same table from an F4A ck_wires dump (W net layer x0 y0 x1 y1 / VIA net x y). usage: ckw_vias.py CKW OUT.tsv"""
import sys
src, out = sys.argv[1:3]; nets = {}
for ln in open(src):
    f = ln.split()
    if not f: continue
    if f[0] == "W":
        v = nets.setdefault(f[1], dict(vias=0, wire={})); x0, y0, x1, y1 = map(float, f[3:7])
        v["wire"][f[2]] = v["wire"].get(f[2], 0) + abs(x1 - x0) + abs(y1 - y0)
    elif f[0] == "VIA":
        nets.setdefault(f[1], dict(vias=0, wire={}))["vias"] += 1
with open(out, "w") as fo:
    fo.write("#net\tvias\twire_um\t" + "\t".join(f"M{i}" for i in range(1, 10)) + "\n")
    for n, v in sorted(nets.items()):
        fo.write(f"{n}\t{v['vias']}\t{sum(v['wire'].values()):.2f}\t" + "\t".join(f"{v['wire'].get(f'M{i}', 0):.2f}" for i in range(1, 10)) + "\n")
print("nets", len(nets))
