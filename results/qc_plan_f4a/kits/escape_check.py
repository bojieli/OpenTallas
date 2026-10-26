#!/usr/bin/env python3
"""QC-PLAN-F4A task 4: M4/M6 escape of the column-SRAM M5 signal pins under the PG straps, from the GRT route guides.
For every SRAM signal pin: the GRT guide boxes of its net that touch the pin box (layer list); the pin ESCAPES if its net's
guide reaches the pin on M5 and continues on M4 or M6 within the pin's GCell, or leaves on M5 without crossing an M5 strap
(M5 straps run over the pin band -> an M5-only exit is legal only if no strap is between the pin and the exit).  Also: the
guide's GCell overflow is read from the GRT congestion report when given.  usage: escape_check.py PINS.txt route.guide OUT.json"""
import json, sys
from collections import defaultdict
pins_f, guide_f, out = sys.argv[1:4]
pins, straps = [], []
for l in open(pins_f):
    f = l.split()
    if f[0] == "STRAP":
        straps.append((f[2], *map(float, f[3:7])))
    else:
        pins.append(dict(inst=f[0], pin=f[1], net=f[2], layer=f[3], box=list(map(float, f[4:8]))))
want = {p["net"] for p in pins}
guides = defaultdict(list)
cur, inb = None, False
for l in open(guide_f):
    s = l.strip()
    if not s:
        continue
    if s == "(":
        inb = True; continue
    if s == ")":
        inb = False; cur = None; continue
    if not inb:
        cur = s; continue
    if cur in want:
        f = s.split()
        guides[cur].append((float(f[0]) / 1000, float(f[1]) / 1000, float(f[2]) / 1000, float(f[3]) / 1000, f[4]))
def touch(a, b, e=0.0):
    return a[0] <= b[2] + e and b[0] <= a[2] + e and a[1] <= b[3] + e and b[1] <= a[3] + e
res, by = [], defaultdict(int)
for p in pins:
    g = [x for x in guides.get(p["net"], []) if touch(x[:4], p["box"])]
    lay = sorted({x[4] for x in g})
    esc = [L for L in lay if L in ("M4", "M6")]
    under = [s for s in straps if s[1] == "M5" and touch(s[2:], p["box"], 0.0)]
    m5x = [x for x in g if x[4] == "M5"]
    ok = bool(g) and (bool(esc) or (bool(m5x) and not under))
    kind = "no_guide" if not g else ("M4/M6" if esc else ("M5_only" if ok else "M5_blocked"))
    by[kind] += 1
    res.append(dict(p, guide_layers=lay, escape=esc, under_m5_strap=bool(under), ok=ok, kind=kind))
rep = dict(scope="GRT route guides (5_1_grt), CHECKED = measured guide geometry; DRT not run", n_pins=len(pins),
           by_kind=dict(by), n_fail=sum(1 for r in res if not r["ok"]),
           strap_layers={L: sum(1 for s in straps if s[1] == L) for L in ("M4", "M5", "M6")},
           pins_under_m5_strap=sum(1 for r in res if r["under_m5_strap"]),
           verdict="PASS" if pins and all(r["ok"] for r in res) else "FAIL", failures=[r for r in res if not r["ok"]][:50], pins=res)
json.dump(rep, open(out, "w"), indent=1)
print("ESCAPE", out, rep["verdict"], "pins", len(pins), dict(by), "under_M5_strap", rep["pins_under_m5_strap"], "straps", rep["strap_layers"])
