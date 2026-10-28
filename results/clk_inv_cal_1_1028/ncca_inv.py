#!/usr/bin/env python3
"""NUMBER-CHECK-CA-1: independent CA margin recompute from raw built clock arrivals.
Own code (no import of die_plan tools). Model per METHODOLOGY 12.16b(ii): STA phase (OpenSTA late/early tap arrivals)
+ CPPR at the LCA of the two tap driver chains + clock_variation=table (3 sigma random over unshared stages, incl. core
latency class B, + g*diag/2 per side; droop +5.11 % late cells if different droop region; nets flat 1.03/0.97)
+ spice scale per corner; union TT/FF and ALL tap pairs of the two partitions. Wander +-0.05 x max unshared.
Margins with the EMITTED plan K_eff (= K + n0): L = K_eff T + d;  m_lo = L_lo - T/2,  m_hi = (DEPTH - 1/2) T - L_hi.
usage: ncca.py TREE ARR_TT ARR_FF PLAN PART_REGION AOCV_JSON PLAN_OUT OUT_JSON [--inv-pair-stages]"""
import json, math, sys, random
from collections import defaultdict

a = sys.argv[1:]
TREE, ATT, AFF, PLAN, PREG, AOCV, POUT, OUT = a[:8]
INVPAIR = "--inv-pair-stages" in a
T = 833.0
SPICE = {"TT": 1.0485, "FF": 1.0552}
# CLK-INV-CAL-1 copy: --inv-cal = measured CKINVDCx16 row (class Ainv, every inverter one stage) + inverter spice factor
INVCAL = "--inv-cal" in a
CA_ = "Ainv" if INVCAL else "A"
if INVCAL:
    SPICE = {"TT": 0.9324, "FF": 0.9380}
CORELAT = {"TT": 250.0, "FF": 202.5}

tree = json.load(open(TREE))
reg = json.load(open(PREG))["part_region"]
plan = json.load(open(PLAN))
tab = json.load(open(AOCV))["clock_aocv"]
pout = json.load(open(POUT))


def rd(f, s):
    Tt, N = {}, {}
    for ln in open(f):
        x = ln.split()
        if not x:
            continue
        if x[0] == "T":
            Tt[x[1]] = (float(x[2]) * s, float(x[3]) * s)
        elif x[0] == "N":
            N[x[1]] = (float(x[2]) * s, float(x[3]) * s)
    return Tt, N


arr = {c: rd(f, SPICE[c]) for c, f in (("TT", ATT), ("FF", AFF))}
par = tree["parent_of"]
sites = tree["sites"]
chains = {}


def chain(c):
    if c in chains:
        return chains[c]
    out = [c]
    while out[-1] in par:
        out.append(par[out[-1]])
    chains[c] = out
    return out


taps_by_part = defaultdict(list)
for t in tree["taps"]:
    t = dict(t)
    t["drv"] = t.get("driver", tree["node_buf"][str(t["node"])])
    taps_by_part[t["part"]].append(t)


def rfrac(cor, nA, nB):
    var = mu = 0.0
    for cls, n in ((CA_, nA), ("B", nB)):
        if n <= 0:
            continue
        c = tab["classes"][cls][cor]
        m, s, rho = c["mu_cell_ps"], c["s_cell"], c.get("rho", [])
        v = float(n)
        for l, r in enumerate(rho, 1):
            if l < n:
                v += 2 * (n - l) * r
        var += (m * s) ** 2 * v
        mu += n * m
    return 0.0 if mu <= 0 else 3.0 * math.sqrt(var) / mu


def pess(cor, late_u, late_n, early_u, early_n, diag, droop):
    """ps: late branch derated late + early branch derated early (cells by table, nets flat)."""
    fA = tab["classes"][CA_][cor]["cell_share"]
    B = tab["classes"]["B"][cor]
    lat = CORELAT[cor]
    nB = max(1, round(lat / B["mu_stage_ps"]))
    sysf = tab["systematic"]["g_per_mm"] * diag / 1000.0 / 2.0
    nl, ne = tab["net_flat"]["late"], tab["net_flat"]["early"]
    tot = 0.0
    for u, n, late in ((late_u, late_n, True), (early_u, early_n, False)):
        cell = fA * u + B["cell_share"] * lat
        net = (1 - fA) * u + (1 - B["cell_share"]) * lat
        f = rfrac(cor, n, nB) + sysf + ((tab["droop"]["one_sided_late_frac"] if droop else 0.0) if late else 0.0)
        tot += cell * f + net * ((nl - 1) if late else (1 - ne))
    return tot


pair_cache = {}


def pair(ta, tb, cor):
    k = (ta["port"], tb["port"], cor)
    if k in pair_cache:
        return pair_cache[k]
    Tt, N = arr[cor]
    ca, cb = chain(ta["drv"]), chain(tb["drv"])
    sb = set(cb)
    ia = next(i for i, c in enumerate(ca) if c in sb)
    node = ca[ia]
    ib = cb.index(node)
    nla, nea = N[node]
    la, ea = Tt[ta["port"]]
    lb, eb = Tt[tb["port"]]
    pts = [ta["xy"], tb["xy"], sites[node]]
    diag = math.hypot(max(p[0] for p in pts) - min(p[0] for p in pts), max(p[1] for p in pts) - min(p[1] for p in pts))
    droop = reg.get(ta["part"]) != reg.get(tb["part"])
    na, nb = (ia, ib) if not INVPAIR else (max(1, ia // 2), max(1, ib // 2))
    # setup-side (d shrinks): launch a late, capture b early ; branch delays below the LCA
    ua_l, ub_e = la - nla, eb - nea
    ub_l, ua_e = lb - nla, ea - nea
    lo = (eb - nea) - (la - nla) - pess(cor, ua_l, na, ub_e, nb, diag, droop)
    hi = (lb - nla) - (ea - nea) + pess(cor, ub_l, nb, ua_e, na, diag, droop)
    uns = max(la - nla, lb - nla)
    r = (lo, hi, uns, node, ia, ib, diag)
    pair_cache[k] = r
    return r


# crossings = plan ports whose partitions sit in different regions and have taps
xs = [p for p in plan["ports"] if p["src"]["part"] != p["dst"]["part"] and reg.get(p["src"]["part"]) != reg.get(p["dst"]["part"])
      and p["src"]["part"] in taps_by_part and p["dst"]["part"] in taps_by_part]
cr = {c["port"]: c for c in pout["crossings"]}
print("plan region crossings with taps", len(xs), "plan_out crossings", len(cr))

# choose: worst 10 by the tool's min(margin_lo, margin_hi) + 10 random (seed 20261028)
data = [c for c in pout["crossings"] if not c["port"].startswith("start") and c.get("depth")]
data.sort(key=lambda c: min(c["margin_lo_ps"], c["margin_hi_ps"]))
pick = [c["port"] for c in data[:10]]
rest = [c["port"] for c in data[10:]]
random.seed(20261028)
pick += random.sample(rest, 10)
if "--all" in a:
    pick = [c["port"] for c in data]
byid = {p["id"]: p for p in plan["ports"]}
res = []
for pid in pick:
    p = byid[pid]
    o = cr[pid]
    A, Bt = taps_by_part[p["src"]["part"]], taps_by_part[p["dst"]["part"]]
    lo, hi, uns = 1e18, -1e18, 0.0
    n = 0
    for cor in ("TT", "FF"):
        for ta in A:
            for tb in Bt:
                l, h, u, *_ = pair(ta, tb, cor)
                lo, hi, uns = min(lo, l), max(hi, h), max(uns, u)
                n += 1
    w = 0.05 * uns
    Ke, D = o["K_eff"], o["depth"]
    Llo, Lhi = Ke * T + lo - w, Ke * T + hi + w
    mlo, mhi = Llo - T / 2, (D - 0.5) * T - Lhi
    res.append(dict(port=pid, src=o["src"], dst=o["dst"], pairs=n, d_lo=round(lo, 1), d_hi=round(hi, 1), wander=round(w, 1),
                    K_eff=Ke, DEPTH=D, my_m_lo=round(mlo, 1), my_m_hi=round(mhi, 1), tool_m_lo=o["margin_lo_ps"],
                    tool_m_hi=o["margin_hi_ps"], tool_L=[o["L_lo_ps"], o["L_hi_ps"]], my_L=[round(Llo, 1), round(Lhi, 1)],
                    my_pass=min(mlo, mhi) >= 100))
    print(json.dumps(res[-1]))
json.dump(res, open(OUT, "w"), indent=1)
bad = [r for r in res if not r["my_pass"]]
print("checked", len(res), "my FAIL(<100)", len(bad), "min my_m_lo", min(r["my_m_lo"] for r in res),
      "min my_m_hi", min(r["my_m_hi"] for r in res), "max |dm_lo|", max(abs(r["my_m_lo"] - r["tool_m_lo"]) for r in res))
