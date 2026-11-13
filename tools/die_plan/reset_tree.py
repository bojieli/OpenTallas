#!/usr/bin/env python3
"""OWNER RESET RULE (BRIEFING "OWNER DECISIONS" 2026-10-24 #2, amended by DECISION 13): pipeline reset like data.  THE
reset tool of every die.

CURRENT MODE = reset.release "wavefront" (OWNER DECISION 13, 2026-10-24 21:31; supersedes "equal depth to every tap"):
  * region = the WHOLE die: ONE root 2-flop synchroniser (ot_dp_rsync_s<N> u_rst_root) in the root partition (the one at
    the die rst_n pin, or reset.root_part); its async input = die rst_n = the only reset false path.  Every partition of
    the root's TYPE carries the synchroniser as its entry (uniform per type; at the others it sees a synchronous input).
  * NEIGHBOUR WAVEFRONT: every soft partition registers its incoming reset (arst_n -> pin register u_rst_in, interior
    pin at the type's IN site) and re-drives registered outs rst_o_<k> (interior pins at face sites, one relay each) to
    its neighbours; inside the partition an equal-depth relay tree (hops <= relay_um) reaches every clock tap and every
    rst_o.  Pins are uniform per type (the union of the sites any instance uses); the die top only wires a parent's
    rst_o_<k> to a child's arst_n (die hop <= hop_um, M8/M9), no die-top relays, no per-instance variants.
  * wf_solve picks per type the IN site (face midpoints, corners, face sites; reset.in_sites overrides) and per partition
    the parent (Dijkstra on release cycles + local search; objective: every partition within hop, then the latest
    release).  Hard partitions are leaves (their reset tap = IN; reset.depth clocks to release, default 1).
  * PUBLISHED OFFSETS (`reset_tree.py offsets PLAN.json [--out J]`): per partition the release cycle = clocks after the
    die rst_n deasserts at which its taps (and rst_o) release: root N + K_root, child release(parent) + entry + K
    (entry 1, or N for the root's type).  test_reset_wavefront.py checks the table against a simulation of the
    generated die.  The static schedule starts with an explicit start broadcast after reset (decision 13c); only
    control state is reset (13d).

LEGACY MODE "pipelined" (decision 2 as first written; G0 warns it is superseded):

Rule: exactly ONE root 2-flop reset synchroniser per die REGION (its async input is the only reset false path / CDC).
From it the synchronised reset travels as a SYNCHRONOUS signal through relay flops every <= 405 um (the data reach
rule), with EQUAL depth to every clock tap, so every block releases on the same known cycle.  Local flops use the
delivered reset with normal timed recovery/removal (or as a sync reset).  Assertion is synchronous too (the clock runs
at boot).  No recovery waivers.

Plan switch: reset.release "pipelined" (plan level; "counted" = the legacy per-tap asynchronous synchronisers).
  reset.relay_um     relay reach (default 405).  Trees are PLANNED at relay_um - MARGIN_UM (legalisation slack) and
                     CHECKED at relay_um (planned here, placed in the kit's reset_tree.tcl report).
  reset.part_depth   the partition reset contract K: relay stages from the partition's reset entry stage to every
                     clock tap, the SAME for every type of the plan (default: the deepest type's own tree depth).  A
                     replicated type then has one kit whatever its die position; the die tree pads per instance.
  reset.regions      [{name, parts?, root_um?}]: die regions (default ONE region = the whole die).  `parts` = member
                     partitions (default: every partition not listed in another region); `root_um` = the region's
                     root synchroniser site in the die frame (default: the die rst_n pin at the clock spine root,
                     gen_phys.die_root_pins).

Partition (kit) structure, per type (gen_rtl for generated kits, kit_rsync for bound kits):
  entry stage at the arst_n pin: ot_dp_rrelay u_rst_in, a plain pin register -- arst_n is a SYNCHRONOUS input (the die
  reset tree's last relay drives it; timed under the kit IO budget like any data pin; NO synchroniser, NO false path)
  -> rst_root_n -> relay tree ot_dp_rrelay u_rrl_<k>: shortest-hop tree over the clock taps, intermediate relays on
     the x-then-y L path (pushed off hard cores / macros), pads at the taps, depth exactly K at every tap -> rst_n_t<i>.
  Leaf contents take the tap nearest the outline centre (rst_n = rst_n_t<c>); boundary flops / ft stations their
  nearest tap (gen_rtl rsel, reset_taps.tcl after FIRM placement).
  Release at every tap: 1 + K clocks after the arst_n pin.
  (Interim, kit_rsync on a plan that is NOT pipelined: entry "sync" = ot_dp_rsync_s<N> u_rst_root at the pin, i.e. a
  region per partition; the partition's own depth.  Not the die-region rule: use only until the plan switches.)

Die level (the die top RTL and `reset_tree.py die`): per region ONE root synchroniser ot_dp_rsync_s<N> at root_um
(async input = the die rst_n pin: the region's only reset false path), then a die relay tree over the member
partitions' arst_n pins (die frame, same builder, hops <= relay_um) with equal depth E.  Every tap of the region is
released N + E + 1 + K clocks after rst_n deasserts.  HOSTING (OPEN): the die has no std-cell rows of its own
(partitions abut), so the root synchroniser and the die relays must sit inside partitions; `reset_tree.py die`
reports, per partition instance and type, the die relays falling in its outline.  The die top RTL instantiates them
at die level (functional model; exact boot cycles for benches).

usage (any form takes --release wavefront|pipelined to price a plan that has not switched yet):
       reset_tree.py offsets PLAN.json [--out J]    -> wavefront: per-partition release cycles (compiler / benches)
       reset_tree.py type PLAN.json TYPE            -> the type's tree summary (entry, depth, relays, boot cycles)
       reset_tree.py die  PLAN.json [--out J]       -> die regions: root, die depth E, hosting per partition, boot cycles
       reset_tree.py all  PLAN.json                 -> every type (G0 rule check) + die summary
       reset_tree.py render PLAN.json TYPE [--png F] [--release pipelined]   -> review picture of the type's tree"""
import heapq
import json
import math
import re
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import schema as S  # noqa: E402

REACH_UM = 405.0        # owner rule: relay flops every <= 405 um
# RESET-SLEW (REACH-FIX-2 11-12, COORD): the longest reset relay hop ONE relay stage (its INVx3 output driver) drives
# within the 320 ps max-slew rule at TT and FF with 20 % margin, from 141 measured routed reset relay nets in 6 HEAD
# kits (rp17 k17 wshim_tx / eshim_rx, w10 eshim_rx, hb4k eshim_tx, ctlk hd_ctl): worst wire term over nets >= 150 um
# k = 0.0093 TT / 0.0103 FF ps/um^2 on top of the driver slew (p90 102 TT / 65 FF ps): sqrt((320/1.2 - drv) / k) =
# 133 TT / 140 FF -> 130 um.  All 4 measured violators (350-418 ps) were single-driver segments of 186-219 um.
# A plan opts in with reset.relay_rule "slew_safe" (die default for relay_um, a type's reset.relay_um only tightens).
SLEW_SAFE_RELAY_UM = 130.0
MARGIN_UM = 25.0        # planning slack under the reach (row / site snapping, ff_put_near spiral, macro push-off)
CLEAR_UM = 4.32         # relay sites stay this far off hard cores / macro leaves (one std-cell row + halo)


class ResetError(Exception):
    pass


# ----------------------------------------------------------------------------------------------- plan settings
def pipelined(P):
    return P.reset.get("release") == "pipelined"


def relay_um(P, tn=None):
    """die reset relay reach (reset.relay_um, default 405); with tn, partition_types[tn].reset.relay_um may only
    TIGHTEN it for that type (REACH-FIX-2 11-12, HEAD-95 rp18: hd_spn_wshim_rx u_rrl_14 -> u_rrl_17 334.8 um on a
    380-um plan reach -> 250 puts one more relay on that hop; reach is set by this fixed script, not by hand)"""
    die = float(P.reset.get("relay_um", SLEW_SAFE_RELAY_UM if P.reset.get("relay_rule") == "slew_safe" else REACH_UM))
    if P.reset.get("relay_rule") == "slew_safe":
        die = min(die, SLEW_SAFE_RELAY_UM)
    if tn is None:
        return die
    t = (P.types.get(tn) or {}).get("reset") or {}
    v = t.get("relay_um")
    if v is None:
        return die
    v = float(v)
    if not (MARGIN_UM < v <= die):
        raise ResetError(f"type {tn}: reset.relay_um {v:g} must be in ({MARGIN_UM:g}, die relay_um {die:g}]")
    return v


def sync_stages(P, tn=None):
    t = P.types[tn] if tn else {}
    return int((t.get("reset", {}) or {}).get("sync_stages", P.reset.get("sync_stages", 2)))


def die_root_um(P):
    """the die rst_n pin (gen_phys.die_root_pins: at the clock spine root)."""
    import gen_phys
    for name, _L, x, y in gen_phys.die_root_pins(P):
        if name == "rst_n":
            return (x, y)
    return (P.W / 2, P.H / 2)


# ----------------------------------------------------------------------------------------------- die reset pad
# PATH-KV DECISION 10-25 14:19 + CLOCK-RESET amendments A/B (14:32): ONE external reset pad per die IS the die reset
# root pin.  reset.source.pad names a die_io entry {kind die_root_pad, iface reset, part = the root partition, rect over
# the gen_phys.die_root_pins 'rst_n' pin, pad_port = the as-built top port}.  The raw pad has exactly these loads, all in
# the root partition: the root synchroniser u_rst_root async input (the ONLY digital reset false path) and the declared
# analog loads (reset.source.analog_loads, e.g. the PLL por_n: the clock source cannot be synchronised to itself).
# The PLL lock (reset.source.lock {inst, pin, stable_cycles}) enters through its own 2-flop synchroniser + lock-stable
# counter (ot_dp_lockq u_rst_lockq) and qualifies the root release SYNCHRONOUSLY (sticky: a later loss of lock is HOST
# status, never a die reset); no combinational por_n & locked.  Every other leaf input on the pad, and every leaf
# input matching reset.source.por_pins, is rebound by the binder to its partition's delivered wavefront reset (and its
# type must be start_role bootstrap: a power-on reset cannot wait for START).  tools/die_plan/por_gate.py checks it.
LOCKQ_EXTRA = 3        # ot_dp_lockq: 2 lock-synchroniser stages + the qualifier flop on top of STABLE counted cycles


def die_io_entries(P):
    """the plan's die.io windows, else the PLANDIR/die_io.json sidecar (check.py rule: the plan's die.io wins)."""
    io = P.die.get("io")
    if io:
        return io
    if getattr(P, "path", None) is not None:
        sc = Path(P.path).resolve().parent / "die_io.json"
        if sc.is_file():
            return json.loads(sc.read_text())
    return []


def pad_spec(P):
    """None, or the declared die reset pad: {pad, port, io, analog_loads, por_pins, lock}."""
    src = P.reset.get("source") or {}
    if not src.get("pad"):
        return None
    io = next((w for w in die_io_entries(P) if w.get("name") == src["pad"]), None)
    return dict(pad=src["pad"], port=(io or {}).get("pad_port", src["pad"]), io=io,
                analog_loads=list(src.get("analog_loads", [])), por_pins=src.get("por_pins"),
                lock=src.get("lock"))


def die_reset_port(P):
    """the die / bound-top reset input: the as-built pad port of a declared pad, else rst_n."""
    ps = pad_spec(P)
    return ps["port"] if ps else "rst_n"


def lock_stages(P):
    """root-entry stages added by the PLL lock qualifier (ot_dp_lockq): 0 without a declared lock."""
    ps = pad_spec(P)
    if not ps or not ps.get("lock"):
        return 0
    return int(ps["lock"].get("stable_cycles", 16)) + LOCKQ_EXTRA


def pad_false_path_pins(P, tn):
    """root type of a pad plan: the ONLY pins the raw pad may reach (kit SDC set_false_path -from arst_n -to them)."""
    ps = pad_spec(P)
    if not ps or not wavefront(P) or tn != wf_solve(P)["root_type"]:
        return []
    return ["u_rst_root/async_rst_n"] + [f"{a['inst']}/{a['pin']}" for a in ps["analog_loads"]]


def check_pad(P):
    """G0 errors of a declared die reset pad (empty when none is declared)."""
    ps = pad_spec(P)
    if ps is None:
        return []
    errs = []
    w = ps["io"]
    if w is None:
        return [f"reset.source.pad {ps['pad']}: no die_io entry of that name"]
    if w.get("kind") != "die_root_pad" or w.get("iface") != "reset":
        errs.append(f"reset pad {w['name']}: kind {w.get('kind')} / iface {w.get('iface')}, expected die_root_pad / reset")
    pads = [x["name"] for x in die_io_entries(P) if x.get("kind") == "die_root_pad" or x.get("iface") == "reset"]
    if pads != [w["name"]]:
        errs.append(f"die reset pads {pads}: exactly ONE external reset pad per die (two async reset inputs = two "
                    "reset false paths)")
    if not wavefront(P):
        errs.append("reset.source.pad needs reset.release wavefront")
        return errs
    root = wf_solve(P)["root"]
    if w.get("part") != root:
        errs.append(f"reset pad {w['name']}: part {w.get('part')} is not the reset root partition {root}")
    x, y = die_root_um(P)
    r = w["rect_um"]
    if not (r[0] - 1e-6 <= x <= r[2] + 1e-6 and r[1] - 1e-6 <= y <= r[3] + 1e-6):
        errs.append(f"reset pad {w['name']}: rect {r} does not cover the die rst_n root pin ({x:.3f}, {y:.3f})")
    if not ps["analog_loads"]:
        errs.append(f"reset pad {w['name']}: reset.source.analog_loads empty (declare the PLL por_n, or drop the pad)")
    for a in ps["analog_loads"]:
        if not (isinstance(a, dict) and a.get("inst") and a.get("pin")):
            errs.append(f"reset pad analog load {a}: needs inst + pin")
    lk = ps.get("lock")
    if ps["analog_loads"] and not (lk and lk.get("inst") and lk.get("pin")):
        errs.append("reset.source.lock {inst, pin} missing: the PLL lock must qualify the root release through its "
                    "own synchroniser (CLOCK-RESET amendment A), never a combinational por_n & locked")
    if lk and int(lk.get("stable_cycles", 16)) < 1:
        errs.append("reset.source.lock.stable_cycles must be >= 1")
    return errs


def regions(P):
    """[{name, parts, root_um}] covering every partition exactly once."""
    allp = list(P.parts)
    regs = P.reset.get("regions")
    if not regs:
        return [dict(name="die", parts=allp, root_um=die_root_um(P))]
    out, seen = [], set()
    for r in regs:
        seen |= set(r.get("parts") or [])
    rest = [n for n in allp if n not in seen]
    for r in regs:
        parts = list(r.get("parts") or rest)
        out.append(dict(name=r["name"], parts=parts, root_um=tuple(r.get("root_um") or die_root_um(P))))
    return out


# ----------------------------------------------------------------------------------------------- geometry
def _man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _hops(a, b, reach):
    return max(1, math.ceil(_man(a, b) / reach - 1e-9))


def _lpath(a, b, n):
    """n interior points at equal spacing on the x-then-y L path a -> b."""
    L = _man(a, b)
    dx = abs(b[0] - a[0])
    pts = []
    for j in range(1, n + 1):
        s = L * j / (n + 1)
        if s <= dx:
            pts.append((a[0] + math.copysign(s, b[0] - a[0]), a[1]))
        else:
            pts.append((b[0], a[1] + math.copysign(s - dx, b[1] - a[1])))
    return pts


def _lef_origin_boxes(t, clear=CLEAR_UM):
    """Pre-74080dbb8 reset obstacle model (hard cores + LEF'd contents at their raw plan origin).

    Opt-in per type (`reset.obstacle_model: "lef_origin"`) for frozen plans whose published reset
    relay graphs / landing collector_tree snapshots were solved with it (KV plan_c, DIE-KV-61 11-02):
    reproduces the as-planned relay graph exactly instead of re-solving it under a frozen plan."""
    out = []
    for c in list(t.get("hard_cores", []) or []) + [c for c in t.get("contents", []) or [] if c.get("lef")]:
        if "origin_um" not in c or "outline_um" not in c:
            continue
        (ox, oy), (cw, ch) = c["origin_um"], c["outline_um"]
        if c.get("orient") in ("R90", "R270", "MXR90", "MYR90"):
            cw, ch = ch, cw
        out.append((ox - clear, oy - clear, ox + cw + clear, oy + ch + clear))
    return out


def blockages(t, clear=CLEAR_UM):
    """Canonical placed obstacle union with the unchanged reset clearance.

    Match clock / G0 / physical placement: apply core track offsets once,
    retain reuse leaves without LEFs, and keep split-container streets open.
    """
    if ((t.get("reset") or {}).get("obstacle_model")) == "lef_origin":
        out = _lef_origin_boxes(t, clear)
    else:
        from placement_obstacles import placement_boxes
        out = list(placement_boxes(t, halo=clear).values())
    # Analog/isolated-PG keepouts are uniform per type, shared with the clock
    # planner. Reset relay cells and wavefront port sites must not reoccupy a
    # domain from which the plan has removed clock taps.
    for x0, y0, x1, y1 in (t.get("clock", {}) or {}).get("keepouts_um", []):
        halo = max(clear, 8.64)
        out.append((x0 - halo, y0 - halo, x1 + halo, y1 + halo))
    return out


def _free(p, boxes, box_out):
    x, y = p
    x0, y0, x1, y1 = box_out
    # Grown blockage faces are legal (the full CLEAR_UM is already included).
    # Decimal abutting faces can differ by binary roundoff, e.g. 816.48
    # versus 816.4799999999999. This tolerance is far below one physical DBU.
    eps = 1e-9
    if not (x0-eps <= x <= x1+eps and y0-eps <= y <= y1+eps):
        return False
    return not any(a+eps < x < c-eps and b+eps < y < d-eps for a, b, c, d in boxes)


def _edge_ok(p, q, boxes):
    """one of the two L routes p -> q stays outside every blockage (a relay hop is a wire: a hard core obstructs it;
    KV-PLAN2 10-25).  _seg_hits is defined with the WALL helpers below."""
    for m in ((q[0], p[1]), (p[0], q[1])):
        if not _seg_hits(p, m, boxes) and not _seg_hits(m, q, boxes):
            return True
    return False


def _crosses(nodes, root, boxes):
    for nd in nodes:
        u = nd["par"]
        if not _edge_ok(root if u is None or u < 0 else nodes[u]["xy"], nd["xy"], boxes):
            return True
    return False


def push_off(p, boxes, box_out, step=2.16):
    """nearest point outside every blockage and inside box_out: candidates are the projections onto the faces of the
    boxes holding the point (repeated while a projection lands in another box), nearest free one wins."""
    if not boxes or _free(p, boxes, box_out):
        return p
    x0o, y0o, x1o, y1o = box_out

    def clampo(q):
        return (min(max(q[0], x0o), x1o), min(max(q[1], y0o), y1o))
    # Project onto the legal grown face itself. An extra epsilon can land
    # inside the opposite halo when two cores leave exactly 2*CLEAR_UM.
    eps = 0.0
    seen, front, best = set(), [p], None
    for _ in range(6):
        nxt = []
        for q in front:
            for a, b, c, d in boxes:
                if not (a < q[0] < c and b < q[1] < d):
                    continue
                for r in ((a - eps, q[1]), (c + eps, q[1]), (q[0], b - eps), (q[0], d + eps)):
                    r = clampo((round(r[0], 4), round(r[1], 4)))
                    if r in seen:
                        continue
                    seen.add(r)
                    if _free(r, boxes, box_out):
                        dd = _man(p, r)
                        if best is None or (dd, r) < best:
                            best = (dd, r)
                    else:
                        nxt.append(r)
        # A free projection from this layer may be much farther than a point
        # reached through another overlapping box. Keep exploring blocked
        # projections before choosing the nearest legal candidate.
        front = nxt
        if not front:
            break
    if best is not None:
        return best[1]
    # fully tiled blockages (no channel between abutting cores): nearest free point of an 8.64 um scan
    best = None
    st = 8.64
    nx, ny = int((x1o - x0o) / st) + 1, int((y1o - y0o) / st) + 1
    for j in range(ny):
        for i in range(nx):
            q = (x0o + i * st, y0o + j * st)
            dd = _man(p, q)
            if (best is None or dd < best[0]) and _free(q, boxes, box_out):
                best = (dd, q)
    return best[1] if best else p


def _seg_hits(p, q, walls):
    """the axis-parallel segment p -> q runs through the interior of a wall box."""
    lx, hx = min(p[0], q[0]), max(p[0], q[0])
    ly, hy = min(p[1], q[1]), max(p[1], q[1])
    return any(lx < c and hx > a and ly < d and hy > b for a, b, c, d in walls)


def _lfree(a, b, walls):
    """a wall-free L route a -> b exists (x-then-y or y-then-x): the hop routes at its Manhattan length."""
    if not walls:
        return True
    for k in ((b[0], a[1]), (a[0], b[1])):
        if not _seg_hits(a, k, walls) and not _seg_hits(k, b, walls):
            return True
    return False


def walls(P, tn):
    """WIRE walls of a type (CLOCK-RESET 10-25, S81 col_h9_r1 u_rrl_73 -> 74): blockages whose routing obstruction
    reaches the type's top signal layer (S81 ROM elem / BF col views: LEF OBS M1-M7 under MAX_ROUTING_LAYER M7).  A
    partition wire cannot cross them on any layer it owns (M8/M9 are the die's: BRIEFING decision 12), so a relay hop
    over one is a ~2x detour in the kit, not its planned Manhattan length.  Same obstruction convention as the G2 /
    PROTO probe (g2.probe_blockages obs_max).  Un-grown core outlines: relay sites already keep CLEAR_UM off them."""
    import g2                                  # lazy: g2 -> gen_phys -> reset_tree
    t = P.types[tn]
    top = int(P.type_top_layer(tn)[1:])
    out = []
    for c in g2.probe_blockages(t, P.type_top_layer(tn)):
        if "origin_um" not in c or "outline_um" not in c or int(str(c.get("obs_max", "M5"))[1:]) < top:
            continue
        (ox, oy), (cw, ch) = c["origin_um"], c["outline_um"]
        if c.get("orient") in ("R90", "R270", "MXR90", "MYR90"):
            cw, ch = ch, cw
        out.append((ox, oy, ox + cw, oy + ch))
    return out


def walled_hops(nodes, root, walls):
    """hops (child node, parent xy) with no wall-free L route."""
    out = []
    for v, nd in enumerate(nodes):
        pu = root if nd["par"] < 0 else nodes[nd["par"]]["xy"]
        if not _lfree(nd["xy"], pu, walls):
            out.append(v)
    return out



# ------------------------------------------------------------------- crossing-hop re-site (DQ85-SUL0 11-06, class rule)
# QC su_l0 (slw_su_l0__cl76fb247e vA/vB, GRT-0116): after the lane bus was split, ALL 1880 overflow gcells were 4 reset
# relay hops that ran straight over a lane macro (OBS M1-M6; only M7 open, not a wall()), 470 gcells each: u_rrl_35 /
# u_rrl_39 / u_rrl_26 / u_srl_26.  One such net alone reproduces the 470 overflow (probe, PDN and M5/M6 OBS removed).
# Rule: a relay hop with no L route outside every grown blockage moves the free relays of its chain (single-child,
# not at a tap) onto an obstacle-avoiding rectilinear route from the fixed anchor above to the fixed node below.  The
# graph, names, nets, depths and kinds stay; only xy changes; every hop stays <= plan reach.
def _route(a, b, boxes, box_out, cap=250000, faces=None):
    """shortest rectilinear path a -> b outside the interior of every box (Hanan grid of the box faces, `faces` when
    given; ties: fewer bends), collinear points merged.  None when no path exists or the grid exceeds `cap` points."""
    fb = boxes if faces is None else faces
    xs = sorted({a[0], b[0]} | {v for bx in fb for v in (bx[0], bx[2])} | ({box_out[0], box_out[2]} if box_out else set()))
    ys = sorted({a[1], b[1]} | {v for bx in fb for v in (bx[1], bx[3])} | ({box_out[1], box_out[3]} if box_out else set()))
    if box_out:
        xs = [x for x in xs if box_out[0] - 1e-9 <= x <= box_out[2] + 1e-9]
        ys = [y for y in ys if box_out[1] - 1e-9 <= y <= box_out[3] + 1e-9]
    if len(xs) * len(ys) > cap:
        return None
    xi, yi = {x: i for i, x in enumerate(xs)}, {y: j for j, y in enumerate(ys)}
    if a[0] not in xi or a[1] not in yi or b[0] not in xi or b[1] not in yi:
        return None
    s0, t0 = (xi[a[0]], yi[a[1]]), (xi[b[0]], yi[b[1]])
    dist = {(s0, -1): (0.0, 0)}
    prev = {}
    pq = [(0.0, 0, s0, -1)]
    while pq:
        d, nb, u, dr = heapq.heappop(pq)
        if dist.get((u, dr), (1e30, 0)) < (d, nb):
            continue
        if u == t0:
            path, k = [], (u, dr)
            while k in prev or k[0] == s0:
                path.append((xs[k[0][0]], ys[k[0][1]]))
                if k not in prev:
                    break
                k = prev[k]
            path = path[::-1]
            out = [path[0]]
            for k2, pt in enumerate(path[1:], 1):
                if pt == out[-1]:
                    continue
                if (len(out) >= 2 and k2 < len(path) and
                        ((out[-2][0] == out[-1][0] == pt[0]) or (out[-2][1] == out[-1][1] == pt[1]))):
                    out[-1] = pt                         # collinear: extend the segment
                else:
                    out.append(pt)
            return out
        for nd, (di, dj) in enumerate(((1, 0), (-1, 0), (0, 1), (0, -1))):
            v = (u[0] + di, u[1] + dj)
            if not (0 <= v[0] < len(xs) and 0 <= v[1] < len(ys)):
                continue
            p, q = (xs[u[0]], ys[u[1]]), (xs[v[0]], ys[v[1]])
            if _seg_hits(p, q, boxes):
                continue
            c = (d + _man(p, q), nb + (dr >= 0 and dr // 2 != nd // 2))
            if c < dist.get((v, nd), (1e30, 0)):
                dist[(v, nd)] = c
                prev[(v, nd)] = (u, dr)
                heapq.heappush(pq, (c[0], c[1], v, nd))
    return None


def _walk(path, s):
    """the point at arc length s along polyline path, and the index of the segment holding it."""
    for i in range(len(path) - 1):
        L = _man(path[i], path[i + 1])
        if s <= L + 1e-9:
            f = 0.0 if L == 0 else s / L
            return (path[i][0] + f * (path[i + 1][0] - path[i][0]), path[i][1] + f * (path[i + 1][1] - path[i][1])), i
        s -= L
    return path[-1], len(path) - 2


def _place_on(path, n, reach):
    """n relay sites on path (anchor path[0] -> fixed path[-1]) so that every one of the n+1 hops is a sub-path of
    <= 1 bend (an L route the path proves free) and <= the smallest feasible per-hop length <= reach; None if the
    path needs more than n+1 such hops."""
    cum = [0.0]
    for i in range(len(path) - 1):
        cum.append(cum[-1] + _man(path[i], path[i + 1]))
    L = cum[-1]

    def greedy(r):
        out, s = [], 0.0
        while L - s > r + 1e-9:
            _, i = _walk(path, s + 1e-9)
            lim = cum[min(i + 2, len(path) - 1)]         # <= 1 bend: stay within the next two segments
            s2 = min(s + r, lim)
            if s2 <= s + 1e-9:
                return None
            out.append(s2)
            s = s2
        return out
    lo, hi = L / (n + 1), float(reach)
    g = greedy(hi)
    if g is None or len(g) > n:
        return None
    for _ in range(40):                                 # smallest per-hop length that still fits n relays
        mid = (lo + hi) / 2
        gm = greedy(mid)
        if gm is not None and len(gm) <= n:
            hi, g = mid, gm
        else:
            lo = mid
    pts = [tuple(round(c, 4) for c in _walk(path, s)[0]) for s in g]
    while len(pts) < n:                                 # spare relays co-site at the fixed end (pads)
        pts.append(tuple(path[-1]))
    return pts


def crossing_hops(T, boxes):
    """relay names whose hop from its driver has no L route outside every box."""
    xy = {r["q"]: r["xy"] for r in T["relays"]}
    root = next((r["d"] for r in T["relays"] if r["d"].endswith("rst_root_n")), None)
    if root is not None:
        xy[root] = T["root"]
    return [r["name"] for r in T["relays"] if r["d"] in xy and not _edge_ok(tuple(xy[r["d"]]), tuple(r["xy"]), boxes)]


def resite_crossing(T, boxes, box_out=None, reach=None):
    """the class rule above on an assigned tree T (in place on a copy).  Returns (T, moves {name: [old, new]},
    unresolved [name]).  A tree without crossing hops comes back unchanged (byte-identical)."""
    import copy
    if not boxes:
        return T, {}, []
    # grown faces are legal (relays sit ON them); decimal faces differ by binary roundoff (997.932 vs 997.9319999)
    faces = [tuple(round(v, 4) for v in bx) for bx in boxes]
    boxes = [(a + 1e-6, b + 1e-6, c - 1e-6, d - 1e-6) for a, b, c, d in faces]
    bad = crossing_hops(T, boxes)
    if not bad:
        return T, {}, []
    T = copy.deepcopy(T)
    reach = float(reach or T.get("plan_reach_um") or T.get("reach_um") or REACH_UM - MARGIN_UM)
    by_q = {r["q"]: r for r in T["relays"]}
    by_n = {r["name"]: r for r in T["relays"]}
    kids = {}
    for r in T["relays"]:
        kids.setdefault(r["d"], []).append(r)

    def movable(r):
        return r.get("tap") is None and len(kids.get(r["q"], [])) == 1

    moves, unresolved, done = {}, [], set()
    for name in bad:
        if name in done:
            continue
        r = by_n[name]
        chain = []                                       # free relays between the anchor and the fixed node
        up = by_q.get(r["d"])
        while up is not None and movable(up):
            chain.insert(0, up)
            up = by_q.get(up["d"])
        anchor = tuple(T["root"]) if up is None else tuple(up["xy"])
        low = r
        while movable(low):
            chain.append(low)
            low = kids[low["q"]][0]
        fixed = tuple(low["xy"])
        path = _route(anchor, fixed, boxes, box_out, faces=faces)
        sites = _place_on(path, len(chain), reach) if path else None
        if sites is None:
            unresolved.append(name)
            continue
        for rr, xy in zip(chain, sites):
            if tuple(rr["xy"]) != tuple(xy):
                moves[rr["name"]] = [list(rr["xy"]), list(xy)]
                rr["xy"] = list(xy)
            done.add(rr["name"])
        done.add(low["name"])
    xy = {r["q"]: r["xy"] for r in T["relays"]}
    root = next((r["d"] for r in T["relays"] if r["d"].endswith("rst_root_n")), None)
    if root is not None:
        xy[root] = T["root"]
    T["max_hop_um"] = round(max(_man(xy[r["d"]], r["xy"]) for r in T["relays"] if r["d"] in xy), 1)
    unresolved = sorted(set(unresolved) | set(crossing_hops(T, boxes)))
    if moves:
        T["resited_crossing"] = len(moves)
    return T, moves, unresolved


def native_resite_sites(tree, boxes, box_out=None, paths=None):
    """the class rule for a CAPTURED native tree (bound_native_reset.json, gen_phys native contract): it is never
    re-solved, so the rule is applied as a sites-only bound_reset_placement overlay (bound_reset_contract.placement):
    {native instance: [x, y]} for every moved u_rrl_<k> and its run / raw copies (u_srl_<k>, u_rrl_<k>_r), filtered
    to `paths` (the native instance IDs) when given.  Returns (sites, unresolved)."""
    _, moves, unresolved = resite_crossing(tree, boxes, box_out)
    sites = {}
    for n, (_, xy) in moves.items():
        for m in (n, n.replace("u_rrl", "u_srl", 1), n + "_r"):
            if paths is None or m in paths:
                sites[m] = [round(xy[0], 4), round(xy[1], 4)]
    return sites, unresolved


def resite_type(P, tn, T):
    """plan hook: reset.relay_resite_crossing (opt-in per plan, DEFAULT OFF: absent/false = the pre-11-06 trees; COORD
    11-06 19:2x asked for it on the QC non-signed types only, so the QC plan sets it true).  reset.relay_resite_skip_types [type] keeps the listed (signed-off) types byte-identical: their
    tree object comes back untouched.  A tree without a crossing comes back unchanged anyway."""
    if not P.reset.get("relay_resite_crossing", False) or tn in (P.reset.get("relay_resite_skip_types") or ()):
        return T
    t = P.types[tn]
    w, h = t["outline_um"]
    T2, moves, unresolved = resite_crossing(T, blockages(t), (CLEAR_UM, CLEAR_UM, w - CLEAR_UM, h - CLEAR_UM))
    if moves and T2["max_hop_um"] > T2.get("reach_um", REACH_UM) + 1e-6:
        return T                                         # never trade a crossing for an over-reach hop
    return T2


# ----------------------------------------------------------------------------------------------- the tree
def build(taps, root_xy, depth=None, reach=REACH_UM, margin=MARGIN_UM, boxes=(), box_out=None, prefix="", walls=(),
          avoid_cores=False):
    """taps [(name, x, y)] (tap index = list index); root_xy = the entry stage (reset pin).
    Topology: a shortest-hop tree over the taps (ties: fewer intermediate relays, then shorter wire) with intermediate
    relays on the x-then-y L path, pushed off `boxes`; when a push-off breaks the reach, a shortest-hop tree over a
    grid of free relay sites (wires may cross blockages that leave the top signal layer open -- never a wall() --, relays may not).  Equal depth: every tap is padded to D =
    max(own depth, `depth`); pads go as HIGH in the tree as possible (on the edge into the subtree that has slack), so
    one pad serves every tap below it.
    Returns {root, depth, own_depth, relays[{name, xy, d, q, depth, tap, kind}], reach_um, max_hop_um, ...}."""
    topo = topology(taps, root_xy, reach, margin, boxes, box_out, walls, avoid_cores)
    return assign(topo, depth, prefix)


def topology(taps, root_xy, reach=REACH_UM, margin=MARGIN_UM, boxes=(), box_out=None, walls=(), avoid_cores=False,
             column=None):
    """the depth-independent part of build(): relay sites and parents.  A tap (or the entry) over a blockage gets its
    relay site at the nearest free point (tap_offset_um records how far).  `walls` (see walls()): every hop must have
    a wall-free L route, else the grid topology routes around them; a remaining walled hop fails closed."""
    if not taps:
        raise ResetError("reset tree: no taps")
    root = (float(root_xy[0]), float(root_xy[1]))
    pts = [(float(x), float(y)) for _, x, y in taps]
    off = 0.0
    if box_out is not None and boxes:
        root = push_off(root, boxes, box_out)
        sites = [push_off(p, boxes, box_out) for p in pts]
        off = max(_man(a, b) for a, b in zip(pts, sites))
        pts = sites
    plan_reach = reach - margin
    walls = list(walls or ())
    if column is not None:
        nodes, method = _topo_column(pts, root, column, plan_reach, boxes, box_out), "column"
    else:
        nodes, method = _topo_taps(pts, root, plan_reach, boxes, box_out), "taps"
    # WALL rule (CLOCK-RESET 10-25): never a hop without a wall-free L route.  avoid_cores (plan reset.relay_avoid_cores,
    # KV-PLAN2 10-25): no hop whose both L routes cross ANY blockage (G2 kv3_pc: rrl_13 -> rrl_14 straight through
    # kvpc0, 1272 M3 overflow)
    hb = boxes if avoid_cores else ()
    if column is None and ((_maxhop(nodes, root) > reach + 1e-6 and boxes) or walled_hops(nodes, root, walls)
                           or (hb and _crosses(nodes, root, hb))):
        nodes, method = _topo_grid(pts, root, plan_reach, boxes, box_out, walls=walls, hop_boxes=hb), "grid"
    bad = walled_hops(nodes, root, walls)
    if bad:
        raise ResetError(f"reset tree: {len(bad)} relay hop(s) cross a wall (blockage closed to the top signal layer) "
                         f"with no wall-free L route, e.g. node {bad[0]} at {nodes[bad[0]]['xy']}")
    return dict(nodes=nodes, root=root, ntap=len(pts), reach=reach, plan_reach=plan_reach, method=method,
                taps=[n for n, _, _ in taps], tap_offset_um=round(off, 1), walls=len(walls))


def assign(topo, depth=None, prefix="", pad_spread=False, boxes=(), box_out=None, walls=(), site_names=False):
    geometry = dict(boxes=boxes, box_out=box_out, walls=walls) if pad_spread else None
    T = _assign(topo["nodes"], topo["root"], topo["ntap"], depth, prefix, geometry, site_names)
    reach = topo["reach"]
    T.update(reach_um=reach, plan_reach_um=topo["plan_reach"], topology=topo["method"], taps=list(topo["taps"]),
             tap_offset_um=topo["tap_offset_um"])
    if T["max_hop_um"] > reach + 1e-6:
        raise ResetError(f"reset tree: max hop {T['max_hop_um']} um > {reach:g} um (no relay site within reach)")
    return T


def _maxhop(nodes, root):
    return max(_man(nodes[v]["xy"], root if nodes[v]["par"] < 0 else nodes[nodes[v]["par"]]["xy"])
               for v in range(len(nodes)))


def _topo_taps(pts, root, reach, boxes, box_out):
    """nodes [{xy, par (-1 = root), tap (index or None)}]: taps first (node i = tap i), then wire relays."""
    n = len(pts)
    dist = {-1: (0, 0, 0.0)}
    par = {}
    pq = [(0, 0, 0.0, -1)]
    done = set()
    while pq:
        h, nw, w, u = heapq.heappop(pq)
        if u in done:
            continue
        done.add(u)
        pu = root if u < 0 else pts[u]
        for v in range(n):
            if v in done:
                continue
            e = _hops(pu, pts[v], reach)
            c = (h + e, nw + e - 1, w + _man(pu, pts[v]))
            if v not in dist or c < dist[v]:
                dist[v] = c
                par[v] = u
                heapq.heappush(pq, c + (v,))
    nodes = [dict(xy=pts[v], par=None, tap=v) for v in range(n)]
    for v in sorted(range(n), key=lambda v: dist[v]):
        u = par[v]
        pu = root if u < 0 else pts[u]
        prev = u
        for p in _lpath(pu, pts[v], _hops(pu, pts[v], reach) - 1):
            if box_out is not None:
                p = push_off(p, boxes, box_out)
            nodes.append(dict(xy=p, par=prev, tap=None))
            prev = len(nodes) - 1
        nodes[v]["par"] = prev
    return nodes


def _topo_column(pts, root, column, reach, boxes, box_out):
    """reset column (column_spec): a straight relay chain from the entry along column['axis'] to column['end'] (the
    exit site, or the farthest tap projection), relays every <= reach; every tap hangs off the chain node that gives it
    the fewest hops (then the least wire), with reach-limited L relays on the branch.  Nodes as _topo_taps."""
    n = len(pts)
    k = 1 if column["axis"] == "y" else 0                      # along-axis coordinate index
    a0 = root[k]
    if column.get("end") is not None:
        a1 = column["end"][k]
    else:
        a1 = max((p[k] for p in pts), key=lambda v: abs(v - a0))
    m = max(0, math.ceil(abs(a1 - a0) / reach - 1e-9) - 1)
    nodes = [dict(xy=pts[v], par=None, tap=v) for v in range(n)]
    chain = [(-1, root, 0)]
    prev = -1
    for i in range(1, m + 1):
        a = a0 + (a1 - a0) * i / (m + 1)
        p = (root[0], a) if k == 1 else (a, root[1])
        if box_out is not None and boxes:
            p = push_off(p, boxes, box_out)
        nodes.append(dict(xy=p, par=prev, tap=None))
        prev = len(nodes) - 1
        chain.append((prev, p, i))
    for v in range(n):
        u, pu, du = min(chain, key=lambda c: (c[2] + _hops(c[1], pts[v], reach), _man(c[1], pts[v]), c[2]))
        par = u
        for p in _lpath(pu, pts[v], _hops(pu, pts[v], reach) - 1):
            if box_out is not None and boxes:
                p = push_off(p, boxes, box_out)
            nodes.append(dict(xy=p, par=par, tap=None))
            par = len(nodes) - 1
        nodes[v]["par"] = par
    return nodes


def _topo_grid(pts, root, reach, boxes, box_out, pitch=None, walls=(), hop_boxes=()):
    """shortest-hop tree over the taps + a grid of free relay sites (pitch um); ties: fewer hops, then less wire."""
    x0, y0, x1, y1 = box_out
    pitch = pitch or max(21.6, reach / 4)
    while (x1 - x0) * (y1 - y0) / pitch ** 2 > 3000:
        pitch *= 1.5
    grid = []
    nx, ny = int((x1 - x0) / pitch) + 1, int((y1 - y0) / pitch) + 1
    for j in range(ny):
        for i in range(nx):
            q = (x0 + i * pitch, y0 + j * pitch)
            if _free(q, boxes, box_out):
                grid.append(q)
    # thin channels between abutting blockages / along the outline: sites ON every blockage edge (the blockages are
    # grown by CLEAR_UM, so an edge point is CLEAR_UM off the core; two cores 2 x CLEAR_UM apart share that line)
    eps = 0.0
    for a, b, c, d in list(boxes) + [(x0 - 2 * eps, y0 - 2 * eps, x1 + 2 * eps, y1 + 2 * eps)]:
        for t in range(int(max(c - a, d - b) / pitch) + 2):
            for q in ((min(a + t * pitch, c), b - eps), (min(a + t * pitch, c), d + eps),
                      (a - eps, min(b + t * pitch, d)), (c + eps, min(b + t * pitch, d))):
                if box_out is not None and not (x0 <= q[0] <= x1 and y0 <= q[1] <= y1):
                    q = (min(max(q[0], x0), x1), min(max(q[1], y0), y1))
                if _free(q, boxes, box_out):
                    grid.append(q)
    grid = sorted(set(grid))
    allp = list(pts) + grid               # node index: taps first
    cell = reach
    buckets = {}
    for k, q in enumerate(allp):
        buckets.setdefault((int(q[0] // cell), int(q[1] // cell)), []).append(k)

    def near(q):
        cx, cy = int(q[0] // cell), int(q[1] // cell)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for k in buckets.get((cx + dx, cy + dy), ()):
                    if _man(q, allp[k]) <= reach and _lfree(q, allp[k], walls) and _edge_ok(q, allp[k], hop_boxes):
                        yield k
    dist = {}
    par = {}
    pq = [(0, 0.0, -1)]
    best = {-1: (0, 0.0)}
    while pq:
        h, w, u = heapq.heappop(pq)
        if u in dist:
            continue
        dist[u] = (h, w)
        pu = root if u < 0 else allp[u]
        for v in near(pu):
            if v in dist:
                continue
            c = (h + 1, w + _man(pu, allp[v]))
            if v not in best or c < best[v]:
                best[v] = c
                par[v] = u
                heapq.heappush(pq, c + (v,))
    miss = [v for v in range(len(pts)) if v not in dist]
    if miss:
        raise ResetError(f"reset tree: taps {miss[:5]} unreachable through free relay sites within {reach:g} um")
    nodes = [dict(xy=pts[v], par=None, tap=v) for v in range(len(pts))]
    gid = {}
    for v in range(len(pts)):
        chain, u = [], par[v]
        while u >= 0 and u >= len(pts) and u not in gid:
            chain.append(u)
            u = par[u]
        top = u if u < len(pts) else gid[u]            # a tap (or -1) or an already-made grid node
        for g in reversed(chain):
            nodes.append(dict(xy=allp[g], par=top, tap=None))
            gid[g] = top = len(nodes) - 1
        u = par[v]
        nodes[v]["par"] = u if u < len(pts) else gid[u]
    return nodes


def _pad_sites(p, q, count, boxes=(), box_out=None, walls=()):
    """Latency-neutral pad sites on a legal incoming L path; short/blocked remainder stays at q.

    Never push an interpolated point through a macro: a candidate route is accepted
    only if its wires avoid walls and every new site is outside all placement boxes.
    """
    if not count:
        return []
    if box_out is None:
        box_out = (-math.inf, -math.inf, math.inf, math.inf)
    length = _man(p, q)
    movable = min(count, max(0, int(length // 20) - 1))
    if not movable:
        return [q] * count
    for corner in ((q[0], p[1]), (p[0], q[1])):
        if _seg_hits(p, corner, walls) or _seg_hits(corner, q, walls):
            continue
        a = _man(p, corner)
        sites = []
        for j in range(1, movable + 1):
            d = length * j / (movable + 1)
            u, v, at = (p, corner, d) if d <= a else (corner, q, d-a)
            seg = _man(u, v)
            t = at / seg if seg else 0
            sites.append((u[0] + t*(v[0]-u[0]), u[1] + t*(v[1]-u[1])))
        if all(_free(xy, boxes, box_out) for xy in sites):
            return sites + [q] * (count-movable)
    return [q] * count


def site_relay_id(xy, dep, used):
    """RELAY-SITES (TYPE-SAFE-5 11-09): relay number from where the relay is, not from its visit order.  A tap re-bin
    used to renumber every later relay, so plan raw_reset names went stale (QC 'writer START raw reset rst_rl_228 has no
    registered wavefront driver') and two different trees could hold different relays under one name (t35/t71 collector
    rst_rl_235, rst_rl_45).  Still decimal, so the rst_rl_<n> / u_rrl_<n> patterns in the flow keep matching."""
    seed = f"{round(xy[0] * 10)}:{round(xy[1] * 10)}:{dep}"
    v = zlib.crc32(seed.encode())
    while v in used:                       # relays sharing a site and depth, in preorder
        seed += "+"
        v = zlib.crc32(seed.encode())
    used.add(v)
    return v


def _assign(nodes, root, ntap, depth, prefix, pad_geometry=None, site_names=False):
    """relay names / nets / depths with shared pads: D = max(structural depth, depth)."""
    kids = {}
    for v, nd in enumerate(nodes):
        kids.setdefault(nd["par"], []).append(v)
    order, st = [], [-1]
    while st:                                  # preorder from the root
        u = st.pop()
        if u >= 0:
            order.append(u)
        st += sorted(kids.get(u, []), reverse=True)
    sdep = {-1: 0}
    for v in order:
        sdep[v] = sdep[nodes[v]["par"]] + 1
    H = {}
    for v in reversed(order):                  # remaining structural relays below v to its deepest tap
        H[v] = max([1 + H[c] for c in kids.get(v, [])] + [0])
    own = max(sdep[v] for v in range(ntap))
    D = max(own, int(depth or 0))
    relays, net, k, arr = [], {-1: f"{prefix}rst_root_n"}, 0, {-1: 0}
    tap_own_net = {}
    used = set()

    def add(xy, d, kind, tap, dep, last_tap=None):
        nonlocal k
        n = site_relay_id(xy, dep, used) if site_names else k
        q = f"{prefix}rst_n_t{last_tap}" if last_tap is not None else f"{prefix}rst_rl_{n}"
        relays.append(dict(name=f"{prefix}u_rrl_{n}", xy=xy, d=d, q=q, depth=dep, tap=tap, kind=kind))
        k += 1
        return q
    for v in order:
        nd = nodes[v]
        u = nd["par"]
        src, a = net[u], arr[u]
        slack = D - (a + 1) - H[v]
        tapv = nd["tap"]
        padxy = [nd["xy"]] * slack
        if pad_geometry is not None:
            pxy = root if u < 0 else nodes[u]["xy"]
            padxy = _pad_sites(pxy, nd["xy"], slack, **pad_geometry)
        for xy_pad in padxy:                   # shared pads keep the exact same depth and topology
            a += 1
            src = add(xy_pad, src, "pad", tapv, a)
        a += 1
        leaf_done = tapv is not None and a == D
        q = add(nd["xy"], src, "tap" if tapv is not None else "wire", tapv, a, tapv if leaf_done else None)
        net[v], arr[v] = q, a
        if tapv is not None and not leaf_done:    # an interior tap: its own output padded to D at the tap
            s2 = q
            for j in range(a + 1, D + 1):
                s2 = add(nd["xy"], s2, "pad", tapv, j, tapv if j == D else None)
            tap_own_net[tapv] = s2
    xy = {r["q"]: r["xy"] for r in relays}
    xy[f"{prefix}rst_root_n"] = root
    maxhop = max(_man(xy[r["d"]], r["xy"]) for r in relays)
    return dict(root=root, depth=D, own_depth=own, relays=relays, max_hop_um=round(maxhop, 1),
                tap_depth={v: sdep[v] for v in range(ntap)},
                n_tree=sum(r["kind"] != "pad" for r in relays), n_pad=sum(r["kind"] == "pad" for r in relays))


def verify(T):
    """structural rule check of a built tree: [errors]."""
    errs = []
    drv = {T["relays"][0]["d"]} if T["relays"] else set()
    qs = {}
    for r in T["relays"]:
        if r["q"] in qs:
            errs.append(f"net {r['q']} driven twice")
        qs[r["q"]] = r
    root_net = next((r["d"] for r in T["relays"] if r["d"].endswith("rst_root_n")), None)
    for r in T["relays"]:
        if r["d"] != root_net and r["d"] not in qs:
            errs.append(f"{r['name']}: input {r['d']} has no driver")
    # depth along the driver chain, equal at every tap
    def dep(net):
        n = 0
        while net != root_net:
            net = qs[net]["d"]
            n += 1
        return n
    taps = list(range(len(T["taps"])))
    for v in taps:
        net = next((r["q"] for r in T["relays"] if r["q"].endswith(f"rst_n_t{v}")), None)
        if net is None:
            errs.append(f"tap {v}: no rst_n_t{v}")
        elif dep(net) != T["depth"]:
            errs.append(f"tap {v}: depth {dep(net)} != {T['depth']}")
    for c in T.get("core_resets", []):
        q = qs.get(f"rst_n_t{c['tap']}")
        if q is None or _man(q["xy"], c["pin_um"]) > T["reach_um"]:
            errs.append(f"hard-core reset {c['inst']}.{c['pin']}: missing or over-reach relay")
    del drv
    if T["max_hop_um"] > T["reach_um"] + 1e-6:
        errs.append(f"max hop {T['max_hop_um']} > {T['reach_um']}")
    return errs


# ----------------------------------------------------------------------------------------------- per type
_TAPS = {}


def _taps(P, tn):
    """Geometry-only explicit endpoints, otherwise schema.tap_grid, memoised per Plan.
    The entry retains P, preventing identity reuse; full explicit sink budgets stay
    in schema.tap_grid/taps.explicit_taps after reset/START positions are solved.
    """
    e = _TAPS.get((id(P), tn))
    if e is None or e[0] is not P:
        if P.types[tn].get("clock", {}).get("tap_mode") == "explicit":
            import taps
            # Control topology must exist before its sink census can be
            # assigned. This geometry phase cannot qualify clock capacity.
            sites = taps.explicit_tap_sites(P, tn)
        elif P.types[tn].get("clock", {}).get("tap_mode") == "grid+explicit":
            import taps
            sites = taps.grid_explicit_sites(P, tn)     # geometry only, as explicit
        else:
            sites = _S_TAP_GRID(P, tn)
        e = _TAPS[(id(P), tn)] = (P, sites)
    return list(e[1])


_S_TAP_GRID = S.tap_grid


def consumer_taps(P, tn):
    """Reset consumers independent of clock entry pins (opt-in type.reset.local_taps_um).

    Clock tap indices stay first and unchanged. Extra local reset/START terminal
    relays share the type's equal release depth; they add no clock ports.
    """
    taps = _taps(P, tn)
    extra = P.types[tn].get("reset", {}).get("local_taps_um", [])
    if extra and not (wavefront(P) or pipelined(P)):
        raise ResetError(f"type {tn}: reset.local_taps_um needs synchronous wavefront/pipelined reset")
    w, h = P.types[tn]["outline_um"]
    boxes = blockages(P.types[tn])
    for j, xy in enumerate(extra):
        x, y = map(float, xy)
        if not (CLEAR_UM <= x <= w-CLEAR_UM and CLEAR_UM <= y <= h-CLEAR_UM):
            raise ResetError(f"type {tn}: local reset tap {xy} is outside the legal interior")
        if not _free((x, y), boxes, (CLEAR_UM, CLEAR_UM, w-CLEAR_UM, h-CLEAR_UM)):
            raise ResetError(f"type {tn}: local reset tap {xy} is blocked")
        if any(abs(x-a) < 1e-6 and abs(y-b) < 1e-6 for _, a, b in taps):
            raise ResetError(f"type {tn}: duplicate local reset tap {xy}")
        taps.append((f"reset_local_{j}", x, y))
    return taps


def consumer_count(T):
    if "n_reset_consumers" in T:
        return T["n_reset_consumers"]
    if "n_clock_taps" in T:
        return T["n_clock_taps"]
    return len(T["taps"])


def _plan_taps(P, tn):
    """the taps the wavefront SITING reads (face / corner / start sites, depth estimate): for a density type with
    clock.control_sinks these are the planning taps without the control-pin sinks (taps.density_taps control=False),
    because those sinks are the very pins sited here; otherwise = _taps."""
    t = P.types[tn]
    ck = t.get("clock", {})
    if ck.get("tap_mode") == "explicit" and ck.get("control_sinks") and not t.get("hard"):
        import taps as T
        # Endpoint geometry is frozen. The full explicit_taps budget also asks
        # for these control pins and must run only after their siting is known.
        return T.explicit_tap_sites(P, tn)
    if ck.get("tap_mode") == "grid+explicit" and ck.get("control_sinks") and not t.get("hard"):
        import taps as T
        return T.grid_explicit_sites(P, tn)
    if ck.get("tap_mode") == "density" and ck.get("control_sinks") and not t.get("hard"):
        import taps as T
        return [(n, x, y) for n, x, y, _, _ in T.density_taps(P, tn, control=False)]
    return _taps(P, tn)


def bound_native_contract(P, tn):
    """Validated, opt-in bound-kit contract installed by gen_phys, never inferred from a plan singleton."""
    return getattr(P, "_bound_native_reset_contracts", {}).get(tn)


def reset_pin(P, tn):
    """gen_phys.tap_points(P, tn)[1] (the arst_n tap, type frame) with the memoised tap grid."""
    native = bound_native_contract(P, tn)
    if native:
        return tuple(native["tree"]["root"])
    import gen_phys
    S.tap_grid = _taps
    try:
        return tuple(gen_phys.tap_points(P, tn)[1])
    finally:
        S.tap_grid = _S_TAP_GRID


def _type_tree(P, tn, depth, reach):
    import copy
    cache = P.__dict__.setdefault("_reset_tree_cache", {})
    key = (tn, depth, reach)
    if key not in cache:
        cache[key] = _type_tree0(P, tn, depth, reach)
    return copy.deepcopy(cache[key])


def _type_tree0(P, tn, depth, reach):
    cache = P.__dict__.setdefault("_reset_tree_cache", {})
    if ("topo", tn, reach) not in cache:
        t = P.types[tn]
        w, h = t["outline_um"]
        cache[("topo", tn, reach)] = topology(consumer_taps(P, tn), reset_pin(P, tn), reach=reach,
                                              boxes=blockages(t), box_out=(CLEAR_UM, CLEAR_UM, w - CLEAR_UM,
                                                                           h - CLEAR_UM), walls=walls(P, tn),
                                              avoid_cores=bool(P.reset.get("relay_avoid_cores")))
    t = P.types[tn]; w, h = t["outline_um"]
    T = assign(cache[("topo", tn, reach)], depth,
               pad_spread=bool(P.reset.get("relay_pad_spread")), boxes=blockages(t),
               box_out=(CLEAR_UM, CLEAR_UM, w-CLEAR_UM, h-CLEAR_UM), walls=walls(P, tn),
               site_names=t.get("reset_relay_names") == "site")
    T = resite_type(P, tn, T)
    if t.get("reset", {}).get("local_taps_um"):
        T.update(n_clock_taps=len(_taps(P, tn)), n_reset_consumers=len(consumer_taps(P, tn)), local_reset_taps=True)
    return T


def part_depth(P):
    """the plan's partition reset contract K (reset.part_depth, else the deepest non-hard type's own tree depth)."""
    if P.reset.get("part_depth") is not None:
        return int(P.reset["part_depth"])
    cache = P.__dict__.setdefault("_reset_tree_cache", {})
    if "K" not in cache:
        reach = relay_um(P)
        cache["K"] = max([_type_tree(P, tn, None, relay_um(P, tn))["own_depth"] for tn, t in P.types.items()
                          if not t.get("hard")] or [1])
    return cache["K"]


def for_type(P, tn, reach=None):
    """the reset tree of a plan type in its own frame (taps = schema.tap_grid, entry = gen_phys reset tap).
    Pipelined plans: entry 'relayed', depth = the plan contract K.  Other plans (kit_rsync interim): entry 'sync', the
    type's own depth."""
    native = bound_native_contract(P, tn)
    if native:
        import copy
        return copy.deepcopy(native["tree"])
    reach = float(reach or relay_um(P, tn))
    boot_buses, boot_contents = bootstrap_consumers(P, tn)
    if wavefront(P):
        if P.types[tn].get("hard"):
            raise ResetError(f"type {tn}: hard partitions carry no generated reset tree")
        T = _wf_type_tree(P, tn)
        T.update(entry="sync" if tn == wf_solve(P)["root_type"] else "relayed", sync_stages=sync_stages(P, tn),
                 type=tn, start=start_broadcast(P), relay_driver=bool(P.reset.get("relay_driver")))
        raw_used = start_raw_requests(P.types[tn])
        if raw_used:
            T["start_raw_used"] = raw_used
        if relay_lockup(P, tn):
            T["relay_lockup"] = relay_lockup_form(P)
        if T["entry"] == "sync" and lock_stages(P):
            lk = pad_spec(P)["lock"]
            T["lock"] = dict(inst=lk["inst"], pin=lk["pin"], stable=int(lk.get("stable_cycles", 16)),
                             stages=lock_stages(P))
        if T["relay_driver"]:
            T["relay_pair_boxes"] = blockages(P.types[tn])
        role, core_roles = start_roles(P, tn)
        if T["start"]:
            T["start_in"] = list(start_in_pin(P, tn))
            known = {c["inst"] for c in T.get("core_resets", [])}
            bad = sorted(set(core_roles) - known)
            if bad:
                raise ResetError(f"type {tn}: reset.core_start_roles names {bad}, not hard-core reset targets {sorted(known)}")
            nck = consumer_count(T)
            T["start_role"] = role
            T["tap_roles"] = {i: role for i in range(nck)}
            for c in T.get("core_resets", []):
                T["tap_roles"][c["tap"]] = core_roles.get(c["inst"], role)
            # BOOTSTRAP types publish ONE registered local START tap (start_t<leaf tap>, = what a MISSION tap would be:
            # registered reset AND run at the same site/depth) for the contents' explicit mission-admission input
            T["start_tap"] = leaf_tap(P, tn) if role == "bootstrap" else None
            if boot_buses or boot_contents:
                T.update(bootstrap_buses=boot_buses, bootstrap_contents=boot_contents,
                         bootstrap_taps=list(range(nck)))
        return T
    if pipelined(P):
        K = part_depth(P)
        T = _type_tree(P, tn, K, reach)
        if T["own_depth"] > K:
            raise ResetError(f"type {tn}: own reset tree depth {T['own_depth']} > the plan contract "
                             f"reset.part_depth {K}")
        ent = "relayed"
    else:
        ent = "sync"
        T = _type_tree(P, tn, None, reach)
    T.update(entry=ent, sync_stages=sync_stages(P, tn), type=tn,
             relay_driver=bool(P.reset.get("relay_driver")))
    if relay_lockup(P, tn):
        T["relay_lockup"] = relay_lockup_form(P)
    if T["relay_driver"]:
        T["relay_pair_boxes"] = blockages(P.types[tn])
    return T


def entry_stages(T):
    """pin -> release of the entry: the root synchroniser (+ the PLL lock qualifier ot_dp_lockq when declared) or one
    pin register."""
    return T["sync_stages"] + int((T.get("lock") or {}).get("stages", 0)) if T["entry"] == "sync" else 1


def release_clocks(T):
    """clocks from the entry pin (arst_n deassert for 'sync', the synchronous reset edge for 'relayed') to the release
    of every tap."""
    return entry_stages(T) + T["depth"]


# ----------------------------------------------------------------------------------------------- die level


def part_reset_pin(P, n):
    """a partition's arst_n pin in the die frame (hard partitions: their reset tap, else their centre)."""
    try:
        return P.to_die(n, reset_pin(P, P.parts[n]["type"]))
    except Exception:
        x0, y0, x1, y1 = P.rect(n)
        return ((x0 + x1) / 2, (y0 + y1) / 2)


def die_plan(P):
    """per region: ONE root synchroniser at root_um, then the die relay tree to every member partition's arst_n pin
    (die frame; equal depth E; hosting = the partition whose outline holds each die relay / the root)."""
    cache = P.__dict__.setdefault("_reset_tree_cache", {})
    if "die" in cache:
        return cache["die"]
    reach = relay_um(P)
    rects = {n: P.rect(n) for n in P.parts}

    def host(x, y):
        return next((n for n, (x0, y0, x1, y1) in rects.items() if x0 <= x <= x1 and y0 <= y <= y1), "(none)")
    regs = []
    for i, r in enumerate(regions(P)):
        pins = [(n,) + tuple(part_reset_pin(P, n)) for n in r["parts"]]
        T = build(pins, r["root_um"], reach=reach, box_out=(0, 0, P.W, P.H), prefix=f"die{i}_")
        hosts = {}
        for rl in T["relays"]:
            hosts.setdefault(host(*rl["xy"]), []).append(rl["name"])
        regs.append(dict(name=r["name"], index=i, root_um=[round(v, 3) for v in r["root_um"]],
                         root_host=host(*r["root_um"]), members=len(pins), die_depth=T["depth"],
                         relays=len(T["relays"]), tree_relays=T["n_tree"], pad_relays=T["n_pad"],
                         max_hop_um=T["max_hop_um"], hosts={k: len(v) for k, v in hosts.items()},
                         part_of_tap={j: n for j, (n, _, _) in enumerate(pins)}, tree=T))
    out = dict(regions=regs)
    cache["die"] = out
    return out


def die_summary(P):
    if wavefront(P):
        W = wf_plan(P)
        return {k: v for k, v in W.items() if k != "parts"}
    K = part_depth(P)
    N = sync_stages(P)
    rows = []
    for r in die_plan(P)["regions"]:
        hosts = r["hosts"]
        per_type = {}
        for n in P.parts:
            per_type.setdefault(P.parts[n]["type"], []).append(hosts.get(n, 0))
        nonuni = sorted(tn for tn, cs in per_type.items() if len(set(cs)) > 1)
        hp = sorted(((c, n) for n, c in hosts.items() if n in P.parts), reverse=True)
        rows.append(dict(region=r["name"], root_um=r["root_um"], root_host=r["root_host"], members=r["members"],
                         die_depth_E=r["die_depth"], die_relays=r["relays"], die_tree_relays=r["tree_relays"],
                         die_pad_relays=r["pad_relays"], max_hop_um=r["max_hop_um"],
                         release_clocks=N + r["die_depth"] + 1 + K,
                         boot_cycles_added_vs_one_sync=r["die_depth"] + 1 + K,
                         host_partitions=len(hp), unhosted=hosts.get("(none)", 0),
                         max_relays_in_one_partition=hp[0][0] if hp else 0, busiest_hosts=hp[:5],
                         types_with_nonuniform_hosting=len(nonuni), nonuniform_types=nonuni[:20]))
    return dict(release="pipelined" if pipelined(P) else P.reset.get("release", "counted"), sync_stages=N,
                part_depth_K=K, relay_um=relay_um(P), regions=rows)


def die_rtl(P, ind="    "):
    """die top lines: per region the root synchroniser + die relay tree; returns (lines, {part: net})."""
    N = sync_stages(P)
    lines, net = [], {}
    for r in die_plan(P)["regions"]:
        T, i = r["tree"], r["index"]
        lines.append(f"{ind}// OWNER RESET RULE 10-24 region {r['name']}: ONE root synchroniser + die relay tree, depth "
                     f"{T['depth']} to {r['members']} partition reset pins (hops <= {T['reach_um']:g} um); HOSTING OPEN: "
                     "these cells sit inside partitions (reset_tree.py die)")
        lines.append(f"{ind}wire die{i}_rst_root_n;")
        lines.append(f"{ind}ot_dp_rsync_s{N} die{i}_u_rst_root (.clk(clk), .async_rst_n(rst_n), "
                     f".sync_rst_n(die{i}_rst_root_n));  // @ {r['root_um']} in {r['root_host']}")
        for rl in T["relays"]:
            lines.append(f"{ind}wire {rl['q']};")
            lines.append(f"{ind}ot_dp_rrelay {rl['name']} (.clk(clk), .d({rl['d']}), .q({rl['q']}));  "
                         f"// {rl['kind']} depth {rl['depth']} @ ({rl['xy'][0]:.0f}, {rl['xy'][1]:.0f})")
        for j, n in r["part_of_tap"].items():
            net[n] = f"die{i}_rst_n_t{j}"
    return lines, net


# ----------------------------------------------------------------------------------------------- WAVEFRONT (decision 13)
INSET_UM = 8.64         # reset in / out interior pins sit this far inside the partition face
HARD_DEPTH = 1          # a hard partition (prebuilt) without reset.depth: its pin register only


def wavefront(P):
    return P.reset.get("release") == "wavefront"


def delivered(P):
    """the partition takes arst_n as a SYNCHRONOUS input (pipelined or wavefront plan)."""
    return pipelined(P) or wavefront(P)


def hop_um(P):
    """die-level reset hop reach: parent rst_o relay -> child u_rst_in (default reset.relay_um)."""
    return float(P.reset.get("hop_um", relay_um(P)))


def _snap(P, x, y):
    import gen_phys
    return tuple(gen_phys._snap_tap(P, x, y))


def column_spec(P, tn):
    """reset 'column' mode of a wavefront soft type (partition_types[t].reset.column, REACH-FIX-2 11-12 for the HEAD
    chain types): the reset enters and leaves on ONE line - entry and exit face sites at the same cross coordinate,
    taken from the parent's exit pin (or reset.column.at_um) and clamped into the type's logic span (its clock taps) -
    and the relay tree is a straight chain along that line with the taps branching off it.
    -> None or {axis ('y': chain along y, S/N faces; 'x': along x, W/E faces), at (cross coordinate or None), span}"""
    if not wavefront(P):
        return None
    t = P.types.get(tn) or {}
    col = (t.get("reset") or {}).get("column")
    if col is None or t.get("hard"):
        return None
    w, h = t["outline_um"]
    cache = P.__dict__.setdefault("_reset_tree_cache", {})
    axis = col.get("axis") or cache.get("column_axis", {}).get(tn) or ("y" if h >= w else "x")
    k = 0 if axis == "y" else 1
    cs = [p[1 + k] for p in _plan_taps(P, tn)]
    span = (min(cs), max(cs)) if cs else ((INSET_UM, (w if axis == "y" else h) - INSET_UM))
    at = col.get("at_um")
    if at is None:
        at = cache.get("column_at", {}).get(tn)
    if at is not None:
        at = min(max(float(at), span[0]), span[1])
    return dict(axis=axis, at=at, span=span)


def _column_sites(P, tn, cs):
    t = P.types[tn]
    w, h = t["outline_um"]
    if cs["axis"] == "y":
        raw = (("S", cs["at"], INSET_UM), ("N", cs["at"], h - INSET_UM))
    else:
        raw = (("W", INSET_UM, cs["at"]), ("E", w - INSET_UM, cs["at"]))
    out = []
    for j, (face, x, y) in enumerate(raw):
        out.append(dict(face=face, j=j, mid=True, xy=_snap(P, x, y)))
    return out


def face_sites(P, tn):
    """candidate reset pin sites of a soft type (type frame): along every face, INSET_UM inside, spaced so that every
    point of the face is within (hop - margin) / 2 of one; pushed off hard cores / macro leaves and off the clock tap
    pins; snapped like the tap pins.  [{face, j, mid, xy}]"""
    cache = P.__dict__.setdefault("_reset_tree_cache", {})
    key = ("sites", tn)
    if key in cache:
        return cache[key]
    cs = column_spec(P, tn)
    line = _column_sites(P, tn, cs) if cs and cs["at"] is not None else []
    t = P.types[tn]
    w, h = t["outline_um"]
    sp = max(50.0, hop_um(P) - MARGIN_UM)
    boxes = blockages(t)
    box_out = (CLEAR_UM, CLEAR_UM, w - CLEAR_UM, h - CLEAR_UM)
    taken = [(x, y) for _, x, y in _plan_taps(P, tn)] + [tuple(c["xy"]) for c in line]
    out = list(line)
    for face, L in (("S", w), ("E", h), ("N", w), ("W", h)):
        m = max(1, math.ceil(L / sp))
        for j in range(m):
            s = (j + 0.5) * L / m
            x, y = {"S": (s, INSET_UM), "N": (s, h - INSET_UM), "W": (INSET_UM, s), "E": (w - INSET_UM, s)}[face]
            if boxes:
                x, y = push_off((x, y), boxes, box_out)
            x, y = _snap(P, x, y)
            for _ in range(8):           # never two pins on one spot (GRT-0080)
                if not any(abs(x - a) < 1.0 and abs(y - b) < 1.0 for a, b in taken):
                    break
                x, y = _snap(P, x + (8.64 if face in "SN" else 0.0), y + (8.64 if face in "EW" else 0.0))
            taken.append((x, y))
            out.append(dict(face=face, j=j, mid=(j == m // 2) and not line, xy=(x, y)))
    cache[key] = out
    return out


def corner_sites(P, tn):
    """the four corner IN-pin candidates of a soft type (INSET_UM inside both faces; reachable from two sides)."""
    cache = P.__dict__.setdefault("_reset_tree_cache", {})
    key = ("corners", tn)
    cs = column_spec(P, tn)
    if cs and cs["at"] is not None:
        return []
    if key not in cache:
        t = P.types[tn]
        w, h = t["outline_um"]
        boxes = blockages(t)
        box_out = (CLEAR_UM, CLEAR_UM, w - CLEAR_UM, h - CLEAR_UM)
        taken = [(x, y) for _, x, y in _plan_taps(P, tn)] + [s["xy"] for s in face_sites(P, tn)]
        out = []
        for x, y in ((INSET_UM, INSET_UM), (w - INSET_UM, INSET_UM), (w - INSET_UM, h - INSET_UM),
                     (INSET_UM, h - INSET_UM)):
            if boxes:
                x, y = push_off((x, y), boxes, box_out)
            x, y = _snap(P, x, y)
            if not any(abs(x - a) < 1.0 and abs(y - b) < 1.0 for a, b in taken):
                out.append((x, y))
                taken.append((x, y))
        cache[key] = out
    return cache[key]


def _est_depth(P, tn, xy):
    """planning estimate of a type's relay depth from an entry at xy (reach-limited hops to the farthest tap / site)."""
    pr = relay_um(P) - MARGIN_UM
    pts = [(x, y) for _, x, y in _plan_taps(P, tn)] + [s["xy"] for s in face_sites(P, tn)]
    pts += [tuple(p) for p in P.types[tn].get("reset", {}).get("local_taps_um", [])]
    return max(1, max(math.ceil(_man(xy, p) / pr) for p in pts))


def _root_part(P, soft):
    rx, ry = die_root_um(P)

    def dist(n):
        x0, y0, x1, y1 = P.rect(n)
        return max(x0 - rx, 0, rx - x1) + max(y0 - ry, 0, ry - y1)
    return min(soft, key=lambda n: (dist(n), n))


def wf_solve(P):
    """die wavefront routing (see _wf_solve_once).  Column types without reset.column.at_um take their line from the
    parent's exit pin: solve, read every instance's parent rst_o site in the type frame (median of the cross
    coordinate), re-solve with the column sites, until the lines no longer move (<= 4 passes)."""
    cache = P.__dict__.setdefault("_reset_tree_cache", {})
    if "wf_solve" in cache:
        return cache["wf_solve"]
    cols = [tn for tn in sorted(P.types) if column_spec(P, tn) and (P.types[tn]["reset"]["column"].get("at_um") is None)]
    if not cols:
        return _wf_solve_once(P)
    for _pass in range(4):
        res = _wf_solve_once(P)
        at = dict(cache.get("column_at", {}))
        ax = dict(cache.get("column_axis", {}))
        moved = False
        for tn in cols:
            w, h = P.types[tn]["outline_um"]
            vals = []
            for n, pr in res["parent"].items():
                if pr is None or P.parts[n]["type"] != tn:
                    continue
                q, j, _d = pr
                qt = P.parts[q]["type"]
                if P.types[qt].get("hard"):
                    continue
                vals.append(P.to_type(n, P.to_die(q, face_sites(P, qt)[j]["xy"])))
            if not vals:
                continue
            px = sorted(v[0] for v in vals)[len(vals) // 2]
            py = sorted(v[1] for v in vals)[len(vals) // 2]
            # the line runs THROUGH the parent's exit pin: a pin beyond the S/N face -> vertical line at its x (axis
            # y); beyond the W/E face -> horizontal line at its y (axis x); explicit reset.column.axis wins
            a = P.types[tn]["reset"]["column"].get("axis") or ("y" if 0.0 <= px <= w else "x" if 0.0 <= py <= h
                                                                else ("y" if h >= w else "x"))
            v = px if a == "y" else py
            if tn not in at or abs(at[tn] - v) > 0.5 or ax.get(tn) != a:
                at[tn], ax[tn], moved = v, a, True
        if not moved and _pass:
            return res
        for key in [k for k in cache if k == "wf_solve" or (isinstance(k, tuple) and k[0] in ("sites", "corners"))]:
            del cache[key]
        cache["column_at"], cache["column_axis"] = at, ax
    return _wf_solve_once(P)


def _wf_solve_once(P):
    """die wavefront routing: per soft type the reset IN site (one of its four face-midpoint sites, or
    reset.in_sites[type]) and per partition its parent (the partition whose rst_o site is within hop of its IN pin and
    releases first).  Dijkstra on release cycles with estimated type depths; local search over the IN faces
    (objective: unreachable partitions, latest release, sum of releases)."""
    cache = P.__dict__.setdefault("_reset_tree_cache", {})
    if "wf_solve" in cache:
        return cache["wf_solve"]
    N = sync_stages(P)
    hp = hop_um(P) - MARGIN_UM
    hard = {n for n in P.parts if P.types[P.parts[n]["type"]].get("hard")}
    soft = sorted(n for n in P.parts if n not in hard)
    if not soft:
        raise ResetError("reset wavefront: no soft partition to carry the reset")
    root = P.reset.get("root_part") or _root_part(P, soft)
    stypes = sorted({P.parts[n]["type"] for n in soft})
    over = P.reset.get("in_sites") or {}
    cands = {}
    for tn in stypes:
        if column_spec(P, tn) and column_spec(P, tn)["at"] is not None:
            cands[tn] = [s["xy"] for s in face_sites(P, tn)[:2]]      # entry on either end of the column (wins over in_sites)
        elif tn in over:
            cands[tn] = [_snap(P, *over[tn])]
        else:          # face midpoints first (the initial choice prefers them), then corners, then every face site
            fs = face_sites(P, tn)
            cands[tn] = [s["xy"] for s in fs if s["mid"]] + corner_sites(P, tn) + \
                [s["xy"] for s in fs if not s["mid"]]
    est = {(tn, c): _est_depth(P, tn, c) for tn in stypes for c in cands[tn]}
    hdep = {n: int((P.types[P.parts[n]["type"]].get("reset") or {}).get("depth", HARD_DEPTH)) for n in hard}
    # every soft partition's out sites in the die frame, bucketed
    cell = max(hp, 1.0)
    grid = {}
    for q in soft:
        for j, s in enumerate(face_sites(P, P.parts[q]["type"])):
            X, Y = P.to_die(q, s["xy"])
            grid.setdefault((int(X // cell), int(Y // cell)), []).append((q, j, X, Y))

    def near(p, xy):
        X, Y = xy
        cx, cy = int(X // cell), int(Y // cell)
        out = []
        for i in (-1, 0, 1):
            for k in (-1, 0, 1):
                for q, j, x, y in grid.get((cx + i, cy + k), ()):
                    d = abs(x - X) + abs(y - Y)
                    if q != p and d <= hp + 1e-6:
                        out.append((q, j, round(d, 1)))
        return out
    ein = {}                                   # (p, cand) -> [(q, j, d)]
    # reset.parent_pins {part: parent} (opt-in, plan events): a part keeps its already solved parent, so a local geometry
    # change cannot flip release races elsewhere and rewrite the reset trees of untouched types; a pin out of hop leaves
    # the part unreachable (flagged like any other, G0 error).
    # A pin [parent, site] also names the parent's rst_o face site; reset.keep_outs {type: [site]} keeps a published out of
    # an untouched type that no instance uses any more, so the type's tree stays as signed.
    pins = P.reset.get("parent_pins") or {}
    pinned = lambda p, rows: (rows if p not in pins else [r for r in rows if r[0] == pins[p]] if isinstance(pins[p], str)
                              else [r for r in rows if r[0] == pins[p][0] and r[1] == pins[p][1]])
    for p in soft:
        for c in cands[P.parts[p]["type"]]:
            ein[(p, c)] = pinned(p, near(p, P.to_die(p, c)))
    for p in hard:
        ein[(p, None)] = pinned(p, near(p, part_reset_pin(P, p)))
    rtype = P.parts[root]["type"]

    def entry(p):
        return N + lock_stages(P) if P.parts[p]["type"] == rtype else 1

    def solve(choice):
        adj = {}
        for p in soft:
            for q, j, d in ein[(p, choice[P.parts[p]["type"]])]:
                adj.setdefault(q, []).append((p, j, d))
        for p in hard:
            for q, j, d in ein[(p, None)]:
                adj.setdefault(q, []).append((p, j, d))
        rel = {root: N + est[(rtype, choice[rtype])]}
        par = {root: None}
        hq = [(rel[root], root)]
        done = set()
        while hq:
            r, q = heapq.heappop(hq)
            if q in done:
                continue
            done.add(q)
            for p, j, d in sorted(adj.get(q, ())):
                if p in hard:
                    rp = r + 1 + hdep[p] - 1
                else:
                    rp = r + entry(p) + est[(P.parts[p]["type"], choice[P.parts[p]["type"]])]
                if p not in rel or rp < rel[p]:
                    rel[p], par[p] = rp, (q, j, d)
                    heapq.heappush(hq, (rp, p))
        unr = sorted(n for n in P.parts if n not in rel)
        return (len(unr), max(rel.values()), sum(rel.values())), rel, par, unr

    def toward_root(tn):
        rx = P.to_die(root, (0, 0))
        inst = [n for n in soft if P.parts[n]["type"] == tn]
        return min(cands[tn], key=lambda c: (sum(_man(P.to_die(n, c), rx) for n in inst), c))
    choice = {tn: toward_root(tn) for tn in stypes}
    best = solve(choice)

    def descend(types, rounds):
        nonlocal choice, best
        for _round in range(rounds):
            improved = False
            for tn in types:
                for c in cands[tn]:
                    if c == choice[tn]:
                        continue
                    trial = dict(choice)
                    trial[tn] = c
                    r = solve(trial)
                    if r[0] < best[0]:
                        choice, best, improved = trial, r, True
            if not improved:
                break
    # (1) reach everything: the types of unreachable soft partitions and of their neighbours, until no gain
    for _ in range(6):
        if not best[3]:
            break
        before = best[0]
        bad = {P.parts[n]["type"] for n in best[3] if n not in hard}
        for n in best[3]:
            x0, y0, x1, y1 = P.rect(n)
            for q in soft:
                a0, b0, a1, b1 = P.rect(q)
                if a0 <= x1 + 1 and x0 <= a1 + 1 and b0 <= y1 + 1 and y0 <= b1 + 1:
                    bad.add(P.parts[q]["type"])
        descend(sorted(bad), 1)
        if best[0] == before:
            break
    # (2) shorten the wavefront: one pass over every type
    descend(stypes, 1)
    obj, rel, par, unr = best
    # partitions still unreachable within hop: attach to the nearest reached rst_o site (flagged: G0 error, the
    # owner of the plan moves the reset pin -- hard types: partition_types[T].reset.tap_um on a face)
    for p in sorted(unr):
        xy = part_reset_pin(P, p) if p in hard else P.to_die(p, choice[P.parts[p]["type"]])
        b = None
        for q in sorted(rel):
            if q in hard:
                continue
            for j, s_ in enumerate(face_sites(P, P.parts[q]["type"])):
                d = _man(P.to_die(q, s_["xy"]), xy)
                if b is None or d < b[0]:
                    b = (d, q, j)
        if b is not None:
            q = b[1]
            par[p] = (q, b[2], round(b[0], 1))
            rel[p] = rel[q] + (hdep[p] if p in hard else entry(p) + est[(P.parts[p]["type"],
                                                                          choice[P.parts[p]["type"]])])
    outs = {tn: set() for tn in stypes}
    for p, pr in par.items():
        if pr is not None:
            outs[P.parts[pr[0]]["type"]].add(pr[1])
    for tn, kept in (P.reset.get("keep_outs") or {}).items():
        outs[tn].update(kept)
    res = dict(root=root, root_type=rtype, choice=choice, parent=par, unreachable=unr, est_rel=rel,
               outs={tn: sorted(v) for tn, v in outs.items()}, hard=sorted(hard), hard_depth=hdep)
    cache["wf_solve"] = res
    return res


def in_pin(P, tn):
    """the wavefront reset IN pin (arst_n) of a soft type (type frame)."""
    native = bound_native_contract(P, tn)
    if native:
        return tuple(native["tree"]["root"])
    return tuple(wf_solve(P)["choice"][tn])


def out_pins(P, tn):
    """[(port, x, y)] the registered reset outputs of a soft type (uniform per type: every site any instance uses)."""
    native = bound_native_contract(P, tn)
    if native:
        # These are the actual emitted native wrapper's registered outputs.
        # Their captured tree sites must survive in io.tcl and the exact pin ABI.
        return [(f"rst_o_{k}",) + tuple(xy) for k, xy in enumerate(native["tree"].get("outs", []))]
    if not wavefront(P) or P.types[tn].get("hard"):
        return []
    sites = face_sites(P, tn)
    return [(f"rst_o_{k}",) + tuple(sites[j]["xy"]) for k, j in enumerate(wf_solve(P)["outs"].get(tn, []))]


START_DX_UM = 2.16      # start_i / start_o_<k> sit this far (then snapped) beside arst_n / rst_o_<k>


def start_broadcast(P):
    """OWNER DECISION 13c: the static schedule starts on an explicit START broadcast after reset (reset.start
    "broadcast", wavefront plans only).  START rides the reset wavefront: every soft partition registers start_i
    beside arst_n and re-drives start_o_<k> beside every rst_o_<k>; the same relay tree carries it (run relays
    u_srl_<k> on the reset relay sites).  Leaf / boundary / hard-core control state is released by the GATED tap reset
    rst_n_t<i> = registered (reset AND run): taps release at start_cycle + the published release offset of the
    partition (identical table, measured from the die `start` pin edge instead of rst_n); rst_o / start_o forward the
    raw reset / run.  start tied high == the plain wavefront."""
    return wavefront(P) and P.reset.get("start", "none") == "broadcast"


def _beside(P, tn, xy, taken):
    """a snapped pin site beside xy (start pin next to its reset pin), not on any taken site."""
    w, h = P.types[tn]["outline_um"]
    x, y = xy
    for k in (1, -1, 2, -2, 3, -3, 4, -4):
        for dx, dy in ((k * START_DX_UM, 0.0), (0.0, k * START_DX_UM)):
            q = _snap(P, min(max(x + dx, INSET_UM), w - INSET_UM), min(max(y + dy, INSET_UM), h - INSET_UM))
            if not any(abs(q[0] - a) < 1.0 and abs(q[1] - b) < 1.0 for a, b in taken):
                return q
    raise ResetError(f"type {tn}: no free start pin site beside {xy}")


def _start_sites(P, tn):
    cache = P.__dict__.setdefault("_reset_tree_cache", {})
    key = ("start_sites", tn)
    if key not in cache:
        import schema as S
        taken = [(x, y) for _, x, y in _plan_taps(P, tn)] + [tuple(in_pin(P, tn))] + \
            [(x, y) for _, x, y in out_pins(P, tn)] + [tuple(v[1:3]) for v in S.core_taps(P, tn)]
        sin = _beside(P, tn, in_pin(P, tn), taken)
        taken.append(sin)
        souts = []
        for n, x, y in out_pins(P, tn):
            q = _beside(P, tn, (x, y), taken)
            taken.append(q)
            souts.append(("start_o_" + n.rsplit("_", 1)[1],) + tuple(q))
        cache[key] = (sin, souts)
    return cache[key]


START_ROLES = ("bootstrap", "mission")


def bootstrap_consumers(P, tn):
    """Explicit raw-reset transports inside an otherwise mission-gated type.

    These are equal-depth copies of delivered reset, never raw die reset. The
    selected content must have a declared reset binding; other content and all
    unselected boundary/station consumers retain their existing mission role.
    """
    t = P.types[tn]; r = t.get('reset', {})
    buses = list(r.get('bootstrap_buses', []))
    contents = list(r.get('bootstrap_contents', []))
    if not buses and not contents:
        return [], []
    if not start_broadcast(P) or t.get('hard'):
        raise ResetError(f'type {tn}: bootstrap consumers need a soft START-broadcast wrapper')
    names = {b['name'] for b in t.get('buses', [])}
    names |= {s['name'] + suffix for s in t.get('ft_slots', []) for suffix in ('_i', '_o')}
    bad = sorted(set(buses)-names)
    cs = {c['inst']: c for c in t.get('contents', [])}
    if bad or set(contents)-set(cs):
        raise ResetError(f'type {tn}: unknown bootstrap consumers buses={bad}, contents={sorted(set(contents)-set(cs))}')
    for inst in contents:
        if not any(v in ('rst_n', 'rst') for v in cs[inst].get('bind', {}).values()):
            raise ResetError(f'type {tn}: bootstrap content {inst} has no declared reset binding')
    return sorted(set(buses)), sorted(set(contents))


def start_roles(P, tn):
    """(type role, {hard-core inst: role}) of a START-broadcast plan (reset fix 10-25, KV/QC bootstrap deadlock).
    Declared explicitly in the plan type's reset block, never inferred from names:
      reset.start_role "mission" (default): every consumer tap = registered (reset AND run) -- control state waits for
        START (decision 13c as before);
      reset.start_role "bootstrap": consumer taps = the registered RAW delivered wavefront reset (same depth, same
        published release offset, measured from rst_n), so boot / program-load / PHY calibration runs BEFORE the one
        global START; the type also publishes ONE registered local START tap start_t<leaf> (reset AND run, i.e. the
        exact release a MISSION tap would have) which the contents' declared mission-admission input must use.
      reset.core_start_roles {inst: role}: per hard-core reset target override.
    No second START, no timer, no raw die-reset bypass (the bootstrap reset is still the delivered wavefront relay),
    and private core reset stages are untouched (core targets keep their equal-depth relay)."""
    r = P.types[tn].get("reset", {})
    role = r.get("start_role", "mission")
    cores = dict(r.get("core_start_roles", {}))
    for v in [role] + list(cores.values()):
        if v not in START_ROLES:
            raise ResetError(f"type {tn}: start role {v!r} not in {START_ROLES}")
    if ("start_role" in r or cores) and not start_broadcast(P):
        raise ResetError(f"type {tn}: reset.start_role / core_start_roles need a wavefront plan with "
                         "reset.start = broadcast")
    if ("start_role" in r or cores) and P.types[tn].get("hard"):
        raise ResetError(f"type {tn}: hard partitions carry no generated reset tree (no start role)")
    return role, cores


def start_in_pin(P, tn):
    """the START IN pin (start_i) of a soft type of a start-broadcast plan (type frame), beside arst_n."""
    native = bound_native_contract(P, tn)
    if native:
        return tuple(native["tree"]["start_in"])
    return tuple(_start_sites(P, tn)[0])


def start_out_pins(P, tn):
    """[(port, x, y)] registered START outs start_o_<k> (beside rst_o_<k>, same neighbour)."""
    native = bound_native_contract(P, tn)
    if native:
        # Use the same deterministic local pin siting as the emitted ABI, with
        # captured reset output sites; never invoke the global wavefront solver.
        if not native["tree"].get("start"):
            return []
        entry, outs = _start_sites(P, tn)
        if tuple(entry) != tuple(native["tree"].get("start_in", ())):
            raise ResetError(f"type {tn}: native START output siting disagrees with captured entry site")
        return outs
    if not start_broadcast(P) or P.types[tn].get("hard"):
        return []
    return list(_start_sites(P, tn)[1])


def core_reset_targets(P, tn):
    """Active-low hard-core reset pins, transformed into the type frame, with legal local relay sites.

    Pin-table paths are plan-relative. The core LEF's ancestor containing that table identifies the plan directory;
    inline tables remain useful for self-contained plans/tests. Every target is padded to the same K as the taps.
    """
    import check
    import cores
    t = P.types[tn]
    domain_contract=None
    if t.get("clock",{}).get("native_domains") is not None:
        import native_clock_domains as NCD
        domain_contract=NCD.contract(P,tn)
    w, h = t["outline_um"]
    boxes = blockages(t)
    out = []
    for c in t.get("hard_cores", []):
        if c.get("reset_net"):
            continue   # QC-SLECTL-B: the core reset pin keeps its bound net (declared), not a wavefront target
        rfm = c.get("reset_from_master")
        if rfm is not None:
            # DIE-HBM-25 (HBM-047/048): a split piece of a reuse content bound WHOLE (one as-built leaf).  The plan
            # declares where the piece's reset pin comes from in the source master: kind "port" = the master's own
            # reset port (the die wavefront drives the master leaf pin, relay sited at this piece pin as usual);
            # kind "internal" = a master-internal reset net (e.g. the master's ot_rst_relay output) - not a die
            # wavefront consumer, the master's reset port is then an ordinary partition reset consumer.
            if rfm.get("kind") not in ("port", "internal") or not rfm.get("content") or not rfm.get("source"):
                raise ResetError(f"type {tn}: {c['inst']}: reset_from_master needs kind port|internal, content, source")
            if not any(d.get("inst") == rfm["content"] for d in t.get("contents", [])):
                raise ResetError(f"type {tn}: {c['inst']}: reset_from_master content {rfm['content']} not in contents")
            if rfm["kind"] == "internal":
                continue
        pd = None
        if c.get("pins_file") and not Path(c["pins_file"]).is_absolute():
            # The declaration's plan directory is authoritative. Pin tables may
            # use "core" rather than "module" metadata, and the LEF may be absent
            # during a logical bind, so do not infer context from either one.
            if P.path is not None:
                plan_dir = Path(P.path).resolve().parent
                if (plan_dir / c["pins_file"]).is_file():
                    pd = plan_dir
            lef = cores.resolve(c.get("lef", "."))
            if pd is None:
                pd = next((a for a in lef.parents if (a / c["pins_file"]).is_file()), None)
            if pd is None:
                # Views may live outside their plan (physical/ref_tile); resolve the plan-relative pin table by
                # its declared module, and refuse differing candidates instead of silently choosing another die.
                base = HERE.parents[1] / "physical" / "die_plan"
                paths = list(base.glob("*/" + c["pins_file"])) + list(base.glob("*/*/" + c["pins_file"]))
                paths = [p for p in paths if isinstance((j := json.loads(p.read_text())), dict)
                         and (j.get("module") or j.get("core")) == c.get("module")]
                if paths and len({p.read_bytes() for p in paths}) == 1:
                    pd = paths[0]
                    for _ in Path(c["pins_file"]).parts:
                        pd = pd.parent
                else:
                    raise ResetError(f"type {tn}: cannot uniquely resolve hard-core pin table {c['pins_file']} from {lef}")
        for name, _layer, x, y in check.core_pins(c, pd):
            if name not in ("rst_n", "arst_n", "reset_n"):
                continue
            cw, ch = c["outline_um"]
            o = c.get("orient", "R0")
            x, y = {"R0": (x, y), "MX": (x, ch-y), "MY": (cw-x, y), "R180": (cw-x, ch-y),
                    "R90": (ch-y, x), "R270": (y, cw-x), "MXR90": (y, x), "MYR90": (ch-y, cw-x)}[o]
            ox, oy = c["origin_um"]
            dx, dy = c.get("track_offset_um", [0, 0])
            pin = (ox + dx + x, oy + dy + y)
            site = push_off(pin, boxes, (CLEAR_UM, CLEAR_UM, w-CLEAR_UM, h-CLEAR_UM))
            if not _free(site, boxes, (CLEAR_UM, CLEAR_UM, w-CLEAR_UM, h-CLEAR_UM)):
                raise ResetError(f"type {tn}: no legal reset relay site for {c['inst']}.{name}")
            if _man(pin, site) > relay_um(P, tn) - MARGIN_UM:
                raise ResetError(f"type {tn}: reset relay -> {c['inst']}.{name} exceeds reach ({_man(pin, site):g} um)")
            if domain_contract is not None:
                roots={root for (inst,module,_),root in domain_contract['macro_pins'].items()
                       if inst==c['inst'] and module==c['module']}
                if len(roots)!=1:raise ResetError(f"type {tn}: reset target {c['inst']} lacks one actual native clock root")
                domain_root=next(iter(roots))
            else:domain_root=None
            out.append(dict(inst=c["inst"], pin=name, pin_um=list(pin), xy=list(site),
                            internal_depth=int(c.get("reset", {}).get("depth", 1))))
            if c.get("physical_inst") and c["physical_inst"] != c["inst"]:
                # KW-FIX-1/S81PF 11-02: the kit netlist names the core by its declared physical identity (bound kit:
                # u_bound.u_u_r0_u_e0 for plan u_r0.u_e0); reset_tree.tcl resolves either name
                out[-1]["physical_inst"] = c["physical_inst"]
            if domain_root is not None:
                out[-1]['native_clock_root']=domain_root
                out[-1]['native_clock_status']='GEOMETRY PREP; period/reset phase qualification separate'
    return out


def wavefront_min_depth(t):
    """Optional per-type physical reset padding; never shortens the built tree.

    Preserve a published release cohort when moving macros makes the legal
    reset topology shallower. Data and K pipelines are unaffected.
    """
    depth = t.get("reset", {}).get("wavefront_min_depth")
    if depth is not None and (type(depth) is not int or depth < 0):
        raise ResetError("reset.wavefront_min_depth must be a nonnegative integer")
    return depth


def _wf_type_tree(P, tn):
    cache = P.__dict__.setdefault("_reset_tree_cache", {})
    key = ("wf_tree", tn)
    if key not in cache:
        t = P.types[tn]
        w, h = t["outline_um"]
        taps = consumer_taps(P, tn)
        outs = out_pins(P, tn)
        core_rst = core_reset_targets(P, tn)
        pts = list(taps) + [(f"o{k}", x, y) for k, (_, x, y) in enumerate(outs)]
        for k, c in enumerate(core_rst):
            c["tap"] = len(pts)
            pts.append((f"core_rst{k}", *c["xy"]))
        cs = column_spec(P, tn)
        column = None
        if cs and cs["at"] is not None:
            ent = tuple(in_pin(P, tn))
            far = [s["xy"] for s in face_sites(P, tn)[:2] if _man(s["xy"], ent) > 1.0]
            used = {(round(x, 3), round(y, 3)) for _, x, y in outs}
            column = dict(axis=cs["axis"], end=far[0] if far and (round(far[0][0], 3), round(far[0][1], 3)) in used
                          else None)
        topo = topology(pts, in_pin(P, tn), reach=relay_um(P, tn), boxes=blockages(t),
                        box_out=(CLEAR_UM, CLEAR_UM, w - CLEAR_UM, h - CLEAR_UM), walls=walls(P, tn),
                        avoid_cores=bool(P.reset.get("relay_avoid_cores")), column=column)
        T = assign(topo, wavefront_min_depth(t), pad_spread=bool(P.reset.get("relay_pad_spread")), boxes=blockages(t),
                   box_out=(CLEAR_UM, CLEAR_UM, w-CLEAR_UM, h-CLEAR_UM), walls=walls(P, tn),
                   site_names=t.get("reset_relay_names") == "site")
        T = resite_type(P, tn, T)
        T.update(n_clock_taps=len(_taps(P, tn)), n_reset_consumers=len(taps),
                 local_reset_taps=bool(t.get("reset", {}).get("local_taps_um")), outs=[[x, y] for _, x, y in outs], core_resets=core_rst)
        cache[key] = T
    import copy
    return copy.deepcopy(cache[key])


def wf_plan(P):
    """the published wavefront: per type (IN pin, outs, depth K, entry), per partition (parent, parent rst_o port,
    die hop, entry stages, release cycle = clocks after die rst_n deasserts at which its taps and rst_o release)."""
    cache = P.__dict__.setdefault("_reset_tree_cache", {})
    if "wf_plan" in cache:
        return cache["wf_plan"]
    sol = wf_solve(P)
    N = sync_stages(P)
    types = {}
    for tn in sorted({P.parts[n]["type"] for n in P.parts if n not in sol["hard"]}):
        T = for_type(P, tn)
        types[tn] = dict(in_um=[round(v, 4) for v in in_pin(P, tn)], outs=[[o[0], round(o[1], 4), round(o[2], 4)]
                         for o in out_pins(P, tn)], depth_K=T["depth"], entry=T["entry"],
                         entry_stages=entry_stages(T), release_after_pin=release_clocks(T), relays=len(T["relays"]),
                         max_hop_um=T["max_hop_um"], core_resets=T.get("core_resets", []))
        if T.get("local_reset_taps"):
            types[tn].update(local_taps_um=P.types[tn]["reset"]["local_taps_um"],
                             clock_ports=len(_taps(P, tn)), reset_consumers=consumer_count(T))
        if T.get("start_role"):
            types[tn].update(start_role=T["start_role"], start_tap=T["start_tap"],
                             core_start_roles={c["inst"]: T["tap_roles"][c["tap"]] for c in T.get("core_resets", [])})
        if T.get('bootstrap_taps'):
            types[tn].update(bootstrap_buses=T['bootstrap_buses'], bootstrap_contents=T['bootstrap_contents'],
                             bootstrap_reset_relays=len(T['bootstrap_taps']),
                             bootstrap_release_after_pin=release_clocks(T))
    kids = {}
    for p, pr in sol["parent"].items():
        if pr is not None:
            kids.setdefault(pr[0], []).append(p)
    parts, st = {}, [sol["root"]]
    while st:
        p = st.pop()
        pr = sol["parent"][p]
        tn = P.parts[p]["type"]
        base = 0 if pr is None else parts[pr[0]]["release"]
        if p in sol["hard"]:
            rel = base + sol["hard_depth"][p]
            ent, K = 1, sol["hard_depth"][p] - 1
        else:
            rel = base + types[tn]["release_after_pin"]
            ent, K = types[tn]["entry_stages"], types[tn]["depth_K"]
        row = dict(type=tn, parent=None if pr is None else pr[0], entry_stages=ent, depth_K=K, release=rel)
        if tn in types:
            row["core_release"] = {}
            for c in types[tn].get("core_resets", []):
                target = c['inst'] + '.' + c['pin']
                root = c.get('native_clock_root', 'clk')
                if root == 'clk':
                    row['core_release'][target] = rel + c['internal_depth']
                else:
                    # Keep the real pin/relay target in types[].core_resets and
                    # its primary raw-pin arrival, but a native-domain internal
                    # synchroniser has no core-cycle release without a proven
                    # frequency/phase/reset relation. Never silently drop it.
                    row['core_release'][target] = None
                    row.setdefault('native_release', {})[target] = dict(
                        status='PENDING', native_clock_root=root, core_cycle_release=None,
                        raw_pin_arrival_core_cycles=rel, internal_depth_native_cycles=c['internal_depth'],
                        qualification='PREP raw-pin geometry only; native period/phase/reset relation unqualified')
        if pr is None:
            row.update(source=f"die {die_reset_port(P)} (asynchronous: the ONE root synchroniser" +
                       (f" + PLL lock qualifier, +{lock_stages(P)} stages)" if lock_stages(P) else ")"))
        else:
            q = pr[0]
            k = sol["outs"][P.parts[q]["type"]].index(pr[1])
            row.update(source=f"{q}.rst_o_{k}", hop_um=pr[2])
        parts[p] = row
        st += sorted(kids.get(p, []))
    out = dict(release="wavefront", sync_stages=N, root=sol["root"], root_type=sol["root_type"],
               hop_um=hop_um(P), relay_um=relay_um(P), unreachable=sol["unreachable"],
               max_release=max([r["release"] for r in parts.values()] or [0]),
               max_die_hop_um=max([r.get("hop_um", 0.0) for r in parts.values()] or [0.0]),
               long_hops=sorted([[p, r["source"], r["hop_um"]] for p, r in parts.items()
                                 if r.get("hop_um", 0.0) > hop_um(P) + 1e-6], key=lambda x: -x[2]),
               types=types, parts=dict(sorted(parts.items())),
               note="OWNER DECISION 13 (2026-10-24): one root 2-flop synchroniser; neighbour wavefront; release = "
                    "clocks after die rst_n deasserts at which the partition's taps (and its rst_o) release; the "
                    "static schedule starts with an explicit start broadcast after reset")
    pending = [dict(part=part, target=target, native_clock_root=item['native_clock_root'])
               for part, row in sorted(parts.items()) for target, item in row.get('native_release', {}).items()]
    if pending:
        out['release_qualification'] = dict(verdict='PENDING', native_targets=pending,
            reason='FULL release qualification requires the actual native clock/reset relation; primary raw-pin geometry remains PREP')
    if start_broadcast(P):
        hard_parts = sorted(p for p in parts if p in sol["hard"])
        out["start"] = dict(
            mode="broadcast", die_pin="start", sync_stages=N,
            types={tn: dict(in_um=[round(v, 4) for v in start_in_pin(P, tn)],
                            outs=[[o[0], round(o[1], 4), round(o[2], 4)] for o in start_out_pins(P, tn)])
                   for tn in types},
            hard_parts_raw_reset=hard_parts,
            bootstrap_types=sorted(tn for tn, ty in types.items() if ty.get("start_role") == "bootstrap"),
            roles_note="start_role mission: taps release at max(release[p], S + release[p]); start_role bootstrap: "
                       "taps (and core resets with role bootstrap) release at release[p] (raw delivered wavefront, "
                       "boot runs before START), the local START tap start_t<start_tap> at S + release[p] gates the "
                       "contents' declared mission admission.  One START, no timer, no die-reset bypass.",
            note="OWNER DECISION 13c: START rides the reset wavefront (start_i / start_o_<k> beside arst_n / "
                 "rst_o_<k>, run relays on the reset relay sites).  Soft partition p's control state (leaves, "
                 "boundary epochs, hard-core resets) releases at  max(release[p], S + release[p])  clocks, S = the "
                 "die start pin's rising edge relative to rst_n deassert; i.e. the START offsets ARE the published "
                 "release offsets.  Hard partitions (prebuilt, no start pin) see the raw reset only.")
    receipt = getattr(P, "_native_reset_release_receipt", None)
    if receipt is not None:
        try:
            import head_native_release
            head_native_release.qualify(P, out, receipt)
        except (ValueError, KeyError, OSError, TypeError) as ex:
            raise ResetError("native reset release receipt refused: " + str(ex)) from ex
    if pending and out["release_qualification"]["verdict"] == "PENDING":
        caution = ' Native-domain internal reset/START release remains PENDING; primary raw-pin arrival is PREP only.'
        out['note'] += caution
        if 'start' in out:
            out['start']['note'] += caution
            out['start']['roles_note'] += caution
    cache["wf_plan"] = out
    return out


def wf_die_rtl(P, ind="    "):
    """die top: the root partition's arst_n = rst_n (die pin); every other arst_n = its parent's rst_o_<k>.
    Returns (wire lines, {part: arst_n net}, {part: {port: net}})."""
    W = wf_plan(P)
    lines = [f"{ind}// OWNER DECISION 13 reset wavefront: root {W['root']} (ONE root synchroniser on rst_n); every "
             f"partition re-drives a registered reset to its neighbours; latest release {W['max_release']} clocks"]
    arst, outs = {}, {}
    for p, r in W["parts"].items():
        if r["parent"] is None:
            arst[p] = die_reset_port(P)
        else:
            net = "rstw_" + re.sub(r"\W", "_", r["source"])
            if net not in {n for d in outs.values() for n in d.values()}:
                lines.append(f"{ind}wire {net};")
            outs.setdefault(r["parent"], {})[r["source"].split(".")[-1]] = net
            arst[p] = net
    return lines, arst, outs


def wf_die_start(P, ind="    "):
    """die top START wiring (decision 13c; start_broadcast plans): the root partition's start_i = the die `start` pin,
    every other soft partition's start_i = its parent's start_o_<k> (the k of its rst_o parent).  Returns (wire lines,
    {part: start_i net}, {part: {start_o port: net}}).  Hard partitions have no start pin."""
    W = wf_plan(P)
    lines = [f"{ind}// OWNER DECISION 13c START broadcast: rides the reset wavefront (start_o_<k> beside rst_o_<k>)"]
    sin, souts = {}, {}
    for p, r in W["parts"].items():
        if r["type"] not in W["types"]:
            continue                                  # hard leaf: raw reset only
        if r["parent"] is None:
            sin[p] = "start"
        else:
            src = r["source"].replace(".rst_o_", ".start_o_")
            net = "stw_" + re.sub(r"\W", "_", src)
            if net not in {n for d in souts.values() for n in d.values()}:
                lines.append(f"{ind}wire {net};")
            souts.setdefault(r["parent"], {})[src.split(".")[-1]] = net
            sin[p] = net
    return lines, sin, souts


def wf_open_outs(P):
    """KV-KITS-2 (COORD 10-27 03:41): the registered wavefront outs a soft INSTANCE leaves unconnected, with the plan
    proof.  rst_o_<k> / start_o_<k> are uniform per TYPE (out_pins: every out site ANY instance of the type uses), so an
    instance whose wavefront children (wf_solve parent table) do not use site k leaves rst_o_<k> open, and start_o_<k>
    is open when no SOFT child uses it (hard partitions take the raw reset only, no start pin).  Each such output is
    driven only by its own pin relay flop (ot_dp_rrelay q -> port; face_guard 'shared' check on the kit), so an
    unloaded port is functionally dead on that instance.  -> {part: {port: reason}} (soft parts only)."""
    if not wavefront(P):
        return {}
    W = wf_plan(P)
    used, soft_used = {}, {}
    for p, r in W["parts"].items():
        if r["parent"] is None:
            continue
        q, port = r["source"].split(".")
        used.setdefault(q, set()).add(port)
        if r["type"] in W["types"]:
            soft_used.setdefault(q, set()).add(port.replace("rst_o_", "start_o_"))
    res = {}
    for p, r in W["parts"].items():
        tn = r["type"]
        if tn not in W["types"]:
            continue
        o = {}
        for n, _x, _y in out_pins(P, tn):
            if n not in used.get(p, set()):
                o[n] = (f"reset wavefront: {tn} out site {n} is used by another instance of the type; {p} has no "
                        "wavefront child on it (wf_solve parent table); driver = its own pin relay flop only")
        for n, _x, _y in start_out_pins(P, tn):
            if n not in soft_used.get(p, set()):
                why = ("no wavefront child" if n.replace("start_o_", "rst_o_") not in used.get(p, set())
                       else "only HARD children (raw reset, no start_i)")
                o[n] = (f"START broadcast: {p} has {why} on {n} (wf_solve parent table); driver = its own run relay "
                        "flop only")
        if o:
            res[p] = o
    return res


_WF_INST = re.compile(r"^    (\w+)(?: #\(.*?\))? (\w+) \(\n(.*?)\n    \);", re.S | re.M)


def write_wf_open_pads(P, f, top_text, sv_id, fresh=False):
    """KV-KITS-2 (COORD 10-27 03:41): declare, with the plan proof, the type-uniform wavefront outs
    (rst_o_<k> / start_o_<k>) an instance leaves open (wf_open_outs), as instance entries of the strict port-bind's
    default pad file <top>.pads.json (spare OUTPUT ports: open, never tied).  Only ports the die top really leaves
    unconnected (absent, or an empty `.port()`) are declared; anything else stays OUTPUT_OPEN.  Shared by the as-built
    binder (bind.py) and the generated die top (gen_rtl, DIE-HEAD-4b).  fresh: drop a stale pad file first (gen_rtl
    owns the whole file).  -> number of declared ports; ValueError on a port the top connects."""
    oo = wf_open_outs(P)
    pf = Path(str(f) + ".pads.json")
    if fresh and pf.exists():
        pf.unlink()
    doc = json.loads(pf.read_text()) if pf.exists() else {}
    inst_m, body = {}, {}
    for m in _WF_INST.finditer(top_text):
        inst_m[m.group(2)], body[m.group(2)] = m.group(1), m.group(3)
    ent = doc.setdefault("instances", {})
    n = 0
    for p, ports in sorted(oo.items()):
        name = sv_id(p)
        if name not in inst_m:
            raise ValueError(f"wavefront open outs: instance {name} not in the bound top")
        for port, why in sorted(ports.items()):
            if re.search(rf"\.{port}\(\s*[^\s)]", body[name]):
                raise ValueError(f"wavefront open outs: {name}.{port} is connected in the top but wf_open_outs "
                                 "says it has no child")
            e = ent.setdefault(name, dict(master=inst_m[name], reason="", ports={}))
            e["ports"][port] = [[0, 0]]
            e.setdefault("wavefront_open", {})[port] = why
            n += 1
    for name, e in ent.items():
        if e.get("wavefront_open"):
            e["reason"] = ("KV-KITS-2 wavefront open outs: type-uniform registered reset/START out pins with no "
                           "wavefront child on this instance (reset_tree.wf_open_outs proof per port); open, "
                           "never tied")
    if n:
        pf.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    return n


# ----------------------------------------------------------------------------------------------- RTL / TCL
def relay_sv():
    """the ot_dp_rrelay module text (held in gen_rtl.CELLS, the one copy of the kit cells)."""
    import gen_rtl
    return re.search(r"(//[^\n]*ot_dp_rrelay.*?\nendmodule\n)", gen_rtl.CELLS, re.S).group(1)


_TAPQ = re.compile(r"^rst_n_t(\d+)$")


def start_raw_requests(t):
    """rr_t<i> nets named as raw_reset by the plan START transport of type dict t (landing_writer_start /
    landing_reader_start).  In a MISSION-role type rst_n_t<i> is gated (reset AND run), so a START relay that must
    run before the gate opens takes the same-depth raw copy u_rrl_<k>_r; start_relays emits it only when asked."""
    out = set()
    clock = t.get("clock") or {}
    for key in ("landing_writer_start", "landing_reader_start"):
        for branch in ((clock.get(key) or {}).get("branches") or {}).values():
            for stage in (branch.get("stages") or []) if isinstance(branch, dict) else []:
                if re.fullmatch(r"rr_t\d+", str(stage.get("raw_reset") or "")):
                    out.add(stage["raw_reset"])
    return sorted(out)


def start_relays(T):
    """START broadcast (decision 13c, T['start']): the relay list with the run relays and the gated tap stages.
    Nets: rr_t<i> raw reset, rn_* run (rn_ + raw net; run_root at the entry).  A CONSUMER tap (clock tap / hard-core
    reset target, not an rst_o) keeps its relay instance u_rrl_<k>, now loading (raw AND run) of its parent: rst_n_t<i>
    releases on the same cycle depth as before, measured from the later of reset and START.  Raw / run copies
    (u_rrl_<k>_r, u_srl_<k>) exist only where something downstream (a deeper relay or an rst_o / start_o) needs them.
    [{name, d (SV expression), q, dlab (parent net label for the hop check), xy, kind, depth, role}]"""
    nck = consumer_count(T)
    outs = set(range(nck, nck + len(T.get("outs", []))))

    def raw(n):
        m = _TAPQ.match(n)
        return f"rr_t{m.group(1)}" if m else n

    def run(n):
        return "run_root" if n == "rst_root_n" else "rn_" + raw(n)
    used = {raw(r["d"]) for r in T["relays"]} | {f"rr_t{i}" for i in outs}
    used |= set(T.get("start_raw_used", ()))     # plan START stages that name a raw wavefront tap (mission types)
    roles = T.get("tap_roles", {})
    def role(i):
        # Actual emission trees use integer indices; JSON receipts carry string keys.
        if i in roles and str(i) in roles and roles[i] != roles[str(i)]:
            raise ResetError(f"conflicting integer/string reset tap role at {i}")
        return roles.get(i, roles.get(str(i), "mission"))
    out = []
    for r in T["relays"]:
        m = _TAPQ.match(r["q"])
        base = dict(xy=r["xy"], kind=r["kind"], depth=r["depth"], dlab=r["d"], tap=r.get("tap"))
        srl = r["name"].replace("u_rrl", "u_srl", 1)
        if m and int(m.group(1)) not in outs:
            i = int(m.group(1))
            if role(i) == "bootstrap":
                # BOOTSTRAP consumer: the registered raw delivered reset (same flop count => same release offset)
                out.append(dict(base, name=r["name"], d=raw(r["d"]), q=r["q"], role="boot"))
            else:
                out.append(dict(base, name=r["name"], d=raw(r["d"]), run=run(r["d"]), q=r["q"], role="gated"))
            if T.get("start_tap") == i:
                # the type's ONE local START tap: registered (reset AND run) beside the leaf tap relay
                out.append(dict(base, name=r["name"] + "_g", d=raw(r["d"]), run=run(r["d"]), q=f"start_t{i}",
                                role="gated"))
            if i in T.get('bootstrap_taps', []):
                out.append(dict(base, name=r['name'] + '_b', d=raw(r['d']), q=f'rst_boot_t{i}',
                                role='bootstrap_transport'))
            if raw(r["q"]) in used:
                out.append(dict(base, name=r["name"] + "_r", d=raw(r["d"]), q=raw(r["q"]), role="raw"))
                out.append(dict(base, name=srl, d=run(r["d"]), q=run(r["q"]), role="run"))
        else:
            out.append(dict(base, name=r["name"], d=raw(r["d"]), q=raw(r["q"]), role="raw"))
            out.append(dict(base, name=srl, d=run(r["d"]), q=run(r["q"]), role="run"))
    return out


LOCK_SRC = "pll_locked_i"     # the root type's PLL lock net (bind.py aliases the declared lock leaf output to it)


def _root_entry_lines(T, ind, src, lock_src, note):
    """root entry: u_rst_root (async input = the raw pad ONLY) [-> u_rst_lockq PLL lock qualifier] -> rst_root_n."""
    ns = T["sync_stages"]
    lk = T.get("lock")
    if not lk:
        return [f"{ind}ot_dp_rsync_s{ns} u_rst_root (.clk(clk), .async_rst_n({src}), .sync_rst_n(rst_root_n));  // {note}"]
    return [f"{ind}wire rst_por_n;",
            f"{ind}ot_dp_rsync_s{ns} u_rst_root (.clk(clk), .async_rst_n({src}), .sync_rst_n(rst_por_n));  // {note} "
            "(async input = the die reset pad ONLY)",
            f"{ind}ot_dp_lockq #(.STABLE({lk['stable']})) u_rst_lockq (.clk(clk), .d(rst_por_n), .locked({lock_src}), "
            f".q(rst_root_n));  // PLL lock qualifier ({lk['inst']}.{lk['pin']}): 2-flop sync + {lk['stable']}-cycle "
            "stable count, sticky synchronous release (loss of lock after boot = HOST status, not a die reset)"]


def relay_cell(T, r, gated=False):
    nck = consumer_count(T)
    external = set(range(nck, nck + len(T.get("outs", []))))
    # A tap may also have raw/run copies; all copies at external output sites stay plain.
    driven = T.get("relay_driver") and r.get("tap") not in external
    if gated:
        return "ot_dp_rgate_drive" if driven else "ot_dp_rgate"
    if T.get("relay_lockup") == "negedge" and not driven and not str(r.get("q", "")).startswith("rst_n_t"):
        return "ot_dp_rrelay_nl"     # CLK form #7: internal relay->relay hop only (gen_rtl.LOCKUP_CELLS)
    return "ot_dp_rrelay_drive" if driven else "ot_dp_rrelay"


RELAY_LOCKUP_FORMS = ("negedge", "latch")


def relay_lockup_form(P):
    """the plan's reset.relay_lockup form ("negedge" | "latch"), None when absent."""
    cfg = P.reset.get("relay_lockup")
    return cfg.get("form") if isinstance(cfg, dict) and cfg else None


# RLK-1108 (DIE-HBM-92-RLK 11-08, opt-in reset.relay_lockup {"form": "latch"}): the hop LOCKUP LATCH form.  CLK form
# #7's negedge re-launch left only T/2 - W of setup for a FULL relay hop (HBM q_spb1 pilot, GRT gate TT: u_rrl_28 clk_t5
# negedge -> u_rrl_30, 377 um, -84.84 ps).  Here every relay stays a plain posedge ot_dp_rrelay (one cycle, so K and the
# release cycle are unchanged) and each INTERNAL relay -> relay hop (launch relay q = rst_rl_*: the same hops the
# negedge form covers; leaf taps rst_n_t<k>, out relays, the entry pin register and START plans stay plain) gets one
# transparent-low ot_dp_lk (gen_rtl.CELLS, the TYPE-SAFE-1 ft hop latch) before the capture relay's d: instance
# u_fl_rst<suffix> so clock_taps.tcl's hop-latch follow-D pass clocks it from the LAUNCH relay's tap (CRPR on the
# relay -> latch check), and tcl_text places it FIRM at the planned hop midpoint.  The latch -> capture check gets ~T/2
# of extra hold whatever taps the relays land on; setup is the half hop after the falling edge (T/2 - W for <= ~200
# um) or, with borrowing, the whole hop within T - W.  0 cycles: lec.py latch_to_wire, bind_verify ot_dp_lk stages 0.
def lockup_latch_names(relay_name):
    """(latch instance, latch q net) of the hop lockup latch in front of relay relay_name (latch form)."""
    suf = relay_name[len("u_rrl"):] if relay_name.startswith("u_rrl_") else "_" + re.sub(r"\W", "_", relay_name)
    return "u_fl_rst" + suf, "rst_lk" + suf


def lockup_hops(T):
    """latch form: [relay] whose d is an INTERNAL relay's q (launch relay q not rst_n_t*), i.e. the hops that get an
    ot_dp_lk; [] for every other tree (absent / negedge)."""
    if T.get("relay_lockup") != "latch" or T.get("start"):
        return []
    internal = {r["q"] for r in T["relays"] if not str(r["q"]).startswith("rst_n_t")}
    return [r for r in T["relays"] if r["d"] in internal]


def relay_lockup(P, tn):
    """CLK FORM #7 / RLK-1108 (opt-in): reset.relay_lockup = {"form": "negedge" | "latch", "types": [type, ...]}.  True
    when type tn's internal relay hops get the lockup form (negedge: ot_dp_rrelay_nl relays; latch: an ot_dp_lk per hop,
    lockup_latch_names).  Absent = False (every tree and kit byte-identical)."""
    cfg = P.reset.get("relay_lockup")
    if not cfg:
        return False
    if not isinstance(cfg, dict) or cfg.get("form") not in RELAY_LOCKUP_FORMS or not isinstance(cfg.get("types"), list):
        raise ResetError('reset.relay_lockup must be {"form": "negedge" | "latch", "types": [type, ...]}')
    bad = sorted(set(cfg["types"]) - set(P.types))
    if bad:
        raise ResetError(f"reset.relay_lockup names unknown types {bad[:5]}")
    if tn not in cfg["types"]:
        return False
    if P.reset.get("relay_driver"):
        raise ResetError(f"type {tn}: reset.relay_lockup and reset.relay_driver are exclusive")
    if start_broadcast(P):
        raise ResetError(f"type {tn}: reset.relay_lockup does not support START broadcast plans")
    return True


def rtl_lines(T, ind="    ", src="arst_n", start_src="start_i", lock_src=LOCK_SRC):
    """SystemVerilog body lines: entry stage + relays.  Declares rst_n_t<i> for every tap.  With T['start'] (decision
    13c START broadcast) the run entry / relays and the gated taps (start_relays) are emitted as well."""
    if T.get("start"):
        return _rtl_lines_start(T, ind, src, start_src, lock_src)
    ns = T["sync_stages"]
    if T["entry"] == "sync" and ns not in (2, 3):
        raise ResetError(f"reset_tree: sync_stages {ns} (root synchronisers exist for 2 or 3)")
    taps = list(range(len(T["taps"])))
    out = [f"{ind}// OWNER RESET RULE 10-24 (tools/die_plan/reset_tree.py): entry {T['entry']} + synchronous relay tree, "
           f"depth {T['depth']} to all {len(taps)} taps, hops <= {T['reach_um']:g} um; release {release_clocks(T)} "
           f"clocks after the entry pin",
           f"{ind}wire rst_root_n;"]
    if T["entry"] == "sync":
        out += _root_entry_lines(T, ind, src, lock_src, "the region's ONE root synchroniser: its async input is the "
                                 "only reset false path")
    else:
        out.append(f"{ind}ot_dp_rrelay u_rst_in (.clk(clk), .d({src}), .q(rst_root_n));  "
                   "// pin register of the SYNCHRONOUS reset input (die reset tree)")
    out += [f"{ind}" + ("(* keep = 1 *) " if T.get("local_reset_taps") else "") + f"wire rst_n_t{i};" for i in taps]
    nck = consumer_count(T)
    oq = out_relays(T)
    lkd = {r["name"]: lockup_latch_names(r["name"]) for r in lockup_hops(T)}
    for r in T["relays"]:
        if not r["q"].startswith("rst_n_t"):
            out.append(f"{ind}wire {r['q']};")
        where = f"depth {r['depth']} @ ({r['xy'][0]:.1f}, {r['xy'][1]:.1f})"
        if r["name"] in lkd:
            # RLK-1108 hop lockup latch (latch form): launch relay q -> transparent-low latch -> this relay's d
            li, lq = lkd[r["name"]]
            out.append(f"{ind}wire {lq};")
            out.append(f"{ind}ot_dp_lk #(.W(1)) {li} (.clk(clk), .d({r['d']}), .q({lq}));  "
                       f"// hop lockup latch {r['d']} -> {r['name']} (0 cycles, at the hop midpoint)")
            r = dict(r, d=lq)
        if r["q"] in oq:
            k = oq[r["q"]]
            # DIE-S81-27 (COORD 10-29 11:28): the registered reset OUT has its OWN relay (drives only the port); the
            # tap net rst_n_t<j> gets a same-d copy for in-type loads (landing rings / collectors at the out site),
            # kept like any relay whose tap has no sinks.  Same d, same depth => same release cycle.
            out.append(f"{ind}{relay_cell(T, r)} {r['name']} (.clk(clk), .d({r['d']}), .q(rst_o_{k}));  "
                       f"// registered reset out rst_o_{k} (wavefront, dedicated relay): {r['kind']} tap {r['tap']} {where}")
            out.append(f"{ind}{relay_cell(T, r)} {r['name']}_t (.clk(clk), .d({r['d']}), .q({r['q']}));  "
                       f"// tap-net copy of {r['name']} for in-type loads: {where}")
        else:
            out.append(f"{ind}{relay_cell(T, r)} {r['name']} (.clk(clk), .d({r['d']}), .q({r['q']}));  "
                       f"// {r['kind']} tap {r['tap']} {where}")
    for k in range(len(T.get("outs", []))):
        if f"rst_n_t{nck + k}" not in oq:
            out.append(f"{ind}assign rst_o_{k} = rst_n_t{nck + k};  // registered reset out (wavefront): the relay at "
                       f"({T['outs'][k][0]:.1f}, {T['outs'][k][1]:.1f}), released with the taps")
    return out


def out_relays(T):
    """{tap net rst_n_t<j>: k} for the non-START wavefront outs rst_o_<k> whose tap j has a relay in T['relays']."""
    if T.get("start"):
        return {}
    nck = consumer_count(T)
    qs = {r["q"] for r in T["relays"]}
    return {f"rst_n_t{nck + k}": k for k in range(len(T.get("outs", []))) if f"rst_n_t{nck + k}" in qs}


def _rtl_lines_start(T, ind, src, start_src, lock_src=LOCK_SRC):
    ns = T["sync_stages"]
    if T["entry"] == "sync" and ns not in (2, 3):
        raise ResetError(f"reset_tree: sync_stages {ns} (root synchronisers exist for 2 or 3)")
    taps = list(range(len(T["taps"])))
    out = [f"{ind}// OWNER RESET RULE 10-24 + DECISION 13c (tools/die_plan/reset_tree.py): entry {T['entry']} + "
           f"synchronous relay tree carrying reset AND run (START broadcast), depth {T['depth']} to all {len(taps)} "
           f"taps, hops <= {T['reach_um']:g} um; every tap releases {release_clocks(T)} clocks after the LATER of the "
           "entry reset release and the entry START",
           f"{ind}wire rst_root_n, run_root;"]
    if T["entry"] == "sync":
        out += _root_entry_lines(T, ind, src, lock_src, "the die's ONE root reset synchroniser: its async input is "
                                 "the only reset false path")
        out.append(f"{ind}ot_dp_rsync_s{ns} u_run_root (.clk(clk), .async_rst_n({start_src}), .sync_rst_n(run_root));  "
                   "// the die's ONE START synchroniser (die start pin, asynchronous level): the only START false path")
    else:
        out.append(f"{ind}ot_dp_rrelay u_rst_in (.clk(clk), .d({src}), .q(rst_root_n));  "
                   "// pin register of the SYNCHRONOUS reset input (neighbour's rst_o)")
        out.append(f"{ind}ot_dp_rrelay u_run_in (.clk(clk), .d({start_src}), .q(run_root));  "
                   "// pin register of the SYNCHRONOUS START input (neighbour's start_o)")
    nck = consumer_count(T)
    outs = set(range(nck, nck + len(T.get("outs", []))))
    out += [f"{ind}" + ("(* keep = 1 *) " if T.get("local_reset_taps") else "") + f"wire rst_n_t{i};" for i in taps if i not in outs]     # consumer taps (gated / boot)
    if T.get("start_role"):
        out.append(f"{ind}// START role {T['start_role']}" + (
            f": consumer taps = registered RAW wavefront reset (boot before START); start_t{T['start_tap']} = the "
            "local registered START tap (reset AND run) for the declared mission-admission input"
            if T["start_role"] == "bootstrap" else ": consumer taps = registered (reset AND run)") +
            ("; core overrides " + ", ".join(f"t{k}:{v}" for k, v in sorted(T["tap_roles"].items(), key=lambda item: int(item[0]))
                                             if v != T["start_role"]) if any(v != T["start_role"] for v in
                                                                              T["tap_roles"].values()) else ""))
    declared = {f"rst_n_t{i}" for i in taps} | {"rst_root_n", "run_root"}
    for r in start_relays(T):
        if r["q"] not in declared:
            out.append(f"{ind}wire {r['q']};")
            declared.add(r["q"])
        cell = relay_cell(T, r, gated=r["role"] == "gated")
        run = f", .run({r['run']})" if r["role"] == "gated" else ""
        out.append(f"{ind}{cell} {r['name']} (.clk(clk), .d({r['d']}){run}, .q({r['q']}));  "
                   f"// {r['role']} {r['kind']} tap {r['tap']} depth {r['depth']} @ ({r['xy'][0]:.1f}, {r['xy'][1]:.1f})")
    for k in range(len(T.get("outs", []))):
        out.append(f"{ind}assign rst_o_{k} = rr_t{nck + k};  // registered reset out (wavefront) at "
                   f"({T['outs'][k][0]:.1f}, {T['outs'][k][1]:.1f})")
        out.append(f"{ind}assign start_o_{k} = rn_rr_t{nck + k};  // registered START out beside rst_o_{k}")
    return out


def leaf_tap(P, tn):
    """the tap whose relay drives the leaf contents' rst_n: nearest the outline centre (halves the leaf reset reach
    vs tap 0 in the SW corner)."""
    w, h = P.types[tn]["outline_um"]
    # optional plan point reset.leaf_um = the planned leaf-logic region (HEAD-SPINE2 10-25: the spine node spo / spr
    # sit under the N face, so the centre tap left their control flops ~1.5 mm from their relay)
    cx, cy = P.types[tn].get("reset", {}).get("leaf_um", (w / 2, h / 2))
    taps = consumer_taps(P, tn)
    return min(range(len(taps)), key=lambda i: (abs(taps[i][1] - cx) + abs(taps[i][2] - cy), i))


TCL_HEAD = """# GENERATED by tools/die_plan/reset_tree.py (OWNER RESET RULE 10-24): FIRM sites of the reset entry stage (root
# synchroniser u_rst_root or synchronous pin register u_rst_in, at the arst_n pin) and of the synchronous reset relays
# u_rrl_<k> (hops <= REACH).  Sourced inside face_flops.tcl (PRE_GLOBAL_PLACE) before reset_taps.tcl; uses its
# ff_put_near / ff_blk / ff_dbu.  Listed in ot_face_flops.txt so face_flops_release.tcl hands them to DPL.
set rtr_n 0; set rtr_miss {}; set rtr_at {}; set rtr_qnets {}; set rtr_qpol {}
set rtr_fh [open $::env(RESULTS_DIR)/ot_face_flops.txt a]
proc rtr_place {key pat x y tag} {
  global ff_blk ff_dbu rtr_n rtr_miss rtr_fh rtr_at rtr_qnets rtr_qpol
  set hit 0
  foreach i [$ff_blk getInsts] {
    set nm [$i getName]
    if {![string match $pat $nm]} continue
    if {![string match "*DFF*" [[$i getMaster] getName]]} continue
    if {[info exists ::ot_reset_pair_locs] && [dict exists $::ot_reset_pair_locs $nm]} {
      set got [dict get $::ot_reset_pair_locs $nm]
    } else {
      set got [ff_put_near $i [expr {round($x * $ff_dbu)}] [expr {round($y * $ff_dbu)}]]
    }
    if {$got eq ""} { lappend rtr_miss $nm; continue }
    puts $rtr_fh "$nm\\t$tag\\t[expr {[lindex $got 0] / double($ff_dbu)}]\\t[expr {[lindex $got 1] / double($ff_dbu)}]\\t-"
    dict set rtr_at $key $got
    set qnets {}; set qpols {}
    foreach it [$i getITerms] {
      if {[[$it getMTerm] getIoType] eq "OUTPUT" && [$it getNet] ne "NULL"} {
        lappend qnets [$it getNet]
        # ASAP7 DFFHQN*: the only output is QN = NOT q; a same-polarity copy of q is an odd-inverter copy of QN
        lappend qpols [expr {[string match "QN*" [[$it getMTerm] getName]] ? "qn" : "q"}]
      }
    }
    if {[llength $qnets] == 1} { dict set rtr_qnets $key [lindex $qnets 0]; dict set rtr_qpol $key [lindex $qpols 0] }
    incr rtr_n; incr hit
  }
  if {!$hit} { lappend rtr_miss $pat }
}
# optional relay copy (out relay tap-net copy): absent when synthesis swept it (no loads) -> not a miss
proc rtr_place_opt {key pat x y tag} {
  global rtr_miss
  set m0 [llength $rtr_miss]
  rtr_place $key $pat $x $y $tag
  if {[llength $rtr_miss] == $m0 + 1 && [lindex $rtr_miss end] eq $pat} { set rtr_miss [lrange $rtr_miss 0 end-1] }
}
"""


# RLK-1108 (reset.relay_lockup latch form): rtr_place for the ASAP7 latch cell (DLL / DHL) of a hop lockup latch
LOCKUP_PLACE_TCL = """proc rtr_place_lk {key pat x y tag} {
  global ff_blk ff_dbu rtr_n rtr_miss rtr_fh rtr_at
  set hit 0
  foreach i [$ff_blk getInsts] {
    set nm [$i getName]
    if {![string match $pat $nm]} continue
    set m [[$i getMaster] getName]
    if {![string match "DLLx*" $m] && ![string match "DHLx*" $m]} continue
    set got [ff_put_near $i [expr {round($x * $ff_dbu)}] [expr {round($y * $ff_dbu)}]]
    if {$got eq ""} { lappend rtr_miss $nm; continue }
    puts $rtr_fh "$nm\\t$tag\\t[expr {[lindex $got 0] / double($ff_dbu)}]\\t[expr {[lindex $got 1] / double($ff_dbu)}]\\t-"
    dict set rtr_at $key $got
    incr rtr_n; incr hit
  }
  if {!$hit} { lappend rtr_miss $pat }
}"""


CORE_RESET_EQ_TCL = """
# Never bypass a core's private reset pipeline: only same-polarity buffer/inverter copies of this partition's
# equal-depth terminal reset relays can be replaced. Other reset sources need an explicit RTL/offset change.
proc rtr_reset_equiv {net parity seen} {
  global rtr_terminal_qnets
  if {$net eq "NULL" || [dict exists $seen [$net getName]]} { return 0 }
  if {[dict exists $rtr_terminal_qnets [$net getName]]} {
    # terminal relay output pin polarity: q (parity 0 = same polarity) or QN (parity 1 = same polarity as q)
    return [expr {$parity == ([dict get $rtr_terminal_qnets [$net getName]] eq "qn" ? 1 : 0)}]
  }
  dict set seen [$net getName] 1
  set drivers {}
  foreach it [$net getITerms] {
    if {[[$it getMTerm] getIoType] eq "OUTPUT"} { lappend drivers [$it getInst] }
  }
  if {[llength $drivers] != 1} { return 0 }
  set i [lindex $drivers 0]; set m [[$i getMaster] getName]
  set inv [string match "INV*" $m]
  if {!$inv && ![string match "BUF*" $m] && ![string match "HB*" $m]} { return 0 }
  set inputs {}
  foreach it [$i getITerms] {
    if {[[$it getMTerm] getIoType] eq "INPUT"} { lappend inputs [$it getNet] }
  }
  if {[llength $inputs] != 1} { return 0 }
  return [rtr_reset_equiv [lindex $inputs 0] [expr {$parity ^ $inv}] $seen]
}
"""


def _core_instance_match(names):
    return " || ".join(f"$n eq {{{x}}} || [string range $n end-[string length {{{x}}}] end] eq {{/{x}}}"
                       f" || [string range $n end-[string length {{{x}}}] end] eq {{.{x}}}" for x in names)


def project_core_paths(text, contents):
    """Project only generated core-target predicates onto authoritative physical identities.

    The full reset-context sidecar retains its root, relays, coordinates, depth
    and connections. A logical target can also match its selected bound path.
    """
    paths = {c['inst']: c['physical_inst'] for c in contents
             if c.get('physical_inst') and c['physical_inst'] != c['inst']}
    if not paths:
        return text
    lines = text.splitlines(keepends=True)
    target = None
    for index, line in enumerate(lines):
        if line.startswith('# Equal-depth reset target for hard core '):
            name = line.strip().split('hard core ', 1)[1]
            target = name.rsplit('.', 1)[0]
        if target not in paths or not line.startswith('foreach i [$ff_blk getInsts]'):
            continue
        old = _core_instance_match([target])
        new = _core_instance_match([target, paths[target]])
        if 'if {' + new + '}' in line:
            continue
        if 'if {' + old + '}' not in line or 'lappend rtr_ci $i' not in line:
            raise ResetError(f'unknown/conflicting reset sidecar target predicate: {target}')
        lines[index] = line.replace('if {' + old + '}', 'if {' + new + '}', 1)
    return ''.join(lines)


def unused_bootstrap_placements(relays, text, module):
    """Physical inventory of final-wrapper BOOT leaves with no RTL consumer.

    Only declaration plus this exact relay's own Q connection is admitted.
    Aliases, output exports, another consumer or an ambiguous cell retain it.
    The RTL/tree/release table is unchanged; synthesis has no physical cell for
    a source-dead leaf, so it must not be a required placement point.
    """
    import hashlib
    clean = re.sub(r"//[^\n]*|/\*.*?\*/", "", text, flags=re.S)
    bodies = re.findall(r"\bmodule\s+" + re.escape(module) + r"\b.*?\bendmodule\b", clean, re.S)
    if len(bodies) != 1:
        raise ResetError('unused BOOT inventory requires one exact final wrapper module')
    body = bodies[0]
    rows = []
    for relay in relays:
        if relay.get('role') != 'bootstrap_transport' or not relay['name'].endswith('_b'):
            continue
        name, q = relay['name'], relay['q']
        if not re.fullmatch(r'rst_boot_t[0-9]+', q):
            continue
        cells = re.findall(r'\bot_dp_rrelay\s+' + re.escape(name) + r'\s*\(([^;]+)\);', body)
        pins = dict(re.findall(r'\.(\w+)\(\s*([^()]+?)\s*\)', cells[0])) if len(cells) == 1 else {}
        count = len(re.findall(r'\b' + re.escape(q) + r'\b', body))
        declaration = len(re.findall(r'\bwire\s+' + re.escape(q) + r'\s*;', body)) == 1
        dead = (len(cells) == 1 and pins == dict(clk='clk', d=relay['d'], q=q)
                and declaration and count == 2)
        rows.append(dict(instance=name, q=q, d=relay['d'], occurrences=count,
                         exact_declaration=declaration, source_dead=dead))
    return dict(schema='opentallas.reset_source_live_inventory.v1', module=module,
                wrapper_sha256=hashlib.sha256(text.encode()).hexdigest(), leaves=rows,
                omitted=[x['instance'] for x in rows if x['source_dead']],
                method='exact source declaration + own Q only; every consumer/alias/export retains placement')


def tcl_text(T, native_paths=None, native_nodes=None, native_sites=None, unused_bootstrap=()):
    if unused_bootstrap and (native_paths is not None or native_nodes is not None or native_sites is not None):
        raise ResetError("source-live omission cannot change a captured native reset contract")
    if native_paths is not None and (T.get("outs") or T.get("core_resets")) and native_nodes is None:
        raise ResetError("native reset exports require verified physical nodes; no implicit output/core rewiring")
    if native_nodes is not None and native_paths is None:
        raise ResetError("native reset placement nodes require exact verified hierarchy paths")
    ent = "u_rst_root" if T["entry"] == "sync" else "u_rst_in"
    root_xy = (native_sites or {}).get(ent, T['root'])
    t = [TCL_HEAD.replace("REACH", f"{T['reach_um']:g} um"),
         f"rtr_place rst_root_n {{*{ent}[./]*}} {root_xy[0]:.3f} {root_xy[1]:.3f} rentry"]
    rel = start_relays(T) if T.get("start") else [dict(r, dlab=r["d"]) for r in T["relays"]]
    omitted = set(unused_bootstrap)
    eligible = {r['name'] for r in rel if r.get('role') == 'bootstrap_transport' and r['name'].endswith('_b')}
    if omitted - eligible:
        raise ResetError('unused physical inventory can omit only audited BOOT leaves')
    if omitted:
        rel = [r for r in rel if r['name'] not in omitted]
        t.append('puts {OT_RESET_SOURCE_DEAD_BOOTSTRAP ' + str(len(omitted)) + ' leaves: ' + ' '.join(sorted(omitted)) + '}')
    if T.get("relay_driver"):
        specs = []
        if T["entry"] != "sync":
            specs.append(("*u_rst_in[./]*", "", *T["root"]))
            if T.get("start"):
                specs.append(("*u_run_in[./]*", "", *T["start_in"]))
        for r in rel:
            driver = (f"*{r['name']}[./]u_drive" if relay_cell(T, r, gated=r.get("role") == "gated").endswith("_drive") else "")
            specs.append((f"*{r['name']}[./]*", driver, *r["xy"]))
        # The physical pair allocator reserves a legal joint footprint and keeps
        # both cells FIRM. Ordinary pin/station cells retain their usual release.
        spec_text = " ".join("{" + f"{{{f}}} {{{d}}} {x:.6f} {y:.6f}" + "}" for f,d,x,y in specs)
        boxes = " ".join("{" + " ".join(str(x) for x in b) + "}" for b in T.get("relay_pair_boxes", []))
        pair_call = ["source /work/reset_pair_place.tcl",
                     f"ot_reset_pair_place [ord::get_db_block] {{{spec_text}}} {{{boxes}}} 8.0",
                     "set rtr_pf [open $::env(RESULTS_DIR)/ot_reset_pair_fixed.txt w]",
                     "foreach n [dict keys $::ot_reset_pair_locs] { puts $rtr_pf $n }", "close $rtr_pf"]
        t[1:1] = pair_call
        t += ["dict for {n xy} $::ot_reset_pair_locs {",
              "  set i [$ff_blk findInst $n]",
              "  if {![string match {BUF*} [[$i getMaster] getName]]} continue",
              '  puts $rtr_fh "$n\\treset_driver\\t[expr {[lindex $xy 0]/double($ff_dbu)}]\\t[expr {[lindex $xy 1]/double($ff_dbu)}]\\t-"',
              "}"]
    if T.get("start"):
        rent = "u_run_root" if T["entry"] == "sync" else "u_run_in"
        run_xy = (native_sites or {}).get(rent, T['start_in'])
        t.append(f"rtr_place run_root {{*{rent}[./]*}} {run_xy[0]:.3f} {run_xy[1]:.3f} sentry")
    oq = out_relays(T)
    for r in (native_nodes if native_nodes is not None else rel):
        place = "rtr_place_opt" if r.get("optional") else "rtr_place"
        t.append(f"{place} {r['q']} {{*{r['name']}[./]*}} {r['xy'][0]:.3f} {r['xy'][1]:.3f} rrl:{r['kind']}{r['depth']}")
        if native_nodes is None and r["q"] in oq:
            # the out relay's tap-net copy (rtl_lines): placed beside it when synthesis kept it (it has loads)
            t.append(f"rtr_place_opt {r['q']}:copy {{*{r['name']}_t[./]*}} {r['xy'][0]:.3f} {r['xy'][1]:.3f} "
                     f"rrl:{r['kind']}{r['depth']}c")
    lkh = lockup_hops(T)
    if lkh:
        # RLK-1108 latch form: each hop lockup latch FIRM at the midpoint of its two relay sites (planned, or the
        # verified native sites of a bound tree; gen_phys.install_bound_native_reset records the latch hierarchy)
        if (native_paths is None) != (native_nodes is None):
            raise ResetError("reset.relay_lockup latch form on a native contract needs both exact paths and nodes")
        xy = {r["q"]: r["xy"] for r in T["relays"]}
        cap = {r["name"]: r["xy"] for r in T["relays"]}
        if native_nodes is not None:
            byname = {r["name"]: r for r in native_nodes}
            for r in T["relays"]:
                if r["name"] in byname:
                    xy[r["q"]] = cap[r["name"]] = byname[r["name"]]["xy"]
            missing = [lockup_latch_names(r["name"])[0] for r in lkh if lockup_latch_names(r["name"])[0] not in native_paths]
            if missing:
                raise ResetError(f"native reset latch form: hop latches without a verified hierarchy {missing[:5]}")
        t.append(LOCKUP_PLACE_TCL)
        for r in lkh:
            li, lq = lockup_latch_names(r["name"])
            (x0, y0), (x1, y1) = xy[r["d"]], cap[r["name"]]
            t.append(f"rtr_place_lk {lq} {{*{li}[./]*}} {(x0 + x1) / 2:.3f} {(y0 + y1) / 2:.3f} rlk:{r['kind']}{r['depth']}")
    if T.get("core_resets") and native_nodes is None:
        terminals = " ".join(r["q"] for r in T["relays"] if r["depth"] == T["depth"])
        t += ["set rtr_terminal_qnets {}", f"foreach key {{{terminals}}} {{",
              "  if {[dict exists $rtr_qnets $key]} { dict set rtr_terminal_qnets [[dict get $rtr_qnets $key] getName] [dict get $rtr_qpol $key] }",
              "}", CORE_RESET_EQ_TCL]
    for c in (T.get("core_resets", []) if native_nodes is None else []):
        q = f"rst_n_t{c['tap']}"
        inst, pin = c["inst"], c["pin"]
        # ODB getName escapes brackets (u_core.u.g_pp\\[0\\].u_pair); match on the plain Verilog form (hd_lep0N).
        # A flat plan core with no physical_inst stays u_bound.<inst> in ODB (QC u_t32, MY tile with no lef in the plan):
        # "." is a hierarchy separator too, and the exactly-one check below still rejects an ambiguous name.
        names = [inst] + ([c["physical_inst"]] if c.get("physical_inst") else [])
        match = _core_instance_match(names)
        t += [f"# Equal-depth reset target for hard core {inst}.{pin}",
              "set rtr_cn {}; set rtr_ci {}",
              f"foreach n [$ff_blk getNets] {{ if {{[regexp {{(^|[/.]){q}$}} [$n getName]]}} {{ lappend rtr_cn $n }} }}",
              f"foreach i [$ff_blk getInsts] {{ set n [string map {{\\\\[ [ \\\\] ]}} [$i getName]]; if {{{match}}} {{ lappend rtr_ci $i }} }}",
              f"if {{[llength $rtr_cn] != 1 || [llength $rtr_ci] != 1}} {{ error {{OT_RESET_CORE unresolved {inst}.{pin} or {q}}} }}",
              f"set rtr_it [[lindex $rtr_ci 0] findITerm {{{pin}}}]",
              f"if {{$rtr_it eq \"NULL\"}} {{ error {{OT_RESET_CORE missing {inst}.{pin}}} }}",
              # CLASS RESET-CORE 11-03 (DIE-S81-51): a core reset that is not an equal-depth relay copy (an RTL
              # private pipeline, a frame reset-forest leaf or a lane-carried reset bit) keeps its RTL driver and
              # latency: no rewire, recorded in ot_reset_core_kept.txt.  Only equal-depth copies are re-targeted.
              f"if {{![rtr_reset_equiv [$rtr_it getNet] 0 {{}}]}} {{",
              f"  puts {{OT_RESET_CORE_KEPT {inst}.{pin}: RTL reset kept (not an equal-depth relay copy; RTL latency preserved)}}",
              f"  set rtr_kf [open $::env(RESULTS_DIR)/ot_reset_core_kept.txt a]; puts $rtr_kf {{{inst}.{pin}}}; close $rtr_kf",
              "} else {",
              "  $rtr_it disconnect; $rtr_it connect [lindex $rtr_cn 0]",
              f"  dict set rtr_at core:{c['tap']} [list [expr {{round({c['pin_um'][0]:.5f} * $ff_dbu)}}] [expr {{round({c['pin_um'][1]:.5f} * $ff_dbu)}}]]",
              f"  puts {{OT_RESET_CORE {inst}.{pin} <- {q} depth {T['depth']}}}",
              "}"]
    edges = " ".join(f"{r['q']} {r['d']}" for r in (native_nodes if native_nodes is not None else rel))
    if native_nodes is None:
        edges += " " + " ".join(f"core:{c['tap']} rst_n_t{c['tap']}" for c in T.get("core_resets", []))
    else:
        edges += " " + " ".join(f"{r['q']} {r['run']}" for r in native_nodes if r.get('run'))
        t.append("# NATIVE RESET: core connections remain exactly as bound; no core rewiring or claimed core-hop check.")
    t += ["close $rtr_fh",
          "# placed hop check (driver relay -> relay, Manhattan between placed sites)",
          f"set rtr_hmax 0; set rtr_hbad 0; set rtr_lim [expr {{{T['reach_um']:g} * $ff_dbu}}]",
          f"foreach {{q d}} {{{edges}}} {{",
          "  if {![dict exists $rtr_at $q] || ![dict exists $rtr_at $d]} continue",
          "  lassign [dict get $rtr_at $q] x1 y1; lassign [dict get $rtr_at $d] x0 y0",
          "  set h [expr {abs($x1 - $x0) + abs($y1 - $y0)}]",
          "  if {$h > $rtr_hmax} { set rtr_hmax $h }",
          "  if {$h > $rtr_lim} { incr rtr_hbad }",
          "}",
          "set rtr_v [expr {($rtr_hbad || [llength $rtr_miss]) ? \"FAIL\" : \"PASS\"}]",
          f"puts \"OT_RESET_TREE entry {T['entry']} depth {T['depth']} ({T['n_tree']} tree + {T['n_pad']} pad relays, "
          f"planned max hop {T['max_hop_um']} um): placed $rtr_n flops FIRM, placed max hop "
          "[format %.1f [expr {$rtr_hmax / double($ff_dbu)}]] um, $rtr_hbad hops > "
          f"{T['reach_um']:g} um: $rtr_v (missing: [llength $rtr_miss] $rtr_miss)\""]
    text = "\n".join(t) + "\n"
    if native_paths is not None:
        for name, path in native_paths.items():
            exact = "[./]".join(path.split(".")) + "[./]*"
            text = text.replace("*" + name + "[./]*", exact)
        if re.search(r"^rtr_place(?:_opt|_lk)?\s+\S+\s+\{\*", text, re.M):
            raise ResetError("native reset placement contains an unverified wildcard instance")
    return text


def summary(T):
    return dict(entry=T["entry"], depth=T["depth"], own_depth=T["own_depth"], relays=len(T["relays"]),
                tree_relays=T["n_tree"], pad_relays=T["n_pad"], max_hop_um=T["max_hop_um"], reach_um=T["reach_um"],
                root_um=[round(v, 3) for v in T["root"]], sync_stages=T["sync_stages"],
                entry_stages=entry_stages(T), release_clocks=release_clocks(T), outs=len(T.get("outs", [])),
                note="OWNER DECISION 13: one root synchroniser per die + neighbour wavefront (registered reset in / out "
                     "per partition, relays <= reach, equal depth inside the partition)" if T.get("outs") is not None
                else "OWNER RESET RULE 10-24: one root synchroniser per die region + equal-depth synchronous relays")


# ----------------------------------------------------------------------------------------------- G0
def check(P):
    """(errors, warnings, info) of the reset rule for a plan (check.py G0)."""
    errs, warns = [], []
    if wavefront(P):
        try:
            errs += check_pad(P)
            for tn, t in sorted(P.types.items()):
                if t.get("hard") or not any(p["type"] == tn for p in P.parts.values()):
                    continue
                T = for_type(P, tn)
                errs += [f"type {tn}: reset tree: {e}" for e in verify(T)]
            W = wf_plan(P)
            if W.get('release_qualification', {}).get('verdict') == 'PENDING':
                errs.append('reset wavefront: FULL native release qualification PENDING: ' +
                            str(W['release_qualification']['native_targets']))
            if W.get("release_qualification", {}).get("verdict") == "QUALIFIED_CONDITIONAL":
                warns.append("native PHY reset conditionally qualified in recovered-clock edges; no finite core-cycle deadline while PMA clock is stopped; no CDC or clock-period exception")
            if W["long_hops"] or W["unreachable"]:
                errs.append(f"reset wavefront: {len(W['long_hops'])} partitions have no neighbour rst_o within "
                            f"{hop_um(P):g} um of their reset IN pin (attached to the nearest, hop um): "
                            f"{[(a, c) for a, _b, c in W['long_hops'][:12]]}; move the IN pin (hard types: "
                            "partition_types[T].reset.tap_um on the face toward a neighbour) or the floorplan")
            info = {k: v for k, v in W.items() if k not in ("parts",)}
        except ResetError as e:
            errs.append(str(e))
            info = None
        return errs, warns, info
    if pipelined(P):
        warns.append("reset.release 'pipelined' (equal depth through a die relay tree) is superseded by OWNER DECISION "
                     "13 (2026-10-24): use 'wavefront'")
    if not pipelined(P):
        warns.append("reset.release is not 'wavefront': per-partition asynchronous synchronisers do not meet the OWNER "
                     "RESET RULE 2026-10-24 / DECISION 13 (tools/die_plan/reset_tree.py)")
        return errs, warns, None
    try:
        K = part_depth(P)
        for tn, t in sorted(P.types.items()):
            if t.get("hard"):
                continue
            T = for_type(P, tn)
            errs += [f"type {tn}: reset tree: {e}" for e in verify(T)]
        info = die_summary(P)
        for r in info["regions"]:
            if r["max_hop_um"] > relay_um(P) + 1e-6:
                errs.append(f"region {r['region']}: die reset hop {r['max_hop_um']} um > {relay_um(P):g}")
        info["part_depth_K"] = K
    except ResetError as e:
        errs.append(str(e))
        info = None
    return errs, warns, info


def render(P, tn, png):
    """review picture of a type's reset tree (review-before-route): outline, hard cores / macro leaves, clock taps, the
    arst_n entry, relays coloured by depth, driver -> relay edges (straight lines; the wire takes an L)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    T = for_type(P, tn)
    t = P.types[tn]
    w, h = t["outline_um"]
    fig, ax = plt.subplots(figsize=(8, 8 * h / max(w, 1e-9) if w else 8))
    ax.add_patch(Rectangle((0, 0), w, h, fill=False, lw=1.5, ec="k"))
    for a, b, c, d in blockages(t):
        ax.add_patch(Rectangle((a, b), c - a, d - b, fc="#ddd", ec="#999", lw=0.5))
    xy = {r["q"]: r["xy"] for r in T["relays"]}
    xy["rst_root_n"] = T["root"]
    cm = plt.get_cmap("viridis")
    for r in T["relays"]:
        (x0, y0), (x1, y1) = xy[r["d"]], r["xy"]
        ax.plot([x0, x1], [y0, y1], "-", color="#c33" if RT_hop(x0, y0, x1, y1) > T["reach_um"] else "#888", lw=0.6)
    for r in T["relays"]:
        ax.plot(*r["xy"], "o", ms=3 if r["kind"] == "pad" else 5, color=cm(r["depth"] / max(1, T["depth"])))
    for i, (_, x, y) in enumerate(consumer_taps(P, tn)):
        ax.plot(x, y, "+", color="b", ms=7)
    ax.plot(*T["root"], "s", color="r", ms=9)
    ax.set_title(f"{tn}: reset entry {T['entry']} (red square) -> depth {T['depth']} to {len(T['taps'])} taps (+), "
                 f"{T['n_tree']} tree + {T['n_pad']} pad relays, max hop {T['max_hop_um']} um", fontsize=8)
    ax.set_xlim(-0.02 * w, 1.02 * w)
    ax.set_ylim(-0.02 * h, 1.02 * h)
    ax.set_aspect("equal")
    fig.savefig(png, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return png


def RT_hop(x0, y0, x1, y1):
    return abs(x1 - x0) + abs(y1 - y0)


def main(argv):
    if len(argv) >= 3 and argv[0] == "render":
        P = S.Plan(json.load(open(argv[1])), argv[1])
        if "--release" in argv:
            P.reset["release"] = argv[argv.index("--release") + 1]
        out = argv[argv.index("--png") + 1] if "--png" in argv else f"reset_tree_{argv[2]}.png"
        print(render(P, argv[2], out))
        return 0
    if len(argv) < 2 or argv[0] not in ("type", "die", "all", "offsets"):
        raise SystemExit(__doc__)
    P = S.Plan(json.load(open(argv[1])), argv[1])
    if "--release" in argv:             # what-if: price a plan that has not switched yet
        P.reset["release"] = argv[argv.index("--release") + 1]
    if argv[0] == "type":
        print(json.dumps(dict(type=argv[2], **summary(for_type(P, argv[2])))))
    elif argv[0] == "offsets":
        if not wavefront(P):
            raise SystemExit("offsets: the plan is not reset.release 'wavefront' (add --release wavefront to price it)")
        js = json.dumps(wf_plan(P), indent=1)
        if "--out" in argv:
            Path(argv[argv.index("--out") + 1]).write_text(js + "\n")
        print(js)
    elif argv[0] == "die":
        s = die_summary(P)
        js = json.dumps(s, indent=1)
        if "--out" in argv:
            Path(argv[argv.index("--out") + 1]).write_text(js + "\n")
        print(js)
    else:
        e, w, info = check(P)
        print(json.dumps(dict(errors=e, warnings=w, die=info), indent=1))
        return 1 if e else 0
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
