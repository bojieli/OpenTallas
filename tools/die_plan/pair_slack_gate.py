"""OWNER 12.25 (2026-10-31 ~01:5x, all dies): the die clock gate is the routed related-pair SLACK, not the skew.

The die clock passes on routed die STA with the real DRT+RCX clock on the 12.24c basis (nominal policy, optimistic RCX,
CPPR at the last common tree node) when
  (a) worst TT setup slack >= 0 on every related pair,
  (b) worst FF hold slack >= +HOLD_MIN_PS (10 ps, on top of the 25 ps hold uncertainty; hold safe by structure),
  (c) every hard block's clock-arrival contract (the tap window used at its sign-off) holds: 0 violations.
Related-pair skew > SKEW_TARGET_PS (150 ps) is a design TARGET: it adds a WARN, never a FAIL.  Missing numbers fail
closed (NOT RUN); unmeasured hold pairs (OWNER 12.19) give BLOCKED(kits), never PASS.

One verdict function for every die clock report (die_sta_related summary, die_infra freeze gate, die_sta).
"""
from __future__ import annotations

import math

RULE = "OWNER 12.25: TT setup >= 0, FF hold >= +10 ps, block arrival-contract violations = 0; skew > 150 ps = WARN only"
SETUP_MIN_PS = 0.0
HOLD_MIN_PS = 10.0
SKEW_TARGET_PS = 150.0
BLOCKED = "BLOCKED(kits)"


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def verdict(tt_setup_ps, ff_hold_ps, contract_violations, skew_max_ps=None, hold_unmeasured=0, setup_neg_pairs=None):
    """-> dict(verdict PASS/FAIL/BLOCKED(kits)/NOT RUN, reasons, warnings, the inputs, rule)."""
    out = dict(rule=RULE, tt_setup_ps=tt_setup_ps, ff_hold_ps=ff_hold_ps, hold_min_ps=HOLD_MIN_PS,
               contract_violations=contract_violations, skew_max_ps=skew_max_ps, skew_target_ps=SKEW_TARGET_PS,
               skew_role="TARGET (WARN only, never FAIL)", reasons=[], warnings=[])
    missing = [n for n, v in (("tt_setup_ps", tt_setup_ps), ("ff_hold_ps", ff_hold_ps)) if not _num(v)
               and not (n == "ff_hold_ps" and v is None and hold_unmeasured)]   # all hold pairs unmeasured -> BLOCKED
    if not (isinstance(contract_violations, int) and not isinstance(contract_violations, bool)
            and contract_violations >= 0):
        missing.append("contract_violations")
    if _num(skew_max_ps) and skew_max_ps > SKEW_TARGET_PS:
        out["warnings"].append(f"related-pair skew {skew_max_ps:.2f} ps > target {SKEW_TARGET_PS:g} ps (WARN only)")
    if _num(tt_setup_ps) and tt_setup_ps < SETUP_MIN_PS or (setup_neg_pairs or 0) > 0:
        out["reasons"].append(f"TT setup {tt_setup_ps} ps < 0" + (f" ({setup_neg_pairs} pairs)" if setup_neg_pairs else ""))
    if _num(ff_hold_ps) and ff_hold_ps < HOLD_MIN_PS:
        out["reasons"].append(f"FF hold {ff_hold_ps} ps < +{HOLD_MIN_PS:g} ps")
    if isinstance(contract_violations, int) and not isinstance(contract_violations, bool) and contract_violations > 0:
        out["reasons"].append(f"{contract_violations} block arrival-contract violation(s)")
    if out["reasons"]:
        out["verdict"] = "FAIL"
    elif missing:
        out["verdict"] = "NOT RUN"
        out["reasons"].append("missing: " + ", ".join(missing))
    elif hold_unmeasured:
        out["verdict"] = BLOCKED
        out["reasons"].append(f"{hold_unmeasured} hold pairs without signed real views (OWNER 12.19)")
    else:
        out["verdict"] = "PASS"
    return out


def from_related(res):
    """the 12.25 verdict of a die_sta_related record ({corners: {TT, FF: {classes}}}) over the gated classes
    (intra, seam, intra_cross_region; landed via its own plan landing window; *_INFO excluded)."""
    cls = {c: (res.get("corners", {}).get(c) or {}).get("classes", {}) for c in ("TT", "FF")}
    setups, holds, skews, neg, unmeas, contract, missing = [], [], [], 0, 0, 0, []
    for k in sorted(set(cls["TT"]) | set(cls["FF"])):
        if k.upper().endswith("_INFO"):
            continue
        t, f = cls["TT"].get(k, {}), cls["FF"].get(k, {})
        if not (t.get("pairs") or f.get("pairs")):
            continue
        for v in (t, f):
            if _num(v.get("skew_diag_max_ps")):
                skews.append(v["skew_diag_max_ps"])
        if k.startswith("landed"):
            pt, pf = t.get("plan_landing") or {}, f.get("plan_landing") or {}
            if pt.get("verdict") != "PASS" or pf.get("verdict") != "PASS":
                contract += 1 if (pt or pf) else 0
                if not (pt and pf):
                    missing.append(f"{k}: plan_landing")
            continue
        setups.append(t.get("worst_setup_slack_ps"))
        neg += int(t.get("setup_neg_pairs") or 0)
        hm = f.get("hold_measured")
        if hm:
            holds.append(hm.get("hold_margin_ps") if hm.get("pairs_measured") else math.inf)
            unmeas += int(hm.get("pairs_unmeasured") or 0)
        else:
            holds.append(f.get("worst_hold_slack_ps"))
        kc = f.get("kit_contract_hold")
        if kc is None:
            missing.append(f"{k}: kit_contract_hold (FF)")
        else:
            contract += int(kc.get("neg_pairs") or 0)
    ws = min(setups) if setups and all(_num(x) for x in setups) else None
    hs = [h for h in holds if h != math.inf]
    wh = (min(hs) if hs else (math.inf if holds else None)) if all(_num(x) or x == math.inf for x in holds) else None
    if wh == math.inf:          # every hold pair unmeasured: no number (BLOCKED(kits) via hold_unmeasured)
        wh = None
    v = verdict(ws, wh, None if missing else contract, max(skews) if skews else None, unmeas, neg)
    if missing:
        v["missing"] = missing
    return v
