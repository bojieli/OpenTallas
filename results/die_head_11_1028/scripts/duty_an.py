import sys, json, re, statistics as st
T = 833.333; D = sys.argv[1]
v = open(f"{D}/out_TT/combo.v").read()
tapnet = dict(re.findall(r"assign\s+(t_\w+)\s*=\s*(\w+)\s*;", v))
drv = {}
for m in re.finditer(r"^\s*(\w+)\s+(ck_\w+)\s*\((.*?)\);", v, re.M | re.S):
    y = re.search(r"\.Y\((\w+)\)", m.group(3))
    if y: drv[y.group(1)] = m.group(2)
out = {}
for C in ("TT", "FF"):
    N = {}
    for l in open(f"{D}/out_{C}/duty_{C}.txt"):
        if l.startswith("N "):
            _, n, ar, af = l.split(); N[n] = (float(ar), float(af))
    allc = [N[n][1] - N[n][0] for n in N]
    d = []
    for t, net in tapnet.items():
        c = drv.get(net)
        if c and c in N: d.append((t, N[c][1] - N[c][0], N[c][0]))
    lat = [x[1] for x in d]
    out[C] = dict(taps=len(d), of=len(tapnet), tap_fall_minus_rise_ps=dict(min=round(min(lat), 2), max=round(max(lat), 2),
                  median=round(st.median(lat), 2), spread=round(max(lat) - min(lat), 2)),
                  all_cells_fall_minus_rise=dict(min=round(min(allc), 2), max=round(max(allc), 2)),
                  min_high_pulse_ps=round(T/2 + min(min(lat), 0), 1), min_low_pulse_ps=round(T/2 - max(max(lat), 0), 1),
                  max_tap_arrival_ps=round(max(x[2] for x in d), 1),
                  worst=[(w[0], round(w[1], 2), round(w[2], 1)) for w in sorted(d, key=lambda x: -abs(x[1]))[:3]])
print(json.dumps(out, indent=1))
