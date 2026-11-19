"""cbc_rules.py -- close-by-construction (CBC, owner r713, 11-19) rule constants: ONE module that the plan generator
(CBC-RULES-1119) and the static estimator (tools/precheck, PRECHECK-1119) both import, so a rule changes in one place.

Units: um, clock sinks, flops, logic levels.  ASAP7, 833 ps clock.
"""
REACH_UM_PER_HOP = 405.0        # FABLE-CLOSURE-STRATEGY 11-19 02:00 (amends r713's 300): longest Manhattan distance between
                                # launch and capture register of any leg, measured on PLACED hops (placed_hops.py on
                                # 3_place.odb, every leg incl. undeclared ones); plan coordinates are an estimate of it
DEPTH_LEVELS_TARGET = 12        # logic levels per register D cone the generator aims for
DEPTH_LEVELS_MAX = 13           # above this a cone is flagged
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
