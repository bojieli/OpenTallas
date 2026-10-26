#!/usr/bin/env python3
"""MASTER PLAN FIRST -- city-planning model (METHODOLOGY 12.7 + 12.8, OWNER 2026-10-26).  One shared tool, every die.

    die_infra.py master-plan PLAN --out D [--mesh MESH] [--tracks preroute.json] [--pg pg.json] [--ir R.json ...]
                             [--entries E.json] [--sites infra_sites.json] [--render]
    (or python3 tools/die_plan/master_plan.py PLAN --out D ...)

Writes D/master_plan.json (census, corridors, bays, entry pins, gates), D/gates.json (the static plan gate verdicts
+ per-check FAIL lists), D/slices/<type>.json (one slice per partition type and per hard-core module, format
opentallas.master_plan_slice.v1, read by tools/die_plan/master_slice.py in the kit generators) and D/master_plan.png.
Exit 1 when any gate FAILs or is NOT RUN (the plan cannot freeze on it).  Read-only on the plan.

Built on INFRA-FIRST-R2's outputs: islands, hard-core rows and the via-stack limit come from infra_sites.run()
(read-only call); PG IR comes from the PG lane's PDNSim result.json files (--ir); the clock geometry from the die
clock mesh dir (--mesh, die_clock_mesh.py build output).

Model (stated, not measured; every constant is a CLI knob):
  CENSUS   every plan lane = one die-level path (bits = widest port of the lane); its geometry = the port face
           points + the declared ft-slot station registers (regs_um) of every partition it crosses; plus every type
           internal_station route (partition-internal long route, from_um -> regs -> to_um).  Abutted one-port lanes
           are census rows of length 0 (no road).
  ROADS    every leg between two registers is routed Manhattan inside its partition (infra_sites.route_leg: HV, VH
           or a Z through a soft column/row, detour <= --detour-um).  Each segment is a band of width = the slot /
           bus window (else bits x pitch x 2) carrying `bits` tracks spread over the band's gcells (10.8 um, the GRT
           gcell).  Layer per segment, greedy by bits: declared slot layers of the segment's direction, then the other
           M4-M7 layer of that direction, then leftover M8 (H) / M9 (V); first one whose worst gcell use stays <= 0.6.
           Capacity per gcell = gcell / pitch x (1 - lower_pg_frac) on M4-M7 (0 over a hard core for layers <=
           core_obs_top, 0 inside an island); M8/M9 = gcell / pitch x leftover fraction (preroute tracks_taken, else
           the PG grid stripes + spacing).
  BAYS     rest stops along every leg: the station registers (bay = the plan's declared bit_sites box when present)
           and repeater bays placed so no gap between rest stops exceeds reach (405 um, any layer incl. M6/M7 over hard
           cores).  A repeater bay sits only on a legal site (soft partition area - hard cores - island, or a declared
           in-core bay).  Where no legal site exists within reach (a core longer than reach on the path and no Z detour
           fits) the gap FAILs and an IN-CORE BAY is proposed at the reach point (core-local coordinates, owner core).
           Bay area = bits x cell / --bay-fill (station flop 1.404 x 0.27, repeater BUFx4 0.378 x 0.27); rect = band
           width x depth (rows of 0.27 um).  Bays are deduplicated per type in the type frame (one kit per type).
  ON-RAMPS every segment the router puts on M8/M9 enters its partition at M7 entry pins beside the bay at both ends
           (one VIA78 per pin; VIA89 + VIA78 for M9).  Per-gcell limit (documented derivation, entry_pin_limit()):
             free_L = gcell / pitch_L x free fraction  (M7 0.064 um pitch: 168.75 tracks/gcell x (1 - lower_pg_frac);
                      M8/M9 0.080 um: 135 tracks x leftover after PG/clock/reset)
             stagger = 0.5: V7 cut 0.032 wide, spacing 0.046 > the 0.032 gap between cuts on adjacent M7 tracks
                      (pitch 0.064), so VIA78s on neighbouring M7 tracks must stagger by one M8 track: at most every
                      other M7 track carries a pin per M8 row.  The M8 landing (0.054 x 0.040) + EOL spacing 0.04 needs
                      0.094 um along M8 > one M7 pitch, the same factor on the M8 side.
             limit = floor(margin 0.6 (12.7e) x stagger x min(free_M7, free_M8, free_M9 when the path uses M9)).
  INFRA    islands = infra_sites (clock drivers + regional reset ONLY, 12.2a) + the hard-core clock entries (12.8a);
           hard-core entry = --entries {module: {"xy": [x, y] core-local}} else the core centre on the 4.32-um PG
           lattice; island 8.64 x 8.64 lattice-aligned around it, M9->M5 stack, M5 interior clock pin at the entry.
GATES (12.7b + 12.8), each FAIL closed; NOT RUN (no input) also blocks the freeze:
  reach_gap        max rest-stop gap <= reach on every leg (in-core bay proposals listed with core-local rects)
  bay_fill         every bay fill <= 0.6, bays inside their partition clear of cores/islands; partition fill
                   (declared est. std-cell fill + bays) <= 0.6
  corridor_tracks  every gcell use <= 0.6 on every layer; no road through a fully blocked section
  entry_pins       pins per gcell <= limit
  clock_shield     every die clock strap/segment (mesh straps + routed clock guides, M8/M9) has a PG stripe on both
                   sides with no free signal track in between (gap < NDR space + min width + min space) and no planned
                   M8/M9 road band within that spacing
  static_ir        every PDNSim region result PASS and declared worst-case power ("power_basis": "worst_case")
  lot_fit          every hard core inside its type outline, no core/core, island/core (except in-core entries) or
                   bay/core overlap, in-core islands/bays inside their core
  clock_entry      (12.8a) every hard core's clock pin (plan tap <inst>.ck) == its slice entry (tol 0.5 um)
  core_reach       (12.8b) entry-to-farthest-corner Manhattan distance <= 200 um, else the core is RESTRUCTURE
  early_taps       (12.8d) no tap declares an insertion different from the die common latency; no mesh tap with
                   early_ps != 0
  tree_balance     (12.8d) sibling H-tree legs equal length (<= 1 um) and equal stub per tap class (<= 20 um)
"""
import argparse
import hashlib
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import schema as S  # noqa: E402
import infra_sites as IS  # noqa: E402
import master_rulings as MR  # noqa: E402

G = 10.8
ROW = 0.27
A_FLOP = 1.404 * ROW
A_REP = 0.378 * ROW
LAT = 4.32                       # die PG stripe lattice (M8/M9 VDD/VSS every 4.32 um)
SLICE_SCHEMA = "opentallas.master_plan_slice.v1"
PLAN_SCHEMA = "opentallas.master_plan.v1"
DIRS = {"H": ("M4", "M6", "M8"), "V": ("M5", "M7", "M9")}
LOWER = ("M4", "M5", "M6", "M7")


def lnum(L):
    return int(L[1:])


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def r3(v):
    return round(float(v), 3)


def snap(v, q=LAT):
    return round(round(v / q) * q, 4)


# ------------------------------------------------------------------------------------------------------ census
def _win(s, key):
    w = s.get(key)
    return abs(w[1] - w[0]) if w and len(w) == 2 else None


def census(P):
    """paths: [dict(id, kind, bits, src, dst, ports, legs=[dict(part, slot, pts, band_um, layers)])]."""
    paths = []
    for lid, ln in P.lanes.items():
        ports = [P.ports[q] for q in ln["ports"] if q in P.ports]
        if not ports:
            continue
        bits = max(int(p.get("width", 1)) for p in ports)
        src, dst = ports[0]["src"], ports[-1]["dst"]
        legs = []
        for part, slot, pin, pout in P.lane_crossings(lid):
            if part not in P.parts or not slot:
                continue
            s = P.slot(part, slot)
            if s is None:
                continue
            try:
                a, b = P.port_point(pin), P.port_point(pout)
            except (KeyError, TypeError):
                continue
            regs = [P.to_die(part, tuple(r)) for r in s.get("regs_um", [])]
            band = _win(s, "out_window_um") or _win(s, "in_window_um")
            legs.append(dict(part=part, slot=slot, pts=[tuple(a)] + regs + [tuple(b)], band_um=band,
                             layers=list(s.get("layers", [])), bit_sites=s.get("bit_sites_um")))
        length = sum(IS.seg_len(p, q) for lg in legs for p, q in zip(lg["pts"], lg["pts"][1:]))
        paths.append(dict(id=lid, kind=ports[0].get("kind", "data"), bits=bits, ports=len(ports),
                          src=f"{src['part']}.{src['bus']}", dst=f"{dst['part']}.{dst['bus']}", legs=legs,
                          length_um=r3(length)))
    for part, p in P.parts.items():
        t = P.types[p["type"]]
        for k, st in enumerate(t.get("internal_stations", [])):
            pts = [st["from_um"]] + st.get("regs_um", []) + [st["to_um"]]
            pts = [P.to_die(part, tuple(q)) for q in pts]
            bits = int(st.get("bits", 1))
            band, layers = None, []
            m = re.match(r"bus:(.+)", st.get("conn", ""))
            if m:
                for b in t.get("buses", []):
                    if b["name"] == m.group(1):
                        band = _win(b, "window_um")
                        layers = list(b.get("layers", []))
            length = sum(IS.seg_len(a, b) for a, b in zip(pts, pts[1:]))
            paths.append(dict(id=f"{part}:istn{k}", kind="internal", bits=bits, ports=0, src=f"{part}.{st.get('conn')}",
                              dst=f"{part}.{st.get('capture', '')}", length_um=r3(length),
                              legs=[dict(part=part, slot=f"istn{k}", pts=pts, band_um=band, layers=layers,
                                         bit_sites=None)]))
    return paths


# ------------------------------------------------------------------------------------------------------ geometry
def part_blockers(P, part, islands):
    """die-frame blockers of a partition: hard cores (x0, y0, x1, y1, inst, module) + its island."""
    t = P.ptype(part)
    out = [IS.rect_pts(P, part, c[:4]) + tuple(c[4:]) for c in IS.type_cores(t)]
    isl = islands.get(P.parts[part]["type"])
    if isl:
        out.append(IS.rect_pts(P, part, isl["rect_um"]) + ("island", "island"))
    return out


def core_entry(h, entries):
    """core-local clock entry of a hard core (12.8a): --entries[module].xy else the centre on the 4.32 lattice."""
    e = (entries or {}).get(h["module"]) or {}
    w, hh = h["outline_um"]
    if "xy" in e:
        return tuple(float(v) for v in e["xy"]), e.get("source", "entries")
    return (snap(w / 2), snap(hh / 2)), "centre"



def core_clock_entry_check(P, h, taps, proposed, tolerance=0.5):
    """Check one real native clock pin and its declared tap against the proposed entry.

    A proposed centre is not evidence of a native pin. Do not choose among two
    core taps, or silently overwrite duplicate names in a dictionary.
    """
    inst = h["inst"]
    row = dict(inst=inst, module=h["module"], entry_um=list(proposed), issues=[])
    candidates = [tp for tp in taps if tp.get("name") in (inst, inst+".ck", inst+".clk")
                  or (tp.get("kind") == "core" and tp.get("name", "").startswith(inst+"."))]
    if len(candidates) != 1:
        row["issues"].append("ambiguous plan core clock taps" if candidates else "no plan clock tap")
    tp = candidates[0] if len(candidates) == 1 else None
    pins = list(h.get("pins") or [])
    if h.get("pins_file"):
        name = Path(h["pins_file"])
        base = Path(P.path).parent if P.path else Path.cwd()
        choices = [name] if name.is_absolute() else [base/name, Path(__file__).resolve().parents[2]/name]
        try:
            path = next((p for p in choices if p.is_file()), choices[0])
            data = json.loads(path.read_text())
            pins.extend(data.get("pins", []) if isinstance(data, dict) else data)
            row["pins_file"] = str(path)
        except (OSError, ValueError, TypeError) as ex:
            row["issues"].append(f"unreadable native pin metadata: {ex}")
    port = tp["name"][len(inst)+1:] if tp and tp["name"] != inst else None
    native = set()
    wanted = {port} if port else {"ck", "clk"}
    for pin in pins:
        if not isinstance(pin, dict):
            row["issues"].append("invalid native pin metadata row")
            continue
        name = pin.get("name")
        if name not in wanted:
            continue
        xy = pin.get("xy", [pin.get("x"), pin.get("y")])
        try:
            xy = tuple(float(v) for v in xy)
            if len(xy) != 2 or not all(math.isfinite(v) for v in xy):
                raise ValueError("invalid native coordinate")
            native.add((name, xy))
        except (TypeError, ValueError):
            row["issues"].append("invalid native clock pin coordinate")
    if len(native) != 1:
        row["issues"].append("ambiguous native clock pins" if native else "missing native core clock-pin metadata")
    else:
        name, xy = next(iter(native))
        row.update(native_pin=name, native_core_um=list(xy))
        d = abs(xy[0]-proposed[0])+abs(xy[1]-proposed[1])
        row["native_to_entry_um"] = r3(d)
        if d > tolerance:
            row["issues"].append("native clock pin differs from proposed entry")
        if tp:
            placed = dict(h, origin_um=[a+b for a,b in zip(h["origin_um"],h.get("track_offset_um",[0,0]))])
            cl = type_to_core_pt(placed, tp["xy"])
            dn = abs(cl[0]-xy[0])+abs(cl[1]-xy[1])
            de = abs(cl[0]-proposed[0])+abs(cl[1]-proposed[1])
            row.update(plan_tap=tp["name"], pin_core_um=[r3(v) for v in cl],
                       tap_to_native_um=r3(dn), off_um=r3(de))
            if dn > tolerance:
                row["issues"].append("plan clock tap differs from native clock pin")
            if de > tolerance:
                row["issues"].append("plan clock tap differs from proposed entry")
    row["verdict"] = "FAIL" if row["issues"] else "PASS"
    if row["issues"]:
        row["issue"] = "; ".join(row["issues"])
    return row


def entry_island(xy, side=8.64):
    """lattice-aligned island rect (8.64 square, edges on the 4.32 PG lattice) containing the entry point."""
    x0 = math.floor(xy[0] / LAT) * LAT
    y0 = math.floor(xy[1] / LAT) * LAT
    if xy[0] - x0 < 1e-6:
        x0 -= LAT
    if xy[1] - y0 < 1e-6:
        y0 -= LAT
    return [r3(x0), r3(y0), r3(x0 + side), r3(y0 + side)]


def core_to_type(h, r):
    """core-local rect -> type frame through the core orient."""
    ox, oy = h["origin_um"]
    w, hh = h["outline_um"]
    o = h.get("orient", "R0")
    x0, y0, x1, y1 = r
    X0, X1 = (w - x1, w - x0) if o in ("MY", "R180") else (x0, x1)
    Y0, Y1 = (hh - y1, hh - y0) if o in ("MX", "R180") else (y0, y1)
    return (ox + X0, oy + Y0, ox + X1, oy + Y1)


def type_to_core_pt(h, pt):
    ox, oy = h["origin_um"]
    w, hh = h["outline_um"]
    o = h.get("orient", "R0")
    x, y = pt[0] - ox, pt[1] - oy
    return ({"R0": (x, y), "MX": (x, hh - y), "MY": (w - x, y), "R180": (w - x, hh - y)}[o])


def restructure_islands(w, h, reach=200.0):
    """12.8b fix proposal: the smallest power-of-two nx x ny H-tree leaf grid whose leaf regions have centre ->
    corner Manhattan <= reach; one 8.64 island per leaf centre (core-local, 4.32 lattice)."""
    nx = ny = 1
    while w / nx / 2 + h / ny / 2 > reach:
        if w / nx >= h / ny:
            nx *= 2
        else:
            ny *= 2
    out = []
    for i in range(nx):
        for j in range(ny):
            c = (snap((i + 0.5) * w / nx), snap((j + 0.5) * h / ny))
            out.append(dict(centre_um=[r3(c[0]), r3(c[1])], rect_um=entry_island(c)))
    return dict(grid=[nx, ny], leaf_reach_um=r3(w / nx / 2 + h / ny / 2), islands=out)


def _type_rect(P, part, r):
    pts = [P.to_type(part, c) for c in ((r[0], r[1]), (r[2], r[3]))]
    return (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))


def phy_entries(P):
    """12.8 / COORD 06:23: a PHY macro's clock pin sits on its digital-strip edge (the PHY edge facing the widest
    soft margin of its partition), fed from an 8.64 island in that strip; no clock tap inside the macro.
    Returns {type: dict(phy, phy_rect_um, strip_rect_um, clock_pin {edge, xy_um, layer}, island)} (type frame)."""
    out = {}
    for io in P.die.get("io") or []:
        if io.get("kind") not in ("phy_macro", "phy", "serdes") or not io.get("rect_um") or io.get("part") not in P.parts:
            continue
        part = io["part"]
        tn = P.parts[part]["type"]
        if tn in out:
            continue
        W, H = P.types[tn]["outline_um"]
        x0, y0, x1, y1 = _type_rect(P, part, io["rect_um"])
        margins = dict(S=(y0, (0.0, 0.0, W, y0)), N=(H - y1, (0.0, y1, W, H)),
                       W=(x0, (0.0, 0.0, x0, H)), E=(W - x1, (x1, 0.0, W, H)))
        edge = max(margins, key=lambda k: margins[k][0])
        depth, strip = margins[edge]
        if depth < 8.64 + 1e-6:
            out[tn] = dict(phy=io["name"], phy_rect_um=[r3(v) for v in (x0, y0, x1, y1)], strip_rect_um=None,
                           error="no digital strip >= 8.64 um beside the PHY")
            continue
        cx = snap((x0 + x1) / 2) if edge in ("S", "N") else None
        cy = snap((y0 + y1) / 2) if edge in ("W", "E") else None
        pin = dict(S=(cx, y0), N=(cx, y1), W=(x0, cy), E=(x1, cy))[edge]
        mid = dict(S=(cx, y0 - depth / 2), N=(cx, y1 + depth / 2), W=(x0 - depth / 2, cy), E=(x1 + depth / 2, cy))[edge]
        tap = (P.types[tn].get("clock") or {}).get("tap_um")
        tap_in = bool(tap) and x0 < tap[0] < x1 and y0 < tap[1] < y1
        out[tn] = dict(phy=io["name"], module=io.get("iface"), plan_tap_um=tap, plan_tap_inside_phy=tap_in, phy_rect_um=[r3(v) for v in (x0, y0, x1, y1)],
                       strip_rect_um=[r3(v) for v in strip], strip_edge=edge, strip_depth_um=r3(depth),
                       clock_pin=dict(edge=edge, xy_um=[r3(pin[0]), r3(pin[1])], layer="M5",
                                      note="published PHY interface edge; no clock tap inside the macro"),
                       island=entry_island(mid), island_centre_um=[r3(mid[0]), r3(mid[1])])
    return out


def core_lattice(centres, q=0.01, lat=8.64):
    """12.8 / COORD 06:23 commensurate die tree: per axis, the core-centre island lattice pitch (smallest gap) and
    the gaps that are not an integer multiple of it.  A die tree whose node/leaf pitch is an integer multiple of
    this pitch (leaf pitch 2 x pitch puts every node midpoint on a core centre) lands every node/driver on a
    core-centre island."""
    res = {}
    for ax in (0, 1):
        raw = sorted(c[ax] for c in centres)
        vs, grp = [], []           # merge lines closer than one island (orientation snapping of the same column)
        for v in raw:
            if grp and v - grp[0] > lat + 1e-6:
                vs.append(sum(grp) / len(grp))
                grp = []
            grp.append(v)
        if grp:
            vs.append(sum(grp) / len(grp))
        gaps = [round(b - a, 3) for a, b in zip(vs, vs[1:]) if b - a > 1.0]
        if not gaps:
            res["xy"[ax]] = dict(pitch_um=None, lines=len(vs), irregular=[])
            continue
        p = min(gaps)
        bad = sorted({g for g in gaps if abs(g / p - round(g / p)) > 1e-3})

        def cover(L):        # share of lines whose +L translate is a line too (or falls past the array end)
            hit = sum(1 for v in vs if v + L > vs[-1] + lat or any(abs(v + L - u) <= lat / 2 for u in vs))
            return hit / len(vs)
        # commensurate leaf pitch: smallest pairwise line distance that maps >= 90 % of the core-centre lines onto
        # lines (the repeat of the abutted core array); a tree node then lands on a centre when its half-span
        # offset maps lines onto lines too
        cands = sorted({round(b - a, 3) for i, a in enumerate(vs) for b in vs[i + 1:i + 12] if b - a > lat})
        leaf = next((L for L in cands if cover(L) >= 0.9), None)
        res["xy"[ax]] = dict(pitch_um=r3(p), on_lattice=abs(p / lat - round(p / lat)) < 1e-3, lines=len(vs),
                             span_um=[r3(vs[0]), r3(vs[-1])], irregular=bad[:20], n_irregular=len(bad),
                             leaf_pitch_um=r3(leaf) if leaf else None,
                             leaf_cover=r3(cover(leaf)) if leaf else None,
                             half_leaf_node_on_centre=r3(cover(leaf / 2)) if leaf else None,
                             breaks=[[r3(a), r3(b)] for a, b in zip(vs, vs[1:])
                                     if leaf and b - a > leaf + lat][:10])
    return res


def clock_sites(M, islands_die, glue_parts, macros_die, tol=0.5):
    """COORD 06:23 gate: every die tree node and mesh driver on a declared island; no clock driver in tile glue
    (inside a partition that holds hard cores, outside every island) and none inside a hard macro."""
    from collections import Counter as _C
    pts = []
    for e in M.get("htree", []):
        pts.append(("tree_node", e.get("tag"), tuple(e["b"])))
    for k, d in (M.get("drivers") or {}).items():
        pts.append(("mesh_driver", k, tuple(d.get("site") or d.get("ideal"))))
    # bin islands for speed
    B = 200.0
    bins = defaultdict(list)
    for r in islands_die:
        for i in range(int((r[0] - tol) // B), int((r[2] + tol) // B) + 1):
            for j in range(int((r[1] - tol) // B), int((r[3] + tol) // B) + 1):
                bins[(i, j)].append(r)

    def on(xy, rs):
        return any(r[0] - tol <= xy[0] <= r[2] + tol and r[1] - tol <= xy[1] <= r[3] + tol for r in rs)
    cnt, glue, inmac, examples = _C(), _C(), _C(), []
    for kind, name, xy in pts:
        ok = on(xy, bins.get((int(xy[0] // B), int(xy[1] // B)), []))
        cnt[(kind, ok)] += 1
        if ok:
            continue
        where = "soft"
        if on(xy, [m[:4] for m in macros_die]):
            where = "macro"
            inmac[kind] += 1
        elif on(xy, glue_parts):
            where = "tile_glue"
            glue[kind] += 1
        if len(examples) < 40:
            examples.append(dict(kind=kind, name=name, xy_um=[r3(xy[0]), r3(xy[1])], where=where))
    off = sum(v for (k, ok), v in cnt.items() if not ok)
    return dict(verdict="PASS" if not off else "FAIL",
                tree_nodes=cnt[("tree_node", True)] + cnt[("tree_node", False)],
                tree_nodes_off_island=cnt[("tree_node", False)],
                mesh_drivers=cnt[("mesh_driver", True)] + cnt[("mesh_driver", False)],
                mesh_drivers_off_island=cnt[("mesh_driver", False)], in_tile_glue=dict(glue), in_macro=dict(inmac),
                declared_islands=len(islands_die), examples=examples)


def island_lattice(M, island_centres, core_rects, B=400.0):
    """12.2a1/12.2c gate: every die tree node / mesh driver coincides with a per-type island (displacement to the
    nearest declared island centre, should be 0), and no die-level clock cell sits inside a hard-core outline (the
    in-core island drivers are PUSHDOWN cells of the core netlist; the die only connects to their ft ports)."""
    bins = defaultdict(list)
    for c in island_centres:
        bins[(int(c[0] // B), int(c[1] // B))].append(c)
    cb = defaultdict(list)
    for r in core_rects:
        for i in range(int(r[0] // B), int(r[2] // B) + 1):
            for j in range(int(r[1] // B), int(r[3] // B) + 1):
                cb[(i, j)].append(r)

    def near(xy):
        i, j = int(xy[0] // B), int(xy[1] // B)
        best = None
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for c in bins.get((i + di, j + dj), []):
                    d = abs(c[0] - xy[0]) + abs(c[1] - xy[1])
                    best = d if best is None or d < best else best
        return best if best is not None else float("inf")
    rows = defaultdict(list)
    in_core = defaultdict(int)
    worst = []
    pts = [("tree_node", e.get("tag"), tuple(e["b"])) for e in M.get("htree", [])]
    pts += [("mesh_driver", k, tuple(d.get("site") or d.get("ideal"))) for k, d in (M.get("drivers") or {}).items()]
    for kind, name, xy in pts:
        d = near(xy)
        rows[kind].append(d)
        worst.append((d, kind, name, xy))
        if any(r[0] < xy[0] < r[2] and r[1] < xy[1] < r[3] for r in cb.get((int(xy[0] // B), int(xy[1] // B)), [])):
            in_core[kind] += 1
    worst.sort(key=lambda t: -t[0] if t[0] != float("inf") else -1e18)
    stat = {k: dict(n=len(v), max_um=r3(max(v)) if v and max(v) < float("inf") else None,
                    mean_um=r3(sum(x for x in v if x < float("inf")) / max(1, sum(1 for x in v if x < float("inf")))),
                    displaced=sum(1 for x in v if x > 0.5)) for k, v in rows.items()}
    bad = sum(v["displaced"] for v in stat.values()) + sum(in_core.values())
    return dict(verdict="PASS" if not bad and pts else ("NOT RUN" if not pts else "FAIL"), displacement=stat,
                die_cells_in_core_outline=dict(in_core),
                worst=[dict(kind=k, name=n, xy_um=[r3(x[0]), r3(x[1])], disp_um=r3(d) if d < float("inf") else None)
                       for d, k, n, x in worst[:30]],
                note="a mesh driver / tree node at an in-core island is the core's PUSHDOWN driver (12.2a1): the die "
                     "mesh build must reference its ft ports, not place a die cell there")


# ---- 12.8 d1 / 12.2a1 island driver sizing from plan geometry only (deterministic, frozen with the slice)
# ASAP7 clock buffers (TT, approx. effective drive resistance, input cap): the plan picks the smallest cell whose
# R x C_load meets the 12.8 slew budget (slew ~ 2.2 R C <= 80 ps -> R C <= 36 ps).  C_load = NDR wire c x the
# driven length + sink input caps.  No measurement feeds this choice.
DRV_CELLS = [("BUFx4_ASAP7_75t_R", 2.40, 1.2), ("BUFx8_ASAP7_75t_R", 1.20, 1.7), ("BUFx12f_ASAP7_75t_R", 0.80, 2.0),
             ("BUFx16f_ASAP7_75t_R", 0.60, 2.3), ("BUFx24_ASAP7_75t_R", 0.40, 2.35)]
WIRE_FF_PER_UM = 0.20
CLOCK_REP_UM = 450.0                 # 12.1e repeaters <= 450 um (H-tree leg repeaters, COORD 06:53)
CLOCK_REP_CELL = "BUFx24_ASAP7_75t_R"   # die_clock_mesh leg repeater master
RC_BUDGET_PS = 36.0


def size_driver(length_um, sinks, sink_cin_ff=2.0):
    c = WIRE_FF_PER_UM * length_um + sinks * sink_cin_ff
    for name, r, cin in DRV_CELLS:
        if r * c <= RC_BUDGET_PS:
            return dict(cell=name, parallel=1, load_ff=r3(c), rc_ps=r3(r * c))
    name, r, cin = DRV_CELLS[-1]
    n = math.ceil(r * c / RC_BUDGET_PS)
    return dict(cell=name, parallel=n, load_ff=r3(c), rc_ps=r3(r * c / n))


def pushdown_island(k, rect, centre, role, drive_len_um, sinks):
    """12.2a1 pushdown spec of one in-core island: ft ports (in from the M9->M5 stack, out to the die mesh/tree or
    the core-internal tree), fixed driver cells at the island centre, sizing per 12.8 d1."""
    cx, cy = centre
    return dict(name=f"isl{k}", role=role, rect_um=rect, centre_um=[r3(cx), r3(cy)], via_stack=["M9", "M5"],
                ft_ports=[dict(name=f"mp_isl{k}_ck_i", dir="in", layer="M5", xy_um=[r3(cx - 2.16), r3(cy + 2.16)],
                               connect="die M9 clock stack (M9->M5 at the island centre)"),
                          dict(name=f"mp_isl{k}_ck_o", dir="out", layer="M5", xy_um=[r3(cx + 2.16), r3(cy + 2.16)],
                               connect="die mesh/tree feed-through net; independent core clock pin"),
                          dict(name=f"mp_isl{k}_rst_i", dir="in", layer="M5", xy_um=[r3(cx - 2.16), r3(cy - 2.16)],
                               connect="die regional reset stack (M9->M5)"),
                          dict(name=f"mp_isl{k}_rst_o", dir="out", layer="M5", xy_um=[r3(cx + 2.16), r3(cy - 2.16)],
                               connect="die reset feed-through net; independent core reset pin")],
                driver=dict(size_driver(drive_len_um, sinks), placement="fixed dont_touch at centre_um",
                            basis="12.8 d1: plan geometry only (driven length %.1f um, %d sinks)" % (drive_len_um, sinks)),
                lec="die-owned feed-through: no core logic on mp_isl* ports (12.2a1)")


def rect_overlap(a, b, eps=1e-6):
    return min(a[2], b[2]) - max(a[0], b[0]) > eps and min(a[3], b[3]) - max(a[1], b[1]) > eps


def subtract_rectangles(rect, blockers):
    """Disjoint legal pieces of a reserved bay; subtract real core/island holes."""
    pieces = [tuple(rect)]
    for c in blockers:
        updated = []
        for r in pieces:
            if not rect_overlap(r, c[:4]):
                updated.append(r)
                continue
            x0,y0,x1,y1 = r
            a,b,d,e = max(x0,c[0]),max(y0,c[1]),min(x1,c[2]),min(y1,c[3])
            if x0<a: updated.append((x0,y0,a,y1))
            if d<x1: updated.append((d,y0,x1,y1))
            if y0<b: updated.append((a,y0,d,b))
            if e<y1: updated.append((a,e,d,y1))
        pieces = updated
    return pieces


def explicit_bay_regions(rect, footprints, blockers):
    """A scattered explicit bank is legal only if EVERY real FF footprint is legal.

    Its enclosing bbox may cross several cores. Preserve the holes in the
    reserved geometry, and charge fill against legal area only. An actual
    cell/core collision remains FAIL; generated repeater bays do not use this.
    """
    relevant = [c for c in blockers if rect_overlap(rect,c[:4])]
    hits = sorted({str(c[4]) if len(c)>4 else str(i) for f in footprints
                   for i,c in enumerate(relevant) if rect_overlap(f,c[:4])})
    return subtract_rectangles(rect,relevant),hits


def rect_inside(a, b, eps=1e-6):
    return a[0] >= b[0] - eps and a[1] >= b[1] - eps and a[2] <= b[2] + eps and a[3] <= b[3] + eps


# ------------------------------------------------------------------------------------------------------ track grid
class Grid:
    """per-layer gcell demand/capacity (numpy, die frame, row = y index)."""

    def __init__(self, P, pg_grid, tracks, lower_pg_frac, core_obs_top, islands_die, cores_die):
        import numpy as np
        self.np = np
        self.P = P
        self.nx, self.ny = int(math.ceil(P.W / G)), int(math.ceil(P.H / G))
        self.cap, self.dem = {}, {}
        for L in LOWER + ("M8", "M9"):
            pitch = P.layers[L]["pitch_um"]
            frac = IS.die_free_frac(P, L, pg_grid, tracks) if L in ("M8", "M9") else 1.0 - lower_pg_frac
            self.cap[L] = np.full((self.ny, self.nx), G / pitch * frac, dtype=np.float32)
            self.dem[L] = np.zeros((self.ny, self.nx), dtype=np.float32)
        top = lnum(core_obs_top)
        for r in cores_die:
            i0, j0, i1, j1 = self.idx(r)
            for L in LOWER:
                if lnum(L) <= top:
                    self.cap[L][j0:j1, i0:i1] = 0.0
        for r in islands_die:
            i0, j0, i1, j1 = self.idx(r)
            for L in LOWER:
                self.cap[L][j0:j1, i0:i1] = 0.0

    def idx(self, r):
        """gcells whose centre lies in rect r (at least one cell)."""
        x0, y0, x1, y1 = r
        i0 = max(0, min(self.nx - 1, int(round(x0 / G))))
        j0 = max(0, min(self.ny - 1, int(round(y0 / G))))
        i1 = max(i0 + 1, min(self.nx, int(round(x1 / G))))
        j1 = max(j0 + 1, min(self.ny, int(round(y1 / G))))
        return i0, j0, i1, j1

    def band(self, a, b, w):
        """gcell slice + across-axis cell count of the band of segment a->b, width w."""
        (x0, y0), (x1, y1) = a, b
        horiz = abs(y1 - y0) < 1e-9
        h = max(w, G) / 2
        if horiz:
            r = (min(x0, x1), y0 - h, max(x0, x1), y0 + h)
        else:
            r = (x0 - h, min(y0, y1), x0 + h, max(y0, y1))
        return self.idx(r), horiz

    def load(self, L, sl, horiz, bits):
        """per-cell add for `bits` spread over the valid (cap > 0) across cells; None if a section is fully blocked."""
        np = self.np
        i0, j0, i1, j1 = sl
        cap = self.cap[L][j0:j1, i0:i1]
        valid = cap > 0
        n = valid.sum(axis=0 if horiz else 1)
        if (n == 0).any():
            return None
        add = np.where(valid, bits / (np.expand_dims(n, 0) if horiz else np.expand_dims(n, 1)), 0.0)
        return add.astype(np.float32)

    def worst(self, L, sl, add):
        np = self.np
        i0, j0, i1, j1 = sl
        cap = self.cap[L][j0:j1, i0:i1]
        d = self.dem[L][j0:j1, i0:i1] + add
        with np.errstate(divide="ignore", invalid="ignore"):
            u = np.where(cap > 0, d / np.maximum(cap, 1e-9), np.where(d > 0, np.inf, 0.0))
        return float(u.max()) if u.size else 0.0

    def commit(self, L, sl, add):
        i0, j0, i1, j1 = sl
        self.dem[L][j0:j1, i0:i1] += add

    def use_report(self, limit, top=20):
        np = self.np
        out, worst = {}, []
        for L in self.cap:
            cap, dem = self.cap[L], self.dem[L]
            with np.errstate(divide="ignore", invalid="ignore"):
                u = np.where(cap > 0, dem / np.maximum(cap, 1e-9), np.where(dem > 0, np.inf, 0.0))
            used = dem > 0
            over = u > limit + 1e-6
            out[L] = dict(max_use=r3(float(u.max())) if np.isfinite(u.max()) else "inf",
                          gcells_used=int(used.sum()), gcells_over=int(over.sum()),
                          mean_use_where_used=r3(float(u[used & np.isfinite(u)].mean())) if used.any() else 0.0)
            if over.any():
                js, is_ = np.nonzero(over)
                vals = u[js, is_]
                order = np.argsort(-vals)[:top]
                worst += [dict(layer=L, gcell_um=[r3(is_[k] * G), r3(js[k] * G)],
                               use=(r3(vals[k]) if np.isfinite(vals[k]) else "inf")) for k in order]
        return out, worst


# ------------------------------------------------------------------------------------------------------ rest stops
def place_stops(route, iv, reach):
    """repeater stops along route (polyline) between its two registers so no gap > reach.
    iv(a, b) -> legal site intervals of segment a->b.  -> (stops [(t, xy)], fails [(t0, t1, xy)])."""
    segs, T = [], 0.0
    sites = []
    for a, b in zip(route, route[1:]):
        L = IS.seg_len(a, b)
        if L < 1e-9:
            continue
        for s0, s1 in iv(a, b):
            sites.append((T + s0, T + s1))
        segs.append((T, a, b, L))
        T += L
    sites = IS.union(sites)

    def xy(t):
        for T0, a, b, L in segs:
            if t <= T0 + L + 1e-9:
                return IS.point_at(a, b, max(0.0, t - T0))
        return tuple(route[-1])

    def legal_in(lo, hi, target):
        best = None
        for s0, s1 in sites:
            c0, c1 = max(lo, s0), min(hi, s1)
            if c1 < c0 - 1e-9:
                continue
            t = min(max(target, c0), c1)
            if best is None or abs(t - target) < abs(best - target):
                best = t
        return best
    stops, fails = [], []
    pos = 0.0
    while T - pos > reach + 1e-6:
        n = math.ceil((T - pos) / reach - 1e-9)
        target = pos + (T - pos) / n
        t = legal_in(pos + 1e-3, pos + reach, target)
        if t is None:
            t = pos + reach
            fails.append((pos, t, xy(t)))
        else:
            stops.append((t, xy(t)))
        pos = t
    return stops, fails, T


def station_sites(P, part, reg_die, groups, face_tol=1.0):
    """(bit-site group of the station register at reg_die, is_face).  A register on the partition face is the
    registered partition pin (boundary flop, partition logic): no bay.  Else the declared bit_sites group whose
    centroid is nearest (type frame), or None."""
    x0, y0, x1, y1 = P.rect(part)
    x, y = reg_die
    if min(abs(x - x0), abs(x - x1), abs(y - y0), abs(y - y1)) <= face_tol:
        return None, True
    if not groups:
        return None, False
    tx, ty = P.to_type(part, reg_die)
    best = None
    for gp in groups:
        if not gp:
            continue
        cx = sum(q[0] for q in gp) / len(gp)
        cy = sum(q[1] for q in gp) / len(gp)
        d = abs(cx - tx) + abs(cy - ty)
        if best is None or d < best[0]:
            best = (d, gp)
    return (best[1] if best and best[0] <= 120.0 else None), False


def fit_rect(r, box, blockers, horiz, step=2.16, slide=81.0, narrow=True):
    """translate a bay rect inside its partition, then slide it along the road (<= slide um) off hard cores /
    islands; returns the first clean position, else the in-box one (the gate then reports the overlap)."""
    w, h = r[2] - r[0], r[3] - r[1]
    x0 = min(max(r[0], box[0]), box[2] - w)
    y0 = min(max(r[1], box[1]), box[3] - h)
    base = (x0, y0, x0 + w, y0 + h)
    for k in range(int(slide / step) + 1):
        for sgn in ((1,) if k == 0 else (1, -1)):
            d = sgn * k * step
            q = (base[0] + d, base[1], base[2] + d, base[3]) if horiz else \
                (base[0], base[1] + d, base[2], base[3] + d)
            if rect_inside(q, box) and not any(rect_overlap(q, c[:4]) for c in blockers):
                return q
    # narrow channel (band wider than the gap between cores): clip the across-road width to the free interval
    # that holds the road centre, keep the cell area by lengthening along the road, then slide again
    if narrow:
        lo, hi = (base[1], base[3]) if horiz else (base[0], base[2])
        mid = (lo + hi) / 2
        a0, a1 = (box[1], box[3]) if horiz else (box[0], box[2])
        for c in blockers:
            s0, s1 = (base[0], base[2]) if horiz else (base[1], base[3])
            c_along = (c[0], c[2]) if horiz else (c[1], c[3])
            if c_along[1] <= s0 - slide or c_along[0] >= s1 + slide:
                continue
            c0, c1 = (c[1], c[3]) if horiz else (c[0], c[2])
            if c1 <= mid:
                a0 = max(a0, c1)
            elif c0 >= mid:
                a1 = min(a1, c0)
        nw = a1 - a0
        if nw >= ROW * 4 and nw < hi - lo:
            area = w * h
            depth = math.ceil(area / nw / ROW - 1e-9) * ROW
            if horiz:
                cx = (base[0] + base[2]) / 2
                q = (cx - depth / 2, a0, cx + depth / 2, a1)
            else:
                cy = (base[1] + base[3]) / 2
                q = (a0, cy - depth / 2, a1, cy + depth / 2)
            return fit_rect(q, box, blockers, horiz, step, slide, narrow=False)
    return base


def bay_rect(xy, horiz, band, area, row=ROW):
    """bay rect centred on xy: band width across the road x depth along it (rounded up to rows)."""
    w = max(band, 2 * G / 4)
    depth = max(row, math.ceil(area / w / row - 1e-9) * row)
    x, y = xy
    if horiz:              # road along x: band across = y
        return (x - depth / 2, y - w / 2, x + depth / 2, y + w / 2)
    return (x - w / 2, y - depth / 2, x + w / 2, y + depth / 2)


# ------------------------------------------------------------------------------------------------------ entry pins
def entry_pin_limit(P, pg_grid, tracks, lower_pg_frac, margin=0.6, stagger=0.5, layers=("M7", "M8", "M9")):
    free = {}
    for L in layers:
        pitch = P.layers[L]["pitch_um"]
        frac = IS.die_free_frac(P, L, pg_grid, tracks) if L in ("M8", "M9") else 1.0 - lower_pg_frac
        free[L] = G / pitch * frac
    lim = int(math.floor(margin * stagger * min(free.values())))
    return lim, {k: r3(v) for k, v in free.items()}, dict(margin=margin, stagger=stagger,
                                                           binding=min(free, key=free.get))


def ring_cells(cx, cy, ring):
    """Exact old lexicographic ring order in O(r), without scanning its O(r^2) square."""
    if ring == 0:
        yield cx, cy
        return
    for j in range(-ring, ring + 1):
        yield cx - ring, cy + j
    for i in range(-ring + 1, ring):
        yield cx + i, cy - ring
        yield cx + i, cy + ring
    for j in range(-ring, ring + 1):
        yield cx + ring, cy + j


def place_pins(occ, bay, n, limit, P=None, bounds=None, reach_um=None):
    """n M7 entry pins (down + up via per bit at a repeater/station drop) in the gcells nearest the bay, filling each
    gcell to <= limit across all bays (occ = shared per-gcell count).  Pins sit on every other M7 track (0.128) and
    every other M8 row (0.16), staggered."""
    cx, cy = int(((bay[0] + bay[2]) / 2) // G), int(((bay[1] + bay[3]) / 2) // G)
    if limit <= 0:
        return []
    out, ring = [], 0
    max_ring = min(400, int(math.ceil(reach_um / G)) + 2) if reach_um is not None else 400
    while len(out) < n and ring < max_ring:
        for gx, gy in ring_cells(cx, cy, ring):
            if gx < 0 or gy < 0 or (P and (gx * G > P.W or gy * G > P.H)):
                continue
            while occ[(gx, gy)] < limit and len(out) < n:
                k = occ[(gx, gy)]
                col, row = k % 84, k // 84
                xy = (r3(gx * G + 0.064 + col * 0.128),
                      r3(gy * G + 0.08 + row * 0.32 + (0.16 if col % 2 else 0.0)))
                # Cursor includes unusable edge slots: never recycle a physical
                # track or spill a bay drop into a different partition.
                occ[(gx, gy)] += 1
                if bounds is not None and not (bounds[0] <= xy[0] <= bounds[2] and bounds[1] <= xy[1] <= bounds[3]):
                    continue
                dist = max(bay[0]-xy[0], 0, xy[0]-bay[2]) + max(bay[1]-xy[1], 0, xy[1]-bay[3])
                if reach_um is not None and dist > reach_um + 1e-6:
                    continue
                out.append(xy)
            if len(out) >= n:
                break
        ring += 1
    return out


def spread_pins(bay, n, limit, start=0):
    """n entry pins beside a bay rect (on its +x side for a vertical road, +y for horizontal): staggered M7 tracks
    (2 x 0.064) x M8 rows (2 x 0.08), <= limit per gcell, as many gcells as needed."""
    x0, y0, x1, y1 = bay
    per = max(1, limit)
    cols = max(1, int(G / 0.128))
    pins = []
    for k in range(n):
        g, q = divmod(k, per)
        cx, cy = q % cols, q // cols
        gx = x1 + 0.5 + (g % 4) * G
        gy = y0 + (g // 4) * G
        pins.append((r3(gx + cx * 0.128), r3(gy + cy * 0.16 + (0.08 if cx % 2 else 0.0))))
    return pins


# ------------------------------------------------------------------------------------------------------ clock gates
def road_clock_conflicts(roads, clock_rects, spacing, bucket_um=500.0):
    """Count intersecting road/clock pairs with a spatial index; geometry/counts unchanged.

    The prior all-pairs loop costs billions of comparisons on HBM. Index the
    spacing-expanded clock rectangles, deduplicate candidates per road, and
    retain the exact rect_overlap predicate (including touching-edge policy).
    """
    buckets = defaultdict(list)
    rects = []
    def cells(r):
        for x in range(math.floor(r[0] / bucket_um), math.floor(r[2] / bucket_um) + 1):
            for y in range(math.floor(r[1] / bucket_um), math.floor(r[3] / bucket_um) + 1):
                yield x, y
    for _, layer, x0, y0, x1, y1, *_ in clock_rects:
        if layer not in spacing:
            continue
        d = spacing[layer]
        r = (x0 - d, y0 - d, x1 + d, y1 + d)
        idx = len(rects)
        rects.append(r)
        for x, y in cells(r):
            buckets[(layer, x, y)].append(idx)
    hits = 0
    for layer, road in roads:
        candidates = set()
        for x, y in cells(road):
            candidates.update(buckets.get((layer, x, y), ()))
        hits += sum(rect_overlap(road, rects[i]) for i in candidates)
    return hits


def clock_shield(P, pg_grid, clock_rects, ndr_space=0.08, roads=(), sample=40):
    """every clock rect on M8/M9: PG stripe both sides, gap < ndr_space + w_min + s_min (no signal track fits)."""
    import bisect
    stripes = defaultdict(list)
    for net, L, x0, y0, x1, y1 in __import__("die_infra").pg_rects(P, pg_grid):
        horiz = P.layers[L]["dir"] == "H"
        stripes[L].append((y0, y1) if horiz else (x0, x1))
    for L in stripes:
        stripes[L].sort()
    lo_idx = {L: [s[0] for s in v] for L, v in stripes.items()}
    fit = {L: ndr_space + 0.04 + 0.04 for L in ("M8", "M9")}
    n = ok = short = 0
    sides_open = 0
    worst = []
    by_cls = defaultdict(lambda: [0, 0])
    for net, L, x0, y0, x1, y1, _w in clock_rects:
        if L not in ("M8", "M9"):
            continue
        n += 1
        horiz = P.layers[L]["dir"] == "H"
        c0, c1 = (y0, y1) if horiz else (x0, x1)
        st, lo = stripes.get(L, []), lo_idx.get(L, [])
        i = bisect.bisect_left(lo, c0)
        below = [s for s in st[max(0, i - 2):i + 1] if s[1] <= c0 + 1e-9]
        above = [s for s in st[max(0, i - 1):i + 3] if s[0] >= c1 - 1e-9]
        g_lo = c0 - max(s[1] for s in below) if below else float("inf")
        g_hi = min(s[0] for s in above) - c1 if above else float("inf")
        if any(s[0] < c1 and s[1] > c0 for s in st[max(0, i - 2):i + 2]):
            short += 1
        good = g_lo < fit[L] and g_hi < fit[L]
        cls = "strap" if net.startswith("ck_mesh") else "segment"
        by_cls[cls][0] += 1
        if good:
            ok += 1
            by_cls[cls][1] += 1
        else:
            sides_open += (g_lo >= fit[L]) + (g_hi >= fit[L])
            if len(worst) < sample:
                worst.append(dict(net=net, layer=L, rect_um=[r3(v) for v in (x0, y0, x1, y1)],
                                  gap_lo_um=r3(g_lo) if math.isfinite(g_lo) else None,
                                  gap_hi_um=r3(g_hi) if math.isfinite(g_hi) else None))
    road_hits = road_clock_conflicts(roads, clock_rects, fit)
    verdict = "PASS" if n and ok == n and not road_hits and not short else ("NOT RUN" if not n else "FAIL")
    return dict(verdict=verdict, clock_rects=n, shielded=ok, unshielded=n - ok, open_sides=sides_open,
                pg_overlaps=short, road_band_conflicts=road_hits, fit_gap_um=fit,
                by_class={k: dict(rects=v[0], shielded=v[1]) for k, v in by_cls.items()}, examples=worst)


def tree_balance(M, stub_tol=20.0, leg_tol=1.0):
    fam = defaultdict(list)
    for e in M.get("htree", []):
        fam[(e["level"], round(e["a"][0], 2), round(e["a"][1], 2))].append(float(e.get("len_um", 0.0)))
    bad = [dict(level=k[0], parent_um=[k[1], k[2]], legs_um=[r3(v) for v in ls], mismatch_um=r3(max(ls) - min(ls)))
           for k, ls in fam.items() if len(ls) > 1 and max(ls) - min(ls) > leg_tol]
    bad.sort(key=lambda d: -d["mismatch_um"])
    cls = defaultdict(list)
    for t in M.get("taps", []):
        cls[(t["part"].split("_")[0], t.get("tap"))].append(float(t.get("stub_um", 0.0)))
    stub_bad = [dict(cls=f"{k[0]}:{k[1]}", n=len(v), stub_min_um=r3(min(v)), stub_max_um=r3(max(v)))
                for k, v in cls.items() if max(v) - min(v) > stub_tol]
    stub_bad.sort(key=lambda d: -(d["stub_max_um"] - d["stub_min_um"]))
    v = "PASS" if not bad and not stub_bad else "FAIL"
    return dict(verdict=v, families=len(fam), unequal_families=len(bad), worst_families=bad[:20],
                tap_classes=len(cls), unequal_tap_classes=len(stub_bad), worst_tap_classes=stub_bad[:20],
                leg_tol_um=leg_tol, stub_tol_um=stub_tol,
                note="tap load = stub length proxy (mesh.json carries no per-tap sink cap); equal sinks per tap class "
                     "is the density-tap rule of the plan")


# ------------------------------------------------------------------------------------------------------ clock model
# 12.9d plan-level analytic core insertion model, calibrated ONCE (not per run) on the measured QC SU trials
# (QC-SU-LAT results/qc_su_lat/trials_1026.json @ claude/qc-su-lat-1026 ad22ae2b28, variant B = structured BUFx16f
# trunks SEG 110 um, GRT RC): insertion_TT = K_PS_PER_UM x L_max, L_max = entry -> farthest core corner (Manhattan);
# routed RCX = RCX_FACTOR x GRT (trial basis note: vmr_s6kc 386.5 routed vs 409.9 GRT).  FF = FF_RATIO x TT
# (same trials, mean FF/TT).  Calibration points (L_max from the S-face centre pin of the trial kits):
CAL_POINTS = [("qfd_dv_s8x_vmr", 406.08, 341.8, 271.8), ("qfd_dv_s8x_prog", 436.32, 419.4, 337.1),
              ("qfd_dv_s8x_btab", 436.32, 384.9, 308.1)]
K_PS_PER_UM = sum(t for _, _, t, _ in CAL_POINTS) / sum(L for _, L, _, _ in CAL_POINTS)
FF_RATIO = sum(f / t for _, _, t, f in CAL_POINTS) / len(CAL_POINTS)
RCX_FACTOR = 386.5 / 409.9
CAL_ERR = [round(K_PS_PER_UM * L - t, 1) for _, L, t, _ in CAL_POINTS]
CAL_RMS_PS = round(math.sqrt(sum(e * e for e in CAL_ERR) / len(CAL_ERR)), 1)


# 12.9d die related-pair skew per clock region, CPPR at the last common tree node (= the region root for same-mesh
# pairs, 12.4b), calibrated ONCE on the measured QC regional mesh claude-infra-qc-1026/b3 (mesh_{TT,FF}.json stub-input
# late/early of 7121 taps, 4 regions; mesh.json tree geometry):
#   pair = K_PITCH x mean mesh pitch (nominal intra-region spread)  +  OCV x K_TREE x tree path below the region root
#          +  core window (12.8b: +-20 ps around the common latency, or the predicted core residual if larger)
SKEW_CAL = dict(source="QC b3 regional mesh (claude-infra-qc-1026/b3, plan ec0cfafd), measured stub-input arrivals",
                K_PITCH=dict(TT=round(103.15 / 449.08, 4), FF=round(105.48 / 449.08, 4)),   # spread / mean pitch
                OCV=dict(TT=round(96.5 / 7423.0, 5), FF=round(86.0 / 6179.0, 5)),          # (late-early) / late
                K_TREE=dict(TT=round(7423.0 / 28841.8, 5), FF=round(6179.0 / 28841.8, 5)),  # insertion / path um
                check=dict(target="mesh-only related pair, region-root CPPR (EARLY-TAP t2 05:41): 154.0 TT / 142.8 FF",
                           predicted=dict(TT=160.5, FF=156.6), error_ps=dict(TT=6.5, FF=13.8)))


def pair_skew_pred(M, corner, core_term=0.0):
    """per-region predicted related-pair skew from the clock plan geometry (mesh pitch, H-tree levels)."""
    meta = M["meta"]
    px, py = meta["pitch_um"]
    depth = int(meta.get("regions_depth", 0) or 0)
    lv = defaultdict(float)
    for e in M.get("htree", []):
        lv[e["level"]] = max(lv[e["level"]], float(e["len_um"]))
    total = sum(lv.values()) + float(meta.get("trunk_um", 0.0))
    above = sum(v for k, v in lv.items() if k <= depth) + float(meta.get("trunk_um", 0.0))
    nominal = SKEW_CAL["K_PITCH"][corner] * (px + py) / 2
    derate = SKEW_CAL["OCV"][corner] * SKEW_CAL["K_TREE"][corner] * (total - above)
    return dict(nominal_ps=round(nominal, 1), derate_ps=round(derate, 1), pair_ps=round(nominal + derate, 1),
                core_residual_ps=round(core_term, 1), pair_with_core_ps=round(nominal + derate + core_term, 1), path_um=round(total, 1),
                below_root_um=round(total - above, 1), regions=len(meta.get("regions") or [1]))


def core_insertion(far_um):
    tt = RCX_FACTOR * K_PS_PER_UM * far_um
    return round(tt, 1), round(tt * FF_RATIO, 1)


# ------------------------------------------------------------------------------------------------------ IR
def static_ir(files):
    if not files:
        return dict(verdict="NOT RUN", note="no PDNSim region result (--ir); PG lane = INFRA-FIRST-R2")
    rows, verdict = [], "PASS"
    for f in files:
        r = json.loads(Path(f).read_text())
        basis = r.get("power_basis")
        v = r.get("ir_verdict", "FAIL")
        row = dict(file=str(f), window=r.get("window"), worst_mv=r.get("worst_ir_drop_mv"),
                   budget_mv=r.get("ir_budget_mv"), regions_mv=r.get("psm_regions_mv"), power_w=r.get("power_w"),
                   power_basis=basis, verdict=v)
        if v != "PASS":
            verdict = "FAIL"
        elif basis != "worst_case" and verdict == "PASS":
            verdict = "NOT QUALIFIED"
        rows.append(row)
    return dict(verdict=verdict, regions=rows,
                note="NOT QUALIFIED = every region PASS but a result does not declare power_basis worst_case (12.7a)")


# ------------------------------------------------------------------------------------------------------ main run
def run(P, out, mesh_dir=None, tracks_file=None, pg_file=None, ir_files=(), entries=None, sites_json=None,
        reach=None, detour=405.0, core_obs_top="M5", lower_pg_frac=0.25, fill_max=0.6, bay_fill=0.5,
        track_max=0.6, core_reach_um=200.0, entry_tol=0.5, core_tol_ps=20.0, skew_gate_ps=80.0, render=True, log=print):
    reach = float(reach or P.reach)
    out = Path(out)
    (out / "slices").mkdir(parents=True, exist_ok=True)
    pg_grid = json.loads(Path(pg_file).read_text())["grid"] if pg_file else P.die.get("pg", {}).get("grid", [])
    tracks = json.loads(Path(tracks_file).read_text()).get("tracks_taken") if tracks_file else None
    common = float(P.clock.get("common_latency_ps", P.clock.get("insertion_ps", 250)))
    plan_sha = sha256_file(P.path) if P.path else None

    # ---- INFRA-FIRST-R2 outputs (islands, cores, stack limit): read-only
    if sites_json:
        SR = json.loads(Path(sites_json).read_text())
    else:
        log("infra_sites.run ...")
        try:
            SR = IS.run(P, mesh_dir=mesh_dir, tracks_file=tracks_file, pg_file=pg_file, reach=reach, detour=detour,
                        core_obs_top=core_obs_top, lower_pg_frac=lower_pg_frac)
        except Exception as ex:          # noqa: BLE001 -- recorded; the islands gate is then NOT RUN
            SR = dict(error=f"{type(ex).__name__}: {ex}")
    islands = SR.get("islands", {})
    sites_gate = dict(verdict=("NOT RUN" if "error" in SR else
                               ("PASS" if (SR.get("summary") or {}).get("verdict") == "PASS" else "FAIL")),
                      source="infra_sites.run (INFRA-FIRST-R2)", error=SR.get("error"),
                      checks=(SR.get("summary") or {}).get("checks"), islands=len(islands))

    # ---- hard-core clock entries (12.8a) + their islands
    core_types = {}
    for tn, t in P.types.items():
        for h in t.get("hard_cores", []):
            core_types.setdefault(h["module"], dict(outline_um=h["outline_um"], uses=[]))["uses"].append((tn, h))
    entry = {}
    for mod, c in core_types.items():
        h0 = c["uses"][0][1]
        xy, src = core_entry(h0, entries)
        entry[mod] = dict(xy=[r3(xy[0]), r3(xy[1])], source=src, island=entry_island(xy))

    # ---- die-frame blockers
    cores_die, isl_die = [], []
    blk = {}
    for part in P.parts:
        b = part_blockers(P, part, islands)
        blk[part] = b
        for r in b:
            (isl_die if r[4] == "island" else cores_die).append(r[:4])
    # entry islands inside cores block nothing extra for roads (cores already block <= core_obs_top)
    grid = Grid(P, pg_grid, tracks, lower_pg_frac, core_obs_top, isl_die, cores_die)

    # ---- census
    paths = census(P)
    log(f"census: {len(paths)} paths")

    # ---- roads + rest stops
    segs_all = []                         # (bits, path, leg index, a, b, band, layers, part)
    bays_die = []                         # dict(part, xy, kind, bits, horiz, band, path, rect)
    gap_fail, in_core = [], []
    gap_max = (0.0, None)
    route_cache = {}
    for pth in paths:
        for li, lg in enumerate(pth["legs"]):
            part = lg["part"]
            box = P.rect(part)
            blockers = [r for r in blk[part]]
            cb = [IS.rect_pts(P, part, c[:4]) + tuple(c[4:]) for c in IS.core_bays(P.ptype(part), None)]
            iv = IS.make_site_iv(box, blockers, cb)
            band = lg["band_um"] or max(G, pth["bits"] * 0.064 * 2)
            pts = lg["pts"]
            for k, (a, b) in enumerate(zip(pts, pts[1:])):
                # station register at a (k > 0) -> station bay
                if 0 < k:
                    grp, face = station_sites(P, part, a, lg["bit_sites"])
                    if not face:          # a face register is the partition's registered pin (rest stop, no bay)
                        bays_die.append(dict(part=part, xy=a, kind="station", bits=pth["bits"], band=band,
                                             horiz=abs(b[1] - a[1]) < abs(b[0] - a[0]), path=pth["id"],
                                             sites=grp))
                if IS.seg_len(a, b) < 1e-6:
                    continue
                # replicated partitions: the route only depends on the partition-relative geometry -> cache it per
                # (type, orient, relative endpoints) and translate (route_leg is INFRA-FIRST-R2's, read-only)
                ck = (P.parts[part]["type"], P.parts[part].get("orient", "R0"),
                      round(a[0] - box[0], 3), round(a[1] - box[1], 3), round(b[0] - box[0], 3),
                      round(b[1] - box[1], 3), round(box[2] - box[0], 3), round(box[3] - box[1], 3))
                Rc = route_cache.get(ck)
                if Rc is None:
                    R = IS.route_leg(a, b, box, blockers, cb, reach, detour)
                    route_cache[ck] = [(q[0] - box[0], q[1] - box[1]) for q in R["route"]]
                else:
                    R = dict(route=[(q[0] + box[0], q[1] + box[1]) for q in Rc])
                route = R["route"]
                stops, fails, T = place_stops(route, iv, reach)
                prev = 0.0
                for t, xy in stops:
                    gap_max = max(gap_max, (t - prev, pth["id"]))
                    prev = t
                    sa = [q for q in zip(route, route[1:])]
                    horiz = True
                    acc = 0.0
                    for p0, p1 in sa:
                        L = IS.seg_len(p0, p1)
                        if acc + L >= t - 1e-9 and L > 1e-9:
                            horiz = abs(p1[1] - p0[1]) < 1e-9
                            break
                        acc += L
                    bays_die.append(dict(part=part, xy=xy, kind="repeater", bits=pth["bits"], band=band,
                                         horiz=horiz, path=pth["id"], sites=None))
                gap_max = max(gap_max, (T - prev, pth["id"]))
                for t0, t1, xy in fails:
                    core = next((c for c in blockers if c[0] <= xy[0] <= c[2] and c[1] <= xy[1] <= c[3]), None)
                    row = dict(path=pth["id"], part=part, type=P.parts[part]["type"], at_um=[r3(xy[0]), r3(xy[1])],
                               bits=pth["bits"], blocker=(core[4] if core else None),
                               module=(core[5] if core else None))
                    if core and core[4] != "island":
                        h = next(h for h in P.ptype(part).get("hard_cores", []) if h["inst"] == core[4])
                        tp = P.to_type(part, xy)
                        cl = type_to_core_pt(h, tp)
                        row["proposed_in_core_bay"] = dict(core_local_um=[r3(cl[0] - band / 2), r3(cl[1] - 5),
                                                                          r3(cl[0] + band / 2), r3(cl[1] + 5)],
                                                           owner=f"{h['module']}", layer="M6/M7")
                        in_core.append(row)
                    gap_fail.append(row)
                for p0, p1 in zip(route, route[1:]):
                    if IS.seg_len(p0, p1) > 1e-6:
                        segs_all.append((pth["bits"], pth["id"], li, p0, p1, band, lg["layers"], part))
    log(f"roads: {len(segs_all)} segments, {len(bays_die)} rest stops, {len(gap_fail)} reach gaps")

    # ---- layer assignment (greedy by bits)
    roads = []
    m89_segs = []
    blocked = []
    for bits, pid, li, a, b, band, decl, part in sorted(segs_all, key=lambda s: -s[0]):
        sl, horiz = grid.band(a, b, band)
        d = "H" if horiz else "V"
        top = lnum(P.type_top_layer(P.parts[part]["type"]))
        cands = [L for L in decl if L in DIRS[d] and lnum(L) <= 7]
        cands += [L for L in DIRS[d] if lnum(L) <= min(7, top) and L not in cands and lnum(L) >= 4]
        if ":istn" not in pid:           # 12.1a: partition-internal paths route <= M7; only die-top nets use M8/M9
            cands += [L for L in DIRS[d] if lnum(L) >= 8]
        best = None
        for L in cands:
            add = grid.load(L, sl, horiz, bits)
            if add is None:
                continue
            u = grid.worst(L, sl, add)
            if best is None or (u <= track_max and best[1] > track_max) or (u < best[1] and best[1] > track_max):
                best = (L, u, add)
            if u <= track_max:
                break
        if best is None:
            blocked.append(dict(path=pid, part=part, a=[r3(v) for v in a], b=[r3(v) for v in b], dir=d))
            continue
        L, u, add = best
        grid.commit(L, sl, add)
        roads.append(dict(path=pid, part=part, layer=L, bits=bits, a=[r3(v) for v in a], b=[r3(v) for v in b],
                          band_um=r3(band), leg=li))
        if lnum(L) >= 8:
            m89_segs.append(roads[-1])
    use, worst_cells = grid.use_report(track_max)
    log(f"layers: {len(roads)} roads, {len(m89_segs)} on leftover M8/M9, {len(blocked)} blocked")

    # ---- bays: rects, legality, fill
    bays = []
    bay_fail = []
    for k, bd in enumerate(bays_die):
        cell = A_FLOP if bd["kind"] == "station" else A_REP
        demand = bd["bits"] * cell
        if bd["sites"]:
            xs = [s[0] for s in bd["sites"]]
            ys = [s[1] for s in bd["sites"]]
            rt = (min(xs), min(ys), max(xs) + 1.404, max(ys) + ROW)
            pts = [P.to_die(bd["part"], c) for c in ((rt[0], rt[1]), (rt[2], rt[3]))]
            r = (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))
        else:
            r = fit_rect(bay_rect(bd["xy"], bd["horiz"], bd["band"], demand / bay_fill), P.rect(bd["part"]),
                         blk[bd["part"]], bd["horiz"])
        regions = [r]
        actual_hits = None
        if bd["sites"]:
            footprints = []
            for x,y in bd["sites"]:
                pts = [P.to_die(bd["part"],c) for c in ((x,y),(x+1.404,y+ROW))]
                footprints.append((min(p[0] for p in pts),min(p[1] for p in pts),
                                   max(p[0] for p in pts),max(p[1] for p in pts)))
            regions,actual_hits = explicit_bay_regions(r,footprints,blk[bd["part"]])
        area = sum((q[2]-q[0])*(q[3]-q[1]) for q in regions)
        fill = demand / area if area > 0 else float("inf")
        bad = []
        if fill > fill_max + 1e-6:
            bad.append("fill")
        if not rect_inside(r, P.rect(bd["part"])):
            bad.append("outside_partition")
        if actual_hits is not None:
            bad.extend(f"actual_ff_overlaps:{name}" for name in actual_hits)
        else:
            for c in blk[bd["part"]]:
                if rect_overlap(r, c[:4]):
                    bad.append(f"overlaps:{c[4]}")
        row = dict(part=bd["part"], type=P.parts[bd["part"]]["type"], kind=bd["kind"], bits=bd["bits"],
                   rect_um=[r3(v) for v in r], xy_um=[r3(v) for v in bd["xy"]], cell_area_um2=r3(demand),
                   fill=r3(fill), path=bd["path"], horiz=bd["horiz"], band=bd["band"], issues=bad,
                   regions_um=[[r3(v) for v in q] for q in regions], legal_area_um2=r3(area),
                   explicit_sites=bool(bd["sites"]))
        bays.append(row)
        if bad:
            bay_fail.append(row)
    # partition fill: declared est. std-cell fill + bays
    soft = {}
    for part in P.parts:
        x0, y0, x1, y1 = P.rect(part)
        a = (x1 - x0) * (y1 - y0) - sum((c[2] - c[0]) * (c[3] - c[1]) for c in blk[part])
        soft[part] = max(a, 1e-9)
    bay_area = defaultdict(float)
    for b in bays:
        bay_area[b["part"]] += b["cell_area_um2"]
    part_fill_fail = []
    for part in P.parts:
        base = IS.note_fill(P.ptype(part)) or 0.0
        f = base + bay_area[part] / soft[part]
        if f > fill_max + 1e-6:
            part_fill_fail.append(dict(part=part, base_fill=base, bay_fill=r3(bay_area[part] / soft[part]),
                                       fill=r3(f)))

    # ---- entry pins
    lim, free_t, deriv = entry_pin_limit(P, pg_grid, tracks, lower_pg_frac)
    pins = []
    occ = defaultdict(int)
    near = defaultdict(list)
    for k, b in enumerate(bays):
        b["_k"] = k
        near[b["path"]].append(b)
    pmap = {p["id"]: p for p in paths}

    def _same(u, v):
        return abs(u[0] - v[0]) + abs(u[1] - v[1]) < 1e-3
    n_bound = 0
    entry_missing = []
    drops = defaultdict(int)             # (part, path) -> drop counter: entry pin names stay unique per partition
    for sgm in m89_segs:
        lg = (pmap[sgm["path"]]["legs"][sgm["leg"]] if sgm.get("leg") is not None and sgm["path"] in pmap
              and pmap[sgm["path"]]["kind"] != "internal" else None)
        for end, other in ((sgm["a"], sgm["b"]), (sgm["b"], sgm["a"])):
            cand = [b for b in near[sgm["path"]] if b["part"] == sgm["part"]]
            if not cand:
                entry_missing.append(dict(part=sgm["part"], path=sgm["path"], requested=2*sgm["bits"],
                                          placed=0, reason="no bay for die-to-partition drop"))
                continue
            bb = min(cand, key=lambda b: abs(b["xy_um"][0] - end[0]) + abs(b["xy_um"][1] - end[1]))
            # pin pairs per bit: even = down (die M8/M9 -> M7 -> partition, dir in), odd = up (dir out).  A segment
            # whose OTHER end is its leg's face-in point carries the slot input port: its down pins here ARE the
            # <slot>_i bits (the port moves from the face to this on-ramp); face-out -> the up pins are <slot>_o.
            bind = None
            if lg and lg.get("slot"):
                if _same(other, lg["pts"][0]):
                    bind = (lg["slot"] + "_i", 0)
                elif _same(other, lg["pts"][-1]):
                    bind = (lg["slot"] + "_o", 1)
            dk = drops[(sgm["part"], sgm["path"])]
            drops[(sgm["part"], sgm["path"])] += 1
            placed = place_pins(occ, bb["rect_um"], 2 * sgm["bits"], lim, P,
                                bounds=P.rect(sgm["part"]), reach_um=reach)
            if len(placed) != 2 * sgm["bits"]:
                entry_missing.append(dict(part=sgm["part"], path=sgm["path"], requested=2*sgm["bits"],
                                          placed=len(placed), reason="entry capacity within partition/reach exhausted"))
            for i, xy in enumerate(placed):
                pin = f"{bind[0]}[{i // 2}]" if bind and i % 2 == bind[1] else None
                n_bound += pin is not None
                pins.append(dict(part=sgm["part"], path=sgm["path"], bit=i, layer="M7", xy_um=list(xy),
                                 die_layer=sgm["layer"], bay=bb["_k"], dir="in" if i % 2 == 0 else "out",
                                 pair=i // 2, pin=pin, bay_kind=bb["kind"], drop=dk))
    for b in bays:
        b.pop("_k", None)
    per_cell = defaultdict(int)
    for p in pins:
        per_cell[(int(p["xy_um"][0] // G), int(p["xy_um"][1] // G))] += 1
    pin_max = max(per_cell.values()) if per_cell else 0

    # ---- lot fit + 12.8 core gates
    lot_fail, entry_fail, restructure = [], [], []
    early = defaultdict(int)
    early_rows = []
    for tn, t in P.types.items():
        W, H = t["outline_um"]
        cs = IS.type_cores(t)
        isl = islands.get(tn)
        for i, c in enumerate(cs):
            if not rect_inside(c[:4], (0, 0, W, H)):
                lot_fail.append(dict(type=tn, inst=c[4], issue="core outside outline"))
            for d in cs[i + 1:]:
                if rect_overlap(c[:4], d[:4]):
                    lot_fail.append(dict(type=tn, inst=c[4], issue=f"overlaps core {d[4]}"))
            if isl and rect_overlap(c[:4], isl["rect_um"]):
                lot_fail.append(dict(type=tn, inst=c[4], issue="partition island overlaps core"))
        for h in t.get("hard_cores", []):
            e = entry[h["module"]]
            if not rect_inside(e["island"], (0, 0) + tuple(h["outline_um"])):
                lot_fail.append(dict(type=tn, inst=h["inst"], issue="entry island outside core"))
            checked = core_clock_entry_check(P, h, (t.get("clock") or {}).get("taps", []), e["xy"], entry_tol)
            if checked["verdict"] != "PASS":
                entry_fail.append(dict(type=tn, **checked))
        for tp in (t.get("clock") or {}).get("taps", []):
            ins = float(tp.get("insertion_ps", common))
            if abs(ins - common) > 1e-6:
                early[tp["kind"]] += 1
                if len(early_rows) < 30:
                    early_rows.append(dict(type=tn, tap=tp["name"], kind=tp["kind"], insertion_ps=ins,
                                           offset_ps=r3(ins - common)))
    for mod, c in core_types.items():
        w, h = c["outline_um"]
        x, y = entry[mod]["xy"]
        far = max(abs(cx - x) + abs(cy - y) for cx in (0, w) for cy in (0, h))
        if far > core_reach_um:
            sub = restructure_islands(w, h, core_reach_um)
            entry[mod]["in_core_islands"] = sub
            restructure.append(dict(module=mod, outline_um=c["outline_um"], entry_um=entry[mod]["xy"],
                                    farthest_corner_um=r3(far), uses=len(c["uses"]), lane=IS.lane_for(P.name),
                                    fix="internal H-tree from the centre entry with in-core islands at the leaf "
                                        "centres below (12.8b/d1); split the core only as a last resort",
                                    in_core_islands=sub))
    restructure.sort(key=lambda d: -d["farthest_corner_um"])
    ins_rows, ins_fail = [], []
    for mod, c in core_types.items():
        w, h = c["outline_um"]
        x, y = entry[mod]["xy"]
        far = max(abs(cx - x) + abs(cy - y) for cx in (0, w) for cy in (0, h))
        tt, ff = core_insertion(far)
        row = dict(module=mod, entry_um=entry[mod]["xy"], farthest_um=r3(far), pred_TT_ps=tt, pred_FF_ps=ff,
                   target_TT_ps=common, tol_ps=core_tol_ps)
        ins_rows.append(row)
        if abs(tt - common) > core_tol_ps + 1e-6 and tt > common:
            ins_fail.append(row)
    ins_fail.sort(key=lambda d: -d["pred_TT_ps"])

    # ---- clock shielding, tree balance (mesh dir)
    if mesh_dir:
        import die_infra as DI
        guide = Path(mesh_dir) / "route_TT.guide"
        M, crects = DI.clock_rects(mesh_dir, str(guide) if guide.exists() else None)
        ndr = DI.NDR[M["meta"].get("ndr", "4w")]
        road_rects = []
        for rd in m89_segs:
            (x0, y0), (x1, y1) = rd["a"], rd["b"]
            h2 = rd["band_um"] / 2
            road_rects.append((rd["layer"], (min(x0, x1) - h2 * (x0 == x1), min(y0, y1) - h2 * (y0 == y1),
                                             max(x0, x1) + h2 * (x0 == x1), max(y0, y1) + h2 * (y0 == y1))))
        shield = clock_shield(P, pg_grid, crects, ndr_space=ndr[1], roads=road_rects)
        shield["mesh"] = str(mesh_dir)
        bal = tree_balance(M)
        mesh_early = [t for t in M.get("taps", []) if abs(float(t.get("early_ps") or 0.0)) > 1e-9]
    else:
        shield = dict(verdict="NOT RUN", note="no --mesh")
        bal = dict(verdict="NOT RUN", note="no --mesh")
        mesh_early = []
    # ---- declared islands (die frame): core-centre entries + in-core leaves + partition islands + PHY strips
    phy = phy_entries(P)
    isl_decl, centres, glue_parts, macros_die = [], [], [], []
    for part in P.parts:
        tn = P.parts[part]["type"]
        t = P.types[tn]
        if islands.get(tn):
            isl_decl.append(IS.rect_pts(P, part, islands[tn]["rect_um"]))
        if t.get("hard_cores"):
            glue_parts.append(P.rect(part))
        for h in t.get("hard_cores", []):
            e = entry[h["module"]]
            r = IS.rect_pts(P, part, core_to_type(h, e["island"]))
            isl_decl.append(r)
            centres.append(((r[0] + r[2]) / 2, (r[1] + r[3]) / 2))
            for q in (e.get("in_core_islands") or {}).get("islands", []):
                isl_decl.append(IS.rect_pts(P, part, core_to_type(h, q["rect_um"])))
            macros_die.append(IS.rect_pts(P, part, core_to_type(h, (0, 0) + tuple(h["outline_um"]))))
        if tn in phy and phy[tn].get("island"):
            isl_decl.append(IS.rect_pts(P, part, phy[tn]["island"]))
    n_core_macros = len(macros_die)
    for io in P.die.get("io") or []:
        if io.get("kind") in ("phy_macro", "phy", "serdes") and io.get("rect_um"):
            macros_die.append(tuple(io["rect_um"]))
    lattice = core_lattice(centres) if centres else {}
    no_leaf = [a for a, v in lattice.items() if v.get("pitch_um") and not v.get("leaf_pitch_um")]
    off_lat = [a for a, v in lattice.items() if v.get("leaf_pitch_um")
               and abs(v["leaf_pitch_um"] / 8.64 - round(v["leaf_pitch_um"] / 8.64)) > 1e-3]
    mesh_mult = {}
    if mesh_dir and lattice:
        for ax, key in (("x", "xs"), ("y", "ys")):
            vs = sorted(M.get(key) or [])
            p = lattice.get(ax, {}).get("leaf_pitch_um")
            if len(vs) > 1 and p:
                g = [b - a for a, b in zip(vs, vs[1:])]
                mesh_mult[ax] = dict(mesh_pitch_um=[r3(min(g)), r3(max(g))],
                                     multiple_of_leaf_pitch=all(abs(v / p - round(v / p)) < 1e-3 for v in g))
    tree_comm = dict(
        verdict=("NOT RUN" if not centres else
                 "FAIL" if no_leaf or off_lat or any(not v["multiple_of_leaf_pitch"] for v in mesh_mult.values())
                 else "PASS"),
        core_lattice=lattice, mesh_vs_core=mesh_mult or None, phy_entries=len(phy),
        rule="die H-tree leaf / mesh-driver pitch = the core-array repeat (leaf_pitch_um, an 8.64 multiple), tree "
             "node spans = integer multiples of it, so every node and mesh driver lands on a core-centre island "
             "(COORD 06:23); breaks = array gaps (e.g. a spine) the tree must bridge at a common node",
        no_leaf_axes=no_leaf, off_lattice_axes=off_lat)
    sites = (clock_sites(M, isl_decl, glue_parts, macros_die) if mesh_dir else
             dict(verdict="NOT RUN", note="no --mesh"))
    if mesh_dir:
        cen = [((r[0] + r[2]) / 2, (r[1] + r[3]) / 2) for r in isl_decl]
        core_only = macros_die[:n_core_macros]
        isl_lat = island_lattice(M, cen, core_only)
    else:
        isl_lat = dict(verdict="NOT RUN", note="no --mesh")
    # ---- COORD 10-26 rulings as static gates (master_rulings.py): leg repeaters at plan-fixed bay sites,
    # tap-region containment (regions = partition unions), footless stubs, no open island ft inputs
    Mx = M if mesh_dir else None
    parts_die, cores_die = MR.die_geometry(P, core_to_type, IS.rect_pts)
    rep_gate, rep_by_type = MR.clock_rep_sites(Mx, P, parts_die, cores_die, reach=CLOCK_REP_UM)
    isl_inst = []
    for part in P.parts:
        tn = P.parts[part]["type"]
        if islands.get(tn):
            isl_inst.append(dict(kind="partition", part=part, inst=part, role="die_node",
                                 rect_um=IS.rect_pts(P, part, islands[tn]["rect_um"])))
        for h in P.types[tn].get("hard_cores", []):
            e = entry[h["module"]]
            isl_inst.append(dict(kind="core", part=part, inst=f"{part}/{h['inst']}", role="clock_entry",
                                 rect_um=IS.rect_pts(P, part, core_to_type(h, e["island"]))))
            for q in (e.get("in_core_islands") or {}).get("islands", []):
                isl_inst.append(dict(kind="core", part=part, inst=f"{part}/{h['inst']}", role="tree_leaf",
                                     rect_um=IS.rect_pts(P, part, core_to_type(h, q["rect_um"]))))
    rulings = dict(clock_rep_sites=rep_gate, tap_region_containment=MR.tap_region_containment(Mx, P),
                   footless_stubs=MR.footless_stubs(Mx), island_ft_inputs=MR.island_ft_inputs(Mx, isl_inst))
    tap_in_phy = sorted(tn for tn, v in phy.items() if v.get("plan_tap_inside_phy"))
    sites["plan_taps_inside_phy"] = tap_in_phy
    if tap_in_phy:
        sites["verdict"] = "FAIL"
    ir = static_ir(ir_files)
    if mesh_dir:
        core_term = 0.0
        if ins_rows:
            core_term = max(core_tol_ps, max(abs(r["pred_TT_ps"] - common) for r in ins_rows
                                             if r["pred_TT_ps"] >= common - core_tol_ps) if any(
                r["pred_TT_ps"] >= common - core_tol_ps for r in ins_rows) else core_tol_ps)
        pr = {c: pair_skew_pred(M, c, core_term) for c in ("TT", "FF")}
        skew_model = dict(verdict="PASS" if max(v["pair_with_core_ps"] for v in pr.values()) <= skew_gate_ps
                          else "FAIL",
                          gate_ps=skew_gate_ps, predicted=pr, calibration=SKEW_CAL,
                          diagnostic_only=True,
                          note="80 ps is the 12.4a clock design target, not the freeze gate. Prediction is diagnostic; "
                               "freeze still requires real propagated-clock TT setup and FF hold STA.")
    else:
        skew_model = dict(verdict="NOT RUN", diagnostic_only=True, note="no --mesh (clock plan geometry)")

    gates = dict(
        reach_gap=dict(verdict="PASS" if not gap_fail else "FAIL", max_gap_um=r3(gap_max[0]),
                       worst_path=gap_max[1], fails=len(gap_fail), in_core_bays_proposed=len(in_core),
                       examples=gap_fail[:30]),
        bay_fill=dict(verdict="PASS" if not bay_fail and not part_fill_fail else "FAIL", bays=len(bays),
                      max_fill=r3(max([b["fill"] for b in bays] or [0])), bay_fails=len(bay_fail),
                      bay_fail_kinds=dict(_count(i.split(":")[0] for b in bay_fail for i in b["issues"])),
                      partition_fill_fails=len(part_fill_fail), examples=bay_fail[:20] + part_fill_fail[:10]),
        corridor_tracks=dict(verdict="PASS" if not worst_cells and not blocked else "FAIL", limit=track_max,
                             layers=use, worst_gcells=worst_cells, blocked_sections=len(blocked),
                             blocked=blocked[:20], m89_roads=len(m89_segs)),
        entry_pins=dict(verdict="PASS" if pin_max <= lim and not entry_missing else "FAIL", pins=len(pins), max_per_gcell=pin_max,
                        unplaced=sum(x["requested"]-x["placed"] for x in entry_missing),
                        failed_drops=len(entry_missing), missing_examples=entry_missing[:20], max_drop_reach_um=reach,
                        limit_per_gcell=lim, free_tracks_per_gcell=free_t, derivation=deriv),
        clock_shield=shield,
        static_ir=ir,
        lot_fit=dict(verdict="PASS" if not lot_fail else "FAIL", fails=lot_fail[:40], n=len(lot_fail)),
        clock_entry=dict(verdict="PASS" if not entry_fail else "FAIL", cores=sum(len(c["uses"]) for c in
                                                                                  core_types.values()),
                         fails=len(entry_fail), examples=entry_fail[:40]),
        core_reach=dict(verdict="PASS" if not restructure else "FAIL", limit_um=core_reach_um,
                        restructure=restructure),
        early_taps=dict(verdict="PASS" if not early and not mesh_early else "FAIL", plan_taps_offset=dict(early),
                        mesh_taps_early=len(mesh_early), examples=early_rows),
        tree_balance=bal,
        core_insertion_model=dict(
            verdict="PASS" if not ins_fail else "FAIL", fails=len(ins_fail), cores=len(ins_rows),
            model=dict(form="TT = RCX x K x L_max(entry -> farthest corner); FF = FF_RATIO x TT", K_ps_per_um=round(
                K_PS_PER_UM, 4), RCX=round(RCX_FACTOR, 4), FF_RATIO=round(FF_RATIO, 4), calibration=CAL_POINTS,
                calibration_err_ps=CAL_ERR, calibration_rms_ps=CAL_RMS_PS,
                note="shallow cores (pred < target) pad up with a designed fixed trunk (12.8c): not a FAIL"),
            examples=ins_fail[:40], all=ins_rows),
        die_pair_skew_model=skew_model,
        tree_commensurate=tree_comm,
        clock_sites=sites,
        island_lattice=isl_lat,
        infra_sites=sites_gate,
        **rulings,
    )
    verdict = "PASS" if all(g["verdict"] == "PASS" for g in gates.values() if not g.get("diagnostic_only")) else "FAIL"

    # ---- slices (type frame)
    mp = dict(schema=PLAN_SCHEMA, die=P.name, plan=str(P.path), plan_sha256=plan_sha, reach_um=reach,
              common_latency_ps=common, verdict=verdict, gates={k: g["verdict"] for k, g in gates.items()},
              model=dict(core_obs_top=core_obs_top, lower_pg_frac=lower_pg_frac, bay_fill=bay_fill,
                         fill_max=fill_max, track_max=track_max, detour_um=detour, gcell_um=G,
                         mesh=str(mesh_dir) if mesh_dir else None, tracks=tracks_file, pg=pg_file,
                         ir=[str(f) for f in ir_files], sites=sites_json),
              census=dict(paths=len(paths), lanes=sum(1 for p in paths if p["kind"] != "internal"),
                          internal=sum(1 for p in paths if p["kind"] == "internal"),
                          bits=sum(p["bits"] for p in paths),
                          bit_mm=r3(sum(p["bits"] * p["length_um"] for p in paths) / 1e3),
                          zero_length=sum(1 for p in paths if p["length_um"] < 1e-6)),
              core_entries=entry)
    body = json.dumps(mp, sort_keys=True).encode()
    mp_sha = hashlib.sha256(body).hexdigest()
    mp["master_plan_sha256"] = mp_sha
    write_slices.extra = dict(phy=phy, die_tree=tree_comm, clock_reps=rep_by_type, reach=reach)
    write_slices(P, out / "slices", bays, pins, roads, islands, entry, core_types, in_core, gates, common,
                 plan_sha, mp_sha)
    (out / "master_plan.json").write_text(json.dumps(dict(mp, paths=[{k: v for k, v in p.items() if k != "legs"}
                                                                    for p in paths]), indent=1, default=str))
    (out / "gates.json").write_text(json.dumps(dict(die=P.name, verdict=verdict, plan_sha256=plan_sha,
                                                    master_plan_sha256=mp_sha, gates=gates), indent=1, default=str))
    (out / "roads.json").write_text(json.dumps(dict(roads=roads, bays=bays, pins=pins[:200000]), default=str))
    if render:
        try:
            draw(P, out / "master_plan.png", roads, bays, pins, islands, gap_fail, entry)
        except Exception as ex:          # noqa: BLE001 -- render failure must not hide the gate report
            log(f"render failed: {ex}")
    return mp, gates


def _count(it):
    d = defaultdict(int)
    for x in it:
        d[x] += 1
    return d


def write_slices(P, d, bays, pins, roads, islands, entry, core_types, in_core, gates, common, plan_sha, mp_sha):
    gv = {k: g["verdict"] for k, g in gates.items()}
    lat = dict(common_clock_latency_ps=dict(TT=common, FF=round(common * 0.81, 1)), tol_ps=20, early_taps=False)
    by_type = defaultdict(list)
    for p, v in P.parts.items():
        by_type[v["type"]].append(p)

    def tr(part, r):
        return [r3(v) for v in IS.rect_pts(P, part, r)] if False else _to_type_rect(P, part, r)
    for tn, ps in by_type.items():
        t = P.types[tn]
        seen = {}
        bay_name = {}                    # die bay index -> slice bay name (entry pins reference the slice name)
        for bi, b in enumerate(bays):
            if b["type"] != tn:
                continue
            rt = tr(b["part"], b["rect_um"])
            key = (b["kind"], tuple(round(v, 1) for v in rt))
            s = seen.setdefault(key, dict(name=f"bay{len(seen)}", rect_um=rt, owner=tn, kind=b["kind"], bits=0,
                                          cell_area_um2=0.0, fill=0.0, layer="M7", paths=[]))
            bay_name[bi] = s["name"]
            if b.get("regions_um"):
                s["regions_um"] = [tr(b["part"],q) for q in b["regions_um"]]
            if b["bits"] > s["bits"]:
                s["bits"], s["cell_area_um2"], s["fill"] = b["bits"], b["cell_area_um2"], b["fill"]
            if len(s["paths"]) < 8:
                s["paths"].append(b["path"])
        isl = islands.get(tn)
        isl_rows = [dict(name="island", rect_um=isl["rect_um"], centre_um=list(isl.get("tap_um", [])),
                         use="clock_driver+reset", via_stack=["M9", "M1"], clock_pin=None,
                         pg_rails="die M8/M9 stripes on the 4.32 lattice")] if isl else []
        hcs, keep = [], [dict(name="island", rect_um=isl["rect_um"], kind="island", use=["placement"])] if isl else []
        for h in t.get("hard_cores", []):
            e = entry[h["module"]]
            ic = [b["proposed_in_core_bay"]["core_local_um"] for b in in_core
                  if b["type"] == tn and b.get("module") == h["module"]]
            hcs.append(dict(inst=h["inst"], module=h["module"], origin_um=h["origin_um"], outline_um=h["outline_um"],
                            orient=h.get("orient", "R0"),
                            islands=[e["island"]] + [q["rect_um"] for q in
                                                     (e.get("in_core_islands") or {}).get("islands", [])], bays=ic,
                            clock_entry_um=e["xy"]))
            keep.append(dict(name=f"core:{h['inst']}", rect_um=[r3(v) for v in (h["origin_um"][0], h["origin_um"][1],
                                                                                 h["origin_um"][0] + h["outline_um"][0],
                                                                                 h["origin_um"][1] + h["outline_um"][1])],
                             kind="hard_core", use=["placement"]))
        ep = []
        for p in pins:
            if p["part"] == ps[0]:
                x, y = P.to_type(p["part"], p["xy_um"])
                ep.append(dict(name=f"ep_{p['path']}_{p.get('drop', 0)}_{p['bit']}", pin=p.get("pin"), layer="M7",
                               xy_um=[r3(x), r3(y)], bay=bay_name.get(p["bay"]), path=p["path"], bit=p["bit"],
                               dir=p.get("dir"), pair=p.get("pair"), bay_kind=p.get("bay_kind"), drop=p.get("drop")))
        cor = []
        for rd in roads:
            if rd["part"] == ps[0]:
                a, b = P.to_type(rd["part"], rd["a"]), P.to_type(rd["part"], rd["b"])
                cor.append(dict(path=rd["path"], layer=rd["layer"], bits=rd["bits"],
                                polyline_um=[[r3(a[0]), r3(a[1])], [r3(b[0]), r3(b[1])]], band_um=rd["band_um"]))
        ex = getattr(write_slices, "extra", {}) or {}
        pe = (ex.get("phy") or {}).get(tn)
        if pe and pe.get("island"):
            isl_rows.append(dict(name="phy_clock_entry", rect_um=pe["island"], centre_um=pe["island_centre_um"],
                                 use="clock_driver+reset", via_stack=["M9", "M5"], clock_pin=pe["clock_pin"],
                                 pg_rails="die M8/M9 stripes on the 4.32 lattice"))
            keep.append(dict(name="phy_clock_entry", rect_um=pe["island"], kind="island", use=["placement"]))
        sl = dict(schema=SLICE_SCHEMA, die=P.name, kind="partition", type=tn, module=t.get("module"),
                  instances=sorted(ps), plan=str(P.path), plan_sha256=plan_sha, master_plan_sha256=mp_sha,
                  frozen=False, outline_um=t["outline_um"], keepouts=keep, islands=isl_rows,
                  bays=list(seen.values()), entry_pins=ep, hard_cores=hcs, latency=lat, corridors=cor, gates=gv)
        if pe:
            sl["phy_clock_entry"] = pe
        # 12.2a1 + COORD 06:53: the partition's infra island and the H-tree leg repeaters on it are PUSHDOWN cells of
        # the partition netlist (fixed, dont_touch, dedicated ft ports); the island blockage is dropped by the kit
        pdi = []
        if isl:
            c = isl.get("tap_um") or [(isl["rect_um"][0] + isl["rect_um"][2]) / 2,
                                      (isl["rect_um"][1] + isl["rect_um"][3]) / 2]
            pdi.append(pushdown_island(0, isl["rect_um"], c, "die_node", ex.get("reach") or 405.0, 0))
        reps = (ex.get("clock_reps") or {}).get(tn, [])
        if pdi or reps:
            sl["pushdown"] = dict(
                rule="12.2a1 / COORD 06:53: die clock drivers + leg repeaters are partition-netlist cells at these fixed "
                     "coordinates, identical for every instance (union of instance sites; unused ones fed from the "
                     "local strap, COORD 06:41); the die connects only through the mp_* ft ports",
                islands=pdi,
                clock_repeaters=[dict(name=f"crep{i}", xy_um=[r3(x), r3(y)], cell=CLOCK_REP_CELL,
                                      rect_um=[r3(x - 2.16), r3(y - 2.16), r3(x + 2.16), r3(y + 2.16)],
                                      ft_ports=[dict(name=f"mp_crep{i}_i", dir="in", layer="M5", xy_um=[r3(x), r3(y)]),
                                                dict(name=f"mp_crep{i}_o", dir="out", layer="M5",
                                                     xy_um=[r3(x + 2.16), r3(y)])])
                                 for i, (x, y) in enumerate(reps)])
        if hcs and ex.get("die_tree"):
            sl["die_tree"] = dict(rule=ex["die_tree"]["rule"], core_lattice=ex["die_tree"]["core_lattice"],
                                  verdict=ex["die_tree"]["verdict"])
        (d / f"{tn}.json").write_text(json.dumps(sl, indent=1))
    for mod, c in core_types.items():
        e = entry[mod]
        ic = [b["proposed_in_core_bay"] for b in in_core if b.get("module") == mod]
        sl = dict(schema=SLICE_SCHEMA, die=P.name, kind="core", type=mod, module=mod,
                  instances=sorted({f"{tn}/{h['inst']}" for tn, h in c["uses"]}), plan=str(P.path),
                  plan_sha256=plan_sha, master_plan_sha256=mp_sha, frozen=False, outline_um=c["outline_um"],
                  keepouts=[dict(name="clock_entry_island", rect_um=e["island"], kind="island", use=["placement"])]
                  + [dict(name=f"in_core_bay{i}", rect_um=b["core_local_um"], kind="in_core_bay",
                          use=["placement"]) for i, b in enumerate(ic)],
                  islands=[dict(name="clock_entry", rect_um=e["island"], centre_um=e["xy"],
                                use="clock_driver+reset", via_stack=["M9", "M5"],
                                clock_pin=dict(layer="M5", xy_um=e["xy"]),
                                pg_rails="die M8/M9 stripes on the 4.32 lattice")]
                  + [dict(name=f"tree_leaf{i}", rect_um=q["rect_um"], centre_um=q["centre_um"],
                          use="clock_driver+reset", via_stack=["M9", "M5"], clock_pin=None,
                          pg_rails="die M8/M9 stripes on the 4.32 lattice")
                     for i, q in enumerate((e.get("in_core_islands") or {}).get("islands", []))],
                  bays=[dict(name=f"in_core_bay{i}", rect_um=b["core_local_um"], owner=mod, kind="repeater",
                             bits=0, cell_area_um2=0.0, fill=0.0, layer="M6/M7", paths=[]) for i, b in enumerate(ic)],
                  entry_pins=[], hard_cores=[], latency=lat, corridors=[], gates=gv)
        w, h = c["outline_um"]
        sub = e.get("in_core_islands") or {}
        leaves = sub.get("islands", [])
        far = max(abs(cx - e["xy"][0]) + abs(cy - e["xy"][1]) for cx in (0, w) for cy in (0, h))
        pd = [pushdown_island(0, e["island"], e["xy"], "clock_entry",
                              (far if not leaves else max(abs(q["centre_um"][0] - e["xy"][0]) +
                                                          abs(q["centre_um"][1] - e["xy"][1]) for q in leaves)),
                              max(1, len(leaves)))]
        for i, q in enumerate(leaves):
            pd.append(pushdown_island(i + 1, q["rect_um"], q["centre_um"], "tree_leaf",
                                      sub.get("leaf_reach_um", 0.0), 0))
        sl["pushdown"] = dict(rule="12.2a1: island drivers are core-netlist cells at these fixed coordinates, "
                                   "identical for every instance; die connects only via the mp_isl* ft ports",
                              islands=pd)
        (d / f"{_safe(mod)}.json").write_text(json.dumps(sl, indent=1))


def _safe(s):
    return re.sub(r"[^A-Za-z0-9_.-]", "_", s)


def _to_type_rect(P, part, r):
    a, b = P.to_type(part, (r[0], r[1])), P.to_type(part, (r[2], r[3]))
    return [r3(min(a[0], b[0])), r3(min(a[1], b[1])), r3(max(a[0], b[0])), r3(max(a[1], b[1]))]


# ------------------------------------------------------------------------------------------------------ render
def draw(P, path, roads, bays, pins, islands, gap_fail, entry, dpi=160):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection, PatchCollection
    from matplotlib.patches import Rectangle
    s = 14.0 / max(P.W, P.H)
    fig, ax = plt.subplots(figsize=(P.W * s + 2.5, P.H * s + 0.6))
    rs, cs = [], []
    for part in P.parts:
        x0, y0, x1, y1 = P.rect(part)
        rs.append(Rectangle((x0, y0), x1 - x0, y1 - y0))
        for c in IS.type_cores(P.ptype(part)):
            q = IS.rect_pts(P, part, c[:4])
            cs.append(Rectangle((q[0], q[1]), q[2] - q[0], q[3] - q[1]))
    ax.add_collection(PatchCollection(rs, facecolor="none", edgecolor="#9aa0a6", linewidths=0.2))
    ax.add_collection(PatchCollection(cs, facecolor="#d9d2c3", edgecolor="#8d7f62", linewidths=0.15))
    for c in P.die.get("channels", []):
        x0, y0, x1, y1 = c["rect_um"] if "rect_um" in c else P.channel_rect(c)
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor="#eef3f8", edgecolor="#b5c3d1", lw=0.3))
    col = dict(M4="#1b9e77", M5="#66a61e", M6="#7570b3", M7="#386cb0", M8="#e7298a", M9="#d95f02")
    by = defaultdict(list)
    wid = defaultdict(list)
    for rd in roads:
        by[rd["layer"]].append([rd["a"], rd["b"]])
        wid[rd["layer"]].append(0.3 + 0.35 * math.log10(max(1, rd["bits"])))
    for L, segs in by.items():
        ax.add_collection(LineCollection(segs, colors=col.get(L, "k"), linewidths=wid[L], alpha=0.8,
                                         label=f"road {L} ({len(segs)})"))
    bx = [b["xy_um"] for b in bays if b["kind"] == "repeater"]
    st = [b["xy_um"] for b in bays if b["kind"] == "station"]
    if st:
        ax.scatter([p[0] for p in st], [p[1] for p in st], s=1.2, c="#08306b", marker="s", lw=0,
                   label=f"station bays ({len(st)})")
    if bx:
        ax.scatter([p[0] for p in bx], [p[1] for p in bx], s=1.6, c="#00a0b0", marker="D", lw=0,
                   label=f"repeater bays ({len(bx)})")
    ip = []
    for part, v in P.parts.items():
        isl = islands.get(v["type"])
        if isl:
            q = IS.rect_pts(P, part, isl["rect_um"])
            ip.append(((q[0] + q[2]) / 2, (q[1] + q[3]) / 2))
        for h in P.ptype(part).get("hard_cores", []):
            e = entry[h["module"]]["island"]
            q = IS.rect_pts(P, part, core_to_type(h, e))
            ip.append(((q[0] + q[2]) / 2, (q[1] + q[3]) / 2))
    if ip:
        ax.scatter([p[0] for p in ip], [p[1] for p in ip], s=2.0, c="#c0392b", marker="o", lw=0,
                   label=f"islands incl. core clock entries ({len(ip)})")
    if pins:
        ax.scatter([p["xy_um"][0] for p in pins], [p["xy_um"][1] for p in pins], s=0.3, c="#ff00ff", lw=0,
                   label=f"M7 entry pins ({len(pins)})")
    if gap_fail:
        ax.scatter([g["at_um"][0] for g in gap_fail], [g["at_um"][1] for g in gap_fail], s=18, c="red", marker="x",
                   lw=0.8, label=f"reach-gap FAIL ({len(gap_fail)})")
    ax.set_xlim(0, P.W)
    ax.set_ylim(0, P.H)
    ax.set_aspect("equal")
    ax.set_title(f"{P.name} master plan: roads (by layer), bays, entry pins, islands", fontsize=9)
    ax.legend(loc="upper left", bbox_to_anchor=(1.0, 1.0), fontsize=6, markerscale=4)
    ax.tick_params(labelsize=6)
    fig.tight_layout()
    fig.savefig(path, dpi=dpi)
    plt.close(fig)


# ------------------------------------------------------------------------------------------------------ CLI
def add_args(p):
    p.add_argument("plan")
    p.add_argument("--out", required=True)
    p.add_argument("--mesh", help="die clock mesh dir (mesh.json + route_TT.guide)")
    p.add_argument("--tracks", help="preroute.json (tracks_taken -> leftover M8/M9)")
    p.add_argument("--pg", help="sized PG pg.json (grid); default the plan die.pg.grid")
    p.add_argument("--ir", nargs="*", default=[], help="PDNSim region result.json files")
    p.add_argument("--entries", help="JSON {core module: {xy: [x, y] core-local, source}} clock entries")
    p.add_argument("--sites", help="precomputed infra_sites.json (else infra_sites.run is called)")
    p.add_argument("--reach", type=float)
    p.add_argument("--detour-um", type=float, default=405.0)
    p.add_argument("--core-obs-top", default="M5")
    p.add_argument("--lower-pg-frac", type=float, default=0.25)
    p.add_argument("--bay-fill", type=float, default=0.5)
    p.add_argument("--core-reach-um", type=float, default=200.0)
    p.add_argument("--no-render", action="store_true")


def cmd(a):
    P = S.Plan(S.load(a.plan), Path(a.plan))
    entries = json.loads(Path(a.entries).read_text()) if a.entries else None
    mp, gates = run(P, a.out, mesh_dir=a.mesh, tracks_file=a.tracks, pg_file=a.pg, ir_files=a.ir, entries=entries,
                    sites_json=a.sites, reach=a.reach, detour=a.detour_um, core_obs_top=a.core_obs_top,
                    lower_pg_frac=a.lower_pg_frac, bay_fill=a.bay_fill, core_reach_um=a.core_reach_um,
                    render=not a.no_render)
    print(json.dumps(dict(die=mp["die"], verdict=mp["verdict"], gates=mp["gates"], census=mp["census"]), indent=1))
    return 0 if mp["verdict"] == "PASS" else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    add_args(ap)
    return cmd(ap.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
