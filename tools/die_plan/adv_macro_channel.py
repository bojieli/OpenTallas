"""ADV-MACRO-CHANNEL (FP-CONVERGE-HEAD 11-25; an estimator, report only, never a gate).

Class: macro channel width.  HEAD colfix measured the channel between two facing hard cores at 8.16 um and needed 14.88 um before
GRT could route the bus through it (a bus of N wires needs N / tracks-per-um of free width; a sliver also loses its PG strap and
pin-access gcells).  No existing check reads the gap between hard cores: ADV-SITE-IN-MACRO tests sites against cores,
ADV-BAND-GAP the landing bands, ADV-EDGE-STRIP the core-to-outline strip.

Per type (type frame, um): every pair of hard_cores[] / lef contents boxes (R90/R270 swap w and h) whose projections overlap by
at least MIN_RUN_UM (20 um) along the shared axis and whose facing edges are 0 < gap < MIN_CHANNEL_UM (14.88 um apart; override
env OT_ADV_MACRO_CHANNEL_UM) is a WARN.  Touching (gap 0, abutted macros: no channel is needed) and overlapping boxes (ADV-GHOST-MACRO /
GEOM own those) are not reported here.
Fix: widen the channel to >= 14.88 um (pre-approved growth: move a core, or grow the outline) or abut the cores.
findings(raw, plan_path, tree=None, **kw) -> WARN lines.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_site_in_macro as M  # noqa: E402

CHECK = "ADV-MACRO-CHANNEL"
MIN_CHANNEL_UM = float(os.environ.get("OT_ADV_MACRO_CHANNEL_UM", "14.88"))
MIN_RUN_UM = 20.0
EPS = 1e-6
MAX_EX = 4


def channels(t, min_um=None, min_run=MIN_RUN_UM):
    """-> [(gap_um, run_um, name_a, name_b, axis)] facing core pairs with 0 < gap < min_um"""
    min_um = MIN_CHANNEL_UM if min_um is None else min_um
    r = M.core_rects(t)
    out = []
    for i in range(len(r)):
        for j in range(i + 1, len(r)):
            a, b = r[i], r[j]
            runx = min(a[2], b[2]) - max(a[0], b[0])
            runy = min(a[3], b[3]) - max(a[1], b[1])
            if runx >= min_run and runy < -EPS:                       # stacked in y: the channel runs along x
                gap = -runy
                axis = "EW"
                run = runx
            elif runy >= min_run and runx < -EPS:
                gap = -runx
                axis = "NS"
                run = runy
            else:
                continue
            if EPS < gap < min_um - 0.005:
                out.append((round(gap, 3), round(run, 2), a[5], b[5], axis))
    return sorted(out)


def findings(raw, plan_path=None, tree=None, **_kw):
    out = []
    n = 0
    for tn, t in sorted((raw.get("partition_types") or {}).items()):
        if not isinstance(t, dict):
            continue
        ch = channels(t)
        if not ch:
            continue
        n += len(ch)
        ex = "; ".join(f"{a} / {b} {g:g} um over {r:g} um ({ax})" for g, r, a, b, ax in ch[:MAX_EX])
        out.append(f"WARN {CHECK} {tn}: {len(ch)} core pair(s) with a channel < {MIN_CHANNEL_UM:g} um (min {ch[0][0]:g}): {ex}")
    if out:
        out.append(f"LIST {CHECK} {len(out)} type(s), {n} narrow channel(s) (fix: widen to >= {MIN_CHANNEL_UM:g} um or abut the cores)")
    return out


if __name__ == "__main__":
    import json
    for line in findings(json.loads(Path(sys.argv[1]).read_text()), sys.argv[1]):
        print(line)
