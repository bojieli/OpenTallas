#!/usr/bin/env python3
"""INFRA-FIRST-QC-R24: signal environment of the pre-routed die clock, from the die GRT guides.

The R17/R18 clock RCX extracted the clock ALONE (empty M6/M7 under the M8 trunks, empty M8 under M9), the
qc_clk_mesh3 model assumes FULL M7/M9 planes.  Neither is the real environment.  This tool measures, along every
fixed clock wire segment of a die_clock_mesh mesh.json, the die-top signal density from the combo GRT guide
(route_<C>.guide), per layer, and the plan-reserved partition share (die_trial grt adjust: partitions keep
`adjust` of M4-M7 for their own logic; die GRT sees the remaining 1-adjust):

  d_grt(L)  = die-top guide tracks in the gcell / raw tracks of the gcell on layer L (measured, GRT)
  d_part(L) = adjust(L) * u_part  inside partition outlines (plan-reserved partition routing; u_part = assumed
              utilisation of that reserve, --u-part, default 0 = lower bound, 1 = reserve full)
  d(L)      = min(1, d_grt + d_part)

Then per-um clock C from fd2d cross-sections (same eps/heights as tools/die_plan/rcx/asap7_m8m9_cal.json):
  C(d7, d6, d9) = mix of {M7 plane, M6 plane, M5 plane} below (coverage d7, then d6 of the remainder) and
  {M9 plane, open} above (coverage d9), linear in coverage (area coupling to orthogonal / parallel lines; fringe
  enhancement at low density not modelled -> slight UNDER-estimate at low d).  Reported per net as C_env / C_model,
  where C_model = full M7 + full M9 planes (qc_clk_mesh3 RC3 basis) and C_empty = clock-alone extraction basis.

usage: clk_env_density.py MESH_JSON GUIDE PLAN_JSON OUT_JSON [--adjust M4=0.75,...] [--u-part 0,0.5,1]
All numbers UNCHECKED until a NUMBER-CHECK."""
import argparse
import json
import math
import re
from collections import defaultdict

import numpy as np

PITCH = {"M4": 0.048, "M5": 0.048, "M6": 0.064, "M7": 0.064, "M8": 0.080, "M9": 0.080}
PG_COV = 0.48 / 4.32      # kit psm: M8/M9 PG 0.48 um every 4.32 um (VDD/VSS alternating at 8.64)
LAYERS = ["M4", "M5", "M6", "M7", "M8", "M9"]


def parse_guide(path, dbu, gc, nx, ny):
    """per-layer gcell track count from guide rectangles (each rect = one track in every gcell it covers)."""
    diff = {L: np.zeros((ny + 1, nx + 1), np.int32) for L in LAYERS}
    nets = rects = 0
    pat = re.compile(r"^(-?\d+) (-?\d+) (-?\d+) (-?\d+) (\S+)$")
    with open(path) as f:
        for line in f:
            if line[0] == "(" or line[0] == ")":
                continue
            m = pat.match(line.rstrip("\n"))
            if not m:
                nets += 1
                continue
            L = m.group(5)
            if L not in diff:
                continue
            x0, y0, x1, y1 = (int(m.group(i)) for i in range(1, 5))
            i0 = max(0, min(nx - 1, int(x0 / dbu / gc)))
            i1 = max(0, min(nx - 1, int((x1 / dbu - 1e-6) / gc)))
            j0 = max(0, min(ny - 1, int(y0 / dbu / gc)))
            j1 = max(0, min(ny - 1, int((y1 / dbu - 1e-6) / gc)))
            d = diff[L]
            d[j0, i0] += 1
            d[j0, i1 + 1] -= 1
            d[j1 + 1, i0] -= 1
            d[j1 + 1, i1 + 1] += 1
            rects += 1
    out = {L: np.cumsum(np.cumsum(d, 0), 1)[:ny, :nx] for L, d in diff.items()}
    return out, nets, rects


def part_mask(plan, gc, nx, ny):
    m = np.zeros((ny, nx), bool)
    T = plan["partition_types"]
    for p in plan["partitions"]:
        w, h = T[p["type"]]["outline_um"]
        if p.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
            w, h = h, w
        x0, y0 = p["origin_um"]
        m[int(y0 / gc):int(math.ceil((y0 + h) / gc)), int(x0 / gc):int(math.ceil((x0 + w) / gc))] = True
    return m


def cross_c(cal_path):
    """fd2d per-um C (fF/um) of a 16w (0.64 um) M8 clock wire with VSS shields at s, plane below at M7/M6/M5 gap,
    optional M9 plane above."""
    import fd2d
    cal = json.load(open(cal_path))
    eps = cal["eps_r"]
    l8 = cal["layers"]["8"]
    t = l8["t"]
    w, s = 0.64, 0.32
    res = {}
    l9 = cal["layers"]["9"]
    for below in ("8", "7", "6"):          # M9 16w strap (top metal: open above), plane below at M8/M7/M6 gap
        cc, fr = fd2d.pattern(w, l9["t"], s, below=l9["gap_over"][below], above=None, neighbours=True, eps_r=eps,
                              h_fine=0.008)
        res[f"m9_b{below}"] = 2 * (cc + fr)
    for below in ("7", "6", "5"):
        for top in (True, False):
            cc, fr = fd2d.pattern(w, t, s, below=l8["gap_over"][below], above=l8["gap_under"]["9"] if top else None,
                                  neighbours=True, eps_r=eps, h_fine=0.008)
            res[f"b{below}_{'t9' if top else 'open'}"] = 2 * (cc + fr)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mesh"); ap.add_argument("guide"); ap.add_argument("plan"); ap.add_argument("out")
    ap.add_argument("--dbu", type=float, default=1000.0)
    ap.add_argument("--gcell-um", type=float, default=10.8)
    ap.add_argument("--adjust", default="M4=0.75,M5=0.75,M6=0.75,M7=0.75,M8=0.4,M9=0.4")
    ap.add_argument("--u-part", default="0,0.5,1")
    ap.add_argument("--cal", default=None)
    a = ap.parse_args()
    mesh = json.load(open(a.mesh))
    plan = json.load(open(a.plan))
    W, H = plan["die"]["outline_um"]
    gc = a.gcell_um
    nx, ny = int(math.ceil(W / gc)), int(math.ceil(H / gc))
    cnt, nnets, nrects = parse_guide(a.guide, a.dbu, gc, nx, ny)
    tracks = {L: gc / PITCH[L] for L in LAYERS}
    dens = {L: cnt[L] / tracks[L] for L in LAYERS}
    pm = part_mask(plan, gc, nx, ny)
    adj = {k: float(v) for k, v in (kv.split("=") for kv in a.adjust.split(","))}
    us = [float(u) for u in a.u_part.split(",")]
    C = cross_c(a.cal) if a.cal else None

    def seg_cells(x0, y0, x1, y1):
        i0, i1 = sorted((int(x0 / gc), int(x1 / gc)))
        j0, j1 = sorted((int(y0 / gc), int(y1 / gc)))
        i0, i1 = max(0, i0), min(nx - 1, i1)
        j0, j1 = max(0, j0), min(ny - 1, j1)
        return slice(j0, j1 + 1), slice(i0, i1 + 1)

    per_net = {}
    die = defaultdict(float)
    for fw in mesh["fixed_wires"]:
        acc = defaultdict(float)
        for L, x0, y0, x1, y1 in fw["segs"]:
            if L not in ("M8", "M9"):
                continue
            ln = abs(x1 - x0) + abs(y1 - y0)
            if ln <= 0:
                continue
            sj, si = seg_cells(x0, y0, x1, y1)
            below = "M7" if L == "M8" else "M8"
            below2 = "M6" if L == "M8" else "M7"
            above = "M9" if L == "M8" else None
            inpart = float(pm[sj, si].mean())
            acc[f"{L}_um"] += ln
            acc["um"] += ln
            acc["part_um"] += ln * inpart
            acc["grt_below_um"] += ln * float(dens[below][sj, si].mean())
            acc["grt_below2_um"] += ln * float(dens[below2][sj, si].mean())
            if above:
                acc["grt_above_um"] += ln * float(dens[above][sj, si].mean())
            if L == "M8":
                acc["m8_um"] += ln
                acc["m8_part_um"] += ln * inpart
                acc["m8_g7_um"] += ln * float(dens["M7"][sj, si].mean())
                acc["m8_g6_um"] += ln * float(dens["M6"][sj, si].mean())
                acc["m8_g9_um"] += ln * float(dens["M9"][sj, si].mean())
            else:
                acc["m9_um"] += ln
                acc["m9_part_um"] += ln * inpart
                acc["m9_g8_um"] += ln * float(dens["M8"][sj, si].mean())
                acc["m9_g7_um"] += ln * float(dens["M7"][sj, si].mean())
        if acc["um"] <= 0:
            continue
        r = {k: round(v, 3) for k, v in acc.items()}
        r["frac_over_partition"] = round(acc["part_um"] / acc["um"], 4)
        r["d_grt_below"] = round(acc["grt_below_um"] / acc["um"], 5)
        r["d_grt_below2"] = round(acc["grt_below2_um"] / acc["um"], 5)
        if C:
            L8, L9 = acc["m8_um"], acc["m9_um"]
            cm8, cm9 = C["b7_t9"], C["m9_b8"]
            for u in us:
                k8 = k9 = 1.0
                if L8 > 0:
                    g7, g6, g9, fp = (acc["m8_g7_um"] / L8, acc["m8_g6_um"] / L8, acc["m8_g9_um"] / L8,
                                      acc["m8_part_um"] / L8)
                    d7 = min(1.0, g7 + fp * adj["M7"] * u)
                    d6 = min(1.0, g6 + fp * adj["M6"] * u)
                    d9 = min(1.0, g9 + PG_COV)
                    def mix(top):
                        k = "t9" if top else "open"
                        return d7 * C[f"b7_{k}"] + (1 - d7) * (d6 * C[f"b6_{k}"] + (1 - d6) * C[f"b5_{k}"])
                    k8 = (d9 * mix(True) + (1 - d9) * mix(False)) / cm8
                    r[f"m8_k_env_u{u}"] = round(k8, 4)
                if L9 > 0:
                    g8, g7, fp = acc["m9_g8_um"] / L9, acc["m9_g7_um"] / L9, acc["m9_part_um"] / L9
                    d8 = min(1.0, g8 + PG_COV)       # M8 = die PG (+ die-top signals); not a partition layer
                    d7 = min(1.0, g7 + fp * adj["M7"] * u)
                    k9 = (d8 * C["m9_b8"] + (1 - d8) * (d7 * C["m9_b7"] + (1 - d7) * C["m9_b6"])) / cm9
                    r[f"m9_k_env_u{u}"] = round(k9, 4)
                r[f"k_env_u{u}"] = round((L8 * k8 + L9 * k9) / (L8 + L9), 4) if L8 + L9 > 0 else 1.0
            r["m8_k_empty"] = round(C["b5_open"] / cm8, 4)
        per_net[fw["name"]] = r
        for k in ("um", "part_um", "grt_below_um", "grt_below2_um", "m8_um", "m8_part_um", "m8_g7_um", "m8_g6_um", "m9_um"):
            die[k] += acc[k]

    def q(vals):
        v = sorted(vals)
        return dict(n=len(v), min=round(v[0], 4), p10=round(v[len(v) // 10], 4), med=round(v[len(v) // 2], 4),
                    p90=round(v[9 * len(v) // 10], 4), max=round(v[-1], 4)) if v else {}
    summ = dict(
        guide_nets=nnets, guide_rects=nrects, gcell_um=gc, grid=[nx, ny], clock_nets=len(per_net),
        die_mean_grt_density={L: round(float(dens[L].mean()), 5) for L in LAYERS},
        clock_um=round(die["um"], 1), clock_m8_um=round(die["m8_um"], 1), clock_m9_um=round(die["m9_um"], 1),
        clock_frac_over_partition=round(die["part_um"] / die["um"], 4),
        clock_lenweighted_grt_below=round(die["grt_below_um"] / die["um"], 5),
        clock_lenweighted_grt_below2=round(die["grt_below2_um"] / die["um"], 5),
        m8_lenweighted_grt_M7=round(die["m8_g7_um"] / max(1, die["m8_um"]), 5),
        m8_lenweighted_grt_M6=round(die["m8_g6_um"] / max(1, die["m8_um"]), 5),
        per_net_d_grt_below=q([r["d_grt_below"] for r in per_net.values()]),
        per_net_frac_over_partition=q([r["frac_over_partition"] for r in per_net.values()]),
        cross_c_fF_um=C, adjust=adj, u_part=us,
        label="UNCHECKED",
    )
    if C:
        for u in us:
            summ[f"per_net_k_env_u{u}"] = q([r[f"k_env_u{u}"] for r in per_net.values() if f"k_env_u{u}" in r])
            summ[f"per_net_m8_k_env_u{u}"] = q([r[f"m8_k_env_u{u}"] for r in per_net.values() if f"m8_k_env_u{u}" in r])
    json.dump(dict(summary=summ, nets=per_net), open(a.out, "w"), indent=0)
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
