#!/usr/bin/env python3
"""DIE-HBM-36 V-A turn probe: copy a probe dir (va12) and add NT synthetic bits that enter the type E face at y in
[YE0, YE1] and leave the N face at x in [XN0, XN1] (free M4/M6 E tracks, free M5/M7 N tracks, interleaved with the
existing pins, <= 12 pins/um), each an L route (west along y, then north) with station flops every <= 390 um (st0 beside
the in pin).  Diagnostic only.  usage: va_turn.py SRC DST NT YE0 YE1 XN0 XN1"""
import sys, re, shutil, json, math
src, dst, NT = sys.argv[1], sys.argv[2], int(sys.argv[3])
YE0, YE1, XN0, XN1 = map(float, sys.argv[4:8])
shutil.copytree(src, dst)
W, H = json.load(open(src + "/probe.json"))["outline_um"]
TR = {"M4": (0.024, 0.048, "0.1920 0.0240"), "M6": (0.032, 0.064, "0.1920 0.0320"),
      "M5": (0.024, 0.048, "0.0240 0.1920"), "M7": (0.032, 0.064, "0.0320 0.1920")}
used = {}
for ln in open(src + "/io.tcl"):
    m = re.search(r"-layer (M\d) -location \{([\d.]+) ([\d.]+)\}", ln)
    if not m or m[1] not in TR: continue
    x, y = float(m[2]), float(m[3])
    o, p, _ = TR[m[1]]
    if x > W - 1: used.setdefault(("E", m[1]), set()).add(round((y - o) / p))
    if y > H - 1: used.setdefault(("N", m[1]), set()).add(round((x - o) / p))
def pick(f, L, v):
    o, p, _ = TR[L]; u = used.setdefault((f, L), set()); k = round((v - o) / p)
    for d in range(400):
        for kk in (k + d, k - d):
            if all(kk + e not in u for e in (-1, 0, 1)):
                u.add(kk); return o + kk * p
    raise SystemExit(f"no track {f} {L} {v}")
io, cells, wires, place = [], [], [], []
for b in range(NT):
    ye = pick("E", "M4" if b % 2 else "M6", YE0 + (b + 0.5) * (YE1 - YE0) / NT)
    # bits entering higher on E leave further west on N (no crossing): order reversed
    LN = "M5" if b % 2 else "M7"
    xn = pick("N", LN, XN1 - (b + 0.5) * (XN1 - XN0) / NT)
    LE = "M4" if b % 2 else "M6"
    io.append(f"place_pin -pin_name {{VT_i[{b}]}} -layer {LE} -location {{{W - 0.096:.4f} {ye:.4f}}} -pin_size {{{TR[LE][2]}}}")
    io.append(f"place_pin -pin_name {{VT_o[{b}]}} -layer {LN} -location {{{xn:.4f} {H - 0.096:.4f}}} -pin_size {{{TR[LN][2]}}}")
    L1, L2 = (W - 2.0) - xn, (H - 2.0) - ye
    tot = L1 + L2; k = max(2, math.ceil(tot / 390.0) + 1)
    prev = f"VT_i[{b}]"
    for j in range(k):
        t = tot * j / (k - 1) if k > 1 else 0
        x, y = ((W - 2.0 - t, ye) if t <= L1 else (xn, ye + (t - L1)))
        x = min(max(x, 4.4), W - 5.5); y = min(max(y, 4.4), H - 4.7)
        last = j == k - 1
        q = f"VT_o[{b}]" if last else f"nvt_{b}_{j}"
        if not last: wires.append(q)
        cells.append(f"  DFFHQNx1_ASAP7_75t_R vt_{b}_{j} (.D({prev}), .QN({q}));")
        place.append((f"vt_{b}_{j}", x, y)); prev = q
with open(dst + "/io.tcl", "a") as fh:
    fh.write("# DIE-HBM-36 V-A synthetic turn bits E->N\n" + "\n".join(io) + "\n")
v = open(src + "/probe.v").read(); i = v.index(");\n")
v = v[:i] + f",\n  input [{NT - 1}:0] VT_i,\n  output [{NT - 1}:0] VT_o" + v[i:]
v = v.replace("endmodule", "\n".join(f"  wire {w};" for w in wires) + "\n" + "\n".join(cells) + "\nendmodule")
open(dst + "/probe.v", "w").write(v)
t = open(src + "/probe.tcl").read()
t = t.replace("detailed_placement -max_displacement", "\n".join(f"place_inst -name {c} -location {{{x:.3f} {y:.3f}}} -status PLACED" for c, x, y in place) + "\ndetailed_placement -max_displacement", 1)
open(dst + "/probe.tcl", "w").write(t)
pj = json.load(open(src + "/probe.json")); pj.update(vt_bits=NT, vt_e=[YE0, YE1], vt_n=[XN0, XN1], pins=pj["pins"] + 2 * NT, flops=pj["flops"] + len(place))
json.dump(pj, open(dst + "/probe.json", "w"), indent=1)
open(dst + "/run.sh", "w").write(open(src + "/run.sh").read())
print("turn bits", NT, "flops", len(place))
