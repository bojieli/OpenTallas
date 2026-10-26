#!/usr/bin/env python3
"""INFRA-FIRST-R5: GRT vs DRT clock-net RC + tap latency/skew on the q52sw crop (83 clock nets, 35 taps).

Per net: total C (wire, coupling folded to ground), total R, max driver->sink Elmore (wire R x (wire C + pin C)).
Tap latency model (same for every SPEF, so GRT->DRT deltas are the RC effect only):
  tree part  = OpenSTA propagated arrival at each mesh-driver A pin (single-driver nets, liberty NLDM, this SPEF)
  mesh net   = linear RC, every BUFx24 driver = Thevenin source (d0(slew) + Rd, die_clock_mesh.lib_buf fit) switching at
               its tree arrival; node time = sum_k w_ik (a_k + d0_k) + 0.69 * (G^-1 C 1)_i (multi-source first moment)
  stub       = BUFx4 NLDM cell_rise at a fixed 30 ps input slew and its stub-net load, + 0.69 * stub-net Elmore to the tap port
usage: cmp_rc.py LIBDIR label=SPEF:ARR_TT:ARR_FF ...   (ARR = arr_pins.tcl output for that SPEF/corner)
"""
import gzip, re, sys, json, math
from collections import defaultdict
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as sla

LIBDIR = sys.argv[1]


def lib(corner):
    txt = gzip.open(f"{LIBDIR}/asap7sc7p5t_INVBUF_RVT_{corner}_nldm_220122.lib.gz", "rt").read()
    out = {}
    for cell in ("BUFx24_ASAP7_75t_R", "BUFx4_ASAP7_75t_R", "BUFx2_ASAP7_75t_R", "BUFx8_ASAP7_75t_R", "BUFx12f_ASAP7_75t_R"):
        i = txt.index(f"cell ({cell})"); blk = txt[i:txt.index("cell (", i + 10)]
        m = re.search(r"cell_rise \(\w+\) \{\s*index_1 \(\"([^\"]+)\"\);\s*index_2 \(\"([^\"]+)\"\);\s*values \((.*?)\);", blk, re.S)
        sl = [float(v) for v in m.group(1).split(",")]; ld = [float(v) for v in m.group(2).split(",")]
        rows = [[float(v) for v in r.split(",")] for r in re.findall(r"\"([^\"]+)\"", m.group(3))]
        cap = float(re.search(r"rise_capacitance : ([\d.]+)", blk).group(1))
        out[cell] = (sl, ld, rows, cap)
    return out


def interp(xv, yv, x):
    if x <= xv[0]:
        k = 1
    elif x >= xv[-1]:
        k = len(xv) - 1
    else:
        k = next(k for k in range(1, len(xv)) if x <= xv[k])
    t = (x - xv[k - 1]) / (xv[k] - xv[k - 1]); return yv[k - 1] + t * (yv[k] - yv[k - 1])


def nldm(t, s, c):
    sl, ld, rows, _ = t
    col = [interp(ld, r, c) for r in rows]
    return interp(sl, col, s)


def thev(t):  # die_clock_mesh.lib_buf: d0(slew) + R*C fit over loads idx 2..5
    sl, ld, rows, cap = t
    slope = sum((r[5] - r[2]) / (ld[5] - ld[2]) for r in rows) / len(rows)
    return sl, [r[2] - slope * ld[2] for r in rows], slope / 0.69


def read_spef(path):
    nets = {}; cur = None; sec = None; nm = {}; cs = 1.0; rs = 1.0; in_map = False
    def M(t):
        if t.startswith("*"):
            h, _, rest = t.partition(":")
            h = nm.get(h, h)
            return h + (":" + rest if rest else "")
        return t
    for line in open(path):
        w = line.split()
        if not w:
            continue
        if w[0] == "*C_UNIT":
            cs = float(w[1]) * {"FF": 1.0, "PF": 1000.0}[w[2]]; continue
        if w[0] == "*R_UNIT":
            rs = float(w[1]) * {"KOHM": 1.0, "OHM": 1e-3}[w[2]]; continue
        if w[0] == "*NAME_MAP":
            in_map = True; continue
        if in_map:
            if len(w) == 2 and w[0].startswith("*") and w[0][1:].isdigit():
                nm[w[0]] = w[1]; continue
            in_map = False
        if w[0] in ("*D_NET", "*I", "*P"):
            w = [w[0], M(w[1])] + w[2:]
        elif sec in ("*CAP", "*RES") and w[0][0].isdigit():
            w = [w[0]] + [M(t) for t in w[1:-1]] + [w[-1]]
        if w[0] == "*D_NET":
            w[2] = str(float(w[2]) * cs)
        elif sec == "*CAP" and w[0][0].isdigit():
            w[-1] = str(float(w[-1]) * cs)
        elif sec == "*RES" and w[0][0].isdigit():
            w[-1] = str(float(w[-1]) * rs)
        if w[0] == "*D_NET":
            cur = dict(name=w[1], tot=float(w[2]), conn=[], cap=defaultdict(float), res=[]); nets[w[1]] = cur; sec = None; continue
        if cur is None:
            continue
        if w[0] in ("*CONN", "*CAP", "*RES"):
            sec = w[0]; continue
        if w[0] == "*END":
            cur = None; continue
        if sec == "*CONN" and w[0] in ("*I", "*P"):
            cur["conn"].append((w[1], w[2], w[4] if len(w) > 4 and w[3] == "*D" else ("PORT" if w[0] == "*P" else None)))
        elif sec == "*CAP":
            if len(w) == 3:
                cur["cap"][w[1]] += float(w[2])
            elif len(w) == 4:   # coupling folded to ground on both ends
                cur["cap"][w[1]] += float(w[3]); cur["cap"][w[2]] += float(w[3])
        elif sec == "*RES":
            cur["res"].append((w[1], w[2], float(w[3])))
    return nets


def network(n, pincap):
    idx = {}
    def I(k):
        if k not in idx:
            idx[k] = len(idx)
        return idx[k]
    for a, b, r in n["res"]:
        I(a); I(b)
    for k in n["cap"]:
        I(k)
    for p, d, cell in n["conn"]:
        I(p)
    N = len(idx); C = np.zeros(N)
    for k, c in n["cap"].items():
        C[idx[k]] += c
    for p, d, cell in n["conn"]:
        if d == "I" and cell in pincap:
            C[idx[p]] += pincap[cell]
    rows, cols, vals = [], [], []
    for a, b, r in n["res"]:
        g = 1.0 / max(r, 1e-6); i, j = idx[a], idx[b]
        rows += [i, j, i, j]; cols += [i, j, j, i]; vals += [g, g, -g, -g]
    G = sp.csr_matrix((vals, (rows, cols)), shape=(N, N))
    # drop floating wire pieces (components without any pin; RCX leaves a few) so G is non-singular
    import scipy.sparse.csgraph as cg
    nc, lab = cg.connected_components(G != 0, directed=False)
    live = {lab[idx[p]] for p, d, cell in n["conn"]}
    keep = [i for i in range(N) if lab[i] in live]
    if len(keep) < N:
        FLOAT[0] += N - len(keep); FLOAT[1] += float(sum(C[i] for i in range(N) if lab[i] not in live))
        rm = {old: new for new, old in enumerate(keep)}
        idx = {k: rm[i] for k, i in idx.items() if i in rm}
        G = G[keep][:, keep].tocsr(); C = C[keep]
    return idx, G, C


FLOAT = [0, 0.0]


def tree_elmore(n, pincap):
    idx, G, C = network(n, pincap)
    drv = [p for p, d, c in n["conn"] if d == "O" and c != "PORT"]
    if len(drv) != 1:
        return None
    i0 = idx[drv[0]]; N = len(idx)
    keep = [i for i in range(N) if i != i0]
    Gr = G[keep][:, keep].tocsc(); m = sla.spsolve(Gr, C[keep]) if N > 1 else np.zeros(0)
    pos = {k: n_ for n_, k in enumerate(keep)}
    return {p: float(m[pos[idx[p]]]) for p, d, c in n["conn"] if idx[p] != i0}


def c_ok(cell):
    return cell != "PORT"


def analyse(spef, arr, corner, L):
    nets = read_spef(spef)
    pincap = {c: L[c][3] for c in L}
    tot = {k: (v["tot"], sum(r for _, _, r in v["res"])) for k, v in nets.items()}
    el = {}
    for k, v in nets.items():
        if "mesh" in k:
            continue
        e = tree_elmore(v, pincap)
        if e:
            el[k] = max(e.values())
    # mesh
    mn = next(v for k, v in nets.items() if "mesh" in k)
    idx, G, C = network(mn, pincap)
    sl, d0, Rd = thev(L["BUFx24_ASAP7_75t_R"])
    A = {}
    for line in open(arr):
        p, amax, amin, slew = line.split()
        A[p.split("/")[0]] = (float(amax), float(slew))
    N = len(idx); Gd = np.zeros(N); src = np.zeros(N)
    for p, d, cell in mn["conn"]:
        if d == "O" and c_ok(cell):
            inst = p.split(":")[0]; a, s = A[inst]
            Gd[idx[p]] += 1.0 / Rd; src[idx[p]] += (a + interp(sl, d0, s)) / Rd
    Gt = (G + sp.diags(Gd)).tocsc()
    lu = sla.splu(Gt)
    w_t = lu.solve(src)                       # sum_k w_ik t_k
    m = lu.solve(C)                           # first moment incl. Rd
    t_node = w_t + 0.69 * m
    # stub nets: stub inst -> tap port
    stub_of = {}
    for k, v in nets.items():
        ports = [p for p, d, c in v["conn"] if c == "PORT" or (":" not in p and d == "O")]
        drv = [p for p, d, c in v["conn"] if d == "O" and ":" in p]
        if len(drv) == 1 and drv[0].startswith("ckm_s_"):
            for p, d, c in v["conn"]:
                if ":" not in p:
                    stub_of[p] = (drv[0].split(":")[0], k)
    lat = {}
    for port, (inst, net) in stub_of.items():
        ta = t_node[idx[inst + ":A"]]
        e = tree_elmore(nets[net], pincap)
        cl = nets[net]["tot"]
        lat[port] = ta + nldm(L["BUFx4_ASAP7_75t_R"], 30.0, cl) + 0.69 * e.get(port, 0.0)
    return tot, el, lat, {k: v[0] for k, v in A.items()}


def main():
    res = {}
    for spec in sys.argv[2:]:
        label, rest = spec.split("=", 1); spef, att, aff = rest.split(":")
        res[label] = {}
        for corner, arr in (("TT", att), ("FF", aff)):
            L = lib(corner)
            res[label][corner] = analyse(spef, arr, corner, L)
    labs = list(res)
    base = labs[0]
    out = dict(labels=labs)
    tb = res[base]["TT"][0]
    for lab in labs[1:]:
        t = res[lab]["TT"][0]
        dc = {k: t[k][0] - tb[k][0] for k in tb if k in t}; dr = {k: t[k][1] - tb[k][1] for k in tb if k in t}
        rc = {k: (t[k][0] / tb[k][0] if tb[k][0] else float("nan"), t[k][1] / tb[k][1] if tb[k][1] else float("nan")) for k in tb if k in t}
        sumC = (sum(v[0] for v in tb.values()), sum(t[k][0] for k in tb if k in t))
        sumR = (sum(v[1] for v in tb.values()), sum(t[k][1] for k in tb if k in t))
        cr = sorted(v[0] for v in rc.values()); rr = sorted(v[1] for v in rc.values() if not math.isnan(v[1]))
        eb, et = res[base]["TT"][1], res[lab]["TT"][1]
        de = sorted(et[k] - eb[k] for k in eb if k in et)
        o = dict(nets=len(rc), sumC_fF=sumC, sumR_kohm=sumR,
                 C_ratio_min_med_max=(cr[0], cr[len(cr) // 2], cr[-1]), R_ratio_min_med_max=(rr[0], rr[len(rr) // 2], rr[-1]),
                 tree_elmore_delta_ps_min_med_max=(de[0], de[len(de) // 2], de[-1]),
                 mesh_C=(tb[next(k for k in tb if "mesh" in k)][0], t[next(k for k in t if "mesh" in k)][0]))
        for corner in ("TT", "FF"):
            lb, lt = res[base][corner][2], res[lab][corner][2]
            ab, at = res[base][corner][3], res[lab][corner][3]
            ks = sorted(set(lb) & set(lt))
            d = [lt[k] - lb[k] for k in ks]
            sk_b = max(lb[k] for k in ks) - min(lb[k] for k in ks); sk_t = max(lt[k] for k in ks) - min(lt[k] for k in ks)
            pair = max(abs((lt[a] - lt[b]) - (lb[a] - lb[b])) for a in ks for b in ks)
            dd = [at[k] - ab[k] for k in ab if k in at]
            o[corner] = dict(taps=len(ks), lat_base_min_max=(min(lb[k] for k in ks), max(lb[k] for k in ks)),
                             lat_new_min_max=(min(lt[k] for k in ks), max(lt[k] for k in ks)),
                             tap_lat_delta_min_mean_max=(min(d), sum(d) / len(d), max(d)),
                             spread_base=sk_b, spread_new=sk_t, max_pair_skew_change=pair,
                             meshdrv_A_arrival_delta_min_max=(min(dd), max(dd)),
                             per_tap={k: (round(lb[k], 2), round(lt[k], 2)) for k in ks})
        o["per_net_C_R"] = {k: (round(tb[k][0], 3), round(t[k][0], 3), round(tb[k][1], 4), round(t[k][1], 4)) for k in sorted(tb) if k in t}
        out[f"{base}->{lab}"] = o
    print(json.dumps(out, indent=1))


main()
