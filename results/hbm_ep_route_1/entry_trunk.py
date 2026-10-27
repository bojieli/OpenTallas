#!/usr/bin/env python3
"""HBM-EP-ROUTE-1: plan-computed 12.8c fixed entry trunk for hfd_ep_static.
Per-stage delay of an N x CELL chain (port -> e1 -> ... -> eN -> root BUFx24) from the NLDM liberty tables (TT/FF),
ideal clock port (slew 0), stage load = Cin(next) + 1.2 um M2 wire.  Picks N so built TT 185.81 + chain ~= 250."""
import gzip, re, sys, json
def cells(path):
    t = gzip.open(path, 'rt').read()
    out = {}
    for m in re.finditer(r'\n\s*cell\s*\(\s*"?(\w+)"?\s*\)', t):
        out[m.group(1)] = m.start()
    return t, out
def block(t, start):
    i = t.index('{', start); d = 0
    for j in range(i, len(t)):
        if t[j] == '{': d += 1
        elif t[j] == '}':
            d -= 1
            if d == 0: return t[i:j+1]
def nums(s): return [float(x) for x in re.findall(r'[-+0-9.eE]+', s)]
def table(b, name):
    m = re.search(name + r'\s*\(\s*\w+\s*\)\s*\{(.*?)\}', b, re.S); s = m.group(1)
    i1 = nums(re.search(r'index_1\s*\(\s*"([^"]*)"', s).group(1)); i2 = nums(re.search(r'index_2\s*\(\s*"([^"]*)"', s).group(1))
    v = nums(re.search(r'values\s*\((.*?)\)\s*;', s, re.S).group(1).replace('\\', ' '))
    return i1, i2, [v[k*len(i2):(k+1)*len(i2)] for k in range(len(i1))]
def interp(tb, x, y):
    i1, i2, v = tb
    def seg(a, q):
        k = max(0, min(len(a)-2, next((j for j in range(len(a)-1) if q <= a[j+1]), len(a)-2)))
        return k, (q - a[k]) / (a[k+1] - a[k])
    a, fa = seg(i1, x); b, fb = seg(i2, y)
    return (v[a][b]*(1-fa)*(1-fb) + v[a+1][b]*fa*(1-fb) + v[a][b+1]*(1-fa)*fb + v[a+1][b+1]*fa*fb)
def cin(cb):
    m = re.search(r'pin\s*\(\s*"?A"?\s*\)\s*\{.*?\bcapacitance\s*:\s*([0-9.]+)', cb, re.S); return float(m.group(1))
def chain(lib, cell, n, wire_ff=0.25):
    t, c = cells(lib); cb = block(t, c[cell]); rb = block(t, c['BUFx24_ASAP7_75t_R'])
    cr, tr = table(cb, 'cell_rise'), table(cb, 'rise_transition'); cf, tf = table(cb, 'cell_fall'), table(cb, 'fall_transition')
    slr = slf = 0.0; dr = df = 0.0; per = []
    for j in range(n):
        load = (cin(cb) if j < n-1 else cin(rb)) + wire_ff
        a = interp(cr, slr, load); b = interp(cf, slf, load)
        slr, slf = interp(tr, slr, load), interp(tf, slf, load)
        dr += a; df += b; per.append(round(a, 2))
    return dr, df, per, slr
TT, FF = sys.argv[1], sys.argv[2]; cell = sys.argv[3] if len(sys.argv) > 3 else 'BUFx16f_ASAP7_75t_R'
base_tt, base_ff = 185.81, 142.56
res = []
for n in range(1, 9):
    dt, _, per, sl = chain(TT, cell, n); df_, _, _, _ = chain(FF, cell, n)
    res.append(dict(n=n, add_tt=round(dt, 2), add_ff=round(df_, 2), tt=round(base_tt+dt, 1), ff=round(base_ff+df_, 1), per_tt=per, out_slew_tt=round(sl, 1)))
    print(res[-1])
best = min(res, key=lambda r: abs(r['tt'] - 250.0))
print('CHOSEN', json.dumps(best))
