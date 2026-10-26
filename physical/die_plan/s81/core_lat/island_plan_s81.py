#!/usr/bin/env python3
"""S81 per-core-type clock entry + in-core island plan (S81-CORE-LAT-R2, 2026-10-26; METHODOLOGY 12.2a1 / 12.3 / 12.8 / 12.9d).

    python3 island_plan_s81.py [--plan-rev REV] [--out island_plan_s81_1026.json]

Inputs (repo-relative, read at --plan-rev with git show): physical/die_plan/s81/die_plan.json (hard-core instances:
type-frame origin/orient + partition origin/orient), physical/die_plan/s81/core_lat/census_main.json (lib insertion).

Per hard-core type it emits:
  entry   the CLOCK ENTRY island (12.8a): 8.64 x 8.64 lattice-aligned rect around the core centre (snapped to the
          4.32 PG lattice), M9->M5 via stack, the core clk pin = M5 interior pin at the island centre.
  islands IN-CORE ISLANDS (12.8b, built by PUSHDOWN 12.2a1): the H-tree leaf grid of master_plan.restructure_islands
          (smallest power-of-two nx x ny with leaf centre->corner <= 200 um), one 8.64 island per leaf centre, plus the
          internal H-tree branch nodes between the entry and the leaves. Each island = fixed, dont_touch clock driver
          (+ reset relay at the entry island) instantiated in the CORE netlist at these core-local coordinates,
          identical for every instance of the type, connected only through dedicated feed-through ports
          (isl_clk_i/o, isl_rst_i/o; no core logic on them; LEC/bind = die-owned feed-through).
  mode    CENTRE_HTREE   the die clock enters only at the entry island; the core's internal H-tree (nodes on the
                         in-core islands) fans out to the leaf islands (predicted insertion inside the window or
                         below it -> fixed trunk chain);
          DIE_TREE_IN    centre->corner too long for 250 +- 20 with one entry (predicted > 270 TT): the die tree
                         descends into the core -- every leaf island is a die tree node (pushdown die driver, port
                         isl_clk_i<k>), the core latency is measured from each leaf island (leaf reach), and the die
                         tree lattice must coincide with the per-type leaf-island lattice (12.2a1).
  model   12.9d analytic core insertion model, the SAME constants as master_plan.py (claude/master-plan-1026@02c545dd4b,
          calibrated once on QC-SU-LAT trial B): TT = RCX 0.943 x K 0.8963 ps/um x L_max (entry -> farthest corner,
          Manhattan), FF = 0.80 x TT. Plan-computed, BEFORE any build (12.8d1); a measured miss goes back to the model.
  chain   12.8c fixed trunk chain at the entry (same cells every instance) when predicted TT < 230:
          n x BUFx4_ASAP7_75t_R stage, 23.85 TT / 17.65 FF ps per stage (2-stage analytic 47.7/35.3, KV-CORELAT-R3
          pv_join), n = round((250 - pred_tt) / 23.85).
  lattice every die-frame instance entry/leaf centre is checked on the 4.32 lattice (orient-invariance); a FAIL
          lists the outline snap (next multiple of 4.32: a mirrored 4.32 point stays on it) as a plan delta.
"""
import argparse
import json
import math
import subprocess
from collections import defaultdict

LAT = 4.32
TARGET_TT, TARGET_FF, TOL = 250.0, 202.5, 20.0
# --- same constants as tools/die_plan/master_plan.py @ claude/master-plan-1026 02c545dd4b (one model, 12.9d)
CAL_POINTS = [("qfd_dv_s8x_vmr", 406.08, 341.8, 271.8), ("qfd_dv_s8x_prog", 436.32, 419.4, 337.1),
              ("qfd_dv_s8x_btab", 436.32, 384.9, 308.1)]
K_PS_PER_UM = sum(t for _, _, t, _ in CAL_POINTS) / sum(L for _, L, _, _ in CAL_POINTS)
FF_RATIO = sum(f / t for _, _, t, f in CAL_POINTS) / len(CAL_POINTS)
RCX_FACTOR = 386.5 / 409.9
STAGE_TT, STAGE_FF, STAGE_CELL = 23.85, 17.65, "BUFx4_ASAP7_75t_R"
REACH = 200.0
SMALL_UM = 100.0


def r3(v):
    return round(float(v), 3)


def snap(v, q=LAT):
    return round(round(v / q) * q, 4)


def entry_island(xy, side=8.64):
    x0 = math.floor(xy[0] / LAT) * LAT
    y0 = math.floor(xy[1] / LAT) * LAT
    if xy[0] - x0 < 1e-6:
        x0 -= LAT
    if xy[1] - y0 < 1e-6:
        y0 -= LAT
    return [r3(x0), r3(y0), r3(x0 + side), r3(y0 + side)]


def restructure_grid(w, h, reach=REACH):
    nx = ny = 1
    while w / nx / 2 + h / ny / 2 > reach:
        if w / nx >= h / ny:
            nx *= 2
        else:
            ny *= 2
    return nx, ny


def core_insertion(far_um):
    tt = RCX_FACTOR * K_PS_PER_UM * far_um
    return round(tt, 1), round(tt * FF_RATIO, 1)


def xf(pt, outline, orient):
    w, h = outline
    x, y = pt
    return {"R0": (x, y), "MX": (x, h - y), "MY": (w - x, y), "R180": (w - x, h - y)}[orient]


def on_lat(v, q=LAT, tol=1e-3):
    return abs(v / q - round(v / q)) * q < tol


def htree(w, h, nx, ny, centre):
    """H-tree nodes from the entry to the leaf centres: alternate splits along the longer remaining axis
    (the same order restructure_grid doubled in); every node snapped to 4.32."""
    nodes, edges = [], []
    seq = []
    cx, cy = 1, 1
    while cx < nx or cy < ny:
        if cx < nx and (w / cx >= h / cy or cy >= ny):
            seq.append("x"); cx *= 2
        else:
            seq.append("y"); cy *= 2
    level = [(0.0, 0.0, w, h, centre)]
    nodes.append(dict(level=0, xy=list(centre), role="entry"))
    for li, ax in enumerate(seq, 1):
        nxt = []
        for (x0, y0, x1, y1, p) in level:
            if ax == "x":
                xm = (x0 + x1) / 2
                kids = [(x0, y0, xm, y1), (xm, y0, x1, y1)]
            else:
                ym = (y0 + y1) / 2
                kids = [(x0, y0, x1, ym), (x0, ym, x1, y1)]
            for k in kids:
                c = (snap((k[0] + k[2]) / 2), snap((k[1] + k[3]) / 2))
                role = "leaf" if li == len(seq) else "branch"
                nodes.append(dict(level=li, xy=[r3(c[0]), r3(c[1])], role=role))
                edges.append(dict(level=li, frm=[r3(p[0]), r3(p[1])], to=[r3(c[0]), r3(c[1])],
                                  len_um=r3(abs(c[0] - p[0]) + abs(c[1] - p[1]))))
                nxt.append((*k, c))
        level = nxt
    return nodes, edges, seq


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan-rev", default="origin/main")
    ap.add_argument("--census", default="physical/die_plan/s81/core_lat/census_main.json")
    ap.add_argument("--out", default="physical/die_plan/s81/core_lat/island_plan_s81_1026.json")
    a = ap.parse_args()
    plan_txt = subprocess.check_output(["git", "show", f"{a.plan_rev}:physical/die_plan/s81/die_plan.json"])
    rev = subprocess.check_output(["git", "rev-parse", "--short=10", a.plan_rev]).decode().strip()
    P = json.loads(plan_txt)
    cen = {c["module"]: c for c in json.load(open(a.census))["cores"]}
    T = P["partition_types"]
    parts = defaultdict(list)
    for p in P["partitions"]:
        parts[p["type"]].append(p)
    inst = defaultdict(list)          # module -> [(part origin, part orient, type outline, core origin, core orient)]
    for tn, t in T.items():
        for hc in t.get("hard_cores", []):
            for p in parts.get(tn, []):
                inst[hc["module"]].append((p["origin_um"], p.get("orient", "R0"), t["outline_um"], hc))
    rows = []
    for mod, lst in sorted(inst.items(), key=lambda kv: -len(kv[1])):
        c = cen.get(mod, {})
        if c.get("memory_macro"):
            continue
        hc0 = lst[0][3]
        w, h = hc0["outline_um"]
        centre = (snap(w / 2), snap(h / 2))
        L_c = r3(max(abs(centre[0]) , abs(w - centre[0])) + max(abs(centre[1]), abs(h - centre[1])))
        pred_tt, pred_ff = core_insertion(L_c)
        row = dict(module=mod, replicas=len(lst), outline_um=[w, h], entry=dict(
            xy_um=[r3(centre[0]), r3(centre[1])], island_rect_um=entry_island(centre), pin="clk M5 interior at xy",
            stack="M9->M5", pushdown_ports=["isl_clk_i", "isl_clk_o", "isl_rst_i", "isl_rst_o"],
            cells=["die clock driver (plan-sized, fixed/dont_touch)", "die reset relay register + repeater"]),
            centre_to_corner_um=L_c, lib_insertion_tt=c.get("lib_insertion_tt"), lib_insertion_ff=c.get("lib_insertion_ff"))
        nodes, edges = [], []
        if L_c > REACH:
            nx, ny = restructure_grid(w, h)
            nodes, edges, seq = htree(w, h, nx, ny, centre)
            leaf_reach = r3(w / nx / 2 + h / ny / 2)
            row.update(grid=[nx, ny], split_order=seq, leaf_reach_um=leaf_reach)
            if pred_tt > TARGET_TT + TOL:
                mode = "DIE_TREE_IN"
                lt, lf = core_insertion(leaf_reach)
                row["pred_core_tt_ff"] = [lt, lf]
                row["pred_note"] = (f"centre entry predicts {pred_tt}/{pred_ff} > {TARGET_TT + TOL}: die tree descends to "
                                    f"the {nx * ny} leaf islands; core latency from each leaf island")
                base_tt, base_ff = lt, lf
            else:
                mode = "CENTRE_HTREE"
                base_tt, base_ff = pred_tt, pred_ff
                row["pred_core_tt_ff"] = [pred_tt, pred_ff]
        else:
            mode = "CENTRE_TREE"
            base_tt, base_ff = pred_tt, pred_ff
            row["pred_core_tt_ff"] = [pred_tt, pred_ff]
        lt_m, lf_m = c.get("lib_insertion_tt"), c.get("lib_insertion_ff")
        row["basis"] = "model"
        if mode == "CENTRE_TREE" and L_c <= SMALL_UM and lt_m and lf_m and lt_m["min"] <= lt_m["max"]:
            # small kept core: the as-built (signed view) insertion is the basis; a centre pin moves it < model error
            base_tt = r3((lt_m["min"] + lt_m["max"]) / 2)
            base_ff = r3((lf_m["min"] + lf_m["max"]) / 2)
            row["basis"] = "measured lib mean (signed view, face pin)"
        row["chain_basis_tt_ff"] = [base_tt, base_ff]
        n = 0
        if base_tt < TARGET_TT - TOL:
            # smallest |TT err| + |FF err| over stage counts, preferring counts with both corners inside the window
            def cost(k):
                et, ef = base_tt + k * STAGE_TT - TARGET_TT, base_ff + k * STAGE_FF - TARGET_FF
                return (not (abs(et) <= TOL and abs(ef) <= TOL), abs(et) + abs(ef))
            n = min(range(0, 16), key=cost)
        row["trunk_chain"] = dict(stages=n, cell=STAGE_CELL, at="entry island" if mode != "DIE_TREE_IN" else "each leaf island",
                                  tt_ps=r3(n * STAGE_TT), ff_ps=r3(n * STAGE_FF))
        tot_tt, tot_ff = r3(base_tt + n * STAGE_TT), r3(base_ff + n * STAGE_FF)
        row["pred_total_tt_ff"] = [tot_tt, tot_ff]
        row["pred_in_window"] = dict(TT=abs(tot_tt - TARGET_TT) <= TOL, FF=abs(tot_ff - TARGET_FF) <= TOL)
        row["mode"] = mode
        row["htree_nodes"] = nodes
        row["htree_edges"] = edges
        row["islands"] = [dict(role=nd["role"], level=nd["level"], centre_um=nd["xy"], rect_um=entry_island(nd["xy"]),
                               die_tree_node=(mode == "DIE_TREE_IN" and nd["role"] == "leaf"))
                          for nd in nodes if nd["role"] != "entry"]
        # die-frame lattice invariance of every instance's entry + islands
        bad = 0
        why = defaultdict(int)
        pts = [tuple(row["entry"]["xy_um"])] + [tuple(i["centre_um"]) for i in row["islands"]]
        for (po, por, tout, hc) in lst:
            for pt in pts:
                q = xf(pt, hc["outline_um"], hc.get("orient", "R0"))
                q = (hc["origin_um"][0] + q[0], hc["origin_um"][1] + q[1])
                q = xf(q, tout, por)
                q = (po[0] + q[0], po[1] + q[1])
                if not (on_lat(q[0]) and on_lat(q[1])):
                    bad += 1
                    why[f"core {hc.get('orient', 'R0')} part {por} core-origin-on-lat "
                        f"{on_lat(hc['origin_um'][0]) and on_lat(hc['origin_um'][1])}"] += 1
                    break
        row["lattice"] = dict(instances=len(lst), off_lattice=bad, verdict="PASS" if bad == 0 else "FAIL", why=dict(why),
                              outline_over_8p64=[r3(w / 8.64), r3(h / 8.64)])
        if bad:
            sw = r3(math.ceil(w / LAT - 1e-6) * LAT)
            sh = r3(math.ceil(h / LAT - 1e-6) * LAT)
            row["lattice"]["outline_snap_delta"] = dict(to_um=[sw, sh], note="outline -> next multiple of 4.32 (mirror w-x of a 4.32 "
                                                        "point stays on the lattice; instance origins already on it)")
        rows.append(row)
    summ = defaultdict(int)
    for r in rows:
        summ[r["mode"]] += 1
    out = dict(schema="opentallas.s81.core_island_plan.v1", plan="physical/die_plan/s81/die_plan.json", plan_rev=rev,
               census=a.census, rules=["12.2a1 pushdown islands", "12.3 common latency 250/202.5 +-20", "12.8a-d", "12.9d model"],
               model=dict(K_ps_per_um=round(K_PS_PER_UM, 4), rcx=round(RCX_FACTOR, 4), ff_ratio=round(FF_RATIO, 4),
                          source="tools/die_plan/master_plan.py @ claude/master-plan-1026 02c545dd4b",
                          stage=dict(cell=STAGE_CELL, tt=STAGE_TT, ff=STAGE_FF, source="KV-CORELAT-R3 pv_join analytic")),
               target=dict(tt=TARGET_TT, ff=TARGET_FF, tol=TOL), reach_um=REACH, summary=dict(summ), types=rows)
    json.dump(out, open(a.out, "w"), indent=1)
    for r in rows:
        print(f"{r['module']:30s} x{r['replicas']:5d} L{r['centre_to_corner_um']:6.1f} {r['mode']:12s} "
              f"grid{r.get('grid', [1, 1])} pred{r['pred_core_tt_ff']} chain{r['trunk_chain']['stages']} "
              f"tot{r['pred_total_tt_ff']} win{int(r['pred_in_window']['TT'])}{int(r['pred_in_window']['FF'])} "
              f"lat {r['lattice']['verdict']} {r['lattice']['off_lattice']}/{r['lattice']['instances']}")


if __name__ == "__main__":
    main()
