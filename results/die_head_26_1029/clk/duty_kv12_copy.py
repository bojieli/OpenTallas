"""DIE-KV-12 duty readout (COORD 08:43 (b)): per tap high pulse = T/2 + k_spice * (fall_arr - rise_arr) from the combo GRT0
STA (root driven by vclk, both edges), target 45-55 % at every tap; MPW estimate = ASAP7 DFFHQNx1 TT lib min_pulse_width at
the tap slew (same table as DIE-QC-11 duty_eval.py); plus the structural polarity of every tap (inverting stages root->tap
in ctree.v must be even).  usage: kv12_duty.py CTREE_V DUTY_TT DUTY_FF OUT.json"""
import json
import re
import statistics
import sys

T = 833.333
K = {"TT": 1.0485, "FF": 1.0552}
IDX = [5, 10, 20, 40, 80, 160, 320]
MPW = [39.99, 42.25, 42.25, 45.32, 80.57, 161.13, 321.05]


def mpw(slew):
    if slew <= IDX[0]:
        return MPW[0]
    for i in range(len(IDX) - 1):
        if slew <= IDX[i + 1]:
            f = (slew - IDX[i]) / (IDX[i + 1] - IDX[i])
            return MPW[i] + f * (MPW[i + 1] - MPW[i])
    return MPW[-1]


cv, ftt, fff, outp = sys.argv[1:5]
# structural polarity: net -> driver (cell, input net)
drv = {}
for m in re.finditer(r"(\w+_ASAP7_75t_R)\s+(\w+)\s*\(\s*\.A\((\w+)\)\s*,\s*\.Y\((\w+)\)\s*\)", open(cv).read()):
    drv[m.group(4)] = (m.group(1), m.group(3))
assigns = dict((b, a) for b, a in re.findall(r"assign\s+(\w+)\s*=\s*(\w+)\s*;", open(cv).read()))


def parity(net):
    n, inv, st = net, 0, 0
    while True:
        if n in assigns:
            n = assigns[n]
            continue
        if n not in drv:
            return inv, st, n
        c, a = drv[n]
        st += 1
        inv += c.startswith(("INV", "CKINV"))
        n = a


out = dict(rule="COORD 08:43: duty 45-55 % at every tap (both edges, spice-scaled); lib MPW both phases", corners={})
pol = None
for c, f in (("TT", ftt), ("FF", fff)):
    rows = []
    for ln in open(f):
        x = ln.split()
        if x and x[0] == "D":
            d = K[c] * (float(x[3]) - float(x[2]))
            hi = T / 2 + d
            lo = T - hi
            m = mpw(max(float(x[4]), float(x[5])))
            rows.append((hi / T, x[1], hi, lo, m, d / K[c]))
    if pol is None:
        pp = {r[1]: parity(r[1]) for r in rows}
        odd = sorted(p for p, v in pp.items() if v[0] % 2)
        roots = sorted(set(v[2] for v in pp.values()))
        st = [v[1] for v in pp.values()]
        pol = dict(taps=len(pp), odd_parity_taps=len(odd), odd_first=odd[:5], roots=roots,
                   stages_med=statistics.median(st), stages_max=max(st))
    du = [r[0] for r in rows]
    fr = [r[5] for r in rows]
    bad = [r for r in rows if not 0.45 <= r[0] <= 0.55]
    mf = [r for r in rows if min(r[2], r[3]) < r[4]]
    out["corners"][c] = dict(taps=len(rows), fall_minus_rise_ps=dict(min=round(min(fr), 1), med=round(statistics.median(fr), 1),
                                                                      max=round(max(fr), 1)),
                             duty_min=round(min(du), 4), duty_med=round(statistics.median(du), 4), duty_max=round(max(du), 4),
                             outside_45_55=len(bad), mpw_est_fail=len(mf),
                             worst=[dict(port=r[1], duty=round(r[0], 4), high_ps=round(r[2], 1), low_ps=round(r[3], 1),
                                         mpw_ps=round(r[4], 1)) for r in sorted(rows, key=lambda r: -abs(r[0] - 0.5))[:5]])
out["polarity"] = pol
json.dump(out, open(outp, "w"), indent=1)
print(json.dumps(pol))
for c, v in out["corners"].items():
    print(c, json.dumps({k: v[k] for k in v if k != "worst"}), "worst", v["worst"][0])
