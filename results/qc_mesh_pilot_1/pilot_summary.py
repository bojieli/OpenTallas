#!/usr/bin/env python3
"""QC-MESH-PILOT-1 summary over trials: pair U (signed-mesh formula), insertion, driver-input spread, tap stability
between trials (nominal mesh-tap arrivals, region-relative), A0 core-tap branch, hold-buffer count (DIE-QC-23 hb_est23
method with the measured windows), clock power and M8/M9 tracks.  usage: pilot_summary.py STAGE HB_EST23.json OUT.json T1 T2 ..
Every number UNCHECKED until NUMBER-CHECK."""
import json
import math
import re
import sys
from pathlib import Path

stage, hbf, outf = sys.argv[1:4]
trials = sys.argv[4:]
HB = json.load(open(hbf))
hbrow = {r["part"]: r for r in HB["rows"]}
FF_EARLY = 44.6
k = lambda d: max(0, math.ceil(d / FF_EARLY - 1e-9))
SIG = {"TT": 2.0743, "FF": 1.5694}       # AOCV class-A sigma per stage (QC-MESH-EST-1 basis)
out = dict(stage=stage, trials={}, checked="UNCHECKED")
nom = {}
for t in trials:
    T = Path(t)
    J = json.load(open(T / "pilot.json"))
    g = J["geom"]
    P = json.load(open(T / f"pair_{stage}.json"))
    rec = json.load(open(T / f"rec_{stage}.json"))
    r = dict(part=g["part"], adjust=g["adjust"], corners={})
    for C in ("TT", "FF"):
        pc = P["corners"][C]
        S = json.load(open(T / f"mc_{stage}_{C}.json"))
        nom[(t, C)] = dict(zip(S["loads"], S["routed"]))
        dA = [n["arr"][C]["late"] for n in rec["nodes"] if n["driver"]]
        # glue <-> A0 core pairs: unshared = core branch (E0, Q, E1: 3 stages) vs mesh path (R..driver: 7 stages) + mesh U
        mesh_u = pc["pair_U_max_ps"]
        aocv = 3 * SIG[C] * math.sqrt(3 + 7)
        off = pc["core_early_error_ps"]
        wc = off + aocv + mesh_u / 2
        wc_planned = aocv + mesh_u / 2          # offset closed by construction (core branch joined upstream, plan-computed)
        r["corners"][C] = dict(pair_U_max_ps=mesh_u, pair_U_p50_ps=pc["pair_U_p50_ps"], nominal_skew_ps=pc["nominal_skew_ps"],
                               mc=pc["mc"], driver_input_spread_ps=round(max(dA) - min(dA), 2),
                               insertion_root_to_mesh_ps=pc["insertion_root_to_mesh_median_ps"],
                               trial14_glue_spread_ps=pc["trial14_glue_spread_ps"],
                               core_required_early_ps=pc["trial14_glue_median_minus_core_median_ps"],
                               core_got_early_ps=pc["core_tap_early_vs_mesh_ps"], core_offset_error_ps=off,
                               W_core_ps=round(wc, 1), W_core_offset_planned_ps=round(wc_planned, 1))
    hr = hbrow[g["part"]]
    Wg = max(r["corners"][C]["pair_U_max_ps"] for C in ("TT", "FF"))
    Wc = max(r["corners"][C]["W_core_ps"] for C in ("TT", "FF"))
    Wcp = max(r["corners"][C]["W_core_offset_planned_ps"] for C in ("TT", "FF"))
    K180 = HB["k_new"]

    def cells(kh, kc):
        return hr["bits_in"] * K180["in_"] + hr["bits_out"] * K180["out"] + (hr["bits_ft"] + hr["bits_ist"]) * kh + hr["bits_core"] * kc
    r["hold_buffers"] = dict(W180=hr["cells_new"], k_hop_mesh=k(Wg - 8), k_core_mesh=k(Wc + 15), k_core_mesh_planned=k(Wcp + 15),
                             mesh=cells(k(Wg - 8), k(Wc + 15)), mesh_offset_planned=cells(k(Wg - 8), k(Wcp + 15)),
                             W_glue_ps=Wg, W_core_ps=Wc, W_core_planned_ps=Wcp, k180=K180)
    # power (C V^2 f, 0.7 V, 1.2 GHz) + BUFx24 internal 7.7 uW/cell (QC-MESH-EST-1 basis)
    log = (T / "run.log").read_text()
    wl = float(re.search(r"Total wirelength: ([\d.]+) um", log).group(1))
    meshC = sum(s[3] for s in rec["segs"]) + 2.3 * len(rec["taps"])
    ncell = sum(1 for n in J["cells"] if not n.startswith("L_"))
    pw = dict(mesh_mW=meshC * 1e-15 * 0.49 * 1.2e9 * 1e3, tree_wire_mW=wl * 0.19e-15 * 0.49 * 1.2e9 * 1e3, cells_mW=ncell * 7.7e-3)
    pw["total_mW"] = sum(pw.values())
    r["power"] = {a: round(v, 2) for a, v in pw.items()} | dict(tree_wire_um=wl, mesh_C_pF=round(meshC / 1e3, 3), clock_cells=ncell)
    r["tracks"] = dict(M9_straps=4, M8_straps=7, strap_tracks_each=8, M9_pct=round(100 * 4 * 8 / (g["W"] / 0.08), 3),
                       M8_pct=round(100 * 7 * 8 / (g["H"] / 0.08), 3))
    drc = T / "drc.rpt"
    r["drc_violations"] = (sum(1 for ln in open(drc) if ln.startswith("violation type")) if drc.exists() else None)
    out["trials"][t] = r
# stability: same template, two trials (tap arrivals relative to each trial's mesh median)
stab = {}
for i, a in enumerate(trials):
    for b in trials[i + 1:]:
        for C in ("TT", "FF"):
            A, B = nom[(a, C)], nom[(b, C)]
            ks = sorted(set(A) & set(B))
            ma, mb = sorted(A[x] for x in ks)[len(ks) // 2], sorted(B[x] for x in ks)[len(ks) // 2]
            stab[f"{a}~{b}_{C}"] = dict(taps=len(ks), abs_move_max_ps=round(max(abs(B[x] - A[x]) for x in ks), 2),
                                        rel_move_max_ps=round(max(abs((B[x] - mb) - (A[x] - ma)) for x in ks), 2))
out["stability"] = stab
Path(outf).write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1)[:6000])
