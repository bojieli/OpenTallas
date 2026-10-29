#!/usr/bin/env python3
"""DIE-S81-5 (COORD 00:06 ruling 5, die-local driver, no shared-tool edit): run main die_trial.py kit with the legal-detour
rule of tree_netlist applied to EVERY leg whose straight repeater placement leaves an unrepeated span > SPAN_X x rep_um
(main: only legs that also run > rep_um through forbidden rects, SPAN_X 2.0).  The detour = main legal_detour (shortest
legal Manhattan path), repeaters evenly along it (main code path).  Fixes the feed legs into lk_ES0 / lk_ES1 whose
repeaters snapped 1.1-1.2 mm apart along the VDDPHY domain edge (1.44-1.66 ns slew, GRT A).
    kit_detour.py SPAN_X <die_trial kit args...>"""
import sys
from pathlib import Path
span = float(sys.argv[1])
import os
WT = Path(os.environ.get("OT_KIT_WT", "/srv/opentallas-scratch2/claude/wt/die-s81-5"))
sys.path.insert(0, str(WT / "tools" / "die_plan"))
import die_trial as DT
DT.DETOUR_SPAN_X = span
DT.leg_blocked_run = lambda site, a, b, step=1.08: float("inf")   # gate the detour on the span test alone
_ld = DT.legal_detour
def _ld_retry(site, a, b, step=5.4, margin=600.0, turn_um=20.0):
    # the legal channel past a PHY domain can be a 3-5 um sliver (lk_ES0 top: domain halo .. next partition core), which
    # a 5.4-um A* grid anchored at bbox-600 can miss (probe 01:35: 778/849 None at m600, found at m1500; 12129 at 2.16)
    for st, m in ((step, margin), (step, 1500.0), (2.16, margin), (2.16, 1500.0)):
        poly = _ld(site, a, b, step=st, margin=m, turn_um=turn_um)
        if poly is not None:
            return poly
    return None
DT.legal_detour = _ld_retry
sys.exit(DT.main(sys.argv[2:]))
