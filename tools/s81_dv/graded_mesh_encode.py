#!/usr/bin/env python3
"""S81 graded-mesh physical encoder (S81-CORES-R23, COORD ruling 5).

Turns the literal graded 3-rail mesh (graded_mesh_physical.materialize -> graded_metal.json) plus the placed clock
cells into ONE explicit M8/M9 shape set, keeping the real rail topology and the die PG spacing:
  * mesh rails     -- every literal segment rect unchanged (same axis, width, span; no uniform replacement); only the
                      two rail ENDS are extended by half their end via pad so every VIA89 array lies inside metal;
  * VIA89 arrays   -- the literal crossing arrays, checked inside the incident M8 AND M9 rects;
  * rail shields   -- two drawn VSS stripes per segment at the wide-metal spacing row of the rail width (ASAP7
                      SPACINGTABLE 0.5/1.0 um at PRL >= 1.8 um), NDR space otherwise;
  * driver banks   -- per bank one M8 collector over all unit Y pins (PG-aware track) + its jog to the rail
                      (M8 straight onto an M9 rail, M9 riser onto an M8 rail) and one M1->M7 pin stack + M7 riser
                      per unit;
  * local trees    -- per stub one drop from its A pin onto the rail (M9 onto an M8 rail, M8 onto an M9 rail) and a
                      pin stack; then every tree net (root / H-tree legs / reps / nodes / stubs) re-routed by the
                      SAME C128.TrackRouter + fixed_wires the base build used, now against PG + the graded rails;
  * census         -- same-layer shorts / spacing (incl. the PG wide rule) over PG + every encoded shape, via-in-
                      incident-rect, max width (M8 2.0 um), PG-gap occupancy (one rail per PG gap), literal graph
                      topology (1 component, (nx-1)(ny-1) cycles) and attachment continuity.
Geometry only: no extraction, timing or P&R claim. physical_encoder_qualified stays False unless every census row is 0.
"""
import argparse, bisect, collections, hashlib, json, math, sys
from pathlib import Path
HERE = Path(__file__).resolve().parents[1] / "die_plan"
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_clock_mesh as D, die_clock_128 as C, schema as S   # noqa: E402

M8_MAXWIDTH = 2.0
PG_PITCH, PG_W = 8.64, 0.48
NET = "ck_mesh"
STACK = ("M1", "M2", "M3", "M4", "M5", "M6", "M7")


def rail_key(seg):
    x0, y0, x1, y1 = seg["centre_um"]
    return (seg["layer"], round(y0 if seg["layer"] == "M8" else x0, 6))


def rail_gap(w, run):
    """edge gap rail -> shield: the wider-shape spacing row for the rail width at its parallel run, NDR space floor"""
    return max(D.NDR["4w"]["space"], C.wide_spacing(w, run))


def gap_axis(v, pitch=4.32, track=0.08, toff=0.04):
    """centre-most 80-nm track of the ACTUAL PG gap holding v: the die grid alternates VDD/VSS every 4.32 um (each
    net on 8.64), so a gap is (k*4.32, (k+1)*4.32), not the 8.64 gap graded_mesh_physical.axis assumed"""
    k = math.floor(v / pitch)
    mid = k * pitch + pitch / 2
    n = round((mid - toff) / track)
    cands = [round(toff + (n + d) * track, 6) for d in (-1, 0, 1)]
    return min(cands, key=lambda q: (abs(q - mid), q))


def snap_to_pg_gaps(g, pitch=4.32):
    """the same literal mesh (same rails, order, widths, segments, via arrays, attachments) with every rail axis
    moved to the centre track of its actual PG gap; returns (g2, moves)"""
    fx = {round(x, 6): gap_axis(x, pitch) for x in g["xs"]}
    fy = {round(y, 6): gap_axis(y, pitch) for y in g["ys"]}
    if len(set(fx.values())) != len(fx) or len(set(fy.values())) != len(fy):
        raise ValueError("two rails snap into one PG gap")
    X = lambda x: fx[round(x, 6)]   # noqa: E731
    Y = lambda y: fy[round(y, 6)]   # noqa: E731
    segs = []
    for s in g["segments"]:
        x0, y0, x1, y1 = s["centre_um"]
        w = s["width_um"]
        c = [X(x0), Y(y0), X(x1), Y(y1)]
        r = [c[0], c[1] - w / 2, c[2], c[1] + w / 2] if s["layer"] == "M8" else [c[0] - w / 2, c[1], c[0] + w / 2, c[3]]
        segs.append(dict(s, centre_um=c, rect_um=[round(v, 6) for v in r]))
    vias = [dict(v, x_um=X(v["x_um"]), y_um=Y(v["y_um"])) for v in g["vias"]]
    att = []
    for a in g["attachments"]:
        x, y = a["xy_um"]
        att.append(dict(a, xy_um=[X(x), y] if a["layer"] == "M9" else [x, Y(y)]))
    moves = [abs(a - b) for a, b in list(fx.items()) + list(fy.items())]
    g2 = dict(g, segments=segs, vias=vias, attachments=att, xs=sorted(fx.values()), ys=sorted(fy.values()))
    return g2, dict(max_um=round(max(moves), 4), mean_um=round(sum(moves) / len(moves), 4), rails=len(moves))


def gap_fit_findings(g, pgr):
    """segments whose width + the wide-row spacing to BOTH actual neighbouring PG stripes does not fit their gap"""
    idx = {"M8": collections.defaultdict(list), "M9": collections.defaultdict(list)}
    for net, lay, x0, y0, x1, y1 in pgr:
        if lay == "M8":
            idx[lay][round((y0 + y1) / 2, 3)].append((x0, x1, y1 - y0))
        elif lay == "M9":
            idx[lay][round((x0 + x1) / 2, 3)].append((y0, y1, x1 - x0))
    cs = {L: sorted(idx[L]) for L in idx}
    bad = []
    for s in g["segments"]:
        lay = s["layer"]
        x0, y0, x1, y1 = s["centre_um"]
        c, a0, a1 = (y0, min(x0, x1), max(x0, x1)) if lay == "M8" else (x0, min(y0, y1), max(y0, y1))
        w, L = s["width_um"], cs[lay]
        i = bisect.bisect_left(L, c)
        for p in L[max(0, i - 2):i + 2]:
            for lo, hi, pw in idx[lay][p]:
                prl = min(a1, hi) - max(a0, lo)
                if prl <= 0:
                    continue
                need = max(D.NDR["4w"]["space"], C.wide_spacing(max(w, pw), prl))
                gap = abs(c - p) - w / 2 - pw / 2
                if gap < need - 1e-6:
                    bad.append(dict(layer=lay, axis=c, span=[a0, a1], width=w, pg=p, pg_width=pw, gap=round(gap, 4), need=need))
    return bad


def rail_shapes(g, nd, shield="VSS", drawn=True):
    """(shapes, rails) of the literal segments. Rail-end segments are extended by half of their end via pad."""
    pad = {(round(v["x_um"], 6), round(v["y_um"], 6)): v["pad_um"] for v in g["vias"]}
    rails = collections.defaultdict(list)
    for s in g["segments"]:
        rails[rail_key(s)].append(s)
    shapes, ws = [], nd["width"]
    for (lay, c), segs in rails.items():
        segs.sort(key=lambda s: min(s["centre_um"][0], s["centre_um"][2]) if lay == "M8" else min(s["centre_um"][1], s["centre_um"][3]))
        for i, s in enumerate(segs):
            x0, y0, x1, y1 = s["centre_um"]
            a0, a1 = (min(x0, x1), max(x0, x1)) if lay == "M8" else (min(y0, y1), max(y0, y1))
            w = s["width_um"]
            e0 = e1 = 0.0
            if i == 0:
                p = pad.get((round(a0, 6), round(c, 6)) if lay == "M8" else (round(c, 6), round(a0, 6)), 0.0)
                e0 = p / 2
            if i == len(segs) - 1:
                p = pad.get((round(a1, 6), round(c, 6)) if lay == "M8" else (round(c, 6), round(a1, 6)), 0.0)
                e1 = p / 2
            shapes.append((lay, NET, "mesh", round(c - w / 2, 6), round(c + w / 2, 6), round(a0 - e0, 6), round(a1 + e1, 6)))
            off = w / 2 + rail_gap(w, a1 - a0) + ws / 2
            for sg in ((-1, 1) if drawn else ()):
                shapes.append((lay, shield, "rail_shield", round(c + sg * off - ws / 2, 6), round(c + sg * off + ws / 2, 6),
                               round(a0 - e0, 6), round(a1 + e1, 6)))
    return shapes, rails


def via_findings(g, shapes):
    """VIA89 pads that are not inside the union of the incident M8 and M9 rail rects"""
    idx = {"M8": collections.defaultdict(list), "M9": collections.defaultdict(list)}
    for s in shapes:
        if s[2] == "mesh":
            idx[s[0]][round((s[3] + s[4]) / 2, 6)].append(s)
    bad = []
    for v in g["vias"]:
        x, y, h = v["x_um"], v["y_um"], v["pad_um"] / 2
        for lay, c, q in (("M8", y, x), ("M9", x, y)):
            rs = idx[lay].get(round(c, 6), [])
            inc = [r for r in rs if r[5] - 1e-6 <= q <= r[6] + 1e-6]
            ok = bool(inc) and all(r[3] <= c - h + 1e-6 and c + h <= r[4] + 1e-6 for r in inc) \
                and min(r[5] for r in inc) <= q - h + 1e-6 and q + h <= max(r[6] for r in inc) + 1e-6
            if not ok:
                bad.append(dict(via=[x, y], layer=lay, pad_um=v["pad_um"], incident=[list(r) for r in inc]))
    return bad


def pg_gap_findings(rails, pgr):
    """rails sharing one PG gap, and rails whose metal is closer than the wide row to a PG stripe (across-axis)"""
    pgc = {"M8": sorted({round((r[3] + r[5]) / 2, 6) for r in pgr if r[1] == "M8"}),
           "M9": sorted({round((r[2] + r[4]) / 2, 6) for r in pgr if r[1] == "M9"})}
    gaps, close = collections.defaultdict(list), []
    for (lay, c), segs in rails.items():
        cs = pgc[lay]
        i = bisect.bisect_left(cs, c)
        lo = cs[i - 1] if i else None
        hi = cs[i] if i < len(cs) else None
        gaps[(lay, lo, hi)].append(c)
        w = max(s["width_um"] for s in segs)
        for p in (lo, hi):
            if p is not None and abs(c - p) - w / 2 - PG_W / 2 < rail_gap(w, 1e9) - 1e-6:
                close.append(dict(layer=lay, rail=c, pg=p, width=w))
    shared = [dict(layer=k[0], gap=[k[1], k[2]], rails=v) for k, v in gaps.items() if len(v) > 1]
    return shared, close


def bank_tie(router, cells, bank_units, attach, nd):
    """M8 collector over all unit Y pins + jog onto the rail; per unit M1-M7 stack and M7 riser. Returns segs, stacks."""
    pins = [C.pin_xy(cells, u, "Y", D.ROW_Y) for u in bank_units]
    xs, ys = [p[0] for p in pins], [p[1] for p in pins]
    ax, ay = attach["xy_um"]
    yc = sum(ys) / len(ys)
    segs, errs = [], []
    if attach["layer"] == "M9":           # vertical rail at x=ax: the collector runs on M8 straight onto it
        a0, a1 = min(xs + [ax]), max(xs + [ax])
        c, m, e = router.place("M8", yc, a0, a1, NET)
        if c is None:
            errs.append(dict(kind="no_collector_track", units=bank_units, ideal=yc))
            return segs, [], errs
        segs.append(("M8", a0, c, a1, c, NET, "bank", m, e))
        if abs(c - ay) > 1e-6:            # rail attachment y moves with the legal collector track
            attach["xy_um"] = [ax, c]
    else:                                  # horizontal rail at y=ay: M8 collector over the pins + M9 riser
        a0, a1 = min(xs), max(xs)
        c, m, e = router.place("M8", yc, a0 - 0.02, a1 + 0.02, NET)
        if c is None:
            errs.append(dict(kind="no_collector_track", units=bank_units, ideal=yc))
            return segs, [], errs
        segs.append(("M8", a0 - 0.02, c, a1 + 0.02, c, NET, "bank", m, e))
        xr = min(max(ax, a0), a1)
        cx, mx, ex = router.place("M9", xr, min(c, ay), max(c, ay), NET)
        if cx is None:
            errs.append(dict(kind="no_riser_track", units=bank_units, ideal=xr))
            return segs, [], errs
        segs.append(("M9", cx, min(c, ay), cx, max(c, ay), NET, "bank_riser", mx, ex))
        attach["xy_um"] = [cx, ay]
    stacks = [dict(unit=u, pin="Y", xy_um=[x, y], layers=list(STACK), riser_M7=[y, c], lands="M8") for u, (x, y) in zip(bank_units, pins)]
    return segs, stacks, errs


def stub_tie(router, cells, attach):
    u = attach["units"][0]
    px, py = C.pin_xy(cells, u, "A", D.ROW_Y)
    ax, ay = attach["xy_um"]
    if attach["layer"] == "M8":           # drop on M9 from the pin row onto the M8 rail
        c, m, e = router.place("M9", px, min(py, ay), max(py, ay), NET)
        if c is None:
            return [], None, dict(kind="no_stub_drop", unit=u, ideal=px)
        attach["xy_um"] = [c, ay]
        return [("M9", c, min(py, ay), c, max(py, ay), NET, "stub_drop", m, e)], \
            dict(unit=u, pin="A", xy_um=[px, py], layers=list(STACK) + ["M8"], lands="M9", jog_M8=[px, c]), None
    c, m, e = router.place("M8", py, min(px, ax), max(px, ax), NET)
    if c is None:
        return [], None, dict(kind="no_stub_drop", unit=u, ideal=py)
    attach["xy_um"] = [ax, c]
    return [("M8", min(px, ax), c, max(px, ax), c, NET, "stub_drop", m, e)], \
        dict(unit=u, pin="A", xy_um=[px, py], layers=list(STACK), lands="M8", riser_M7=[py, c]), None


def encode(plan, build, out, limit=400, gap_snap=False):
    import die_infra as DI
    import graded_mesh_graph as GG
    P = S.Plan(S.load(plan), str(plan))
    b, dst = Path(build), Path(out)
    dst.mkdir(parents=True, exist_ok=True)
    g = json.loads((b / "graded_metal.json").read_text())
    M = json.loads((b / "mesh.json").read_text())
    cells = json.loads((b / "place.json").read_text())
    nets = json.loads((b / "nets.json").read_text())["nets"]
    nd, sh = D.NDR[M["meta"].get("ndr", "4w")], "VSS"
    pgr = DI.pg_rects(P, C.pg_grid(P))
    snap = None
    if gap_snap:     # rails to the actual 4.32-um PG gaps; PG stripes both sides are the rail shields (12.7a pg mode)
        g, snap = snap_to_pg_gaps(g)
    rshapes, rails = rail_shapes(g, nd, sh, drawn=not gap_snap)
    gfit = gap_fit_findings(g, pgr)
    wmax = {L: max([s["width_um"] for s in g["segments"] if s["layer"] == L] or [0]) for L in ("M8", "M9")}
    vbad = via_findings(g, rshapes)
    shared, close = pg_gap_findings(rails, pgr)
    graph = GG.build(g)["summary"]
    # 1) PG, 2) literal rails + shields, 3) bank collectors / stub drops, 4) every tree net -- one router, in order
    router = C.TrackRouter(nd, sh, D.DEFAULT_TRACKS, D.TRACK_MOVE_UM)
    router.reserve(C.pg_shapes(pgr))
    router.reserve(rshapes)
    tie_segs, stacks, errs = [], [], []
    for a in g["attachments"]:
        if a["role"] == "driver":
            s_, st_, e_ = bank_tie(router, cells, a["units"], a, nd)
            tie_segs += s_; stacks += st_; errs += e_
        else:
            s_, st_, e_ = stub_tie(router, cells, a)
            tie_segs += s_
            if st_: stacks.append(st_)
            if e_: errs.append(e_)
    perr = []
    try:
        wires = C.fixed_wires(M, cells, nets, D.BUF_W, D.ROW_Y, router=router)
    except C.PlanError as ex:
        wires, perr = [], ex.args[0] if ex.args else [str(ex)]
    # full census: PG + rails/shields + ties + tree, every pair of different nets, PG wide rule included
    ties = C.clock_shapes([s[:7] + (s[7],) + (s[8],) for s in tie_segs], nd, sh)
    tree = C.clock_shapes(C.tree_segs(wires), nd, sh) if wires else []
    census = C.metal_census(C.pg_shapes(pgr) + rshapes + ties + tree, nd["space"], limit=limit)
    tree_mode = collections.Counter(m for w in wires for m in (w.get("shield_modes") or []))
    rep = dict(
        schema="opentallas.s81.graded_mesh_encode.v1",
        build=str(b), plan_sha256=hashlib.sha256(Path(plan).read_bytes()).hexdigest(),
        graded_metal_sha256=hashlib.sha256((b / "graded_metal.json").read_bytes()).hexdigest(),
        rails=dict(M8=sum(1 for k in rails if k[0] == "M8"), M9=sum(1 for k in rails if k[0] == "M9")),
        segments=len(g["segments"]), crossings=len(g["vias"]), via_cuts=sum(v["rows"] * v["cols"] for v in g["vias"]),
        rail_width_max_um=wmax, m8_maxwidth_um=M8_MAXWIDTH, m8_maxwidth_violations=sum(1 for s in g["segments"] if s["layer"] == "M8" and s["width_um"] > M8_MAXWIDTH + 1e-9),
        rail_end_extensions=sum(1 for s in rshapes if s[2] == "mesh") and None,
        via_outside_incident=len(vbad), gap_snap=snap, rail_shield_mode="pg" if gap_snap else "drawn",
        segments_not_fitting_pg_gap=len(gfit), segments_not_fitting_by_pg_width=dict(collections.Counter(str(f["pg_width"]) for f in gfit)), pg_gap_shared=len(shared), rail_pg_too_close=len(close),
        graph=graph, attachments=collections.Counter(a["role"] for a in g["attachments"]),
        bank_tie_segments=sum(1 for s in tie_segs if s[6] in ("bank", "bank_riser")),
        stub_drops=sum(1 for s in tie_segs if s[6] == "stub_drop"), pin_stacks=len(stacks), tie_errors=len(errs),
        tree_nets=len(wires), tree_segments=sum(len(w["segs"]) for w in wires), tree_mm=round(sum(w["wire_um"] for w in wires) / 1000, 3),
        tree_shield_modes=dict(tree_mode), tree_plan_errors=len(perr), router_modes=dict(router.modes),
        router_move_max_um=round(max(router.moves or [0]), 4), pg_rects=len(pgr),
        metal_shapes=census["shapes"], metal_shorts=census["shorts"], metal_spacing=census["spacing"],
        shorts_by_kind=census["shorts_by_kind"], spacing_by_kind=census["spacing_by_kind"])
    rep["rail_end_extensions"] = 2 * (rep["rails"]["M8"] + rep["rails"]["M9"])
    fails = [k for k in ("segments_not_fitting_pg_gap", "m8_maxwidth_violations", "via_outside_incident", "pg_gap_shared", "rail_pg_too_close",
                         "tie_errors", "tree_plan_errors", "metal_shorts", "metal_spacing") if rep[k]]
    if graph["components"] != 1 or graph["cycles"] != graph["expected_cycles"]:
        fails.append("graph_topology")
    rep["fails"] = fails
    rep["status"] = "ENCODED_CENSUS_PASS" if not fails else "ENCODED_CENSUS_FAIL"
    rep["physical_encoder_qualified"] = False
    rep["limits"] = ["geometry only; extraction/EM/IR/timing OPEN", "M1-M7 pin stacks + M7 risers recorded, not "
                     "censused against signal routing", "VSS shield ties to the die grid not re-derived here"]
    enc = dict(shapes=rshapes + ties + tree, vias=g["vias"], stacks=stacks, attachments=g["attachments"],
               tie_segs=[list(s) for s in tie_segs], tree_wires=wires, pg_rects=[list(r) for r in pgr])
    (dst / "encoded_metal.json").write_text(json.dumps(enc, separators=(",", ":")) + "\n")
    (dst / "ENCODE.json").write_text(json.dumps(rep, indent=1) + "\n")
    (dst / "findings.json").write_text(json.dumps(dict(census_rows=census["rows"], via=vbad[:limit], pg_gap_shared=shared[:limit],
                                                       rail_pg_close=close[:limit], gap_fit=gfit[:limit], tie_errors=errs[:limit], plan_errors=perr[:limit]), indent=0) + "\n")
    print(json.dumps(rep, indent=1))
    return rep


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True); ap.add_argument("--build", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--gap-snap", action="store_true", help="move every rail to the centre of its ACTUAL 4.32-um PG gap")
    a = ap.parse_args()
    encode(a.plan, a.build, a.out, gap_snap=a.gap_snap)
