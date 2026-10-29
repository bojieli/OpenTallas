#!/usr/bin/env python3
"""CLK-INV-CAL-1: inverter clock-tree calibration of the ONE shared die timing model (METHODOLOGY 12.4a b1 / 12.15b).

The shared model was calibrated on BUFx24 only: AOCV class A (clk_aocv_mc.py, 400-sample BSIM-CMG Monte Carlo with
Pelgrom A_VT 1.2 mV.um per transistor) and the OpenSTA-vs-ngspice clock scale x1.0485 TT / x1.0552 FF (OSS-CLOCK-2,
affine per-sink fit spice = a x STA + b over ngspice trees of the same netlist).  The release clock cell is now the
inverter CKINVDCx16 (die_trial --clock-cell inv / inv2).  This tool repeats BOTH methods on the inverter, both edges:

  mcgen / mcparse / mcfit   the clk_aocv_mc.py Monte Carlo, unchanged method (same mismatch model, same cards, same
                            extracted cells, stage = cell -> wire -> next cell, stage 1 dropped), on an INVERTING chain
                            driven by a pulse, so every stage gives an output-rise and an output-fall delay.  Fitted
                            per inverter (class 'Ainv': a branch of N inverters, edge alternates fall/rise) and per
                            inverter PAIR (class 'Ainv2', inv2 legs), plus the per-stage fall-rise asymmetry.
  glob                      process-only SS/TT/FF delay of the cell (information; g stays the OWNER 0.21 %/mm).
  treegen / compare         OSS-CLOCK spice-scale method: one comb tree (trunk of N stages, a 2-stage side branch to a
                            sink every K stages) emitted as ngspice deck AND Verilog+SPEF+OpenSTA Tcl with the same cells
                            and RC ladders; per-sink arrivals of both edges; spice = a x STA + b least squares (slope a =
                            per-stage scale; b = root offset, cancels in skew / crossing d).  --cell buf repeats the
                            BUFx24 control so the method is checked against the published 1.0485 / 1.0552.

    clk_inv_cal.py mcgen --lib L --out D --corner TT --wire-um 250 --samples 400 --seed 21
    clk_inv_cal.py mcparse D... --out mc_inv.json
    clk_inv_cal.py mcfit mc_inv.json --out inv_rows.json
    clk_inv_cal.py treegen --out D --cell inv --wire-um 250 --stages 160 --every 8 --libdir /w/lib --osdi /w/osdi/..
    clk_inv_cal.py compare D --corner TT
"""
import argparse
import json
import math
import random
import re
import statistics as st
import sys
from pathlib import Path

AVT_MV_UM = 1.2
HFIN_NM, TFIN_NM, L_NM = 32.0, 6.5, 20.0
CORNER = {"TT": dict(vdd=0.70, temp=25), "FF": dict(vdd=0.77, temp=0)}
CELLS = {"inv": dict(cell="CKINVDCx16_ASAP7_75t_R", inverting=True),
         "buf": dict(cell="BUFx24_ASAP7_75t_R", inverting=False)}
# die_trial.py clock RC (ASAP7 setRC M8/M9 mean; NDR 2W2S = R/2, C x 1.1), kohm/um -> ohm/um
WIRE_NDR = dict(r_ohm_um=(8.44765e-3 + 8.89556e-3) / 2 / 2 * 1e3, c_ff_um=(1.03962e-1 + 9.28446e-2) / 2 * 1.1)
WIRE_1X = dict(r_ohm_um=(8.44765e-3 + 8.89556e-3) / 2 * 1e3, c_ff_um=(1.03962e-1 + 9.28446e-2) / 2)
PI_UM = 45.0
PULSE_PS = 1500.0


def sigma_vt_v(nfin):
    return AVT_MV_UM / math.sqrt(nfin * (2 * HFIN_NM + TFIN_NM) * 1e-3 * L_NM * 1e-3) * 1e-3


def subckt(cells_sp, name):
    out, on = [], False
    for ln in Path(cells_sp).read_text().splitlines():
        if ln.lower().startswith(".subckt") and ln.split()[1] == name:
            on = True
        if on:
            out.append(ln)
            if ln.lower().startswith(".ends"):
                break
    if not out:
        raise SystemExit(f"{name} not in {cells_sp}")
    return out


def mc_subckt(lines, new):
    """as clk_aocv_mc.mc_subckt: every OSDI device gets delvtrand={dk}."""
    body, nf, k, f = [], [], 0, None
    for ln in lines:
        if ln.lower().startswith(".subckt"):
            f = ln.split()
            continue
        if ln[:1] == "N":
            nf.append(int(re.search(r"nfin=(\d+)", ln).group(1)))
            ln = f"{ln} delvtrand={{d{k}}}"
            k += 1
        body.append(ln)
    head = f".subckt {new} {' '.join(f[2:])} " + " ".join(f"d{i}=0" for i in range(k))
    return "\n".join([head] + body[:-1] + [".ends"]), nf


def ladder(prefix, a, b, L, w, nseg=None):
    n = nseg or max(1, int(math.ceil(L / PI_UM - 1e-9)))
    rs, cs = w["r_ohm_um"] * L / n, w["c_ff_um"] * L / n
    out, prev = [], a
    for j in range(n):
        nx = f"{prefix}_{j}" if j < n - 1 else b
        out += [f"C{prefix}_{j}a {prev} 0 {cs / 2:.5f}f", f"R{prefix}_{j} {prev} {nx} {rs:.4f}",
                f"C{prefix}_{j}b {nx} 0 {cs / 2:.5f}f"]
        prev = nx
    return out


def pwl_pulse(vdd, ramp=40.0, t0=100.0, w=PULSE_PS):
    return (f"PWL(0 0 {t0:.0f}p 0 {t0 + ramp:.0f}p {vdd} {t0 + w:.0f}p {vdd} {t0 + w + ramp:.0f}p 0)")


# ------------------------------------------------------------------------------------------------ Monte Carlo
def mcgen(a):
    cell = CELLS[a.cell]["cell"]
    co = CORNER[a.corner]
    w = WIRE_1X if a.rc == "1x" else WIRE_NDR
    sc, nf = mc_subckt(subckt(Path(a.lib) / a.corner / "cells.sp", cell), "MCC")
    sig = [sigma_vt_v(n) for n in nf]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(a.seed)
    D, vdd = a.depth, co["vdd"]
    vec = " ".join(f"v(n{i}) v(o{i})" for i in range(1, D + 1)) + f" v(n{D + 1})"
    meta = dict(cell=cell, cls=a.cls, corner=a.corner, depth=D, samples=a.samples, seed=a.seed, wire_um=a.wire_um,
                rc=a.rc, wire=w, pi_um=PI_UM, pulse_ps=PULSE_PS, avt_mv_um=AVT_MV_UM, weff_fin_nm=2 * HFIN_NM + TFIN_NM,
                l_nm=L_NM, sigma_vt_mv={str(n): round(sigma_vt_v(n) * 1e3, 3) for n in sorted(set(nf))},
                devices_per_cell=len(nf), corner_def=co, inverting=CELLS[a.cell]["inverting"])
    (out / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")
    tend = 100 + PULSE_PS + 140 + D * 90 + 300
    for s in range(a.samples):
        L = [f"* CLK-INV-CAL MC {cell} {a.corner} wire {a.wire_um} sample {s}", ".control", f"pre_osdi {a.osdi}",
             "set noaskquit", "run", f"wrdata /w/run/{out.name}/s{s:04d}.dat {vec}", "quit", ".endc", ".options klu",
             f".save {vec}", f".temp {co['temp']}", f".include {a.libw}/{a.corner}/models.sp",
             f".include {a.libw}/{a.corner}/cells.sp", sc, f"Vdd vdd 0 {vdd}", "Vss vss 0 0",
             f"Vin in 0 {pwl_pulse(vdd)}", f"Xp1 vss vdd in p1 {cell}", f"Xp2 vss vdd p1 n1 {cell}"]
        for i in range(1, D + 1):
            d = [0.0] * len(nf) if s == 0 else [rng.gauss(0.0, g) for g in sig]
            L.append(f"X{i} vss vdd n{i} o{i} MCC " + " ".join(f"d{k}={v:.6e}" for k, v in enumerate(d)))
            L += ladder(f"w{i}", f"o{i}", f"n{i + 1}", a.wire_um, w)
        L.append(f"Xend vss vdd n{D + 1} oend {cell}")
        L += [f".tran 1p {tend:.0f}p 0 1p", ".end"]
        (out / f"s{s:04d}.sp").write_text("\n".join(L) + "\n")
    print(out, a.samples, "decks", len(nf), "devices/cell", meta["sigma_vt_mv"])


def crossings_all(path, vh):
    """wrdata (t, v) column pairs -> per vector [(t, +1 rise | -1 fall), ...] of every vh crossing."""
    rows = [list(map(float, ln.split())) for ln in Path(path).read_text().splitlines() if ln.strip()]
    nv = len(rows[0]) // 2
    res = []
    for v in range(nv):
        hits, tp, xp = [], None, None
        for r in rows:
            t, x = r[2 * v], r[2 * v + 1]
            if xp is not None and ((xp < vh <= x) or (xp >= vh > x)):
                hits.append((tp + (vh - xp) * (t - tp) / (x - xp), 1 if x > xp else -1))
            tp, xp = t, x
        res.append(hits)
    return res


def mcparse(a):
    out = {}
    for dd in map(Path, a.decks):
        meta = json.loads((dd / "meta.json").read_text())
        vh, D = meta["corner_def"]["vdd"] / 2, meta["depth"]
        S = []
        for f in sorted(dd.glob("s*.dat")):
            c = crossings_all(f, vh)
            if any(len(x) != 2 for x in c):
                continue                       # one input pulse: exactly 2 clean crossings per node
            n = [c[2 * i] for i in range(D)] + [c[2 * D]]
            o = [c[2 * i + 1] for i in range(D)]
            rec = dict(s=int(f.stem[1:]))
            for e in (0, 1):                   # e 0 = input rising edge, 1 = input falling edge
                rec[f"cell{e}"] = [(o[i][e][0] - n[i][e][0]) * 1e12 for i in range(D)]
                rec[f"stage{e}"] = [(n[i + 1][e][0] - n[i][e][0]) * 1e12 for i in range(D)]
                rec[f"odir{e}"] = [o[i][e][1] for i in range(D)]      # +1 output rises
            S.append(rec)
        out[f"{meta['cls']}_{meta['corner']}"] = dict(meta=meta, samples=S)
    Path(a.out).write_text(json.dumps(out) + "\n")
    print({k: len(v["samples"]) for k, v in out.items()})


def corr(x, y):
    mx, my, sx, sy = st.mean(x), st.mean(y), st.pstdev(x), st.pstdev(y)
    return sum((p - mx) * (q - my) for p, q in zip(x, y)) / len(x) / (sx * sy)


def path_fit(groups):
    """groups: [per sample list of the used stage delays] per propagating edge -> sigma_N, a N + b N^2 (clk_aocv_fit
    method); the prefix-sum variance is taken per edge (the two edges have different means) and averaged."""
    pts = []
    for n in range(1, len(groups[0][0]) + 1):
        pts.append((n, st.mean(st.pvariance([sum(x[:n]) for x in seqs]) for seqs in groups)))
    S2, S3, S4 = (sum(n ** k for n, _ in pts) for k in (2, 3, 4))
    B1, B2 = sum(n * v for n, v in pts), sum(n * n * v for n, v in pts)
    det = S2 * S4 - S3 * S3
    return dict(a_ps2_per_stage=round((B1 * S4 - B2 * S3) / det, 4), b_ps2_per_stage2=round((S2 * B2 - S3 * B1) / det, 5),
                sigma_N_ps={str(n): round(math.sqrt(v), 3) for n, v in pts},
                note="sigma_N^2 = a N + b N^2 on the simulated prefix sums of one propagating edge; b = non-averaging part")


def fit_rows(rec, pair=False):
    """class row in the clk_aocv schema.  Per inverter (pair=False): the stage sequence of ONE propagating edge
    alternates output fall / rise; mu/s pooled over both edges and all used stages (a branch of N inverters holds
    N/2 of each), rho = lag correlations along the edge.  pair=True: stage = 2 consecutive inverters (inv2 leg),
    pairs (1,2),(3,4),... of the used stages."""
    S = rec["samples"]
    nom = next(s for s in S if s["s"] == 0)
    mc = [s for s in S if s["s"] > 0]
    D = len(nom["stage0"])
    use = list(range(1, D))                                   # stage 1 sees the pre-driver slew: dropped
    if pair:
        use = use[: len(use) // 2 * 2]
        grp = [(use[k], use[k + 1]) for k in range(0, len(use), 2)]
    else:
        grp = [(i,) for i in use]

    def val(s, key, g):
        return sum(s[key][i] for i in g)
    mu_cell = st.mean(val(nom, f"cell{e}", g) for e in (0, 1) for g in grp)
    mu_stage = st.mean(val(nom, f"stage{e}", g) for e in (0, 1) for g in grp)
    sig = [st.stdev([val(s, f"stage{e}", g) for s in mc]) for e in (0, 1) for g in grp]
    s_stage = math.sqrt(st.mean(v * v for v in sig))
    rho = []
    for lag in (1, 2):
        xs, ys = [], []
        for e in (0, 1):
            for k in range(len(grp) - lag):
                # centred per stage: out-rise and out-fall stages alternate with different means, and pooling
                # uncentred series would turn that mean difference into a fake +-1 lag correlation
                x = [val(s, f"stage{e}", grp[k]) for s in mc]
                y = [val(s, f"stage{e}", grp[k + lag]) for s in mc]
                mx, my = st.mean(x), st.mean(y)
                xs += [v - mx for v in x]
                ys += [v - my for v in y]
        rho.append(round(corr(xs, ys), 4) if xs else 0.0)
    # by output edge (single inverter): output rise / fall cell + stage delay, sigma
    by = {}
    if not pair:
        for dname, dv in (("out_rise", 1), ("out_fall", -1)):
            cells, stages, sg = [], [], []
            for e in (0, 1):
                for i in use:
                    if nom[f"odir{e}"][i] == dv:
                        cells.append(nom[f"cell{e}"][i])
                        stages.append(nom[f"stage{e}"][i])
                        sg.append(st.stdev([s[f"stage{e}"][i] for s in mc]))
            by[dname] = dict(mu_cell_ps=round(st.mean(cells), 3), mu_stage_ps=round(st.mean(stages), 3),
                             sigma_stage_ps=round(math.sqrt(st.mean(v * v for v in sg)), 4),
                             s_cell=round(math.sqrt(st.mean(v * v for v in sg)) / st.mean(cells), 5))
        asym = by["out_fall"]["mu_stage_ps"] - by["out_rise"]["mu_stage_ps"]
    else:
        # pair: an input-rise edge through the pair vs an input-fall edge (polarity-true leg); difference = duty shift
        r = st.mean(val(nom, "stage0", g) for g in grp)
        f = st.mean(val(nom, "stage1", g) for g in grp)
        asym = f - r
        by = dict(edge_in_rise_stage_ps=round(r, 3), edge_in_fall_stage_ps=round(f, 3))
    groups = [[[val(s, f"stage{e}", g) for g in grp] for s in mc] for e in (0, 1)]
    g3 = [val(s, "stage0", grp[min(1, len(grp) - 1)]) for s in mc]
    m3, s3 = st.mean(g3), st.pstdev(g3)
    return dict(mu_cell_ps=round(mu_cell, 3), mu_stage_ps=round(mu_stage, 3), cell_share=round(mu_cell / mu_stage, 4),
                sigma_stage_ps=round(s_stage, 4), s_cell=round(s_stage / mu_cell, 5),
                rho=[max(0.0, x) for x in rho], rho_measured=rho,
                rho_note="negative measured lag correlations clamped to 0 (conservative: no credit for slew anti-correlation)",
                mc_samples=len(mc), stages_used=len(grp), by_edge=by,
                fall_minus_rise_ps_per_stage=round(asym, 3),
                path_fit=path_fit(groups), stage_skewness=round(st.mean(((x - m3) / s3) ** 3 for x in g3), 3))


def mcfit(a):
    mc = json.loads(Path(a.mc).read_text())
    out = {}
    for k, rec in mc.items():
        cls, corner = k.rsplit("_", 1)
        m = rec["meta"]
        d1 = fit_rows(rec)
        d2 = fit_rows(rec, pair=True)
        info = {x: m[x] for x in ("cell", "depth", "samples", "seed", "wire_um", "rc", "wire", "pi_um", "avt_mv_um",
                                  "sigma_vt_mv", "devices_per_cell", "corner_def")}
        out.setdefault(cls, {})[corner] = dict(inv=dict(d1, mc=info), inv2=dict(d2, mc=info))
        print(cls, corner, "inv", {x: d1[x] for x in ("mu_cell_ps", "mu_stage_ps", "s_cell", "rho",
                                                      "fall_minus_rise_ps_per_stage")},
              "| inv2", {x: d2[x] for x in ("mu_cell_ps", "mu_stage_ps", "s_cell", "rho", "fall_minus_rise_ps_per_stage")})
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")


def envelope(rows):
    """one gate row from the per-wire-length rows of one corner: s_cell, rho and cell_share = the max (the conservative
    side: a larger cell share puts more of the branch under the random + droop cell derate than under the flat 3 % net
    derate), mu_cell / mu_stage of the longest measured wire (QC / HEAD rep 200-250)."""
    L = max(rows, key=float)
    r = dict(rows[L])
    r["s_cell"] = max(x["s_cell"] for x in rows.values())
    r["cell_share"] = max(x["cell_share"] for x in rows.values())
    r["rho"] = [max(x["rho"][i] for x in rows.values()) for i in range(2)]
    r["envelope"] = dict(wire_um=sorted(float(k) for k in rows), rule="s_cell / rho / cell_share = max over the "
                         "measured wire lengths; mu from the longest", mu_from_wire_um=float(L))
    return r


def table(a):
    """insert classes Ainv (per CKINVDCx16) and Ainv2 (per inverter pair) into the clock_aocv table (A / B / systematic /
    droop / net rows untouched), the measured rows per wire length under clock_cells, and re-render the grids."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import clk_aocv as CA
    D = json.loads(Path(a.table).read_text())
    T = D["clock_aocv"]
    R = json.loads(Path(a.rows).read_text())          # {"Ainv250": {"TT": {"inv": row, "inv2": row}, ...}, ...}
    by = {}
    for cls, cc in R.items():
        L = cls.replace("Ainv", "")
        for c, v in cc.items():
            for k in ("inv", "inv2"):
                by.setdefault(k, {}).setdefault(c, {})[L] = v[k]
    T["classes"]["Ainv"] = {c: envelope(v) for c, v in by["inv"].items()}
    T["classes"]["Ainv2"] = {c: envelope(v) for c, v in by["inv2"].items()}
    gl = json.loads(Path(a.glob).read_text()) if a.glob else None
    T["clock_cells"] = dict(
        map={"BUFx24_ASAP7_75t_R": "A", "CKINVDCx16_ASAP7_75t_R": "Ainv"},
        note="CLK-INV-CAL-1 (2026-10-28): die clock cell -> die-stage class. Ainv = one CKINVDCx16 stage (inv and inv2 "
             "trees: a branch counts every inverter); Ainv2 = one inverter pair (inv2 leg), information/planner form of "
             "the same MC. Same method as class A (clk_aocv_mc.py: BSIM-CMG 111, A_VT 1.2 mV.um per transistor, ASAP7 "
             "r1p7 xAct3D cells, stage = cell -> NDR M8/M9 wire -> next cell, stage 1 dropped), on an inverting chain "
             "with both edges (tools/die_plan/clk_inv_cal.py). g / droop / net rows are shared (OWNER 0.21 %/mm).",
        rows_by_wire_um={k: v for k, v in by.items()}, process_only_delay_ps=gl)
    new = CA.table(T)["grids"]                     # render the new classes only; the stored A / B grids stay as signed
    for g, v in new.items():
        if g.split("_")[0] in ("Ainv", "Ainv2"):
            T["table"]["grids"][g] = v
    Path(a.out).write_text(json.dumps(D, indent=1) + "\n")
    for k in ("Ainv", "Ainv2"):
        for c, r in T["classes"][k].items():
            print(k, c, {x: r[x] for x in ("mu_cell_ps", "mu_stage_ps", "cell_share", "s_cell", "rho")})


# ------------------------------------------------------------------------------------------------ spice vs OpenSTA
def comb(stages, every, branch):
    """trunk t0..t{stages-1}; after every `every` trunk stages a side branch of `branch` stages ends at a sink.
    -> (cells, edges [(drv, load, L_factor)], sinks)"""
    cells = [f"t{i}" for i in range(stages)]
    edges = [(f"t{i}", f"t{i + 1}") for i in range(stages - 1)]
    sinks = []
    for i in range(every - 1, stages, every):
        prev = f"t{i}"
        for j in range(branch):
            b = f"s{i}_{j}"
            cells.append(b)
            edges.append((prev, b))
            prev = b
        sinks.append(prev)
    return cells, edges, sinks


def treegen(a):
    d = Path(a.out)
    d.mkdir(parents=True, exist_ok=True)
    cell = CELLS[a.cell]["cell"]
    w = WIRE_1X if a.rc == "1x" else WIRE_NDR
    cells, edges, sinks = comb(a.stages, a.every, a.branch)
    root = "t0"
    meas = [root] + sinks
    # ---- ngspice
    for c in ("TT", "FF"):
        v = CORNER[c]["vdd"]
        L = [f"* CLK-INV-CAL comb tree {cell} {c} wire {a.wire_um} {a.rc}", ".control", f"pre_osdi {a.osdi}",
             "set noaskquit", "run", f"wrdata arr_{c}.dat " + " ".join(f"v(i_{s})" for s in meas), "quit", ".endc",
             ".options klu", ".save " + " ".join(f"v(i_{s})" for s in meas), f".temp {CORNER[c]['temp']}",
             f".include {a.libdir}/{c}/models.sp", f".include {a.libdir}/{c}/cells.sp", f"Vdd vdd 0 {v}", "Vss vss 0 0",
             f"Vin src 0 {pwl_pulse(v, w=a.pulse_ps)}", f"Xp1 vss vdd src p1 {cell}", f"Xp2 vss vdd p1 i_{root} {cell}"]
        for b in cells:
            L.append(f"X{b} vss vdd i_{b} o_{b} {cell}")
        for k, (dr, ld) in enumerate(edges):
            L += ladder(f"e{k}", f"o_{dr}", f"i_{ld}", a.wire_um, w)
        for s in sinks:
            L.append(f"Cl_{s} o_{s} 0 {a.sink_ff}f")
        tend = 100 + a.pulse_ps + (a.stages + a.branch) * (60 if a.cell == "inv" else 140) + 800
        L += [f".tran 1p {tend:.0f}p", ".end"]
        (d / f"deck_{c}.sp").write_text("\n".join(L) + "\n")
    # ---- Verilog + SPEF + OpenSTA (same cells, same ladders)
    drv_of = {ld: dr for dr, ld in edges}
    V = [f"module comb_tree (src, {', '.join('q_' + s for s in sinks)});", "input src;"]
    V += [f"output q_{s};" for s in sinks]
    nets = {"p1", f"i_{root}"} | {f"o_{b}" for b in cells}
    V += [f"wire {n};" for n in sorted(nets)]
    V += [f"{cell} xp1 (.A(src), .Y(p1));", f"{cell} xp2 (.A(p1), .Y(i_{root}));"]
    for b in cells:
        inn = f"o_{drv_of[b]}" if b in drv_of else f"i_{b}"
        V.append(f"{cell} x_{b} (.A({inn}), .Y({'q_' + b if b in sinks else 'o_' + b}));")
    V.append("endmodule")
    (d / "comb_tree.v").write_text("\n".join(V) + "\n")
    H = ['*SPEF "IEEE 1481-1998"', '*DESIGN "comb_tree"', '*DATE "-"', '*VENDOR "opentallas"', '*PROGRAM "clk_inv_cal"',
         '*VERSION "1"', '*DESIGN_FLOW "PIN_CAP NONE"', '*DIVIDER /', '*DELIMITER :', '*BUS_DELIMITER [ ]',
         '*T_UNIT 1 PS', '*C_UNIT 1 FF', '*R_UNIT 1 OHM', '*L_UNIT 1 HENRY', ""]
    by = {}
    for dr, ld in edges:
        by.setdefault(dr, []).append(ld)
    for dr, lds in by.items():
        n = max(1, int(math.ceil(a.wire_um / PI_UM - 1e-9)))
        rs, cs = w["r_ohm_um"] * a.wire_um / n, w["c_ff_um"] * a.wire_um / n
        caps, ress, nid, tot = {}, [], 0, 0.0
        for ld in lds:
            prev = f"x_{dr}:Y"
            for j in range(n):
                if j < n - 1:
                    nid += 1
                    nx = f"o_{dr}:{nid}"
                else:
                    nx = f"x_{ld}:A"
                caps[prev] = caps.get(prev, 0.0) + cs / 2
                caps[nx] = caps.get(nx, 0.0) + cs / 2
                ress.append((prev, nx, rs))
                tot += cs
                prev = nx
        H += [f"*D_NET o_{dr} {tot:.5f}", "*CONN", f"*I x_{dr}:Y O"] + [f"*I x_{ld}:A I" for ld in lds] + ["*CAP"]
        H += [f"{i + 1} {k} {v:.5f}" for i, (k, v) in enumerate(caps.items())] + ["*RES"]
        H += [f"{i + 1} {p} {q} {r:.4f}" for i, (p, q, r) in enumerate(ress)] + ["*END", ""]
    (d / "comb_tree.spef").write_text("\n".join(H) + "\n")
    for c in ("TT", "FF"):
        T = [f"read_liberty lib_{c}.lib", "read_verilog comb_tree.v", "link_design comb_tree", "read_spef comb_tree.spef",
             "create_clock -name vclk -period 10000", "set_input_delay 0 -clock vclk [get_ports src]",
             f"set_input_transition {40.0 * 0.8:.2f} [get_ports src]", f"set_load {a.sink_ff} [all_outputs]",
             "set_output_delay 0 -clock vclk [all_outputs]", "report_checks -group_count 1 -digits 3",
             f"set f [open sta_arr_{c}.txt w]",
             f"foreach p [list {' '.join(f'x_{s}/A' for s in meas)}] {{",
             "  set pin [get_pins $p]",
             "  puts $f \"$p [get_property $pin arrival_max_rise] [get_property $pin arrival_max_fall]\"", "}",
             "close $f",
             # min analysis (hold / early): OpenSTA takes the LOW end of the liberty capacitance_range of every load
             # pin (CKINVDCx16 A: 6.68-9.54 fF, BUFx24 A: 1.76-2.35 fF), so early = a lighter load, not variation
             f"set f [open sta_arr_min_{c}.txt w]",
             f"foreach p [list {' '.join(f'x_{s}/A' for s in meas)}] {{",
             "  set pin [get_pins $p]",
             "  puts $f \"$p [get_property $pin arrival_min_rise] [get_property $pin arrival_min_fall]\"", "}",
             "close $f"]
        (d / f"sta_{c}.tcl").write_text("\n".join(T) + "\n")
    par = {}
    depth = {root: 0}
    for dr, ld in edges:
        depth[ld] = depth[dr] + 1
    for s in meas:
        par[s] = depth[s] % 2 if CELLS[a.cell]["inverting"] else 0
    (d / "meas.json").write_text(json.dumps(dict(cell=cell, inverting=CELLS[a.cell]["inverting"], root=root, sinks=sinks,
                                                 depth={s: depth[s] for s in meas}, parity=par, wire_um=a.wire_um,
                                                 rc=a.rc, wire=w, sink_ff=a.sink_ff, stages=a.stages, every=a.every,
                                                 branch=a.branch)) + "\n")
    print(d, len(cells), "cells", len(sinks), "sinks")


def affine(X):
    n = len(X)
    mx, my = sum(m for m, _ in X) / n, sum(p for _, p in X) / n
    a = sum((m - mx) * (p - my) for m, p in X) / sum((m - mx) ** 2 for m, _ in X)
    b = my - a * mx
    ra = [p - (a * m + b) for m, p in X]
    s = sum(m * p for m, p in X) / sum(m * m for m, _ in X)
    return dict(slope=round(a, 4), offset_ps=round(b, 1), affine_resid_ps=[round(min(ra), 2), round(max(ra), 2)],
                scale_through_origin=round(s, 4), points=n)


def compare(a):
    d = Path(a.dir)
    M = json.loads((d / "meas.json").read_text())
    c = a.corner
    vh = CORNER[c]["vdd"] / 2
    meas = [M["root"]] + M["sinks"]
    cr = crossings_all(d / f"arr_{c}.dat", vh)
    sta = {}
    mn = getattr(a, "analysis", "max") == "min"
    for ln in (d / (f"sta_arr_min_{c}.txt" if mn else f"sta_arr_{c}.txt")).read_text().splitlines():
        p, r, f = ln.split()
        sta[p.split("/")[0][2:]] = (float(r), float(f))
    root_sp = cr[0]           # [(t, dir)] edge 0 = rise (true polarity), edge 1 = fall
    rows = []
    for s, x in zip(meas[1:], cr[1:]):
        if len(x) < 2:
            continue
        p = M["parity"][s]
        for e in (0, 1):
            t, dr = x[e]
            sp = (t - root_sp[e][0]) * 1e12
            # STA: rising arrival at the sink pin comes from the root edge of the same parity
            rs, fs = sta[s]
            r0, f0 = sta[M["root"]]
            if dr > 0:
                st_ = rs - (r0 if p == 0 else f0)
            else:
                st_ = fs - (f0 if p == 0 else r0)
            rows.append(dict(sink=s, depth=M["depth"][s], in_edge="rise" if e == 0 else "fall",
                             sink_edge="rise" if dr > 0 else "fall", sta=round(st_, 2), spice=round(sp, 2)))
    out = dict(corner=c, analysis="min" if mn else "max", cell=M["cell"], wire_um=M["wire_um"], rc=M["rc"], sinks=len(meas) - 1,
               all=affine([(r["sta"], r["spice"]) for r in rows]),
               sink_rise=affine([(r["sta"], r["spice"]) for r in rows if r["sink_edge"] == "rise"]),
               sink_fall=affine([(r["sta"], r["spice"]) for r in rows if r["sink_edge"] == "fall"]),
               true_polarity_rise=affine([(r["sta"], r["spice"]) for r in rows if r["in_edge"] == "rise"]),
               sta_range_ps=[min(r["sta"] for r in rows), max(r["sta"] for r in rows)])
    # duty: fall - rise at true-polarity even sinks (spice vs STA)
    ev = {}
    for r in rows:
        ev.setdefault(r["sink"], {})[r["in_edge"]] = r
    dd = [(v["fall"]["spice"] - v["rise"]["spice"], v["fall"]["sta"] - v["rise"]["sta"], M["depth"][k])
          for k, v in ev.items() if "rise" in v and "fall" in v]
    out["duty_shift_fall_minus_rise_ps"] = dict(spice=[round(min(x[0] for x in dd), 2), round(max(x[0] for x in dd), 2)],
                                                sta=[round(min(x[1] for x in dd), 2), round(max(x[1] for x in dd), 2)])
    (d / (f"compare_min_{c}.json" if mn else f"compare_{c}.json")).write_text(json.dumps(dict(summary=out, rows=rows), indent=1) + "\n")
    print(json.dumps(out))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    g = sp.add_parser("mcgen")
    g.add_argument("--lib", required=True)
    g.add_argument("--libw", default="/w/lib")
    g.add_argument("--osdi", default="/w/osdi/bsimcmg23.osdi")
    g.add_argument("--out", required=True)
    g.add_argument("--cell", choices=sorted(CELLS), default="inv")
    g.add_argument("--cls", default="Ainv")
    g.add_argument("--corner", choices=sorted(CORNER), required=True)
    g.add_argument("--wire-um", type=float, default=250.0)
    g.add_argument("--rc", choices=("ndr", "1x"), default="ndr")
    g.add_argument("--samples", type=int, default=400)
    g.add_argument("--seed", type=int, default=21)
    g.add_argument("--depth", type=int, default=8)
    p = sp.add_parser("mcparse")
    p.add_argument("decks", nargs="+")
    p.add_argument("--out", required=True)
    f = sp.add_parser("mcfit")
    f.add_argument("mc")
    f.add_argument("--out", required=True)
    t = sp.add_parser("treegen")
    t.add_argument("--out", required=True)
    t.add_argument("--cell", choices=sorted(CELLS), default="inv")
    t.add_argument("--wire-um", type=float, default=250.0)
    t.add_argument("--rc", choices=("ndr", "1x"), default="ndr")
    t.add_argument("--stages", type=int, default=160)
    t.add_argument("--every", type=int, default=8)
    t.add_argument("--branch", type=int, default=2)
    t.add_argument("--sink-ff", type=float, default=5.0)
    t.add_argument("--pulse-ps", type=float, default=2500.0)
    t.add_argument("--libdir", default="/w/lib")
    t.add_argument("--osdi", default="/w/osdi/bsimcmg23.osdi")
    tb = sp.add_parser("table")
    tb.add_argument("table")
    tb.add_argument("rows")
    tb.add_argument("--glob")
    tb.add_argument("--out", required=True)
    c = sp.add_parser("compare")
    c.add_argument("--analysis", choices=("max", "min"), default="max",
                   help="STA arrival analysis to fit spice against (min = hold/early readout sta_arr_min_<C>.txt)")
    c.add_argument("dir")
    c.add_argument("--corner", default="TT")
    a = ap.parse_args(argv)
    return dict(mcgen=mcgen, mcparse=mcparse, mcfit=mcfit, treegen=treegen, compare=compare, table=table)[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
