#!/usr/bin/env python3
"""HBM big-core GRT FF hold-repair TARGET (HBM-CORES-B 11-09, COORD ruling 11-09).

usage: hold_margin_pick.py HM CONFIG_MK NATIVE_CELL_COUNT_JSON
prints one line: OT_HOLD_PICK hm=<ps> scope=<reg2reg|nonport|-> reason=<text>
(a kit that already sets OT_HOLD_REPAIR_SCOPE=nonport keeps nonport; otherwise the target comes with reg2reg)

Measured GRT -> sign-off FF hold drift on routed HBM cores (core-owned, reg2reg): q3bc_SF1 33.6 ps, q3bc_E2b 38.9 ps
(both > 130k stdcells), own_vRF4T 21.6 ps, qmca_vSR3 22.9 ps.  A GRT repair margin of 0-10 ps leaves the big cores
20-35 ps short at sign-off.  The kit config carries OT_HOLD_FF_MARGIN_BIG (target ps) and OT_HOLD_FF_MARGIN_BIG_CELLS
(stdcell threshold); when the pre-floorplan native cell count (native_cell_cap.tcl receipt) is above the threshold
and the target is above the Make margin HM, the GRT hold repair uses the target with OT_HOLD_REPAIR_SCOPE=reg2reg
(port-start / port-end hold stays the parent's).  This is a repair TARGET only: every hold GATE (kit sign-off,
eco_loop, die STA, counter) stays FF hold slack >= 0 (OWNER 11-02).  A kit without the two keys, without the receipt,
or at or below the threshold keeps HM and its own scope.
"""
import json
import math
import re
import sys

KEYS = ("OT_HOLD_FF_MARGIN_BIG", "OT_HOLD_FF_MARGIN_BIG_CELLS")


def mk_value(text, key):
    """last `[override] export KEY = value` in a config.mk text (Make: the last assignment wins)"""
    val = None
    for line in text.splitlines():
        m = re.match(r"^\s*(?:override\s+)?(?:export\s+)?" + re.escape(key) + r"\s*[:?]?=\s*(.*?)\s*$", line)
        if m:
            val = m.group(1)
    return val


def finite(s):
    x = float(s)
    if not math.isfinite(x):
        raise ValueError(f"not finite: {s}")
    return x


def pick(hm, cfg_text, cells_text):
    """returns (hm_ps, scope or None, reason)"""
    hm = finite(hm)
    big, ncells = (mk_value(cfg_text, k) for k in KEYS)
    if big is None or ncells is None:
        return hm, None, "no big-core target in config"
    big, ncells = finite(big), int(finite(ncells))
    if cells_text is None:
        return hm, None, "no native_cell_count receipt"
    try:
        std = int(json.loads(cells_text)["stdcells"])
    except (ValueError, KeyError, TypeError) as e:
        return hm, None, f"unreadable native_cell_count receipt ({type(e).__name__})"
    if std <= ncells:
        return hm, None, f"{std} stdcells <= {ncells}"
    if big <= hm:
        return hm, None, f"{std} stdcells > {ncells} but target {big:g} <= margin {hm:g}"
    kit_scope = (mk_value(cfg_text, "OT_HOLD_REPAIR_SCOPE") or "").strip().lower()
    scope = kit_scope if kit_scope in ("reg2reg", "nonport") else "reg2reg"
    return big, scope, f"{std} stdcells > {ncells}: big-core GRT hold target {big:g} ps ({scope}), was {hm:g}"


def main(argv):
    if len(argv) != 4:
        print(__doc__.split("\n")[2], file=sys.stderr)
        return 2
    cfg = open(argv[2]).read()
    try:
        cells = open(argv[3]).read()
    except OSError:
        cells = None
    hm, scope, why = pick(argv[1], cfg, cells)
    print(f"OT_HOLD_PICK hm={hm:g} scope={scope or '-'} reason={why}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
