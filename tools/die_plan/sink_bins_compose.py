#!/usr/bin/env python3
"""Compose a type's clock sink bins from its NATIVE bins + the flops the plan rows add (QC-PLAN-R3 V1, FABLE-CBC-QK-0130 s7).

Rule (FABLE-CBC-QK-0130 section 7): at compose, every row that adds flops (station x bits, pad stages, landing rings, lockup
latches) adds its count to the bin at its site; placed dumps refresh only the native logic.  Then clock.tap_max_sinks holds by
construction: the density taps (clock.tap_mode "density", taps.density_taps) are solved from clock.sink_bins_file, and bins
measured on a placed kit miss the flops that rows added after the measurement (QC su_l1 / fw_v2 / stm / ctl / su_l0 1.6-2.6x).

compose_bins(P_raw, tn, base_bins, ...) -> (doc, report).  doc = the bins form {bin_um, n, bins: [[x_c, y_c, count]], type,
placed_kit, source} + provenance {native_bins_file, native_sha256, added: {class: flops}, rows: [...]}.  Classes:
  station   partition_types.<t>.internal_stations, one chain per bus (kit_istations.bus_entries), (bus width + 1 epoch) flops
            per stage; core pin-face chains (rows with 'core') (len(core_bits) + 1) per stage; core<->core rows bits per stage.
            Sites: exact banks (bit_sites_um, one flop per site) EXACT; plain rows at regs_um[j] (wide N/S ranks: the
            kit_istations.ordered_station_row 10-bit groups over x +- 90 um) EXACT as the kit FIRMs them; bit_route per_bit /
            chain / sites=float / core chains at regs_um[j] = the row's nominal centroid (the kit spreads bits along each
            bit's L route): APPROX site, exact count.
  pad       the receiver lane pad u_lpad_<bus> (bind.lane_pad from the latency table: cycles - 2 - ft stations - clock landing,
            less the source kit's out-bus stations and the destination core chains when the lane's fixed_cycles price them,
            native_istations rules), (W + 1) x D flops.  IN-bus stations absorb the pad (kit_istations packed_input_delay), so
            only max(0, D - stations) stages are added here.  Sites spread evenly on face pin window -> bus leaf: APPROX.
  landing   clock landing rings (clock.landing_contract.bands[*].clock_roles.local_read_flops, on the die clock; the
            forwarded_write_flops are on fclk_in* nets, not die clock sinks, and are NOT added) spread over the band rect;
            landing_reader_start / landing_writer_start stages, one flop per distinct stage site.  EXACT count, band-spread site.
  lockup    budgets.r_dly_lockup (gen_phys.dly_lockup_cfg) types: one ot_dp_lk latch per bit on every segment boundary of a
            pad delay line with D > seg: (ceil(D / seg) - 1) x (W + 1), at the boundary points of the pad line.  The u_fl_*_i /
            _o latches (delay fed by a delay / read by a hard core) depend on the bound netlist: NOT derivable, listed.
A rank sited at one point is spread over its flop footprint (FLOP_UM2 / UTIL; per-bit, pad, core-chain and lockup ranks along
their bus pin window), the way placement spreads it; the count is unchanged.  Anything counted at a best site, or not derivable from the plan alone, is listed in the report (approx / not_counted), never
silently skipped.

Idempotent: the base is ALWAYS the native file.  A composed doc keeps its native file path in "native_bins_file"; composing a
type whose clock.sink_bins_file is already a composed doc starts from that native file again.

Native bins: a placed dump holds every flop of the kit, row flops included.  sink_bins_from_place.py bins --native-only drops
the row instances (ROW_INST_RE) so a refreshed dump is native logic only; the report flags a base that is a plain placed dump
(rows present at measurement time are then counted twice: an upper bound).

  sink_bins_compose.py PLAN OUT_PLAN (--types a,b | --all-density) --bins-dir DIR [--report R.json] [--no-apply]
     writes DIR/<type>__composed.json (DIR relative to the tree root = the current directory, an event tree root) and sets
     clock.sink_bins_file through sink_bins_from_place.apply_bins (retap.py re-points forwarded clock outputs and reset
     consumer taps in the same step).
"""
import argparse
import copy
import hashlib
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# row-added instances in a placed dump (flattened names): stations, lane pads, bind pad stages, hop lockups, landing rings
ROW_INST_RE = re.compile(r"(^|[./])(u_ist_|u_isj_|u_lpad_|u_fl_|u_cland_|u_b(?:in|out)_\w+?_pad\d+)")
CLASSES = ("station", "pad", "landing", "lockup")
# footprint of a rank of flops sited at one point: a placed rank occupies its flop area at placement density, so its sinks
# spread over several bins (a 2,000-bit stage in ONE 10.8 um bin is unsplittable by any tap solve).  ASAP7 DFFHQNx1 is
# 0.29 um2; 0.5 local utilisation.
FLOP_UM2 = 0.29
UTIL = 0.5


def snap(x, y, bin_um):
    """bin centre of (x, y), the sink_bins_from_place.bins / binsrep rule"""
    return (round((math.floor(x / bin_um) + .5) * bin_um, 3), round((math.floor(y / bin_um) + .5) * bin_um, 3))


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _centre(box):
    (x, y), (w, h) = box.get("origin_um", [0, 0]), box.get("outline_um", [0, 0])
    return (float(x) + float(w) / 2.0, float(y) + float(h) / 2.0)


def face_point(t, b):
    """centre of a bus's pin window on its face (type frame); None without face / window"""
    W, H = map(float, t["outline_um"])
    f, win = b.get("face"), b.get("window_um")
    if f not in ("N", "S", "E", "W") or not win:
        return None
    m = (float(win[0]) + float(win[1])) / 2.0
    return {"N": (m, H), "S": (m, 0.0), "E": (W, m), "W": (0.0, m)}[f]


def leaf_point(t, b):
    """centre of the bus's leaf instance (contents / hard_cores) in the type frame; None when the leaf has no box"""
    inst = str(b.get("leaf", "")).split(".")[0]
    for c in list(t.get("contents") or []) + list(t.get("hard_cores") or []):
        if c.get("inst") == inst and c.get("origin_um") and c.get("outline_um"):
            return _centre(c)
    return None


def on_line(a, c, frac):
    return (a[0] + (c[0] - a[0]) * frac, a[1] + (c[1] - a[1]) * frac)


def _bus_depths(t):
    """{bus name: station depth} of a type's bus rows (one chain per bus: deepest entry; core chains apart)"""
    out, core = {}, {}
    for e in t.get("internal_stations") or []:
        c = str(e.get("conn", ""))
        if not c.startswith("bus:"):
            continue
        d = core if e.get("core") else out
        d[c[4:]] = max(d.get(c[4:], 0), len(e.get("regs_um") or []))
    return out, core


def lane_pads(raw, tn):
    """{in bus: (D, [lane ids], spread)} receiver lane pads of type tn from the plan latency table (bind.lane_pad with the
    native_istations source / destination-core cuts); D is the max over the type's partitions (a pad is a type property)."""
    ports = {p["id"]: p for p in raw.get("ports", [])}
    parts = {p["name"]: p for p in raw.get("partitions", [])}
    types = raw["partition_types"]
    lat = (raw.get("latency") or {}).get("lanes", {})
    _, dcore = _bus_depths(types[tn])
    out = {}
    for ln in raw.get("lanes", []):
        if not ln.get("ports") or ln["id"] not in lat:
            continue
        a, b = ports[ln["ports"][0]]["src"], ports[ln["ports"][-1]]["dst"]
        if parts.get(b.get("part"), {}).get("type") != tn:
            continue
        L, fixed = lat[ln["id"]], int(ln.get("fixed_cycles", 0))
        D = int(L.get("cycles", 0)) - 2 - int(L.get("stations", 0)) - int(L.get("clock_landing", 0))
        st = types.get(parts.get(a.get("part"), {}).get("type"), {})
        n_src = _bus_depths(st)[0].get(a.get("bus"), 0) if st else 0
        if n_src and fixed >= n_src:
            D -= n_src
        n_core = dcore.get(b["bus"], 0)
        if n_core and fixed >= n_core:
            D -= n_core
        D = max(0, D)
        cur = out.setdefault(b["bus"], [0, [], set()])
        cur[0] = max(cur[0], D); cur[1].append(ln["id"]); cur[2].add(D)
    return {k: (v[0], v[1], sorted(v[2])) for k, v in out.items() if v[0] > 0}


def compose_bins(P_raw, tn, base_bins, native_bins_file=None, native_sha=None, plan_sha=None):
    """-> (doc, report).  base_bins = the NATIVE bins doc; every row-added flop of type tn snapped into its bin_um bins."""
    import kit_istations as KI
    t = P_raw["partition_types"][tn]
    bin_um = float(base_bins.get("bin_um", 10.8))
    acc = {}
    for r in base_bins["bins"]:
        k = (round(float(r[0]), 3), round(float(r[1]), 3))
        acc[k] = acc.get(k, 0) + (r[2] if len(r) > 2 else 1)
    added = {c: 0 for c in CLASSES}
    rows, approx, not_counted = [], [], []

    Wo, Ho = map(float, t["outline_um"])

    def add(cls, x, y, n, along=0.0, axis=None):
        """n flops of one rank at (x, y): spread over a footprint, along the bus pin axis (axis 'x' or 'y', length along =
        the pin window: the bits of a per-bit / pad stage follow their pins) and at least the rank's flop area"""
        if n <= 0:
            return
        area = n * FLOP_UM2 / UTIL
        la = max(float(along), math.sqrt(area))
        lc = max(bin_um, area / la) if la > bin_um else la
        if n == 1 or la <= bin_um:
            pts = [(float(x), float(y))]
        else:
            ka, kc = max(1, math.ceil(la / bin_um)), max(1, math.ceil(lc / bin_um))
            pts = []
            for i in range(ka):
                for j in range(kc):
                    u, v = -la / 2 + la * (i + .5) / ka, -lc / 2 + lc * (j + .5) / kc
                    px, py = (x + v, y + u) if axis == "y" else (x + u, y + v)
                    pts.append((min(max(px, 0.0), Wo), min(max(py, 0.0), Ho)))
        q, r = divmod(n, len(pts))
        for i, (px, py) in enumerate(pts):
            m = q + (1 if i < r else 0)
            if m:
                k = snap(px, py, bin_um)
                acc[k] = acc.get(k, 0) + m
        added[cls] += n

    def pin_axis(b):
        """(window length, axis) of a bus: bits of an E/W face spread in y, of an N/S face in x"""
        win = b.get("window_um") if b else None
        if not win or b.get("face") not in ("N", "S", "E", "W"):
            return 0.0, None
        return abs(float(win[1]) - float(win[0])), ("y" if b["face"] in ("E", "W") else "x")

    buses = {b["name"]: b for b in t.get("buses") or [] if isinstance(b, dict) and "name" in b}
    # -- station rows ------------------------------------------------------------------------------------------------
    plain = [e for e in t.get("internal_stations") or [] if not e.get("core")]
    st_depth = {}
    for e in KI.bus_entries(dict(t, internal_stations=plain)):
        bus = e["conn"][4:]; b = buses.get(bus)
        regs = e.get("regs_um") or []
        if b is None:
            not_counted.append(dict(cls="station", conn=e["conn"], why="bus not in the type"))
            continue
        W = int(b.get("width", 1)); S = len(regs)
        st_depth[bus] = max(st_depth.get(bus, 0), S)
        form = "exact" if e.get("bit_sites_um") is not None else (e.get("bit_route") or ("float" if e.get("sites") == "float" else "plain"))
        n0 = sum(added.values())
        if form == "exact":
            banks = e["bit_sites_um"][:S] if S else e["bit_sites_um"]
            for bank in banks:
                for p in bank:
                    add("station", p[0], p[1], 1)
            if len(banks) != S or any(len(bk) != W + 1 for bk in banks):
                approx.append(dict(cls="station", conn=e["conn"], why=f"exact banks {len(banks)} x {[len(bk) for bk in banks][:3]} != stages {S} x W+1 {W + 1}"))
        elif form == "plain" and W > 256 and b.get("face") in ("N", "S"):
            for x, y in regs:          # kit_istations.ordered_station_row: 10-bit groups over x +- 90 um, epoch at the site
                groups = (W + 9) // 10
                lo, hi = x - 90.0, x + 90.0
                lo, hi = max(2.0, lo), min(float(t["outline_um"][0]) - 2.0, hi)
                for g in range(groups):
                    add("station", lo + (hi - lo) * g / max(1, groups - 1), y, min(10, W - 10 * g))
                add("station", x, y, 1)
        else:
            ln, ax = pin_axis(b) if form != "plain" else (0.0, None)
            for x, y in regs:
                add("station", x, y, W + 1, ln, ax)
            if form != "plain":
                approx.append(dict(cls="station", conn=e["conn"], why=f"{form}: {S} x {W + 1} flops at regs_um centroids"))
        rows.append(dict(cls="station", conn=e["conn"], form=form, stages=S, width=W, flops=sum(added.values()) - n0))
    for e in t.get("internal_stations") or []:
        if not e.get("core"):
            continue
        regs = e.get("regs_um") or []
        nb = len(e.get("core_bits") or []) + 1
        ln, ax = pin_axis(buses.get(str(e.get("conn", ""))[4:]))
        for x, y in regs:
            add("station", x, y, nb, ln, ax)
        rows.append(dict(cls="station", conn=e["conn"], form="core_chain", core=e["core"], stages=len(regs), width=nb - 1, flops=nb * len(regs)))
        approx.append(dict(cls="station", conn=e["conn"], why=f"core chain {e['core']}: {len(regs)} x {nb} at regs_um centroids"))
    for e in t.get("internal_stations") or []:
        if str(e.get("conn", "")).startswith("bus:"):
            continue
        regs = e.get("regs_um") or []; nb = int(e.get("bits", 1))
        for x, y in regs:
            add("station", x, y, nb)
        rows.append(dict(cls="station", conn=e.get("conn"), form="core_core", stages=len(regs), width=nb, flops=nb * len(regs)))
        approx.append(dict(cls="station", conn=e.get("conn"), why="core<->core row: counted bits x stages; the leaf RTL may hold them natively"))
    # -- lane pads + lockup latches ----------------------------------------------------------------------------------
    import gen_phys
    lk = gen_phys.dly_lockup_cfg(P_raw.get("budgets") or {}, tn)
    for bus, (D, lids, spread) in sorted(lane_pads(P_raw, tn).items()):
        b = buses.get(bus)
        if b is None:
            not_counted.append(dict(cls="pad", conn="bus:" + bus, why="lane lands on a bus the type does not declare"))
            continue
        W = int(b.get("width", 1))
        extra = max(0, D - st_depth.get(bus, 0))
        a, c = face_point(t, b), leaf_point(t, b)
        why = []
        if a is None:
            a = (float(t["outline_um"][0]) / 2.0, float(t["outline_um"][1]) / 2.0); why.append("no face window: outline centre")
        if c is None:
            c = a; why.append("leaf without a box: at the face")
        n0 = added["pad"]
        for j in range(st_depth.get(bus, 0), D):          # stages 0..S-1 sit on the station sites (counted as station)
            x, y = on_line(a, c, (j + 1) / (D + 1))
            add("pad", x, y, W + 1, *pin_axis(b))
        rows.append(dict(cls="pad", conn="bus:" + bus, D=D, stations=st_depth.get(bus, 0), stages_added=extra, width=W,
                         flops=added["pad"] - n0, lanes=len(lids), D_seen=spread))
        approx.append(dict(cls="pad", conn="bus:" + bus, why="u_lpad stages spread face window -> leaf (GPL / chain_even site)"
                           + ("; " + "; ".join(why) if why else "") + (f"; partitions disagree D {spread}" if len(spread) > 1 else "")))
        if lk and D > lk["seg"]:
            nseg = math.ceil(D / lk["seg"])
            n1 = added["lockup"]
            for s in range(1, nseg):
                x, y = on_line(a, c, (s * D / nseg) / (D + 1))
                add("lockup", x, y, W + 1, *pin_axis(b))
            rows.append(dict(cls="lockup", conn="bus:" + bus, D=D, seg=lk["seg"], boundaries=nseg - 1, width=W, flops=added["lockup"] - n1))
    if lk:
        not_counted.append(dict(cls="lockup", why=f"r_dly_lockup seg {lk['seg']}: u_fl_*_i / _o latches (delay fed by a delay, "
                                "delay read by a hard core) and bind landing-pad chains u_pd* / tail copies depend on the bound netlist"))
    # -- landing rings -----------------------------------------------------------------------------------------------
    ck = t.get("clock") or {}
    fwd = 0
    for name, bd in sorted(((ck.get("landing_contract") or {}).get("bands") or {}).items()):
        roles = bd.get("clock_roles") or {}
        n = int(roles.get("local_read_flops", 0)); fwd += int(roles.get("forwarded_write_flops", 0))
        rects = bd.get("rects_um") or ([bd["rect_um"]] if bd.get("rect_um") else [])
        if not n:
            continue
        if not rects:
            not_counted.append(dict(cls="landing", conn=name, why=f"{n} local read flops, band without rect"))
            continue
        cells = []
        for x0, y0, x1, y1 in rects:
            nx, ny = max(1, math.ceil((x1 - x0) / bin_um)), max(1, math.ceil((y1 - y0) / bin_um))
            cells += [(x0 + (x1 - x0) * (i + .5) / nx, y0 + (y1 - y0) * (k + .5) / ny) for i in range(nx) for k in range(ny)]
        q, r = divmod(n, len(cells))
        for i, (x, y) in enumerate(cells):
            add("landing", x, y, q + (1 if i < r else 0))
        rows.append(dict(cls="landing", conn=name, flops=n, rects=len(rects), instance=bd.get("instance")))
    seen = set()
    for key in ("landing_reader_start", "landing_writer_start"):
        for br, v in sorted(((ck.get(key) or {}).get("branches") or {}).items()):
            for j, s in enumerate(v.get("stages") or []):
                xy = s.get("xy_um")
                if not xy:
                    continue
                sk = (key, j, round(xy[0], 3), round(xy[1], 3), s.get("raw_reset"))
                if sk in seen:          # share_trunk: one stage serves the branches that list it
                    continue
                seen.add(sk); add("landing", xy[0], xy[1], 1)
    if seen:
        rows.append(dict(cls="landing", conn="fstart stages", flops=len(seen)))
        approx.append(dict(cls="landing", conn="fstart stages", why="one flop per distinct (start key, stage, site, reset); shared-trunk dedupe"))
    if fwd:
        not_counted.append(dict(cls="landing", why=f"{fwd} forwarded_write_flops: clocked by fclk_in*, not die clock sinks"))
    if ck.get("landing_ring_wreg"):
        not_counted.append(dict(cls="landing", why="landing_ring_wreg write registers: size not in the plan"))
    bins_out = [[x, y, n] for (x, y), n in sorted(acc.items()) if n]
    doc = dict(bin_um=bin_um, n=sum(n for _, _, n in bins_out), bins=bins_out, type=tn,
               placed_kit=base_bins.get("placed_kit", base_bins.get("type", tn)),
               source=f"sink_bins_compose.py: native {native_bins_file} + plan rows " + json.dumps({k: v for k, v in added.items() if v}),
               native_bins_file=native_bins_file, native_sha256=native_sha, native_n=int(sum(r[2] if len(r) > 2 else 1 for r in base_bins["bins"])),
               added=added, plan_sha256=plan_sha)
    rep = dict(type=tn, native_bins_file=native_bins_file, native_n=doc["native_n"], added=added, composed_n=doc["n"],
               ratio=round(doc["n"] / doc["native_n"], 4) if doc["native_n"] else None, rows=rows, approx=approx,
               not_counted=not_counted, base_is_native=bool(base_bins.get("native_only")),
               base_source=str(base_bins.get("source", base_bins.get("src", "")))[:160])
    return doc, rep


def native_file(raw, tn, plan_dir, root):
    """(rel path, abs Path, doc) of a type's NATIVE bins: the current sink_bins_file, or its native_bins_file when composed"""
    import taps
    rel = raw["partition_types"][tn].get("clock", {}).get("sink_bins_file")
    if not rel:
        raise ValueError(f"{tn}: no clock.sink_bins_file")
    p = taps.input_path(rel, plan_dir, root)
    doc = json.loads(p.read_text())
    seen = {rel}
    while doc.get("native_bins_file"):
        rel = doc["native_bins_file"]
        if rel in seen:
            raise ValueError(f"{tn}: native_bins_file loop at {rel}")
        seen.add(rel)
        p = taps.input_path(rel, plan_dir, root)
        doc = json.loads(p.read_text())
    return rel, p, doc


def tap_stats(raw, path, tn):
    """(n taps, max planned sinks per tap) of the density solve, via taps.density_taps"""
    import schema
    import taps
    P = schema.Plan(json.loads(json.dumps(raw)), path)
    ts = taps.density_taps(P, tn)
    return len(ts), max(t[3] for t in ts), [(t[0], t[1], t[2]) for t in ts]


def old_taps_load(raw_new, path, tn, old_taps):
    """max sinks on the OLD tap set, nearest tap and no cap (native vs composed sinks: the over-plan the old bins hid)"""
    import schema
    import taps
    P = schema.Plan(json.loads(json.dumps(raw_new)), path)
    load = [0.0] * len(old_taps)
    for x, y, w in taps.sink_sites(P, tn):
        j = min(range(len(old_taps)), key=lambda i: abs(old_taps[i][1] - x) + abs(old_taps[i][2] - y))
        load[j] += w
    return round(max(load))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan"); ap.add_argument("out")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--types"); g.add_argument("--all-density", action="store_true")
    ap.add_argument("--bins-dir", required=True, help="output dir of <type>__composed.json, relative to the tree root (cwd)")
    ap.add_argument("--report"); ap.add_argument("--no-apply", action="store_true", help="write bins + report, plan unchanged")
    ap.add_argument("--tap-stats", action="store_true", help="report density taps before / after (taps.density_taps)")
    a = ap.parse_args(argv)
    import taps
    root = Path.cwd().resolve()
    if root != taps._root().resolve():
        print(f"WARN cwd {root} is not the tools tree root {taps._root()}: bins paths resolve against the tools tree", file=sys.stderr)
    plan_path = Path(a.plan)
    raw = json.loads(plan_path.read_text())
    plan_sha = _sha(plan_path)
    pt = raw["partition_types"]
    if a.all_density:
        types = sorted(tn for tn, t in pt.items() if (t.get("clock") or {}).get("tap_mode") == "density" and t["clock"].get("sink_bins_file"))
    else:
        types = [x for x in a.types.split(",") if x]
        miss = [x for x in types if x not in pt]
        if miss:
            raise SystemExit(f"types not in plan: {miss}")
    outdir = Path(a.bins_dir)
    if outdir.is_absolute():
        raise SystemExit("--bins-dir must be relative to the tree root")
    (root / outdir).mkdir(parents=True, exist_ok=True)
    reps, bmap, errs = {}, {}, {}
    for tn in types:
        try:
            rel, p, base = native_file(raw, tn, plan_path.resolve().parent, root)
            doc, rep = compose_bins(raw, tn, base, rel, _sha(p), plan_sha)
        except (ValueError, KeyError, OSError, TypeError) as ex:
            errs[tn] = f"{type(ex).__name__}: {ex}"[:300]
            continue
        f = outdir / f"{tn}__composed.json"
        (root / f).write_text(json.dumps(doc) + "\n")
        bmap[tn] = str(f); reps[tn] = rep
    old_raw = copy.deepcopy(raw)
    retap = {}
    if bmap and not a.no_apply:
        import sink_bins_from_place as SB
        retap = SB.apply_bins(raw, bmap, str(plan_path))
        plan_path_out = Path(a.out)
        plan_path_out.write_text(json.dumps(raw, indent=1) + "\n")
    if a.tap_stats:
        new = copy.deepcopy(old_raw)
        for tn, f in bmap.items():
            new["partition_types"][tn]["clock"]["sink_bins_file"] = f
        for tn in bmap:
            try:
                n0, m0, old_t = tap_stats(old_raw, str(plan_path), tn)
                n1, m1, _ = tap_stats(new, str(plan_path), tn)
                reps[tn]["taps"] = dict(before=n0, after=n1, max_sinks_before=round(m0), max_sinks_after=round(m1),
                                        old_taps_max_nearest_native=old_taps_load(old_raw, str(plan_path), tn, old_t),
                                        old_taps_max_nearest_composed=old_taps_load(new, str(plan_path), tn, old_t),
                                        tap_max_sinks=pt[tn]["clock"].get("tap_max_sinks"))
            except (ValueError, KeyError, OSError, TypeError, ZeroDivisionError) as ex:
                reps[tn]["taps"] = dict(error=f"{type(ex).__name__}: {ex}"[:200])
    for tn, r in reps.items():
        print("COMPOSE", tn, "native", r["native_n"], "added", json.dumps({k: v for k, v in r["added"].items() if v}),
              "composed", r["composed_n"], "ratio", r["ratio"], *(["taps", json.dumps(r["taps"])] if "taps" in r else []))
    for tn, e in errs.items():
        print("ERROR", tn, e)
    print("SINK-BINS-COMPOSE types", len(reps), "errors", len(errs), "retap types", len(retap),
          "refs", sum(len(c) for c in retap.values()), "plan", "unchanged" if a.no_apply else a.out)
    if a.report:
        Path(a.report).write_text(json.dumps(dict(plan=str(plan_path), plan_sha256=plan_sha, bins_dir=str(outdir), types=reps,
                                                  errors=errs, retap=retap), indent=1) + "\n")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
