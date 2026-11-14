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
# R-PERIOD (OWNER 11-13 "we can accept cost in area, performance, clock frequency"; EXPERT-REVIEW-3): each die signs off
# at P_die (default 1000 ps; COORD may raise one die, e.g. 1250).  Gate 2 = routed TT WNS at 833 ps >= -(P_die - 833) - 42.
# Override: env OT_DIE_PERIOD_PS (all dies) or OT_DIE_PERIOD_PS_<DIE> (DIE = s81, s81_head, qwen_compute, qwen_kvsys, hbm;
# upper case), e.g. OT_DIE_PERIOD_PS_QWEN_KVSYS=1250.
DIE_PERIOD_DEFAULT_PS = 1000.0
DIE_ALIAS = {"qc": "qwen_compute", "kv": "qwen_kvsys", "head": "s81_head", "results": "s81_head", "cp1": "s81"}


def die_period_ps(die=None):
    """P_die of a die (R-PERIOD); legacy profile: 833"""
    if not is_minimal():
        return PERIOD_PS
    d = DIE_ALIAS.get(str(die or "").lower(), str(die or "").lower())
    for k in ([f"OT_DIE_PERIOD_PS_{d.upper()}"] if d else []) + ["OT_DIE_PERIOD_PS"]:
        v = _num(os.environ.get(k))
        if v is not None:
            return v
    return DIE_PERIOD_DEFAULT_PS


def setup_tolerance_ps(die=None):
    """|min TT WNS at 833 ps| that still signs off: (P_die - 833) + 42"""
    return max(0.0, die_period_ps(die) - PERIOD_PS) + SETUP_TOL_PS
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


def internal_hold_port_only(rec):
    """True when the record shows every negative FF hold endpoint starts at an INPUT PORT (signoff.py port_only_hold,
    OWNER rule COORD 11-06: such a miss is the io_hold_parent obligation, i.e. port hold, measured once at die STA), so
    the INTERNAL reg-to-reg hold is >= 0.  Full records: checks.hold_ff.port_only_needs_parent; autopilot summaries:
    hold_ff absent from 'fails' while the local verdict is SIGNED (the local hold check passed)."""
    hf = (rec.get("checks") or {}).get("hold_ff")
    if isinstance(hf, dict):
        return bool(hf.get("port_only_needs_parent")) and hf.get("verdict") == "PASS"
    fails = rec.get("fails")
    return (isinstance(fails, list) and "hold_ff" not in fails and rec.get("local_verdict") == "SIGNED"
            and not any(str(r).startswith("hold_ff") for r in rec.get("reasons") or []))


def achieved_period_ps(tt_wns):
    """the routed period this type closes at: 833 - min(0, WNS) (a positive slack keeps the plan period)"""
    return None if tt_wns is None else round(PERIOD_PS - min(0.0, tt_wns), 2)


def gate_verdicts(drc, tt, ff, tol=SETUP_TOL_PS):
    return dict(drc="NOT RUN" if drc is None else ("PASS" if drc == 0 else "FAIL"),
                setup_tt="NOT RUN" if tt is None else ("PASS" if tt >= -tol else "FAIL"),
                hold_ff="NOT RUN" if ff is None else ("PASS" if ff >= HOLD_MIN_PS else "FAIL"))


def record_die(rec):
    """the die of a record: rec['die'] (autopilot job / summary) or the kit path (.../kit-wave/<die>/... | die_plan/<die>/)"""
    if rec.get("die"):
        return rec["die"]
    import re
    k = str(((rec.get("inputs") or {}).get("kit")) or rec.get("path") or rec.get("base") or "")
    m = re.search(r"/kit-wave/(s81_head|s81|qwen_compute|qwen_kvsys|hbm)/", k) or \
        re.search(r"die_plan/(s81_head|s81|qwen_compute|qwen_kvsys|hbm)/", k)
    return m.group(1) if m else None


def judge(rec, die=None):
    """R-MINIMAL judgement of one record (does not modify it).
    -> dict(verdict SIGNED|NOT SIGNED, gates, reasons (blocking), advisories, tt_wns_ps, ff_hold_wns_ps, drc,
            achieved_period_ps, setup_within_tolerance, legacy_verdict)"""
    drc, tt, ff, src = metrics(rec)
    die = die or record_die(rec)
    tol = setup_tolerance_ps(die)
    gates = gate_verdicts(drc, tt, ff, tol)
    port_only = ff is not None and ff < HOLD_MIN_PS and internal_hold_port_only(rec)
    if port_only:
        gates["hold_ff"] = "PASS"          # internal reg-to-reg hold >= 0; the port-start hold is the die STA's (advisory)
    reasons = []
    if gates["drc"] != "PASS":
        reasons.append(f"drc: {gates['drc']}" + ("" if drc is None else f" {drc}"))
    if gates["setup_tt"] != "PASS":
        reasons.append(f"setup_tt: {gates['setup_tt']}" + ("" if tt is None else f" WNS {tt:+.2f} ps < -{tol:g} "
                                                            f"(P_die {die_period_ps(die):g} ps)"))
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
                advisories=adv + ([f"hold_ff: port-start hold {ff:+.2f} ps (io_hold_parent, die STA)"] if port_only else []),
                drc=drc, tt_wns_ps=tt, ff_hold_wns_ps=ff, hold_source=src, hold_port_only=port_only,
                setup_within_tolerance=tt is not None and -tol <= tt < 0, die=die, die_period_ps=die_period_ps(die),
                setup_tolerance_ps=tol,
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
               setup_within_tolerance=j["setup_within_tolerance"], die_period_ps=j["die_period_ps"],
               profile_rule="R-MINIMAL + R-PERIOD (OWNER 2026-11-13)")
    return rec


def die_gate_thresholds(value=None):
    """die clock gate: minimal = routed related-pair setup >= 0 at the achieved period, hold >= 0 (one corner pair),
    kit window advisory; legacy = setup >= 0 at 833 ps, hold >= +10 ps, kit window blocking"""
    if is_minimal(value):
        return dict(setup_min_ps=0.0, hold_min_ps=0.0, period="achieved", kit_window_blocking=False)
    return dict(setup_min_ps=0.0, hold_min_ps=10.0, period=PERIOD_PS, kit_window_blocking=True)
