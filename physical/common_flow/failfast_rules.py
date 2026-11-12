#!/usr/bin/env python3
"""failfast_rules.py -- progress-based stop rules for a kit's route stages (lane FAILFAST-1, 2026-11-11).

Why: a successful type build takes ~10 h; the 24-49 h tail is a congested build looping (GRT "extra iterations to remove
congestion" 3-15 rounds, GRT-0273 "Disabled NDR"; DRT at pass 27; hold repair that hits the buffer cap and then routes anyway).
The 2-h hung-job watchdog never fires on them because the log keeps growing.  Each rule below stops on PROGRESS, not on
silence.  Pure functions here; `judge` (CLI) is what grt183_make.sh polls every OT_GRT_STALL_POLL seconds inside the kit.
Stdlib only, no repo imports: the file is copied into every kit as /work/failfast_rules.py (core_flow.stage_grt183) and
sent verbatim to a host by tools/autopilot/failfast_scan.py (read-only dry run on live jobs).

Rules (config key, default; env wins over `export KEY = value` in the kit's config.mk; OT_FAILFAST=0 turns all off):
  (a) GRT_NO_PROGRESS   OT_FF_GRT=1  OT_FF_GRT_MAX=1000  OT_FF_GRT_MIN_DROP_PCT=10  OT_FF_GRT_ROUNDS=2  OT_FF_GRT_ROUND_ITERS=30
      After OT_FF_GRT_ROUNDS x OT_FF_GRT_ROUND_ITERS (60) extra iterations: stop when the latest congestion-<N>.rpt total is
      ABOVE OT_FF_GRT_MAX and fell by less than OT_FF_GRT_MIN_DROP_PCT % against the report one round (30 iterations) older.
      Both conditions must hold ("above the ceiling AND not falling"): a run that is high but falling >= 10 % per round is
      converging and keeps going; a run at or below the ceiling is left to DRT (KW-FIX-8).  The OpenROAD log prints no overflow
      count, only the iteration counter, so the totals come from congestion-<N>.rpt (written every 5 iterations, overwritten in
      each round): the watcher records every new report with its cumulative iteration, which is the history.
  (b) DRT_NO_PROGRESS   OT_FF_DRT=1  OT_FF_DRT_ITER=20  OT_FF_DRT_MAX_VIOL=10000  OT_FF_DRT_MIN_DROP_PCT=5  OT_FF_DRT_WINDOW=3
      From completed iteration OT_FF_DRT_ITER: stop when the violation count is above OT_FF_DRT_MAX_VIOL and over the last
      OT_FF_DRT_WINDOW iterations it fell by less than OT_FF_DRT_MIN_DROP_PCT % per iteration (compound: v_last >
      v_before * (1 - pct/100) ** window).
  (c) HOLD_STRUCTURAL   OT_FF_HOLD=1  OT_FF_HOLD_CAPS=2
      Hold repair that reports the buffer cap (RSZ-0060) OT_FF_HOLD_CAPS times in this run's CTS + GRT logs, or an
      OT_HOLD_STALL NEEDS_RTL line: the run ends as hold-structural instead of continuing to route.  A kit with
      'export OT_HOLD_STRUCTURAL_ADVISORY = 1' is exempt (owner: advisory kits keep going).
Classes (the first token of the stop line, read by tools/autopilot/autopilot.py):
  OT_GRT_NO_PROGRESS stage=grt ...  carries the last overflow per layer (H / V split and every named layer of the report)
  OT_DRT_NO_PROGRESS stage=route ...
  OT_HOLD_STRUCTURAL stage=cts|grt failfast ...
"""
import collections
import glob
import json
import os
import re
import sys
import time

DEFAULTS = {
    "OT_FAILFAST": 1,
    "OT_FF_GRT": 1, "OT_FF_GRT_MAX": 1000, "OT_FF_GRT_MIN_DROP_PCT": 10, "OT_FF_GRT_ROUNDS": 2, "OT_FF_GRT_ROUND_ITERS": 30,
    "OT_FF_DRT": 1, "OT_FF_DRT_ITER": 20, "OT_FF_DRT_MAX_VIOL": 10000, "OT_FF_DRT_MIN_DROP_PCT": 5, "OT_FF_DRT_WINDOW": 3,
    "OT_FF_HOLD": 1, "OT_FF_HOLD_CAPS": 2,
}

ITER_RE = re.compile(r"\[INFO GRT-0102\] Start extra iteration (\d+)/(\d+)")
NDR_RE = re.compile(r"\[WARNING GRT-0273\] Disabled NDR")
DRT_START_RE = re.compile(r"\[INFO DRT-0195\] Start (\d+)\w* (?:(stubborn tiles) )?(?:optimization )?iteration")
DRT_VIOL_RE = re.compile(r"\[INFO DRT-0199\]\s+Number of violations = (\d+)")
CAP_RE = re.compile(r"buffer cap .*reached \(RSZ-0060\)|OT_HOLD_STOP cap of \d+ buffers reached|OT_HOLD_GUARD_GRT chunk \d+: .*cap")
STALL_RE = re.compile(r"OT_HOLD_STALL NEEDS_RTL[^\n]*")
CONG_RE = re.compile(r"congestion:(\d+)")
LAYER_RE = re.compile(r"\bon Layer (\S+)")
FINAL_RE = re.compile(r"^(M\d+|V\d+|Total)\s+\d+\s+\d+\s+[\d.]+%\s+(\d+)\s*/\s*(\d+)\s*/\s*(\d+)\s*$")


def config_values(env=None, config_text=""):
    """DEFAULTS overridden by `export KEY = value` lines of the kit config.mk, then by the environment"""
    env = os.environ if env is None else env
    out = dict(DEFAULTS)
    for k in out:
        ms = re.findall(r"(?m)^export %s[ \t]*=[ \t]*(-?\d+)[ \t]*$" % re.escape(k), config_text or "")
        v = ms[-1] if ms else None
        if k in env and re.fullmatch(r"-?\d+", str(env[k]).strip()):
            v = env[k].strip()
        if v is not None:
            out[k] = int(v)
    return out


def advisory(config_text):
    return bool(re.search(r"(?m)^export OT_HOLD_STRUCTURAL_ADVISORY[ \t]*=[ \t]*1[ \t]*$", config_text or ""))


# ------------------------------------------------------------------------------------------------ log scan (one pass)
def scan_lines(lines):
    """-> dict: iters [(i, n)] of GRT-0102 lines, ndr count, drt [(label, violations)] of completed DRT iterations,
    caps (hold buffer-cap hits), stall (first OT_HOLD_STALL line), final {layer: (H, V, total)} of the last GRT-0096 table"""
    r = {"iters": [], "ndr": 0, "drt": [], "caps": 0, "stall": None, "final": {}}
    open_drt = None
    in_final = False
    for ln in lines:
        if "GRT-0102" in ln:
            m = ITER_RE.search(ln)
            if m:
                r["iters"].append((int(m[1]), int(m[2])))
        elif "GRT-0273" in ln:
            if NDR_RE.search(ln):
                r["ndr"] += 1
        elif "DRT-0195" in ln:
            m = DRT_START_RE.search(ln)
            open_drt = (("S" if m[2] else "") + m[1]) if m else None
        elif "DRT-0199" in ln:
            m = DRT_VIOL_RE.search(ln)
            if m and open_drt is not None:
                r["drt"].append((open_drt, int(m[1])))
                open_drt = None
        elif "RSZ-0060" in ln or "OT_HOLD_STOP cap" in ln or "OT_HOLD_GUARD_GRT chunk" in ln:
            if CAP_RE.search(ln):
                r["caps"] += 1
        elif "OT_HOLD_STALL" in ln:
            m = STALL_RE.search(ln)
            if m and r["stall"] is None:
                r["stall"] = m[0][:300]
        elif "GRT-0096" in ln:
            in_final = True
            r["final"] = {}
        elif in_final:
            m = FINAL_RE.match(ln.strip())
            if m:
                r["final"][m[1]] = (int(m[2]), int(m[3]), int(m[4]))
                if m[1] == "Total":
                    in_final = False
    return r


def iteration_state(iters):
    """[(i, n)] GRT-0102 lines -> (cum, cur, round_len, rounds): total iterations started, index in the current round, length of
    the previous round (its last index), completed rounds.  A new round starts when the index does not increase (OpenROAD
    restarts at 1/N after every GRT-0273 NDR relaxation; DISK-1111: rounds are 15-30 iterations long)."""
    cum, cur, prev_len, rounds = 0, 0, 0, 0
    for i, _n in iters:
        if cur and i <= cur:
            prev_len, rounds = cur, rounds + 1
        cur = i
        cum += 1
    return cum, cur, prev_len, rounds


# ------------------------------------------------------------------------------------------------ (a) GRT
def parse_report(text):
    """congestion-<N>.rpt text -> {total, H, V, layers {name: overflow}}"""
    tot, hv, layers = 0, collections.Counter(), collections.Counter()
    kind = None
    cur = 0
    for ln in text.splitlines():
        if ln.startswith("violation type:"):
            kind = "H" if "Horizontal" in ln else "V" if "Vertical" in ln else "?"
        else:
            m = CONG_RE.search(ln)
            if m:
                cur = int(m[1])
                tot += cur
                hv[kind] += cur
                continue
            m = LAYER_RE.search(ln)
            if m and m[1] != "-":
                layers[m[1]] += cur
                cur = 0
    return {"total": tot, "H": hv["H"], "V": hv["V"], "layers": dict(layers)}


def report_cum(n, cum_now, cur, prev_len, round_len=30):
    """cumulative iteration at which a report of iteration index n was written, seen when the log is at (cum_now, cur)"""
    if cur >= n:
        return cum_now - (cur - n)
    return cum_now - cur - ((prev_len or round_len) - n)


def grt_decide(series, total_iters, c):
    """series [{cum, n, total, H, V, layers, mtime}] oldest first (one entry per report write); total_iters = cumulative
    iterations started.  -> None or the stop record.  See the module doc, rule (a)."""
    if not c["OT_FF_GRT"] or not series:
        return None
    rnd = c["OT_FF_GRT_ROUND_ITERS"]
    if total_iters < c["OT_FF_GRT_ROUNDS"] * rnd:
        return None
    last = series[-1]
    if last["total"] <= c["OT_FF_GRT_MAX"]:
        return None
    older = [s for s in series if s["cum"] <= last["cum"] - rnd]
    if not older:
        return None
    ref = older[-1]
    if ref["total"] <= 0:
        return None
    fall = 100.0 * (ref["total"] - last["total"]) / ref["total"]
    if fall >= c["OT_FF_GRT_MIN_DROP_PCT"]:
        return None
    return {"rule": "GRT_NO_PROGRESS", "iterations": total_iters, "last": last, "ref": ref, "fall_pct": round(fall, 1),
            "max": c["OT_FF_GRT_MAX"], "min_drop_pct": c["OT_FF_GRT_MIN_DROP_PCT"]}


def grt_line(d, rounds=None, ndr=None, stamp=True):
    last, ref = d["last"], d["ref"]
    lay = " ".join("%s=%d" % (k, v) for k, v in sorted(last.get("layers", {}).items())) or "unnamed(mid-route report)"
    return ("OT_GRT_NO_PROGRESS stage=grt class=GRT_NO_PROGRESS: after %d extra iterations%s total overflow %d (congestion-%d) "
            "> %d and fell %.1f%% (< %d%%) over the last round (%d at iteration %d -> %d at iteration %d); last overflow H %d / V %d, "
            "per layer %s%s; stopping the stage (FAILFAST-1)%s"
            % (d["iterations"], "" if rounds is None else " in %d rounds" % rounds, last["total"], last["n"], d["max"],
               d["fall_pct"], d["min_drop_pct"], ref["total"], ref["cum"], last["total"], last["cum"], last["H"], last["V"], lay,
               "" if ndr is None else ", %d NDR relaxations" % ndr, time.strftime(" %Y-%m-%d %H:%M:%S", time.gmtime()) if stamp else ""))


# ------------------------------------------------------------------------------------------------ (b) DRT
def drt_decide(series, c):
    """series [(label, violations)] of completed iterations -> None or the stop record"""
    if not c["OT_FF_DRT"]:
        return None
    w = c["OT_FF_DRT_WINDOW"]
    if len(series) < max(c["OT_FF_DRT_ITER"], w + 1):
        return None
    last, before = series[-1][1], series[-1 - w][1]
    if last <= c["OT_FF_DRT_MAX_VIOL"] or before <= 0:
        return None
    if last <= before * (1 - c["OT_FF_DRT_MIN_DROP_PCT"] / 100.0) ** w:
        return None
    return {"rule": "DRT_NO_PROGRESS", "iteration": len(series), "violations": last, "before": before, "window": w,
            "fall_pct": round(100.0 * (before - last) / before, 1), "max": c["OT_FF_DRT_MAX_VIOL"],
            "min_drop_pct": c["OT_FF_DRT_MIN_DROP_PCT"], "tail": [v for _l, v in series[-(w + 1):]]}


def drt_line(d, stamp=True):
    return ("OT_DRT_NO_PROGRESS stage=route class=DRT_NO_PROGRESS: iteration %d has %d violations > %d and the last %d iterations fell "
            "%.1f%% in all (< %g%% per iteration): %s; stopping the stage (FAILFAST-1)%s"
            % (d["iteration"], d["violations"], d["max"], d["window"], d["fall_pct"], d["min_drop_pct"],
               " -> ".join(str(v) for v in d["tail"]), time.strftime(" %Y-%m-%d %H:%M:%S", time.gmtime()) if stamp else ""))


# ------------------------------------------------------------------------------------------------ (c) hold
def hold_decide(caps, stall, c, config_text=""):
    if not c["OT_FF_HOLD"] or advisory(config_text):
        return None
    if stall:
        return {"rule": "HOLD_STRUCTURAL", "why": "OT_HOLD_STALL: " + stall[:200]}
    if caps >= c["OT_FF_HOLD_CAPS"]:
        return {"rule": "HOLD_STRUCTURAL", "why": "hold repair hit the buffer cap (RSZ-0060) %d times (limit %d)" % (caps, c["OT_FF_HOLD_CAPS"])}
    return None


def hold_line(d, stage, stamp=True):
    return ("OT_HOLD_STRUCTURAL stage=%s failfast class=HOLD_STRUCTURAL: %s; the build ends here instead of continuing to route "
            "(FAILFAST-1; revise plan/RTL/boundary)%s" % (stage, d["why"], time.strftime(" %Y-%m-%d %H:%M:%S", time.gmtime()) if stamp else ""))


# ------------------------------------------------------------------------------------------------ the kit-side judge
def _dirs(work):
    lg = sorted(glob.glob(os.path.join(work, "run", "logs", "asap7", "*", "base")))
    rp = sorted(glob.glob(os.path.join(work, "run", "reports", "asap7", "*", "base")))
    return (lg[0] if lg else None), (rp[0] if rp else None)


def _fresh(paths, t0):
    out = []
    for p in paths:
        try:
            if os.path.getmtime(p) >= t0:
                out.append(p)
        except OSError:
            pass
    return out


def _read_lines(path):
    try:
        with open(path, errors="replace") as f:
            for ln in f:
                yield ln
    except OSError:
        return


def reports_now(rp, t0, settle_s=20, now=None):
    """[(n, mtime, path)] of this run's complete congestion reports (older than settle_s)"""
    now = time.time() if now is None else now
    out = []
    for p in glob.glob(os.path.join(rp or "/nonexistent", "congestion-[0-9]*.rpt")):
        m = re.search(r"congestion-(\d+)\.rpt$", p)
        try:
            mt = os.path.getmtime(p)
        except OSError:
            continue
        if m and mt >= t0 and now - mt >= settle_s:
            out.append((int(m[1]), mt, p))
    return sorted(out, key=lambda x: (x[1], x[0]))


def judge(work, t0, state_path=None, env=None, settle_s=None, now=None):
    """-> list of stop lines (empty = keep going).  Reads this run's logs only (mtime >= t0).  State (the report history of the
    GRT rule) is kept in state_path as JSON; without it the history starts empty on every call."""
    config_text = ""
    try:
        config_text = open(os.path.join(work, "config.mk"), errors="replace").read()
    except OSError:
        pass
    c = config_values(env, config_text)
    if not c["OT_FAILFAST"]:
        return []
    if settle_s is None:      # same knob as the GRT-EARLY report settle in grt183_make.sh
        e = os.environ if env is None else env
        settle_s = int(e.get("OT_GRT_EARLY_SETTLE_S", 20)) if str(e.get("OT_GRT_EARLY_SETTLE_S", "20")).isdigit() else 20
    lg, rp = _dirs(work)
    if not lg:
        return []
    logs = {os.path.basename(p): p for p in _fresh(glob.glob(os.path.join(lg, "*.log")), t0)}
    cts = [p for n, p in logs.items() if n.startswith("4_1_cts")]
    grt = [p for n, p in logs.items() if n.startswith("5_1_grt")]
    drt = [p for n, p in logs.items() if n.startswith("5_2_route")]
    # (c) hold: CTS + GRT logs of this run
    caps, stall, stage = 0, None, "cts"
    for p in sorted(cts + grt):
        s = scan_lines(_read_lines(p))
        caps += s["caps"]
        if s["caps"] and p in grt:
            stage = "grt"
        if s["stall"] and not stall:
            stall, stage = s["stall"], "cts" if p in cts else "grt"
    d = hold_decide(caps, stall, c, config_text)
    if d:
        return [hold_line(d, stage)]
    # (b) DRT
    for p in sorted(drt):
        s = scan_lines(_read_lines(p))
        d = drt_decide(s["drt"], c)
        if d:
            return [drt_line(d)]
    # (a) GRT
    tmp = [p for p in grt if os.path.basename(p).startswith("5_1_grt.tmp")] or grt
    if not tmp or not c["OT_FF_GRT"]:
        return []
    s = scan_lines(_read_lines(sorted(tmp)[-1]))
    cum, cur, prev_len, rounds = iteration_state(s["iters"])
    state = {"series": []}
    if state_path:
        try:
            state = json.load(open(state_path))
        except (OSError, ValueError):
            pass
    seen = {(x["n"], x["mtime"]) for x in state["series"]}
    changed = False
    for n, mt, p in reports_now(rp, t0, settle_s, now):
        if (n, mt) in seen:
            continue
        try:
            rep = parse_report(open(p, errors="replace").read())
        except OSError:
            continue
        state["series"].append(dict(rep, n=n, mtime=mt, cum=report_cum(n, cum, cur, prev_len, c["OT_FF_GRT_ROUND_ITERS"])))
        changed = True
    state["series"].sort(key=lambda x: (x["mtime"], x["cum"]))
    if state_path and changed:
        tmpf = state_path + ".tmp.%d" % os.getpid()
        try:
            with open(tmpf, "w") as f:
                json.dump(state, f)
            os.replace(tmpf, state_path)
        except OSError:
            pass
    d = grt_decide(state["series"], cum, c)
    if d:
        return [grt_line(d, rounds=rounds + (1 if cur else 0), ndr=s["ndr"])]
    return []


def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    if len(a) >= 3 and a[0] == "judge":
        # failfast_rules.py judge WORK T0_EPOCH [STATE_FILE]
        for ln in judge(a[1], float(a[2]), a[3] if len(a) > 3 else None):
            print(ln)
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
