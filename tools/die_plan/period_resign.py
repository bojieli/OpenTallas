#!/usr/bin/env python3
"""period_resign.py -- REPORT the period a routed DB achieves (report only; never a sign-off path).

OWNER 11-20, superseding the 1000 ps part of decision (1): "Fix hold structurally, never by changing the clock. Fix setup misses with
more pipeline stages."  Nothing signs above 833 ps.  This tool measures, on the SAME routed DB, the smallest period <= 1000 ps at which
TT setup >= -42 ps, and writes it to <unit>/signoff_period/period_report.json (achievable_period_ps): it shows how far a type is from
833 so its setup miss can be fixed with pipeline stages.  It never writes a signoff.json; signoff_profile refuses any record timed
above 833 ps.  The text below describes the measurement (originally SIGN-PERIOD, lane SIGN-PROFILE-0400).

OWNER 11-20: a type signs at 833 ps where its build passes.  Otherwise the SAME routed DB is signed at a relaxed period, up to
1000 ps; the die then runs at the slowest signed type's period (up to -17 % tok/s accepted).  The gates are unchanged: detailed
route DRC 0, TT setup >= -42 ps AT THE SIGNED PERIOD, internal FF hold >= 0 (hold is re-checked at that period), bind + LATCHECK
(the kit was bound when it was generated).  No re-route, no re-synthesis: this is a re-STA of the existing routed DB.

How: the kit's golden SDC is copied with every create_clock period (and waveform) scaled to the trial period; IO budgets
(set_input_delay / set_output_delay), uncertainties and every other line stay as written (they are absolute die-level budgets).
signoff.py then times the routed DB at TT + FF exactly as the 833 sign-off did (same corners, margin policy, overlays).  The search
starts at the smallest period on the step grid the 833 TT WNS allows under the full-cycle model (P0 = 833 - 42 - WNS_833), and
moves up by the measured deficit (at least one step) until TT setup >= -42 ps or 1000 ps is passed.  Half-cycle paths gain only
half the period change, which is why every step is measured, never extrapolated.

Result, next to the 833 record in the same unit (so the counter's scan, the store ingest and the cleanup see the routed DB):
  <unit>/signoff_period/signoff.json   the record at the signed period: every check measured there, plus
                                        signed_period_ps, at_833 {path, sha256, verdict, tt / ff / drc} (the 833 result is kept),
                                        period_search [{period_ps, tt_wns_ps, ff_hold_wns_ps, drc, verdict}], period_rule
  <unit>/signoff_period/trial_p<P>/    each trial's signoff.py output; its record is renamed sta_p<P>.json (a trial is not a
                                        sign-off record: tools/die_plan/signoff_profile.period_problem refuses a >833 clock without
                                        signed_period_ps anyway)
  <unit>/signoff_period/period_resign.json   the search summary (verdict SIGNED_AT_PERIOD | SIGNED_AT_833 | NOT_ELIGIBLE | OVER_1000 | ERROR)

LAST RESORT (COORD 11-20 on the owner decision): sign at 833 wherever possible.  A DB is eligible only after its 833 late-stage
repair failed: an eco_loop.json (tools/die_plan/eco_loop.py) for that kit or ECO pass with a verdict other than PASS (EXHAUSTED,
NOT_NEAR_MISS, FAIL ...), found beside the record, in its kit's eco_*/ dirs, or named with --eco-evidence.  Without one the verdict is
ECO_FIRST.  --no-eco-evidence (lane / owner override, recorded in the record) skips it.  DIE-PERIOD.tsv names the types that force each
die's period so they can be targeted for a real 833 fix.

Hold: a record whose internal hold fails is not eligible here (verdict HOLD_FIRST): the late hold ECO and its residual pass
(eco_loop.py run --kit K) come first, on the 833 constraint, and this tool then runs on the ECO's signed-off pass dir record.

    period_resign.py check SIGNOFF.json                       eligibility + the first trial period (no STA)
    period_resign.py sdc IN.sdc PERIOD OUT.sdc                the period-scaled SDC only
    period_resign.py run --signoff SIGNOFF.json [--step 5] [--max 1000] [--out DIR] [--image IMG] [--dry]
Heavy (two OpenSTA corner sessions per trial): run through ot-run on a gen host, never on the hub or localhost.
"""
import argparse
import datetime
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import signoff_profile as SP  # noqa: E402

SCHEMA = "opentallas.period_resign.v1"
PERIOD_PS = SP.PERIOD_PS                      # 833
PERIOD_MAX_PS = SP.ACHIEVABLE_REPORT_MAX_PS   # 1000 (report range; signing stays at 833)
SETUP_TOL_PS = SP.SETUP_TOL_PS                # 42
STEP_PS = 5.0
RULE = ("SIGN-PERIOD (OWNER 2026-11-20 decision (1)): sign at 833 ps where the build passes, else the same routed DB at the smallest "
        "period <= 1000 ps where TT setup >= -42 ps, hold re-checked there; the die runs at the slowest signed type's period")

_NUM = r"[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?"


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def fmt(v):
    return ("%.4f" % v).rstrip("0").rstrip(".") if v != int(v) else "%.4f" % v


def _lines(text, k, names):
    for ln in text.splitlines(keepends=True):
        s = ln.lstrip()
        if s.startswith("create_clock"):
            ln = re.sub(r"(-period\s+)(" + _NUM + r")(?![\w.])", lambda m: m.group(1) + fmt(float(m.group(2)) * k), ln)
            ln = re.sub(r"(-waveform\s+)\{([^}]*)\}",
                        lambda m: m.group(1) + "{" + " ".join(fmt(float(x) * k) for x in re.findall(_NUM, m.group(2))) + "}", ln)
        else:
            m = re.match(r"^(\s*set\s+)(\w+)(\s+)(" + _NUM + r")(\s*(?:[;#].*)?)$", ln.rstrip("\n"))
            if m and m.group(2) in names:
                ln = m.group(1) + m.group(2) + m.group(3) + fmt(float(m.group(4)) * k) + m.group(5) + ("\n" if ln.endswith("\n") else "")
        yield ln


def _count(text, names):
    n = len(re.findall(r"^\s*create_clock\b[^\n]*-period\s+" + _NUM, text, re.M))
    n += sum(1 for ln in text.splitlines() if re.match(r"^\s*set\s+(\w+)\s+" + _NUM + r"\s*(?:[;#].*)?$", ln)
             and re.match(r"^\s*set\s+(\w+)", ln).group(1) in names)
    return n


def clock_vars(text):
    return {m.group(1) for m in re.finditer(r"^\s*create_clock\b[^\n]*?-period\s+\$\{?(\w+)\}?", text, re.M)}


def scaled_sdc(text, period, base=PERIOD_PS):
    """-> (scaled SDC text, number of periods scaled).  Every create_clock -period (a literal, or the `set VAR n` it names) is
    multiplied by period/base, its -waveform with it.  Nothing else changes (IO delays, uncertainty, exceptions)."""
    k = float(period) / float(base)
    names = clock_vars(text)
    return "".join(_lines(text, k, names)), _count(text, names)


scale_sdc = scaled_sdc


def on_grid(p, step=STEP_PS):
    return math.ceil(round(p / step, 6)) * step


def first_period(tt_wns, step=STEP_PS):
    """smallest grid period the 833 TT WNS allows under the full-cycle model: 833 - 42 - WNS (>= 833)"""
    if tt_wns is None:
        return None
    if tt_wns >= -SETUP_TOL_PS:
        return PERIOD_PS
    return on_grid(PERIOD_PS - SETUP_TOL_PS - tt_wns, step)


def next_period(p, tt_wns, step=STEP_PS):
    """the next trial after a miss at p: up by the measured deficit, at least one step"""
    deficit = -SETUP_TOL_PS - tt_wns
    return on_grid(p + max(step, deficit), step)


ECO_FAIL_VERDICTS = ("EXHAUSTED", "NOT_NEAR_MISS", "FAIL", "NOT_ELIGIBLE", "LEC_FAIL")


def eco_evidence(path833, rec, extra=()):
    """-> [(eco_loop.json path, verdict)] of failed 833 late-stage repairs of this DB's kit (any PASS means 833 is reachable: [])"""
    p = Path(path833).resolve()
    kit = Path((rec.get("inputs") or {}).get("kit") or unit_dir(p))
    cands = [Path(x) for x in extra]
    for d in [p.parent, p.parent.parent, p.parent.parent.parent, kit]:
        cands += [d / "eco_loop.json"] + sorted(d.glob("eco_*/eco_loop.json"))
    out, seen = [], set()
    for c in cands:
        try:
            if c in seen or not c.is_file():
                continue
            seen.add(c)
            v = json.loads(c.read_text()).get("verdict")
        except (OSError, ValueError):
            continue
        if v == "PASS":
            return []
        if v in ECO_FAIL_VERDICTS:
            out.append((str(c), v))
    return out


def check(rec):
    """-> dict(verdict ELIGIBLE | SIGNED_AT_833 | HOLD_FIRST | NOT_ELIGIBLE | OVER_1000, why, first_period_ps, tt, ff, drc)"""
    j = SP.judge(rec)
    drc, tt, ff = j["drc"], j["tt_wns_ps"], j["ff_hold_wns_ps"]
    base = dict(tt_wns_ps=tt, ff_hold_wns_ps=ff, drc=drc, gates=j["gates"])
    if SP.signed_period_ps(rec) is not None:
        return dict(base, verdict="NOT_ELIGIBLE", why="already a period record (signed_period_ps %g)" % SP.signed_period_ps(rec))
    if j["period_problem"]:
        return dict(base, verdict="NOT_ELIGIBLE", why="record timed above 833 ps: " + j["period_problem"])
    if j["gates"]["drc"] != "PASS":
        return dict(base, verdict="NOT_ELIGIBLE", why="DRC %s: a period re-STA does not change routing" % drc)
    if tt is None:
        return dict(base, verdict="NOT_ELIGIBLE", why="no TT setup measurement")
    if j["gates"]["hold_ff"] != "PASS":
        return dict(base, verdict="HOLD_FIRST", why="internal FF hold %s: late hold ECO + residual pass first (eco_loop.py run --kit K), "
                    "then this tool on the ECO pass record" % ff)
    if j["verdict"] == "SIGNED" and tt >= -SETUP_TOL_PS:
        return dict(base, verdict="SIGNED_AT_833", why="signs at 833 ps", first_period_ps=PERIOD_PS)
    p0 = first_period(tt)
    if p0 > PERIOD_MAX_PS:
        return dict(base, verdict="OVER_1000", why="TT WNS %+.1f ps at 833 needs >= %g ps under the full-cycle model" % (tt, p0),
                    first_period_ps=p0)
    return dict(base, verdict="ELIGIBLE", why="setup-only miss %+.1f ps at 833" % tt, first_period_ps=p0)


def unit_dir(signoff_path):
    """the unit of a record: <unit>/signoff/signoff.json -> <unit>; <unit>/signoff.json -> <unit>"""
    p = Path(signoff_path).resolve()
    return p.parent.parent if p.parent.name.startswith("signoff") else p.parent


def signoff_cmd(rec, sdc, out, image=None, tools=HERE):
    i = rec.get("inputs") or {}
    cmd = [sys.executable, "-I", str(Path(tools) / "signoff.py"), "run", "--base", i["base"], "--sdc", str(sdc), "--out", str(out),
           "--corners", "tt,ff", "--name", rec.get("name") or i.get("design") or Path(i["base"]).name]
    if i.get("kit"):
        cmd += ["--kit", i["kit"]]
    if image:
        cmd += ["--image", image]
    mp = (rec.get("policy") or {}).get("margin_policy")
    if isinstance(mp, str) and mp in ("legacy", "nominal"):
        cmd += ["--margin-policy", mp]
    return cmd


def trial_row(p, r):
    j = SP.judge(r)
    return dict(period_ps=p, tt_wns_ps=j["tt_wns_ps"], ff_hold_wns_ps=j["ff_hold_wns_ps"], drc=j["drc"],
                clock_period_ps=SP.record_clock_period_ps(r), gates=j["gates"])


def finalize(rec833, path833, trial, p, search, eco=None):
    """the period record: the trial record measured at p + signed_period_ps + at_833, judged by the profile"""
    j833 = SP.judge(rec833)
    out = dict(trial)
    out["signed_period_ps"] = float(p)
    out["at_833"] = dict(path=str(path833), sha256=sha256_file(path833) if Path(path833).exists() else None,
                         verdict=rec833.get("verdict"), generated=rec833.get("generated"), tt_wns_ps=j833["tt_wns_ps"],
                         ff_hold_wns_ps=j833["ff_hold_wns_ps"], drc=j833["drc"], gates=j833["gates"])
    out["period_search"] = search
    out["period_rule"] = RULE
    out["period_eco_evidence"] = eco
    out["generated_period_resign"] = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    return SP.apply(out)


def run(a, runner=None):
    path833 = Path(a.signoff).resolve()
    rec833 = json.loads(path833.read_text())
    c = check(rec833)
    if c["verdict"] == "ELIGIBLE":
        ev = eco_evidence(path833, rec833, getattr(a, "eco_evidence", None) or ())
        c["eco_evidence"] = ev
        if getattr(a, "no_eco_evidence", False):
            c["eco_evidence_override"] = True
        elif not ev:
            c.update(verdict="ECO_FIRST", why="no failed 833 late-stage repair (eco_loop.json) for this DB: run eco_loop.py run --kit K "
                     "first; the relaxed period is the last resort (COORD 11-20)")
    out = Path(a.out).resolve() if a.out else unit_dir(path833) / "signoff_period"
    summary = dict(schema=SCHEMA, signoff_833=str(path833), check=c, rule=RULE, out=str(out), search=[])
    if c["verdict"] != "ELIGIBLE":
        summary["verdict"] = c["verdict"]
        print(json.dumps(summary, indent=1))
        if not a.dry:
            out.mkdir(parents=True, exist_ok=True)
            (out / "period_resign.json").write_text(json.dumps(summary, indent=1) + "\n")
        return 0 if c["verdict"] in ("SIGNED_AT_833",) else 3
    sdc_src = Path((rec833.get("inputs") or {}).get("sdc") or "")
    if not sdc_src.is_file():
        summary.update(verdict="ERROR", why="golden SDC %s not readable" % sdc_src)
        print(json.dumps(summary, indent=1))
        return 2
    text = sdc_src.read_text()
    run_ = runner or (lambda cmd, log: subprocess.run(cmd, stdout=open(log, "w"), stderr=subprocess.STDOUT).returncode)
    p, step, pmax = c["first_period_ps"], float(a.step), float(a.max)
    while p <= pmax + 1e-6:
        td = out / ("trial_p%g" % p)
        sdc, n = scaled_sdc(text, p)
        if not n:
            summary.update(verdict="ERROR", why="no create_clock -period in %s" % sdc_src)
            break
        cmd = signoff_cmd(rec833, td / ("constraint_p%g.sdc" % p), td, image=a.image)
        if a.dry:
            print("trial %g ps: %d clock period(s) scaled; %s" % (p, n, " ".join(map(str, cmd))))
            summary["search"].append(dict(period_ps=p, dry=True))
            break
        td.mkdir(parents=True, exist_ok=True)
        (td / ("constraint_p%g.sdc" % p)).write_text(sdc)
        rc = run_(cmd, td / "signoff.log")
        rj = td / "signoff.json"
        if not rj.exists():
            summary["search"].append(dict(period_ps=p, rc=rc, error="no signoff.json"))
            summary.update(verdict="ERROR", why="signoff.py rc %s wrote no record at %g ps (log %s)" % (rc, p, td / "signoff.log"))
            break
        trial = json.loads(rj.read_text())
        os.replace(rj, td / ("sta_p%g.json" % p))      # a trial is not a sign-off record
        row = dict(trial_row(p, trial), rc=rc)
        summary["search"].append(row)
        print("trial %g ps: TT %s ps, FF hold %s ps, DRC %s" % (p, row["tt_wns_ps"], row["ff_hold_wns_ps"], row["drc"]), flush=True)
        if row["clock_period_ps"] is not None and abs(row["clock_period_ps"] - p) > SP.PERIOD_MATCH_PS:
            summary.update(verdict="ERROR", why="STA ran at %s ps, asked %g" % (row["clock_period_ps"], p))
            break
        if row["tt_wns_ps"] is None:
            summary.update(verdict="ERROR", why="no TT result at %g ps" % p)
            break
        if row["tt_wns_ps"] >= -SETUP_TOL_PS:
            fin = finalize(rec833, path833, trial, p, summary["search"], eco=dict(evidence=c.get("eco_evidence"), override=bool(c.get("eco_evidence_override"))))
            fin.pop("signed_period_ps", None)
            fin.update(achievable_period_ps=float(p), report_only=True, verdict="REPORT ONLY (not a sign-off: OWNER 11-20, nothing signs above 833)")
            (out / "period_report.json").write_text(json.dumps(fin, indent=1) + "\n")
            summary.update(verdict="ACHIEVABLE_AT_PERIOD", achievable_period_ps=p, record=str(out / "period_report.json"))
            break
        p = next_period(p, row["tt_wns_ps"], step)
    else:
        summary.update(verdict="OVER_1000", why="TT setup < -42 ps at every trial up to %g ps" % pmax)
    if not a.dry:
        out.mkdir(parents=True, exist_ok=True)
        (out / "period_resign.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps({k: summary.get(k) for k in ("verdict", "achievable_period_ps", "record", "why")}))
    return 0 if summary.get("verdict") == "ACHIEVABLE_AT_PERIOD" else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("signoff")
    s = sub.add_parser("sdc")
    s.add_argument("sdc")
    s.add_argument("period", type=float)
    s.add_argument("out")
    r = sub.add_parser("run")
    r.add_argument("--signoff", required=True)
    r.add_argument("--out")
    r.add_argument("--step", type=float, default=STEP_PS)
    r.add_argument("--max", type=float, default=PERIOD_MAX_PS)
    r.add_argument("--image")
    r.add_argument("--dry", action="store_true")
    r.add_argument("--eco-evidence", action="append", help="eco_loop.json of the failed 833 repair (else searched beside the record)")
    r.add_argument("--no-eco-evidence", action="store_true", help="override: run without a failed 833 repair (recorded)")
    a = ap.parse_args(argv)
    if a.cmd == "check":
        print(json.dumps(check(json.loads(Path(a.signoff).read_text())), indent=1))
        return 0
    if a.cmd == "sdc":
        t, n = scaled_sdc(Path(a.sdc).read_text(), a.period)
        Path(a.out).write_text(t)
        print("%d clock period(s) scaled to %g ps" % (n, a.period))
        return 0 if n else 1
    if a.max > PERIOD_MAX_PS:
        raise SystemExit("--max above %g ps is not allowed (OWNER 11-20)" % PERIOD_MAX_PS)
    return run(a)


if __name__ == "__main__":
    sys.exit(main())
