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
import hashlib
import json
import math
import os
import re

PERIOD_PS = 833.0
SETUP_TOL_PS = 42.0          # 5 % of 833 ps
def die_period_ps(die=None):
    """Return the 833 ps sign-off period for every die."""
    return PERIOD_PS


def setup_tolerance_ps(die=None):
    """Return the allowed routed TT setup miss at 833 ps."""
    return SETUP_TOL_PS


HOLD_MIN_PS = 0.0            # internal FF hold, no tolerance
# Period (OWNER 11-20): every sign-off is timed at 833 ps.  A record whose STA ran at a relaxed clock (corners.<c>.periods above 833) is
# NOT a sign-off, whether or not it declares signed_period_ps; period_problem() blocks its setup gate.
# OWNER 11-20 (superseding the 1000 ps part of (1)): "Fix hold structurally, never by changing the clock. Fix setup misses with more
# pipeline stages."  NOTHING signs above 833 ps: a signed_period_ps above 833 is refused like any other relaxed clock.  The achievable
# period of a routed DB is a REPORT-ONLY number (tools/die_plan/period_resign.py period_report.json: how far a type is from 833).
SIGN_PERIOD_MAX_PS = PERIOD_PS
ACHIEVABLE_REPORT_MAX_PS = 1000.0
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

    core_n/core_wns are emitted only after the required searches finish without
    truncation, including any declared native pad inputs. A zero count/zero
    bound proves no internal hold miss; it does
    not claim the boundary WNS is zero. Typed summaries may carry that same
    measurement, but an old local SIGNED/port-only verdict is not evidence.
    """
    ff = (rec.get("corners") or {}).get("ff")
    if not isinstance(ff, dict):
        ff = rec.get("ff_census")     # Stored autopilot summaries carry the native census here.
    if isinstance(ff, dict):
        c = ff.get("std_min_start") or {}
        if not isinstance(c, dict):
            c = {}
        done = ff.get("done") is True and not ff.get("errors") and ff.get("rc", 0) == 0
        complete = done and c.get("err") == 0 and c.get("trunc") == 0
        w, n = _num(c.get("core_wns")), _num(c.get("core_n"))
        if "native_n" in c:
            native_n, native_w = _num(c["native_n"]), _num(c.get("native_wns"))
            complete = (complete and native_n is not None and n is not None and w is not None
                        and 0 <= native_n <= n and native_n.is_integer()
                        and native_w is not None and (native_w == 0 if native_n == 0 else w <= native_w < 0))
        source = "corners.ff.std_min_start.core_wns (complete internal census)"
        # Older native signers omitted the census when every STD min path met.
        # That complete, finite all-path minimum is a stronger internal bound.
        # Never replace a present/ambiguous core census or use another frame.
        if "core_wns" not in c and "core_n" not in c and "native_n" not in c:
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
    ff = (rec.get("corners") or {}).get("ff") or rec.get("ff_census") or {}
    census = ff.get("std_min_start") if isinstance(ff, dict) else None
    if isinstance(census, dict) and census.get("native_n", 0) != 0:
        return None, None    # The all-path WNS may belong to a native pad path.
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


CLOCK_EVIDENCE_SCHEMA = "opentallas.clock_period_evidence.v1"


def edge_clock_evidence(sdc, lint_context):
    """Source-bound period ratios for the PHY edge clocks generated by gen_phys."""
    text = sdc.decode()
    spec = json.loads(lint_context)
    root = re.search(r"^create_clock -name clk -period ([0-9.]+) \[get_ports \{[^}]+\}\]$", text, re.M)
    if not root or not re.search(r"^# GENERATED by tools/die_plan/gen[.]py phys: partition type ", text, re.M):
        return {}
    plan_ps = _num(spec.get("period_ps"))
    units_ps = _num(spec.get("time_unit_ps", 1))
    declared = _num(root[1])
    if plan_ps is None or units_ps is None or declared is None:
        return {}
    root_ps = declared * units_ps
    if not math.isclose(root_ps, plan_ps, rel_tol=0, abs_tol=1e-3):
        return {}
    entry = (r"^# PHY-edge clock \(plan clock[.]edge_clocks\): synchronous with clk, period ([0-9]+) x T\n"
             r"create_clock -name ([A-Za-z_][A-Za-z0-9_]*) -period ([0-9.]+) \[get_ports \2\]$")
    allowed = spec.get("port_period_mult")
    if not isinstance(allowed, dict):
        return {}
    ratios = {}
    for multiplier, name, declared_edge in re.findall(entry, text, re.M):
        ratio = int(multiplier)
        edge_ps = _num(declared_edge)
        if ratio > 1 and allowed.get(name) == ratio and edge_ps is not None and math.isclose(
                edge_ps * units_ps, root_ps * ratio, rel_tol=0, abs_tol=1e-3):
            ratios[name] = ratio
    if not ratios:
        return {}
    return dict(schema=CLOCK_EVIDENCE_SCHEMA, root="clk", root_ps=root_ps, edge_mult=ratios,
                sdc_sha256=hashlib.sha256(sdc).hexdigest(),
                lint_context_sha256=hashlib.sha256(lint_context).hexdigest())


def record_clock_period_ps(rec):
    """Largest measured primary clock, excluding only a proved synchronous edge ratio."""
    proof = rec.get("clock_period_evidence")
    if not isinstance(proof, dict) or proof.get("schema") != CLOCK_EVIDENCE_SCHEMA:
        proof = {}
    declared = _num(proof.get("root_ps"))
    ratios = proof.get("edge_mult")
    if not isinstance(ratios, dict):
        ratios = {}
    best = None
    for c in (rec.get("corners") or {}).values():
        if not isinstance(c, dict) or not isinstance(c.get("periods"), dict):
            continue
        periods = c["periods"]
        generated = c.get("generated_clocks")
        generated = set(generated) if isinstance(generated, list) else set()
        virtual = c.get("vclks")
        virtual = set(virtual) if isinstance(virtual, list) else set()
        peripheral = generated | virtual
        have_primary = any(name not in peripheral and (_num(v) or 0) > 0 for name, v in periods.items())
        root = _num(periods.get(proof.get("root")))
        bound = declared is not None and root is not None and math.isclose(root, declared, rel_tol=0, abs_tol=1e-3)
        for name, value in periods.items():
            v = _num(value)
            if v is None or v <= 0 or (have_primary and name in generated):
                continue
            m = ratios.get(name)
            if bound and type(m) is int and m > 1 and math.isclose(v, root * m, rel_tol=0, abs_tol=1e-3):
                continue
            if best is None or v > best:
                best = v
    return best


def signed_period_ps(rec):
    """the declared sign-off period of a period re-sign record (SIGN-PERIOD), else None"""
    return _num(rec.get("signed_period_ps"))


def period_problem(rec):
    """Return the setup gate failure reason if the timing period violates the 833 ps policy."""
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
    tol = setup_tolerance_ps(die)
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


def die_gate_thresholds(value=None):
    """die clock gate: minimal = routed related-pair setup >= 0 at the achieved period, hold >= 0 (one corner pair),
    kit window advisory; legacy = setup >= 0 at 833 ps, hold >= +10 ps, kit window blocking"""
    if is_minimal(value):
        return dict(setup_min_ps=0.0, hold_min_ps=0.0, period="achieved", kit_window_blocking=False)
    return dict(setup_min_ps=0.0, hold_min_ps=10.0, period=PERIOD_PS, kit_window_blocking=True)
