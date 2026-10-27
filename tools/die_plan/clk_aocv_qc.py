#!/usr/bin/env python3
"""CLK-AOCV step 4: re-compute the QC-MP-REGION seam pessimism classes (claude/qc-mp-region-1026@c0ee907c63,
gates_r1/region/region_plan.json + die_tree_plan.json) under flat and table derates, droop old vs shared.

    clk_aocv_qc.py --region-plan region_plan.json --dtp die_tree_plan.json --margins die_ci_margins.json \
                   [--aocv clk_aocv_table.json] --out qc_pessimism.json

Per seam pair (QC-MP-REGION seam_pairs/nc_estimate rows) and per side, from the plan only (nothing measured):
  branch = common node -> lattice edges (n = ceil(L/450) stages, Manhattan L) -> region legs (n_seg stages, len_um)
           -> partition centre entry -> core tree (12.3 latency 250 TT / 202.5 FF, class-B stages)
  cell_ps = sum n*d0 (die stages, class A) + core cell share; net_ps = sum k*L (+ core wire share)
  distance = bounding-box diagonal of every node / leg-polyline point of both branches
  same_region = common node inside one lattice region (region root or region node)
Variants (all UNCHECKED plan estimates):
  lane_flat          QC-MP-REGION formula (fc share on max branch, IR on all) = reproduction check
  flat_old_droop     flat derates on the exact branch split, IR +5.1 % late on the late clock branch always
  flat_shared_droop  flat derates, droop 0 when both branches share a region (owner correction 10-26)
  table_old_droop    AOCV table cells + flat nets, IR always
  table_shared_droop AOCV table + shared droop  (= the proposed b1 form)
  table_shared_g0 / table_shared_ghalf   sensitivity of the distance gradient
"""
import argparse
import copy
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clk_aocv as A  # noqa: E402

REP_UM = 450.0
CORE_LAT = {"TT": 250.0, "FF": 202.5}


def md(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def n_min(L):
    return max(1, int(math.ceil(L / REP_UM - 1e-9)))


def build(rp, dtp):
    R = rp["region_distribution"]
    st = R["stage_model"]
    lat = {n["tag"]: n for n in dtp["lattice"]["nodes"]}
    legs = {lg["tag"]: lg for lg in R["legs"]}
    ent = {lg["part"]: lg["tag"] for lg in R["legs"] if lg["to"] == "entry"}
    leaf_xy = {r["leaf"]: tuple(r["leaf_xy_um"]) for r in R["regions"]}
    tr = rp["trunk"]

    def chain(part):
        """[(tag, kind, n_stages, len_um, pts)] from the entry leg up to the die root 't' (each item = the edge INTO tag)."""
        out = []
        t = ent[part]
        while t in legs:
            lg = legs[t]
            out.append((t, "leg", lg["n_seg"], lg["len_um"], [tuple(p) for p in lg["polyline"]]))
            t = lg["parent"]
        # t = region root 'r<sfx>' at the lattice leaf 't<sfx>'
        lt = "t" + t[1:]
        out.append((t, "root", 0, 0.0, [leaf_xy[lt]]))
        while lat[lt]["parent"] is not None:
            p = lat[lt]["parent"]
            L = md(lat[p]["xy_um"], lat[lt]["xy_um"])
            out.append((lt, "lat", n_min(L), L, [tuple(lat[p]["xy_um"]), tuple(lat[lt]["xy_um"])]))
            lt = p
        out.append(("t", "die_root", 0, 0.0, [tuple(lat["t"]["xy_um"])]))
        return out

    def branch(ch, common, corner, core_b):
        d0, k = st[corner]
        cell = net = 0.0
        nA = 0
        pts = []
        for tag, kind, n, L, p in ch:
            if tag == common:
                pts += p[-1:] if kind != "leg" else []
                break
            cell += n * d0
            net += k * L
            nA += n
            pts += p
        # core tree below the entry (declared 12.3 latency), class B stages
        lat_c = CORE_LAT[corner]
        cell += lat_c * core_b[corner]["cell_share"]
        net += lat_c * (1 - core_b[corner]["cell_share"])
        nB = max(1, round(lat_c / core_b[corner]["mu_stage_ps"]))
        return dict(cell_ps=cell, net_ps=net, stages={"A": nA, "B": nB}), pts

    return chain, branch, st


def bbox_diag(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return math.hypot(max(xs) - min(xs), max(ys) - min(ys))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--region-plan", required=True)
    ap.add_argument("--dtp", required=True)
    ap.add_argument("--margins", required=True)
    ap.add_argument("--aocv", help="clock_aocv block file (default: the block inside --margins)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    rp = json.loads(Path(a.region_plan).read_text())
    dtp = json.loads(Path(a.dtp).read_text())
    m = json.loads(Path(a.margins).read_text())
    T = A.load(a.aocv or a.margins)
    Tg0 = copy.deepcopy(T)
    Tg0["systematic"]["g_per_mm"] = 0.0
    Tgh = copy.deepcopy(T)
    Tgh["systematic"]["g_per_mm"] = T["systematic"]["g_per_mm"] / 2
    core_b = {c: dict(cell_share=T["classes"]["B"][c]["cell_share"], mu_stage_ps=T["classes"]["B"][c]["mu_stage_ps"])
              for c in ("TT", "FF")}
    chain, branch, st = build(rp, dtp)
    rows = []
    for pr in rp["pair_rows"]:
        ca, cb = chain(pr["a"]), chain(pr["b"])
        sb = {t for t, *_ in cb}
        common = next(t for t, *_ in ca if t in sb)
        assert common == pr["common"] or (pr["common"] == "t" and common == "t"), (pr, common)
        same = pr["common_level"] in ("region_root", "region_node")
        row = dict(a=pr["a"], b=pr["b"], common=common, level=pr["common_level"], same_region=same)
        for corner, check in (("TT", "setup"), ("FF", "hold")):
            ba, pa = branch(ca, common, corner, core_b)
            bb, pb = branch(cb, common, corner, core_b)
            d = bbox_diag(pa + pb)
            v = {}
            v["lane_flat"] = pr[corner]["ocv_pessimism_ps"]
            for name, fn in (
                    ("flat_old_droop", lambda x, y: A.flat_pessimism(m, x, y, check, same, False)),
                    ("flat_shared_droop", lambda x, y: A.flat_pessimism(m, x, y, check, same, True)),
                    ("table_old_droop", lambda x, y: A.branch_pessimism(T, corner, x, y, d, False, check)),
                    ("table_shared_droop", lambda x, y: A.branch_pessimism(T, corner, x, y, d, same, check)),
                    ("table_shared_g0", lambda x, y: A.branch_pessimism(Tg0, corner, x, y, d, same, check)),
                    ("table_shared_ghalf", lambda x, y: A.branch_pessimism(Tgh, corner, x, y, d, same, check))):
                v[name] = round(max(fn(ba, bb), fn(bb, ba)), 1)     # worst launch/capture order of the seam
            nc = max(ba["cell_ps"] + ba["net_ps"], bb["cell_ps"] + bb["net_ps"])
            row[corner] = dict(noncommon_ps=round(nc, 1), lane_noncommon_ps=pr[corner]["noncommon_ps"],
                               dist_mm=round(d / 1000, 3), stages_a=ba["stages"], stages_b=bb["stages"],
                               cell_frac=round(ba["cell_ps"] / (ba["cell_ps"] + ba["net_ps"]), 3), **v)
        rows.append(row)
    by = defaultdict(list)
    for r in rows:
        by[r["level"]].append(r)
    keys = ("lane_flat", "flat_old_droop", "flat_shared_droop", "table_old_droop", "table_shared_droop",
            "table_shared_g0", "table_shared_ghalf")
    summ = {}
    for lvl in ("die_root", "lattice", "region_root", "region_node"):
        v = by.get(lvl, [])
        if not v:
            continue
        s = dict(pairs=len(v), same_region=v[0]["same_region"])
        for c in ("TT", "FF"):
            s[c] = dict(noncommon_ps_max=max(x[c]["noncommon_ps"] for x in v),
                        lane_noncommon_ps_max=max(x[c]["lane_noncommon_ps"] for x in v),
                        dist_mm_max=max(x[c]["dist_mm"] for x in v),
                        stages_A_max=max(max(x[c]["stages_a"]["A"], x[c]["stages_b"]["A"]) for x in v),
                        stages_A_min=min(min(x[c]["stages_a"]["A"], x[c]["stages_b"]["A"]) for x in v),
                        **{k: max(x[c][k] for x in v) for k in keys})
        summ[lvl] = s
    res = dict(schema="opentallas.clk_aocv_qc.v1", status="UNCHECKED (plan model; NUMBER-CHECK pending)",
               inputs=dict(region_plan=str(Path(a.region_plan).resolve()), dtp=str(Path(a.dtp).resolve()),
                           margins=str(Path(a.margins).resolve()), aocv=str(Path(a.aocv or a.margins).resolve()),
                           region_plan_inputs=rp.get("inputs")),
               table_g_per_mm=T["systematic"]["g_per_mm"], summary=summ, rows=rows)
    Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
    for lvl, s in summ.items():
        for c in ("TT", "FF"):
            x = s[c]
            print(f"{lvl:12s} {c} n={s['pairs']:4d} nc {x['noncommon_ps_max']:7.1f} (lane {x['lane_noncommon_ps_max']:7.1f}) "
                  f"d {x['dist_mm_max']:6.2f} mm A {x['stages_A_min']}-{x['stages_A_max']} | " +
                  " ".join(f"{k} {x[k]:6.1f}" for k in keys))
    return 0


if __name__ == "__main__":
    sys.exit(main())
