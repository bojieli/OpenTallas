import json, sys, numpy as np
P = json.load(open(sys.argv[1])); arr = {}
for ln in open(sys.argv[2]):
    pn, n, a, b, s = ln.split()
    if a != "-INF": arr[(n, pn)] = (float(a), float(s))
C, N = P["cells"], P["nets"]
def xy(n): return (C[n]["x"], C[n]["y"])
def man(a, b): return abs(a[0]-b[0]) + abs(a[1]-b[1])
rows = []
for nn, net in N.items():
    if net["kind"] != "tree" or net["drv"].startswith("port"): continue
    d = net["drv"]; Ls = net["loads"]
    if (d, "A") not in arr: continue
    ltot = sum(man(xy(d), xy(l)) for l in Ls)
    for l in Ls:
        if (l, "A") not in arr: continue
        lk = man(xy(d), xy(l))
        rows.append((arr[(l, "A")][0] - arr[(d, "A")][0], lk, ltot, len(Ls), arr[(d, "A")][1], d, l))
y = np.array([r[0] for r in rows]); lk = np.array([r[1] for r in rows]); lt = np.array([r[2] for r in rows])
fo = np.array([r[3] for r in rows]); sl = np.array([r[4] for r in rows])
print("stages", len(rows), "fo2", int((fo == 2).sum()))
for lab, X in (("a+b*Ltot+c*Lk^2+e*Lk", np.c_[np.ones_like(y), lt, lk**2, lk]),
               ("+fo", np.c_[np.ones_like(y), lt, lk**2, lk, fo == 2]),
               ("+fo+Ltot^2+slew_in", np.c_[np.ones_like(y), lt, lk**2, lk, fo == 2, lt**2, sl])):
    co, *_ = np.linalg.lstsq(X, y, rcond=None); r = y - X @ co
    print(lab, np.round(co, 6), "sd", round(r.std(), 2), "max", round(abs(r).max(), 1))
# residual by length bins
X = np.c_[np.ones_like(y), lt, lk**2, lk, fo == 2, lt**2, sl]; co, *_ = np.linalg.lstsq(X, y, rcond=None); r = y - X @ co
for lo, hi in ((0, 50), (50, 150), (150, 300), (300, 500), (500, 2000)):
    m = (lk >= lo) & (lk < hi)
    if m.any(): print(f"Lk {lo}-{hi}: n {m.sum()} mean d {y[m].mean():.1f} resid sd {r[m].std():.1f} max {abs(r[m]).max():.1f}")
big = np.argsort(-abs(r))[:8]
for i in big: print("worst", rows[i][5], rows[i][6], "d", round(y[i],1), "Lk", round(lk[i]), "Ltot", round(lt[i]), "fo", fo[i], "slew_in", round(sl[i],1), "res", round(r[i],1))
# slew model at the load pin: s = a + b*Ltot + c*Lk^2 + e*Lk + g*Ltot^2
s = np.array([arr[(r[6], "A")][1] for r in rows])
Xs = np.c_[np.ones_like(y), lt, lk**2, lk, lt**2]
cs, *_ = np.linalg.lstsq(Xs, s, rcond=None); rs = s - Xs @ cs
print("SLEW", list(np.round(cs, 8)), "sd", round(rs.std(), 2), "max", round(abs(rs).max(), 1), "slew range", s.min(), s.max())
print("DELAY", list(np.round(co, 8)), "order: 1, Ltot, Lk^2, Lk, fo2, Ltot^2, slew_in")
# chained validation: predict each driver arrival by walking the tree with modelled slews
par = {}
for nn, net in N.items():
    if net["kind"] == "tree":
        for l in net["loads"]: par[l] = net["drv"]
def pred(n, memo={}):
    if n in memo: return memo[n]
    p = par.get(n)
    if p is None or p == "port:root": memo[n] = (arr[(n, "A")][0], arr[(n, "A")][1]); return memo[n]
    ap, sp = pred(p)
    net = N["n_" + p]; ltot = sum(man(xy(p), xy(l)) for l in net["loads"]); l1 = man(xy(p), xy(n))
    d = co @ [1, ltot, l1**2, l1, len(net["loads"]) == 2, ltot**2, sp]
    sl = cs @ [1, ltot, l1**2, l1, ltot**2]
    memo[n] = (ap + d, sl); return memo[n]
M = [n for n in C if n.startswith("M") and (n, "A") in arr]
e = np.array([pred(n)[0] - arr[(n, "A")][0] for n in M]); ma = np.array([arr[(n, "A")][0] for n in M]); pa = ma + e
print("drivers", len(M), "measured spread", round(ma.max()-ma.min(),1), "pred spread", round(pa.max()-pa.min(),1), "pred err sd", round(e.std(),1), "max", round(abs(e - e.mean()).max(),1))
