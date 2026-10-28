"""DIE-QC-11 duty readout (COORD 08:4x): per tap high pulse = T/2 + k_spice*(fall_arr - rise_arr) from the clock-only GRT
STA (both edges propagated); duty target 45-55 % at every tap; MPW = ASAP7 SEQ RVT DFF min_pulse_width (lib, interpolated
on the tap slew; worst of rise/fall constraint over the DFFHQNx1 'when' arcs).  usage: duty_eval.py ARR_TT ARR_FF OUT.json"""
import json, sys, statistics
T = 833.0
K = {"TT": 1.0485, "FF": 1.0552}           # data/asap7_bufx24_spice_cal.json clock scale
IDX = [5, 10, 20, 40, 80, 160, 320]
MPW = {"TT": [39.99, 42.25, 42.25, 45.32, 80.57, 161.13, 321.05]}   # DFFHQNx1 TT worst arc (lib 220123), conservative for FF


def mpw(slew, c):
    v = MPW.get(c, MPW["TT"])
    if slew <= IDX[0]:
        return v[0]
    for i in range(len(IDX) - 1):
        if slew <= IDX[i + 1]:
            f = (slew - IDX[i]) / (IDX[i + 1] - IDX[i])
            return v[i] + f * (v[i + 1] - v[i])
    return v[-1]


out = {}
for c, f in (("TT", sys.argv[1]), ("FF", sys.argv[2])):
    rows = []
    slew = {}
    for l in open(f):
        x = l.split()
        if x and x[0] == "T":
            slew[x[1]] = float(x[4])
    for l in open(f):
        x = l.split()
        if x and x[0] == "F":
            d = K[c] * (float(x[2]) - float(x[3]))
            hi = T / 2 + d
            lo = T - hi
            m = mpw(max(slew.get(x[1], 0.0), float(x[4])), c)
            rows.append((hi / T, x[1], hi, lo, m))
    du = [r[0] for r in rows]
    bad = [r for r in rows if not 0.45 <= r[0] <= 0.55]
    mpwf = [r for r in rows if min(r[2], r[3]) < r[4]]
    out[c] = dict(taps=len(rows), duty_min=round(min(du), 4), duty_med=round(statistics.median(du), 4),
                  duty_max=round(max(du), 4), outside_45_55=len(bad), mpw_fail=len(mpwf),
                  worst=[dict(port=r[1], duty=round(r[0], 4), high_ps=round(r[2], 1), low_ps=round(r[3], 1), mpw_ps=round(r[4], 1))
                         for r in sorted(rows, key=lambda r: -abs(r[0] - 0.5))[:5]])
    print(c, json.dumps({k: v for k, v in out[c].items() if k != "worst"}), "worst", out[c]["worst"][0])
json.dump(dict(rule="COORD 08:4x: duty 45-55 % at every tap (both edges, spice-scaled), lib MPW on both phases", corners=out),
          open(sys.argv[3], "w"), indent=1)
