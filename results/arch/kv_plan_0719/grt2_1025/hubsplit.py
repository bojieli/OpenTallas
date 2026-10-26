#!/usr/bin/env python3
"""PATH-KV-GRT2 what-if: hub_Wi -> hub_Wo E-W kvs buses L1449/L1450 (hub_Wi ft5/ft6 -> hub_Wo ft2/ft3, 2 x 1118 b at
10.5 b/um in ONE hub_Wi W-face mouth) spread over two host-core-free mouths of hub_Wi (type y 613.44-855.36 and
1555.2-1652) at ~6.6 b/um.  Moves hub_Wi ft5_o/ft6_o (W face) and hub_Wo ft2_i/ft3_i (E face) pins (both R0, same y).
usage: hubsplit.py ABS_DIR OUT_JSON"""
import re, sys, json, collections
from pathlib import Path
AD = Path(sys.argv[1])
pinre = re.compile(r"  PIN (\S+)\[(\d+)\]\n((?:(?!  END ).*\n)*?)  END \1\[\2\]\n")
rectre = re.compile(r"(      LAYER (M\d) ;\n        RECT )([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)( ;)")
A, Bm = (614.4, 854.4), (1556.2, 1652.0)
SETS = {"kv3_hub_Wi_part": ("ft5_o", "ft6_o", "W"), "kv3_hub_Wo_part": ("ft2_i", "ft3_i", "E")}
rep = {}
for m, (b1, b2, face) in SETS.items():
    f = AD / f"{m}.lef"; s = f.read_text(); W = float(re.search(r"SIZE ([\d.]+) BY", s).group(1))
    pins, used = [], collections.defaultdict(set)
    for pm in pinre.finditer(s):
        body = pm.group(0); r = rectre.search(body)
        if not r: continue
        x0, y0, x1, y1 = map(float, r.groups()[2:6])
        onface = (x0 < 0.5) if face == "W" else (x1 > W - 0.5)
        if pm.group(1) in (b1, b2) and onface: pins.append((pm, r, pm.group(1), int(pm.group(2)), y0, y1))
        elif onface: used[r.group(2)].add(round((y0 + y1) / 2, 3))
    pins.sort(key=lambda t: (t[2] != b1, t[3]))
    n = len(pins); nb = round(n * (Bm[1] - Bm[0]) / ((A[1] - A[0]) + (Bm[1] - Bm[0])))
    grpA, grpB = pins[:n - nb], pins[n - nb:]
    repl = {}
    for grp, (lo, hi) in ((grpA, A), (grpB, Bm)):
        for j, (pm, r, bus, bit, y0, y1) in enumerate(grp):
            ln = r.group(2); pitch, off = (0.048, 0.024) if ln in ("M4", "M5") else (0.064, 0.032)
            want = lo + (j + 0.5) * (hi - lo) / len(grp); j0 = round((want - off) / pitch)
            for dd in range(4000):
                y = None
                for jj in (j0 + dd, j0 - dd):
                    c = off + jj * pitch
                    if lo <= c <= hi and round(c, 3) not in used[ln]: y = c; break
                if y is not None: break
            used[ln].add(round(y, 3)); hw = (y1 - y0) / 2; body = pm.group(0)
            nbdy = body[:r.start(4)] + f"{y - hw:.4f}" + body[r.end(4):r.start(6)] + f"{y + hw:.4f}" + body[r.end(6):]
            repl[pm.start()] = (pm.end(), nbdy)
    out, i = [], 0
    for st in sorted(repl): out += [s[i:st], repl[st][1]]; i = repl[st][0]
    out.append(s[i:]); f.write_text("".join(out))
    rep[m] = dict(pins=n, mouthA=len(grpA), mouthB=len(grpB), dens=[round(len(grpA) / (A[1] - A[0]), 2), round(len(grpB) / (Bm[1] - Bm[0]), 2)])
json.dump(rep, open(sys.argv[2], "w"), indent=1); print(json.dumps(rep))
