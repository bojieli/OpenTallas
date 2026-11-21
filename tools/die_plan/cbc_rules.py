"""cbc_rules.py -- close-by-construction (CBC, owner r713, 11-19) rule constants: ONE module that the plan generator
(CBC-RULES-1119) and the static estimator (tools/precheck, PRECHECK-1119) both import, so a rule changes in one place.

Units: um, clock sinks, flops, logic levels.  ASAP7, 833 ps clock.
"""
import os as _os
REACH_UM_PER_HOP = float(_os.environ.get("OT_CBC_REACH_UM", "300"))   # OWNER 11-20 #6 (COORD): generator default on EVERY die -- the longest placed hop (launch ->
                                # capture register, Manhattan, placed_hops.py on 3_place.odb) a plan generator / station tool
                                # builds for; PRECHECK REACH estimates against it.  Was 405 (FABLE-CLOSURE-STRATEGY 11-19).
                                # OT_CBC_REACH_UM overrides it (tools/conftest.py: 405 for the suites drawn at the old rule).
REACH_GATE_UM = 405.0           # the CHECK rule is unchanged (METHODOLOGY 12.1e registered hop): G0 ft_station_max_um, bind
                                # reach, routed reach.  Generators aim at REACH_UM_PER_HOP; nothing that passes 405 fails here.
SITE_MARGIN_UM = 5.0            # generators that site cell centres keep 5 um under the cap for the cell-centre vs pin model
DEPTH_LEVELS_TARGET = 12        # logic levels per register D cone the generator aims for
DEPTH_LEVELS_MAX = 13           # COORD 11-19 (amends r713 rule 3): a cheap PRE-SCREEN only -- level count does not predict
                                # closure (hd_ctl signed at 23 levels, tt_ctlm at 24 used 820 of 833 ps at zero wire)
PERIOD_PS = 833.0               # die clock
LOGIC_PS_MAX = 600.0            # rule 3 (COORD 11-19): zero-wire logic delay per endpoint (clk->Q + cells + setup, ASAP7 RVT
                                # TT NLDM, pin loads only, fanout bounded) above this is flagged: leaves ~230 ps for wire + clock
FANOUT_BOUND = 8                # zero-wire STA: every net over this many cell sinks gets a buffer tree first (the
                                # FABLE-FIX-S81-GLUE method: driver copies at 8), as placement repair would
REACH_CORE_SPAN_UM = 200.0       # COORD 11-19 (FABLE-CLOSURE-STRATEGY 03:30): a leg over REACH_UM_PER_HOP takes +cycle stations
                                # only if its path spans more than this much hard core (no buffers over a core) or carries logic
REACH_BUFFERED_UM = 550.0       # ... otherwise it is a buffered register-to-pin leg: closes to ~550 um (col_h9_r2 30 / 30 at 491-550)
STATIC_LEG_RE = r"(^|[._])(strap|tie|id_strap|cfg_strap)[_a-z0-9]*"   # static strap / tie legs: never a reach cycle
TAP_REGION_WH_UM = 300.0        # COORD 11-19 tap rule, PRIMARY: one tap's sink region W + H <= 300 um (placed sinks); 3,476 taps:
                                # 450-600 um regions give 40-80 % of taps over 100 ps
TAP_SPILL = False               # a tap that reaches TAP_MAX_SINKS asks for another tap in its region, never spills to a farther one
TAP_MAX_SINKS = 1000            # SECONDARY cap (COORD 11-19): clock sinks per tap (a plan's lower clock.tap_max_sinks wins)
TAP_RADIUS_UM = 200.0           # kit clock_taps.tcl rebalance reach (superseded by TAP_REGION_WH_UM; kept for old callers)
RESET_LEAF_MAX_FANOUT = 32      # flops per reset relay leaf
BOUNDARY_REG_UM = 50.0          # every block port has a register within this distance of its pin (both sides)
AIM_MIN_BIT_FRAC = 0.10         # a receiver chain aimed at a capture holding < 10 % of the bus bits is mis-aimed
AIM_MIN_BITS = 64               # ... checked on buses of at least this width
SINK_BINS_STALE_FRAC = 0.10     # plan sink bins vs the newest kit sink count
TAP_SKEW_PASS_PS = 60.0         # in-tap skew (sink latency spread within one tap): < 60 ps 58 of 111 kits closed
TAP_SKEW_FAIL_PS = 100.0        # >= 100 ps: 0 of 23 closed (FABLE-CLOSURE-STRATEGY 11-19)
TAP_SKEW_PS_PER_UM = 0.065      # fit 11-19 (14 S81 kits, 413 taps): skew ~ 0.065 x (p98 - p2) + 44, R2 0.013 -- NOT predictive;
                                # kit_scan posts the measured CTS skew (OT_TAP_INSERTION) instead

# CBC rule 4 (OWNER 11-20 #6 + COORD 11-20, CBC-ALL-0200): every RESET hop -- reset relay tree, ring reset relay copies
# (u_cland_rst_* / u_cland_rfan_*), literal raw START / reset branches -- is <= 300 um, all copies releasing on the same
# edge.  The reset tools take min(plan value, this cap) as their reach; OT_RESET_HOP_CAP_UM overrides (e.g. 405 = old rule).
RESET_HOP_CAP_UM = 300.0

# MONITOR-PIN rule (S81-MONITOR-PIN-1745, FABLE-CLOSURE-1730 lever 2): a landing monitor ring (u_cland_monitor_<i>, band
# monitor_<i>) and its cland_dn_ready_<i> / cland_dn_fault_<i> / fclk_in_cland_dn_<i> pins are ONE site: every pin within this
# Manhattan distance of the monitor seat (band rect centre).  J5 (224567138ab) broke it: aced0fb210 (reset hop 300) re-wired
# the die reset wavefront, the monitor tree follows that wavefront so the cland_dn pins moved to the new reset-out sites, and
# the frozen clock.band_fixed_um.monitor_<i> (S81-BANDTAP-1115) kept the seat (slice_station t36 31 -> 2,057 um, -766 ps).
# The compose re-seats a frozen monitor band that breaks it; precheck MONITOR-PIN reports it on any plan.
MONITOR_PIN_REACH_UM = 300.0


def monitor_pin_distances(lc):
    """[(monitor index, pin name, Manhattan um seat centre -> pin)] of a landing_contract dict (bands + pins).  A monitor
    band without a rect (placement FAIL) or without pins is skipped."""
    pins = {p.get("name"): p.get("xy_um") for p in (lc or {}).get("pins") or [] if p.get("xy_um")}
    out = []
    for name, b in sorted(((lc or {}).get("bands") or {}).items()):
        if not name.startswith("monitor_") or not (b or {}).get("rect_um"):
            continue
        i = name.split("_", 1)[1]
        x0, y0, x1, y1 = b["rect_um"]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        for pn in (f"cland_dn_ready_{i}", f"cland_dn_fault_{i}", f"fclk_in_cland_dn_{i}"):
            if pn in pins:
                out.append((i, pn, round(abs(cx - pins[pn][0]) + abs(cy - pins[pn][1]), 3)))
    return out


_BOUND_CAP = []          # FLOW-NOADV-R2 11-20: stack of caps pushed by bound_reset_hop_cap(); the innermost wins over default AND env


class bound_reset_hop_cap:
    """FLOW-NOADV-R2 11-20 (FABLE-FLOW-1000 class 1): a bound tree is solved with the cap it was BOUND with (the bind records it
    as reach_cap_um in the reset receipt, tree.reach_um before that field), never with the tool default or an env value.  A default change (aced0fb210: 405 ->
    300) then only touches new binds.  `with bound_reset_hop_cap(405.0): ...`; None / non-positive pushes nothing."""

    def __init__(self, um):
        try:
            self.um = float(um) if um is not None and float(um) > 0 else None
        except (TypeError, ValueError):
            self.um = None

    def __enter__(self):
        if self.um is not None:
            _BOUND_CAP.append(self.um)
        return self

    def __exit__(self, *exc):
        if self.um is not None:
            _BOUND_CAP.pop()
        return False


def plan_reset_hop_cap(plan):
    """BOUND-PLAN-CAP (HEAD-PLAN-R16 11-20, FABLE-PD-HEAD-2040 F3): the reset hop cap a die plan's trees were BOUND with,
    recorded in the plan as reset.reach_cap_um (plan authority, not an env value).  plan = a Plan, its raw dict, its reset
    section or a plan path; None when the plan records no cap (then the tool default / env apply, i.e. new binds)."""
    import json as _json
    from pathlib import Path as _Path
    if plan is None:
        return None
    if isinstance(plan, (str, _Path)):
        try:
            plan = _json.loads(_Path(plan).read_text())
        except (OSError, ValueError):
            return None
    rs = getattr(plan, "reset", None)
    if rs is None and isinstance(plan, dict):
        rs = plan.get("reset") if "reset" in plan or "partition_types" in plan else plan
    v = (rs or {}).get("reach_cap_um") if isinstance(rs, dict) else None
    if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0:
        return float(v)
    return None


def reset_hop_cap_um(die=None, plan=None):
    """the reset hop cap (um) every reset generator applies by default (die reserved for a die-scoped override); inside
    bound_reset_hop_cap() the bound tree's own cap; else the plan's recorded reset.reach_cap_um (plan_reset_hop_cap)"""
    import os
    if _BOUND_CAP:
        return _BOUND_CAP[-1]
    pc = plan_reset_hop_cap(plan)
    if pc is not None:
        return pc
    v = os.environ.get("OT_RESET_HOP_CAP_UM")
    try:
        return float(v) if v else RESET_HOP_CAP_UM
    except ValueError:
        return RESET_HOP_CAP_UM


# CBC seam input budget (COORD 11-20 QC-HOLD-0030-INDELAY, CBC-ALL-0200): under CBC the sender of an ft / ring hop is a
# registered station whose last segment is a placed hop <= the hop cap, so the time the hop spends OUTSIDE the receiving
# kit is clk->q + that segment's wire, not the fixed (1 - ft_hop_in_share) x T = 0.92 T (766 ps) or the QC ring
# ft_ring_max_ps 350 ps.  Priced with the FABLE-METHOD s1 buffered-wire model (plan_timing_audit: 50 ps + 0.65 ps/um):
# 50 + 0.65 x 300 = 245 ps.  The receiver kit's input max delay is min(old budget, this); the sender kit's output budget
# is unchanged (tightening only on no side; the die STA prices the real crossing).  OT_FT_IN_BUDGET=fixed = old rule.
SEAM_CLKQ_PS = 50.0
SEAM_PS_PER_UM = 0.65


def seam_budget_ps(seam_um):
    """registered-sender seam budget (ps) of a seam of seam_um (clk->q + buffered wire, capped at the hop cap)"""
    return SEAM_CLKQ_PS + SEAM_PS_PER_UM * min(float(seam_um), REACH_UM_PER_HOP)


def ft_in_budget_ps(die=None, port=None, tn=None, budgets=None):
    """max input delay (ps, before tap-window shift) of an ft / ring seam input under CBC, or None (env opt-out).
    QC-PLAN-R8 11-20: opt-in plan budgets.ft_in_budget_ps = {"<type>/<port>" | "<port>": ps | {"seam_um": um}} sets
    the budget of one receiver input port (the ft slot's "<slot>_i", e.g. "cws2_i") from its geometry; a type-scoped
    key wins over the bare port key, {"seam_um": L} prices 50 + 0.65 x min(L, hop cap).  Absent key / port = the
    die-wide 50 + 0.65 x hop cap (245 ps at 300 um), byte-identical to before."""
    import os
    if os.environ.get("OT_FT_IN_BUDGET", "").lower() == "fixed":
        return None
    ov = (budgets or {}).get("ft_in_budget_ps") or {}
    v = None
    if port is not None:
        v = ov.get(f"{tn}/{port}") if tn is not None else None
        v = ov.get(port) if v is None else v
    if v is None:
        return SEAM_CLKQ_PS + SEAM_PS_PER_UM * REACH_UM_PER_HOP
    if isinstance(v, dict):
        return seam_budget_ps(v["seam_um"])
    return float(v)


def rules():
    """the rule set as a dict (records, posts)"""
    return {k: v for k, v in globals().items() if k.isupper()}


# ---------------------------------------------------------------- leg classification (shared with CBC-RULES-1119)
import re as _re

STRAP_TIE = _re.compile(r"(^|[._/:])(strap|tie|TIEHI|TIELO|count_strap)", _re.I)
LEG_CLASSES = ("core", "channel", "logic", "strap")   # strap/tie legs are excluded from reach counts


def _l_paths_blocked(a, b, rects):
    """True when both L-shaped Manhattan routes a -> b cross a hard-core rect interior"""
    def seg_hits(p, q, r):
        x0, y0, x1, y1 = r
        if p[0] == q[0]:                       # vertical
            return x0 < p[0] < x1 and min(p[1], q[1]) < y1 and max(p[1], q[1]) > y0
        return y0 < p[1] < y1 and min(p[0], q[0]) < x1 and max(p[0], q[0]) > x0

    def path_hits(c):
        return any(seg_hits(a, c, r) or seg_hits(c, b, r) for r in rects)
    return path_hits((b[0], a[1])) and path_hits((a[0], b[1]))


def classify_leg(launch, capture, la, lb, macro_rects):
    """class of a placed register -> register leg: 'strap' (strap / tie source or sink: excluded), 'core' (every
    Manhattan route crosses a hard core: the leg spans over a core), 'channel' (a block port end: boundary / ft
    channel leg), 'logic' (core-free soft logic leg)"""
    if STRAP_TIE.search(launch or "") or STRAP_TIE.search(capture or ""):
        return "strap"
    if macro_rects and _l_paths_blocked(tuple(la), tuple(lb), macro_rects):
        return "core"
    if (launch or "").startswith("port:") or (capture or "").startswith("port:"):
        return "channel"
    return "logic"


_EPS = 0.01


def _out_of(p, rects):
    """(point, extra_um): a pin end inside a hard core (a macro pin sits on or just inside its outline) leaves by the
    nearest outline side; extra_um is that walk (0 when p is outside every core)"""
    x, y = p
    for x0, y0, x1, y1 in rects:
        if x0 < x < x1 and y0 < y < y1:
            d, q = min((x - x0, (x0, y)), (x1 - x, (x1, y)), (y - y0, (x, y0)), (y1 - y, (x, y1)))
            return q, d
    return (x, y), 0.0


def detour_um(a, b, macro_rects, cap=None):
    """COORD 11-21 (FAM-S81-COL-R4): shortest rectilinear path a -> b that stays outside every hard-core body (rect
    interiors; abutting cores are one body, a shared edge is not a channel).  Exact on the Hanan grid of the end points and
    the core edges (cell occupancy precomputed per call, Dijkstra on the grid).  cap: search only paths <= cap (window =
    bbox(a, b) grown by (cap - straight) / 2) and return float('inf') when none is that short.  A pin end inside its own
    core walks out by the nearest side first."""
    import bisect, heapq
    rects = [tuple(map(float, r[:4])) for r in macro_rects or []]
    a = (float(a[0]), float(a[1])); b = (float(b[0]), float(b[1]))
    grown = [(x0 - _EPS, y0 - _EPS, x1 + _EPS, y1 + _EPS) for x0, y0, x1, y1 in rects]
    a, ea = _out_of(a, grown); b, eb = _out_of(b, grown)
    straight = abs(a[0] - b[0]) + abs(a[1] - b[1])
    if cap is not None:
        if straight + ea + eb > cap:
            return float("inf")
        m = max(0.0, (cap - ea - eb - straight) / 2.0)
        wx0, wx1 = min(a[0], b[0]) - m, max(a[0], b[0]) + m
        wy0, wy1 = min(a[1], b[1]) - m, max(a[1], b[1]) + m
        grown = [r for r in grown if r[0] < wx1 and r[2] > wx0 and r[1] < wy1 and r[3] > wy0]
    if not _l_paths_blocked(a, b, grown):
        return straight + ea + eb
    xs = sorted({a[0], b[0]} | {v for r in grown for v in (r[0], r[2])})
    ys = sorted({a[1], b[1]} | {v for r in grown for v in (r[1], r[3])})
    nx, ny = len(xs), len(ys)
    # cell (i, j) = open rectangle xs[i]..xs[i+1] x ys[j]..ys[j+1]; blocked when inside a core.  A grid node is blocked when
    # strictly inside a core; a grid edge is blocked when its open segment is inside a core (= both cells beside it blocked,
    # or the segment runs through a core interior).
    cell = [bytearray(ny) for _ in range(nx)]
    node = [bytearray(ny) for _ in range(nx)]
    for x0, y0, x1, y1 in grown:
        i0, i1 = bisect.bisect_left(xs, x0), bisect.bisect_left(xs, x1)
        j0, j1 = bisect.bisect_left(ys, y0), bisect.bisect_left(ys, y1)
        for i in range(i0, i1):
            ci = cell[i]
            for j in range(j0, j1):
                ci[j] = 1
        for i in range(i0 + 1, i1):
            ni = node[i]
            for j in range(j0 + 1, j1):
                ni[j] = 1
    def hblk(i, j):                 # edge (i, j) -> (i + 1, j)
        return (j > 0 and cell[i][j - 1]) and (j < ny - 1 and cell[i][j]) if 0 < j < ny - 1 else False
    def vblk(i, j):                 # edge (i, j) -> (i, j + 1)
        return (cell[i - 1][j] and cell[i][j]) if 0 < i < nx - 1 else False
    src = (xs.index(a[0]), ys.index(a[1])); dst = (xs.index(b[0]), ys.index(b[1]))
    lim = float("inf") if cap is None else cap - ea - eb
    best = {src: 0.0}; pq = [(0.0, src[0], src[1])]
    while pq:
        d, i, j = heapq.heappop(pq)
        if (i, j) == dst:
            return d + ea + eb
        if d > best.get((i, j), float("inf")):
            continue
        for ni, nj, blk in ((i + 1, j, i + 1 < nx and hblk(i, j)), (i - 1, j, i > 0 and hblk(i - 1, j)),
                            (i, j + 1, j + 1 < ny and vblk(i, j)), (i, j - 1, j > 0 and vblk(i, j - 1))):
            if not (0 <= ni < nx and 0 <= nj < ny) or blk or node[ni][nj]:
                continue
            nd = d + abs(xs[ni] - xs[i]) + abs(ys[nj] - ys[j])
            if nd <= lim and nd < best.get((ni, nj), float("inf")):
                best[(ni, nj)] = nd; heapq.heappush(pq, (nd, ni, nj))
    return float("inf")


def reach_leg_um(leg, macro_rects=(), reach=REACH_UM_PER_HOP, routed_um=None):
    """-> (class, length_um) of a counted placed leg, or None.  COORD 11-21 ruling (replaces the 11-19 'not over a core'
    exclusion): a leg whose every Manhattan route crosses a hard core ('core') is measured at its detour length around
    the cores (detour_um), or at routed_um when the routed length is known, not at its straight length, and counts when
    that is over the reach.  Other legs keep the 11-19 rule: PIN-TO-PIN straight Manhattan distance (placed_hops leg
    [straight, acc, launch, capture, pin, la, lb]: macro ends sit at the macro pin) over the reach, no strap / tie leg, a
    channel leg (a block port end: a buffered register-to-pin leg) only over REACH_BUFFERED_UM."""
    c = classify_leg(leg[2], leg[3], leg[5], leg[6], list(macro_rects or []))
    if c == "strap":
        return None
    if c == "core":
        if routed_um is not None:
            L = float(routed_um)
        elif leg[0] > reach:            # counted whatever the detour (detour >= straight); length = detour, searched up to 2x
            L = detour_um(leg[5], leg[6], macro_rects, cap=2.0 * leg[0])
            L = 2.0 * leg[0] if L == float("inf") else L     # longer than 2x straight: reported as that lower bound
        else:                           # only the question 'over the reach?' matters: search paths <= reach
            L = detour_um(leg[5], leg[6], macro_rects, cap=reach)
            if L == float("inf"):
                L = detour_um(leg[5], leg[6], macro_rects, cap=2.0 * reach)
                L = 2.0 * reach if L == float("inf") else L
        return (c, L) if L > reach else None
    if leg[0] <= reach:
        return None
    if c == "channel" and leg[0] <= REACH_BUFFERED_UM:
        return None
    return c, float(leg[0])


def reach_leg(leg, macro_rects=(), reach=REACH_UM_PER_HOP, routed_um=None):
    """class of a counted placed leg (reach_leg_um), or None (not counted)"""
    r = reach_leg_um(leg, macro_rects, reach, routed_um)
    return r[0] if r else None
