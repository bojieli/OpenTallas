#!/usr/bin/env python3
"""ASAP7 wire-RC calibration to routed OpenRCX (lane FLOW, 2026-10-25).

Subcommands
  emit   --scales JSON --out FILE      write a setRC.tcl (stock ASAP7 values x per-layer R/C scales, via R scales)
  fit    --wire W.tsv --spef S.spef [...] per-layer unit C / unit R least squares: SPEF net totals vs routed length per layer
  nets   --wire W.tsv --n N --out F     longest routed signal nets (setup sanity list)
  cmp    --ref RCX.tsv --est EST.tsv    est-minus-RCX clock-arrival / net-delay statistics (ps)

Pipeline (diagnostic, docker --memory on a fleet host, run dirs mounted read-only):
  rc_calib_run.sh <signoff_dir> <out> <M2-M5> <mem_gb> wd                 -> <out>/wire.tsv (rc_calib_wire_dump.py, 6_final.odb)
  rc_calib.py nets --wire <out>/wire.tsv --n 150 --out <out>/nets.txt
  rc_calib_run.sh <signoff_dir> <out> <M2-M5> <mem_gb> "rcx_tt rcx_ff est_tt est_ff"
      rcx = 6_final.odb + 6_final.spef; est = 5_1_grt.odb + its stored GRT routes + each <out>/rc/*.tcl
      (rc_calib_probe.tcl; source latency 0, propagated clocks, same libs/SDC as the signoff session)
  rc_calib.py fit --wire <out>/wire.tsv --spef 6_final.spef [--sigtype CLOCK|SIGNAL]
  rc_calib.py cmp --ref <out>/tt_rcx_rcx.tsv --est <out>/tt_est_<rc>.tsv
"""
import argparse, json, math, re, sys

STOCK_LAYER = {  # ORFS platforms/asap7/setRC.tcl: R kOhm/um, C fF/um
    "M1": (7.04175e-02, 1e-10), "M2": (2.97127e-02, 1.74942e-01), "M3": (3.12870e-02, 1.55554e-01),
    "M4": (1.80365e-02, 1.78475e-01), "M5": (1.89935e-02, 1.64264e-01), "M6": (1.18796e-02, 1.87426e-01),
    "M7": (1.25096e-02, 1.62979e-01), "M8": (8.44765e-03, 1.03962e-01), "M9": (8.89556e-03, 9.28446e-02)}
STOCK_VIA = {"V1": 1.72e-02, "V2": 1.72e-02, "V3": 1.72e-02, "V4": 1.18e-02, "V5": 1.18e-02,
             "V6": 8.20e-03, "V7": 8.20e-03, "V8": 6.30e-03, "V9": 6.30e-03}  # kOhm per cut
STOCK_WIRE = {"signal": (2.65684e-02, 1.65790e-01), "clock": (2.14161e-02, 1.45426e-01)}
LAYERS = ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9"]


def layer_values(params):
    """params: {"layer": {"M2": {"r": x, "c": y} | absolute {"R":..,"C":..}}, "via": {"V1": s}, "default": {"r":,"c":}}
    Returns (layer {L: (R, C)}, via {V: R}) in setRC units."""
    d = params.get("default", {})
    lay = {}
    for L in LAYERS:
        r0, c0 = STOCK_LAYER[L]
        p = params.get("layer", {}).get(L, {})
        R = p["R"] if "R" in p else r0 * p.get("r", d.get("r", 1.0))
        C = p["C"] if "C" in p else c0 * p.get("c", d.get("c", 1.0))
        lay[L] = (R, C)
    via = {}
    for V, r0 in STOCK_VIA.items():
        p = params.get("via", {}).get(V)
        if isinstance(p, dict) and "R" in p:
            via[V] = p["R"]
        else:
            via[V] = r0 * (p if p is not None else params.get("via_default", d.get("r", 1.0)))
    return lay, via


def emit_tcl(params, header=""):
    lay, via = layer_values(params)
    out = [("# " + h).rstrip() for h in header.splitlines()] if header else []
    for L in LAYERS:
        R, C = lay[L]
        out.append("set_layer_rc -layer %s -resistance %.5E -capacitance %.5E" % (L, R, C))
    # set_wire_rc (placement-stage, layer-agnostic): stock ratio to the M2-M5 mean, applied to the calibrated M2-M5 mean
    def mean(ix, src):
        return sum(src[L][ix] for L in ("M2", "M3", "M4", "M5")) / 4.0
    for kind in ("signal", "clock"):
        r0, c0 = STOCK_WIRE[kind]
        R = r0 / mean(0, STOCK_LAYER) * mean(0, lay)
        C = c0 / mean(1, STOCK_LAYER) * mean(1, lay)
        out.append("set_wire_rc -%s -resistance %.5E -capacitance %.5E" % (kind, R, C))
    for V in sorted(via):
        out.append("set_layer_rc -via %s -resistance %.5E" % (V, via[V]))
    return "\n".join(out) + "\n"


def parse_wire(path):
    """wire_dump.py TSV -> {net: (sigtype, {layer_or_V@layer: value})}"""
    res = {}
    with open(path) as f:
        for line in f:
            p = line.rstrip("\n").split("\t")
            if len(p) < 3:
                continue
            acc = {}
            for kv in p[2].split():
                k, v = kv.split("=")
                acc[k] = float(v)
            res[p[0]] = (p[1], acc)
    return res


def _unesc(n):
    return n.replace("\\", "")


def parse_spef(path, want=None):
    """-> {net: (C_fF, R_ohm_sum)}; SPEF C_UNIT/R_UNIT honoured (PF/FF, OHM/KOHM)."""
    cu, ru = 1.0, 1.0
    names = {}
    res = {}
    cur = None; sec = None; rs = 0.0; ctot = 0.0
    with open(path) as f:
        for line in f:
            if not line or line[0] == "\n":
                continue
            if line.startswith("*C_UNIT"):
                v, u = line.split()[1:3]; cu = float(v) * {"PF": 1e3, "FF": 1.0}[u.upper()]
            elif line.startswith("*R_UNIT"):
                v, u = line.split()[1:3]; ru = float(v) * {"OHM": 1.0, "KOHM": 1e3}[u.upper()]
            elif line.startswith("*D_NET"):
                _, n, c = line.split()[:3]
                n = names.get(n, n)
                cur = _unesc(n); ctot = float(c) * cu; rs = 0.0; sec = None
            elif line.startswith("*RES"):
                sec = "R"
            elif line.startswith("*CAP") or line.startswith("*CONN"):
                sec = "C"
            elif line.startswith("*END"):
                if cur is not None and (want is None or cur in want):
                    res[cur] = (ctot, rs)
                cur = None; sec = None
            elif line.startswith("*") and cur is None and line[1].isdigit():
                k, v = line.split()[:2]
                names[k] = v
            elif sec == "R" and cur is not None:
                p = line.split()
                if len(p) >= 4:
                    rs += float(p[3]) * ru
    return res


def lstsq(rows, ys, ridge=0.0, prior=None):
    """Plain normal-equation least squares (no numpy): minimize |Ax-y|^2 + ridge*|x-prior|^2."""
    k = len(rows[0])
    A = [[0.0] * k for _ in range(k)]
    b = [0.0] * k
    for r, y in zip(rows, ys):
        for i in range(k):
            if r[i] == 0:
                continue
            b[i] += r[i] * y
            for j in range(k):
                A[i][j] += r[i] * r[j]
    if ridge:
        for i in range(k):
            A[i][i] += ridge
            b[i] += ridge * (prior[i] if prior else 0.0)
    # Gauss-Jordan
    M = [A[i] + [b[i]] for i in range(k)]
    for c in range(k):
        piv = max(range(c, k), key=lambda r: abs(M[r][c]))
        if abs(M[piv][c]) < 1e-30:
            continue
        M[c], M[piv] = M[piv], M[c]
        for r in range(k):
            if r != c and M[r][c]:
                fct = M[r][c] / M[c][c]
                M[r] = [a - fct * bb for a, bb in zip(M[r], M[c])]
    return [M[i][k] / M[i][i] if M[i][i] else 0.0 for i in range(k)]


def fit_layers(wire, spef, layers, min_len=5.0, sigtype=None):
    """Per-layer unit C (fF/um, no intercept: SPEF PIN_CAP NONE) and unit R (Ohm/um) + per-via-level R (Ohm/cut).
    Only nets with total routed length >= min_len um. Returns dict + residual stats."""
    vias = ["V@" + L for L in ["M1"] + layers[:-1]]
    rc, yc, rr, yr = [], [], [], []
    for n, (st, acc) in wire.items():
        if n not in spef or (sigtype and st != sigtype):
            continue
        tot = sum(acc.get(L, 0.0) for L in layers)
        if tot < min_len:
            continue
        C, R = spef[n]
        xl = [acc.get(L, 0.0) for L in layers]
        # M1 pin-access stubs: tiny, folded into the M2 column
        xl[0] += acc.get("M1", 0.0)
        rc.append(xl); yc.append(C)
        rr.append(xl + [acc.get(v, 0.0) for v in vias]); yr.append(R)
    if not rc:
        return None
    c = lstsq(rc, yc)
    r = lstsq(rr, yr)

    def stats(rows, ys, x):
        e = [sum(a * b for a, b in zip(row, x)) / y - 1 for row, y in zip(rows, ys) if y > 0]
        e.sort()
        return {"n": len(e), "mean_rel": sum(e) / len(e), "p05": e[int(.05 * len(e))], "p95": e[int(.95 * len(e)) - 1]}
    return {"layers": layers, "C_fF_per_um": dict(zip(layers, c)), "R_ohm_per_um": dict(zip(layers, r[:len(layers)])),
            "via_R_ohm": dict(zip(vias, r[len(layers):])), "C_fit": stats(rc, yc, c), "R_fit": stats(rr, yr, r)}


def read_probe(path):
    ck, net, meta = {}, {}, {}
    with open(path) as f:
        for line in f:
            p = line.rstrip("\n").split("\t")
            if p[0] == "CK" and len(p) > 2 and p[2] not in ("", "nan"):
                ck[p[1]] = float(p[2])
            elif p[0] == "NET" and len(p) > 3:
                net[(p[1], p[2])] = float(p[3])
            elif p[0] in ("HOLD", "SETUP"):
                meta[p[0]] = (float(p[1]), int(p[2]))
    return ck, net, meta


def err_stats(d):
    if not d:
        return None
    a = sorted(abs(x) for x in d)
    n = len(d)
    return {"n": n, "mean": round(sum(d) / n, 2), "mean_abs": round(sum(a) / n, 2),
            "p95_abs": round(a[min(n - 1, int(0.95 * n))], 2), "max_abs": round(a[-1], 2),
            "std": round(math.sqrt(sum((x - sum(d) / n) ** 2 for x in d) / n), 2)}


def compare(ref, est):
    rck, rnet, rmeta = read_probe(ref)
    eck, enet, emeta = read_probe(est)
    dck = [eck[k] - rck[k] for k in eck if k in rck]
    dnet = [enet[k] - rnet[k] for k in enet if k in rnet]
    rel = [(enet[k] - rnet[k]) / rnet[k] for k in enet if k in rnet and rnet[k] > 5.0]
    out = {"clock_arrival": err_stats(dck), "net_delay": err_stats(dnet),
           "net_delay_rel_mean": round(sum(rel) / len(rel), 3) if rel else None,
           "hold_wns_est": emeta.get("HOLD"), "hold_wns_rcx": rmeta.get("HOLD"),
           "setup_wns_est": emeta.get("SETUP"), "setup_wns_rcx": rmeta.get("SETUP")}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    e = sp.add_parser("emit"); e.add_argument("--scales", required=True); e.add_argument("--out", required=True)
    e.add_argument("--header", default="")
    f = sp.add_parser("fit"); f.add_argument("--wire", nargs="+", required=True); f.add_argument("--spef", nargs="+", required=True)
    f.add_argument("--layers", default="M2,M3,M4,M5"); f.add_argument("--out"); f.add_argument("--sigtype")
    f.add_argument("--min-len", type=float, default=5.0)
    n = sp.add_parser("nets"); n.add_argument("--wire", required=True); n.add_argument("--n", type=int, default=200)
    n.add_argument("--out", required=True)
    c = sp.add_parser("cmp"); c.add_argument("--ref", required=True); c.add_argument("--est", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "emit":
        params = json.loads(open(a.scales).read()) if not a.scales.lstrip().startswith("{") else json.loads(a.scales)
        open(a.out, "w").write(emit_tcl(params, a.header))
    elif a.cmd == "fit":
        wire, spef = {}, {}
        for w, s in zip(a.wire, a.spef):
            wd = parse_wire(w)
            sd = parse_spef(s, set(wd))
            tag = w + ":"
            wire.update({tag + k: v for k, v in wd.items()})
            spef.update({tag + k: v for k, v in sd.items()})
        r = fit_layers(wire, spef, a.layers.split(","), a.min_len, a.sigtype)
        s = json.dumps(r, indent=1)
        if a.out:
            open(a.out, "w").write(s)
        print(s)
    elif a.cmd == "nets":
        w = parse_wire(a.wire)
        tot = sorted(((sum(v for k, v in acc.items() if not k.startswith("V@")), nm)
                      for nm, (st, acc) in w.items() if st == "SIGNAL"), reverse=True)
        open(a.out, "w").write("\n".join(nm for _, nm in tot[:a.n]) + "\n")
    elif a.cmd == "cmp":
        print(json.dumps(compare(a.ref, a.est)))


if __name__ == "__main__":
    main()
