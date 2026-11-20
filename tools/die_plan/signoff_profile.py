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
# at P_die (PROPOSAL, HELD by COORD 11-13: default stays 833 ps = the -42 ps gate until the owner decides; 1000 / 1250 via env).  Gate 2 = routed TT WNS at 833 ps >= -(P_die - 833) - 42.
# Override: env OT_DIE_PERIOD_PS (all dies) or OT_DIE_PERIOD_PS_<DIE> (DIE = s81, s81_head, qwen_compute, qwen_kvsys, hbm;
# upper case), e.g. OT_DIE_PERIOD_PS_QWEN_KVSYS=1250.
DIE_PERIOD_DEFAULT_PS = 833.0   # COORD 11-13 18:2x: R-PERIOD held (owner to decide); 1000 = proposal
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
# SIGN-PERIOD (OWNER 2026-11-20 decision (1), SIGN-PROFILE-0400): a type signs at 833 ps where its build passes; otherwise the SAME routed
# DB is re-timed (no re-route) at a relaxed period up to SIGN_PERIOD_MAX_PS and signs there.  Such a record carries signed_period_ps and
# its checks (setup_tt, hold_ff) are measured AT that period (tools/die_plan/period_resign.py: the golden SDC with every create_clock
# period scaled, IO budgets unchanged); the 833 ps result is kept in at_833.  The gates are unchanged: DRC 0, setup >= -42 ps at the
# signed period, internal hold >= 0.  A die runs at the slowest signed type's period (die_period_ps, count_hourly / DIE-PERIOD.tsv).
SIGN_PERIOD_MAX_PS = 1000.0
PERIOD_MATCH_PS = 0.5
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


TIMING_ABS_MAX_PS = 1e6       # OpenSTA prints ~1e42 'INF' slack when a corner has no constrained path: not a measurement


def _num(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) and abs(v) < TIMING_ABS_MAX_PS else None


def internal_hold_measurement(rec):
    """Complete native internal census, or a complete nonnegative all-path bound.

    core_n/core_wns are emitted only after both native searches finish without
    truncation. A zero count/zero bound proves no internal hold miss; it does
    not claim the boundary WNS is zero. Typed summaries may carry that same
    measurement, but an old local SIGNED/port-only verdict is not evidence.
    """
    ff = (rec.get("corners") or {}).get("ff")
    if isinstance(ff, dict):
        c = ff.get("std_min_start") or {}
        if not isinstance(c, dict):
            c = {}
        done = ff.get("done") is True and not ff.get("errors") and ff.get("rc", 0) == 0
        complete = done and c.get("err") == 0 and c.get("trunc") == 0
        w, n = _num(c.get("core_wns")), _num(c.get("core_n"))
        source = "corners.ff.std_min_start.core_wns (complete internal census)"
        # Older native signers omitted the census when every STD min path met.
        # That complete, finite all-path minimum is a stronger internal bound.
        # Never replace a present/ambiguous core census or use another frame.
        if "core_wns" not in c and "core_n" not in c:
            all_w, all_n = _num(ff.get("std_wns_min")), _num(ff.get("std_nviol_min"))
            census_ok = c.get("err", 0) == 0 and c.get("trunc", 0) == 0
            if done and census_ok and all_w is not None and all_w >= 0 and all_n == 0:
                complete, w, n = True, all_w, 0.0
                source = "corners.ff.std_wns_min (complete all-path STD lower bound; no internal census)"
    else:
        c = rec.get("internal_hold") or {}
        if not isinstance(c, dict):
            c = {}
        complete = c.get("schema") == "opentallas.internal_ff_hold.v1" and c.get("complete") is True
        w, n = _num(c.get("wns_ps")), _num(c.get("violators"))
        source = c.get("source") or "typed internal hold summary"
    valid = (complete and w is not None and n is not None and n >= 0 and n.is_integer()
             and ((n == 0 and w >= 0) or (n > 0 and w < 0)))
    return dict(schema="opentallas.internal_ff_hold.v1", complete=bool(valid),
                wns_ps=w if valid else None, violators=int(n) if valid else None,
                source=source, reason=None if valid else "missing or ambiguous complete internal FF measurement")


def boundary_hold_metric(rec):
    ch = rec.get("checks") or {}
    hf = ch.get("hold_ff") if isinstance(ch.get("hold_ff"), dict) else {}
    for value, source in ((hf.get("wns_ps"), "hold_ff.wns_ps (standard overlay)"),
                          (hf.get("sdc_wns_ps"), "hold_ff.sdc_wns_ps (kit SDC)"),
                          (rec.get("ff_wns"), "summary ff_wns")):
        value = _num(value)
        if value is not None:
            return value, source
    return None, None


def metrics(rec):
    """(drc, tt_wns_ps, ff_hold_wns_ps, hold_source) from a signoff.json record or an autopilot job summary
    (keys drc / tt_wns plus a typed complete internal_hold). Missing = None."""
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
    internal = internal_hold_measurement(rec)
    ff, src = internal["wns_ps"], internal["source"]
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


def record_clock_period_ps(rec):
    """largest create_clock period the record's STA ran at (corners.<c>.periods; generated clocks print 0), None when not recorded"""
    best = None
    for c in (rec.get("corners") or {}).values():
        if not isinstance(c, dict) or not isinstance(c.get("periods"), dict):
            continue
        for v in c["periods"].values():
            v = _num(v)
            if v is not None and v > 0 and (best is None or v > best):
                best = v
    return best


def signed_period_ps(rec):
    """the declared sign-off period of a period re-sign record (SIGN-PERIOD), else None"""
    return _num(rec.get("signed_period_ps"))


def period_problem(rec):
    """None when the record's timing period is admissible: no signed_period_ps and no clock above 833 ps, or a signed_period_ps in
    [833, 1000] that equals the period the STA really ran at.  Else the reason (blocks the setup gate: the setup number is not a
    measurement at an admissible period)."""
    sp, cp = signed_period_ps(rec), record_clock_period_ps(rec)
    if sp is None:
        if cp is not None and cp > PERIOD_PS + PERIOD_MATCH_PS:
            return f"clock period {cp:g} ps above {PERIOD_PS:g} without signed_period_ps"
        return None
    if sp < PERIOD_PS - PERIOD_MATCH_PS or sp > SIGN_PERIOD_MAX_PS + 1e-6:
        return f"signed_period_ps {sp:g} outside [{PERIOD_PS:g}, {SIGN_PERIOD_MAX_PS:g}]"
    if cp is None:
        return f"signed_period_ps {sp:g} without a recorded STA clock period"
    if abs(cp - sp) > PERIOD_MATCH_PS:
        return f"signed_period_ps {sp:g} but the STA clock period is {cp:g}"
    return None


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
    sp, pprob = signed_period_ps(rec), period_problem(rec)
    tol = SETUP_TOL_PS if sp is not None else setup_tolerance_ps(die)   # a period record is timed AT its period: plain -42 ps
    gates = gate_verdicts(drc, tt, ff, tol)
    if pprob and gates["setup_tt"] == "PASS":
        gates["setup_tt"] = "FAIL"
    boundary_ff, boundary_source = boundary_hold_metric(rec)
    port_only = ff is not None and ff >= HOLD_MIN_PS and boundary_ff is not None and boundary_ff < HOLD_MIN_PS
    reasons = []
    if gates["drc"] != "PASS":
        reasons.append(f"drc: {gates['drc']}" + ("" if drc is None else f" {drc}"))
    if pprob:
        reasons.append(f"setup_tt: FAIL period: {pprob}")
    elif gates["setup_tt"] != "PASS":
        reasons.append(f"setup_tt: {gates['setup_tt']}" + ("" if tt is None else f" WNS {tt:+.2f} ps < -{tol:g} "
                                                            + (f"at signed period {sp:g} ps" if sp is not None else f"(P_die {die_period_ps(die):g} ps)")))
    if gates["hold_ff"] != "PASS":
        reasons.append(f"hold_ff: {gates['hold_ff']}" + ("" if ff is None else f" WNS {ff:+.2f} ps < {HOLD_MIN_PS:g}"))
    # HEAD-DIE-R 11-17 (COORD): balance pads on a forwarded-clock output (fwd_pad_check.py) shift the receiver's
    # landing clock by ns at die level while the type STA stays clean: blocking whenever the record measured it
    fp = (rec.get("checks") or {}).get("fwd_pads")
    if isinstance(fp, dict) and fp.get("verdict") in ("PASS", "FAIL"):
        gates["fwd_pads"] = fp["verdict"]
        if fp["verdict"] == "FAIL":
            reasons.append(f"fwd_pads: FAIL {', '.join(fp.get('failing') or [])} max {fp.get('max_pads')} "
                           f"delaybuf_otstb > {fp.get('limit')} on fclk_out")
    adv = []
    for k, v in sorted((rec.get("checks") or {}).items()):
        if k in MINIMAL_GATES or k == "fwd_pads" or not isinstance(v, dict):
            continue
        if v.get("verdict") not in ("PASS", "REPORT", "WARN", None):
            adv.append(f"{k}: {v.get('verdict')}")
    for r in rec.get("reasons") or []:          # summary-only records (autopilot job 'signoff')
        k = str(r).split(":", 1)[0]
        if k not in MINIMAL_GATES and not any(a.startswith(k + ":") for a in adv):
            adv.append(str(r)[:160])
    return dict(verdict="SIGNED" if not reasons else "NOT SIGNED", profile="minimal", gates=gates, reasons=reasons,
                advisories=adv + ([f"hold_ff: boundary hold {boundary_ff:+.2f} ps (io_hold_parent, die STA; advisory)"]
                                  if boundary_ff is not None and boundary_ff < 0 else []),
                drc=drc, tt_wns_ps=tt, ff_hold_wns_ps=ff, hold_source=src, hold_port_only=port_only,
                boundary_ff_hold_wns_ps=boundary_ff, boundary_hold_source=boundary_source,
                internal_hold=internal_hold_measurement(rec),
                setup_within_tolerance=tt is not None and -tol <= tt < 0, die=die, die_period_ps=die_period_ps(die),
                setup_tolerance_ps=tol,
                achieved_period_ps=achieved_period_ps(tt) if sp is None else sp,
                signed_period_ps=(sp if sp is not None else PERIOD_PS) if not reasons else None,
                period_problem=pprob, legacy_verdict=rec.get("verdict"))


def apply(rec, value=None):
    """signoff.py hook: under the minimal profile, keep the legacy verdict/reasons as legacy_* and set the record's
    verdict/reasons from judge(); legacy profile: the record is returned unchanged (profile='legacy' stamped)."""
    if not is_minimal(value):
        rec["profile"] = "legacy"
        return rec
    j = judge(rec)
    rec["legacy_verdict"], rec["legacy_reasons"] = rec.get("verdict"), list(rec.get("reasons") or [])
    rec.update(verdict=j["verdict"], reasons=j["reasons"], advisories=j["advisories"], profile="minimal",
               profile_gates=j["gates"], internal_hold=j["internal_hold"], achieved_period_ps=j["achieved_period_ps"],
               setup_within_tolerance=j["setup_within_tolerance"], die_period_ps=j["die_period_ps"],
               **({"signed_period_ps": signed_period_ps(rec)} if signed_period_ps(rec) is not None else {}),
               profile_rule="R-MINIMAL + R-PERIOD (OWNER 2026-11-13)")
    return rec


def die_period_from_types(periods):
    """SIGN-PERIOD: a die runs at the slowest signed type's period.  periods = iterable of signed type periods (None = 833) -> ps"""
    vals = [PERIOD_PS if p is None else float(p) for p in periods]
    return max(vals) if vals else PERIOD_PS


def signed_die_period_ps(die, path=None):
    """die_period_ps of a die from the count's lanes/DIE-PERIOD.tsv (count_hourly writes it: die, die_period_ps, slowest type, ...);
    833 when the file or row is missing.  For the die STA (run the die at this period)."""
    import pathlib
    d = DIE_ALIAS.get(str(die or "").lower(), str(die or "").lower())
    p = pathlib.Path(path or os.environ.get("OT_DIE_PERIOD_TSV") or pathlib.Path.home() / "coord/lanes/DIE-PERIOD.tsv")
    try:
        for ln in p.read_text().splitlines():
            f = ln.split("\t")
            if len(f) >= 2 and not ln.startswith("#") and DIE_ALIAS.get(f[0], f[0]) == d and _num(f[1]) is not None:
                return _num(f[1])
    except OSError:
        pass
    return PERIOD_PS


def die_gate_thresholds(value=None):
    """die clock gate: minimal = routed related-pair setup >= 0 at the achieved period, hold >= 0 (one corner pair),
    kit window advisory; legacy = setup >= 0 at 833 ps, hold >= +10 ps, kit window blocking"""
    if is_minimal(value):
        return dict(setup_min_ps=0.0, hold_min_ps=0.0, period="achieved", kit_window_blocking=False)
    return dict(setup_min_ps=0.0, hold_min_ps=10.0, period=PERIOD_PS, kit_window_blocking=True)
