#!/usr/bin/env python3
"""INFRA-FIRST-QC-R12: as r11_phys_sites.py but with the top tree solved + placed on ONE per-type island lattice
(qc_clk_mesh3 --islands type; COORD ruling INFRA-FIRST-QC-R11).  Also writes r15_islands.json = the per-type slot
declaration (type frame, identical on every instance) that the partition kits consume (12.2a1 pushdown).
--- r11 doc ---
INFRA-FIRST-QC-R11 (1a): physical export of the mesh3 TOP TREE (COORD ruling INFRA-FIRST-QC-R10: topology = mesh3 top
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
sys.path.insert(0, "/srv/opentallas-scratch2/claude/wt/qc-mesh-r15-1026/tools/die_plan")
import qc_clk_mesh3 as M3  # noqa: E402
import die_clock as DC  # noqa: E402

SITE_X, ROW_Y = 0.054, 0.27
LEF = {"BUFx24": ("BUFx24_ASAP7_75t_R", 1.62), "BUFx16f": ("BUFx16f_ASAP7_75t_R", 1.188)}
KINDS = ("top_node", "top_rep", "col_tap", "chan_node", "chan_rep")


def snap(v, q):
    return round(round(v / q) * q, 6)


def main(argv=None):
    ap = argparse.ArgumentParser()
    M3.add_common(ap)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    a.no_spine, a.top_w, a.top_m, a.top_reach = True, "16w", 2, 450.0   # r10 G450 configuration
    a.islands = "type"
    a.feed = "periodic"   # R13 periodic + centre channel
    a.lanes = "vss"       # R15 per-level VSS lanes (COORD ruling INFRA-FIRST-QC-R14)
    st = M3.Stage(a.stage)
    B = M3.build(a, st)
    # R15: the same d1 fine-driver cells as cmd_solve --geometry legal (export == timed geometry)
    rec = B["rec"]
    xs, ys = [M3.r3(x) for x in rec["xs"]], [M3.r3(y) for y in rec["ys"]]
    taps = [(M3.r3(t["tap"][0]), M3.r3(t["tap"][1])) for t in rec["taps"]]
    fd0 = sorted({(M3.r3(n["xy"][0]), M3.r3(n["xy"][1])) for ct in B["ctrees"] for n in ct["nodes"] if not n["kids"]})
    N0 = M3.mesh([(y, xs[0], xs[-1]) for y in ys], [(x, ys[0], ys[-1]) for x in xs], fd0, taps, M3.RC3[a.fine_w], (M3.RC3[a.stub_w], a.stub_um))
    m0 = M3.size(M3.voronoi_c(N0), a.fine_m, a.sizing)
    cells, stats = M3.legalize(B, {q: M3.decompose(float(mm)) for q, mm in zip(fd0, m0)})
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
        vert = n["lane_ax"] == "y" if n.get("lane_ax") else abs(p[0] - q[0]) < 1e-6   # R15: lane legs by their run axis
        for u, v in zip(ch, ch[1:]):
            if n.get("lane_ax"):        # R15: per net, the trunk layer of its dominant extent (a jog-only lane step = M9 drop)
                du, dv = cells[u]["site"], cells[v]["site"]
                vert = abs(du[1] - dv[1]) > abs(du[0] - dv[0])
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
        hp0 = (c.get("island") or {}).get("part")
        if lx and abs(sum(lx) / len(lx) - c["site"][0]) < 1.0:   # R15: vertical load (lane jog only) -> type-frame R0
            orient = "MY" if hp0 and P.parts[hp0].get("orient", "R0") in ("MY", "R180") else "R0"
        else:
            orient = "MY" if lx and sum(lx) / len(lx) < c["site"][0] else "R0"
        y0 = snap(c["site"][1] - ROW_Y / 2, ROW_Y)          # one base row per group; units stack upward
        if c["kind"].startswith("chan"):    # R15: channel cells sit on the YC VSS lane, units stack upward from it
            y0 = snap(c["site"][1], ROW_Y)
        # R13: units stack along the TYPE frame (+y in R0/MY hosts, -y in MX/R180 hosts) so every instance of a type
        # holds the identical type-frame cell set (12.2a1); r12 stacked +y in die frame (MX instances mirrored).
        hp = (c.get("island") or {}).get("part")
        sgn = -1 if hp and P.parts[hp].get("orient", "R0") in ("MX", "R180") else 1
        if sgn < 0:                     # MX island body (2 rows): unit 0 = type row sy = die TOP row of the body
            y0 = round(y0 + ROW_Y, 6)
        for u, m in enumerate(c["masters"]):
            lib, w = LEF[m]
            x = snap(c["site"][0] - w / 2, SITE_X)
            y = round(y0 + sgn * u * ROW_Y, 6)
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
    # R12 lattice membership: unit-0 origin of every top group == its island slot's die image (identical type grid)
    Isl = B["islands"]
    slot_at = {(s_[2], s_[4], s_[5]): (s_[6], s_[7]) for s_ in Isl.at.values()}
    off_lattice = 0
    for i in sel:
        c = cells[i]
        isd = c.get("island")
        o = site_rows.get(f"ckt_{i}_0")
        if not isd or not o:
            off_lattice += 1
            continue
        sx, sy = slot_at[(isd["part"], isd["k"], isd["j"])]
        sy_u0 = sy + (ROW_Y if P.parts[isd["part"]].get("orient", "R0") in ("MX", "R180") else 0.0)
        if abs(o["origin_um"][0] - sx) > 1e-3 or abs(o["origin_um"][1] - sy_u0) > 1e-3 or o["part"] != isd["part"]:
            off_lattice += 1
    errs_lat = off_lattice
    # overlap census on the real cells (abutting legal)
    from die_clock_mesh import placement_overlaps  # noqa: E402
    ov = placement_overlaps({k: dict(x=v["origin_um"][0], y=v["origin_um"][1], lib=v["master"]) for k, v in site_rows.items()})
    types_hosting = {t: dict(instances=len(inst_win[t]), union_sites=len(win[t]),
                             max_inst_sites=max(len(s) for s in inst_win[t].values()),
                             union_over_max=round(len(win[t]) / max(1, max(len(s) for s in inst_win[t].values())), 2))
                     for t in win}
    # R15 VSS phase: every unit row must touch a VSS stripe (R0 unit-0 origin on 8.64k, MX unit-0 top on 8.64k)
    ph = Counter()
    for v in site_rows.values():
        y = v["origin_um"][1]
        d = min(abs(y - 8.64 * round(y / 8.64)), abs(y + ROW_Y - 8.64 * round((y + ROW_Y) / 8.64)))
        ph["on_vss" if d < 1e-3 else ("unit1_of_stack" if d < 0.28 else "off_phase")] += 1
    leaves = [i for i in sel if cells[i]["kind"] == "col_tap"]
    rows = sorted({M3.r3(cells[i]["xy0"][1]) for i in leaves})
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    summ = dict(
        schema="opentallas.r15_top_sites.v1", label="UNCHECKED (plan export; no route)",
        config=dict(top_w=a.top_w, top_m=a.top_m, top_reach=a.top_reach, no_spine=True),
        groups=len(sel), groups_by_kind=dict(Counter(cells[i]["kind"] for i in sel)),
        instances=len(site_rows), instances_by_master=dict(Counter(v["master"] for v in site_rows.values())),
        mirrored=sum(v["orient"] == "MY" for v in site_rows.values()),
        nets=len(nets), nets_by_layer=dict(Counter(e["layer"] for e in nets)),
        leaf_rows=len(rows), leaf_rows_y=rows, leaves=len(leaves), vss_phase=dict(ph),
        seam_fix_moves=dict(n=len(moves), max_um=round(max(moves or [0.0]), 4)),
        off_island_lattice=errs_lat,
        gate=dict(errors=dict(errs), examples=dict(ex), overlaps=len(ov), overlap_examples=ov[:5],
                  verdict="PASS" if not errs and not ov and not errs_lat else "FAIL"),
        hosts=len({v["part"] for v in site_rows.values() if v["part"]}),
        types_hosting=len(types_hosting),
        type_window_union_worst=sorted(types_hosting.items(), key=lambda kv: -kv[1]["union_over_max"])[:8],
        r9_tool_gaps_r11=[
            "die_clock_mesh.NDR has 4w/8w only; mesh3 top tree is 16W (0.64 um) M8/M9: TrackRouter/shield/short-stack pads/"
            "via arrays need a 16w NDR (wide-metal spacing + VIA78/89 arrays) before route",
            "build_lattice() accepts only binary, midpoint, equal-cut, equal-length H-trees (plan errors node_midpoint/"
            "leg_reps/path_spread); mesh3 is DELAY-balanced (node off-midpoint, lifts arity 1, extra repeaters) -> needs an "
            "explicit-cells build path (cells+nets from this export) into C128.fixed_wires",
            "multi-unit groups (2 x BUFx24 stacked rows) need the unit A/Y tie straps encoded as fixed wires",
        ])
    I = B["islands"]
    isl = stats.get("islands") or {}
    decl = dict(schema="opentallas.r15_islands.v1", label="UNCHECKED", pitch_um=I.pitch, body_um=[I.CW, I.BH], edge_um=I.EDGE,
                core_clear_um=I.CLR, rule=isl.get("rule"),
                types={t: dict(v, gx_um=[float(q) for q in I.tgrid[t][0]], gy_um=[float(q) for q in I.tgrid[t][1]],
                             valid_kj=[[int(k), int(j)] for k, j in zip(*I.tgrid[t][2].nonzero())]) for t, v in I.types.items()},
                usage={t: {k: v[k] for k in ("hosting_instances", "used_slots_max_inst", "used_slots_union") if k in v}
                       for t, v in isl.get("per_type", {}).items() if v.get("hosting_instances")})
    (out / "r15_islands.json").write_text(json.dumps(decl) + "\n")
    summ["islands"] = {k: v for k, v in isl.items() if k != "per_type"}
    summ["islands"]["lattice_identical_per_type"] = True
    summ["islands"]["reserved_slots_per_type"] = {t: v["slots"] for t, v in I.types.items()}
    (out / "r15_top_sites.json").write_text(json.dumps(dict(summary=summ, cell_sites=site_rows,
                                                             nets=[dict(e, drv=f"g{e['drv']}", load=f"g{e['load']}") for e in nets]),
                                                        indent=0) + "\n")
    (out / "r15_top_sites_summary.json").write_text(json.dumps(summ, indent=1) + "\n")
    print(json.dumps({k: v for k, v in summ.items() if k not in ("leaf_rows_y",)}, indent=1)[:6000])
    try:
        render(B, cells, sel, site_rows, nets, out / "r15_top_sites.png", errs, ex)
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
    ax.set_title(f"R12 mesh3 top tree on per-type island lattice (16W M9 vertical blue / M8 horizontal green); errors {dict(errs)} UNCHECKED",
                 fontsize=9)
    fig.savefig(path, bbox_inches="tight")


if __name__ == "__main__":
    main()
