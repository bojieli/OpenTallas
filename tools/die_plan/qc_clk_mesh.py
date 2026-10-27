#!/usr/bin/env python3
"""QC-CLK-MESH (12.8e MSCTS die clock, OWNER 10-26 17:0x): plan model of the QC die clock as industry multi-source CTS.

  (1) global H-tree on M8/M9 (shielded, NDR), equal branches BY CONSTRUCTION (geometric H: every level's branches are
      the same length; no balance-detour padding), carried down to a uniform die-wide MESH-DRIVER lattice;
  (2) one regional mesh per lattice region (M8 horizontal / M9 vertical straps on the 8.64-um island lattice, pitch
      a multiple of 8.64), driven at every driver-lattice point inside the region (driver islands, 12.2a1);
  (3) short local trees: one tap buffer on the mesh at the crossing nearest each partition centre entry
      (die_tree_plan regions.entries; the partition / core kit owns entry -> cores at 250 TT / 202.5 FF, 12.3).

Everything is computed from plan geometry (12.8 d1; nothing measured is read).  Delay per stage d = D0 + K * L_seg
(region_clock.STAGE, calibrated once on the CLOCK-128-R4 tree-only geometry SPEF, UNCHECKED).  Related-pair
pessimism uses region_clock.nc_estimate's flat-OCV convention (die_ci_margins.json) on the NON-COMMON clock:
  * same mesh (signed mesh = common point, 12.4a b exception): local tap stage + stub + core latency, plus the mesh
    sign-off skew (ngspice) as explicit uncertainty;
  * different meshes: last common H-tree node (12.4a b): everything below it is non-common.
Sub-command `deck` writes an ngspice deck (transistor-level ASAP7 BUFx24 drivers + tap buffers, plan-RC mesh straps)
of ONE region for the variation sign-off simulation (see qc_clk_mesh_mc.py).
"""
import argparse
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import region_clock as RC  # noqa: E402

STAGE, REP_UM, ISL, CORE_LAT, DERATE = RC.STAGE, RC.REP_UM, RC.ISL, RC.CORE_LAT, RC.DERATE
LAYER_RC = {"M8": (8.44765e-3, 1.03962e-1), "M9": (8.89556e-3, 9.28446e-2)}   # kohm/um, fF/um (die_clock.LAYER_RC)
NDR = {"2w": (0.5, 1.1), "4w": (0.25, 1.3), "8w": (0.125, 1.6)}               # (R factor, C factor)
NDR_FOOT_UM = {"2w": 0.08 + 2 * (0.08 + 0.04), "4w": 0.16 + 2 * (0.08 + 0.04), "8w": 0.32 + 2 * (0.08 + 0.04)}
TRACK_UM = 0.08                        # M8/M9 pitch (asap7_tech_1x_201209.lef)
BUF_CIN_FF = 2.3                       # BUFx24 A pin cap (liberty ~2.0-2.6 fF)
VDD = {"TT": 0.70, "FF": 0.77}
F_CLK_GHZ = 1.0 / 0.833
SNAP_UM = 54.0                         # max glue-island snap (tree imbalance from jogs stays < ~4 ps)


def r3(v):
    return round(float(v), 3)


def md(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def edge_delay(L, c):
    return RC.stage_delay(L, RC.n_min(L), c) if L > 1e-6 else 0.0


# ---------------------------------------------------------------- global H-tree to the driver lattice
def htree(W, H, ndx, ndy, rx, ry):
    """geometric H-tree over the die box: ndx x ndy drivers (powers of two), region roots where the remaining box
    holds (ndx/rx) x (ndy/ry) drivers.  Split rule: the dimension with more remaining leaves (x on ties), so every
    level's branches have one length.  Returns nodes [{tag,parent,depth,xy,box,kind}]."""
    assert ndx % rx == 0 and ndy % ry == 0
    per = (ndx // rx, ndy // ry)
    nodes = []

    def rec(tag, parent, depth, box, nx, ny):
        xy = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
        kind = "driver" if nx == ny == 1 else ("region_root" if (nx, ny) == per else
                                                ("root" if parent is None else "tree"))
        if (nx, ny) == per and nx == ny == 1:
            kind = "region_root_driver"
        nodes.append(dict(tag=tag, parent=parent, depth=depth, xy=xy, box=box, kind=kind, n=(nx, ny)))
        if nx == ny == 1:
            return
        if nx >= ny:
            xm = (box[0] + box[2]) / 2
            kids = [(box[0], box[1], xm, box[3]), (xm, box[1], box[2], box[3])]
            n2 = (nx // 2, ny)
        else:
            ym = (box[1] + box[3]) / 2
            kids = [(box[0], box[1], box[2], ym), (box[0], ym, box[2], box[3])]
            n2 = (nx, ny // 2)
        for i, b in enumerate(kids):
            rec(tag + str(i), tag, depth + 1, b, *n2)
    rec("h", None, 0, (0.0, 0.0, W, H), ndx, ndy)
    return nodes


def build(P, parts, cores, entries, trunk, ndx, ndy, rx, ry, pitch_um, ndr, snap=True):
    legal = RC.Legal(parts, cores)
    nodes = htree(P.W, P.H, ndx, ndy, rx, ry)
    by = {n["tag"]: n for n in nodes}
    disp = []
    # island sites: every tree node / driver snapped to the 8.64 lattice in partition glue off hard cores
    for n in sorted(nodes, key=lambda n: n["depth"]):
        # 12.2a1: a node over a hard core is an IN-CORE PUSHDOWN island at its ideal point (core netlist owns the
        # driver cells at a per-type fixed offset); a node in partition glue snaps to the nearest legal glue island
        # within SNAP_UM, else it also becomes an in-core / glue pushdown request at its ideal point.
        c = legal.in_core(n["xy"], ISL / 2)
        q, d = (None, None)
        if snap and c is None:
            q, d = legal.snap(n["xy"], rmax=SNAP_UM)
        if q is not None:
            n["site"], n["disp_um"], n["binding"] = q, d, "partition_island"
        else:
            n["site"], n["disp_um"] = n["xy"], 0.0
            n["binding"] = "in_core_pushdown" if c is not None else "glue_pushdown_request"
            if c is not None:
                n["core"] = dict(part=c[4], inst=c[5], type=c[6], off=[r3(n["xy"][0] - c[0]), r3(n["xy"][1] - c[1])])
        disp.append(n["disp_um"])
    # arrivals: trunk (die input -> root) + per edge: ideal H length (equal by construction) + island jogs
    base = {c: RC.stage_delay(trunk["len_um"], trunk["n_seg"], c) for c in ("TT", "FF")}
    for n in sorted(nodes, key=lambda n: n["depth"]):
        if n["parent"] is None:
            n["arr"] = dict(base)
            n["arr_ideal"] = dict(base)
            n["edge_um"] = 0.0
            continue
        p = by[n["parent"]]
        L_ideal = md(p["xy"], n["xy"])
        L = md(p["site"], n["site"])
        n["edge_um"] = r3(L)
        n["edge_ideal_um"] = r3(L_ideal)
        n["arr"] = {c: p["arr"][c] + edge_delay(L, c) for c in ("TT", "FF")}
        n["arr_ideal"] = {c: p["arr_ideal"][c] + edge_delay(L_ideal, c) for c in ("TT", "FF")}
    drivers = [n for n in nodes if n["kind"].endswith("driver") or n["kind"] == "driver"]
    rroots = [n for n in nodes if n["kind"].startswith("region_root")]
    # region of a driver / entry = lattice cell
    rw, rh = P.W / rx, P.H / ry

    def cell(xy):
        return (min(rx - 1, max(0, int(xy[0] // rw))), min(ry - 1, max(0, int(xy[1] // rh))))
    root_of_cell = {cell(n["xy"]): n for n in rroots}
    # mesh straps per region (island-lattice pitch), local tap per entry at the nearest strap crossing
    p_ = pitch_um
    meshes = {}
    for (i, j), rn in root_of_cell.items():
        x0, y0, x1, y1 = i * rw, j * rh, (i + 1) * rw, (j + 1) * rh
        xs = [ISL * math.ceil((x0 + p_ / 2) / ISL) + k * p_ for k in range(int((x1 - x0) // p_) + 1)]
        xs = [x for x in xs if x0 < x < x1]
        ys = [ISL * math.ceil((y0 + p_ / 2) / ISL) + k * p_ for k in range(int((y1 - y0) // p_) + 1)]
        ys = [y for y in ys if y0 < y < y1]
        meshes[(i, j)] = dict(cell=[i, j], box=[r3(x0), r3(y0), r3(x1), r3(y1)], root=rn["tag"], xs=xs, ys=ys,
                              drivers=[], taps=[])
    for d in drivers:
        meshes[cell(d["xy"])]["drivers"].append(d["tag"])
    taps = []
    for e in entries:
        c = cell(e["xy_um"])
        m = meshes[c]
        X = min(m["xs"], key=lambda x: abs(x - e["xy_um"][0]))
        Y = min(m["ys"], key=lambda y: abs(y - e["xy_um"][1]))
        stub = md((X, Y), e["xy_um"])
        t = dict(part=e["part"], entry=e["xy_um"], cell=list(c), tap=[r3(X), r3(Y)], stub_um=r3(stub))
        m["taps"].append(e["part"])
        taps.append(t)
    return dict(nodes=nodes, by=by, drivers=drivers, rroots=rroots, meshes=meshes, taps=taps, cell=cell,
                disp=disp, rw=rw, rh=rh)


# ---------------------------------------------------------------- related pairs by seam class
def local_delay(stub_um, c, ndr="2w"):
    """mesh crossing -> tap buffer (BUFx24) -> stub to the partition entry: one stage of length stub (+ via drop)."""
    return RC.stage_delay(stub_um, 1, c)


def pair_classes(B, pairs, mesh_skew_ps, continuous=False):
    """per seam pair: last common point (signed mesh if both entries tap one mesh, else last common H-tree node),
    non-common delay per side, flat-OCV pessimism (region_clock.nc_estimate convention) + mesh uncertainty."""
    by = B["by"]
    tap = {t["part"]: t for t in B["taps"]}
    root_tag = {tuple(m["cell"]): m["root"] for m in B["meshes"].values()}
    fc = {c: STAGE[c][0] / (STAGE[c][0] + STAGE[c][1] * REP_UM) for c in ("TT", "FF")}

    def pess(nc, c):
        cell = fc[c] * nc
        return cell * (DERATE["cell_late"] + DERATE["ir_late"] + DERATE["cell_early"]) + (nc - cell) * (
            DERATE["net_late"] + DERATE["net_early"])

    # arrival at each mesh = mean of its drivers' modelled arrival (the signed mesh absorbs their spread into
    # mesh_skew); mesh -> entry = local stage
    mesh_arr = {}
    for k, m in B["meshes"].items():
        ds = [by[t]["arr"] for t in m["drivers"]]
        mesh_arr[k] = {c: max(d[c] for d in ds) for c in ("TT", "FF")}
    rows = []
    for a, b, edge in pairs:
        if a not in tap or b not in tap:
            continue
        ta, tb = tap[a], tap[b]
        ca, cb = tuple(ta["cell"]), tuple(tb["cell"])
        row = dict(a=a, b=b, edge_um=edge)
        if ca == cb or continuous:
            row["common"] = "mesh:%d_%d" % ca if ca == cb else "mesh:continuous"
            row["cls"] = "same_mesh" if ca == cb else "seam_joined_mesh"
            for c in ("TT", "FF"):
                nc = max(local_delay(ta["stub_um"], c), local_delay(tb["stub_um"], c)) + CORE_LAT[c]
                row[c] = dict(noncommon_ps=r3(nc), ocv_pessimism_ps=r3(pess(nc, c)),
                              mesh_uncertainty_ps=r3(mesh_skew_ps.get(c, 0.0)),
                              total_ps=r3(pess(nc, c) + mesh_skew_ps.get(c, 0.0)))
        else:
            # LCA in the H-tree of the two region roots
            ra, rb = root_tag[ca], root_tag[cb]
            k = 0
            while k < min(len(ra), len(rb)) and ra[k] == rb[k]:
                k += 1
            lca = ra[:k]
            row["common"] = lca
            row["lca_depth"] = len(lca) - 1
            row["cls"] = "cross_mesh_d%d" % (len(lca) - 1)
            for c in ("TT", "FF"):
                ea = mesh_arr[ca][c] + local_delay(ta["stub_um"], c)
                eb = mesh_arr[cb][c] + local_delay(tb["stub_um"], c)
                nc = max(ea, eb) - by[lca]["arr"][c] + CORE_LAT[c]
                row[c] = dict(noncommon_ps=r3(nc), ocv_pessimism_ps=r3(pess(nc, c)), total_ps=r3(pess(nc, c)))
        rows.append(row)
    return rows


def summarise(rows):
    by = defaultdict(list)
    for r in rows:
        by[r["cls"]].append(r)
    out = {}
    for k, v in sorted(by.items()):
        out[k] = dict(pairs=len(v), **{c: dict(noncommon_ps_max=r3(max(x[c]["noncommon_ps"] for x in v)),
                                              pessimism_ps_max=r3(max(x[c]["ocv_pessimism_ps"] for x in v)),
                                              total_ps_max=r3(max(x[c]["total_ps"] for x in v)))
                                       for c in ("TT", "FF")})
    return out


# ---------------------------------------------------------------- budgets: tracks, power, EM
def budgets(B, P, pitch_um, ndr):
    rf, cf = NDR[ndr]
    out = {}
    tot_c = 0.0
    tree_um = sum(n.get("edge_um", 0.0) for n in B["nodes"])
    for k, m in B["meshes"].items():
        x0, y0, x1, y1 = m["box"]
        Lh = len(m["ys"]) * (x1 - x0)
        Lv = len(m["xs"]) * (y1 - y0)
        c_mesh = Lh * LAYER_RC["M8"][1] * cf + Lv * LAYER_RC["M9"][1] * cf
        c_taps = len(m["taps"]) * BUF_CIN_FF
        nd = len(m["drivers"])
        c = c_mesh + c_taps
        tot_c += c
        V = VDD["TT"]
        q = c * 1e-15 * V                       # C per edge
        i_avg_ma = q * F_CLK_GHZ * 1e9 * 1e3    # supply current (one charge per cycle)
        out["%d_%d" % tuple(m["cell"])] = dict(
            straps=dict(M8=len(m["ys"]), M9=len(m["xs"])), wire_um=r3(Lh + Lv), cap_pF=r3(c / 1e3),
            drivers=nd, cap_per_driver_fF=r3(c / max(nd, 1)), taps=len(m["taps"]),
            power_mW=r3(c * 1e-15 * V * V * F_CLK_GHZ * 1e9 * 1e3),
            i_avg_per_driver_mA=r3(i_avg_ma / max(nd, 1)),
            i_peak_per_driver_mA=r3(c * 1e-15 / max(nd, 1) * V / 25e-12 * 1e3),      # C/n * V / 25 ps edge
            track_frac=dict(M8=r3(len(m["ys"]) * NDR_FOOT_UM[ndr] / (y1 - y0)),
                            M9=r3(len(m["xs"]) * NDR_FOOT_UM[ndr] / (x1 - x0))))
    c_tree = tree_um * LAYER_RC["M9"][1] * cf + len(B["nodes"]) * 0  # repeater input caps small
    n_rep = sum(RC.n_min(n["edge_um"]) for n in B["nodes"] if n.get("edge_um", 0) > 0)
    c_tree += n_rep * BUF_CIN_FF
    V = VDD["TT"]
    vals = list(out.values())
    return dict(per_region=out,
                die=dict(mesh_cap_nF=r3(tot_c / 1e6), tree_wire_mm=r3(tree_um / 1e3), tree_repeaters=n_rep,
                         tree_cap_nF=r3(c_tree / 1e6),
                         power_W=r3((tot_c + c_tree) * 1e-15 * V * V * F_CLK_GHZ * 1e9),
                         max_track_frac=dict(M8=max(v["track_frac"]["M8"] for v in vals),
                                             M9=max(v["track_frac"]["M9"] for v in vals)),
                         max_i_avg_per_driver_mA=max(v["i_avg_per_driver_mA"] for v in vals),
                         max_i_peak_per_driver_mA=max(v["i_peak_per_driver_mA"] for v in vals),
                         basis="C V^2 f at TT 0.70 V, 1/0.833 ns; NDR %s; peak = C/n_drv * V / 25 ps" % ndr))


# ---------------------------------------------------------------- render
def draw(P, parts, cores, B, rows, out, title, box=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, ax = plt.subplots(figsize=(16, 13.5))
    for p in parts:
        ax.add_patch(Rectangle((p[0], p[1]), p[2] - p[0], p[3] - p[1], fill=False, lw=0.3, ec="#999999"))
    for c in cores:
        ax.add_patch(Rectangle((c[0], c[1]), c[2] - c[0], c[3] - c[1], fc="#e4e4e4", ec="none"))
    for m in B["meshes"].values():
        x0, y0, x1, y1 = m["box"]
        for x in m["xs"]:
            ax.plot([x, x], [y0, y1], "-", c="#7fb3ff", lw=0.25)
        for y in m["ys"]:
            ax.plot([x0, x1], [y, y], "-", c="#7fb3ff", lw=0.25)
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, lw=1.6, ec="#0030a0"))
    by = B["by"]
    maxd = max(n["depth"] for n in B["nodes"])
    for n in B["nodes"]:
        if n["parent"] is None:
            continue
        p = by[n["parent"]]["site"]
        q = n["site"]
        lw = 0.5 + 3.0 * (1 - n["depth"] / maxd)
        ax.plot([p[0], q[0], q[0]], [p[1], p[1], q[1]], "-", c="k", lw=lw)
    dx = [d["site"][0] for d in B["drivers"]]
    dy = [d["site"][1] for d in B["drivers"]]
    ax.plot(dx, dy, "s", ms=2.2, c="#c00000", label="mesh driver island (%d)" % len(dx))
    rr = B["rroots"]
    ax.plot([n["site"][0] for n in rr], [n["site"][1] for n in rr], "D", ms=5, c="#ff8c00", label="region root")
    ex = [t["entry"][0] for t in B["taps"]]
    ey = [t["entry"][1] for t in B["taps"]]
    ax.plot(ex, ey, "o", ms=3, mfc="none", c="#008000", label="partition centre entry (%d)" % len(ex))
    tap = {t["part"]: t for t in B["taps"]}
    for r in rows:
        if r["cls"] != "same_mesh":
            a, b = tap[r["a"]]["entry"], tap[r["b"]]["entry"]
            ax.plot([a[0], b[0]], [a[1], b[1]], "-", c="#e000e0", lw=0.8, alpha=0.7)
    ax.plot([], [], "-", c="#e000e0", label="cross-mesh seam pair")
    ax.set_aspect("equal")
    ax.set_xlim(box[0] if box else 0, box[2] if box else P.W)
    ax.set_ylim(box[1] if box else 0, box[3] if box else P.H)
    ax.legend(loc="upper right", fontsize=8)
    ax.set_title(title, fontsize=10)
    fig.savefig(out, dpi=100, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------- ngspice deck of one region
def write_deck(B, region, corner, out_dir, ndr, seg_um=54.0, samples=None, t_end=900.0, mode="late",
               sigma=None, tree_in=None, lib="/w/lib", half_offset_ps=0.0, attach="strap", drv_mult=1):
    """deck(s) of ONE region mesh: straps (plan RC, NDR), every driver = transistor-level BUFx24 (per-instance
    DELVTRAND n/p), each driver input = PWL ramp at its modelled H-tree arrival relative to the region root plus a
    Monte Carlo offset; every partition entry = BUFx24 tap buffer on the nearest crossing driving its stub + 20 fF.
    sigma: dict(vt_mV, wire_rel, tree_ps_per_stage)."""
    import random
    m = B["meshes"][region]
    by = B["by"]
    rf, cf = NDR[ndr]
    x0, y0, x1, y1 = m["box"]
    xs, ys = m["xs"], m["ys"]
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    root = by[m["root"]]
    drv = [by[t] for t in m["drivers"]]
    taps = [t for t in B["taps"] if tuple(t["cell"]) == region]
    # attach points on straps
    hp, vp = defaultdict(set), defaultdict(set)
    for j, y in enumerate(ys):
        hp[j] |= set(xs) | {x0 + 1e-3, x1 - 1e-3}
    for i, x in enumerate(xs):
        vp[i] |= set(ys) | {y0 + 1e-3, y1 - 1e-3}
    att = []
    for d in drv:
        X, Y = d["site"]
        j = min(range(len(ys)), key=lambda j: abs(ys[j] - Y))
        if attach == "crossing":     # driver output to the nearest strap crossing (both M8 and M9 straps)
            i = min(range(len(xs)), key=lambda i: abs(xs[i] - X))
            att.append(("H", j, xs[i], abs(ys[j] - Y) + abs(xs[i] - X)))
        else:
            att.append(("H", j, round(X, 3), abs(ys[j] - Y)))
            hp[j].add(round(X, 3))
    tat = []
    for t in taps:
        X, Y = t["tap"]
        j = ys.index(Y) if Y in ys else min(range(len(ys)), key=lambda j: abs(ys[j] - Y))
        tat.append(("H", j, round(X, 3)))
        hp[j].add(round(X, 3))
    seeds = samples or [0]
    meta = dict(attach=attach, drv_mult=drv_mult, half_offset_ps=half_offset_ps, region=list(region), corner=corner, ndr=ndr, straps=dict(M8=len(ys), M9=len(xs)), drivers=len(drv),
                taps=len(taps), box=m["box"], seg_um=seg_um, sigma=sigma, mode=mode, decks=[])
    for s in seeds:
        rnd = random.Random(1000 * s + 17)
        wr = (sigma or {}).get("wire_rel", 0.0) if s else 0.0
        vt = (sigma or {}).get("vt_mV", 0.0) if s else 0.0
        tps = (sigma or {}).get("tree_ps_per_stage", 0.0) if s else 0.0
        L = [f"* QC-CLK-MESH region {region} {corner} sample {s} (0 = nominal)",
             f".param vdd={VDD[corner]}", ".temp %s" % ({"TT": 25.0, "FF": 0.0}[corner]),
             f".include {lib}/{corner}/models.sp", f".include {lib}/{corner}/cells_var.sp", "Vdd vdd 0 {vdd}"]
        nid = {}
        nC = defaultdict(float)
        ne = [0]

        def node(k):
            if k not in nid:
                nid[k] = "n%d" % len(nid)
            return nid[k]

        def wire(a, b, length, layer):
            r, c = LAYER_RC[layer]
            r, c = r * rf * 1e3, c * cf     # ohm/um, fF/um
            n = max(1, int(math.ceil(length / seg_um)))
            prev = node(a)
            for q in range(1, n + 1):
                cur = node(b) if q == n else node((a, b, q))
                f = rnd.gauss(1.0, wr) if wr else 1.0
                L.append(f"R{ne[0]} {prev} {cur} {r * length / n * f:.4f}")
                ne[0] += 1
                nC[prev] += c * length / n / 2 * f
                nC[cur] += c * length / n / 2 * f
                prev = cur

        def canon(k):
            if k[0] == "H" and k[2] in xs:
                return ("X", xs.index(k[2]), k[1])
            if k[0] == "V" and k[2] in ys:
                return ("X", k[1], ys.index(k[2]))
            return k
        for j, pts in hp.items():
            p = sorted(pts)
            for u, w in zip(p, p[1:]):
                wire(canon(("H", j, u)), canon(("H", j, w)), w - u, "M8")
        for i, pts in vp.items():
            p = sorted(pts)
            for u, w in zip(p, p[1:]):
                wire(canon(("V", i, u)), canon(("V", i, w)), w - u, "M9")
        # drivers
        rel = []
        for k, (d, a_) in enumerate(zip(drv, att)):
            t_rel = {c: d["arr"][c] - root["arr"][c] for c in ("TT", "FF")}[corner]
            stop = None if (sigma or {}).get("full_path") else root["tag"]   # V2: every driver path independent from the die root
            nst = sum(RC.n_min(by[t]["edge_um"]) for t in chain(by, d["tag"], stop) if by[t].get("edge_um"))
            off = rnd.gauss(0.0, tps * math.sqrt(nst)) if tps else 0.0
            if half_offset_ps and d["xy"][0] > (x0 + x1) / 2:
                off += half_offset_ps          # V2 seam experiment: right half fed from a subtree delta later
            rel.append(t_rel + off)
            jog = a_[3]
            out_n = "d%d" % k
            L.append(f"R{ne[0]} {out_n} {node(canon(a_[:3]))} {(0.0512 + jog * LAYER_RC['M9'][0] * rf) * 1e3:.4f}")
            ne[0] += 1
            nC[out_n] += jog * LAYER_RC["M9"][1] * cf
            for q_ in range(drv_mult):
                dn = rnd.gauss(0.0, vt) if vt else 0.0
                dp = rnd.gauss(0.0, vt) if vt else 0.0
                L.append(f"X{out_n}_{q_} vss vdd in{k} {out_n} BUFx24v dvn={dn / 1e3:.5f} dvp={dp / 1e3:.5f}")
            d["_in"] = f"in{k}"
        t0 = min(rel)
        tsl = 40.0
        for k, r_ in enumerate(rel):
            st = 100.0 + (r_ - t0)
            L.append(f"Vin{k} in{k} 0 PWL(0 0 {st:.3f}p 0 {st + tsl / 0.8:.3f}p {{vdd}})")
        # taps
        for k, (t, a_) in enumerate(zip(taps, tat)):
            dn = rnd.gauss(0.0, vt) if vt else 0.0
            dp = rnd.gauss(0.0, vt) if vt else 0.0
            L.append(f"Xt{k} vss vdd {node(canon(a_))} to{k} BUFx24v dvn={dn / 1e3:.5f} dvp={dp / 1e3:.5f}")
            sl = t["stub_um"]
            r, c = LAYER_RC["M9"]
            L.append(f"R{ne[0]} to{k} te{k} {max(1.0, sl * r * rf * 1e3):.4f}")
            ne[0] += 1
            nC[f"to{k}"] += sl * c * cf / 2
            nC[f"te{k}"] += sl * c * cf / 2 + 20.0
        for k, v in nC.items():
            if v > 0:
                L.append(f"C{k} {k} 0 {v:.5f}f")
        L.append("Vss vss 0 0")
        for k in range(len(taps)):
            L.append(f".meas tran tm{k} TRIG v(in0) VAL={{vdd/2}} RISE=1 TARG v({node(canon(tat[k]))}) VAL={{vdd/2}} RISE=1")
            L.append(f".meas tran te{k} TRIG v(in0) VAL={{vdd/2}} RISE=1 TARG v(te{k}) VAL={{vdd/2}} RISE=1")
        # mesh uniformity: every strap crossing
        for i in range(len(xs)):
            for j in range(len(ys)):
                L.append(f".meas tran x{i}_{j} TRIG v(in0) VAL={{vdd/2}} RISE=1 TARG v({node(('X', i, j))}) VAL={{vdd/2}} RISE=1")
        L.append(".options method=gear reltol=1e-4 abstol=1e-12 vntol=1e-7")
        L.append(f".tran 0.5p {t_end}p 0 0.5p")
        L.append(".control\npre_osdi /w/osdi/bsimcmg23.osdi\nrun\nquit\n.endc")
        L.append(".end")
        dd = out_dir / f"s{s:03d}"
        dd.mkdir(exist_ok=True)
        (dd / "deck.sp").write_text("\n".join(L) + "\n")
        meta["decks"].append(dict(sample=s, dir=str(dd), in0_rel_ps=r3(rel[0] - t0), drv_rel_ps=[r3(x - t0) for x in rel],
                                  nodes=len(nid), resistors=ne[0]))
    meta["taps_parts"] = [t["part"] for t in taps]
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=1))
    return meta


def chain(by, tag, stop):
    out = []
    t = tag
    while t != stop and t is not None:
        out.append(t)
        t = by[t]["parent"]
    return out


# ---------------------------------------------------------------- main
def load(plan_path, dtp_path):
    import schema as S
    import master_plan as MP
    import master_rulings as MR
    import infra_sites as IS
    P = S.Plan(S.load(plan_path), Path(plan_path))
    dtp = json.loads(Path(dtp_path).read_text())
    psha = sha(plan_path)
    if dtp.get("plan_sha256") != psha:
        raise SystemExit(f"die_tree_plan cut from {dtp.get('plan_sha256', '')[:12]}, plan {psha[:12]}")
    parts, cores = MR.die_geometry(P, MP.core_to_type, IS.rect_pts)
    return P, dtp, parts, cores, psha


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan")
    ap.add_argument("--tree-plan", required=True, help="die_tree_plan.json (regions.entries + lattice.trunk)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--drivers", default="32x32", help="die-wide mesh-driver lattice NXxNY (powers of two)")
    ap.add_argument("--regions", default="4x4,8x8,16x16", help="comma list of region lattices to evaluate")
    ap.add_argument("--primary", default="4x4")
    ap.add_argument("--pitch", type=float, default=216.0, help="mesh strap pitch um (multiple of 8.64)")
    ap.add_argument("--ndr", default="4w", choices=sorted(NDR))
    ap.add_argument("--mesh-skew", default=None, help="json {TT:ps,FF:ps} signed mesh skew (ngspice) for same-mesh pairs")
    ap.add_argument("--deck-region", default=None, help="i,j of the primary lattice: write ngspice MC decks")
    ap.add_argument("--deck-samples", type=int, default=0)
    ap.add_argument("--deck-corner", default="TT")
    ap.add_argument("--sigma", default='{"vt_mV": 10.0, "wire_rel": 0.05, "tree_ps_per_stage": 2.0}')
    ap.add_argument("--half-offset", type=float, default=0.0, help="deck: extra ps on right-half drivers (V2 seam test)")
    ap.add_argument("--deck-name", default=None)
    ap.add_argument("--attach", default="strap", choices=["strap", "crossing"])
    ap.add_argument("--drv-mult", type=int, default=1, help="parallel BUFx24 per mesh-driver island")
    ap.add_argument("--zoom", default="3,3", help="region i,j of the primary lattice to render zoomed")
    ap.add_argument("--no-render", action="store_true")
    a = ap.parse_args(argv)
    assert abs(a.pitch / ISL - round(a.pitch / ISL)) < 1e-6, "mesh pitch must be a multiple of the 8.64 island lattice"
    P, dtp, parts, cores, psha = load(a.plan, a.tree_plan)
    entries = dtp["regions"]["entries"]
    trunk = dtp["lattice"]["trunk"]
    pairs = RC.seam_pairs(P, parts)
    ndx, ndy = (int(v) for v in a.drivers.split("x"))
    skew = json.loads(a.mesh_skew) if a.mesh_skew else {"TT": 0.0, "FF": 0.0}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rec = dict(schema="ot_qc_clk_mesh/1", die=P.name, plan=a.plan, plan_sha256=psha, tree_plan=a.tree_plan,
               tree_plan_sha256=sha(a.tree_plan), argv=sys.argv, stage_model=dict(STAGE=STAGE, cal=RC.STAGE_CAL),
               derate=DERATE, core_latency=CORE_LAT, mesh=dict(pitch_um=a.pitch, ndr=a.ndr, layers="M8 H / M9 V"),
               drivers=a.drivers, mesh_skew_ps=skew, options={},
               baseline=dict(source="QC-MP-REGION c0ee907c63 region_summary (UNCHECKED)", input_to_entry_TT=6341.0,
                             pess_TT=dict(die_root=759.3, lattice=598.7, region_root=316.4, region_node=219.2)),
               checked="UNCHECKED (plan model; NUMBER-CHECK)")
    for opt in a.regions.split(","):
        rx, ry = (int(v) for v in opt.split("x"))
        B = build(P, parts, cores, entries, trunk, ndx, ndy, rx, ry, a.pitch, a.ndr)
        rows = pair_classes(B, pairs, skew)
        rows2 = pair_classes(B, pairs, skew, continuous=True)
        drv = B["drivers"]
        arr = {c: [d["arr"][c] for d in drv] for c in ("TT", "FF")}
        arri = {c: [d["arr_ideal"][c] for d in drv] for c in ("TT", "FF")}
        ent = {c: [] for c in ("TT", "FF")}
        mesh_max = {}
        for k, m in B["meshes"].items():
            mesh_max[k] = {c: max(B["by"][t]["arr"][c] for t in m["drivers"]) for c in ("TT", "FF")}
        for t in B["taps"]:
            for c in ("TT", "FF"):
                ent[c].append(mesh_max[tuple(t["cell"])][c] + local_delay(t["stub_um"], c))
        rr = B["rroots"]
        reg_far = max(md(n["xy"], (x, y)) for n in rr for (x, y) in
                      [(n["box"][0], n["box"][1]), (n["box"][2], n["box"][3])])
        intra = defaultdict(list)
        for m in B["meshes"].values():
            ds = [B["by"][t]["arr"] for t in m["drivers"]]
            for c in ("TT", "FF"):
                intra[c].append(max(d[c] for d in ds) - min(d[c] for d in ds))
        o = dict(regions=[rx, ry], region_um=[r3(B["rw"]), r3(B["rh"])], region_far_um=r3(reg_far),
                 drivers_per_region=len(drv) // (rx * ry),
                 tree=dict(levels=max(n["depth"] for n in B["nodes"]), nodes=len(B["nodes"]),
                           root_to_driver_ideal_um=r3(sum(B["by"][t].get("edge_ideal_um", 0.0) for t in chain(B["by"], drv[0]["tag"], None))),
                           max_island_disp_um=r3(max(B["disp"])), mean_island_disp_um=r3(sum(B["disp"]) / len(B["disp"]))),
                 insertion=dict(die_input_to_driver={c: dict(min=r3(min(arr[c])), max=r3(max(arr[c]))) for c in arr},
                                ideal_equal={c: dict(min=r3(min(arri[c])), max=r3(max(arri[c]))) for c in arri},
                                die_input_to_entry={c: dict(min=r3(min(ent[c])), max=r3(max(ent[c]))) for c in ent},
                                driver_spread_in_region_ps={c: r3(max(intra[c])) for c in intra},
                                stub_um_max=r3(max(t["stub_um"] for t in B["taps"]))),
                 bindings={b: sum(1 for n in B["nodes"] if n.get("binding") == b) for b in
                           ("partition_island", "in_core_pushdown", "glue_pushdown_request")},
                 in_core_type_offsets=len({(n["core"]["type"], tuple(n["core"]["off"])) for n in B["nodes"] if n.get("core")}),
                 in_core_types=len({n["core"]["type"] for n in B["nodes"] if n.get("core")}),
                 pairs=summarise(rows), pairs_V2_continuous=summarise(rows2), budgets=budgets(B, P, a.pitch, a.ndr)["die"])
        rec["options"][opt] = o
        if opt == a.primary:
            rec["primary"] = opt
            bud = budgets(B, P, a.pitch, a.ndr)
            rec["primary_detail"] = dict(per_region=bud["per_region"],
                                         meshes={"%d_%d" % k: dict(box=m["box"], root=m["root"], straps=[len(m["xs"]), len(m["ys"])],
                                                                    drivers=len(m["drivers"]), taps=m["taps"])
                                                 for k, m in B["meshes"].items()},
                                         drivers=[dict(tag=d["tag"], ideal=[r3(v) for v in d["xy"]], site=[r3(v) for v in d["site"]],
                                                       disp_um=d["disp_um"], arr=d["arr"]) for d in drv],
                                         pairs=rows)
            if not a.no_render:
                po = rec["options"][opt]["pairs"]
                cm = sum(v["pairs"] for k, v in po.items() if k != "same_mesh")
                draw(P, parts, cores, B, rows, out / f"mesh_plan_{opt}.png",
                     f"QC MSCTS plan {opt} regions ({o['region_um'][0]:.0f}x{o['region_um'][1]:.0f} um), driver lattice "
                     f"{a.drivers}, mesh pitch {a.pitch:.0f} um {a.ndr} M8/M9; same-mesh pairs "
                     f"{po.get('same_mesh', {}).get('pairs', 0)}, cross-mesh {cm} (magenta). UNCHECKED")
                zb = B["meshes"][tuple(int(v) for v in a.zoom.split(","))]["box"]
                draw(P, parts, cores, B, rows, out / f"mesh_zoom_{opt}.png",
                     f"zoom region {a.zoom} + neighbours: mesh straps (blue), H-tree (black), drivers (red), entries "
                     f"(green), cross-mesh seams (magenta). UNCHECKED",
                     box=(zb[0] - 600, zb[1] - 600, zb[2] + 600, zb[3] + 600))
            if a.deck_region:
                i, j = (int(v) for v in a.deck_region.split(","))
                rec["deck"] = write_deck(B, (i, j), a.deck_corner, out / (a.deck_name or f"deck_{a.deck_corner}"),
                                         a.ndr, samples=list(range(a.deck_samples + 1)), sigma=json.loads(a.sigma),
                                         half_offset_ps=a.half_offset, attach=a.attach, drv_mult=a.drv_mult)
                rec["deck"].pop("decks", None)
    (out / "qc_clk_mesh.json").write_text(json.dumps(rec, indent=1, default=str))
    summ = {k: dict(region_um=v["region_um"], far=v["region_far_um"], drv_per_region=v["drivers_per_region"],
                    insertion_entry=v["insertion"]["die_input_to_entry"], disp=v["tree"]["max_island_disp_um"],
                    pairs={c: (x["pairs"], x["TT"]["total_ps_max"], x["FF"]["total_ps_max"]) for c, x in v["pairs"].items()})
            for k, v in rec["options"].items()}
    print(json.dumps(summ, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
