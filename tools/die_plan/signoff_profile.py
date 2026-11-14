#!/usr/bin/env python3
"""Sign-off profile (OWNER 2026-11-13 R-MINIMAL, lanes/RULEBOOK-1113.md; supersedes R-PROFILE KEEP/RELAX).

ONE switch, env OT_SIGNOFF_PROFILE:
  minimal (default)  the ONLY blocking type sign-off gates are
                       1. detailed route DRC == 0
                       2. routed TT setup WNS >= -42 ps (5 % of 833 ps); the achieved period is recorded
                       3. internal reg-to-reg FF hold WNS >= 0 ps (no tolerance, no +10 margin)
                       4. bind + LATCHECK lane latency: checked when the kit is generated (strict bind) and at die
                          level (token pass); a routed record that exists came from a bound kit
                     everything else (LEC pre/post, antenna, DRV slew/cap/fanout, clock insertion band, sdc_lint,
                     face_guard, PG census, G0/G0C, preflight, visual verdict, io_hold_parent receipts, kit-window
                     contract, no-blind-retry, route-hold / visual-wait states) is ADVISORY: reported, never blocking.
  legacy             the previous behaviour, unchanged (every BLOCKING check of signoff.py, io_hold_parent obligation,
                     routed LEC in signoff_chain, visual gate in the autopilot ...).

Die clock gate (R-PROFILE, kept by R-MINIMAL): routed related-pair setup >= 0 at the achieved period and hold >= 0,
one corner pair; the kit-window contract is advisory.  See die_gate_thresholds().

This module is a pure function of a signoff.json record, so the same judgement runs in signoff.py (new records),
signoff_chain.py (records written by an older kit-frozen signoff.py) and rejudge_minimal.py (existing results).
"""
import math
import os

PERIOD_PS = 833.0
SETUP_TOL_PS = 42.0          # 5 % of 833 ps
HOLD_MIN_PS = 0.0            # internal FF hold, no tolerance
MINIMAL_GATES = ("drc", "setup_tt", "hold_ff")
PROFILES = ("minimal", "legacy")
ENV = "OT_SIGNOFF_PROFILE"


def profile(value=None):
    """the active profile: explicit value, else env OT_SIGNOFF_PROFILE, else 'minimal'"""
    p = str(value if value is not None else os.environ.get(ENV, "minimal") or "minimal").strip().lower()
    if p not in PROFILES:
        raise ValueError(f"{ENV}={p!r}: expected one of {PROFILES}")
    return p


def is_minimal(value=None):
    return profile(value) == "minimal"


def _num(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def metrics(rec):
    """(drc, tt_wns_ps, ff_hold_wns_ps, hold_source) from a signoff.json record or an autopilot job summary
    (keys drc / tt_wns / ff_wns).  Missing = None."""
    ch = rec.get("checks") or {}
    drc = (ch.get("drc") or {}).get("count") if isinstance(ch.get("drc"), dict) else None
    if drc is None:
        drc = (rec.get("route") or {}).get("drc")
    if drc is None:
        drc = rec.get("drc")
    st = ch.get("setup_tt") if isinstance(ch.get("setup_tt"), dict) else {}
    tt = _num(st.get("wns_ps"))
    if tt is None:
        tt = _num(st.get("sdc_wns_ps"))
    if tt is None:
        tt = _num(rec.get("tt_wns"))
    hf = ch.get("hold_ff") if isinstance(ch.get("hold_ff"), dict) else {}
    ff, src = _num(hf.get("wns_ps")), "hold_ff.wns_ps (standard overlay)"
    if ff is None:
        ff, src = _num(hf.get("sdc_wns_ps")), "hold_ff.sdc_wns_ps (kit SDC)"
    if ff is None:
        ff, src = _num(rec.get("ff_wns")), "summary ff_wns"
    if ff is None:
        src = None
    return (None if drc is None else int(drc)), tt, ff, src


def achieved_period_ps(tt_wns):
    """the routed period this type closes at: 833 - min(0, WNS) (a positive slack keeps the plan period)"""
    return None if tt_wns is None else round(PERIOD_PS - min(0.0, tt_wns), 2)


def gate_verdicts(drc, tt, ff):
    return dict(drc="NOT RUN" if drc is None else ("PASS" if drc == 0 else "FAIL"),
                setup_tt="NOT RUN" if tt is None else ("PASS" if tt >= -SETUP_TOL_PS else "FAIL"),
                hold_ff="NOT RUN" if ff is None else ("PASS" if ff >= HOLD_MIN_PS else "FAIL"))


def judge(rec):
    """R-MINIMAL judgement of one record (does not modify it).
    -> dict(verdict SIGNED|NOT SIGNED, gates, reasons (blocking), advisories, tt_wns_ps, ff_hold_wns_ps, drc,
            achieved_period_ps, setup_within_tolerance, legacy_verdict)"""
    drc, tt, ff, src = metrics(rec)
    gates = gate_verdicts(drc, tt, ff)
    reasons = []
    if gates["drc"] != "PASS":
        reasons.append(f"drc: {gates['drc']}" + ("" if drc is None else f" {drc}"))
    if gates["setup_tt"] != "PASS":
        reasons.append(f"setup_tt: {gates['setup_tt']}" + ("" if tt is None else f" WNS {tt:+.2f} ps < -{SETUP_TOL_PS:g}"))
    if gates["hold_ff"] != "PASS":
        reasons.append(f"hold_ff: {gates['hold_ff']}" + ("" if ff is None else f" WNS {ff:+.2f} ps < {HOLD_MIN_PS:g}"))
    adv = []
    for k, v in sorted((rec.get("checks") or {}).items()):
        if k in MINIMAL_GATES or not isinstance(v, dict):
            continue
        if v.get("verdict") not in ("PASS", "REPORT", "WARN", None):
            adv.append(f"{k}: {v.get('verdict')}")
    for r in rec.get("reasons") or []:          # summary-only records (autopilot job 'signoff')
        k = str(r).split(":", 1)[0]
        if k not in MINIMAL_GATES and not any(a.startswith(k + ":") for a in adv):
            adv.append(str(r)[:160])
    return dict(verdict="SIGNED" if not reasons else "NOT SIGNED", profile="minimal", gates=gates, reasons=reasons,
                advisories=adv, drc=drc, tt_wns_ps=tt, ff_hold_wns_ps=ff, hold_source=src,
                setup_within_tolerance=tt is not None and -SETUP_TOL_PS <= tt < 0,
                achieved_period_ps=achieved_period_ps(tt), legacy_verdict=rec.get("verdict"))


def apply(rec, value=None):
    """signoff.py hook: under the minimal profile, keep the legacy verdict/reasons as legacy_* and set the record's
    verdict/reasons from judge(); legacy profile: the record is returned unchanged (profile='legacy' stamped)."""
    if not is_minimal(value):
        rec["profile"] = "legacy"
        return rec
    j = judge(rec)
    rec["legacy_verdict"], rec["legacy_reasons"] = rec.get("verdict"), list(rec.get("reasons") or [])
    rec.update(verdict=j["verdict"], reasons=j["reasons"], advisories=j["advisories"], profile="minimal",
               profile_gates=j["gates"], achieved_period_ps=j["achieved_period_ps"],
               setup_within_tolerance=j["setup_within_tolerance"], profile_rule="R-MINIMAL (OWNER 2026-11-13)")
    return rec


def die_gate_thresholds(value=None):
    """die clock gate: minimal = routed related-pair setup >= 0 at the achieved period, hold >= 0 (one corner pair),
    kit window advisory; legacy = setup >= 0 at 833 ps, hold >= +10 ps, kit window blocking"""
    if is_minimal(value):
        return dict(setup_min_ps=0.0, hold_min_ps=0.0, period="achieved", kit_window_blocking=False)
    return dict(setup_min_ps=0.0, hold_min_ps=10.0, period=PERIOD_PS, kit_window_blocking=True)
