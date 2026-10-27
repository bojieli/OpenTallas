#!/usr/bin/env python3
"""INFRA-FIRST-QC-R11 (1a): physical export of the mesh3 TOP TREE (COORD ruling INFRA-FIRST-QC-R10: topology = mesh3 top
tree, leaves = column-tap cells on the 19 mesh tap rows) onto R9's physical cell-site rules (die_clock_mesh
apply_lattice_cell_sites, c540e671da): every real cell (units expanded) gets a lower-left ASAP7 row/site origin, exactly
one partition host holding the full body (no seam crossing), clear of every hard keep-out, no footprint overlap, and an
orientation from its load direction (R9 MY rule).  Per partition TYPE the pushdown island windows are the union over its
instances (R9 abstract-window rule) -> reported, because 12.2a1 wants identical per-type islands.
Output: r11_top_sites.json (cell_sites in R9 lattice.cell_sites form + nets + per-edge layer/width) + gate summary.
Usage (pkg dir layout of results/qc_clk_mesh3/scripts/run_solve_r10.sh):
  r11_phys_sites.py --r2 inputs/r2_plan_w.json --stage inputs/stage_table.json --out out/r11_sites
"""
import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "die_plan"))
sys.path.insert(0, "/w/die_plan")
import qc_clk_mesh3 as M3  # noqa: E402
import die_clock as DC  # noqa: E402

SITE_X, ROW_Y = 0.054, 0.27
LEF = {"BUFx24": ("BUFx24_ASAP7_75t_R", 1.62), "BUFx16f": ("BUFx16f_ASAP7_75t_R", 1.188)}
KINDS = ("top_node", "top_rep", "col_tap")


def snap(v, q):
    return round(round(v / q) * q, 6)


def main(argv=None):
    ap = argparse.ArgumentParser()
    M3.add_common(ap)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    a.no_spine, a.top_w, a.top_m, a.top_reach = True, "16w", 2, 450.0   # r10 G450 configuration
    st = M3.Stage(a.stage)
    B = M3.build(a, st)
    cells, stats = M3.legalize(B)
    B["cells"] = cells
    P = B["P"]
    parts = {n: P.rect(n) for n in P.parts}
    K = DC.KeepIndex(DC.keepouts(P), die=(float(P.W), float(P.H)))
    so = B["site_of"]
    idx = {id(c): i for i, c in enumerate(cells)}
    sel = [i for i, c in enumerate(cells) if c["kind"] in KINDS]
    # tree nets over the TOP tree only: parent group -> its repeaters -> child group (the col_tap leaf is the load end)
    nets = []
    tby = {n["tag"]: n for n in B["top_nodes"]}
    for n in B["top_nodes"]:
        if not n.get("parent"):
            continue
        ch = ([so[("t", n["parent"])]] + [so[("top_rep", n["tag"], k)] for k in range(1, n["nseg"])] + [so[("t", n["tag"])]])
        p, q = tby[n["parent"]]["xy"], n["xy"]
        vert = abs(p[0] - q[0]) < 1e-6
        for u, v in zip(ch, ch[1:]):
            nets.append(dict(drv=u, load=v, layer="M9" if vert else "M8", ndr="16w", edge=n["tag"]))
    drv_loads = defaultdict(list)
    for e in nets:
        drv_loads[e["drv"]].append(e["load"])
    site_rows, errs = {}, Counter()
    moves = []
    ex = defaultdict(list)
    win = defaultdict(set)              # type -> set of type-frame windows (rounded) over instances
    inst_win = defaultdict(lambda: defaultdict(set))
    for i in sel:
        c = cells[i]
        loads = drv_loads.get(i, [])
        lx = [cells[j]["site"][0] for j in loads]
        orient = "MY" if lx and sum(lx) / len(lx) < c["site"][0] else "R0"
        y0 = snap(c["site"][1] - ROW_Y / 2, ROW_Y)          # one base row per group; units stack upward
        for u, m in enumerate(c["masters"]):
            lib, w = LEF[m]
            x = snap(c["site"][0] - w / 2, SITE_X)
            y = round(y0 + u * ROW_Y, 6)
            name = f"ckt_{i}_{u}"
            host = None
            for pn, r in parts.items():
                if r[0] <= x + w / 2 <= r[2] and r[1] <= y + ROW_Y / 2 <= r[3]:
                    host = pn
                    break
            why = []
            if host is None:
                why.append("no_host")
            else:
                r = parts[host]
                if not (r[0] <= x and x + w <= r[2]):
                    why.append("seam_body_x")
                if not (r[1] <= y and y + ROW_Y <= r[3]):
                    why.append("seam_body_y")
                if why:     # R9 rule: the nearest move putting the full body in ONE partition (plan fix, reported)
                    dx = max(0.0, r[0] - x) - max(0.0, x + w - r[2])
                    dy = max(0.0, r[1] - y) - max(0.0, y + ROW_Y - r[3])
                    moves.append(abs(dx) + abs(dy))
            if any(K.hit(px, py, m=0.0) for px in (x, x + w) for py in (y, y + ROW_Y)):
                why.append("hard_keepout")
            for k in why:
                errs[k] += 1
                if len(ex[k]) < 5:
                    ex[k].append(dict(cell=name, kind=c["kind"], origin_um=[x, y], host=host))
            site_rows[name] = dict(origin_um=[x, y], part=host, master=lib, w=w, orient=orient, group=i, kind=c["kind"])
            if host is not None:
                t = P.parts[host]["type"]
                r = parts[host]
                # type frame: offset from the instance origin (orientation-agnostic proxy; R9 used to_die inverse)
                key = (round(x - r[0], 3), round(y - r[1], 3))
                win[t].add(key)
                inst_win[t][host].add(key)
    # overlap census on the real cells (abutting legal)
    from die_clock_mesh import placement_overlaps  # noqa: E402
    ov = placement_overlaps({k: dict(x=v["origin_um"][0], y=v["origin_um"][1], lib=v["master"]) for k, v in site_rows.items()})
    types_hosting = {t: dict(instances=len(inst_win[t]), union_sites=len(win[t]),
                             max_inst_sites=max(len(s) for s in inst_win[t].values()),
                             union_over_max=round(len(win[t]) / max(1, max(len(s) for s in inst_win[t].values())), 2))
                     for t in win}
    leaves = [i for i in sel if cells[i]["kind"] == "col_tap"]
    rows = sorted({M3.r3(cells[i]["xy0"][1]) for i in leaves})
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    summ = dict(
        schema="opentallas.r11_top_sites.v1", label="UNCHECKED (plan export; no route)",
        config=dict(top_w=a.top_w, top_m=a.top_m, top_reach=a.top_reach, no_spine=True),
        groups=len(sel), groups_by_kind=dict(Counter(cells[i]["kind"] for i in sel)),
        instances=len(site_rows), instances_by_master=dict(Counter(v["master"] for v in site_rows.values())),
        mirrored=sum(v["orient"] == "MY" for v in site_rows.values()),
        nets=len(nets), nets_by_layer=dict(Counter(e["layer"] for e in nets)),
        leaf_rows=len(rows), leaf_rows_y=rows, leaves=len(leaves),
        seam_fix_moves=dict(n=len(moves), max_um=round(max(moves or [0.0]), 4)),
        gate=dict(errors=dict(errs), examples=dict(ex), overlaps=len(ov), overlap_examples=ov[:5],
                  verdict="PASS" if not errs and not ov else "FAIL"),
        hosts=len({v["part"] for v in site_rows.values() if v["part"]}),
        types_hosting=len(types_hosting),
        type_window_union_worst=sorted(types_hosting.items(), key=lambda kv: -kv[1]["union_over_max"])[:8],
        r9_tool_gaps=[
            "die_clock_mesh.NDR has 4w/8w only; mesh3 top tree is 16W (0.64 um) M8/M9: TrackRouter/shield/short-stack pads/"
            "via arrays need a 16w NDR (wide-metal spacing + VIA78/89 arrays) before route",
            "build_lattice() accepts only binary, midpoint, equal-cut, equal-length H-trees (plan errors node_midpoint/"
            "leg_reps/path_spread); mesh3 is DELAY-balanced (node off-midpoint, lifts arity 1, extra repeaters) -> needs an "
            "explicit-cells build path (cells+nets from this export) into C128.fixed_wires",
            "multi-unit groups (2 x BUFx24 stacked rows) need the unit A/Y tie straps encoded as fixed wires",
        ])
    (out / "r11_top_sites.json").write_text(json.dumps(dict(summary=summ, cell_sites=site_rows,
                                                             nets=[dict(e, drv=f"g{e['drv']}", load=f"g{e['load']}") for e in nets]),
                                                        indent=0) + "\n")
    (out / "r11_top_sites_summary.json").write_text(json.dumps(summ, indent=1) + "\n")
    print(json.dumps({k: v for k, v in summ.items() if k not in ("leaf_rows_y",)}, indent=1)[:6000])
    try:
        render(B, cells, sel, site_rows, nets, out / "r11_top_sites.png", errs, ex)
    except Exception as e:          # noqa: BLE001
        print("render failed", e)


def render(B, cells, sel, site_rows, nets, path, errs, ex):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, ax = plt.subplots(figsize=(16, 13.5), dpi=110)
    P = B["P"]
    for n in P.parts:
        r = P.rect(n)
        ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fill=False, lw=0.2, ec="#999"))
    for c in B["cores"]:
        ax.add_patch(Rectangle((c[0], c[1]), c[2] - c[0], c[3] - c[1], fc="#f2d7d5", ec="none"))
    for e in nets:
        p, q = cells[e["drv"]]["site"], cells[e["load"]]["site"]
        ax.plot([p[0], q[0]], [p[1], q[1]], lw=0.6 if e["layer"] == "M9" else 0.4,
                c="#1f4e9c" if e["layer"] == "M9" else "#2e8b57")
    col = {"top_node": "#d62728", "top_rep": "#555", "col_tap": "#ff7f0e"}
    for k in col:
        xs = [cells[i]["site"][0] for i in sel if cells[i]["kind"] == k]
        ys = [cells[i]["site"][1] for i in sel if cells[i]["kind"] == k]
        ax.scatter(xs, ys, s=3 if k == "top_rep" else 6, c=col[k], label=f"{k} ({len(xs)})", zorder=3)
    for k, v in ex.items():
        for r in v:
            ax.scatter([r["origin_um"][0]], [r["origin_um"][1]], s=60, facecolors="none", edgecolors="m", zorder=4)
    ax.set_xlim(0, float(P.W))
    ax.set_ylim(0, float(P.H))
    ax.set_aspect("equal")
    ax.legend(loc="upper right", fontsize=8)
    ax.set_title(f"R11 mesh3 top tree physical sites (16W M9 vertical blue / M8 horizontal green); errors {dict(errs)} UNCHECKED",
                 fontsize=9)
    fig.savefig(path, bbox_inches="tight")


if __name__ == "__main__":
    main()
