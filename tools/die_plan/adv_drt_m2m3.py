#!/usr/bin/env python3
"""adv_drt_m2m3.py -- report-only INVENTORY ADV-DRT-M2M3 (FP-CONVERGE-QC, COORD 11-25).  NOT CALIBRATED: no FAIL threshold.

Why: 41 QC kits sat 10-29 h in detailed route with 18k-60k DRV (slw_sc_v2 x3, sle_fe_v2, sle_sc_v1, sle_fw_v2, coll_core); QC-DRT-LAYERS
(11-25) measured that on sle_sc_v1 / sle_fw_v2 70-80 % of GRT demand sits on M2+M3, so the M2/M3 pin-access + local-demand load
of the placed cells is what DRT pays for.  The plan has no netlist, so this reports three plan-level proxies per type:
  rho    cells / soft area (outline minus hard cores) um^-2: plan `cells`, else the kit/sibling count of adv_density   std-cell pin
         access on M2/M3 (cell pins sit on M1/M2); the same figure as ADV-DENSITY
  hot    gcells of ADV-ROUTE-DEMAND est. util >= 0.8                  planned bus demand competing for the same tracks
  peak   max ADV-ROUTE-DEMAND util
CALIBRATION (11-25, v13 plan, 130 types): the 7 known DRT-heavy types span rho 0.24-0.38, hot 360-1004, peak 2.2-7.7; they are
NOT separable from the other types by any one proxy or a combination (sle_fw_v2 has rho 0.15, peak 2.4 like 5 other fw types
with no DRT result posted; no list of DRT-clean types exists to fit a threshold).  So a line is an inventory entry, "this type
has at least the load of a known DRT-heavy type on one proxy" (loose floors = the minima of the known set), never a verdict;
fix when calibrated: replace the floors by thresholds fitted on QC-DRT-LAYERS / DRT result per type.

    findings(raw, plan_path=None, tree=None, types=None, **kw) -> ["WARN ADV-DRT-M2M3 INVENTORY ..."]
"""
import re

import adv_density as DN
import adv_route_demand as R

CHECK = "DRT-M2M3"
KNOWN = ("slw_sc_v2", "sle_fe_v2", "sle_sc_v1", "sle_fw_v2", "coll_core")   # DRT-heavy kits (names as posted, prefix match)
RHO_FLOOR = 0.24
HOT_FLOOR = 850
MAX_LINES = 140


def _cells(tn, t, dc, by_base):
    c = t.get("cells")
    if c:
        return float(c)
    r = DN.cells_for(tn, t, dc, by_base)[0]
    return float(r) if r else 0.0


def metrics(t, cells):
    soft, _core = DN.soft_area(t)
    rho = cells / soft if soft > 0 else 0.0
    hot, peak = 0, 0.0
    if t.get("internal_stations") or t.get("ft_slots"):
        u = R.grid(t)["util"]
        peak = max(max(r) for r in u)
        hot = sum(1 for r in u for v in r if v >= R.WARN_UTIL)
    return rho, hot, peak


def findings(raw, plan_path=None, tree=None, types=None, **_kw):
    P = raw.get("partition_types") or {}
    if not P:
        return [f"WARN ADV-{CHECK} not checked: plan has no partition_types"]
    cache, _src = DN.load_cache(None)
    allc = (cache or {}).get("cells") or {}
    die = (raw.get("die") or {}).get("name")
    dc = dict(allc.get(die) or {}) if die in allc else {k: v for d in allc.values() for k, v in d.items()}
    by_base = {}
    for n in dc:
        by_base.setdefault(DN.base_type(n), []).append(n)
    out = []
    for tn in sorted(P):
        t = P[tn]
        if types and not re.search(types, tn):
            continue
        if not isinstance(t, dict) or not t.get("outline_um"):
            continue
        try:
            cells = _cells(tn, t, dc, by_base)
            if not cells:
                continue
            rho, hot, peak = metrics(t, cells)
        except Exception as e:  # noqa: BLE001 an estimator never breaks the gate
            out.append(f"WARN ADV-{CHECK} {tn}: not checked: {type(e).__name__}: {str(e)[:120]}")
            continue
        why = []
        if rho >= RHO_FLOOR:
            why.append("rho %.3f cells/soft-um2 >= %.2f" % (rho, RHO_FLOOR))
        if hot >= HOT_FLOOR:
            why.append("%d hot route-demand gcells >= %d" % (hot, HOT_FLOOR))
        if why:
            known = " [type is a known DRT-heavy kit]" if tn.startswith(KNOWN) else ""
            out.append("WARN ADV-%s INVENTORY %s: at/above the M2/M3 load of a known DRT-heavy type (%s; peak util %.2f)%s; "
                       "uncalibrated proxy, no threshold, not a verdict" % (CHECK, tn, "; ".join(why), peak, known))
    return out[:MAX_LINES]
