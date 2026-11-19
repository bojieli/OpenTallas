"""cbc_rules.py -- close-by-construction (CBC, owner r713, 11-19) rule constants: ONE module that the plan generator
(CBC-RULES-1119) and the static estimator (tools/precheck, PRECHECK-1119) both import, so a rule changes in one place.

Units: um, clock sinks, flops, logic levels.  ASAP7, 833 ps clock.
"""
REACH_UM_PER_HOP = 405.0        # FABLE-CLOSURE-STRATEGY 11-19 02:00 (amends r713's 300): longest Manhattan distance between
                                # launch and capture register of any leg, measured on PLACED hops (placed_hops.py on
                                # 3_place.odb, every leg incl. undeclared ones); plan coordinates are an estimate of it
DEPTH_LEVELS_TARGET = 12        # logic levels per register D cone the generator aims for
DEPTH_LEVELS_MAX = 13           # COORD 11-19 (amends r713 rule 3): a cheap PRE-SCREEN only -- level count does not predict
                                # closure (hd_ctl signed at 23 levels, tt_ctlm at 24 used 820 of 833 ps at zero wire)
PERIOD_PS = 833.0               # die clock
LOGIC_PS_MAX = 600.0            # rule 3 (COORD 11-19): zero-wire logic delay per endpoint (clk->Q + cells + setup, ASAP7 RVT
                                # TT NLDM, pin loads only, fanout bounded) above this is flagged: leaves ~230 ps for wire + clock
FANOUT_BOUND = 8                # zero-wire STA: every net over this many cell sinks gets a buffer tree first (the
                                # FABLE-FIX-S81-GLUE method: driver copies at 8), as placement repair would
TAP_MAX_SINKS = 1000            # clock sinks per tap (a plan's lower clock.tap_max_sinks wins)
TAP_RADIUS_UM = 200.0           # kit clock_taps.tcl rebalance reach
RESET_LEAF_MAX_FANOUT = 32      # flops per reset relay leaf
BOUNDARY_REG_UM = 50.0          # every block port has a register within this distance of its pin (both sides)
AIM_MIN_BIT_FRAC = 0.10         # a receiver chain aimed at a capture holding < 10 % of the bus bits is mis-aimed
AIM_MIN_BITS = 64               # ... checked on buses of at least this width
SINK_BINS_STALE_FRAC = 0.10     # plan sink bins vs the newest kit sink count
TAP_SKEW_PASS_PS = 60.0         # in-tap skew (sink latency spread within one tap): < 60 ps 58 of 111 kits closed
TAP_SKEW_FAIL_PS = 100.0        # >= 100 ps: 0 of 23 closed (FABLE-CLOSURE-STRATEGY 11-19)
TAP_SKEW_PS_PER_UM = 0.065      # fit 11-19 (14 S81 kits, 413 taps): skew ~ 0.065 x (p98 - p2) + 44, R2 0.013 -- NOT predictive;
                                # kit_scan posts the measured CTS skew (OT_TAP_INSERTION) instead


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
