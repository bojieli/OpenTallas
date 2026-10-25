# Fit per-layer wire C (fF/um) and R (ohm/um) of routed DEF vs OpenRCX SPEF, separately for clock and signal nets.
# Least squares C_net = sum_l c_l * len_l (pin caps excluded by SPEF D_NET total? -> total includes only wire caps in OpenRCX).
import re, sys, json
deff, spef = sys.argv[1], sys.argv[2]
LAY = ['M2', 'M3', 'M4', 'M5']
pt = re.compile(r'\(\s*(-?\d+|\*)\s+(-?\d+|\*)(?:\s+\S+)?\s*\)')
lens = {}; sec = False; buf = ''
def flush(t):
    m = re.match(r'-\s+(\S+)', t)
    if not m or '+ ROUTED' not in t: return
    L = dict.fromkeys(LAY, 0.0); vias = 0
    for part in re.split(r'\+ ROUTED|NEW', t)[1:]:
        tok = part.split()
        if not tok: continue
        lay = tok[0]; ps = pt.findall(part); prev = None
        if len(ps) == 1 or (len(tok) > 3 and not tok[-1].startswith(')') and len(ps) < 2): vias += 1
        for x, y in ps:
            if prev is None: px, py = int(x), int(y)
            else:
                px = prev[0] if x == '*' else int(x); py = prev[1] if y == '*' else int(y)
                if lay in L: L[lay] += (abs(px - prev[0]) + abs(py - prev[1])) / 1000
            prev = (px, py)
    lens[m.group(1).replace('\\', '')] = L
for raw in open(deff):
    s = raw.strip()
    if s.startswith('NETS'): sec = True; continue
    if sec and s.startswith('END NETS'):
        flush(buf); break
    if sec:
        if s.startswith('- '):
            if buf: flush(buf)
            buf = s
        else: buf += ' ' + s
nm = {}; cap = {}; res = {}; cur = None; mode = None
for raw in open(spef):
    if raw.startswith('*NAME_MAP'): mode = 'map'; continue
    if mode == 'map':
        if raw.startswith('*') and ' ' in raw and raw[1].isdigit():
            k, v = raw.split(None, 1); nm[k] = v.strip().replace('\\', ''); continue
        elif raw.strip() == '': continue
        else: mode = None
    if raw.startswith('*D_NET'):
        f = raw.split(); cur = nm.get(f[1], f[1]); cap[cur] = float(f[2]) * 1000; res[cur] = 0.0; mode = None; continue
    if raw.startswith('*RES'): mode = 'res'; continue
    if raw.startswith('*END'): mode = None; continue
    if mode == 'res' and cur:
        f = raw.split()
        if len(f) == 4: res[cur] += float(f[3])
def fit(names, val):
    import itertools
    n = len(LAY); A = [[0.0]*n for _ in range(n)]; b = [0.0]*n
    for k in names:
        x = [lens[k][l] for l in LAY]; y = val[k]
        for i in range(n):
            b[i] += x[i]*y
            for j in range(n): A[i][j] += x[i]*x[j]
    # solve
    M = [A[i] + [b[i]] for i in range(n)]
    for i in range(n):
        p = max(range(i, n), key=lambda r: abs(M[r][i])); M[i], M[p] = M[p], M[i]
        for r in range(n):
            if r != i and M[i][i]:
                f = M[r][i] / M[i][i]; M[r] = [a - f*c for a, c in zip(M[r], M[i])]
    return {LAY[i]: round(M[i][n] / M[i][i], 5) if M[i][i] else None for i in range(n)}
out = {}
for cls, sel in [('clock', lambda k: k.startswith('clknet') or k == 'clk'), ('signal', lambda k: not (k.startswith('clknet') or k == 'clk'))]:
    ks = [k for k in lens if k in cap and sel(k) and sum(lens[k].values()) > 20]
    out[cls] = dict(n=len(ks), C_fF_per_um=fit(ks, cap), R_ohm_per_um_sum=fit(ks, res),
                    len_um={l: round(sum(lens[k][l] for k in ks)) for l in LAY})
for k in sys.argv[3:]:
    if k in lens: out[k] = dict(len=lens[k], C_fF=cap.get(k), Rsum=res.get(k))
print(json.dumps(out, indent=1))
