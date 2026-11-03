#!/usr/bin/env python3
"""QC die y-shrink plan event (DIE-QC-66/PLAN, 2026-11-03; XCHECK-1/COORD reticle rule: die y <= 25690 um).

    python3 physical/die_plan/qwen_compute/delta_shrink_y_1103.py PLAN [--out OUT] [--report REPORT.json] \
        [--sidecar results/qc_die63_red_1102/bind/sidecar.json]

plan_qc52 outline 31216.32 x 26265.6 -> 31216.32 x 25643.52 (-622.08 = 8 CB rows x D 77.76 = 9 x 8.64 grid).

1. CB16 rows (form (a), right-size): every cb* type loses D: type-frame y >= SHIFT_Y (1370.0, between the tap/strap
   cluster and the upper NK core row at 1382.4) moves down by D, so the upper NK core row lands at 1304.64 (NK core
   outline unchanged, lower row unchanged; measured clean band 34.56..51.84 um under the core row).  Collector
   relays left inside a moved core rect are re-sited CORE_CLEAR (4.32) below the core edge.  N/S windows are
   x-only; E/W windows and all points use the one y map, so the rows abut as before.
2. Array partitions (x >= ARRAY_X0) move down D per CB row fully below them (slices -4D, rows 4..7 -4D..-7D).
3. West strip follows (its slice / row seams are abutment ports and landing edges, not channel lanes): the three
   lower coll_ft collectors take the 4D (311.04) the slice band moved, inside measured clean bands:
   coll_ft__cl78c7b300 (coll_f0) -207.36 at type y >= 820 (clean 518.4..828.0) and coll_ft__cla4a25d77 (coll_f1,
   coll_f2) -51.84 at type y >= 300 (clean 196.56..322.70).  coll_core and every west partition above it, and the
   x<777.6 edge column above channel[0] (coll_ucie..tt_ctlm), move -4D; channel[0] top / channel[1] / channel[2]
   follow.  io_serdes_1/_2, coll_s, coll_f0 stay.
4. Seam re-site in cbf_q00_s2 (c_W5_bf_00 only, MX, row 1): its W seam to coll_s (which stays) would move -2D in
   the die frame, so every W-face item (serdes ft slot W pins/windows, landing pins, edge clocks, landing bands,
   collector local sources) moves -2D (155.52) in the type frame; the slot stations in the column beside the lower
   NK core are re-spaced evenly between the moved W end and the first station above the core (8.64 grid), with
   each station's bit sites moved rigidly with it.
5. Die-frame plan geometry (clock spine root, START provider stage rows / edge rects, bump field rects) uses the
   same per-partition map; provider partition-pin rects and the START root reset source (native rst_o pin, release,
   hop) are re-derived on the new plan; reset.root_part pins the base wavefront root (the PG-free snapped die rst_n
   pin would otherwise land 2.12 um across the sl_W0_sc / sl_W0_ctl seam).
6. --sidecar: the bind clock-landing sidecar (regions, collector types, edge hops) on the same maps.
Slice types, coll_s/coll_core/f3..f5/coll_n/PHY types, NK core outlines, PG strap pitch and reach are unchanged.
Idempotent guard: refuses a plan whose outline is not the base.
"""
import argparse, copy, json, os, sys

D = 77.76
SHIFT_Y = 1370.0
CORE_CLEAR = 4.32
GRID = 8.64
ARRAY_X0 = 1563.84
EDGE_X1 = 777.6
EDGE_Y0 = 7603.2   # top of channel[0] (x 0..777.6) = coll_ucie origin; checked in apply()
BASE_H, NEW_H = 26265.6, 26265.6 - 8 * D
EPS = 1e-6
SKIP = {"outline_um", "track_offset_um", "bit_site_cell_um", "resized_from_um"}
WEST_CUT = {"coll_ft__cl78c7b300": (820.0, 207.36), "coll_ft__cla4a25d77": (300.0, 51.84)}
SEAM_TYPE, SEAM_DY = "cbf_q00_s2", -2 * D
CTX = {}           # maps of the last apply(), for remap_sidecar()
PLAN_PATH = None   # the plan file (schema.Plan resolves hard-core pin tables next to it); set by main()


def r6(v):
    return round(v, 6)


def snap(v):
    return r6(round(v / GRID) * GRID)


def cb_ymap(y):
    return r6(y - D) if y >= SHIFT_Y - EPS else y


def is_num_list(o, n):
    return isinstance(o, list) and len(o) == n and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in o)


def walk_type(t, ymap, stats):
    """apply a type-frame y map to every point/rect and to E/W windows (N/S windows are x-only)."""
    def walk(o, key=None, face=None, out_face=None):
        if isinstance(o, dict):
            f = o.get("face", face)
            of = o.get("out_face", out_face)
            for k, v in o.items():
                if k in SKIP:
                    continue
                if k == "window_um" and is_num_list(v, 2):
                    if f in ("E", "W"):
                        o[k] = [ymap(v[0]), ymap(v[1])]
                        stats["win"] += 1
                    continue
                if k == "out_window_um" and is_num_list(v, 2):
                    if of in ("E", "W"):
                        o[k] = [ymap(v[0]), ymap(v[1])]
                        stats["win"] += 1
                    continue
                if is_num_list(v, 2):
                    o[k] = [v[0], ymap(v[1])]
                    stats["pt"] += 1
                elif is_num_list(v, 4):
                    o[k] = [v[0], ymap(v[1]), v[2], ymap(v[3])]
                    stats["rect"] += 1
                else:
                    walk(v, k, f, of)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                if is_num_list(v, 2) and key not in SKIP:
                    o[i] = [v[0], ymap(v[1])]
                    stats["pt"] += 1
                elif is_num_list(v, 4):
                    o[i] = [v[0], ymap(v[1]), v[2], ymap(v[3])]
                    stats["rect"] += 1
                else:
                    walk(v, key, face, out_face)
    walk(t)


def new_stats():
    return {"pt": 0, "rect": 0, "win": 0, "relay_resite": 0, "seam_items": 0, "stations_respaced": 0}


def shift_cb_type(t, stats):
    w, h = t["outline_um"]
    t["outline_um"] = [w, r6(h - D)]
    walk_type(t, cb_ymap, stats)
    cores = [(c["origin_um"][0], c["origin_um"][1], c["origin_um"][0] + c["outline_um"][0],
              c["origin_um"][1] + c["outline_um"][1]) for c in t.get("hard_cores", [])]
    upper = [c for c in cores if SHIFT_Y - D - EPS < c[1] < SHIFT_Y]
    tree = (t.get("clock", {}).get("landing_contract", {}) or {}).get("collector_tree") or {}
    for rl in tree.get("relays", []):
        x, y = rl["xy"]
        for (x0, y0, x1, y1) in upper:
            if x0 + EPS < x < x1 - EPS and y0 - EPS < y < y1 - EPS:
                rl["xy"] = [x, r6(y0 - CORE_CLEAR)]
                stats["relay_resite"] += 1


def cut_type(t, line, cut, stats):
    w, h = t["outline_um"]
    t["outline_um"] = [w, r6(h - cut)]
    walk_type(t, lambda y: r6(y - cut) if y >= line - EPS else y, stats)


def resite_w_seam(t, dy, stats):
    """move every W-face item of the type by dy (type frame) and re-space the ft-slot stations beside the lower core."""
    core_top = min(c["origin_um"][1] + c["outline_um"][1] for c in t["hard_cores"])
    lc = t["clock"]["landing_contract"]
    names = set()
    for s in t.get("ft_slots", []):
        if "W" not in (s["in_face"], s["out_face"]):
            continue
        regs, groups = s["regs_um"], s["bit_sites_um"]
        if len(groups) != len(regs) - 1:
            raise SystemExit(f"refuse: {s['name']} bit-site groups {len(groups)} != stations {len(regs) - 1}")
        if s["in_face"] == "W":
            regs[0] = [regs[0][0], r6(regs[0][1] + dy)]
        else:
            s["out_window_um"] = [r6(v + dy) for v in s["out_window_um"]]
        names.add(s["name"])
        stations = range(1, len(regs))
        low = sorted((i for i in stations if regs[i][1] < core_top), key=lambda i: regs[i][1])
        anchor = min(regs[i][1] for i in stations if regs[i][1] >= core_top)
        y0 = r6(regs[low[0]][1] + dy)
        for j, i in enumerate(low):
            ny = y0 if j == 0 else snap(y0 + (anchor - y0) * j / len(low))
            d = ny - regs[i][1]
            regs[i] = [regs[i][0], r6(ny)]
            groups[i - 1] = [[b[0], r6(b[1] + d)] for b in groups[i - 1]]
            stats["stations_respaced"] += 1
    for p in lc["pins"]:
        if p["xy_um"][0] < 5.0 and p["xy_um"][1] < core_top:
            p["xy_um"] = [p["xy_um"][0], r6(p["xy_um"][1] + dy)]
            stats["seam_items"] += 1
    for e in t["clock"].get("edge_clocks", []):
        if e["tap_um"][0] < 5.0 and e["tap_um"][1] < core_top:
            e["tap_um"] = [e["tap_um"][0], r6(e["tap_um"][1] + dy)]
            stats["seam_items"] += 1
    for k, b in lc["bands"].items():
        if k.endswith("_i") and k[:-2] in names and b["rect_um"][0] < 5.0 + 17.28:
            r = b["rect_um"]
            b["rect_um"] = [r[0], r6(r[1] + dy), r[2], r6(r[3] + dy)]
            stats["seam_items"] += 1
    for src in lc.get("collector_local_sources", []):
        if src["xy_um"][0] < 5.0 and src["xy_um"][1] < core_top:
            for k in ("xy_um", "pin_xy_um"):
                src[k] = [src[k][0], r6(src[k][1] + dy)]
            r = src["band"]["rect_um"]
            src["band"]["rect_um"] = [r[0], r6(r[1] + dy), r[2], r6(r[3] + dy)]
            stats["seam_items"] += 1


def rows_of(plan, T):
    cb = {n for n in T if n.startswith("cb")}
    return sorted({(q["origin_um"][1], q["origin_um"][1] + T[q["type"]]["outline_um"][1])
                   for q in plan["partitions"] if q["type"] in cb})


def die_y(y, rows):
    """array die-frame y map: D per CB row fully below y."""
    return r6(y - D * sum(1 for (r0, r1) in rows if r1 <= y + EPS))


def west_dy(x, y, cuts):
    """west-strip die-frame shift at (x, y): the collector cuts below y; the x < EDGE_X1 edge column takes the full
    cut from the top of its lowest channel (EDGE_Y0, coll_ucie and above: it abuts coll_core and above only)."""
    full = sum(c for _, c in cuts)
    if x < EDGE_X1 - EPS and y >= EDGE_Y0 - EPS:
        return -full
    return -sum(c for ln, c in cuts if ln <= y + EPS)


class DieMap:
    """old die frame -> new die frame, through the partition (and its type map) holding the point."""

    def __init__(self, old_parts, old_T, new_parts, new_T, rows, cuts, type_maps):
        self.o, self.oT, self.n, self.nT = old_parts, old_T, new_parts, new_T
        self.rows, self.cuts, self.tm = rows, cuts, type_maps

    def __call__(self, x, y):
        for name, q in self.o.items():
            ox, oy = q["origin_um"]
            w, h = self.oT[q["type"]]["outline_um"]
            if ox - EPS <= x <= ox + w + EPS and oy - EPS <= y <= oy + h + EPS:
                o = q.get("orient", "R0")
                if o not in ("R0", "MX"):
                    raise SystemExit(f"refuse: orient {o} of {name}")
                ty = y - oy if o == "R0" else h - (y - oy)
                nty = self.tm.get(q["type"], lambda v: v)(ty)
                ny0 = self.n[name]["origin_um"][1]
                nh = self.nT[q["type"]]["outline_um"][1]
                return [x, r6(ny0 + (nty if o == "R0" else nh - nty))]
        if x >= ARRAY_X0 - EPS:
            return [x, die_y(y, self.rows)]
        return [x, r6(y + west_dy(x, y, self.cuts))]


def _tools():
    here = os.path.dirname(os.path.abspath(__file__))
    p = os.path.normpath(os.path.join(here, "..", "..", "..", "tools", "die_plan"))
    if p not in sys.path:
        sys.path.insert(0, p)


def base_reset_root(plan):
    """the reset wavefront root of the base plan (reset.root_part or the partition at the die rst_n pin)."""
    if plan.get("reset", {}).get("root_part") or plan.get("reset", {}).get("release") != "wavefront":
        return None
    _tools()
    import schema as S, reset_tree as RT
    P = S.Plan(copy.deepcopy(plan))
    return RT._root_part(P, sorted(n for n in P.parts if not P.types[P.parts[n]["type"]].get("hard")))


def refresh_reset_source(plan, rs):
    """START root reset source: the native rst_o pin position, release and hop re-derived on the new plan."""
    _tools()
    import schema as S, reset_tree as RT, reset_route as RR, gen_phys, start_provider_plan as SP
    P = S.Plan(plan, path=PLAN_PATH)
    part, pin = rs["part"], rs["pin"]
    tn = P.parts[part]["type"]
    native = next(q for q in RR.scalar_pins(P, tn) if q["name"] == pin)
    rs["xy_um"] = list(P.to_die(part, native["xy_um"]))
    rs["source_part_release_cycles"] = RT.wf_plan(P)["parts"][part]["release"]
    root = next(n for n in plan["clock"]["landing_network"]["start_tree"]["provider"]["nodes"] if n.get("root"))
    tw = gen_phys.LAYER_W[P.layer_budget["partition_signal_max"]] / 2
    hh = gen_phys.tap_pin_height(P, tn, pin) / 2
    x, y = native["xy_um"]
    a, b = P.to_die(part, [x - tw, y - hh]), P.to_die(part, [x + tw, y + hh])
    rs["hop_to_root_um"] = SP.hop([min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])], root["rect_um"])
    return {"xy_um": rs["xy_um"], "release": rs["source_part_release_cycles"], "hop_to_root_um": rs["hop_to_root_um"]}


def remap_start_tree(plan, dm):
    st = plan["clock"].get("landing_network", {}).get("start_tree")
    if not st:
        return None
    rs = st.get("reset_source")
    if isinstance(rs, dict) and is_num_list(rs.get("xy_um"), 2):
        rs["xy_um"] = dm(*rs["xy_um"])
    pr = st.get("provider")
    if not pr:
        return {"nodes": 0}

    def rect(r):
        a, b = dm(r[0], r[1]), dm(r[2], r[3])
        return [r[0], min(a[1], b[1]), r[2], max(a[1], b[1])]
    by = {}
    for n in pr["nodes"]:
        n["rect_um"] = rect(n["rect_um"])
        n["clock_node_xy_um"] = dm(*n["clock_node_xy_um"])
        by[n["id"]] = n["rect_um"]
    _tools()
    import schema as S
    P = S.Plan(plan, path=PLAN_PATH)
    pins = 0
    for e in pr["edges"]:
        for end, key in (("src_stage", "src_rect_um"), ("dst_stage", "dst_rect_um")):
            if end in e:
                e[key] = by[e[end]]
        if "part" in e:
            xy = P.to_die(e["part"], next(p["xy_um"] for p in P.ptype(e["part"])["clock"]["landing_contract"]["pins"]
                                          if p["name"] == e["pin"]))
            key = "src_rect_um" if "dst_stage" in e else "dst_rect_um"
            e[key] = list(xy) + list(xy)          # == start_provider_plan.pin_rect (exact, unrounded)
            pins += 1
    out = {"nodes": len(pr["nodes"]), "edges": len(pr["edges"]), "pin_rects": pins}
    if isinstance(rs, dict) and rs.get("part"):
        out["reset_source"] = refresh_reset_source(plan, rs)
    return out


def apply(plan):
    die = plan["die"]
    if abs(die["outline_um"][1] - BASE_H) > EPS:
        raise SystemExit(f"refuse: die outline y {die['outline_um'][1]} is not the base {BASE_H}")
    root0 = base_reset_root(plan)
    T = plan["partition_types"]
    old_T = {n: {"outline_um": list(t["outline_um"])} for n, t in T.items()}
    old_parts = {q["name"]: copy.deepcopy(q) for q in plan["partitions"]}
    cb = sorted(n for n in T if n.startswith("cb"))
    rows = rows_of(plan, T)
    if len(rows) != 8:
        raise SystemExit(f"refuse: expected 8 CB rows, found {rows}")
    stats = {n: new_stats() for n in cb + sorted(WEST_CUT)}
    before = {n: list(T[n]["outline_um"]) for n in stats}
    for n in cb:
        shift_cb_type(T[n], stats[n])
    resite_w_seam(T[SEAM_TYPE], SEAM_DY, stats[SEAM_TYPE])
    for n, (line, cut) in WEST_CUT.items():
        cut_type(T[n], line, cut, stats[n])
    ins = plan.get("reset", {}).get("in_sites", {})
    for k, v in list(ins.items()):
        if k.startswith("cb"):
            ins[k] = [v[0], cb_ymap(v[1])]
        elif k in WEST_CUT and v[1] >= WEST_CUT[k][0] - EPS:
            ins[k] = [v[0], r6(v[1] - WEST_CUT[k][1])]
    ch0 = [c["rect_um"] for c in die.get("channels", []) if c["rect_um"][2] <= EDGE_X1 + EPS]
    if not ch0 or abs(min(r[3] for r in ch0) - EDGE_Y0) > EPS:
        raise SystemExit(f"refuse: edge-column channel top {ch0} != {EDGE_Y0}")
    cuts = sorted((r6(q["origin_um"][1] + WEST_CUT[q["type"]][0]), WEST_CUT[q["type"]][1])
                  for q in plan["partitions"] if q["type"] in WEST_CUT)
    if abs(sum(c for _, c in cuts) - 4 * D) > EPS:
        raise SystemExit(f"refuse: west cuts {cuts} != slice band move {4 * D}")
    moved = 0
    for q in plan["partitions"]:
        x, y = q["origin_um"]
        ny = die_y(y, rows) if x >= ARRAY_X0 - EPS else r6(y + west_dy(x, y, cuts))
        if ny != y:
            q["origin_um"] = [x, ny]
            moved += 1
    die["outline_um"] = [die["outline_um"][0], r6(NEW_H)]
    for c in die.get("channels", []):
        r = c["rect_um"]
        y0 = r6(r[1] + west_dy(r[0], r[1], cuts)) if r[1] > EPS else r[1]
        y1 = r6(NEW_H) if abs(r[3] - BASE_H) < EPS else r6(r[3] + west_dy(r[0], r[3], cuts))
        c["rect_um"] = [r[0], y0, r[2], y1]
    for f in die.get("pg", {}).get("bumps", {}).get("fields", []):
        f["rects_um"] = [[r[0], die_y(r[1], rows) if r[1] > EPS else r[1], r[2],
                          r6(NEW_H) if abs(r[3] - BASE_H) < EPS else die_y(r[3], rows)] for r in f["rects_um"]]
    type_maps = {n: cb_ymap for n in cb}
    for n, (ln, c) in WEST_CUT.items():
        type_maps[n] = (lambda ln, c: (lambda v: r6(v - c) if v >= ln - EPS else v))(ln, c)
    dm = DieMap(old_parts, old_T, {q["name"]: q for q in plan["partitions"]}, T, rows, cuts, type_maps)
    sp = plan["clock"]["spine"]
    sp["root_um"] = dm(*sp["root_um"])
    # the die rst_n pin is PG-free snapped on the fixed die stripe grid: after the -4D move it lands 2.12 um across
    # the sl_W0_sc / sl_W0_ctl seam, so the default root would flip; keep the base reset root explicitly
    if root0 and not plan["reset"].get("root_part"):
        plan["reset"]["root_part"] = root0
    prov = remap_start_tree(plan, dm)
    note = (f"DIE-QC-66/PLAN 11-03 y-shrink (die y <= 25690): 16 cb* types -{D} um at type y>={SHIFT_Y}; array "
            f"partitions -{D}/CB row below; west coll_ft__cl78c7b300 -207.36 / coll_ft__cla4a25d77 -51.84, west above "
            f"coll_f2 -{r6(4 * D)}; cbf_q00_s2 W seam -{r6(-SEAM_DY)}; die {BASE_H} -> {r6(NEW_H)}; PG strap pitch, "
            f"reach, NK cores unchanged")
    plan["note"] = note + " <- " + plan.get("note", "")
    CTX.update(old_parts=old_parts, old_T=old_T, type_maps=type_maps,
               seam_names={s["name"] for s in T[SEAM_TYPE].get("ft_slots", []) if "W" in (s["in_face"], s["out_face"])})
    return {"outline_before": [die["outline_um"][0], BASE_H], "outline_after": die["outline_um"],
            "partitions_moved": moved, "west_cuts_die": cuts, "spine_root_um": sp["root_um"], "start_provider": prov,
            "types": {n: {"before": before[n], "after": T[n]["outline_um"], **stats[n]} for n in stats},
            "channels": [c["rect_um"] for c in die.get("channels", [])],
            "bump_rects": [f["rects_um"] for f in die["pg"]["bumps"]["fields"]]}


def _to_die(origin, outline, orient, pt):
    w, h = outline
    x, y = pt
    X, Y = {"R0": (x, y), "MX": (x, h - y), "MY": (w - x, y), "R180": (w - x, h - y)}[orient]
    return origin[0] + X, origin[1] + Y


def remap_sidecar(sc, plan, ctx):
    """bind clock-landing sidecar (die-frame region boxes, per-type collector geometry, collector edge hops) on the
    same maps: changed types take the plan's new collector tree / local sources / children; the other type-frame
    points use the type map (W seam items of cbf_q00_s2 move SEAM_DY); region boxes follow their member partitions;
    edge hops move by the change of their child-node -> reset-entry distance."""
    old_parts, old_T, type_maps, seam_names = ctx["old_parts"], ctx["old_T"], ctx["type_maps"], ctx["seam_names"]
    T = plan["partition_types"]
    new = {q["name"]: q for q in plan["partitions"]}
    st = new_stats()
    # 1. region boxes
    for r in sc["regions"]:
        b = r["box_um"]
        mem = [n for n, q in old_parts.items()
               if b[0] <= q["origin_um"][0] + old_T[q["type"]]["outline_um"][0] / 2 < b[2]
               and b[1] <= q["origin_um"][1] + old_T[q["type"]]["outline_um"][1] / 2 < b[3]]
        if not mem:
            raise SystemExit(f"refuse: sidecar region {r['tag']} holds no partition")
        o0 = min(old_parts[n]["origin_um"][1] for n in mem)
        o1 = max(old_parts[n]["origin_um"][1] + old_T[old_parts[n]["type"]]["outline_um"][1] for n in mem)
        n0 = min(new[n]["origin_um"][1] for n in mem)
        n1 = max(new[n]["origin_um"][1] + T[new[n]["type"]]["outline_um"][1] for n in mem)
        r["box_um"] = [b[0], r6(b[1] + n0 - o0) if b[1] > EPS else b[1], b[2],
                       r6(NEW_H) if abs(b[3] - BASE_H) < EPS else r6(b[3] + n1 - o1)]
    for n, q in new.items():
        w, h = T[q["type"]]["outline_um"]
        x, y = q["origin_um"][0] + w / 2, q["origin_um"][1] + h / 2
        k = [r["tag"] for r in sc["regions"] if r["box_um"][0] <= x < r["box_um"][2] and r["box_um"][1] <= y < r["box_um"][3]]
        if len(k) != 1:
            raise SystemExit(f"refuse: sidecar region map for {n}: {k}")
    # 2. per-type collector geometry
    C = sc["collector"]
    old_geo = {tn: copy.deepcopy({k: C["types"][tn][k] for k in ("children", "reset_entry_um")}) for tn in C["types"]}
    for tn, ym in type_maps.items():
        t = C["types"].get(tn)
        if t is None:
            continue
        lc = T[tn]["clock"]["landing_contract"]
        for k, pk in (("tree", "collector_tree"), ("local_sources", "collector_local_sources"), ("children", "collector_children")):
            if k in t and pk in lc:
                t[k] = copy.deepcopy(lc[pk])
        for k in ("reset_entry_um", "collector_root_xy"):
            if is_num_list(t.get(k), 2):
                t[k] = [t[k][0], ym(t[k][1])]
        walk_type(t.get("bands", {}), ym, st)
        for g in (t.get("bus_geometry") or {}).values():
            if g.get("face") in ("E", "W") and is_num_list(g.get("window_um"), 2):
                g["window_um"] = [ym(g["window_um"][0]), ym(g["window_um"][1])]
        if tn == SEAM_TYPE:
            for k, b in t.get("bands", {}).items():
                if k.endswith("_i") and k[:-2] in seam_names and b["rect_um"][0] < 5.0 + 17.28:
                    r = b["rect_um"]
                    b["rect_um"] = [r[0], r6(r[1] + SEAM_DY), r[2], r6(r[3] + SEAM_DY)]
            for k, g in (t.get("bus_geometry") or {}).items():
                if g.get("face") == "W" and k[:-2] in seam_names:
                    g["window_um"] = [r6(v + SEAM_DY) for v in g["window_um"]]
                    st["seam_items"] += 1
    # 3. collector edge hops (child node of the parent -> reset entry of the child)
    def dist(geo, parts, TT, e):
        dq, sq = parts[e["dst"]], parts[e["src"]]
        ch = geo[dq["type"]]["children"][e["dst_index"]]["xy_um"]
        a = _to_die(dq["origin_um"], TT[dq["type"]]["outline_um"], dq.get("orient", "R0"), ch)
        b = _to_die(sq["origin_um"], TT[sq["type"]]["outline_um"], sq.get("orient", "R0"), geo[sq["type"]]["reset_entry_um"])
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
    for e in C.get("edges", []):
        d = dist(C["types"], new, T, e) - dist(old_geo, old_parts, old_T, e)
        e["hop_um"] = r6(e["hop_um"] + d)
    if C.get("edges"):
        C["max_die_hop_um"] = max(e["hop_um"] for e in C["edges"])
    return {"regions": len(sc["regions"]), "edges": len(C.get("edges", [])), "max_die_hop_um": C.get("max_die_hop_um"),
            "seam_items": st["seam_items"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--out")
    ap.add_argument("--report")
    ap.add_argument("--sidecar", help="bind clock-landing sidecar JSON of this plan, remapped in place")
    a = ap.parse_args()
    global PLAN_PATH
    PLAN_PATH = os.path.abspath(a.plan)
    raw = open(a.plan).read()
    plan = json.loads(raw)
    rep = apply(plan)
    s = json.dumps(plan) + ("\n" if raw.endswith("\n") else "")
    open(a.out or a.plan, "w").write(s)
    if a.sidecar:
        sraw = open(a.sidecar).read()
        sc = json.loads(sraw)
        rep["sidecar"] = remap_sidecar(sc, plan, CTX)
        ind = 1 if sraw.startswith("{\n ") and not sraw.startswith("{\n  ") else None
        open(a.sidecar, "w").write(json.dumps(sc, indent=ind) + ("\n" if sraw.endswith("\n") else ""))
        print("sidecar", json.dumps(rep["sidecar"]))
    if a.report:
        json.dump(rep, open(a.report, "w"), indent=1)
    print(json.dumps({k: rep[k] for k in ("outline_before", "outline_after", "partitions_moved", "spine_root_um",
                                          "west_cuts_die", "start_provider", "channels")}))
    print("relay_resite", sum(v["relay_resite"] for v in rep["types"].values()),
          "seam", rep["types"][SEAM_TYPE]["seam_items"], rep["types"][SEAM_TYPE]["stations_respaced"])


if __name__ == "__main__":
    main()
