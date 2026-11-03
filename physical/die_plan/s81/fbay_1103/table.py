#!/usr/bin/env python3
"""FIXED-BAY pre-build table for one station kit: bays from ft_stations.txt/pins (type frame), hop timing from hop_table.json.
usage: table.py KIT hop_table.json OUT.tsv [skew_ps] [duty_ps]"""
import sys, json, re, math
K, HT, OUT = sys.argv[1:4]; SKEW = float(sys.argv[4]) if len(sys.argv) > 4 else 30.0; DUTY = float(sys.argv[5]) if len(sys.argv) > 5 else 30.0
ht = {(r["corner"], r["case"]): r for r in json.load(open(HT))}
pins = {}
for ln in open(f"{K}/io.tcl"):
    m = re.search(r"-pin_name \{?(\w+)\[\d+\]\}? .*-location \{([\d.]+) ([\d.]+)\}", ln)
    if m: pins.setdefault(m.group(1), []).append((float(m.group(2)), float(m.group(3))))
cen = {b: (sum(p[0] for p in v) / len(v), sum(p[1] for p in v) / len(v)) for b, v in pins.items()}
rows = []; lanes = []
for ln in open(f"{K}/ft_stations.txt"):
    if ln.startswith("#") or not ln.strip(): continue
    f = ln.split(); s, k = f[0], int(f[1]); a = cen[s + "_i"]; b = cen[s + "_o"]
    L = abs(a[0] - b[0]) + abs(a[1] - b[1]); landed = len(f) == 4
    # bay j (j=0..k-1) at L*j/k from the in face (plan stage); landed: ring at the in face, station i at stage i+1
    pts = [(a[0] + (b[0] - a[0]) * j / k, a[1] + (b[1] - a[1]) * j / k) for j in range(k)] + [b]
    regs = [(float(f[i]), float(f[i + 1])) for i in range(4, len(f), 2)]
    if len(regs) >= k: st = regs[:k]                 # plan regs_um: station j at plan site j (j=0 = in-face register)
    else: st = pts[1:k] + [b] if landed else pts[:k - 1] + [b]
    src = [("ring u_cland_%s_i" % s, a)] if landed else [("port %s_i" % s, a)]
    chain = src + [("%s station s%d" % (s, i), p) for i, p in enumerate(st)]
    lanes.append((s, k, landed, round(L, 1)))
    for (n0, p0), (n1, p1) in zip(chain, chain[1:]):
        h = abs(p0[0] - p1[0]) + abs(p0[1] - p1[1])
        case = "L307" if h <= 307.5 else "L405"
        if h < 1.0:      # face register: IO-budget path (kit contract), not a bay hop
            rows.append(dict(lane=s, frm=n0, to=n1, hop_um=round(h, 1), kind="face (IO budget, unchanged)")); continue
        r = {}
        for form, suf in (("A_lockup", "lk"), ("plain", "ff")):
            tt = ht[("TT", f"{case}_M5_BUFx4_100_{suf}")]; ff = ht[("FF", f"{case}_M5_BUFx4_100_{suf}")]
            sk = SKEW + (DUTY if suf == "lk" else 0)
            r[form] = dict(wirebuf_tt=tt["max_wirebuf_ps"], slew_tt=tt["max_slew_max"], setup_tt=round(tt["wire_max_slack"] - sk, 1),
                           hold_ff=round(ff["wire_min_slack"] - SKEW, 1), bay_hold_ff=ff.get("bay_min_slack"))
        rows.append(dict(lane=s, frm=n0, to=n1, hop_um=round(h, 1), kind="bay hop", reps=tt["nseg"] - 1, **{f"{f}_{x}": v for f, d in r.items() for x, v in d.items()}))
cols = ["lane", "frm", "to", "hop_um", "kind", "reps"] + [f"{f}_{x}" for f in ("A_lockup", "plain") for x in ("wirebuf_tt", "slew_tt", "setup_tt", "hold_ff", "bay_hold_ff")]
with open(OUT, "w") as o:
    o.write(f"# FIXED-BAY pre-build table {K.rstrip('/').split('/')[-1]}: M5 1-um... RCX ladder, BUFx4 every <=100 um (OT_MAXWIRE_UM), skew bound {SKEW} ps (tap window+tol), duty {DUTY} ps on the fall edge (form A)\n")
    o.write("# lanes (slot k landed L_um): " + "; ".join(f"{s} k={k} {'landed' if ld else 'plain'} L={L}" for s, k, ld, L in lanes) + "  -> cycle counts unchanged (form A: neg-level lockup behind each station flop)\n")
    o.write("\t".join(cols) + "\n")
    for r in rows: o.write("\t".join(str(r.get(c, "")) for c in cols) + "\n")
print(open(OUT).read())
