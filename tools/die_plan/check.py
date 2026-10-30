"""G0 die-plan check (TOPDOWN-PLAN): seconds, read-only, no EDA tools.

    python3 tools/die_plan/check.py PLAN.json [--out DIR] [--png] [--json-only] [--strict]

Checks (each finding is ERROR or WARN; G0 PASS = no ERROR):
  schema      structure + references (schema.validate): buses bound exactly once, no tie-offs, lane continuity
  geometry    partitions inside the die, on die.grid_um, pairwise non-overlapping; uncovered die area not in
              die.channels (WARN); partition larger than one hop without extra stations (WARN)
  abutment    every port's src face and dst face coincide (same line, window inside both edges, or on the die edge
              for @die); the pins (schema.pin_positions) land on tracks in BOTH partition frames; ports sharing a
              face + layer do not overlap; ft slot buses sit on the slot's in/out face; every instance of a
              replicated type yields the IDENTICAL pin table (bus, bit, layer, type-frame face and coordinate)
  layers      port and ft layers <= die.layer_budget.partition_signal_max
  m89_signals METHODOLOGY 5.1 / ruling 9.3 (B#12 2026-10-24): no signal on M8/M9 -- they carry only the die clock
              spine, die reset and PG.  ERROR for die_use ft_reserved, ft_route_layers / lane route_layers / port /
              bus / spare-slot / face_layers / ft slot / channel layers on M8/M9, type ft_budget on M8/M9, and
              partition_signal_max above M7
  faces       per partition face: pins / um <= face_pins_per_um averaged over every face_window_um window (all
              layers together, at most face_pin_layers layers per port); per port + layer pins / tracks <= pin_track_max
  cuts        cut sweep every cut_step_um, vertical and horizontal lines: the bits of every lane route crossing the
              line against the free tracks (M4-M7, core OBS union removed, per-layer FT-band shares or ft_track_frac); full line and per partition
              segment <= cut_ratio_max (the die layers M8/M9 add no signal capacity, ruling 9.3; the M8/M9-only
              ratio is still reported as research info)
  hops        every register-to-register hop of every lane <= reach (lane.reach_um, else die.reach_um; both capped
              at the 405-um M4-M7 signal reach, ruling 9.3); ft stations <= ft_station_max_um (default 405, R3,
              ruling 9.4) apart; a plan budget above 405 is an ERROR
  types       type count, instances per type, near-duplicate types (same outline + interface, other offsets: merge
              them; replicated types should declare type-frame pin windows)
  latency     the latency table lists every lane and equals Plan.lane_latency() (only source for RTL + compiler)
  r8          COORD R8 bus-coherent latency on BINDER2's as-built bus groups (--groups bus_groups.json, else
              PLANDIR/{r8,bind}/bus_groups.json): one added delay per as-built bus, equal across replicated consumers, no
              as-built order inversion, one landing pad per site of a replicated type (r8.py); depth = the R8 landing
              table (--landing, else PLANDIR/**/<die>_r8_landing.json from gen.py latency --groups) or the bound top
  hard_pinreg registered-pin hard types (hard_pinreg.py): single hard core with registered_pins + lib, no ft slots;
              every lib corner view has setup+hold on every input and clk->q on every output (fail closed)
  clock/reset every non-hard type has a clock tap inside its outline on a die layer and a reset synchronizer;
              data_reset false, epoch bit true (schema)
  clock_mesh  (--clock-build DIR, repeatable; COORD PATH-S81-PD12 ruling A 10-27) the die clock mesh build in DIR is
              ONE connected net: an M8-M9 VIA89 at every strap crossing, emitted (mesh.json meta.mesh_vias) and in the
              routed DB (OT_MESH_VIAS of combo_<corner>.log); ERROR in G0 and G0C (die_clock_mesh.mesh_via_findings)
  clock_entry_macro (G0C) plan clock entry / island (clock_entries.json) over a hard-core macro of core_macros.json
  merged_clock_view (G0C, HBM-STREETS-3, COORD 10-27 19:12 ruling 1) every merged core tap (merged_clock_ports) checked on
              its own vs the native LEF+Liberty (merged_core_clocks.audit): mismatch = ERROR; a core with no native view is
              a PENDING-VIEW item (never PASS: verdict PENDING-VIEW, exit 3 when it is the only finding class)
  streets     (G0C, METHODOLOGY 12.10c street rule, streets.py) street_reach: every hard-core point <= 400 um from the
              street network (free area >= die.streets.width_um wide, largest connected component); street_width: width >=
              (clock + hold + FT repeater widths) / 0.6; street_clock_leg: no die-clock H-tree leg / driver of a
              --clock-build across a hard core, unplaced build rows = ERROR; street_die_leg: no lane station inside a core
  core_pg     (PG-CORECONN-2) a type placing hard-core / hardened macros (non-PHY) without core_pg_connect: true, or
              a macro LEF with no VDD+VSS PG pin geometry on M4/M5/M6: WARN; ERROR with --strict-core-pg
  G0C (--completeness): hard_cores, core_faces, complete, clock_entry_macro; PLAN-TOOL5 cross-die rules die_io_plan (die_io.py),
              cut_lines / reach / face_tracks / ft_budget (xdie.py, per-layer reach table reach.py)
Outputs in --out (default: next to the plan): g0_report.json and, with --png, die_plan.png (the G1 render).
"""
import argparse
import bisect
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reach as RT  # noqa: E402
import schema as S  # noqa: E402
from schema import DIE_PART, OPP  # noqa: E402

EPS = 1e-6
PART_FT_LAYERS = dict(H=("M4", "M6"), V=("M5", "M7"))   # in-partition ft layers (M2/M3 are cell-local)
FT_TRACK_FRAC = 0.25                                       # default share of those tracks a partition gives to ft


def lnum(name):
    return int(name[1:])


# G0C (COORD 10-23 ~20:10): the plan-completeness / hard-core rules are ERRORs only under `check.py --completeness`;
# plain G0 reports them as WARN "[G0C] ..." so a plan that passed G0 keeps passing while it is completed.
G0C_CHECKS = ("hard_cores", "core_faces", "complete",
              # PLAN-TOOL5 (COORD die-plan visual review 10-23, cross-die items (a)-(e)): die_io.py / xdie.py
              "die_io_plan", "cut_lines", "reach", "face_tracks", "ft_budget",
              # HBM-MU-QUAD-6/CLK (COORD 10-27): a core clock entry (12.8a) / its island never sits over a hard-core macro
              "clock_entry_macro", "merged_clock_view",
              # HBM-STREETS-1 (OWNER 10-27 ~18:4x, METHODOLOGY 12.10c): street rule (streets.py)
              "street_reach", "street_width", "street_clock_leg", "street_die_leg")


class Report:
    def __init__(self, completeness=False):
        self.items = []
        self.completeness = completeness

    def err(self, check, msg, **kw):
        if check in G0C_CHECKS:
            kw["g0c"] = True
            if not self.completeness:
                self.items.append(dict(level="WARN", check=check, msg="[G0C] " + msg, **kw))
                return
        self.items.append(dict(level="ERROR", check=check, msg=msg, **kw))

    def warn(self, check, msg, **kw):
        self.items.append(dict(level="WARN", check=check, msg=msg, **kw))

    def errors(self):
        return [i for i in self.items if i["level"] == "ERROR"]

    def pending(self, check, msg, **kw):
        """PENDING-VIEW item (HBM-STREETS-3): never an ERROR, never a PASS."""
        self.items.append(dict(level="PENDING-VIEW", check=check, msg=msg, g0c=True, **kw))

    def pendings(self):
        return [i for i in self.items if i["level"] == "PENDING-VIEW"]


def check_merged_clock_view(P, R):
    """merged_clock_view: merged_core_clocks.audit over every merged core tap (no stop at the first core)."""
    import merged_core_clocks as MC
    rows = MC.audit(P)
    for r in rows:
        if r["status"] == "FAIL":
            R.err("merged_clock_view", r["msg"], type=r["type"])
        elif r["status"] == "PENDING-VIEW" and R.completeness:
            R.pending("merged_clock_view", r["msg"], type=r["type"])
    by = defaultdict(int)
    for r in rows:
        by[r["status"]] += 1
    mods = sorted({r["module"] for r in rows if r["status"] == "PENDING-VIEW"})
    return dict(taps=len(rows), by_status=dict(by), pending_view_modules=mods)


def on_grid(v, g):
    k = v / g
    return abs(k - round(k)) < 1e-6


def face_line(rect, face):
    """(axis coordinate of the face line, lo, hi along the face)."""
    x0, y0, x1, y1 = rect
    return {"E": (x1, y0, y1), "W": (x0, y0, y1), "N": (y1, x0, x1), "S": (y0, x0, x1)}[face]


def on_track(c, L):
    k = (c - L["offset_um"]) / L["pitch_um"]
    return abs(k - round(k)) < 1e-4


# --------------------------------------------------------------------------------------------------- geometry
def check_ft_macro_sites(P, R):
    """Reject station cells inside placed SRAM/ROM/core footprints at actual bit sites."""
    import gen_phys
    import ft_bit_sites
    from ft_full_stage import load
    count = 0
    for tn, t in P.types.items():
        try:
            boxes = S.placed_macro_boxes(t)
        except ValueError as exc:
            R.err('geometry', f'type {tn}: {exc}', type=tn)
            continue
        try:
            full = load(P, tn)
        except (ValueError, KeyError, OSError) as exc:
            R.err('geometry', f'type {tn}: invalid full-stage FT packet: {exc}', type=tn)
            continue
        if not boxes or not t.get('ft_slots'):
            continue
        pins = defaultdict(dict)
        for bus, bit, _layer, x, y, face in gen_phys.type_pins(P, tn):
            pins[bus][bit] = (x, y, face)
        for slot in t['ft_slots']:
            try:
                ft_bit_sites.validate_slot(slot)
            except ValueError as exc:
                R.err('geometry', f'type {tn} slot {slot["name"]}: {exc}', type=tn)
                continue
            name = slot['name']; stages = int(slot.get('stations', 1)); hits = 0; example = None
            if name in full:
                for (j,bit), row in full[name].items():
                    x,y=row['xy']; w,h=row['size']
                    for macro,(x0,y0,x1,y1) in boxes.items():
                        if min(x+w,x1)-max(x,x0)>EPS and min(y+h,y1)-max(y,y0)>EPS:
                            hits+=1; example=example or (j,bit,macro); break
                if hits:
                    j,bit,macro=example; count+=hits
                    R.err('geometry', f'type {tn} slot {name}: {hits} exact full-stage cells intersect physical macros (stage {j}, bit {bit}, macro {macro})', type=tn)
                continue
            pi, po = pins[name+'_i'], pins[name+'_o']
            for bit in sorted(set(pi) | set(po)):
                ap = pi.get(bit) or po[bit]; bp = po.get(bit) or pi[bit]
                def inset(p):
                    x, y, face = p
                    return {'E': (x-1,y), 'W': (x+1,y), 'N': (x,y-1), 'S': (x,y+1)}[face]
                a, b = inset(ap), inset(bp); route = zroute(a, b, ap[2], bp[2]); length = plen(route)
                for j in range(stages):
                    if name in full:
                        row = full[name][j,bit]; x,y = row['xy']; w,h = row['size']
                        rect = (x,y,x+w,y+h)
                    elif slot.get('bit_sites_um') and j > 0:
                        x, y = slot['bit_sites_um'][j-1][bit]; w, h = slot['bit_site_cell_um']
                        rect = (x, y, x+w, y+h)
                    else:
                        xy = a if slot.get('bit_sites_um') else tuple(slot['regs_um'][j]) if slot.get('regs_um') else point_at(route, length*j/stages)
                        x, y = xy; rect = (x, y, x, y)
                    for macro, (x0,y0,x1,y1) in boxes.items():
                        # Centres have no extent; explicit cells must clear with their whole envelope.
                        hit = (x0+EPS < rect[0] < x1-EPS and y0+EPS < rect[1] < y1-EPS) if rect[0] == rect[2] else (min(rect[2],x1)-max(rect[0],x0)>EPS and min(rect[3],y1)-max(rect[1],y0)>EPS)
                        if hit:
                            hits += 1; example = example or (j, bit, macro); break
            if hits:
                j, bit, macro = example; count += hits
                R.err('geometry', f'type {tn} slot {name}: {hits} actual-bit station cells/sites intersect physical macros (stage {j}, bit {bit}, macro {macro})', type=tn)
    return count


def check_clock_entry_macro(P, R, plan_dir=None, macros_file=None, entries_file=None, eps=1e-3):
    """HBM-MU-QUAD-6/CLK (COORD 10-27, METHODOLOGY 12.8a): every hard core's plan clock entry (PLANDIR/clock_entries.json,
    core frame) sits in a std-cell region: its island rect and its point must not overlap any macro rectangle (+ halo) of
    that core's module in the plan macro sidecar (PLANDIR/core_macros.json, opentallas.core_macros.v1: cores[module] =
    {status KNOWN|NONE|UNKNOWN, macros[{name, rect_um}]}, halo_um).  Overlap = ERROR (G0C); touching edges is legal.
    Missing sidecar / entries, modules with UNKNOWN macro positions and hard cores without an entry are WARN."""
    out = dict(entries=0, checked=0, over_macro=0, unknown_macros=0, no_entry=0, sidecar=None)
    pd = Path(plan_dir) if plan_dir else None
    mf = Path(macros_file) if macros_file else (pd / "core_macros.json" if pd else None)
    ef = Path(entries_file) if entries_file else (pd / "clock_entries.json" if pd else None)
    if not ef or not ef.is_file():
        return out
    CEN = json.loads(ef.read_text())
    if not mf or not mf.is_file():
        R.warn("clock_entry_macro", f"no core macro sidecar ({mf}): clock entries vs hard-core macros unchecked")
        return out
    MAC = json.loads(mf.read_text())
    out["sidecar"] = str(mf)
    halo = float(MAC.get("halo_um", 0.0))
    cores = MAC.get("cores", {})

    def ov(a, b):
        return (min(a[2], b[2] + halo) - max(a[0], b[0] - halo) > eps and
                min(a[3], b[3] + halo) - max(a[1], b[1] - halo) > eps)

    def pin(p, b):
        return b[0] - halo + eps < p[0] < b[2] + halo - eps and b[1] - halo + eps < p[1] < b[3] + halo - eps

    unknown, seen = set(), set()
    for tn, t in P.types.items():
        ents = CEN.get(tn) or {}
        for c in t.get("hard_cores", []) or []:
            inst = c.get("inst")
            e = ents.get(inst)
            if not isinstance(e, dict):
                e = ents.get(re.sub(r"__q\d+$", "", inst or ""))      # hub split u_x__q0/__q1 share u_x's entry
            if not isinstance(e, dict):
                out["no_entry"] += 1
                R.warn("clock_entry_macro", f"type {tn} hard core {inst} ({c.get('module')}): no plan clock entry", type=tn)
                continue
            out["entries"] += 1
            m = c.get("module")
            cm = cores.get(m) or {}
            if cm.get("status") != "KNOWN":
                if cm.get("status") != "NONE" and m not in unknown:
                    unknown.add(m)
                    R.warn("clock_entry_macro", f"module {m}: macro positions {cm.get('status', 'not in sidecar')} -- "
                           "clock entry vs macros unchecked", type=tn)
                continue
            out["checked"] += 1
            key = (m, tuple(e["xy_um"]), tuple(e["island_um"]))
            hits = [mm.get("name") for mm in cm.get("macros", [])
                    if ov(e["island_um"], mm["rect_um"]) or pin(e["xy_um"], mm["rect_um"])]
            if hits:
                out["over_macro"] += 1
                if key not in seen:
                    seen.add(key)
                    R.err("clock_entry_macro", f"type {tn} core {inst} ({m}): clock entry {e['xy_um']} / island "
                          f"{e['island_um']} over macro(s) {hits[:3]} (+halo {halo:g}): move the entry to a std-cell "
                          "region at the core's clock centroid (12.8a)", type=tn)
    out["unknown_macros"] = len(unknown)
    return out


def channel_flows(P):
    """declared partition channels that state a bit count ("N bits" in channel.reason): a flow along the channel's
    long axis through its centre (die frame), for the per-street demand."""
    import re as _re
    out = []
    for n, p in P.parts.items():
        for k, ch in enumerate(P.types[p["type"]].get("channels", []) or []):
            m = _re.search(r"(\d+)\s*bits", str(ch.get("reason", "")))
            if not m or not ch.get("rect_um"):
                continue
            x, y, w, h = ch["rect_um"]
            a, b = ((x, y + h / 2), (x + w, y + h / 2)) if w >= h else ((x + w / 2, y), (x + w / 2, y + h))
            a, b = P.to_die(n, a), P.to_die(n, b)
            if abs(a[0] - b[0]) < 1e-6 or abs(a[1] - b[1]) < 1e-6:
                out.append((f"{n}/channel{k}", int(m.group(1)), [tuple(a), tuple(b)]))
    return out


def check_streets(P, R, plan_dir=None, clock_builds=(), geo=None, max_msgs=40, png=None, keep=None):
    """METHODOLOGY 12.10c STREET RULE (G0C, streets.py): hard cores on a street grid, every core point <= reach_um
    (400) from the street network, street width >= repeater + hold + FT budget / fill, no clock leg (clock builds:
    htree legs, driver sites, unplaced rows) across a hard core, every die lane station off the hard cores."""
    import die_clock as DC
    import streets as ST
    ko = DC.keepouts(P)
    cfg = ST.config(P.die.get("streets"))
    legs, pts, unpl = [], [], []
    for b in clock_builds or ():
        lg, pt, up = ST.clock_build_legs(b)
        legs += lg
        pts += pt
        unpl += up
    flows = []
    for lid, (lpts, regs, _xs) in (geo or {}).items():
        pts += [(f"{lid}#{k}", tuple(p), "lane_station") for k, p in enumerate(regs[1:-1], 1)]
        try:
            bits = int(P.ports[P.lanes[lid]["ports"][0]]["width"])
        except (KeyError, IndexError, TypeError, ValueError):
            bits = 0
        flows.append((lid, bits, [tuple(q) for q in lpts]))
    flows += channel_flows(P)
    # HBM-STREETS-2 (COORD 10-27 18:52): per-street demand replaces the flat 34.56-um width; a plan may still pin the
    # legacy flat width with die.streets.mode = "flat"
    if str((P.die.get("streets") or {}).get("mode", "demand")) == "flat":
        flows = None
    A = ST.analyze(float(P.W), float(P.H), ko, cfg, legs, pts, unpl, flows=flows)
    if png:
        ST.render(A, ko, png, float(P.W), float(P.H), P.name)
    if keep is not None:
        keep.append((A, ko))      # ROOT-MERGE-82: run() renders streets.png AFTER the G1 render (see run)
    # severity (COORD 10-27 18:52): ERROR on hbm (12.10c); REPORT-ONLY (WARN) on the other dies until their own ruling;
    # die.streets.enforce overrides
    enforce = (P.die.get("streets") or {}).get("enforce")
    if enforce is None:
        enforce = str(getattr(P, "name", "")).lower().startswith("hbm")
    emit = R.err if enforce else R.warn
    n = {}
    for chk, core, msg in A["errors"]:
        n[chk] = n.get(chk, 0) + 1
        if n[chk] <= max_msgs:
            emit(chk, msg)
    for chk, c in n.items():
        if c > max_msgs:
            emit(chk, f"... {c - max_msgs} more {chk} findings (g0_report summary.streets)")
    over = [c for c in A["cores"] if c["street_dist_um"] is None or c["street_dist_um"] > cfg["reach_um"] + 1e-6]
    return dict(enforce=bool(enforce), cfg={k: v for k, v in cfg.items()}, clock_builds=len(clock_builds or ()), streets=A["streets"], cores=len(A["cores"]), cores_over_reach=len(over),
                worst_cores=A["worst_cores"], clock_legs=len(legs), clock_legs_over_core=len(A["legs_over_core"]),
                legs_over_core=A["legs_over_core"][:50], points_in_core=len(A["points_in_core"]),
                points_in_core_rows=A["points_in_core"][:50], unplaced=len(unpl), counts=n)


def check_geometry(P, R):
    g = P.grid
    for nm, base in [("ORFS base lattice", S.BASE_LATTICE_UM)] + \
            [(f"{L} pitch", P.layers[L]["pitch_um"]) for L in sorted(P.layers) if int(L[1:]) >= 4]:
        k = g / base
        if abs(k - round(k)) > 1e-6:
            R.err("geometry", f"die.grid_um {g:g} is not a multiple of the {nm} {base:g} um")
    W, H = P.W, P.H
    rects = {n: P.rect(n) for n in P.parts}
    for n, (x0, y0, x1, y1) in rects.items():
        if x0 < -EPS or y0 < -EPS or x1 > W + EPS or y1 > H + EPS:
            R.err("geometry", f"partition {n} {fmt_rect((x0, y0, x1, y1))} outside the die {W}x{H}", part=n)
        for v in (x0, y0):
            if not on_grid(v, P.grid):
                R.err("geometry", f"partition {n} origin {x0},{y0} not on the {P.grid}-um grid", part=n)
                break
    for tn, t in P.types.items():
        for v in t["outline_um"]:
            if not on_grid(v, P.grid):
                R.err("geometry", f"type {tn} outline {t['outline_um']} not on the {P.grid}-um grid", type=tn)
                break
    names = sorted(rects, key=lambda n: rects[n][0])
    xs = [rects[n][0] for n in names]
    for i, a in enumerate(names):
        ax0, ay0, ax1, ay1 = rects[a]
        j = i + 1
        while j < len(names) and xs[j] < ax1 - EPS:
            b = names[j]
            bx0, by0, bx1, by1 = rects[b]
            if min(ax1, bx1) - max(ax0, bx0) > EPS and min(ay1, by1) - max(ay0, by0) > EPS:
                R.err("geometry", f"partitions {a} and {b} overlap", part=a, other=b)
            j += 1
    area = sum((r[2] - r[0]) * (r[3] - r[1]) for r in rects.values())
    chan = 0.0
    chans = []
    for c in P.die.get("channels", []):
        r = P.channel_rect(c)
        chan += max(0.0, r[2] - r[0]) * max(0.0, r[3] - r[1])
        if "ports" in c:
            vert = (r[2] - r[0]) < (r[3] - r[1])            # vertical channel: wires cross it horizontally
            along, wdir = ((r[3] - r[1]), "H") if vert else ((r[2] - r[0]), "V")
            tr = sum(along / P.layers[L]["pitch_um"] for L in c["layers"] if P.layers[L]["dir"] == wdir)
            bits = sum(S.port_pins_count(P.ports[q]) for q in c["ports"])
            ratio = bits / tr if tr else math.inf
            if abs((r[2] - r[0] if vert else r[3] - r[1]) - c["width_um"]) > 1e-3:
                R.err("geometry", f"channel {c.get('name', '?')}: gap between {c['between']} is "
                      f"{(r[2] - r[0] if vert else r[3] - r[1]):g} um, width_um {c['width_um']:g}")
            if ratio > P.budgets["cut_ratio_max"] + EPS:
                R.err("cuts", f"channel {c.get('name', '?')}: {bits} pins on {tr:.0f} {wdir} tracks = {ratio:.2f} > "
                      f"{P.budgets['cut_ratio_max']}")
            chans.append(dict(name=c.get("name"), between=c["between"], rect_um=[round(v, 4) for v in r],
                              width_um=c["width_um"], area_mm2=round((r[2] - r[0]) * (r[3] - r[1]) / 1e6, 5),
                              bits=bits, tracks=round(tr), ratio=round(ratio, 4)))
    gap = W * H - area - chan
    if gap > 0.001 * W * H:
        R.warn("geometry", f"{gap / 1e6:.3f} mm2 ({100 * gap / (W * H):.1f}% of the die) is neither partition nor a "
               "die.channels entry with a reason")
    for tn, t in P.types.items():
        w, h = t["outline_um"]
        for sl in t.get("ft_slots", []):
            fs = {sl["in_face"], sl["out_face"]}
            span = w if fs == {"E", "W"} else h if fs == {"N", "S"} else (w + h) / 2.0
            if span > P.reach * sl.get("stations", 1) + EPS:
                R.warn("geometry", f"type {tn} slot {sl['name']}: crossing ~{span:.0f} um > {sl.get('stations', 1)} "
                       f"station(s) x reach {P.reach:.0f} (see hops)", type=tn)
    macro_hits = check_ft_macro_sites(P, R)
    return dict(partition_area_mm2=area / 1e6, channel_area_mm2=chan / 1e6, uncovered_mm2=max(gap, 0) / 1e6,
                fill=area / (W * H), planned_channels=chans, station_macro_intersections=macro_hits)


def fmt_rect(r):
    return "[" + ",".join(f"{v:g}" for v in r) + "]"


# --------------------------------------------------------------------------------------------------- abutment
def check_abutment(P, R):
    """returns {(part, die_face): [(coord, layer, port)]} for the face-density check."""
    face_pins = defaultdict(list)
    type_tables = defaultdict(dict)    # type -> {inst: {(bus, bit): (layer, tface, coord)}}
    smax = lnum(P.layer_budget["partition_signal_max"])
    for pid, pr in P.ports.items():
        f = pr["face"]
        # per-face layer sets (COORD 10-23): a type may list face_layers[type face]; then every pin layer on that
        # face must be in the set, and a layer above partition_signal_max is allowed only when EVERY partition end
        # lists it for its face (still <= M7: an M8/M9 face layer is an m89_signals ERROR, ruling 9.3)
        pend = []
        if pr["src"]["part"] != DIE_PART:
            pend.append((pr["src"]["part"], f))
        if pr["dst"]["part"] != DIE_PART:
            pend.append((pr["dst"]["part"], OPP[f] if pr["src"]["part"] != DIE_PART else f))
        fl = [(pt, P.type_face(pt, df), P.ptype(pt).get("face_layers", {}).get(P.type_face(pt, df)))
              for pt, df in pend]
        for ln in pr["layers"]:
            for pt, tf, allowed in fl:
                if allowed is not None and ln not in allowed:
                    R.err("layers", f"port {pid}: pin layer {ln} not in {pt}'s face_layers[{tf}] {allowed}",
                          port=pid)
            if ln in P.layers and lnum(ln) > smax and not (fl and all(a and ln in a for _, _, a in fl)):
                R.err("layers", f"port {pid}: pin layer {ln} above partition_signal_max "
                      f"{P.layer_budget['partition_signal_max']} (allowed only via the type's face_layers)",
                      port=pid)
        try:
            pins = P.port_pins(pid)
        except (ValueError, KeyError) as e:
            R.err("abutment", f"port {pid}: {e}", port=pid)
            continue
        ends = []
        if pr["src"]["part"] != DIE_PART:
            ends.append(("src", pr["src"], f))
        if pr["dst"]["part"] != DIE_PART:
            ends.append(("dst", pr["dst"], OPP[f] if pr["src"]["part"] != DIE_PART else f))
        lo, hi = sorted(pr["window_um"])
        lines = []
        for side, e, df in ends:
            line, a, b = face_line(P.rect(e["part"]), df)
            lines.append((side, e["part"], df, line))
            if lo < a - EPS or hi > b + EPS:
                R.err("abutment", f"port {pid}: window [{lo:g},{hi:g}] outside the {df} face [{a:g},{b:g}] of "
                      f"{e['part']}", port=pid)
        ch = P.channel_of(pid)
        if ch and len(lines) == 2:
            if {pr["src"]["part"], pr["dst"]["part"]} != set(ch["between"]):
                R.err("abutment", f"port {pid}: in channel {ch.get('name', '?')} but its ends are not "
                      f"{ch['between']}", port=pid)
            elif abs(abs(lines[0][3] - lines[1][3]) - ch["width_um"]) > 1e-3:
                R.err("abutment", f"port {pid}: faces {lines[0][3]:g} / {lines[1][3]:g} are not one channel width "
                      f"({ch['width_um']:g}) apart", port=pid)
            for ln in pr["layers"]:
                if ln not in ch["layers"]:
                    R.err("abutment", f"port {pid}: pin layer {ln} not a layer of channel {ch.get('name', '?')} "
                          f"{ch['layers']}", port=pid)
        elif len(lines) == 2 and abs(lines[0][3] - lines[1][3]) > EPS:
            R.err("abutment", f"port {pid}: {lines[0][1]}.{lines[0][2]} at {lines[0][3]:g} and {lines[1][1]}."
                  f"{lines[1][2]} at {lines[1][3]:g} do not abut", port=pid)
        if DIE_PART in (pr["src"]["part"], pr["dst"]["part"]) and lines:
            side, part, df, line = lines[0]
            edge = {"E": P.W, "W": 0.0, "N": P.H, "S": 0.0}[df]
            if abs(line - edge) > EPS:
                R.err("abutment", f"port {pid}: die IO on {part}.{df} at {line:g}, not on the die edge {edge:g}",
                      port=pid)
        for side, e, df in ends:
            part = e["part"]
            tf = P.type_face(part, df)
            b = P.buses(part).get(e["bus"], {})
            if b.get("slot") and b.get("face") != tf:
                R.err("abutment", f"port {pid}: {part}.{e['bus']} is on type face {tf}, slot face is {b['face']}",
                      port=pid)
            tab = type_tables[P.parts[part]["type"]].setdefault(part, {})
            o = P.orient(part)
            w, h = P.ptype(part)["outline_um"]
            ox, oy = P.parts[part]["origin_um"]
            if df in "EW":     # 1-D transform of the along-face coordinate into the type frame
                flip, base, ext = o in ("MX", "R180"), oy, h
            else:
                flip, base, ext = o in ("MY", "R180"), ox, w
            for bit, ln, c in pins:
                tc = (ext - (c - base)) if flip else (c - base)
                if not on_track(tc, P.layers[ln]):
                    R.err("abutment", f"port {pid}: bit {bit} {ln} at die {c:.3f} is off-track in {part}'s frame "
                          f"({P.orient(part)}, type coord {tc:.4f})", port=pid, part=part)
                    break
                tab[(e["bus"], bit)] = (ln, tf, round(tc, 4))
            for bit, ln, c in pins:
                face_pins[(part, df)].append((c, ln, pid))
    # spare slots (COORD 10-23): reserved type-face windows with NO pins
    for tn, t in P.types.items():
        sp = t.get("spare_slots", [])
        if not sp:
            continue
        w, h = t["outline_um"]
        for s_ in sp:
            lo, hi = sorted(s_["window_um"])
            ext = h if s_["face"] in "EW" else w
            if lo < -EPS or hi > ext + EPS:
                R.err("abutment", f"type {tn} spare slot {s_['name']}: window [{lo:g},{hi:g}] outside face "
                      f"{s_['face']} [0,{ext:g}]", type=tn)
            for fs in t.get("ft_slots", []):
                for fk, wk in (("in_face", "in_window_um"), ("out_face", "out_window_um")):
                    if fs.get(fk) == s_["face"] and fs.get(wk):
                        a, b = sorted(fs[wk])
                        if a < hi and lo < b and set(fs.get("layers") or s_["layers"]) & set(s_["layers"]):
                            R.err("abutment", f"type {tn} spare slot {s_['name']} overlaps ft slot {fs['name']} "
                                  f"{wk} [{a:g},{b:g}]", type=tn)
        for part, tab in type_tables.get(tn, {}).items():
            for (bus, bit), (ln, tf, tc) in tab.items():
                for s_ in sp:
                    lo, hi = sorted(s_["window_um"])
                    if s_["face"] == tf and ln in s_["layers"] and lo - EPS <= tc <= hi + EPS:
                        R.err("abutment", f"{part}.{bus}[{bit}] {ln} at type {tf} {tc:g} lies in spare slot "
                              f"{s_['name']} [{lo:g},{hi:g}] (a spare slot carries no pins)", part=part)
                        break
    # overlapping ports on one face + layer
    for (part, df), pins in face_pins.items():
        by = defaultdict(list)
        for c, ln, pid in pins:
            by[ln].append((c, pid))
        for ln, lst in by.items():
            lst.sort()
            for (c0, p0), (c1, p1) in zip(lst, lst[1:]):
                if p0 != p1 and abs(c1 - c0) < P.layers[ln]["pitch_um"] - EPS:
                    R.err("abutment", f"{part}.{df} {ln}: ports {p0} and {p1} share track {c0:.3f}", part=part)
                    break
    # replicated types: identical pin tables
    for tn, insts in type_tables.items():
        ref_name, ref = None, None
        for inst, tab in sorted(insts.items()):
            if ref is None:
                ref_name, ref = inst, tab
                continue
            if tab != ref:
                diff = set(tab.items()) ^ set(ref.items())
                k = sorted(diff)[0]
                R.err("abutment", f"type {tn}: instance {inst} pin table differs from {ref_name} ({len(diff)} "
                      f"entries, e.g. {k[0][0]}[{k[0][1]}] {k[1]}) -- a replicated type must have identical pins",
                      type=tn)
    return face_pins


# ------------------------------------------------------------------------------------------------------ faces
def check_faces(P, R, face_pins):
    B = P.budgets
    win = B["face_window_um"]
    # allowance of 2 pins per pin layer, so a window spread at exactly the budget passes (PLAN-HBM 10-23):
    # 1 pin for whole-track quantisation;
    # 1 pin for pins pushed out of the partition PG bands (schema.spread, coordinate-uniform, nearest usable track).
    worst = []
    for (part, df), pins in face_pins.items():
        # a type face whose face_layers lists n > face_pin_layers layers (S81 svc fold: M7/M5 + M8 from the die
        # budget, COORD 10-23 07:43) gets the per-layer budget on each layer: face_pins_per_um * n / face_pin_layers
        fl = P.ptype(part).get("face_layers", {}).get(P.type_face(part, df))
        nl = max(B["face_pin_layers"], len(fl) if fl else 0)
        # per-type budget (G2-proven, KV RULING 10-25 (a)) where the type declares one, never above the hard cap
        tb = P.ptype(part).get("face_pins_per_um")
        per = min(float(tb), S.FACE_PINS_HARD_CAP) if tb else B["face_pins_per_um"]
        if tb and not P.ptype(part).get("face_budget_g2"):
            R.err("faces", f"{part}: type face_pins_per_um {tb:g} without face_budget_g2 (the G2 probe that proves "
                  "it)", part=part)
        lim = per * nl / B["face_pin_layers"] * win + 2 * nl
        cs = sorted(c for c, _, _ in pins)
        mx, at = 0, None
        for i, c in enumerate(cs):
            j = bisect.bisect_right(cs, c + win - EPS)
            if j - i > mx:
                mx, at = j - i, c
        worst.append((mx / win, part, df))
        if mx > lim + EPS:
            R.err("faces", f"{part}.{df}: {mx} pins in the {win:g}-um window at {at:.2f} "
                  f"({mx / win:.2f}/um > {per:g})", part=part)
    for pid, pr in P.ports.items():
        if len(pr["layers"]) > B["face_pin_layers"]:
            ends = [(pr[k]["part"], pr["face"] if k == "src" else OPP[pr["face"]]) for k in ("src", "dst")
                    if pr[k]["part"] != DIE_PART]
            if not ends or not all(set(pr["layers"]) <= set(P.ptype(pt).get("face_layers", {}).get(
                    P.type_face(pt, df), [])) for pt, df in ends):
                R.err("faces", f"port {pid}: {len(pr['layers'])} pin layers > {B['face_pin_layers']} "
                      "(more only on a face_layers face listed by both ends)", port=pid)
        nl = len(pr["layers"])
        # per window: a multi-window hop (KV-PLAN-DELTA-9 `segments`) is judged on each of its segment windows
        for b0, b1, swin in S.port_segments(pr):
            lo, hi = sorted(swin)
            for li, ln in enumerate(pr["layers"]):
                if ln not in P.layers:
                    continue
                nb = sum(1 for k in range(b0, b1) if k % nl == li)
                tr = max(1, S.usable_tracks(P.layers[ln], ln, lo, hi))     # tracks off the PG stripes (M5-M8)
                if nb / tr > B["pin_track_max"] + EPS:
                    R.err("faces", f"port {pid}: {nb} pins on {tr} {ln} tracks = {nb / tr:.2f} > "
                          f"{B['pin_track_max']}", port=pid)
    worst.sort(reverse=True)
    return [dict(part=p, face=f, pins_per_um=round(v, 3)) for v, p, f in worst[:10]]


# ---------------------------------------------------------------------------------------------- lane routes
def zroute(a, b, face_in, face_out=None):
    """rectilinear route from a to b inside a partition entered on face_in: an L for a turning slot (out face
    perpendicular to the in face: along the in face's normal, then along the out face's normal), else a Z through the
    midpoint (straight-through slot with a jog)."""
    if abs(a[0] - b[0]) < EPS or abs(a[1] - b[1]) < EPS:
        return [a, b]
    if face_out and (face_in in "EW") != (face_out in "EW"):
        return [a, (b[0], a[1]), b] if face_in in "EW" else [a, (a[0], b[1]), b]
    if face_in in "EW":
        xm = (a[0] + b[0]) / 2.0
        return [a, (xm, a[1]), (xm, b[1]), b]
    ym = (a[1] + b[1]) / 2.0
    return [a, (a[0], ym), (b[0], ym), b]


def plen(pts):
    return sum(abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(pts, pts[1:]))


def point_at(pts, t):
    for p, q in zip(pts, pts[1:]):
        d = abs(p[0] - q[0]) + abs(p[1] - q[1])
        if t <= d + EPS:
            f = 0.0 if d == 0 else t / d
            return (p[0] + f * (q[0] - p[0]), p[1] + f * (q[1] - p[1]))
        t -= d
    return pts[-1]


def lane_geometry(P, lid):
    """route polyline (die frame), register points in order, and per-crossing info."""
    ln = P.lanes[lid]
    pts = [P.port_point(ln["ports"][0])]
    regs = [pts[0]]
    xs = []
    for part, slot, a, b in P.lane_crossings(lid):
        pa, pb = P.port_point(a), P.port_point(b)
        s = P.slot(part, slot) or {}
        fin = P.die_face(part, s.get("in_face", "W"))
        fout = P.die_face(part, s.get("out_face", "E"))
        seg = zroute(pa, pb, fin, fout)
        L = plen(seg)
        k = int(s.get("stations", 1))
        from ft_full_stage import load, centre
        full = load(P, P.parts[part]["type"])
        if slot in full:
            st = [P.to_die(part, centre(full[slot][j,0])) for j in range(k)]
        elif s.get("regs_um"):
            st = [P.to_die(part, tuple(r)) for r in s["regs_um"]]
        else:
            st = [point_at(seg, L * j / k) for j in range(k)]
        regs.extend(st)
        xs.append(dict(part=part, slot=slot, len_um=round(L, 1), stations=k))
        pts.extend(seg[1:])
    regs.append(P.port_point(ln["ports"][-1]))
    return pts, regs, xs



def lane_pin_hops(P, lid, regs):
    """FF-to-FF reach through mandatory slot pins, including inter-partition seams.

    Manhattan distance between FF centres can shortcut a required output/input
    pin detour. Each intervening declared pin is part of the actual net route.
    This remains a geometric lower bound; routed wire may be longer.
    """
    if not regs:
        return []
    hops = []
    previous = regs[0]
    length = 0.0
    index = 1
    for part, slot, a, b in P.lane_crossings(lid):
        pa, pb = P.port_point(a), P.port_point(b)
        length += abs(previous[0] - pa[0]) + abs(previous[1] - pa[1])
        previous = pa
        count = int((P.slot(part, slot) or {}).get("stations", 1))
        for point in regs[index:index + count]:
            length += abs(previous[0] - point[0]) + abs(previous[1] - point[1])
            hops.append(length)
            previous, length = point, 0.0
        index += count
        length += abs(previous[0] - pb[0]) + abs(previous[1] - pb[1])
        previous = pb
    endpoint = regs[-1]
    length += abs(previous[0] - endpoint[0]) + abs(previous[1] - endpoint[1])
    hops.append(length)
    return hops


def station_max(P, R=None):
    """R3 (ruling 9.4): ft stations at most ft_station_max_um apart, a ceiling of 405 um (SIGNAL_REACH_UM)."""
    v = float(P.budgets.get("ft_station_max_um", S.SIGNAL_REACH_UM))
    if R is not None and v > S.SIGNAL_REACH_UM + EPS:
        R.err("stations", f"budgets.ft_station_max_um {v:g} > {S.SIGNAL_REACH_UM:g} um (R3, ruling 9.4: stations every "
              f"<= {S.SIGNAL_REACH_UM:g} um); judged at {S.SIGNAL_REACH_UM:g}")
    return min(v, S.SIGNAL_REACH_UM)


def check_m89_signals(P, R, max_msgs=40):
    """ruling 9.3: signals (partition pins, ft, die-top nets) only on <= M7; M8/M9 = die clock spine / reset / PG."""
    res = set(S.RESERVED_DIE_LAYERS)
    smax = lnum(S.SIGNAL_LAYER_MAX)
    cnt = defaultdict(int)
    n = [0]

    def bad(what, msg, **kw):
        cnt[what] += 1
        n[0] += 1
        if n[0] <= max_msgs:
            R.err("m89_signals", msg + " (ruling 9.3: M8/M9 carry only the die clock spine, reset and PG)", **kw)

    lb = P.layer_budget
    if lnum(lb["partition_signal_max"]) > smax:
        bad("partition_signal_max", f"layer_budget.partition_signal_max {lb['partition_signal_max']} above "
            f"{S.SIGNAL_LAYER_MAX}")
    if "ft_reserved" in lb.get("die_use", []):
        bad("ft_reserved", "layer_budget.die_use lists ft_reserved (over-the-top ft on M8/M9)")
    if res & set(lb.get("ft_route_layers", [])):
        bad("ft_route_layers", f"layer_budget.ft_route_layers {lb['ft_route_layers']} include M8/M9")
    for lid, ln in P.lanes.items():
        if res & set(ln.get("route_layers", [])):
            bad("lane_route_layers", f"lane {lid}: route_layers {ln['route_layers']} include M8/M9", lane=lid)
    for tn, t in P.types.items():
        for f, ls in t.get("face_layers", {}).items():
            if res & set(ls):
                bad("face_layers", f"type {tn}: face_layers[{f}] {ls} include M8/M9", type=tn)
        for b in t.get("buses", []):
            if res & set(b.get("layers", [])):
                bad("bus_layers", f"type {tn} bus {b['name']}: layers {b['layers']} include M8/M9", type=tn)
        for sl in t.get("ft_slots", []):
            if res & ({sl.get("layer")} | set(sl.get("layers", []))):
                bad("ft_slot_layers", f"type {tn} ft slot {sl['name']}: on M8/M9", type=tn)
        for sp in t.get("spare_slots", []):
            if res & set(sp.get("layers", [])):
                bad("spare_slot_layers", f"type {tn} spare slot {sp['name']}: layers {sp['layers']} include M8/M9",
                    type=tn)
        fb = {k: v for k, v in t.get("ft_budget", {}).items() if k in res and v > 0}
        if fb:
            bad("ft_budget", f"type {tn}: ft_budget {fb} reserves M8/M9 tracks for ft", type=tn)
    for pid, pr in P.ports.items():
        if res & set(pr.get("layers", [])):
            bad("port_layers", f"port {pid}: pin layers {pr['layers']} include M8/M9", port=pid)
    for ch in P.die.get("channels", []):
        if "ports" in ch and res & set(ch.get("layers", [])):
            bad("channel_layers", f"channel {ch.get('name', '?')}: signal layers {ch['layers']} include M8/M9")
    if n[0] > max_msgs:
        R.err("m89_signals", f"... {n[0] - max_msgs} more signal uses of M8/M9 (counts in summary.m89_signals)")
    dr = P.die_reach_um
    if dr > S.SIGNAL_REACH_UM + EPS:
        R.warn("hops", f"die.reach_um {dr:g} > the {S.SIGNAL_REACH_UM:g}-um M4-M7 signal reach (ruling 9.3); hops "
               f"are judged at {S.SIGNAL_REACH_UM:g}")
    return dict(total=n[0], by=dict(cnt))


def check_hops(P, R, geo):
    worst = []
    for lid, (pts, regs, xs) in geo.items():
        reach = min(float(P.lanes[lid].get("reach_um", P.reach)), P.reach)
        from ft_full_stage import lane_hops
        has_full = any(P.types[P.parts[x["part"]]["type"]].get("ft_full_stage_placement_file") for x in xs)
        hops = lane_hops(P, lid) if has_full else lane_pin_hops(P, lid, regs)
        h = max(hops) if hops else 0.0
        worst.append((h / reach, lid, h, reach))
        if h > reach + EPS:
            i = hops.index(h)
            R.err("hops", f"lane {lid}: hop {i} via mandatory slot pins is {h:.0f} um > reach {reach:.0f} (add stations to the crossed "
                  "partition's slot or shorten it)", lane=lid)
    # R3 (ruling 9.4): ft stations at most budgets.ft_station_max_um (<= 405) apart inside every crossed partition
    smax = station_max(P, R)
    seen = set()
    for lid, (pts, regs, xs) in geo.items():
        for x in xs:
            key = (P.parts[x["part"]]["type"], x["slot"])
            if key in seen:
                continue
            seen.add(key)
            from ft_full_stage import load, centre
            full = load(P, key[0])
            if key[1] in full:
                rows = full[key[1]]
                k = x["stations"]
                width = next(s["width"]+1 for s in P.types[key[0]]["ft_slots"] if s["name"]==key[1])
                sp = max((sum(abs(a-b) for a,b in zip(centre(rows[j,b]),centre(rows[j+1,b]))) for b in range(width) for j in range(k-1)), default=0)
            else:
                sp = x["len_um"] / max(1, x["stations"])
            if sp > smax + EPS:
                detail = "exact per-bit internal hop" if key[1] in full else f"{x['len_um']:.0f}um route / {x['stations']} stations"
                R.err("stations", f"type {key[0]} slot {key[1]}: {detail} = {sp:.0f} um > ft_station_max_um {smax:.0f}", type=key[0])
    worst.sort(reverse=True)
    result = []
    for _, lid, h, reach in worst[:10]:
        regs = geo[lid][1]
        direct = max((abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(regs, regs[1:])), default=0.0)
        result.append(dict(lane=lid, hop_um=round(h, 1), reach_um=reach,
                           direct_ff_hop_um=round(direct, 1),
                           via_pin_role="mandatory seam pin lower bound"))
    return result


# ------------------------------------------------------------------------------------------------------- cuts
def track_density(P, names, frac):
    return sum(frac / P.layers[n]["pitch_um"] for n in names if n in P.layers)


def cut_interval_tracks(lo, hi, pitch, frac, blocked=(), bands=()):
    """Exact free tracks on a cut: OBS union wins; bands replace the base share.

    blocked=[(lo,hi)], bands=[(lo,hi,share)] are intervals on ONE layer.
    Integrating all boundaries avoids double-counting overlapping OBS or bands.
    """
    points={float(lo),float(hi)}
    for a,b in blocked:
        points.update((max(lo,min(hi,a)),max(lo,min(hi,b))))
    for a,b,_ in bands:
        points.update((max(lo,min(hi,a)),max(lo,min(hi,b))))
    points=sorted(points);tracks=0.0
    for a,b in zip(points,points[1:]):
        mid=(a+b)/2
        if b-a<=EPS or any(u<mid<v for u,v in blocked):continue
        shares=[share for u,v,share in bands if u<=mid<=v]
        tracks+=(b-a)*(max(shares) if shares else frac)/pitch
    return tracks


def check_cuts(P, R, geo):
    # Same rectangles as the die-route capacity model: declared/routed core
    # obstructions (union), transformed through each instance orientation,
    # plus the explicitly reserved per-layer feedthrough bands.
    from die_trial import die_core_rects, ft_band_rects
    cores={L:die_core_rects(P,L) for L in {l for ls in PART_FT_LAYERS.values() for l in ls}}
    bands=ft_band_rects(P)
    B = P.budgets
    step = B["cut_step_um"]
    lim = B["cut_ratio_max"]
    avail = P.layer_budget.get("cut_avail", {})
    die_l = [n for n in P.layer_budget["die_layers"] if n in P.layers]
    out = dict(vertical=[], horizontal=[])
    # segment list: (x0, y0, x1, y1, bits)
    segs = []
    for lid, (pts, _, _) in geo.items():
        w = P.ports[P.lanes[lid]["ports"][0]]["width"]
        for p, q in zip(pts, pts[1:]):
            segs.append((p, q, w))
    rects = {n: P.rect(n) for n in P.parts}
    worst_full, worst_loc = (0, None), (0, None)
    for orient, D, along in (("vertical", P.W, P.H), ("horizontal", P.H, P.W)):
        wire_dir = "H" if orient == "vertical" else "V"     # wires crossing a vertical line run horizontally
        dl = [n for n in die_l if P.layers[n]["dir"] == wire_dir]
        die_den = 0.0           # ruling 9.3: M8/M9 carry no signals, cut_avail adds no capacity
        die_den_raw = sum(1.0 / P.layers[n]["pitch_um"] for n in dl)
        n = int(D // step)
        for k in range(1, n + 1):
            c = k * step
            if c >= D - EPS:
                break
            hits = []
            for p, q, w in segs:
                a, b = (p[0], q[0]) if orient == "vertical" else (p[1], q[1])
                if min(a, b) < c - EPS and max(a, b) > c + EPS:
                    hits.append(((p[1] if orient == "vertical" else p[0]), w))
            bits = sum(w for _, w in hits)
            cap = along * die_den
            parts_cap = 0.0
            loc = []
            for pn, r in rects.items():
                lo, hi, a0, a1 = (r[1], r[3], r[0], r[2]) if orient == "vertical" else (r[0], r[2], r[1], r[3])
                if not (a0 < c - EPS and a1 > c + EPS):
                    continue
                t = P.ptype(pn)
                frac = t.get("ft_track_frac", FT_TRACK_FRAC)
                seg_cap=0.0
                for L in PART_FT_LAYERS[wire_dir]:
                    if L not in P.layers:continue
                    obs=[((cr[1],cr[3]) if orient=="vertical" else (cr[0],cr[2]))
                         for cr in cores[L] if ((cr[0]+EPS<c<cr[2]-EPS) if orient=="vertical" else (cr[1]+EPS<c<cr[3]-EPS))]
                    reserved=[(*((br[2],br[4]) if orient=="vertical" else (br[1],br[3])),br[5])
                              for br in bands if br[0]==L and
                              ((br[1]+EPS<c<br[3]-EPS) if orient=="vertical" else (br[2]+EPS<c<br[4]-EPS))]
                    seg_cap+=cut_interval_tracks(lo,hi,P.layers[L]["pitch_um"],frac,obs,reserved)
                parts_cap+=seg_cap
                sb = sum(w for y, w in hits if lo - EPS <= y <= hi + EPS)
                if sb:
                    loc.append((sb / seg_cap if seg_cap else math.inf, pn, sb, seg_cap))
            for ch in P.die.get("channels", []):          # planned channels: their own layers are die-route tracks
                if "ports" not in ch:
                    continue
                r = P.channel_rect(ch)
                lo, hi, a0, a1 = (r[1], r[3], r[0], r[2]) if orient == "vertical" else (r[0], r[2], r[1], r[3])
                if not (a0 < c - EPS and a1 > c + EPS):
                    continue
                cden = sum(1.0 / P.layers[L]["pitch_um"] for L in ch["layers"] if P.layers[L]["dir"] == wire_dir
                           and L not in dl)
                seg_cap = (hi - lo) * (cden + die_den)
                parts_cap += (hi - lo) * cden
                sb = sum(w for y, w in hits if lo - EPS <= y <= hi + EPS)
                if sb:
                    loc.append((sb / seg_cap if seg_cap else math.inf, f"channel:{ch.get('name', '?')}", sb, seg_cap))
            cap += parts_cap
            ratio = bits / cap if cap else (math.inf if bits else 0.0)
            m89 = bits / (along * die_den_raw) if die_den_raw else 0.0
            rec = dict(at_um=c, bits=bits, tracks=round(cap), ratio=round(ratio, 4), m89_only_ratio=round(m89, 4))
            if loc:
                lr, lp, lb, lc = max(loc)
                rec.update(worst_part=lp, worst_part_ratio=round(lr, 4), worst_part_bits=lb)
                if lr > lim + EPS:
                    R.err("cuts", f"{orient} cut at {c:g}: {lp} segment carries {lb} bits on {lc:.0f} tracks "
                          f"= {lr:.2f} > {lim}", part=lp)
                if lr > worst_loc[0]:
                    worst_loc = (lr, f"{orient}@{c:g}:{lp}")
            if ratio > lim + EPS:
                R.err("cuts", f"{orient} cut at {c:g}: {bits} bits on {cap:.0f} tracks = {ratio:.2f} > {lim}")
            if ratio > worst_full[0]:
                worst_full = (ratio, f"{orient}@{c:g}")
            out[orient].append(rec)
    out["worst_full"] = dict(ratio=round(worst_full[0], 4), at=worst_full[1])
    out["worst_partition_segment"] = dict(ratio=round(worst_loc[0], 4), at=worst_loc[1])
    out["model"] = dict(partition_ft_layers=PART_FT_LAYERS, ft_track_frac_default=FT_TRACK_FRAC,
                        die_layers=die_l, cut_avail=avail, step_um=step,
                        core_obs="declared/routed union", ft_bands="piecewise per-layer reserved shares")
    return out


# ---------------------------------------------------------------------------------------------- latency etc.
def check_latency(P, R):
    tab = P.raw.get("latency", {}).get("lanes")
    if tab is None:
        R.err("latency", "no latency table (generate it: python3 tools/die_plan/gen.py latency PLAN.json --inplace)")
        return {}
    for lid in P.lanes:
        ln_ = P.lanes[lid]
        if ln_.get("beats") or ln_.get("word_bits"):
            # DEC12 multi-beat lane: both keys, and the port carries ceil(word / beats) + beat-index bits
            bt, wb = int(ln_.get("beats", 0)), int(ln_.get("word_bits", 0))
            w0 = int(P.ports[ln_["ports"][0]]["width"])
            need = -(-wb // bt) + int(ln_.get("beat_index_bits", max(1, (bt - 1).bit_length()))) if bt and wb else None
            if need is None or w0 != need:
                R.err("latency", f"lane {lid}: beats {bt} / word_bits {wb} need port width {need}, got {w0}", lane=lid)
        want = P.lane_latency(lid)
        got = tab.get(lid)
        if got is None:
            R.err("latency", f"lane {lid}: missing from the latency table", lane=lid)
        elif got["cycles"] != want["cycles"]:
            R.err("latency", f"lane {lid}: table says {got['cycles']} cycles, plan gives {want['cycles']}", lane=lid)
        elif got.get("word_cycles") != want.get("word_cycles"):
            R.err("latency", f"lane {lid}: table word_cycles {got.get('word_cycles')} != plan {want.get('word_cycles')}",
                  lane=lid)
    # R8: one cycle per latency group (bus groups from BINDER2 + replicated consumers), checked on the TABLE (what the
    # binder / compiler read), and pads realisable per type
    for name, kind, lids in P.latency_groups():
        got = {l: tab.get(l, {}).get("cycles") for l in lids if l in P.lanes}
        if len(set(got.values())) > 1:
            R.err("latency", f"{kind} group {name}: unequal delays {got} (regenerate: gen.py latency --inplace pads "
                  "every member to the slowest)")
    _, bad = P.bus_pads()
    for m in bad + P.landed_skew():
        R.err("latency", m)
    return {lid: P.lane_latency(lid)["cycles"] for lid in P.lanes}


def check_clock_reset(P, R):
    die_l = set(P.layer_budget["die_layers"])
    for tn, t in P.types.items():
        if t.get("hard"):
            continue
        ck = t.get("clock")
        if ck and "tap_um" in ck:
            w, h = t["outline_um"]
            x, y = ck["tap_um"]
            if not (0 <= x <= w and 0 <= y <= h):
                R.err("clock", f"type {tn}: clock tap {x},{y} outside the outline", type=tn)
            if ck.get("layer") and ck["layer"] not in die_l:
                R.err("clock", f"type {tn}: clock tap layer {ck['layer']} is not a die layer {sorted(die_l)}", type=tn)
            far = max(abs(x - a) + abs(y - b) for a in (0, w) for b in (0, h))
            ck_reach = min(RT.TABLE[n]["measured_um"] for n in S.RESERVED_DIE_LAYERS)   # clock wire: M8/M9 relay reach
            if far > 2 * ck_reach:
                R.warn("clock", f"type {tn}: farthest boundary point {far:.0f} um from the tap (> 2 hops)", type=tn)
        insts = {c["inst"] for c in t.get("contents", [])}
        for b in t.get("buses", []):
            lf = b.get("leaf")
            if lf is None:
                R.warn("schema", f"type {tn}: bus {b['name']} has no leaf binding", type=tn)
            elif lf.split(".")[0] not in insts:
                R.err("schema", f"type {tn}: bus {b['name']} binds to unknown instance {lf}", type=tn)
        smax = lnum(P.layer_budget["partition_signal_max"])
        for s in t.get("ft_slots", []):
            if s.get("layer") and lnum(s["layer"]) > smax:
                R.err("layers", f"type {tn} slot {s['name']}: ft layer {s['layer']} above partition_signal_max",
                      type=tn)


CLOCK_LEG_MAX_UM = 405.0   # OWNER 10-17 planned reach; GEOM-REVIEW-2 11:35 R1 (3) chain-hop taps <= ~400 um
CLOCK_BUF_HALO_UM = 2.0   # GEOM-REVIEW 15:24 [PATH-HBM-TKMCLKBUF] (1): halo to any FT bit site / station register


def _buf_near_station(t, q, cell=(1.404, 0.27), full=None):
    """First FT bit site / ft station / internal station register whose cell box (bit_site_cell_um, LL at the point)
    comes within CLOCK_BUF_HALO_UM of the buffer point q, else None."""
    h = CLOCK_BUF_HALO_UM

    def hit(p, wh):
        return (p[0] - h - EPS < q[0] < p[0] + wh[0] + h + EPS) and (p[1] - h - EPS < q[1] < p[1] + wh[1] + h + EPS)

    for slot, rows in (full or {}).items():
        for row in rows.values():
            if hit(row["xy"], row["size"]):
                return f"ft {slot} full-stage {row['stage']}/{row['bit']}"
    for f in t.get("ft_slots", []) or []:
        if f["name"] in (full or {}):
            continue
        wh = f.get("bit_site_cell_um") or cell
        for p in f.get("regs_um", []) or []:
            if hit(p, wh):
                return f"ft {f['name']} station {p}"
        for grp in f.get("bit_sites_um", []) or []:
            for p in grp:
                if hit(p, wh):
                    return f"ft {f['name']} bit site {p}"
    for s in t.get("internal_stations", []) or []:
        for p in s.get("regs_um", []) or []:
            if hit(p, cell):
                return f"internal station {s.get('conn')} {p}"
    return None

def check_clock_branch_buffers(P, R):
    """PATH-HBM 10-25 (COORD ruling (1) 14:44): clock.branch_buffers are real std-cell clock buffers: none inside a
    hard core, every driven tap exists and names the buffer as its parent (and every taps[].parent is a buffer),
    and every leg (buffer -> driven tap, Manhattan) is <= CLOCK_LEG_MAX_UM."""
    from ft_full_stage import load
    out = dict(buffers=0, worst_leg_um=0.0, types=[])
    reach = CLOCK_LEG_MAX_UM
    for tn, t in P.types.items():
        full = load(P, tn)
        ck = t.get("clock") or {}
        bufs = ck.get("branch_buffers") or []
        taps = {tp["name"]: tp for tp in ck.get("taps", []) or []}
        names = [b["name"] for b in bufs]
        bad = False
        if len(set(names)) != len(names):
            R.err("clock", f"type {tn}: duplicate branch buffer names", type=tn)
            bad = True
        for nm, tp in taps.items():
            if tp.get("parent") and tp["parent"] not in names:
                R.err("clock", f"type {tn}: tap {nm} parent {tp['parent']} is not a branch buffer", type=tn)
                bad = True
        boxes = []
        for c in t.get("hard_cores", []) or []:
            x, y = c["origin_um"]
            dx, dy = c.get("track_offset_um", [0, 0])
            w, h = c["outline_um"]
            boxes.append((c["inst"], x + dx, y + dy, x + dx + w, y + dy + h))
        for b in bufs:
            out["buffers"] += 1
            q = b["xy"]
            hit = next((n for n, x0, y0, x1, y1 in boxes
                        if x0 + EPS < q[0] < x1 - EPS and y0 + EPS < q[1] < y1 - EPS), None)
            if hit:
                R.err("clock", f"type {tn}: branch buffer {b['name']} at {q} is inside hard core {hit}", type=tn)
                bad = True
            near = _buf_near_station(t, q, full=full)
            if near:
                R.err("clock", f"type {tn}: branch buffer {b['name']} at {q} within {CLOCK_BUF_HALO_UM} um halo of "
                               f"{near}", type=tn)
                bad = True
            for d in b["drives"]:
                tp = taps.get(d)
                if tp is None:
                    R.err("clock", f"type {tn}: branch buffer {b['name']} drives unknown tap {d}", type=tn)
                    bad = True
                    continue
                if tp.get("parent") != b["name"]:
                    R.err("clock", f"type {tn}: tap {d} driven by {b['name']} but its parent is {tp.get('parent')}",
                          type=tn)
                    bad = True
                leg = abs(tp["xy"][0] - q[0]) + abs(tp["xy"][1] - q[1])
                out["worst_leg_um"] = max(out["worst_leg_um"], round(leg, 2))
                if leg > reach + EPS:
                    R.err("clock", f"type {tn}: branch buffer {b['name']} leg to {d} {leg:.1f} um > reach {reach:g}",
                          type=tn)
                    bad = True
            # GEOM-REVIEW 15:24 (2): leg repeaters (slew) are SYMMETRIC -- the same count on every leg of a buffer --
            # std cells off every hard core and the station halo; every segment buffer -> rep -> ... -> tap <= reach
            reps = b.get("leg_repeaters")
            if reps is not None:
                cnt = {d: [r for r in reps if r.get("tap") == d] for d in b["drives"]}
                if len({len(v) for v in cnt.values()}) != 1 or any(r.get("tap") not in cnt for r in reps):
                    R.err("clock", f"type {tn}: branch buffer {b['name']} leg repeaters not symmetric "
                                   f"{ {d: len(v) for d, v in cnt.items()} }", type=tn)
                    bad = True
                for d, rl in cnt.items():
                    tp = taps.get(d)
                    pts = [q] + [r["xy"] for r in sorted(rl, key=lambda r: r["k"])] + ([tp["xy"]] if tp else [])
                    for a_, b_ in zip(pts, pts[1:]):
                        if abs(a_[0] - b_[0]) + abs(a_[1] - b_[1]) > reach + EPS:
                            R.err("clock", f"type {tn}: {b['name']} leg {d} segment {a_}->{b_} > reach {reach:g}",
                                  type=tn)
                            bad = True
                    for r in rl:
                        ll, (cw, ch_) = r["cell_ll_um"], r.get("cell_wh_um", (1.404, 0.27))
                        hit = next((n for n, x0, y0, x1, y1 in boxes if ll[0] < x1 - EPS and ll[0] + cw > x0 + EPS
                                    and ll[1] < y1 - EPS and ll[1] + ch_ > y0 + EPS), None)
                        if hit:
                            R.err("clock", f"type {tn}: leg repeater {r['name']} cell at {ll} overlaps hard core {hit}",
                                  type=tn)
                            bad = True
                        near = _buf_near_station(t, r["xy"], full=full)
                        if near:
                            R.err("clock", f"type {tn}: leg repeater {r['name']} within {CLOCK_BUF_HALO_UM} um halo of "
                                           f"{near}", type=tn)
                            bad = True
                        out["leg_repeaters"] = out.get("leg_repeaters", 0) + 1
        if bad:
            out["types"].append(tn)
    return out


def check_reset(P, R):
    """OWNER RESET RULE 2026-10-24 (reset_tree.py): pipelined plans -- every type's equal-depth relay tree builds with
    hops <= reset.relay_um under the plan contract part_depth, the die region trees reach every partition; counted
    plans -- one WARN (the rule is not met yet).  Summary: release, K, per region die depth E / release clocks /
    hosting."""
    import reset_tree
    errs, warns, info = reset_tree.check(P)
    for e in errs:
        R.err("reset", e)
    for w in warns:
        R.warn("reset", w)
    if info is None:
        return dict(release=P.reset.get("release", "counted"))
    if info.get("release") == "wavefront":     # OWNER DECISION 13: per-partition release offsets (reset_tree.py offsets)
        return {k: info[k] for k in ("release", "sync_stages", "root", "hop_um", "relay_um", "max_release",
                                     "max_die_hop_um", "unreachable")}
    return dict(release=info["release"], part_depth_K=info["part_depth_K"], relay_um=info["relay_um"],
                regions=[{k: v for k, v in r.items() if k not in ("nonuniform_types", "busiest_hosts")}
                         for r in info["regions"]])


# ------------------------------------------------------------------------------------------- taps, hard cores
def _orient_pt(o, w, h, x, y):
    return {"R0": (x, y), "MX": (x, h - y), "MY": (w - x, y), "R180": (w - x, h - y)}[o]


CORE_CELLS_MAX = 400_000      # COORD 10-23 (CORE-KS): above this a partition type must be built from hard cores
MIRROR_SKIP = ("M2", "M3")    # platform cell-access tracks: not the plan lattice in a mirrored instance's die frame


def type_cells(t):
    """estimated std cells of one instance: type.cells, else the sum of contents[].cells (None when unknown)."""
    if "cells" in t:
        return int(t["cells"])
    cs = [c["cells"] for c in t.get("contents", []) if "cells" in c]
    return sum(cs) if cs else None


_PIN_CACHE = {}


def core_pins(hc, plan_dir=None):
    """[(name, layer, x, y)] of one hard core in its own frame (R0, origin 0): pins[] + pins_file (cached)."""
    pins = [(p_["name"], p_["layer"], *p_["xy"]) for p_ in hc.get("pins", [])]
    if hc.get("pins_file"):
        key = str(Path(plan_dir or ".") / hc["pins_file"])
        if key not in _PIN_CACHE:
            js = json.loads(Path(key).read_text())
            js = js.get("pins", js) if isinstance(js, dict) else js
            _PIN_CACHE[key] = [(q.get("name") or f"{q['bus']}[{q.get('bit', 0)}]", q["layer"], q["x"], q["y"])
                               for q in js]
        pins += _PIN_CACHE[key]
    return pins


def check_taps_cores(P, R, plan_dir=None, evidence=None):
    """clock.taps[] inside the type outline, unique names; hard_cores[]: pins land on the plan tracks after
    origin + track_offset and the core orient, in the type frame AND in every placed instance's die frame (MX/MY)."""
    out = dict(taps=0, hard_cores=0, core_pins=0, core_pins_off_track=0, types_no_cells=0, over_cap_no_cores=0)
    import cells as CE
    est, out["cell_sources"] = CE.estimate(P.raw, plan_dir, evidence or ())
    no_cells = []
    for tn, t in P.types.items():
        w, h = t["outline_um"]
        nc, basis = est.get(tn, (None, None))
        if nc is None:
            out["types_no_cells"] += 1
            no_cells.append(tn)
        elif nc > CORE_CELLS_MAX and not t.get("hard_cores"):
            out["over_cap_no_cores"] += 1
            R.err("hard_cores", f"type {tn}: {nc} cells ({basis}) > {CORE_CELLS_MAX} and no hard_cores[] (outline, "
                  "pins, track_offset): a type this large is built from hardened cores (COORD 10-23 CORE-KS)",
                  type=tn)
        ck = t.get("clock", {})
        names = set()
        for tp in ck.get("taps", []):
            out["taps"] += 1
            x, y = tp["xy"]
            if not (-EPS <= x <= w + EPS and -EPS <= y <= h + EPS):
                R.err("clock", f"type {tn}: clock tap {tp['name']} at ({x:g},{y:g}) outside the outline", type=tn)
            if tp["name"] in names:
                R.err("clock", f"type {tn}: duplicate clock tap {tp['name']}", type=tn)
            names.add(tp["name"])
        for hc in t.get("hard_cores", []):
            out["hard_cores"] += 1
            cw, chh = hc["outline_um"]
            o = hc.get("orient", "R0")
            ox, oy = hc["origin_um"]
            dx, dy = hc.get("track_offset_um", [0.0, 0.0])
            if abs(ox / P.grid - round(ox / P.grid)) > 1e-6 or abs(oy / P.grid - round(oy / P.grid)) > 1e-6:
                R.err("hard_cores", f"type {tn} core {hc['inst']}: origin {hc['origin_um']} not on the "
                      f"{P.grid:g}-um lattice (put the sub-lattice shift in track_offset_um)", type=tn)
            if max(abs(dx), abs(dy)) >= S.BASE_LATTICE_UM:
                R.err("hard_cores", f"type {tn} core {hc['inst']}: track_offset {hc.get('track_offset_um')} is not a "
                      "sub-lattice shift", type=tn)
            X0, Y0 = ox + dx, oy + dy
            if X0 < -EPS or Y0 < -EPS or X0 + cw > w + EPS or Y0 + chh > h + EPS:
                R.err("hard_cores", f"type {tn} core {hc['inst']}: placed box outside the type outline", type=tn)
            try:
                pins = core_pins(hc, plan_dir)
            except (OSError, ValueError, KeyError) as e:
                pins = [(p_["name"], p_["layer"], *p_["xy"]) for p_ in hc.get("pins", [])]
                R.err("hard_cores", f"type {tn} core {hc['inst']}: pins_file {hc['pins_file']}: {e}", type=tn)
            if not pins:
                R.err("hard_cores", f"type {tn} core {hc['inst']}: no pins listed (pins / pins_file): the core pins "
                      "must be proven on the kit tracks", type=tn)
            if hc.get("straps") or hc.get("parent_id_straps"):
                from parent_id_straps import validate_parent_id_straps
                try:
                    validate_parent_id_straps(hc, pins=pins)
                except ValueError as e:
                    R.err("hard_cores", f"type {tn} core {hc['inst']}: {e}", type=tn)
            insts = [n for n, p_ in P.parts.items() if p_["type"] == tn]
            bad = 0
            for nm, ln, x, y in pins:
                out["core_pins"] += 1
                L = P.layers.get(ln)
                if L is None or ln == "M1":
                    continue
                tx, ty = _orient_pt(o, cw, chh, x, y)
                tx, ty = X0 + tx, Y0 + ty
                # M2/M3 keep the platform cell-access tracks: checked in the type frame and unmirrored instances
                # only (a mirrored instance's die frame is not their lattice; CORE-KS false M3 errors)
                frames = [("type", tx, ty)] + [(pi, *P.to_die(pi, (tx, ty))) for pi in insts
                                               if ln not in MIRROR_SKIP or P.parts[pi].get("orient", "R0") == "R0"]
                for fr, fx, fy in frames:
                    c = fx if L["dir"] == "V" else fy
                    if not on_track(c, L):
                        bad += 1
                        if bad <= 5:
                            R.err("hard_cores", f"type {tn} core {hc['inst']} pin {nm} {ln}: "
                                  f"{'x' if L['dir'] == 'V' else 'y'} {c:.4f} off the plan track "
                                  f"(offset {L['offset_um']:g}, pitch {L['pitch_um']:g}) in the {fr} frame", type=tn)
                        break
            out["core_pins_off_track"] += bad
            if bad > 5:
                R.err("hard_cores", f"type {tn} core {hc['inst']}: {bad} pins off the plan tracks", type=tn)
    out["no_cells"] = no_cells
    if False and out["types_no_cells"]:
        R.warn("hard_cores", f"{out['types_no_cells']} types without a cell estimate (type.cells, contents[].cells or "
               f"a cells.py evidence file): the > {CORE_CELLS_MAX}-cell hard-core rule is unchecked for them: "
               f"{', '.join(no_cells[:30])}{' ...' if len(no_cells) > 30 else ''}")
    return out


# ------------------------------------------------------------------------- core pin face form + island ft rows
# CLOCK-KV hm_r26q3 (COORD 10-27): two plan-view rules every hardened-core kit relies on.
#  core_pin_form: a face of one pin view uses ONE pin form: edge (pin centre on the outline, d = 0) or centre
#    (pin centre inside, 0 < d < 0.5 um, the kit's half-pin form).  A mixed face (kv3_head_eighth_e1 N:
#    strap_bsel[0..1] at y = 216.000 beside the 215.904 bus pins) is an ERROR.
#  island_ft_rows: every island_ft arc rect of every pin view (12.2a1 in-core clock islands) sits on a real
#    std-cell row and site of the kit core area (CORE_AREA = outline inset 4.32, rows 0.27, sites 0.054) in the
#    view's own frame AND in its R0/MX/MY/R180 images, is n x cell-width by one row, is one of the plan
#    clock.mesh.core_islands rects of its module, and its ports are interior M5 pins on the M5 tracks on the row.
CORE_INSET_UM, CORE_ROW_UM, CORE_SITE_UM = 4.32, 0.27, 0.054
CORE_M5 = dict(offset_um=0.024, pitch_um=0.048)
FT_CELL_W = {"BUFx24_ASAP7_75t_R": 1.62}
PIN_FORM_D_MAX = 0.5


def _pin_views(P, plan_dir):
    """{pins_file: (module, (w, h), doc)} of every hard core that names a pins_file (one entry per file)."""
    out = {}
    for t in P.types.values():
        for hc in t.get("hard_cores", []):
            pf = hc.get("pins_file")
            if pf and pf not in out:
                try:
                    doc = json.loads((Path(plan_dir or ".") / pf).read_text())
                except (OSError, ValueError):
                    continue          # check_taps_cores reports unreadable pin files
                out[pf] = (hc.get("module"), tuple(hc["outline_um"]), doc if isinstance(doc, dict) else {"pins": doc})
    return out


def _img_rect(o, w, h, r):
    x0, y0, x1, y1 = r
    xs = (x0, x1) if o in ("R0", "MX") else (w - x1, w - x0)
    ys = (y0, y1) if o in ("R0", "MY") else (h - y1, h - y0)
    return (xs[0], ys[0], xs[1], ys[1])


def check_core_pin_forms(P, R, plan_dir=None, views=None):
    out = dict(views=0, faces=0, mixed=0)
    for pf, (mod, (w, h), doc) in sorted((views or _pin_views(P, plan_dir)).items()):
        out["views"] += 1
        forms = {}
        for q in doc.get("pins", []):
            x, y = q["x"], q["y"]
            d, face = min((h - y, "N"), (y, "S"), (w - x, "E"), (x, "W"))
            if d < -EPS or d >= PIN_FORM_D_MAX:
                continue
            form = "edge" if d <= 1e-4 else "centre"
            forms.setdefault(face, {}).setdefault(form, []).append(q.get("name"))
        for face, fm in sorted(forms.items()):
            out["faces"] += 1
            if len(fm) == 1 and "edge" in fm and any("centre" in f2 for f2 in forms.values()) \
                    and not all(str(n).startswith("strap_") for n in fm["edge"]):
                # data-pin faces of mixed-form views (qkd_hr_* edge N/S + centre W): kitted as is -> WARNING only
                R.warn("core_pin_form", f"{pf} ({mod}) face {face}: {len(fm['edge'])} edge-form pins in a view with "
                       f"centre-form faces")
                continue
            if len(fm) == 1 and "edge" in fm and any("centre" in f2 for f2 in forms.values()):
                # COORD 10-27 (hm_r26q4): one VIEW uses one form.  In a centre-form view (0 < d < 0.5 um, e.g. 0.096 /
                # 215.904, what the kits emit) a face whose only pins are edge form (x=0 / y=h; e.g. the e0/e2/e6
                # strap faces) breaks PREFLIGHT pins_canonical against the kits.  All-edge views (qkd_hr_*) stay legal.
                out["edge_only"] = out.get("edge_only", 0) + 1
                R.err("core_pin_form", f"{pf} ({mod}) face {face}: {len(fm['edge'])} edge-form pins and no centre-form "
                      f"pin; plan pins use the centre form ({', '.join(fm['edge'][:6])})")
                continue
            if len(fm) > 1:
                out["mixed"] += 1
                few = min(fm, key=lambda k: len(fm[k]))
                R.err("core_pin_form", f"{pf} ({mod}) face {face}: {len(fm['edge'])} edge-form + {len(fm['centre'])} "
                      f"centre-form pins; one face uses one form (minority {few}: {', '.join(fm[few][:6])})")
    return out


def check_island_ft_rows(P, R, plan_dir=None, views=None):
    out = dict(views=0, arcs=0, bad=0)
    ci = (P.clock.get("mesh") or {}).get("core_islands") or {}
    for pf, (mod, (w, h), doc) in sorted((views or _pin_views(P, plan_dir)).items()):
        isl = doc.get("island_ft")
        if not isl:
            continue
        out["views"] += 1
        plan_rects = [tuple(round(v, 4) for v in r) for r in (ci.get(mod) or {}).get("rects_um", [])]
        pins = {q["name"]: q for q in doc.get("pins", [])}
        x0c, y0c, x1c, y1c = CORE_INSET_UM, CORE_INSET_UM, w - CORE_INSET_UM, h - CORE_INSET_UM
        for a in isl.get("arcs") or []:
            out["arcs"] += 1
            bad = []
            r = tuple(float(v) for v in a["rect_um"])
            n, cw = a.get("cells"), FT_CELL_W.get(a.get("master"))
            if cw is None or not isinstance(n, int) or abs((r[2] - r[0]) - n * cw) > 1e-4 \
                    or abs((r[3] - r[1]) - CORE_ROW_UM) > 1e-4:
                bad.append(f"not {n} x {a.get('master')} by one row")
            for o in ("R0", "MX", "MY", "R180"):
                q = _img_rect(o, w, h, r)
                if q[0] < x0c - EPS or q[1] < y0c - EPS or q[2] > x1c + EPS or q[3] > y1c + EPS:
                    bad.append(f"{o} image {fmt_rect(q)} outside the core area"); continue
                if not on_grid(round(q[1] - y0c, 6), CORE_ROW_UM) or not on_grid(round(q[0] - x0c, 6), CORE_SITE_UM):
                    bad.append(f"{o} image {fmt_rect(q)} off the std row/site grid")
            if cw:
                cells = [tuple(round(v, 4) for v in (r[0] + j * cw, r[1], r[0] + (j + 1) * cw, r[3]))
                         for j in range(n or 0)]
                if plan_rects and not all(c in plan_rects for c in cells):
                    bad.append(f"cells {cells} not in clock.mesh.core_islands.{mod}.rects_um")
            for nm in (a.get("source"), a.get("sink")):
                p = pins.get(nm)
                if p is None:
                    bad.append(f"port {nm} missing"); continue
                if p["layer"] != "M5" or not on_track(p["x"], CORE_M5) or not (r[1] - EPS <= p["y"] <= r[3] + EPS):
                    bad.append(f"port {nm} {p['layer']} ({p['x']:g},{p['y']:g}) not an M5-track pin on the island row")
            if bad:
                out["bad"] += 1
                R.err("island_ft_rows", f"{pf} ({mod}) island_ft {a.get('source')} rect {fmt_rect(r)}: " + "; ".join(bad))
    return out


# ------------------------------------------------------------------------------------- hard-core face rule
_NORMAL = dict(N=(0.0, 1.0), S=(0.0, -1.0), E=(1.0, 0.0), W=(-1.0, 0.0))
FACE_AWAY_COS = -0.1     # a core port whose pins' mean best cos(face normal, direction to a partner) is below this
FACE_WARN_COS = 0.0      # FAILs; between the two (pins about perpendicular to the partner) it WARNs


def _core_face(o, x, y, cw, ch):
    """face of a core-frame pin, in the type frame after the core orient."""
    f = min([(x, "W"), (cw - x, "E"), (y, "S"), (ch - y, "N")])[1]
    if o in ("MX", "R180") and f in "NS":
        f = OPP[f]
    if o in ("MY", "R180") and f in "EW":
        f = OPP[f]
    return f


def _bus_bit_targets(P, tn):
    """{bus: {bit: (x, y)}} type-frame pin of every bit of the type's planned partition ports (schema port_pins of the
    first instance that carries the bus, die -> type frame); a bus whose pins cannot be placed is left out."""
    insts = {n for n, p_ in P.parts.items() if p_["type"] == tn}
    out = {}
    for pid, pr in P.ports.items():
        if "face" not in pr or "window_um" not in pr:
            continue
        for side in ("src", "dst"):
            e = pr[side]
            if e["part"] not in insts or e["bus"] in out:
                continue
            df = pr["face"] if side == "src" or pr["src"]["part"] == DIE_PART else OPP[pr["face"]]
            x0, y0, x1, y1 = P.rect(e["part"])
            try:
                pins = P.port_pins(pid)
            except (ValueError, KeyError):
                continue
            pts = {}
            for b, _ln, c in pins:
                dpt = dict(N=(c, y1), S=(c, y0), E=(x1, c), W=(x0, c))[df]
                pts[str(b)] = P.to_type(e["part"], dpt)
            out[e["bus"]] = pts
    return out


def _bus_targets(P, tn):
    """{bus: (x, y) type-frame point on the partition face that carries it}: the type's bus face/window when
    declared, else the first planned port of an instance of the type (die window -> type frame)."""
    t = P.types[tn]
    w, h = t["outline_um"]

    def pt(face, a, b):
        m = 0.5 * (a + b)
        return dict(N=(m, h), S=(m, 0.0), E=(w, m), W=(0.0, m))[face]
    out = {}
    for b in t.get("buses", []):
        if "face" in b and "window_um" in b:
            out[b["name"]] = (b["face"], pt(b["face"], *b["window_um"]))
    insts = {n for n, p_ in P.parts.items() if p_["type"] == tn}
    for pr in P.ports.values():
        if "face" not in pr or "window_um" not in pr:
            continue
        for side in ("src", "dst"):
            e = pr[side]
            if e["part"] not in insts or e["bus"] in out:
                continue
            df = pr["face"] if side == "src" or pr["src"]["part"] == DIE_PART else OPP[pr["face"]]
            a, b_ = pr["window_um"]
            x0, y0, x1, y1 = P.rect(e["part"])
            m = 0.5 * (a + b_)
            dpt = dict(N=(m, y1), S=(m, y0), E=(x1, m), W=(x0, m))[df]
            tf = P.type_face(e["part"], df)
            out[e["bus"]] = (tf, P.to_type(e["part"], dpt))
    return out


def best_face(dirs):
    """core face (type frame) that best faces a set of partner directions [(what, ux, uy)] (re-pin hint)."""
    return max("NSEW", key=lambda f: sum(_NORMAL[f][0] * ux + _NORMAL[f][1] * uy for _, ux, uy in dirs))


def load_core_conns(plan_dir=None, path=None):
    """optional sidecar {type: {core inst: {core port: ["bus:<type bus>" | "core:<inst>" | "leaf:<content inst>" |
    "face:<N|S|E|W>", ...]}}} (default PLANDIR/core_conns.json): core connectivity the plan JSON does not carry
    (cores nested inside a content leaf, e.g. S81 frame qbanks; KV head cores), written by the binder / plan owner."""
    f = Path(path) if path else Path(plan_dir or ".") / "core_conns.json"
    if path is not None and not f.is_file():
        raise FileNotFoundError(f"explicit --core-conns file does not exist: {f}")
    return json.loads(f.read_text()) if f.is_file() else {}


def check_core_faces(P, R, plan_dir=None, conns_file=None, max_msgs=5, per_core=None, collect=None):
    """Connectivity-aware hard-core face rule (GEOM-REVIEW face rule; COORD 10-23 PLAN-TOOL4).

    Every hard-core pin group (core port) that connects to a partition face or to another core / placed leaf must
    sit on a core face that faces a partner.  Connectivity: type.buses[].leaf "<inst>.<port>", contents[].bind
    "bus:/epoch:<bus>" and "net:<net>" (leaf-to-leaf), and the core_conns.json sidecar.  A core matches a leaf inst
    when equal or split from it ("<leaf>_<piece>").  Score, in the type frame: per pin, the best cosine over the
    port's partners between the pin's face normal and the direction from the core centre to the partner (partition
    face: the bus window centre; core / leaf: its centre); the port FAILs when the mean over its pins is < 0
    (most pins on the far side: the route wraps the core).  Cores with no known connectivity are counted
    (unchecked) and WARNed per type.  `collect` (optional list, DIE-HBM-15 core_face_repin.py) receives one record per
    scored port {type, inst, port, faces, dirs, mean}; it changes nothing else."""
    out = dict(groups=0, groups_away=0, pins=0, pins_away=0, types_away=0, cores=0, cores_unchecked=0)
    side = load_core_conns(plan_dir, conns_file)
    for tn, t in P.types.items():
        hcs = t.get("hard_cores", [])
        if not hcs:
            continue
        w, h = t["outline_um"]
        bt = None
        boxes = {}
        for hc in hcs:
            cw, ch = hc["outline_um"]
            dx, dy = hc.get("track_offset_um", [0.0, 0.0])
            boxes[hc["inst"]] = (hc["origin_um"][0] + dx + cw / 2, hc["origin_um"][1] + dy + ch / 2)
        cent = dict(boxes)
        for c in t.get("contents", []):
            if c["inst"] not in cent and "origin_um" in c and "outline_um" in c:
                cent[c["inst"]] = (c["origin_um"][0] + c["outline_um"][0] / 2,
                                   c["origin_um"][1] + c["outline_um"][1] / 2)
        ist_bus = [e for e in t.get("internal_stations", [])
                   if str(e.get("conn", "")).startswith("bus:") and e.get("regs_um")]
        # Broadcast buses may have distinct final relay legs for each capture core.
        # Unscoped legacy entries retain their previous last-entry behavior.
        ist_last = {e["conn"][4:]: tuple(e["regs_um"][-1]) for e in ist_bus
                    if not e.get("capture") or str(e["capture"]).startswith("face bus ")}
        ist_capture = {(e["conn"][4:], str(e["capture"])): tuple(e["regs_um"][-1])
                       for e in ist_bus if e.get("capture") and not str(e["capture"]).startswith("face bus ")}
        conns = {}          # (leaf inst, leaf port) -> [(kind, name)]
        for b in t.get("buses", []):
            if b.get("leaf") and "." in b["leaf"]:
                li, lp = b["leaf"].split(".", 1)
                conns.setdefault((li, lp), []).append(("bus", b["name"]))
        net_ends = {}
        for c in t.get("contents", []):
            for lp, v in c.get("bind", {}).items():
                k, _, nm = v.partition(":")
                if k in ("bus", "epoch") and nm:
                    conns.setdefault((c["inst"], lp), []).append(("bus", nm))
                elif k == "net" and nm:
                    conns.setdefault((c["inst"], lp), []).append(("net", nm))
                    net_ends.setdefault(nm, set()).add(c["inst"])
        for ci, ports in side.get(tn, {}).items():
            for lp, lst in ports.items():
                for v in lst:
                    k, _, nm = v.partition(":")
                    conns.setdefault((ci, lp), []).append((k, nm))
        bad_t = unchecked = 0
        for hc in hcs:
            ci = hc["inst"]
            out["cores"] += 1
            mine = [(lp, tg) for (li, lp), tg in conns.items() if li == ci or ci.startswith(li + "_")]
            if not mine:
                unchecked += 1
                continue
            try:
                pins = core_pins(hc, plan_dir)
            except (OSError, ValueError, KeyError):
                continue
            cw, ch = hc["outline_um"]
            o = hc.get("orient", "R0")
            cx, cy = boxes[ci]
            by_base = {}
            for nm, _ln, x, y in pins:
                by_base.setdefault(re.sub(r"\[\d+\]$", "", nm), []).append(_core_face(o, x, y, cw, ch))
            ports = {}
            for lp, tg in mine:
                ports.setdefault(lp, []).extend(tg)
            for lp, tg in ports.items():
                faces = by_base.get(lp)
                if not faces:
                    continue
                pts = []
                for kind, nm in tg:
                    if kind == "bus":
                        if bt is None:
                            bt = _bus_targets(P, tn)
                        if (nm, ci + "." + lp) in ist_capture:
                            pts.append((f"station {nm} -> {ci}.{lp}", ist_capture[(nm, ci + "." + lp)]))
                        elif (nm, ci) in ist_capture:
                            pts.append((f"station {nm} -> {ci}", ist_capture[(nm, ci)]))
                        elif nm in ist_last:
                            # R3-INTERNAL: a bus with FIRM internal stations reaches the core from its last station
                            # (regs_um[-1], the register next to the core pin), not from the face window
                            pts.append((f"station {nm}", ist_last[nm]))
                        elif nm in bt:
                            pts.append((f"face {bt[nm][0]} ({nm})", bt[nm][1]))
                    elif kind == "net":
                        pts += [(f"{oi} (net {nm})", cent[oi]) for oi in sorted(net_ends.get(nm, ()))
                                if oi != ci and not ci.startswith(oi + "_") and oi in cent]
                    elif kind in ("core", "leaf") and nm in cent and nm != ci:
                        pts.append((nm, cent[nm]))
                    elif kind == "face" and nm in _NORMAL:
                        pts.append((f"face {nm}", dict(N=(cx, h), S=(cx, 0.0), E=(w, cy), W=(0.0, cy))[nm]))
                dirs = []
                for what, (tx, ty) in pts:
                    d = math.hypot(tx - cx, ty - cy)
                    if d > 1e-6:
                        dirs.append((what, (tx - cx) / d, (ty - cy) / d))
                if not dirs:
                    continue
                best = {f: max(_NORMAL[f][0] * ux + _NORMAL[f][1] * uy for _, ux, uy in dirs) for f in set(faces)}
                cs = [best[f] for f in faces]
                away = sum(1 for c_ in cs if c_ < -1e-9)
                mean = sum(cs) / len(cs)
                out["groups"] += 1
                out["pins"] += len(cs)
                out["pins_away"] += away
                if collect is not None:
                    collect.append(dict(type=tn, inst=ci, port=lp, faces=list(faces), dirs=dirs, mean=mean))
                if per_core is not None:        # CLOCK-KV-R12: per-core away-pin tally (core_pins_orient.py)
                    pc = per_core.setdefault((tn, ci), [0, 0])
                    pc[0] += away
                    pc[1] += 1 if mean < FACE_AWAY_COS else 0
                if mean < FACE_WARN_COS:
                    bf = best_face(dirs)
                    part = ", ".join(sorted({wh for wh, _, _ in dirs})[:3]) + (" ..." if len(dirs) > 3 else "")
                    msg = (f"type {tn} core {ci} port {lp}: {len(cs)} pins on face {'/'.join(sorted(set(faces)))} "
                           f"face away from its partner(s) {part}: mean cos {mean:+.2f}, {away} pins on the far "
                           f"side (re-pin to face {bf})")
                    if mean >= FACE_AWAY_COS:
                        out["groups_side"] = out.get("groups_side", 0) + 1
                        if out["groups_side"] <= 50:
                            R.warn("core_faces", msg + " [about perpendicular: WARN]", type=tn)
                        continue
                    out["groups_away"] += 1
                    bad_t += 1
                    if bad_t <= max_msgs:
                        R.err("core_faces", msg, type=tn)
        if bad_t > max_msgs:
            R.err("core_faces", f"type {tn}: {bad_t} core ports face away from their partners "
                  f"({bad_t - max_msgs} more not listed)", type=tn)
        if unchecked:
            R.warn("core_faces", f"type {tn}: {unchecked}/{len(hcs)} hard cores with no known connectivity (no "
                   "buses[].leaf / contents[].bind / core_conns.json entry): face rule unchecked for them", type=tn)
        out["cores_unchecked"] += unchecked
        out["types_away"] += bool(bad_t)
    return out


# ------------------------------------------------------------------------------------- plan completeness
COMPLETE_FIELDS = ("cells", "track_offset", "clock_method", "common_latency", "insertion_target", "reset_sync",
                   "face_flop", "internal_station")


def _box_dist(pt, box):
    """Manhattan distance from a point to a box (x0, y0, x1, y1); 0 inside."""
    x, y = pt
    return max(box[0] - x, 0, x - box[2]) + max(box[1] - y, 0, y - box[3])


def _hops_ok(a, regs, b, smax):
    pts = [tuple(a)] + [tuple(r) for r in regs] + [tuple(b)]
    return max(abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(pts, pts[1:])) <= smax + EPS


def check_completeness(P, R, no_cells=(), max_msgs=5, side=None, plan_dir=None):
    """PLAN COMPLETENESS (COORD 10-23 ~20:00): G0 is a completeness check; a missing field is an ERROR.
    Per partition type (hard IP types: cells / clock / reset / face flops not required):
      cells            a cell estimate (type.cells, contents[].cells or cells.py evidence)
      track_offset     every hard_cores[] entry declares track_offset_um (pins on tracks / > 400k: hard_cores check)
      clock_method     type.clock with tap_um, taps[] or tap_mode
      insertion_target a type clock.insertion_ps equal to the die common latency (one die-wide target, R4 b)
      reset_sync       type.reset (one async-assert / sync-deassert synchronizer)
      face_flop        every type bus is carried by a planned port with face geometry (face + window + layers), so
                       the R2 face flop is FIRM at its pin (the schema pass already refuses unbound buses and ports
                       without geometry; this re-counts them for the completeness table)
      internal_station every estimated internal reg-reg connection > ft_station_max_um (face window -> leaf / core
                       box, core <-> core net) has internal_stations[] whose hops are all <= the limit (R3-INTERNAL)
                       S81 10-24 (coordinator ruling (a), R3 inside hardened types): with budgets.core_internal_reach_um
                       set, the types with declared core connectivity (core_conns.json sidecar) use that reach for their
                       internal_stations[] hops, and every declared core port bundle -- bus window -> core box, core box
                       -> partner core box (lower bounds) -- longer than it needs an entry (conn "bus:<bus>" with capture
                       "<core>.<port>", or conn "core:<core>.<port>|core:<partner>" either way round)
                       S81-CORES-R25 10-27 (COORD ruling: pin-to-pin, not box-to-box): where the core has plan pins
                       (pins[] / pins_file) the length is measured from its PINS (origin + track_offset + orient), per
                       bit: bus window point -> each pin of the port; core -> partner "core:<inst>.<port>" = per-bit pin
                       -> partner pin Manhattan (max over common bits); a partner named without a port = pin -> partner
                       box.  The box distance stays the floor, so a pin-aware length is never shorter than the old one.
                       A bus target is measured per bit (the bus's planned partition pin, schema port_pins -> core
                       port bit of the same index) when the port covers all bus bits but at most max(2, width/32)
                       side bits (valid, tag); a port that is a slice of a wider bus has no known bit map -> pin ->
                       window centre.
                       An entry covers a core -> bus bundle with conn "bus:<bus>" and capture OR launch "<core>.<port>".
    Die: clock.common_latency_ps (R4 owner rule)."""
    miss = {f: 0 for f in COMPLETE_FIELDS}
    smax0 = smax = station_max(P)
    creach = P.budgets.get("core_internal_reach_um")
    cside = side or {}
    n_msg = defaultdict(int)

    def bad(field, tn, msg):
        miss[field] += 1
        n_msg[field] += 1
        if True:
            R.err("complete", f"[{field}] " + (f"type {tn}: " if tn else "") + msg, type=tn, field=field)
    raw_ck = P.raw.get("clock", {})
    common = raw_ck.get("common_latency_ps")
    if common is None:
        bad("common_latency", None, "die clock.common_latency_ps missing (R4: one die-wide common latency target "
            "every partition balances its face-flop insertion to; vclk latency of the IO SDC)")
    no_cells = set(no_cells)
    ends = defaultdict(set)              # type -> buses used by a port
    for pr in P.ports.values():
        for side in ("src", "dst"):
            e = pr[side]
            if e["part"] != DIE_PART and e["part"] in P.parts:
                ends[P.parts[e["part"]]["type"]].add((e["bus"], pr["id"], "face" in pr and "window_um" in pr
                                                      and "layers" in pr))
    for tn, t in P.types.items():
        hard = bool(t.get("hard"))
        if tn in no_cells and not hard:
            bad("cells", tn, "no cell estimate (type.cells, contents[].cells or a cells.py evidence file)")
        for hc in t.get("hard_cores", []):
            if "track_offset_um" not in hc:
                bad("track_offset", tn, f"hard core {hc['inst']}: no track_offset_um (state [0, 0] if on the plan "
                    "tracks)")
        if hard:
            continue
        ck = t.get("clock") or {}
        if not ({"tap_um", "taps", "tap_mode"} & set(ck)):
            bad("clock_method", tn, "no clock method (clock.tap_um, clock.taps[] or clock.tap_mode)")
        if common is not None and "insertion_ps" in ck and abs(float(ck["insertion_ps"]) - float(common)) > EPS:
            bad("insertion_target", tn, f"clock.insertion_ps {ck['insertion_ps']:g} != die common latency "
                f"{float(common):g} (R4: one die-wide target)")
        if "reset" not in t:
            bad("reset_sync", tn, "no reset synchronizer entry (one per partition)")
        used = {bus for bus, _pid, _ok in ends.get(tn, ())}
        nf = [pid for bus, pid, ok in ends.get(tn, ()) if not ok] + \
             [b["name"] for b in t.get("buses", []) if b["name"] not in used]
        if nf:
            bad("face_flop", tn, f"{len(nf)} bus(es) with no planned port / face geometry, e.g. {nf[0]}: the R2 "
                "face flop has no FIRM pin site")
        # internal reg-reg length estimate (lower bound: point to box / box to box, Manhattan)
        boxes = {}
        for hc in t.get("hard_cores", []):
            dx, dy = hc.get("track_offset_um", [0.0, 0.0])
            x0, y0 = hc["origin_um"][0] + dx, hc["origin_um"][1] + dy
            boxes[hc["inst"]] = (x0, y0, x0 + hc["outline_um"][0], y0 + hc["outline_um"][1])
        for c in t.get("contents", []):
            if c["inst"] not in boxes and "origin_um" in c and "outline_um" in c:
                x0, y0 = c["origin_um"]
                boxes[c["inst"]] = (x0, y0, x0 + c["outline_um"][0], y0 + c["outline_um"][1])
        if not boxes:
            continue
        smax = float(creach) if creach and tn in cside else smax0
        ist = t.get("internal_stations", [])
        for e in ist:
            if not _hops_ok(e["from_um"], e["regs_um"], e["to_um"], smax):
                bad("internal_station", tn, f"internal_stations {e.get('conn', e['from_um'])}: a hop > {smax:g} um")
        conns = {e.get("conn") for e in ist if e.get("conn")}
        hcs = {hc["inst"]: hc for hc in t.get("hard_cores", [])}
        cpin = {}

        def port_pins(ci, lp):
            """{bit: (x, y)} of core ci's port lp in the type frame; None when the core has no plan pins."""
            if ci not in cpin:
                hc = hcs.get(ci)
                tab = None
                if hc is not None and (hc.get("pins") or hc.get("pins_file")):
                    try:
                        raw = core_pins(hc, plan_dir)
                    except (OSError, ValueError, KeyError):
                        raw = []
                    if raw:
                        tab = defaultdict(dict)
                        cw_, ch_ = hc["outline_um"]
                        o_ = hc.get("orient", "R0")
                        dx_, dy_ = hc.get("track_offset_um", [0.0, 0.0])
                        for nm_, _ln, x_, y_ in raw:
                            pn, _, bit = nm_.partition("[")
                            tx, ty = _orient_pt(o_, cw_, ch_, x_, y_)
                            tab[pn][bit.rstrip("]")] = (hc["origin_um"][0] + dx_ + tx, hc["origin_um"][1] + dy_ + ty)
                cpin[ci] = tab
            tab = cpin[ci]
            return None if tab is None or lp not in tab else tab[lp]

        def covered(key, a, b_box):
            if key in conns:
                return True
            return any(abs(e["from_um"][0] - a[0]) + abs(e["from_um"][1] - a[1]) <= 50.0
                       and _box_dist(e["to_um"], b_box) <= 50.0 for e in ist)
        bt = None
        nets = defaultdict(set)
        for c in t.get("contents", []):
            for lp, v in c.get("bind", {}).items():
                if v.startswith("net:"):
                    nets[v[4:]].add(c["inst"])
        todo = []
        for b in t.get("buses", []):
            lf = b.get("leaf") or ""
            li = lf.split(".")[0]
            cand = [ci for ci in boxes if ci == li or ci.startswith(li + "_")] if li else []
            if not cand:
                continue
            if bt is None:
                bt = _bus_targets(P, tn)
            if b["name"] not in bt:
                continue
            a = bt[b["name"]][1]
            d = min(_box_dist(a, boxes[ci]) for ci in cand)
            if d > smax and not covered(f"bus:{b['name']}", a, boxes[cand[0]]) and not covered(lf, a, boxes[cand[0]]):
                todo.append((f"bus {b['name']} (face window -> {lf})", d))
        for nm, insts in nets.items():
            ins = sorted(i for i in insts if i in boxes)
            for i, x in enumerate(ins):
                for y in ins[i + 1:]:
                    bx, by = boxes[x], boxes[y]
                    d = max(bx[0] - by[2], by[0] - bx[2], 0) + max(bx[1] - by[3], by[1] - bx[3], 0)
                    if d > smax and f"{x}|{y}" not in conns and f"{y}|{x}" not in conns:
                        todo.append((f"net {nm} ({x} <-> {y})", d))
        if creach and tn in cside:
            ents = {(e.get("conn"), e.get("capture")) for e in ist} | {(e.get("conn"), e.get("launch")) for e in ist}
            bbt = None
            for ci, ports in cside[tn].items():
                if ci not in boxes:
                    continue
                for lp, tgs in ports.items():
                    for tg in tgs:
                        kd, _, nm = tg.partition(":")
                        if kd == "bus":
                            if bt is None:
                                bt = _bus_targets(P, tn)
                            if nm not in bt:
                                continue
                            d = _box_dist(bt[nm][1], boxes[ci])
                            pp = port_pins(ci, lp)
                            if pp:
                                if bbt is None:
                                    bbt = _bus_bit_targets(P, tn)
                                bq = bbt.get(nm) or {}
                                if bq and set(pp) <= set(bq) and len(bq) - len(pp) <= max(2, len(pp) // 32):
                                    d = max(d, max(abs(v[0] - bq[k][0]) + abs(v[1] - bq[k][1]) for k, v in pp.items()))
                                else:
                                    q = bt[nm][1]
                                    d = max(d, max(abs(v[0] - q[0]) + abs(v[1] - q[1]) for v in pp.values()))
                            ok = (f"bus:{nm}", f"{ci}.{lp}") in ents
                        elif kd == "core" and (nm in boxes or nm.rpartition(".")[0] in boxes) and nm != ci:
                            np_ = None
                            if nm not in boxes:
                                nm, _, np_ = nm.rpartition(".")
                            if nm == ci:
                                continue
                            bx, by = boxes[ci], boxes[nm]
                            d = max(bx[0] - by[2], by[0] - bx[2], 0) + max(bx[1] - by[3], by[1] - bx[3], 0)
                            pa = port_pins(ci, lp)
                            pb = port_pins(nm, np_) if np_ else None
                            common = set(pa) & set(pb) if pa and pb else set()
                            if common:
                                d = max(d, max(abs(pa[k][0] - pb[k][0]) + abs(pa[k][1] - pb[k][1]) for k in common))
                            elif pa:
                                d = max(d, max(_box_dist(v, by) for v in pa.values()))
                            ok = any(c_ == f"core:{ci}.{lp}|core:{nm}" or
                                     (str(c_).startswith(f"core:{nm}.") and str(c_).endswith(f"|core:{ci}")
                                      and cap == f"{ci}.{lp}") for c_, cap in ents)
                        else:
                            continue
                        if d > smax + EPS and not ok:
                            todo.append((f"core bundle {ci}.{lp} -> {tg}", d))
        for what, d in todo:
            bad("internal_station", tn, f"internal {what} >= {d:.0f} um > {smax:g} um with no internal_stations[] "
                "entry (R3-INTERNAL: FIRM plan stations)")
    if any(miss.values()):
        R.warn("complete", "missing-field counts: " + ", ".join(f"{k} {v}" for k, v in miss.items() if v))
    return miss


# ------------------------------------------------------------------------------------------------------ types
def check_die_io(P, R):
    """COORD 10-23 (S81-P5): every off-die port lands in a declared pad / bump window over its host partition."""
    io = P.die.get("io")
    die_ports = {pid: pr for pid, pr in P.ports.items() if DIE_PART in (pr["src"]["part"], pr["dst"]["part"])}
    if not io:
        if die_ports:
            R.warn("die_io", f"{len(die_ports)} die IO ports ({sum(int(p['width']) for p in die_ports.values())} b) "
                   "and no die.io pad / bump windows: off-die pads (SerDes PMA, HBM PHY memory side, host) unplanned")
        return dict(windows=0, ports=len(die_ports))
    seen = {}
    for w in io:
        x0, y0, x1, y1 = w["rect_um"]
        if not (0 <= x0 < x1 <= P.W + EPS and 0 <= y0 < y1 <= P.H + EPS):
            R.err("die_io", f"io window {w['name']}: rect {w['rect_um']} outside the die")
        if w["part"] not in P.parts:
            R.err("die_io", f"io window {w['name']}: unknown host partition {w['part']}")
            continue
        px0, py0, px1, py1 = P.rect(w["part"])
        if x0 < px0 - EPS or y0 < py0 - EPS or x1 > px1 + EPS or y1 > py1 + EPS:
            R.err("die_io", f"io window {w['name']}: not inside its host partition {w['part']}")
        bits = 0
        for pid in w.get("ports", []):
            pr = P.ports.get(pid)
            if pr is None or pid not in die_ports:
                R.err("die_io", f"io window {w['name']}: {pid} is not a die IO port")
                continue
            if pid in seen:
                R.err("die_io", f"die IO port {pid} in two windows ({seen[pid]}, {w['name']})")
            seen[pid] = w["name"]
            end = pr["dst"]["part"] if pr["src"]["part"] == DIE_PART else pr["src"]["part"]
            if end != w["part"]:
                R.err("die_io", f"io window {w['name']}: port {pid} ends in {end}, not the host {w['part']}")
            bits += S.port_pins_count(pr)
        if bits > w["sites"]:
            R.err("die_io", f"io window {w['name']}: {bits} signal bits > {w['sites']} sites")
    for pid in sorted(set(die_ports) - set(seen)):
        R.err("die_io", f"die IO port {pid} ({die_ports[pid]['width']} b) has no pad / bump window (die.io)")
    return dict(windows=len(io), ports=len(die_ports), placed=len(seen))


def check_seams(P, R):
    """Seam-net invariant (COORD 10-23, OpenROAD abutment semantics): every inter-partition port bit is ONE 2-pin net,
    boundary flop to boundary flop -- one out bus (src boundary flop or ft station) to one in bus (dst boundary flop or
    station), same layer and coordinate on both sides, no fan-out, no die-port tap, no clock / reset kind.  Abutted
    seams must be pin-to-pin same-layer overlaps (dbNet::isConnectedByAbutment); planned-channel seams are the die
    route's only signal nets.  Returns per partition pair {abutted, channel} pin counts = the audit's expected nets."""
    seen = defaultdict(list)
    pairs = defaultdict(lambda: dict(abutted=0, channel=0))
    for pid, pr in P.ports.items():
        a, b = pr["src"]["part"], pr["dst"]["part"]
        if DIE_PART in (a, b):
            continue
        for side in ("src", "dst"):
            e = pr[side]
            seen[(e["part"], e["bus"])].append(pid)
            bus = P.buses(e["part"]).get(e["bus"], {})
            if bus.get("kind", "data") not in ("data", "ctl"):
                R.err("seams", f"port {pid}: {e['part']}.{e['bus']} is kind {bus.get('kind')}; a seam carries only "
                      "registered data / ctl (clock and reset come from the die spine taps)", port=pid)
        n = S.port_pins_count(pr)
        key = "|".join(sorted((a, b)))
        pairs[key]["channel" if P.channel_of(pid) else "abutted"] += n
    for (part, bus), pids in seen.items():
        if len(pids) > 1:
            R.err("seams", f"{part}.{bus} is an end of {len(pids)} seam ports {pids}: fan-out on a seam", part=part)
    tot = dict(abutted=sum(v["abutted"] for v in pairs.values()), channel=sum(v["channel"] for v in pairs.values()))
    return dict(nets=tot, pairs=dict(pairs))


def check_core_pg(P, R, plan_dir=None, strict=False, max_msgs=1000):
    """PG-CORECONN-2 (measured failure PG-CORECONN-1 10-28: hd_tile 10/10 core PG terms / 744 M5 pin shapes, S81
    col_h10_r2 134/134 / 21001 untouched by tile PG metal = physical open).  Every type that places hard-core /
    hardened macros (gen_phys.type_macros, PHY-domain macros excluded: their VDDPHY grid lands them) must set
    partition_types.<t>.core_pg_connect: true, and every such macro LEF must carry PG pin geometry gen_phys can land
    (gen_phys.core_pg_connect_layer: VDD+VSS on one of M4/M5/M6).  WARN by default (dies regenerate their kits first);
    ERROR with --strict-core-pg (COORD flips it once the dies have regenerated).  A LEF that does not resolve is a WARN
    (unchecked) in both modes."""
    import cores as C
    import gen_phys as GP
    emit = R.err if strict else R.warn
    out = dict(mode="ERROR" if strict else "WARN", types_with_macros=0, types_missing=[], macro_insts_missing=0,
               lefs_no_pg={}, lefs_unresolved=[], insts_no_pg=0,
               # hard_cores declared without a plan LEF (view attached at kit generation): not checkable here
               types_cores_without_lef=sorted(tn for tn, t in P.types.items()
                                              if any(not c.get("lef") for c in t.get("hard_cores", []))))
    n = [0]

    def say(f, msg, **kw):
        n[0] += 1
        if n[0] <= max_msgs:
            f("core_pg", msg, **kw)

    lef_ok = {}
    for tn in sorted(P.types):
        try:
            mac = GP.type_macros(P, tn)
        except (ValueError, KeyError, TypeError) as ex:
            say(R.warn, f"type {tn}: macros not enumerable ({ex}); core PG landing unchecked", type=tn)
            continue
        try:
            phy = {i for d in GP.phy_pg_domains(P, tn) for i in d[4]}
        except (ValueError, KeyError, TypeError):
            phy = set()
        mac = [m for m in mac if m[0] not in phy]
        if not mac:
            continue
        out["types_with_macros"] += 1
        ninst = sum(1 for p in P.parts.values() if p["type"] == tn)
        if not P.types[tn].get("core_pg_connect"):
            out["types_missing"].append(tn)
            out["macro_insts_missing"] += len(mac) * max(ninst, 1)
            say(emit, f"type {tn}: {len(mac)} placed hard-core macro(s) ({mac[0][0]} ...) without core_pg_connect: true "
                f"-- the kit PDN lands no via on their PG pins (physical PG open); set core_pg_connect and regenerate",
                type=tn)
        for inst, _mod, lef, *_ in mac:
            if lef not in lef_ok:
                cand = [C.resolve(lef)] + ([Path(plan_dir) / lef] if plan_dir and not Path(lef).is_absolute() else [])
                f = next((c for c in cand if c.is_file()), None)
                if f is None:
                    lef_ok[lef] = "unresolved"
                    out["lefs_unresolved"].append(lef)
                    say(R.warn, f"type {tn}: macro {inst} LEF {lef} not found; PG pin geometry unchecked", type=tn)
                else:
                    try:
                        GP.core_pg_connect_layer(f)
                        lef_ok[lef] = "ok"
                    except ValueError as ex:
                        lef_ok[lef] = str(ex)
                        out["lefs_no_pg"][lef] = 0
                        say(emit, f"type {tn}: macro {inst}: {ex}", type=tn)
            if lef in out["lefs_no_pg"]:
                out["lefs_no_pg"][lef] += max(ninst, 1)
                out["insts_no_pg"] += max(ninst, 1)
    if n[0] > max_msgs:
        R.warn("core_pg", f"... {n[0] - max_msgs} more core_pg findings (counts in summary.core_pg)")
    out["types_missing_n"] = len(out["types_missing"])
    out["types_cores_without_lef_n"] = len(out["types_cores_without_lef"])
    return out


def check_types(P, R):
    """type count, instances per type, and near-duplicate types: same outline + same bus interface (name, dir, width,
    kind) + same ft slots (faces, width, stations), differing only in pin offsets / contents.  Such types should be
    ONE type placed with orient / lattice shifts and pins declared on the type (type-frame windows)."""
    inst = defaultdict(int)
    for p in P.parts.values():
        inst[p["type"]] += 1
    sig = defaultdict(list)
    for tn, t in P.types.items():
        k = (tuple(t["outline_um"]),
             tuple(sorted((b["name"], b["dir"], b["width"], b.get("kind", "data")) for b in t.get("buses", []))),
             tuple(sorted((s["in_face"], s["out_face"], s["width"], s.get("stations", 1))
                          for s in t.get("ft_slots", []))))
        sig[k].append(tn)
    groups = [sorted(v) for v in sig.values() if len(v) > 1]
    for g in groups:
        R.warn("types", f"near-duplicate types {g[:8]}{'...' if len(g) > 8 else ''} ({len(g)}): same outline, buses and "
               "slots -- merge into one type (orient MX/MY/R180 + lattice origin, pins declared on the type)")
    no_geo = [tn for tn, t in P.types.items() if inst[tn] > 1 and any(
        "window_um" not in b for b in t.get("buses", []))]
    if no_geo:
        R.warn("types", f"{len(no_geo)} replicated types without type-frame pin windows on their buses (e.g. "
               f"{no_geo[:5]}): declare face/window_um/layers on the type so every instance shares one pin table")
    return dict(types=len(P.types), partitions=len(P.parts), singleton_types=sum(1 for v in inst.values() if v == 1),
                max_instances=max(inst.values()) if inst else 0, near_duplicate_groups=len(groups),
                near_duplicate_types=sum(len(g) for g in groups), mergeable_saving=sum(len(g) - 1 for g in groups))


def check_registered_pins(P, R, plan_dir=None):
    """REGISTERED-PIN hard partitions (COORD 10-25 11:31; hard_pinreg.py): declaration (hard type, single hard core,
    lib, no ft slots) and the lib claim (setup+hold on every input, clk->q on every output, every corner view).  Fails
    closed: an ERROR, the binder then refuses the type too."""
    import hard_pinreg as HP
    errs, summ = HP.check_plan(P.raw, (plan_dir,) if plan_dir else ())
    for e in errs:
        m = re.match(r"type (\S+):", e)
        R.err("hard_pinreg", e, **({"type": m.group(1)} if m else {}))
    return summ


def check_r8(P, R, plan_dir=None, groups=None, landing=None):
    """COORD R8 (r8.py) on BINDER2's bus groups.  No bus groups -> WARN (R8 cannot be judged without the bind)."""
    import r8
    pd = Path(plan_dir) if plan_dir else None
    if groups is None and pd is not None:
        groups = next((q for q in (pd / "bus_groups.json", pd / "r8" / "bus_groups.json", pd / "bind" / "bus_groups.json")
                       if q.exists()), None)
    if groups is None:
        if pd is None:
            return dict(checked=False)
        R.warn("r8", "R8 not checked: no as-built bus groups (BINDER2 bind.py bus_groups.json; pass --groups)")
        return dict(checked=False)
    bg = json.loads(Path(groups).read_text())
    if landing is None and pd is not None:
        hits = sorted(pd.glob(f"*/{P.name}_r8_landing.json")) + sorted(pd.glob(f"{P.name}_r8_landing.json"))
        landing = hits[0] if hits else None
    lmap = None
    if landing is not None:
        lmap, ljs = r8.load_landing(landing)
        if ljs.get("bus_groups_digest") != r8.bg_digest(bg):
            R.err("r8", f"R8 landing table {landing} was made from other bus groups (digest {ljs.get('bus_groups_digest')}"
                  f" != {r8.bg_digest(bg)}): regenerate with gen.py latency --groups")
        mode = dict(replica=ljs.get("replica", "all"), bus=ljs.get("bus", "part"))
    else:
        mode = dict(replica="all", bus="part")
    msgs, st = r8.check(bg, P.raw, lmap, **mode)
    for sev, m in msgs:
        (R.err if sev == "ERROR" else R.warn)("r8", m)
    st.update(checked=True, groups_file=str(groups), landing_file=str(landing) if landing else None)
    return st


# ------------------------------------------------------------------------------------------------------- run
def check_clock_mesh(R, builds):
    """--clock-build DIRs: fail-closed mesh continuity (die_clock_mesh.mesh_via_findings); a plain G0 ERROR."""
    import die_clock_mesh as DCM
    out = []
    for b in builds or []:
        p = Path(b) / "mesh.json"
        if not p.is_file():
            R.err("clock_mesh", f"--clock-build {b}: no mesh.json")
            out.append(dict(build=str(b), continuous=False, findings=["no mesh.json"]))
            continue
        M = json.loads(p.read_text())
        f_ = DCM.mesh_via_findings(M, b)
        for m_ in f_:
            R.err("clock_mesh", f"{b}: {m_}")
        out.append(dict(build=str(b), continuous=not f_, crossings={str(g["k"]): DCM.mesh_crossings(M, g)
                                                                     for g in DCM.mesh_regions(M)},
                        emitted=M["meta"].get("mesh_vias"), routed=DCM.routed_mesh_vias(b)[0], findings=f_))
    return out


KNOWN_ERRORS_FILE = "g0c_known_errors.json"


def apply_known_errors(R, plan_dir, completeness):
    """NAMED KNOWN-ERROR LIST (COORD 10-27 18:21, S81 gunit plan event): PLANDIR/g0c_known_errors.json
    {"owner": lane, "rule": ..., "errors": [{"check": c, "msg": exact finding text}, ...]} lists G0C ERRORs that a
    reviewed plan event newly exposed and that a named owner fixes.  Under --completeness each listed ERROR is reported
    as WARN "[KNOWN-ERROR <owner>] ..." (counted in summary.known_errors), so the check stays ON for every other
    finding.  The list may only shrink: an entry that no longer matches an ERROR is itself an ERROR (remove it), and
    the list must be empty before the die freeze.  No file = no effect."""
    f = Path(plan_dir) / KNOWN_ERRORS_FILE if plan_dir else None
    if not completeness or f is None or not f.is_file():
        return None
    K = json.loads(f.read_text())
    owner = K.get("owner")
    want = {(e["check"], e["msg"]) for e in K.get("errors", [])}
    hit = set()
    for i in R.items:
        key = (i["check"], i["msg"])
        if i["level"] == "ERROR" and key in want:
            i["level"] = "WARN"
            i["msg"] = f"[KNOWN-ERROR {owner}] " + i["msg"]
            i["known_error"] = True
            hit.add(key)
    stale = sorted(want - hit)
    for c, m in stale:
        R.err("known_errors", f"{KNOWN_ERRORS_FILE}: entry no longer matches an ERROR ({c}: {m[:160]}); remove it "
                              f"(the list may only shrink)")
    if want and not owner:
        R.err("known_errors", f"{KNOWN_ERRORS_FILE}: no owner named")
    return dict(file=str(f), owner=owner, listed=len(want), matched=len(hit), stale=len(stale))


def g0c_summary(P, R):
    """per partition type: G0C findings by check; types with none are G3-eligible (as far as the plan goes)."""
    by = {tn: defaultdict(int) for tn in P.types}
    die = defaultdict(int)
    for i in R.items:
        if not i.get("g0c"):
            continue
        tgt = by.get(i.get("type"), die)
        tgt[i["check"] + (f":{i['field']}" if i.get("field") else "")] += 1
    bad = {tn: dict(c) for tn, c in by.items() if c}
    return dict(types=len(P.types), clean=len(P.types) - len(bad), die_level=dict(die),
                g3_eligible=sorted(tn for tn in P.types if tn not in bad and not die), by_type=bad)


def run(raw, png=None, plan_dir=None, groups=None, landing=None, evidence=None, core_conns=None, completeness=False,
        clock_builds=None, core_macros=None, strict_core_pg=False):
    R = Report(completeness)
    io_src = "plan" if raw.get("die", {}).get("io") else None
    sc = Path(plan_dir) / "die_io.json" if plan_dir else None
    if io_src is None and sc is not None and sc.exists():
        # PLAN-TOOL5: die IO sidecar (die_io.py plan --out PLANDIR/die_io.json) when the plan has no die.io: it survives
        # the die generators' regeneration; a die.io list in the plan always wins
        raw = dict(raw, die=dict(raw["die"], io=json.loads(sc.read_text())))
        io_src = str(sc)
    errs = S.validate(raw)
    for e in errs:
        R.err("schema", e)
    if errs:
        return R, dict()
    # Plan-relative declarations (core pins_file for the reset wavefront) resolve against the plan's own directory.
    P = S.Plan(raw, Path(plan_dir) / "die_plan.json" if plan_dir else None)
    summ = dict(die=P.name, partitions=len(P.parts), types=len(P.types), ports=len(P.ports), lanes=len(P.lanes),
                bits=sum(p["width"] for p in P.ports.values()))
    if any(t.get("infra_ports") for t in P.types.values()):
        import infra_rtl as IR
        try:
            IR.die_lines(P)
        except (ValueError, KeyError, TypeError) as ex:
            R.err("infrastructure", str(ex))
    summ["types"] = check_types(P, R)
    summ["core_pg"] = check_core_pg(P, R, plan_dir, strict=strict_core_pg)
    summ["taps_cores"] = check_taps_cores(P, R, plan_dir, evidence)
    summ["core_faces"] = check_core_faces(P, R, plan_dir, core_conns)
    _views = _pin_views(P, plan_dir)
    summ["core_pin_form"] = check_core_pin_forms(P, R, plan_dir, _views)
    summ["island_ft_rows"] = check_island_ft_rows(P, R, plan_dir, _views)
    summ["complete"] = check_completeness(P, R, summ["taps_cores"].get("no_cells", ()), plan_dir=plan_dir,
                                          side=load_core_conns(plan_dir, core_conns))
    summ["g0c"] = g0c_summary(P, R)
    summ["geometry"] = check_geometry(P, R)
    summ["clock_entry_macro"] = check_clock_entry_macro(P, R, plan_dir, core_macros)
    summ["merged_clock_view"] = check_merged_clock_view(P, R)
    import landing_islands as LI
    li_errs = LI.check(raw)
    for e in li_errs:
        R.err("landing_islands", e)
    for e in LI.check_die_islands(raw):
        R.err("die_islands", e)
        li_errs.append(e)
    summ["landing_islands"] = dict(islands=sum(len(t.get("landing_islands") or []) for t in raw["partition_types"].values()),
                                   errors=len(li_errs))
    fp = check_abutment(P, R)
    summ["worst_faces"] = check_faces(P, R, fp)
    geo = {lid: lane_geometry(P, lid) for lid in P.lanes}
    summ["m89_signals"] = check_m89_signals(P, R)
    summ["worst_hops"] = check_hops(P, R, geo)
    summ["cuts"] = check_cuts(P, R, geo)
    summ["latency"] = check_latency(P, R)
    summ["r8"] = check_r8(P, R, plan_dir, groups, landing)
    rp = check_registered_pins(P, R, plan_dir)
    if rp:
        summ["registered_pins"] = rp
    import landing_contract as LC
    cland = LC.check(P)
    if P.clock.get("landing_network"):
        summ["clock_landings"] = {k: v for k, v in cland.items() if k != "errors"}
        for err in cland["errors"]:
            R.err("clock_landings", err)
    check_clock_reset(P, R)
    summ["clock_branch_buffers"] = check_clock_branch_buffers(P, R)
    summ["reset"] = check_reset(P, R)
    summ["seams"] = check_seams(P, R)
    summ["die_io"] = check_die_io(P, R)
    # PLAN-TOOL5 cross-die G0C rules (COORD DIE-PLAN VISUAL REVIEW 10-23 (a)-(e))
    import die_io
    import xdie
    summ["die_io"]["plan"] = die_io.check(P, R)
    summ["die_io"]["pg_domains"] = die_io.check_pg_domains(P, R)
    summ["die_io"]["source"] = io_src
    summ["cut_lines"] = xdie.check_cut_lines(P, R, geo)
    summ["reach"] = xdie.check_reach(P, R, geo)
    summ["face_tracks"] = xdie.check_face_tracks(P, R, fp)
    summ["ft_budget"] = xdie.check_ft_budget(P, R, fp)
    _st = []
    summ["streets"] = check_streets(P, R, plan_dir, clock_builds, geo, keep=_st)
    summ["g0c"] = g0c_summary(P, R)
    summ["xdie_counts"] = {c: sum(1 for i in R.items if i["check"] == c and i.get("g0c")) for c in G0C_CHECKS}
    import census_cov
    summ["census"] = census_cov.coverage(P, plan_dir or ".", R)
    if clock_builds:
        summ["clock_mesh"] = check_clock_mesh(R, clock_builds)
    summ["known_errors"] = apply_known_errors(R, plan_dir, completeness)
    if png:
        import render
        render.render(P, geo, R, png)
        summ["png"] = str(png)
        # ROOT-MERGE-82 (COORD 18:52): the street map renders after the G1 render, so a render failure (e.g. no
        # matplotlib) surfaces from the existing die_plan.png render first, as before the street rule
        import streets as ST
        A_, ko_ = _st[0]
        ST.render(A_, ko_, Path(png).with_name("streets.png"), float(P.W), float(P.H), P.name)
        summ["streets_png"] = str(Path(png).with_name("streets.png"))
    return R, summ


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--out")
    ap.add_argument("--png", action="store_true")
    ap.add_argument("--strict", action="store_true", help="WARN counts as failure")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--groups", help="R8: BINDER2 bus_groups.json (default PLANDIR/bind/bus_groups.json)")
    ap.add_argument("--landing", help="R8: <die>_r8_landing.json (default PLANDIR/*/<die>_r8_landing.json)")
    ap.add_argument("--cells-evidence", action="append", default=[],
                    help="cells.py evidence file (type / partition / module cell table or Yosys stat); repeatable; "
                         "PLANDIR cells_est.json, plan_notes.json, l1_cores_v3*.json, cells_evidence.json are read too")
    ap.add_argument("--completeness", action="store_true",
                    help="G0C: plan-completeness + hard-core rules are ERRORs (default: WARN '[G0C]'); per-type "
                         "summary in summary.g0c (types with 0 findings = G3-eligible)")
    ap.add_argument("--core-conns", help="hard-core connectivity sidecar (default PLANDIR/core_conns.json)")
    ap.add_argument("--core-macros", help="hard-core macro sidecar for clock_entry_macro (default PLANDIR/core_macros.json)")
    ap.add_argument("--clock-build", action="append", default=[],
                    help="die clock mesh build dir (die_clock_mesh build/combo); repeatable: ERROR unless the mesh is one "
                         "connected net (VIA89 at every strap crossing, emitted + routed DB)")
    ap.add_argument("--strict-core-pg", action="store_true",
                    help="core_pg: a type placing hard-core macros without core_pg_connect, or a macro LEF with no "
                         "connectable PG geometry, is an ERROR (default WARN until the dies regenerate their kits)")
    a = ap.parse_args(argv)
    raw = S.load(a.plan)
    out = Path(a.out) if a.out else Path(a.plan).resolve().parent
    out.mkdir(parents=True, exist_ok=True)
    R, summ = run(raw, png=(out / "die_plan.png") if a.png else None, plan_dir=Path(a.plan).resolve().parent,
                  groups=a.groups, landing=a.landing, evidence=a.cells_evidence, core_conns=a.core_conns,
                  completeness=a.completeness, clock_builds=a.clock_build,
                  core_macros=a.core_macros, strict_core_pg=a.strict_core_pg)
    ne = len(R.errors())
    npv = len(R.pendings())
    nw = len(R.items) - ne - npv
    ok = ne == 0 and not (a.strict and nw)
    verdict = ("PENDING-VIEW" if npv else "PASS") if ok else "FAIL"   # PENDING-VIEW is never PASS
    rep = dict(schema="opentallas.die_plan.g0.v1", plan=str(Path(a.plan).resolve()), verdict=verdict, pending_view=npv,
               mode="G0C" if a.completeness else "G0",
               errors=ne, warnings=nw, summary=summ, findings=R.items)
    (out / "g0_report.json").write_text(json.dumps(rep, indent=1) + "\n")
    if not a.quiet:
        for i in R.items[:200]:
            print(f"{i['level']:5s} [{i['check']}] {i['msg']}")
        if len(R.items) > 200:
            print(f"... {len(R.items) - 200} more in g0_report.json")
    c = summ.get("cuts", {})
    ty = summ.get("types", {})
    g = summ.get("g0c", {})
    print(f"G0C per type: {g.get('clean')}/{g.get('types')} types clean (G3-eligible: {len(g.get('g3_eligible', []))}); "
          f"die-level {g.get('die_level')}; {'ERRORs' if a.completeness else 'reported as WARN (run --completeness)'}")
    print(f"{rep['mode']} {rep['verdict']}: {ne} errors, {npv} pending-view, {nw} warnings; {ty.get('types')} types / {ty.get('partitions')} "
          f"partitions ({ty.get('near_duplicate_types')} in near-duplicate groups); worst cut {c.get('worst_full')}, worst partition "
          f"segment {c.get('worst_partition_segment')}; report {out / 'g0_report.json'}")
    return (3 if npv else 0) if ok else 1


if __name__ == "__main__":
    sys.exit(main())
