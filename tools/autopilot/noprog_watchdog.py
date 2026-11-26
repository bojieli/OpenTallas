#!/usr/bin/env python3
"""noprog_watchdog.py -- NO-PROGRESS watchdog for running openroad / yosys / LEC containers (NOPROG-WATCHDOG, OWNER 2026-11-14:
"we need a no progress watchdog rather than a time limit").

Builds have no time limits.  A job that is still improving runs forever; a job whose progress metric has not improved by at
least MIN_IMPROVE (2 %) from its best over a WINDOW (6 h) is NO-PROGRESS.  Elapsed time alone is never a reason.

The same file runs on every build host (`tick`, a systemd user timer every 15 min):
  scan  one host: containers -> scope (ot-heavy oth-*.scope) -> kit dir -> the running stage's log -> metric series -> verdict.
        Writes ~/.local/state/noprog/report.json.  --act also cancels (see PASSES below).
  hub   on the hub only (has ~/coord): pushes the policy files to every host, fetches every host's report.json, writes the table
        lanes/NOPROG-TABLE.md, appends actions to lanes/NOPROG-ACTIONS.tsv (lanes/NOPROG.tsv is the advisory per-job table of noprog_stage.py), posts the table (first pass and on changes) and NEEDS-LANE
        lines to lanes/COORD-REVIEW-QUEUE.md, all through ~/coord/bin/coord-commit.sh.
  tick  scan --act, then hub when this host is the hub.

Progress metric per stage (all read from the stage's *.tmp.log under the kit's run/logs, or the kit's own step log):
  gpl    global place   Overflow column of the `iter | overflow | HPWL` table
  drt    detailed route `[INFO DRT-0199] Number of violations = N` after each optimization iteration
  grt    global route   repair tables inside 5_1_grt.tmp.log (Remaining / Viol / Violations / |TNS|), the GRT-0096 final
                        congestion Total.  The extra-iteration loop (GRT-0101/0102) prints NO overflow in this OpenROAD, so
                        while it loops the metric is "any new non-iteration line"; a loop that adds only iteration lines for
                        a whole window is NO-PROGRESS.
  other  cts / floorplan / lec / yosys / hold gate ... : growth of the log (noise lines excluded) plus CPU.
A log without timestamps gets line times by interpolation between the stage start (log birth, never before the container start),
the samples this tool took on earlier passes, and the log's mtime.  A verdict needs >= WINDOW of evidence.

PASSES: a job is cancelled only after an earlier pass listed it in a report-mode table (state `reported`), so every cancel
was on a posted table first.  HBM (parked) skips the window but not that rule; a kit whose plan is not the adopted one is NEVER a reason (FLOW-FIX-2045, OWNER: a type counts once signed on any plan; old-plan kits are never cancelled for a newer plan): only real no-progress cancels.  Excluded: --priority plan
jobs (bind / LATCHECK / G0 / die-proto / chain), and anything matched by a NOPROG-KEEP.tsv line.  The kit dir is never cleaned.

Cancel = `ot-heavy-stop --match <kit dir>` (exact `--unit` when the match would hit another scope), nothing else is killed.
"""
import argparse, glob, json, os, re, shlex, shutil, socket, subprocess, sys, time

WINDOW_S = 6 * 3600
# PREGRT-HOLD-WATCHDOG-1123 (COORD 17:25, FABLE flow review; owner 12.22 2-h hung-job watchdog): kit steps that are bounded
# repairs get a 2 h no-progress window, and a metric that reached 0 counts as progress only while the step still writes
# (five KV kits sat in pregrt_ff_hold 11-13 h after repair_TNS reached 0: "reached 0" kept them PROGRESS forever).
# NOPROG-TNS0-1124 overrides the zero half of that rule for TNS metrics: TNS >= 0 is converged, never NO-PROGRESS (tns_converged);
# the 2 h window still applies to a non-zero flat TNS.
STEP_WINDOW_S = {"pregrt_ff_hold": 2 * 3600}


def step_window(log):
    """(window_s, zero_needs_growth) for the running step's log"""
    n = os.path.basename(log or "")
    for k, w in STEP_WINDOW_S.items():
        if n.startswith(k):
            return w, True
    return WINDOW_S, False
MIN_IMPROVE = 0.02
HUB = os.environ.get("OT_HUB_NAME", "intel2")
HOSTS = ["intel1", "intel2", "epyc2", "epyc7", "epyc8", "epyc9", "epyc10", "epyc11", "epyc12"]
STATE_DIR = os.path.expanduser(os.environ.get("NOPROG_DIR", "~/.local/state/noprog"))
COORD = os.path.expanduser(os.environ.get("OT_COORD_DIR", "~/coord"))
MAX_SAMPLES = 80
LEC_MAX_S = 24 * 3600
MIN_REPORT_AGE_S = 1000        # a job is cancelled only when an earlier pass (>= 2 ticks ago) listed it, so the hub has posted it

# ---------------------------------------------------------------- parsing (pure)
GPL_ROW = re.compile(r"^\s*(\d+) \|\s+([0-9]+\.[0-9]+) \|\s+([0-9.]+e[+-]?\d+) \|")
GPL_ROW_OLD = re.compile(r"Iter:\s*(\d+)\s+overflow:\s*([0-9.]+)", re.I)
TABLE_HDR = re.compile(r"^\s*(Iteration|Iter)\s*\|(.*)$")
TABLE_ROW = re.compile(r"^\s*(\d+|final)\*?\s*\|(.*)$")       # repair_timing rows carry a trailing "*" ("3154* |")
DRT_ITER = re.compile(r"DRT-0199\]\s+Number of violations = (\d+)")
DRT_PCT = re.compile(r"Completing \d+% with (\d+) violations")
GRT_TOTAL = re.compile(r"^Total\s+\d+\s+\d+\s+[\d.]+%\s+(\d+)\s*/\s*(\d+)\s*/\s*(\d+)")
# MEM-RECLAIM-2200 (FABLE-FLOW-2200 class 10): the STAGE-CAP keep/skip line (stage_odb_cap.log, every few minutes, 148 jobs) and heartbeat lines are the
# harness talking, not the flow: they are never progress (the watchdog called every such job PROGRESSING, 0.0 h since the last event)
NOISE = re.compile(r"GRT-0102|GRT-0273|RSZ-0104|STAGE-CAP|WATCHER (?:replaced|would)|heartbeat|^\s*$", re.I)
NOT_FLOW_LOG = re.compile(r"stage_odb_cap|heartbeat", re.I)     # whole log files that only carry such lines
METRIC_COLS = ["Remaining", "Violations", "Viol", "TNS"]     # priority; TNS is taken as |TNS|
GRT_HOLD_CHUNK = re.compile(r"^OT_HOLD_GUARD_GRT chunk (\d+): hold ws .*? tns (-?\d+(?:\.\d+)?) viol \d+,")



def num(s):
    s = s.strip().replace("%", "").replace("+", "")
    try:
        return float(s)
    except ValueError:
        return None


def parse_tables(lines):
    """-> list of {'cols': [...], 'rows': [(line_idx, [values])], 'final': bool}"""
    out, cur = [], None
    for i, ln in enumerate(lines):
        if TABLE_HDR.match(ln):
            cur = {"cols": [c.strip() for c in ln.split("|")], "rows": [], "final": False}
            out.append(cur)
            continue
        if cur is None:
            continue
        m = TABLE_ROW.match(ln)
        if m:
            if m.group(1) == "final":
                cur["final"] = True
                continue
            cur["rows"].append((i, [num(x) for x in ln.split("|")]))
    return out


def table_series(tbl, kind=None):
    """the lower-is-better value column of one repair table -> (name, [(line_idx, value)]) or None.
    FLOW-HEALTH-1 11-15 (FABLE-PD-KV-1450 fix 7): in a global-route log (5_1_grt) a table whose value column is a bare `Violations`
    is the detailed-placement legalizer's, not global-route progress: it is not the metric there (Remaining / Viol / TNS of the resizer
    repair tables still are)."""
    for want in METRIC_COLS:
        if kind == "grt" and want == "Violations":
            continue
        for k, c in enumerate(tbl["cols"]):
            if c == want or (want == "TNS" and c in ("TNS", "StTNS")):
                ser = []
                for i, vals in tbl["rows"]:
                    if k < len(vals) and vals[k] is not None:
                        ser.append((i, abs(vals[k]) if want == "TNS" else vals[k]))
                if ser:
                    return want, ser
    return None


def stage_kind(logname):
    n = os.path.basename(logname)
    if "place_gp" in n:
        return "gpl"
    if "5_2_route" in n:
        return "drt"
    if "5_1_grt" in n or n == "fabric.log":
        return "grt"
    if "lec" in n.lower():
        return "lec"
    if "yosys" in n or n in ("run_finish.log", "1_synth.log") or "synth" in n:
        return "yosys"
    return "other"


def extract(kind, text):
    """-> dict(name, series=[(line_idx, value)] lower is better or [], growth_idx = index of the last meaningful line, n = lines)"""
    lines = text.splitlines()
    n = len(lines)
    meaningful = [i for i, ln in enumerate(lines) if not NOISE.search(ln)]
    res = {"name": None, "series": [], "growth_idx": meaningful[-1] if meaningful else -1, "n": n}
    if kind == "gpl":
        ser = []
        for i, ln in enumerate(lines):
            m = GPL_ROW.match(ln) or GPL_ROW_OLD.search(ln)
            if m:
                ser.append((i, float(m.group(2))))
        res["name"], res["series"] = "overflow", ser
        return res
    if kind == "drt":
        ser = [(i, float(m.group(1))) for i, ln in enumerate(lines) for m in [DRT_ITER.search(ln)] if m]
        res["name"], res["series"] = "drt_violations", ser
        pct = [i for i, ln in enumerate(lines) if DRT_PCT.search(ln)]
        if pct:
            res["growth_idx"] = pct[-1]
        # FLOW-OPS-1000 (FABLE-PD-S81-1100 #2: col_h9_r0 rep 0d6487d7a8c6 was cancelled at 60,258 violations, 70 % through iteration 1,
        # down from the iteration-0 total 151,954, because only DRT-0199 totals were read): the `Completing N% with V violations` counts
        # of the ACTIVE iteration (after the last completed total) are kept, so judge() can see a count still falling inside it
        last = ser[-1][0] if ser else None
        if last is not None:
            res["active"] = [(i, float(DRT_PCT.search(lines[i]).group(1))) for i in pct if i > last]
        return res
    if kind in ("grt", "other"):
        tbls = parse_tables(lines)
        act = tbls[-1] if tbls and not tbls[-1]["final"] else None
        if act is not None:
            ts = table_series(act, kind)
            if ts:
                res["name"], res["series"] = "repair_" + ts[0], ts[1]
                return res
        if kind == "grt":
            # global_route's own news: GRT-0xxx lines (iteration / overflow / incremental GRT); a legalizer table filling the log is not growth
            grt_events = [i for i, ln in enumerate(lines) if re.search(r"\bGRT-0\d+\]", ln)]
            g = [i for i in grt_events if not NOISE.search(lines[i])]
            if g:
                res["growth_idx"] = g[-1]
            # Between repair tables, retain only completed hold chunks after the last routing event.
            # Starting a new chunk sequence resets the baseline.
            completed = []
            last_chunk = 0
            for i in range(grt_events[-1] + 1 if grt_events else 0, n):
                m = GRT_HOLD_CHUNK.match(lines[i])
                if not m:
                    continue
                chunk = int(m[1])
                if chunk <= last_chunk:
                    completed = []
                completed.append((i, abs(float(m[2]))))
                last_chunk = chunk
            if completed:
                res["growth_idx"] = completed[-1][0]
                if len(completed) > 1:
                    res["name"], res["series"] = "grt_hold_TNS", completed
                return res
        tot = [(i, float(m.group(3))) for i, ln in enumerate(lines) for m in [GRT_TOTAL.match(ln)] if m]
        # GRT-0096 final congestion total (one per global_route call): the metric only while it is the stage's last news
        if tot and kind == "grt" and (not meaningful or tot[-1][0] >= meaningful[-1] - 40):
            res["name"], res["series"] = "grt_overflow", tot
    return res


def judge_activity(last_t, start_t, now, what, window=WINDOW_S):
    """no metric at all (LEC): the newest write of the job's files must be newer than `window`"""
    age, span = now - last_t, now - start_t
    detail = f"{what} last write {age / 3600:.1f} h ago"
    if span < window:
        return "YOUNG", f"evidence {span / 3600:.1f} h < {window / 3600:g} h", detail
    if age >= window:
        return "NO-PROGRESS", f"no new {what} file/log write for {age / 3600:.1f} h", detail
    return "PROGRESS", f"{what} still writing", detail


def route_done(work):
    """the kit's routed database exists (5_route / 5_2_route / 6_final odb under run/results)"""
    return bool(work) and any(glob.glob(f"{work}/run/results/*/*/*/{n}") for n in ("5_route.odb", "5_2_route.odb", "6_final.odb"))


def lec_activity(work, started):
    """newest mtime of the LEC work files (lec/hypN.aig, gold.ys.log ...) written since the container started"""
    best = 0.0
    for p in glob.glob(f"{work}/lec/*") + glob.glob(f"{work}/lec/*/*") + glob.glob(f"{work}/*lec*.log"):
        try:
            mt = os.stat(p).st_mtime
        except OSError:
            continue
        if mt >= started - 120:
            best = max(best, mt)
    return best


def interp_time(idx, anchors):
    """line index -> time from [(time, line_count)] anchors: piecewise-linear"""
    anchors = sorted(anchors)
    if idx <= anchors[0][1]:
        return anchors[0][0]
    for (t0, l0), (t1, l1) in zip(anchors, anchors[1:]):
        if idx <= l1:
            return t0 if l1 == l0 else t0 + (t1 - t0) * (idx - l0) / (l1 - l0)
    return anchors[-1][0]


EST_MARGIN = 1.25      # line times that are interpolated (no own samples over a full window yet) get a 25 % longer window


def tns_converged(res):
    """NOPROG-TNS0-1124 (COORD; healthy QC V4 kits were ot-heavy-stopped at pregrt_ff_hold with "repair_TNS best 0 last 0"): a TNS
    metric (stored as |TNS|) whose last row is 0 means TNS >= 0, i.e. the repair is done or converged.  That is never a stall: such a
    job is PROGRESS whatever its log silence (a clean-corner repair_timing pass can write nothing for hours)."""
    name = res.get("name") or ""
    ser = res.get("series") or []
    return "TNS" in name and bool(ser) and ser[-1][1] <= 0


def judge(res, anchors, now, window=WINDOW_S, improve=MIN_IMPROVE, exact=False, zero_needs_growth=False):
    """-> (verdict, why, detail).  verdict: PROGRESS | NO-PROGRESS | YOUNG | NO-DATA.
    metric series: improved if the best value inside the last `window` is <= best_before_window * (1 - improve), or 0.
    no metric (or no row yet): the last meaningful line must be newer than `window`.
    exact=False: the line times are interpolated (this tool has not watched the log for a whole window yet), so the window is
    stretched by EST_MARGIN: a borderline job is judged on a later pass from real samples, never on a guess."""
    if not exact:
        window = window * EST_MARGIN
    start = min(a[0] for a in anchors)
    span = now - start
    ser = res["series"]
    if ser:
        pts = [(interp_time(i, anchors), v) for i, v in ser]
        before = [v for t, v in pts if t <= now - window]
        recent = [v for t, v in pts if t > now - window]
        best_all = min(v for _, v in pts)
        detail = f"{res['name']} best {best_all:g} last {pts[-1][1]:g} rows {len(pts)}"
        if tns_converged(res):
            return "PROGRESS", f"{res['name']} last 0 (TNS >= 0: converged/done, not stalled; never cancelled)", detail
        if recent and min(recent) == 0:
            gi = res["growth_idx"]
            if not zero_needs_growth or (gi >= 0 and now - interp_time(gi, anchors) < window) or span < window:
                return "PROGRESS", f"{res['name']} reached 0", detail
            return "NO-PROGRESS", (f"{res['name']} reached 0 but the step wrote nothing for "
                                   f"{(now - interp_time(gi, anchors)) / 3600:.1f} h (>= {window / 3600:g} h)"), detail
        if span < YOUNG_S:
            return "YOUNG", f"stage {span / 3600:.1f} h < {YOUNG_S / 3600:g} h", detail
        if span < window:
            return "YOUNG", f"evidence {span / 3600:.1f} h < {window / 3600:g} h", detail
        # WAVE-PREPNR-1115: a series that restarted inside the window (GRT rounds restart the table) keeps the evidence age of
        # the stage: the baseline is the series start, not "no data" (18 h flat GRT jobs were YOUNG)
        bb = min(before) if before else pts[0][1]
        rb = min(recent) if recent else None
        detail += f" | before-window best {bb:g}, window best {'-' if rb is None else format(rb, 'g')}"
        if rb is None:
            gi = res["growth_idx"]
            if gi >= 0 and now - interp_time(gi, anchors) < window:       # the table is quiet but the stage still writes real news
                return "PROGRESS", f"no new {res['name']} row, but other log lines are new", detail
            return "NO-PROGRESS", f"no new {res['name']} row in {window / 3600:g} h", detail
        if rb <= bb * (1 - improve):
            return "PROGRESS", f"{res['name']} improved {100 * (1 - rb / bb):.1f} % in window", detail
        act = res.get("active") or []
        if act:
            # an iteration >= 1 in flight whose own count has fallen below the best completed total, or is still falling in the window:
            # never NO-PROGRESS (the next DRT-0199 total will carry it)
            apts = [(interp_time(i, anchors), v) for i, v in act]
            arec = [v for t, v in apts if t > now - window]
            if apts[-1][1] <= best_all * (1 - improve):
                return "PROGRESS", (f"{res['name']}: active iteration at {apts[-1][1]:g} < best completed total {best_all:g} "
                                    f"(in-iteration DRT progress)"), detail
            if len(arec) >= 2 and arec[-1] <= max(arec) * (1 - improve):
                return "PROGRESS", f"{res['name']}: falling inside the active iteration ({max(arec):g} -> {arec[-1]:g})", detail
        return "NO-PROGRESS", f"{res['name']} best {rb:g} vs {bb:g} before window: < {100 * improve:.0f} % in {window / 3600:g} h", detail
    gi = res["growth_idx"]
    if gi < 0:
        return "NO-DATA", "empty log", ""
    age = now - interp_time(gi, anchors)
    detail = f"last meaningful line {age / 3600:.1f} h ago ({gi + 1}/{res['n']} lines)"
    if span < window:
        return "YOUNG", f"evidence {span / 3600:.1f} h < {window / 3600:g} h", detail
    if age >= window:
        return "NO-PROGRESS", f"no new non-iteration log line for {age / 3600:.1f} h", detail
    return "PROGRESS", "log still growing", detail


# ---------------------------------------------------------------- WAVE-PREPNR-1115 GRT rounds / yosys stall (pure)
GRT_LABEL = "GRT-LABEL"        # label-only verdict of the GRT round metric (never cancels, never counts as bad)
YOUNG_S = 3600                 # YOUNG = < 1 h since the start of the CURRENT stage
GRT_STOP_OVF = 1000            # FABLE-PD-T14-0935: iteration-10 overflow above ~1000 (or still rising) = design failure
CONG_RPT = re.compile(r"congestion-(\d+)\.rpt$")
CONG_VAL = re.compile(r"congestion:(\d+)")
EXEC_PASS = re.compile(r"Executing (\S+) pass")
SYNTH_STALL_PASSES = ("SHARE", "OPT_MEM_PRIORITY")
SYNTH_STALL_S = 3600


def grt_rounds(report_dir):
    """[(extra-iteration N, total overflow)] from the congestion-N.rpt files FastRoute writes every 5 extra iterations
    (the stage log prints no overflow while it loops).  Overflow = sum of the `congestion:K` values of the violations."""
    out = []
    try:
        names = os.listdir(report_dir)
    except OSError:
        return out
    for nm in names:
        m = CONG_RPT.match(nm)
        if m:
            try:
                out.append((int(m.group(1)), sum(int(x) for x in CONG_VAL.findall(read_text(os.path.join(report_dir, nm))))))
            except OSError:
                pass
    return sorted(out)


GRT_FLAT_ITERS = 5            # FLEET-WATCH-2000: overflow not lower by MIN_IMPROVE over the last 5 extra iterations = flat


def grt_flat(rounds, iters=GRT_FLAT_ITERS, improve=MIN_IMPROVE):
    """-> detail string when the latest overflow is above 0 and has not fallen by `improve` over the last `iters` or more extra iterations (rounds are [(N, overflow)], N the extra iteration
    number, a congestion report every 5), else ''.  A measurement of the rounds, not a time limit."""
    if len(rounds) < 2 or rounds[-1][1] <= 0:
        return ""
    n, v = rounds[-1]
    ref = [(m, w) for m, w in rounds[:-1] if n - m >= iters]
    if not ref:
        return ""
    m, w = ref[-1]
    if v >= w * (1 - improve):
        return f"overflow {w} at iteration {m} -> {v} at iteration {n}: flat for {n - m} iterations"
    return ""


def grt_falling(rounds, improve=MIN_IMPROVE):
    """NOPROG-GRTFALL-1124: True when the latest GRT round's overflow is >= `improve` below the round before it (FastRoute still
    converging).  KV HGI kits 11-24 19:3x were cancelled 'design' at 28701 -> 12166 and 25885 -> 10162 (round 5 -> 10).  Pure."""
    return len(rounds) >= 2 and rounds[-1][1] < rounds[-2][1] * (1 - improve)


def grt_round_interval(report_dir, rounds):
    """seconds between the last two congestion-N.rpt writes (0 when unknown).  NOPROG-GRTFALL-1124: a flat clock shorter than one GRT round
    judges a kit that simply has not reached its next round."""
    if len(rounds) < 2:
        return 0.0
    try:
        a = os.path.getmtime(os.path.join(report_dir, f"congestion-{rounds[-2][0]}.rpt"))
        b = os.path.getmtime(os.path.join(report_dir, f"congestion-{rounds[-1][0]}.rpt"))
    except OSError:
        return 0.0
    return max(0.0, b - a)


def judge_grt_rounds(rounds, log_text=""):
    """-> None | (verdict, why, detail, klass).  DESIGN-FAIL (GRT-CONGESTION): the first GRT-0273 (a clock NDR dropped under
    congestion), or the overflow at round >= 10 above GRT_STOP_OVF or still rising.  NO-PROGRESS: the overflow has not fallen
    across 2 consecutive rounds.  A measurement of the rounds, not a time limit."""
    trend = " -> ".join(f"{n}:{v}" for n, v in rounds[-6:])
    detail = f"grt rounds {len(rounds)} overflow {trend}"
    if "GRT-0273" in log_text:
        return "DESIGN-FAIL", "GRT-0273 (clock NDR dropped under congestion)", detail, "GRT-CONGESTION"
    late = [(n, v) for n, v in rounds if n >= 10]
    if late:
        n10, v10 = late[0]
        if v10 > GRT_STOP_OVF:
            return "DESIGN-FAIL", f"overflow {v10} at round {n10} > {GRT_STOP_OVF}", detail, "GRT-CONGESTION"
        if len(late) > 1 and late[-1][1] > late[-2][1]:
            return "DESIGN-FAIL", f"overflow rising at round {late[-1][0]}: {late[-2][1]} -> {late[-1][1]}", detail, "GRT-CONGESTION"
    v = [x for _, x in rounds]
    if len(v) >= 3 and v[-1] > 0 and v[-1] >= v[-2] >= v[-3]:
        return "NO-PROGRESS", f"overflow has not fallen across 2 consecutive rounds ({v[-3]} {v[-2]} {v[-1]})", detail, ""
    return None


GRT_ROUTE_END = re.compile(r"GRT-0115\]|^Repair setup and hold|^OT_HOLD_GUARD_GRT start|^repair_design |^repair_timing |^Iteration \|")


def grt_repair_phase(text):
    """NOPROG-GRTHOLD-1124 (COORD): True when the global route of this 5_1_grt log has FINISHED its extra iterations (a GRT-0115 / repair
    marker after the last 'Start extra iteration') and the log is in the post-route repair (repair_design, hold/setup repair_timing).
    The congestion-N.rpt overflow is then final: it can never fall again, so a flat overflow says nothing about the repair that runs
    (KV kv3_hgi_1124155644 / kv3_hgi_v2_1124155702 were cancelled 'design' 11-24 22:29 in hold repair / repair_design).  Pure."""
    lines = text.splitlines()
    last = -1
    for i, ln in enumerate(lines):
        if "GRT-0102] Start extra iteration" in ln:
            last = i
    return any(GRT_ROUTE_END.search(ln) for ln in lines[last + 1:])


def grt_repair_progress(r):
    """True for a row whose GRT routing is done and whose repair step is not stalled (judge verdict PROGRESS / YOUNG)"""
    return str(r.get("grt_repair") or "").startswith(("PROGRESS", "YOUNG"))


def synth_mem_stall(text, log_age_s):
    """a yosys log whose last pass is SHARE / OPT_MEM_PRIORITY and silent for 60 min: a DESIGN failure (SYNTH-MEM-STALL)"""
    passes = EXEC_PASS.findall(text)
    if passes and passes[-1] in SYNTH_STALL_PASSES and log_age_s >= SYNTH_STALL_S:
        return "DESIGN-FAIL", f"yosys in pass {passes[-1]} for {log_age_s / 60:.0f} min", f"yosys last pass {passes[-1]}", "SYNTH-MEM-STALL"
    return None


# ---------------------------------------------------------------- policy helpers (pure)
PLAN_RE = re.compile(r"(?i)(strict[-_ ]?bind|bind[-_]?strict|die[-_]?proto|(?:^|[/_ -])g0(?:[/_. -]|$)|latcheck|chain[A-Za-z]*\d*\.sh|kit[-_]gen[-_]proof)")
HBM_RE = re.compile(r"(?i)(^|[/_-])(hbm|trialhbm|hbmcore)")


B64 = re.compile(r"[A-Za-z0-9+/=]{60,}")


# ---------------------------------------------------------------- UNSIGNABLE (FLEET-WATCH-1015, owner rule 11-20, FABLE-FLOW-1000 class 5)
# A job running > 3 h whose MEASURED post-CTS/repair setup (4_1_cts.json cts__timing__setup__ws) is worse than -300 ps cannot sign off (gate TT >= -42 ps).  The hub cancels it by
# `ot-run --cancel <exact unit>` after it was listed in a posted table, and writes the evidence row to lanes/CANCEL-UNSIGNABLE-1120.tsv.  Never touched: hold-only failures (setup is the only
# number read), unmeasured jobs (no 4_1_cts.json written by THIS job), --priority plan / proof jobs and proofs by name, ECOs, HBM (parked: its own verdict), KEEP lines, setup between -42 and -300.
UNSIGNABLE = "UNSIGNABLE"
UNSIGNABLE_SETUP_PS = -300.0
UNSIGNABLE_MIN_AGE_H = 3.0
UNSIGNABLE_REPORT_ONLY_S = 3600       # legacy (pre FLOW-OPS-0900); the notice flow below replaced the report hour
GATE_SETUP_PS = -42.0
# FLOW-OPS-0900 (owner 11-21): NOTICE to the owning lane, cancel 30 min later unless the lane posted KEEP <unit>.  COORD 11-23 02:3x: the owner's 30 min window is the
# default (LAUNCH-GUARD had made it 0); NOPROG_UNSIGNABLE_GRACE_S=0 gives a first-pass cancel.  GRT-LABEL DESIGN-FAIL cancels (design_fail_pass) stay first-pass.
UNSIGNABLE_GRACE_S = int(os.environ.get("NOPROG_UNSIGNABLE_GRACE_S", "1800"))
UNSIGNABLE_FORGET_S = 6 * 3600        # a unit not seen for 6 h is forgotten; a short gap in the list keeps its first-listed time
PRIVATE_RE = re.compile(r"/private/")
HOLD_ONLY_RE = re.compile(r"(?i)(?:^|[/_\-.])hold(?:[_-]?only|[_-]?fix|[_-]?eco|[_-]?gate)?(?:$|[/_\-.0-9])")
# never auto-cancelled: posted to the named lane for a decision (COORD 11-21 FLOW-OPS-0900 brief); lanes/UNSIGNABLE-DECIDE.tsv (regex<TAB>lane) adds more
DECIDE_ONLY = ((r"ot_s81sl_leaf__t11(?![0-9])", "FABLE-FIX-S81-LEAF-R5"), (r"(?:^|[^A-Za-z0-9])slw_su_c(?![A-Za-z0-9])", "QC-SUC-FTSITE"))
ECO_RE = re.compile(r"(?i)(?:^|[/_\-.])eco(?:$|[/_\-.0-9])")
PROOF_RE = re.compile(r"(?i)(?:^|[/_\-.])proofs?(?:$|[/_\-.0-9])")
UNSIG_GLOBS = ("run/logs/*/*/*/4_1_cts.json", "gen/*/run/logs/*/*/*/4_1_cts.json", "logs/*/*/*/4_1_cts.json", "*/4_1_cts.json", "4_1_cts.json")


def _posthook_setup(json_path):
    """setup_ws of the LAST OT_CTS_POST_TIMING line of the 4_1_cts.log next to json_path, else None (TAP-GRID-2130)"""
    try:
        with open(os.path.join(os.path.dirname(json_path), "4_1_cts.log"), errors="replace") as f:
            ms = re.findall(r"(?m)^OT_CTS_POST_TIMING setup_ws (-?[0-9.]+)", f.read())
    except OSError:
        return None
    return float(ms[-1]) if ms else None


def measured_setup(dirs, started):
    """-> (setup_ws_ps, path) from the newest 4_1_cts.json under any of dirs that THIS job wrote (mtime >= its container start - 60 s), else None.  Missing key / unparsable = None (unmeasured)."""
    best = None
    for d in dict.fromkeys(x for x in dirs if x):
        for g in UNSIG_GLOBS:
            for p in glob.glob(os.path.join(d, g)):
                try:
                    mt = os.path.getmtime(p)
                    if mt < started - 60 or (best and mt <= best[0]):
                        continue
                    v = json.load(open(p)).get("cts__timing__setup__ws")
                    # TAP-GRID-2130: 4_1_cts.json cts__timing is PRE-hook on kits older than the post-hook rewrite; the
                    # 4_1_cts.log OT_CTS_POST_TIMING line (tap-balanced DB) wins when present (die_plan/cts_read.py)
                    pv = _posthook_setup(p)
                    if pv is not None:
                        v = pv
                except (OSError, ValueError, AttributeError):
                    continue
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    best = (mt, float(v), p)
    return (best[1], best[2]) if best else None


STAGE_JSON_KEYS = ("cts", "globalroute", "detailedroute", "finish")
SETUP_LOG_GLOBS = ("run/logs/*/*/*/5_*.tmp.log", "run/logs/*/*/*/5_*.log", "gen/*/run/logs/*/*/*/5_*.tmp.log", "gen/*/run/logs/*/*/*/5_*.log", "5_*.tmp.log", "5_*.log")
TT_LOG_GLOBS = ("tt_setup_*.log", "gen/*/tt_setup_*.log")
TT_WNS_RE = re.compile(r"\bwns\s+(-?\d+(?:\.\d+)?)(?:\s*->\s*(-?\d+(?:\.\d+)?))?")
FLAT_ROWS, FLAT_TAIL, FLAT_FRAC = 20, 10, 0.01


def setup_table_wns(text):
    """-> WNS of the last setup repair table (see setup_table_state)"""
    return setup_table_state(text)[0]


def setup_table_state(text):
    """-> (wns, how) with how 'final' | 'flat' | None.  WNS (ps) of the LAST setup repair_timing table of a log (header with WNS and StTNS; hold tables and repair_design are never read), else None.  A table still being written counts only
    when it is FLAT (>= FLAT_ROWS rows, the last FLAT_TAIL rows within FLAT_FRAC of the value); otherwise the job is still repairing and the number is not final -> None."""
    last = None
    for t in parse_tables(text.splitlines()):
        cols = t["cols"]
        if "WNS" not in cols or "StTNS" not in cols:
            continue
        i = cols.index("WNS")
        vals = [r[i] for _ln, r in t["rows"] if i < len(r) and r[i] is not None]
        if not vals:
            continue
        if t["final"]:
            last = (vals[-1], "final")
        elif len(vals) >= FLAT_ROWS and (max(vals[-FLAT_TAIL:]) - min(vals[-FLAT_TAIL:])) <= FLAT_FRAC * abs(vals[-1]):
            last = (vals[-1], "flat")
        else:
            last = None            # still improving: a number that is not the stage result
    return last or (None, None)


def latest_setup(dirs, started):
    """-> (ws_ps, source path) or None; see latest_setup_ex"""
    r = latest_setup_ex(dirs, started)
    return r[:2] if r else None


def latest_setup_ex(dirs, started):
    """-> (ws_ps, source path, how) or None, how = 'flat' when the number is a setup repair table that went flat while still running (FLOW-OPS-0900: owner 'flat repair' rule).  COORD 11-20 (FABLE-FLOW-1200: cancels on the post-CTS number while GRT repair had moved one job to -0.494 ps): the NEWEST setup number THIS job wrote (mtime >= its container start - 60 s, so a resumed
    run is unmeasured until it reports): stage jsons (cts / globalroute / detailedroute), OT_TT_SETUP_* logs (last wns), the last finished or flat setup repair table of a 5_* stage log.  A newer stage
    file of the job that yields no setup number (repair still improving, hold pass) makes the job UNMEASURED.  -> (ws_ps, source path) or None."""
    cands, newest_unread = [], 0.0
    def fresh(p):
        try:
            mt = os.path.getmtime(p)
        except OSError:
            return None
        return mt if mt >= started - 60 else None
    for d in dict.fromkeys(x for x in dirs if x):
        for g in ("run/logs/*/*/*/[45]_*.json", "gen/*/run/logs/*/*/*/[45]_*.json", "[45]_*.json"):
            for p in glob.glob(os.path.join(d, g)):
                mt = fresh(p)
                if mt is None:
                    continue
                try:
                    j = json.load(open(p))
                except (OSError, ValueError):
                    newest_unread = max(newest_unread, mt); continue
                v = next((j[f"{k}__timing__setup__ws"] for k in STAGE_JSON_KEYS if isinstance(j.get(f"{k}__timing__setup__ws"), (int, float)) and not isinstance(j.get(f"{k}__timing__setup__ws"), bool)), None)
                if v is not None:
                    cands.append((mt, float(v), p, ""))
        for g in TT_LOG_GLOBS:
            for p in glob.glob(os.path.join(d, g)):
                mt = fresh(p)
                if mt is None:
                    continue
                ms = TT_WNS_RE.findall(read_text(p))
                if ms:
                    a, b = ms[-1]
                    cands.append((mt, float(b or a), p, ""))
                else:
                    newest_unread = max(newest_unread, mt)
        for g in SETUP_LOG_GLOBS:
            for p in glob.glob(os.path.join(d, g)):
                mt = fresh(p)
                if mt is None:
                    continue
                v, how = setup_table_state(read_text(p))
                if v is None:
                    newest_unread = max(newest_unread, mt)
                else:
                    cands.append((mt, v, p, how if how == "flat" else ""))
    if not cands:
        return None
    mt, v, p, how = max(cands)
    if newest_unread > mt:
        return None                      # a newer stage file carries no setup number yet: unmeasured, never the stale one
    return v, p, how


def unsignable_exempt(ident, prio, kind):
    """-> reason the job is never judged UNSIGNABLE, else ''.  Pure.  Proofs (--priority proof/plan, proof by name, private-spec kits under /private/), ECOs, hold-only jobs, LEC, HBM."""
    if prio in ("plan", "proof"):
        return f"priority {prio}"
    if kind == "lec":
        return "LEC"
    if ECO_RE.search(ident):
        return "ECO"
    if PROOF_RE.search(ident):
        return "proof"
    # LAUNCH-GUARD 11-23 (COORD FIX 2): a private-spec kit is a lane's representative, not a proof: it is judged like any kit (hub post b556fc6:
    # col_h9_r0_p3 private kit ran 72,008 s and died RSZ-0060; the old 'proof / private kit' exemption meant no private kit was ever cancelled)
    if HOLD_ONLY_RE.search(ident):
        return "hold-only job"
    if is_hbm(ident):
        return "HBM (parked)"
    return ""


def unsignable_evidence(ident, prio, kind, age_h, setup):
    """-> evidence text when the rule applies, else None.  Pure.  setup = (ws, path[, how]); how 'flat' = a setup repair table that stopped improving.
    Fires on setup < -300 ps, or on a FLAT repair still worse than the -42 ps gate (owner 11-20 'flat repair'), only after 3 h."""
    if setup is None or age_h <= UNSIGNABLE_MIN_AGE_H or unsignable_exempt(ident, prio, kind):
        return None
    how = setup[2] if len(setup) > 2 else ""
    if setup[0] < UNSIGNABLE_SETUP_PS:
        return f"{os.path.basename(setup[1])} latest setup WNS {setup[0]:.2f} ps (< {UNSIGNABLE_SETUP_PS:.0f}, gate TT >= -42); job age {age_h} h > {UNSIGNABLE_MIN_AGE_H:g} h"
    if how == "flat" and setup[0] < GATE_SETUP_PS:
        return f"{os.path.basename(setup[1])} setup repair FLAT at WNS {setup[0]:.2f} ps (gate TT >= {GATE_SETUP_PS:.0f}, repair no longer improving); job age {age_h} h > {UNSIGNABLE_MIN_AGE_H:g} h"
    return None


def grt_unsignable_evidence(row):
    """GRT overflow flat over 2 rounds (the NOPROG GRT label 'not fallen across 2 consecutive rounds' or grt_flat) on a job > 3 h that the wave's GRT-FLAT pass does not take (lane jobs).  Pure."""
    if row.get("age_h", 0) <= UNSIGNABLE_MIN_AGE_H or row.get("kind") != "grt" or unsignable_exempt(row.get("ident", ""), row.get("prio", ""), row.get("kind", "")):
        return None
    why = str(row.get("why") or "")
    if row.get("grt_flat"):
        return f"GRT overflow flat: {row['grt_flat']}; job age {row['age_h']} h"
    if row.get("verdict") == GRT_LABEL and "2 consecutive rounds" in why:
        return f"GRT {why}; {row.get('detail') or ''}; job age {row['age_h']} h"
    return None


# ---------------------------------------------------------------- ECO / repair FLAT (LAUNCH-GUARD 11-23, COORD FIX 2; owner rule 11-20 "flat repair")
# Post 8f2ce5a: a late-ECO loop ran 80,509 s (3 iterations) with FF hold flat at -160 ps (-161.47 -> -160.51 -> -160.57); ECOs were exempt from every
# judgement.  An ECO that no longer improves cannot sign: after >= 3 h, when its last two sign-off measurements gained less than ECO_MIN_GAIN (2 %) of the
# deficit on every failing gate (TT setup < -42 ps, FF hold < 0 ps), it is UNSIGNABLE (class ECO-FLAT).  An ECO still gaining is never touched.
ECO_SIGNOFF_RE = re.compile(r"TT setup (-?\d+(?:\.\d+)?)\s*\|\s*FF hold (-?\d+(?:\.\d+)?)")
ECO_MIN_GAIN = 0.02
ECO_LOG_GLOBS = ("ot-run.log", "eco/*.log", "eco_loop.log", "*.live.log")


def eco_root(path):
    """the ECO job dir of a kit / work path: the prefix before '/eco/' or an 'eco_*' dir component"""
    p = str(path or "")
    if "/eco/" in p:
        return p.split("/eco/")[0]
    m = re.search(r"^(.*?/eco_[^/]+)", p)
    return m.group(1) if m else ""


def eco_series(text):
    """-> [(tt_setup, ff_hold)] of every SIGNOFF measurement line, in order"""
    return [(float(a), float(b)) for a, b in ECO_SIGNOFF_RE.findall(text or "")]


def eco_flat_evidence(series, age_h, min_gain=ECO_MIN_GAIN):
    """-> evidence text when the last two measurements show no >= min_gain improvement of any failing gate's deficit, else None.  Pure."""
    if age_h <= UNSIGNABLE_MIN_AGE_H or len(series) < 2:
        return None
    (t0, f0), (t1, f1) = series[-2], series[-1]
    fails = []
    if t1 < GATE_SETUP_PS:
        fails.append(("TT setup", t0, t1, GATE_SETUP_PS))
    if f1 < 0:
        fails.append(("FF hold", f0, f1, 0.0))
    if not fails:
        return None                                    # passing gates: the ECO is about to sign
    for name, a, b, gate in fails:
        deficit = max(gate - a, 1e-9)
        if (b - a) >= min_gain * deficit:
            return None                                # still improving on this gate
    return ("ECO-FLAT: " + "; ".join(f"{n} {a:.2f} -> {b:.2f} ps (gate {g:+.0f})" for n, a, b, g in fails)
            + f" over the last 2 of {len(series)} sign-off measurements (< {int(min_gain * 100)} % of the deficit); job age {age_h} h > {UNSIGNABLE_MIN_AGE_H:g} h")


def eco_measurements(kit, work):
    root = eco_root(kit) or eco_root(work)
    if not root:
        return []
    out = []
    for g in ECO_LOG_GLOBS:
        for p in sorted(glob.glob(os.path.join(root, g))):
            out += eco_series(read_text(p))
        if out:
            break
    return out


# ---------------------------------------------------------------- GRT-STUCK (FLOW-FLEET-R1 11-22, FABLE-FLOW-2200 H3, owner rule 11-20)
# 19 GRT-0273 containers ran 7 to 51 h with an empty action column: the GRT-LABEL verdict is a label, grt_flat_pass takes only wave kits under
# items/<item>/attempt_N, and lane / private / gen-path kits had no action at all.  GRT-STUCK = the overflow is flat or rising over the last 3 or more
# GRT rounds (best of the later rounds not 2 % below the first) AND the job has been > 6 h in GRT.  It is a BAD verdict like NO-PROGRESS: REPORTED on the
# first pass, cancelled (ot-heavy-stop of its scope, NOPROG-ACTIONS row, NEEDS-LANE post) on a later pass.  Not judged: wave attempts that grt_flat_pass
# cancels through cancel-rows, re-sign / ECO / hold-only jobs, kits that are, hold or lie under a PROTECTED-DBS path of the host, and jobs a lane named
# (container, unit, kit dir) in a post of the last 2 h.  The hub copies both lists to every host's policy dir each tick.
GRT_STUCK = "GRT-STUCK"
GRT_STUCK_ROUNDS = 3
GRT_STUCK_MIN_STAGE_H = 6.0
GRT_STUCK_POST_S = 2 * 3600
POST_STAMP_RE = re.compile(r"^- (\d{4}-\d{2}-\d{2} \d{2}:\d{2})")
WATCHDOG_POSTERS = re.compile(r"(?i)^(NOPROG-WATCHDOG|FLEET-WATCH|WATCHDOG|STALL-WATCH|PROGRESS-WATCH|COORD-REVIEW-QUEUE)")


def grt_stuck(rounds, stage_age_h, rounds_n=GRT_STUCK_ROUNDS, improve=MIN_IMPROVE, min_stage_h=GRT_STUCK_MIN_STAGE_H):
    """-> evidence string when the latest overflow is > 0, there are >= rounds_n GRT rounds, the best overflow of the last rounds_n - 1 rounds is not
    `improve` below the round before them (flat or rising over rounds_n rounds), and the GRT stage is older than min_stage_h; else ''.  Pure."""
    if len(rounds) < rounds_n or rounds[-1][1] <= 0 or (stage_age_h or 0) <= min_stage_h:
        return ""
    base_n, base = rounds[-rounds_n]
    later = rounds[-rounds_n + 1:]
    best = min(v for _n, v in later)
    if best < base * (1 - improve):
        return ""
    trend = " -> ".join(f"{n}:{v}" for n, v in rounds[-rounds_n:])
    return (f"GRT overflow flat/rising over {rounds_n} rounds ({trend}; best {best} vs {base} at round {base_n}); "
            f"{stage_age_h:.1f} h in GRT > {min_stage_h:g} h")


def _related_path(a, b):
    a, b = (a or "").rstrip("/"), (b or "").rstrip("/")
    return bool(a) and bool(b) and (a == b or a.startswith(b + "/") or b.startswith(a + "/"))


def protected_rows(text, host):
    """PROTECTED-DBS rows of fleet host `host` -> [path].  Rows are host<TAB|spaces>path[ note] or host:/path (lanes/ and root lists); a row that
    starts with a bare /path names no host and protects that path on every host."""
    out = []
    for ln in (text or "").splitlines():
        if ln.lstrip().startswith("#"):
            continue
        f = ln.split()
        if f and ":/" in f[0]:
            f = f[0].split(":", 1) + f[1:]
        if f and f[0].startswith("/"):
            out.append(f[0].rstrip("/"))
        elif len(f) >= 2 and f[0] == host and f[1].startswith("/"):
            out.append(f[1].rstrip("/"))
    return out


def recent_posts(coord, now, horizon_s=GRT_STUCK_POST_S + 1800):
    """-> [(epoch, lane, text)] of the post entries of lanes/posts/*.md stamped within horizon_s (watchdog lanes excluded).  Hub side."""
    out = []
    for p in glob.glob(os.path.join(coord, "lanes/posts/*.md")):
        lane = os.path.basename(p)[:-3]
        if WATCHDOG_POSTERS.match(lane):
            continue
        try:
            if now - os.path.getmtime(p) > horizon_s:
                continue
            lines = read_text(p, cap=4 * 2**20).splitlines()
        except OSError:
            continue
        cur = None
        for ln in lines[-3000:]:
            m = POST_STAMP_RE.match(ln)
            if m:
                try:
                    t = time.mktime(time.strptime(m.group(1), "%Y-%m-%d %H:%M"))
                except ValueError:
                    t = None
                cur = [t, lane, ln] if t and now - t <= horizon_s else None
                if cur:
                    out.append(cur)
            elif cur is not None and ln.startswith("  "):
                cur[2] += " " + ln.strip()
    return [(t, l, x.replace("\t", " ").replace("\n", " ")) for t, l, x in out]


def grt_stuck_spare(row, protected, posts, now, post_s=GRT_STUCK_POST_S):
    """-> reason the GRT-STUCK row is spared, else ''.  Pure.  protected = [path] of this host; posts = [(epoch, lane, text)]."""
    ident = " ".join(str(row.get(k) or "") for k in ("container", "type", "kit", "work", "ident"))
    if "resign" in ident.lower() or "re-sign" in ident.lower():
        return "re-sign"
    if ECO_RE.search(ident) or HOLD_ONLY_RE.search(ident):
        return "ECO"
    ex = grt_flat_exempt(row)
    if not ex:
        return "wave attempt: grt_flat_pass cancels it through cancel-rows"
    if not (ex.startswith("OT_LANE") or ex.startswith("private kit")):
        return ex
    for pth in protected:
        if _related_path(row.get("kit"), pth) or _related_path(row.get("work"), pth):
            return f"PROTECTED-DBS {pth}"
    toks = [t for t in (row.get("container"), row.get("unit"), (row.get("kit") or "").rstrip("/"), (row.get("work") or "").rstrip("/")) if t and len(t) > 8]
    kit = (row.get("kit") or "").rstrip("/")
    m = LANE_DIR_RE.search(kit + "/")
    if m:
        toks.append(kit.split("/claude/", 1)[1])     # lane-relative kit path ("lockup-station-r2/proof6_t39") as lanes write it
    for t, lane, text in posts:
        if now - t <= post_s and any(tok in text for tok in toks):
            return f"lane {lane} posted about it {(now - t) / 60:.0f} min ago"
    return ""


def load_spare_inputs(pol):
    """host side: (protected paths, recent posts) from the policy files the hub writes per host (protected.tsv = one path per line, already this host's
    rows; posts_recent.tsv = epoch<TAB>lane<TAB>text); missing files = empty lists"""
    prot = [l.strip().rstrip("/") for l in read_lines(os.path.join(pol, "protected.tsv")) if l.strip().startswith("/")]
    posts = []
    for l in read_lines(os.path.join(pol, "posts_recent.tsv")):
        f = l.split("\t", 2)
        try:
            posts.append((float(f[0]), f[1], f[2]))
        except (ValueError, IndexError):
            continue
    return prot, posts


def is_plan(env_prio, text):
    """--priority plan (OT_HEAVY_PRIO=plan) or a bind / LATCHECK / G0 / die-proto / chain command.  --priority die (die-level
    trials) is NOT excluded: those are exactly the long builds this watchdog is for.  base64 spec blobs are stripped first."""
    # WAVE-PREPNR-1115 (COORD FABLE-FLOW-1200 f4 / FLOW-1350 c3): ONLY a declared OT_HEAVY_PRIO=plan excludes.  The old text match
    # (PLAN_RE on the command line) excluded 81 of 110 rows although no job carried --priority plan.
    return env_prio == "plan"


# KIT-OPS-6 11-14 (COORD item 8): 20:46 the watchdog killed HEAD elemA/elemB core builds (intel1 A1/B1) because HEAD cores use the HBM
# core-kit generator: container hbmcore-kit_*, command run_kit_hbm.sh.  The generator name says nothing about the die.  HBM is decided
# from the die metadata the ident carries (kit dir / work dir / type name under an hbm die: .../runs/hbm/..., hbm-*, ot_hbm_*, trialhbm-*),
# after the generator tokens are removed.
GENERATOR_RE = re.compile(r"(?i)(?:^|(?<=[\s/]))hbmcore-|run_kit_hbm\.sh")


# HBM-DIE-FIELD-1122 (COORD flow review: QC slw_su_l0 epyc2 / slw_hc2 epyc8 design_export jobs listed CANCEL-NOW "HBM is parked" because
# HBM_RE matched "hbm" anywhere in the ident, here a stale cwd .../w/hbm.t.q_spt2/raw): HBM is decided by the job's DIE FIELD only, never
# by a substring of a path.  The die field, first hit wins:
#   1. the job's own design id <die>.t.<type> in the container name or in a path basename (explorer / export jobs);
#   2. the kit's freeze.json "die" (every gen_phys type kit) for each path of the ident;
#   3. a die path segment /runs/<die>/, /kit-wave/<die>/, /die_plan/<die>/;
#   4. HBM die type names: ot_hbm_* (after the container prefix) or a trialhbm-* container.
# The generator name (hbmcore-*, run_kit_hbm.sh) is never a die (KIT-OPS-6 11-14).
DIE_NAMES = ("qwen_compute", "qwen_kvsys", "s81_head", "s81", "hbm")
DESIGN_ID_RE = re.compile(r"(?<![A-Za-z0-9_])(" + "|".join(DIE_NAMES) + r")\.t\.")
DIE_SEG_RE = re.compile(r"/(?:runs|kit-wave|die_plan)/(" + "|".join(DIE_NAMES) + r")(?=/|$)")
HBM_TYPE_RE = re.compile(r"^(?:trialhbm-|(?:dpkit|hbmcore|trialhbm|prd|kqc|klegacy|otc)-ot_hbm_|ot_hbm_)")
_KIT_DIE = {}


def kit_die(path):
    """-> the die named by <path>/freeze.json (cached; '' when absent / unreadable)"""
    if not path or not path.startswith("/"):
        return ""
    if path not in _KIT_DIE:
        try:
            with open(os.path.join(path, "freeze.json")) as f:
                d = json.load(f).get("die")
            _KIT_DIE[path] = d if isinstance(d, str) else ""
        except (OSError, ValueError, AttributeError):
            _KIT_DIE[path] = ""
    return _KIT_DIE[path]


def die_of(text):
    """-> the die field of a job ident ('<container> <kit> <work> [<log>] ...'), '' when it names none.  See HBM-DIE-FIELD-1122."""
    toks = (text or "").split()
    if not toks:
        return ""
    name, paths = ("", toks) if toks[0].startswith("/") else (toks[0], toks[1:])
    paths = [t for t in paths if t.startswith("/")]
    for t in [name] + [os.path.basename(t.rstrip("/")) for t in paths]:
        m = DESIGN_ID_RE.search(t)
        if m:
            return m.group(1)
    for t in paths:
        d = kit_die(t.rstrip("/"))
        if d:
            return d
    for t in paths:
        m = DIE_SEG_RE.search(t)
        if m:
            return m.group(1)
    if HBM_TYPE_RE.search(name):
        return "hbm"
    return ""


def is_hbm(text):
    return die_of(text) == "hbm"


def base_type(name):
    n = re.sub(r"^(dpkit|hbmcore|trialhbm|prd|kqc|klegacy|otc|ap-ageom-kw)-", "", name)
    n = re.sub(r"-\d+(-lec)?$", "", n)
    return re.split(r"__(?:cl|pv)[0-9a-f]{6,}", n)[0]


def read_lines(path):
    try:
        return [l.rstrip("\n") for l in open(path, errors="replace") if l.strip() and not l.startswith("#")]
    except OSError:
        return []


def keep_match(keep_lines, text):
    for ln in keep_lines:
        k = ln.split("\t")[0].strip()
        if k and k in text:
            return ln
    return None


# ---------------------------------------------------------------- host scan
DOCKER_ERR = []     # DOCKERGRP-1400: why a docker call returned nothing (filled by sh, read by scan, which says so loudly)


def sh(*a, timeout=60):
    """run a command, return stdout.  DOCKERGRP-1400: a systemd USER manager keeps the groups it started with; epyc8/9/10 started theirs before ubuntu joined group docker,
    so every unit it runs gets 'permission denied' on the socket and `docker ps -q` was empty on every pass (167 of 369 jobs unwatched, 30 h).  A docker call that is
    refused is retried once through `sg docker -c` (setuid newgrp; the user is in /etc/group docker); a failure that remains is kept in DOCKER_ERR."""
    try:
        r = subprocess.run(list(a), capture_output=True, text=True, timeout=timeout)
        if a and a[0] == "docker" and r.returncode != 0 and "permission denied" in (r.stderr or "").lower():
            r = subprocess.run(["sg", "docker", "-c", " ".join(shlex.quote(x) for x in a)], capture_output=True, text=True, timeout=timeout)
        if a and a[0] == "docker" and r.returncode != 0:
            DOCKER_ERR.append((r.stderr or "").strip()[:200] or f"rc {r.returncode}")
        return r.stdout
    except (subprocess.SubprocessError, OSError) as e:
        if a and a[0] == "docker":
            DOCKER_ERR.append(f"{type(e).__name__}: {e}"[:200])
        return ""


def owner_pid(name):
    m = re.match(r"otc-(\d+)-\d+$", name) or re.search(r"-(\d+)(?:-lec)?$", name)
    return int(m[1]) if m else None


def scopes():
    """unit -> [pids] of active oth-* scopes"""
    out = {}
    for root, dirs, files in os.walk("/sys/fs/cgroup/user.slice"):
        b = os.path.basename(root)
        if b.startswith("oth-") and b.endswith(".scope"):
            try:
                out[b[:-6]] = [int(x) for x in open(os.path.join(root, "cgroup.procs")).read().split()]
            except OSError:
                pass
            dirs[:] = []
    return out


def proc_info(pid):
    try:
        return open(f"/proc/{pid}/cmdline").read().replace("\0", " "), os.readlink(f"/proc/{pid}/cwd")
    except OSError:
        return "", ""


def proc_env(pid, key):
    try:
        for kv in open(f"/proc/{pid}/environ", "rb").read().split(b"\0"):
            if kv.startswith(key.encode() + b"="):
                return kv.split(b"=", 1)[1].decode()
    except OSError:
        pass
    return ""


def proc_env_prio(pid):
    return proc_env(pid, "OT_HEAVY_PRIO")


def cgroup_dir(pid):
    try:
        for ln in open(f"/proc/{pid}/cgroup"):
            if ln.startswith("0::"):
                return "/sys/fs/cgroup" + ln[3:].strip()
    except OSError:
        pass
    return None


def cg_read(cg, f):
    try:
        return open(os.path.join(cg, f)).read()
    except OSError:
        return ""


def cpu_usec(cg):
    m = re.search(r"usage_usec (\d+)", cg_read(cg, "cpu.stat")) if cg else None
    return int(m[1]) if m else None


def mem_gb(cg):
    try:
        return int(cg_read(cg, "memory.current").strip() or 0) / 2**30 if cg else 0.0
    except ValueError:
        return 0.0


def birth(path):
    try:
        v = int(sh("stat", "-c", "%W", path, timeout=10).strip())
        return v if v > 0 else None
    except ValueError:
        return None


def work_dir(mounts):
    for m in mounts:
        if m["Destination"] == "/work":
            return m["Source"]
    for m in mounts:
        if "/run/results/" in m["Source"]:
            return m["Source"].split("/run/results/")[0]
    return mounts[0]["Source"] if mounts else None


def candidate_logs(work, mounts, cname, started):
    """the newest log that is not older than the container: ORFS stage tmp logs first, else the kit's own step logs
    (LEC containers: the lec logs)"""
    cands = []
    _glob = glob.glob
    glob_ = lambda pat: [p for p in _glob(pat) if not NOT_FLOW_LOG.search(os.path.basename(p))]
    if work:
        cands += glob_(f"{work}/run/logs/*/*/*/*.log")        # *.tmp.log = the running OpenROAD stage; yosys writes its *.log directly
    if cname.endswith("-lec"):
        for root in {work} | {m["Source"] for m in mounts}:
            if root:
                cands += glob_(f"{root}/*lec*.log") + glob_(f"{root}/*/*lec*.log") + glob_(f"{root}/lec/*.log")
    else:
        if work:        # a kit step's own log (pregrt_ff_hold.log, hold_gate.log ...); run_*.log is the aggregate runner stdout: fallback only
            cands += [p for p in glob_(f"{work}/*.log") + glob_(f"{work}/run/*.log") if not os.path.basename(p).startswith("run_")]
        if not cands and work:
            cands += glob_(f"{work}/run_*.log")
        if not cands:
            for m in mounts:
                cands += glob_(f"{m['Source']}/*.log") + glob_(f"{m['Source']}/*/*.log")
    out = []
    for p in cands:
        try:
            out.append((p, os.stat(p).st_mtime))
        except OSError:
            pass
    live = sorted((x for x in out if x[1] >= started - 120), key=lambda x: -x[1])
    return (live or [(None, 0)])[0]


def read_text(path, cap=64 * 2**20):
    try:
        sz = os.path.getsize(path)
        with open(path, "rb") as f:
            if sz > cap:
                f.seek(sz - cap)
                f.readline()
            return f.read().decode(errors="replace")
    except OSError:
        return ""


def load_state():
    try:
        return json.load(open(os.path.join(STATE_DIR, "state.json")))
    except (OSError, ValueError):
        return {"jobs": {}, "reported": {}}


def save_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + f".tmp{os.getpid()}"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1, sort_keys=True)
    os.replace(tmp, path)


# COORD ruling 11-22 (owner rule: proofs, ECOs and hold-only jobs are exempt from unsignable cancels; lanes own their private kits): a NO-PROGRESS or
# GRT-STUCK job whose kit is a lane's own (a kit-wave .../private/<LANE>/... spec, or a dir under a lane's scratch dir) is REPORTED to that lane and the
# hub, never auto-cancelled.  Shared roots below /srv/opentallas-scratch*/claude/ are not lane dirs.
LANE_OWN_VERDICTS = ("NO-PROGRESS", GRT_STUCK)
SHARED_ROOT_RE = re.compile(r"^(kw\d+-wave.*|kw45|autopilot|rt|ot-jobs|warm|tree-cache|counted|mq-gate|git|flow-canary|signed-export.*)$")
_LANE_KIT_RE = re.compile(r"/srv/opentallas-scratch\d*/claude/([A-Za-z0-9][A-Za-z0-9._-]*)/")
_PRIV_RE = re.compile(r"/kit-wave/[^/]+/[^/]+/private/([A-Za-z0-9][A-Za-z0-9._-]*)/")


def lane_own_kit(kit):
    """-> the owning lane-ish name when KIT is a lane's private kit (kit-wave private/<LANE>/ spec or a lane scratch dir), else ''.  Pure."""
    k = (kit or "").rstrip("/") + "/"
    m = _PRIV_RE.search(k)
    if m:
        return m.group(1)
    m = _LANE_KIT_RE.search(k)
    if m and not SHARED_ROOT_RE.match(m.group(1)):
        return m.group(1)
    return ""


BAD_VERDICTS = ("NO-PROGRESS", "CANCEL-NOW", "DESIGN-FAIL", GRT_STUCK)      # GRT_LABEL is deliberately NOT here: it never cancels; GRT-STUCK does (FLOW-FLEET-R1)


def decide(rows, reported, now, act):
    """annotate rows with `action`; -> units to cancel now.  A scope is cancelled only when every container in it is
    NO-PROGRESS / CANCEL-NOW, it has an ot-heavy scope, and an earlier pass (>= MIN_REPORT_AGE_S ago) already listed each."""
    by_unit = {}
    for r in rows:
        by_unit.setdefault(r["unit"], []).append(r)
    out = []
    for unit, rs in by_unit.items():
        bad = [r for r in rs if r["verdict"] in BAD_VERDICTS]
        if not bad:
            continue
        healthy = [r for r in rs if r["verdict"] not in BAD_VERDICTS]
        own = [lane_own_kit(r.get("kit")) for r in bad if r["verdict"] in LANE_OWN_VERDICTS]
        if own and all(own):
            for r in bad:
                r["action"] = "REPORT-ONLY: lane-own kit (%s decides; never auto-cancelled)" % own[0]
            continue
        standalone = unit is None and all(r.get("lec_only") for r in bad) and not healthy
        if healthy or (unit is None and not standalone):
            for r in bad:
                r["action"] = "REPORT-ONLY: " + ("no ot-heavy scope" if unit is None else "sibling healthy: " + ",".join(h["container"] for h in healthy))
        elif all(r["key"] in reported and now - reported[r["key"]] >= MIN_REPORT_AGE_S for r in bad):
            for r in rs:
                r["action"] = "CANCELLED" if act else "WOULD-CANCEL (report mode)"
            if act:
                out.append(unit)
        else:
            for r in rs:
                r["action"] = "REPORTED (cancel next pass)"
    return out


def scan(now=None, act=False, probe_s=4):
    now = now or time.time()
    hostname = os.environ.get("NOPROG_HOST") or socket.gethostname()
    pol = os.path.join(STATE_DIR, "policy")
    keep = read_lines(os.path.join(pol, "keep.tsv"))
    prot_paths, posts = load_spare_inputs(pol)
    state = load_state()
    del DOCKER_ERR[:]
    ids = sh("docker", "ps", "-q").split()
    insp = json.loads(sh("docker", "inspect", *ids) or "[]") if ids else []
    if DOCKER_ERR:
        print(f"noprog scan: DOCKER FAILED on {hostname}: {DOCKER_ERR[0]} -- this host is NOT watched this pass", file=sys.stderr)
    sc = scopes()
    pid2unit = {p: u for u, ps in sc.items() for p in ps}
    cg0 = {}
    for c in insp:
        cg = cgroup_dir(c["State"]["Pid"])
        cg0[c["Id"]] = (cg, cpu_usec(cg))
    t_probe = time.time()
    rows = []
    for c in insp:
        name = c["Name"].lstrip("/")
        started = time.mktime(time.strptime(c["State"]["StartedAt"][:19], "%Y-%m-%dT%H:%M:%S")) - time.timezone
        mounts = [{"Source": m["Source"], "Destination": m["Destination"]} for m in c.get("Mounts", [])]
        work = work_dir(mounts)
        unit = pid2unit.get(owner_pid(name))
        kit, prio, text, lane = work, "", name, ""
        if unit:
            for p in sc[unit]:
                cmd, cwd = proc_info(p)
                text += " " + cmd[:600] + " " + cwd
                if "run_kit.sh" in cmd and kit == work and cwd and not cwd.rstrip("/").endswith("/ot-jobs"):
                    kit = cwd
                prio = prio or proc_env_prio(p)
                lane = lane or proc_env(p, "OT_LANE")
        th = re.search(r"NUM_CORES=(\d+)", " ".join(c["Config"].get("Cmd") or []))
        log, mt = candidate_logs(work, mounts, name, started)
        kind = stage_kind(log) if log else "other"
        lec_mt = lec_activity(work, started) if work and "lec.py" in " ".join(c["Config"].get("Cmd") or []) else 0.0
        # a flow container with a live OpenROAD stage log is judged on that stage (an async LEC beside it must not hide a stuck
        # placement); LEC activity decides only for a -lec container or once the flow has no running stage log
        if lec_mt and (name.endswith("-lec") or (not (log or "").endswith(".tmp.log") and lec_mt >= mt)):
            kind, mt = "lec", max(mt, lec_mt)
            log = log or os.path.join(work, "lec")
        stage = ("lec" if kind == "lec" else os.path.basename(log).replace(".tmp.log", "").replace(".log", "")) if log else "-"
        cg, cpu_a = cg0[c["Id"]]
        row = {"host": hostname, "container": name, "unit": unit, "type": base_type(name), "kit": kit, "work": work,
               "log": log, "stage": stage, "kind": kind, "age_h": round((now - started) / 3600, 1),
               "threads": int(th[1]) if th else 1, "gb": round(mem_gb(cg), 1), "prio": prio, "lane": lane, "image": c["Config"].get("Image", ""), "_cg": cg, "_cpu0": cpu_a}
        ident = " ".join([name, kit or "", work or "", log or ""])
        k = keep_match(keep, ident)
        if k:
            row.update(verdict="KEEP", why=k.strip()[:120])
        elif is_plan(prio, text):
            row.update(verdict="EXCLUDED", why="plan priority job (bind/LATCHECK/G0/die-proto)")
        elif is_hbm(ident):
            row.update(verdict="CANCEL-NOW", why="HBM is parked")
        elif not log:
            row.update(verdict="NO-DATA", why="no log found")
        else:
            lbirth = max(birth(log) or started, started)
            st = state["jobs"].setdefault(f"{c['Id'][:12]}|{log}", {"samples": []})
            res = extract(kind, read_text(log) if os.path.isfile(log) else "")
            anchors = [(lbirth, 0)]
            for s in st["samples"]:
                if s[0] > anchors[-1][0] and s[1] <= res["n"] and s[1] >= anchors[-1][1]:
                    anchors.append((s[0], s[1]))
            anchors.append((max(mt, anchors[-1][0] + 1), res["n"]))
            log_text = read_text(log) if os.path.isfile(log) else ""
            sw, z0 = step_window(log)
            exact = len(st["samples"]) > 0 and now - st["samples"][0][0] >= sw
            v, why, detail = (judge_activity(mt, started, now, "LEC") if kind == "lec"
                              else judge(res, anchors, now, window=sw, exact=exact, zero_needs_growth=z0))
            v, why = lec_exempt(kind, v, why)
            special = None
            if kind == "grt" and log and grt_repair_phase(log_text):
                row["grt_repair"] = f"{v}: {why}"[:160]      # NOPROG-GRTHOLD-1124: the repair step's own verdict (judge), kept next to the round label
            if kind == "grt" and log:
                rdir = os.path.dirname(log).replace("/logs/", "/reports/")
                rounds_ = grt_rounds(rdir)
                row["grt_flat"] = grt_flat(rounds_)
                if rounds_:
                    row["grt_ovf"] = rounds_[-1][1]       # GRT-LABEL-NOTICE-1122: latest total overflow (hub tracks it over time)
                row["grt_falling"] = grt_falling(rounds_)      # NOPROG-GRTFALL-1124: a falling overflow is progress, never a design cancel
                row["grt_round_s"] = round(grt_round_interval(rdir, rounds_))
                special = judge_grt_rounds(rounds_, log_text)
                if special:
                    # OWNER rule 11-14 deleted the GRT early stop: the round metric is a LABEL (class + trend + NEEDS-LANE), never a cancel
                    special = (GRT_LABEL, f"{special[0]}: {special[1]}", special[2], "GRT-CONGESTION")
            elif kind == "yosys" and log:
                special = synth_mem_stall(read_text(log) if os.path.isfile(log) else "", now - mt)
            if special:
                v, why, detail, row["klass"] = special
            if kind == "grt" and log:
                ev = grt_stuck(rounds_, (now - max(birth(log) or started, started)) / 3600)
                if ev and grt_repair_progress(row):
                    row["grt_stuck_spared"] = "post-route repair is progressing: " + row["grt_repair"][:100]
                elif ev:
                    spare = grt_stuck_spare(dict(row, ident=" ".join([name, kit or "", work or ""]), lane=lane), prot_paths, posts, now)
                    if spare:
                        row["grt_stuck_spared"] = spare[:160]
                    else:
                        v, why, row["klass"] = GRT_STUCK, ev, "GRT-CONGESTION"
                        detail = detail or ""
            try:
                drt_vals = drt_totals(log_text) if kind == "drt" else None
                drc_t = ""
                if drt_vals:
                    rdir_ = os.path.dirname(log).replace("/logs/", "/reports/")
                    reps_ = sorted(glob.glob(os.path.join(rdir_, "5_route_drc.rpt*")), key=lambda q: os.stat(q).st_mtime)
                    drc_t = read_text(reps_[-1], cap=64 * 2**20) if reps_ else ""
                cts_ = None
                if str(stage).startswith("4_1_cts"):
                    cm = CTS_POST_RE.findall(log_text)
                    cts_ = (float(cm[-1][0]), float(cm[-1][1]) if cm[-1][1] else None) if cm else None
                rounds_s = grt_rounds(os.path.dirname(log).replace("/logs/", "/reports/")) if kind == "grt" else None
                row["smell"] = smell_triggers(kind, stage, (now - mt) / 3600, (now - lbirth) / 3600, rounds_s, drt_vals, drc_t, log_text if kind == "gpl" else "", cts_)
                if drt_vals:
                    p3 = drt_plateau3(drt_vals)         # PLATEAU-ACT 11-25: the progress measure (within 5 % over 3 iterations, or rising)
                    if p3:
                        row["plateau3"], row["plateau3_kind"] = p3
                    p5 = drt_plateau5(drt_vals)
                    if p5 is not None:
                        row["plateau5"] = p5
                        if p5 > PLATEAU_SMELL_MIN:
                            row["smell"].append(("DRT", f"DRT plateau: 5 iterations < 2 % change at {p5:g} violations"))
            except (OSError, ValueError, IndexError):
                row["smell"] = []
            if kind == "drt" and log:
                pev = drt_plateau_evidence(drt_totals(log_text))
                if pev:
                    row.update(plateau=pev, plateau_class=DRT_PLATEAU, drc_summary=latest_drc_summary(log)[:700])
            elif kind == "other" and log:
                pev = hold_stall_evidence(stage, res, v, why, detail, anchors, now, sw if exact else sw * EST_MARGIN)
                if pev:
                    row.update(plateau=pev, plateau_class=HOLD_STALL)
            if kind == "lec" and now - started > LEC_MAX_S:
                # COORD 11-14: LEC is advisory under R-MINIMAL.  A LEC-only job (the route result exists) older than 24 h goes,
                # alive or not; a LEC whose route stage has not produced its result is never cancelled here.
                cmd_text = " ".join(c["Config"].get("Cmd") or [])
                row["lec_only"] = "lec.py" in cmd_text and "make DESIGN_CONFIG" not in cmd_text      # a standalone LEC container: no flow behind it
                if row["lec_only"] or route_done(work):
                    v, why = "CANCEL-NOW", "LEC >24h, advisory"
                else:
                    v, why = "PROGRESS", "LEC >24h but the route result is not there yet: kept"
            row.update(verdict=v, why=why, detail=detail, metric=res["name"] or "growth", stage_age_h=round((now - lbirth) / 3600, 1),
                       log_age_h=round((now - mt) / 3600, 1), lines=res["n"])
            st["samples"].append([now, res["n"], cpu_a])
            st["samples"] = st["samples"][-MAX_SAMPLES:]
            st["seen"] = now
        row["key"] = f"{name}|{kit}"
        row["ident"] = ident[:400]
        if row["verdict"] not in ("KEEP", "EXCLUDED") and row["age_h"] > UNSIGNABLE_MIN_AGE_H:
            # a 4_1_cts.json under the kit / work dir written by THIS container; the verdict is only a label here (the HUB cancels, host scans never do)
            ms = latest_setup_ex([kit, work], started)
            ev = unsignable_evidence(ident, prio, kind, row["age_h"], ms)
            if ms:
                row["setup_ps"] = ms[0]
            if not ev and lane and grt_flat_exempt(dict(row, ident=ident)).startswith("OT_LANE"):
                ev = grt_unsignable_evidence(dict(row, ident=ident, prio=prio))      # wave kits: grt_flat_pass cancels them through cancel-rows
            if not ev and ECO_RE.search(ident) and not PROOF_RE.search(ident) and not HOLD_ONLY_RE.search(ident) and prio not in ("plan", "proof") and not is_hbm(ident):
                ev = eco_flat_evidence(eco_measurements(kit, work), row["age_h"])     # LAUNCH-GUARD 11-23: an ECO that stopped improving
            if ev and row["verdict"] not in BAD_VERDICTS:
                row.update(verdict=UNSIGNABLE, why=ev, action="UNSIGNABLE (hub: ot-run --cancel --reason design on the first pass unless KEEP)")
        rows.append(row)
    time.sleep(max(0.0, probe_s - (time.time() - t_probe)))
    t1 = time.time()
    for r in rows:
        cg, c0 = r.pop("_cg", None), r.pop("_cpu0", None)
        if cg and c0 is not None:
            c1 = cpu_usec(cg)
            if c1 is not None:
                r["cores_now"] = round((c1 - c0) / 1e6 / max(t1 - t_probe, 1e-3), 2)
        if r["verdict"] == "NO-PROGRESS" and r.get("cores_now") is not None and r["cores_now"] < 0.05:
            r["why"] += " (cpu idle: hung)"
    for r in rows:
        if r.get("smell") and smell_exempt(r):
            r["smell"] = []
    try:
        vis_pass(rows, state, STATE_DIR, now)
    except Exception as e:      # advisory render: never stops the scan
        print(f"noprog vis pass failed: {e!r}", file=sys.stderr)
    sp, sn = smell_pending_write(rows, hostname)
    if sn and not os.path.exists(os.path.join(COORD, "bin/post.sh")):
        print(f"noprog smell: {sn} kit(s) smell on {hostname}; the hub is not reachable from this host, fallback file {sp}", file=sys.stderr)
    reported = state.setdefault("reported", {})
    cancel_units = decide(rows, reported, now, act)
    actions = [do_cancel(u, [r for r in rows if r["unit"] == u and r["verdict"] in BAD_VERDICTS] if u is None else [r for r in rows if r["unit"] == u], now) for u in cancel_units] if act else []
    for r in rows:
        if r["verdict"] in BAD_VERDICTS and not r.get("action", "").startswith("REPORT-ONLY"):
            reported.setdefault(r["key"], now)
    live = {r["key"] for r in rows}
    for k in list(reported):
        if k not in live and now - reported[k] > 86400:
            del reported[k]
    for sk in list(state["jobs"]):
        if now - state["jobs"][sk].get("seen", 0) > 3 * 86400:
            del state["jobs"][sk]
    save_json(os.path.join(STATE_DIR, "state.json"), state)
    save_json(os.path.join(STATE_DIR, "report.json"), {"host": hostname, "t": now, "rows": rows, "actions": actions})
    if actions:
        with open(os.path.join(STATE_DIR, "actions.jsonl"), "a") as f:
            for a in actions:
                f.write(json.dumps(a, sort_keys=True) + "\n")
    return rows, actions


def do_cancel(unit, rs, now):
    """ot-heavy-stop for the scope: --match <kit dir> after a dry run that hits exactly this unit, else --unit"""
    kit = rs[0]["kit"] or ""
    if unit is None:        # standalone LEC container (no ot-heavy scope): docker stop of that exact container after a cmdline check
        res = ""
        for r in rs:
            top = sh("docker", "top", r["container"], "-eo", "args", timeout=30)
            if "/work/lec.py" in top and "make DESIGN_CONFIG" not in top:
                res += sh("docker", "stop", "-t", "20", r["container"], timeout=120)
        return {"t": now, "host": rs[0]["host"], "unit": "-", "how": "docker stop (lec.py only)", "result": res.strip()[-300:],
                "containers": [r["container"] for r in rs], "type": rs[0]["type"], "stage": rs[0]["stage"], "metric": rs[0].get("detail", ""),
                "kit": kit, "why": rs[0]["why"], "verdict": rs[0]["verdict"], "gb": round(sum(r["gb"] for r in rs), 1),
                "cores": sum(r["threads"] for r in rs), "cores_busy": round(sum(r.get("cores_now") or 0 for r in rs), 1)}
    out = sh("ot-heavy-stop", "--dry-run", "--match", kit, timeout=120) if kit else ""
    args = ["--match", kit] if kit and re.findall(r"ot-heavy-stop: (oth-[\w-]+):", out) == [unit] else ["--unit", unit]
    res = sh("ot-heavy-stop", *args, timeout=300)
    return {"t": now, "host": rs[0]["host"], "unit": unit, "how": " ".join(args), "result": res.strip()[-300:],
            "containers": [r["container"] for r in rs], "type": rs[0]["type"], "stage": rs[0]["stage"],
            "metric": rs[0].get("detail", ""), "kit": kit, "why": rs[0]["why"], "verdict": rs[0]["verdict"], "class": rs[0].get("klass", ""),
            "gb": round(sum(r["gb"] for r in rs), 1), "cores": sum(r["threads"] for r in rs),
            "cores_busy": round(sum(r.get("cores_now") or 0 for r in rs), 1)}


# ---------------------------------------------------------------- hub
ORDER = {UNSIGNABLE: 0, GRT_STUCK: 0, "GRT-LABEL": 1, "DESIGN-FAIL": 0, "NO-PROGRESS": 0, "CANCEL-NOW": 0, "NO-DATA": 2, "YOUNG": 2, "EXCLUDED": 3, "KEEP": 3, "PROGRESS": 4}


def md_table(reports):
    rows = [r for rep in reports for r in rep["rows"]]
    rows.sort(key=lambda r: (ORDER.get(r["verdict"], 5), r["host"], r["container"]))
    out = "| host | container | type | stage | age h | metric trend | verdict | action |\n|---|---|---|---|---|---|---|---|\n"
    for r in rows:
        out += (f"| {r['host']} | {r['container']} | {r['type']} | {r['stage']} | {r['age_h']} | {(r.get('detail') or '')[:120]} | "
                f"{r['verdict']}: {r.get('why', '')[:80]} | {r.get('action', '')[:50]} |\n")
    return out, rows


def run_host(host, cmd, inp=None, timeout=60):
    if host == HUB or host == socket.gethostname():
        return subprocess.run(["bash", "-c", cmd], input=inp, capture_output=True, text=True, timeout=timeout)
    return subprocess.run(["ssh", "-o", "ControlPath=none", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", host, cmd],
                          input=inp, capture_output=True, text=True, timeout=timeout)


def action_tsv(action):
    return "\t".join(str(x) for x in [
        time.strftime("%F %T", time.localtime(action["t"])), action["host"], action["type"], action["stage"],
        action["metric"].replace("\t", " "), action["kit"], ",".join(action["containers"]), action["why"],
        action["gb"], action["cores"], action["cores_busy"],
    ])


def hub(now=None, post=True):
    now = now or time.time()
    keep = read_lines(os.path.join(COORD, "lanes/NOPROG-KEEP.tsv"))
    prot_all = []
    for pf in ("lanes/PROTECTED-DBS.txt", "PROTECTED-DBS.txt"):
        prot_all += read_lines(os.path.join(COORD, pf))
    posts = [f"{t:.0f}\t{l}\t{x[:2000]}" for t, l, x in recent_posts(COORD, now)]
    for h in HOSTS:
        for fname, lines in (("keep.tsv", keep), ("protected.tsv", protected_rows("\n".join(prot_all), h)), ("posts_recent.tsv", posts)):
            try:
                d = f"{STATE_DIR}/policy"
                run_host(h, f"mkdir -p {d} && cat > {d}/{fname}.new && mv {d}/{fname}.new {d}/{fname}", inp="".join(l + "\n" for l in lines))
            except (subprocess.SubprocessError, OSError):
                pass
    reports, missing = [], []
    for h in HOSTS:
        try:
            rep = json.loads(run_host(h, f"cat {STATE_DIR}/report.json", timeout=40).stdout)
            for r in rep["rows"]:
                r["host"] = h
            rep["host"] = h
            reports.append(rep)
        except (subprocess.SubprocessError, OSError, ValueError):
            missing.append(h)
    table, rows = md_table(reports)
    stamp = time.strftime("%Y-%m-%d %H:%M PST", time.localtime(now))
    flagged = [r for r in rows if r["verdict"] in ("NO-PROGRESS", "CANCEL-NOW", "DESIGN-FAIL", GRT_LABEL, UNSIGNABLE, GRT_STUCK)]
    counts = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    tpath = os.path.join(COORD, "lanes/NOPROG-TABLE.md")
    open(tpath, "w").write(f"# NOPROG-TABLE (NOPROG-WATCHDOG, generated {stamp})\n\nWindow {WINDOW_S // 3600} h, improvement >= "
                           f"{int(MIN_IMPROVE * 100)} % from best. Verdict counts: {counts}. Hosts without report: {missing or 'none'}.\n\n" + table)
    seen_path = os.path.join(STATE_DIR, "hub_seen.json")
    try:
        seen = json.load(open(seen_path))
    except (OSError, ValueError):
        seen = {"offset": {}, "posted": [], "table_sig": ""}
    new_actions = []
    offsets = dict(seen["offset"])
    for h in HOSTS:
        try:
            ledger = run_host(h, f"cat {STATE_DIR}/actions.jsonl 2>/dev/null", timeout=40)
        except (subprocess.SubprocessError, OSError):
            continue
        if ledger.returncode:
            continue
        lines = [line for line in ledger.stdout.splitlines() if line.strip()]
        for line in lines[offsets.get(h, 0):]:
            try:
                a = json.loads(line)
                a["host"] = h
                new_actions.append(a)
            except ValueError:
                pass
        offsets[h] = len(lines)
    files = ["lanes/NOPROG-TABLE.md"]
    qlines = []
    sig = json.dumps(sorted({f"{r['host']}|{r['container']}|{r['verdict']}" for r in flagged}))
    if sig != seen.get("table_sig") and flagged:
        qlines.append(f"- {stamp} STATE [NOPROG-WATCHDOG -> COORD] NO-PROGRESS table: {len(flagged)} flagged of {len(rows)} containers {counts}; full table lanes/NOPROG-TABLE.md; flagged: "
                      + "; ".join(f"{r['host']} {r['type']} {r['stage']} [{r['verdict']}: {(r.get('why') or '')[:60]}] {r.get('action', '')[:28]}" for r in flagged[:40]))
    seen["table_sig"] = sig
    labelled = set(seen.get("labelled", []))
    for r in rows:
        if r["verdict"] == GRT_LABEL and r["type"] not in labelled:
            labelled.add(r["type"])
            qlines.append(f"- {stamp} NEEDS-LANE [NOPROG-WATCHDOG -> COORD] {r['type']}: DESIGN-FAIL class GRT-CONGESTION on {r['host']} at {r['stage']} "
                          f"({(r.get('why') or '')[:90]}; {(r.get('detail') or '')[:160]}). Label only, the job keeps running; no unchanged retry.")
    seen["labelled"] = sorted(labelled)
    told = seen.setdefault("lane_own_told", {})
    for r in rows:
        a_ = r.get("action") or ""
        if r["verdict"] in LANE_OWN_VERDICTS and a_.startswith("REPORT-ONLY: lane-own kit"):
            k = f"{r['host']}|{r.get('key')}"
            if k in told:
                continue
            told[k] = now
            owner = owner_of([r])
            txt = (f"NOTICE [NOPROG-WATCHDOG -> {owner}] {r['verdict']} on your own kit {r.get('kit')} ({r['host']} {r.get('unit')} {r['stage']}, job {r['age_h']} h): "
                   f"{(r.get('why') or '')[:160]}; {(r.get('detail') or '')[:120]}. Not cancelled (lane-own kit, COORD 11-22): cancel it yourself with ot-run --cancel "
                   f"<unit> if it cannot sign, or post KEEP {r.get('unit')} <why>.")
            qlines.append(f"- {stamp} {txt}")
            if post and owner != "COORD":
                _post("NOPROG-WATCHDOG", txt)
    for k in [k for k, t in told.items() if now - t > 3 * 86400]:
        del told[k]
    done = set(seen["posted"])
    for a in new_actions:
        if a["type"] in done:
            continue
        done.add(a["type"])
        qlines.append(f"- {stamp} NEEDS-LANE [NOPROG-WATCHDOG -> COORD] {a['type']}: cancelled {a.get('verdict') or 'NO-PROGRESS'}{(' class ' + a['class']) if a.get('class') else ''} on {a['host']} at {a['stage']} ({a['why'][:90]}; {a['metric'][:140]}); "
                      f"kit kept at {a['kit']}; freed {a['gb']} GB / {a['cores']} cores. "
                      + ("DESIGN failure (congestion/synthesis): do not retry unchanged." if a.get("class") else "Needs a structural fix, not a retry."))
    seen["posted"] = sorted(done)
    umode, ucand, udone = unsignable_pass(rows, seen, now, post=post)
    if udone:
        files.append("lanes/CANCEL-UNSIGNABLE-1120.tsv")
    gmode, gcand, gdone = grt_flat_pass(rows, seen, now, post=post)
    ddone = design_fail_pass(rows, seen, now, post=post)
    try:
        smode, sfired = smell_pass(rows, seen, now, post=post, render=lambda r, t: host_smell_render(dict(r, smell=[(c, x) for c, x in r["smell"] if x in t])) if post else ("dry", ""))
        if sfired:
            files.append("lanes/SMELL.tsv")
    except Exception as e:      # the smell is advisory: it must never stop the cancel passes or the table commit
        print(f"noprog smell pass failed: {e!r}", file=sys.stderr)
    grt_label_notice_pass(rows, seen, now, post=post)
    if gdone:
        files.append("lanes/CANCEL-GRT-FLAT.tsv")
    if ddone:
        files.append("lanes/CANCEL-DESIGN-FAIL.tsv")
    try:
        plateau_route_pass(rows, seen, now, post=post)
    except Exception as e:
        print(f"noprog plateau route failed: {e!r}", file=sys.stderr)
    try:
        if plateau_act_pass(rows, seen, now, post=post):
            files.append("lanes/PLATEAU-ACT.tsv")
    except Exception as e:      # the act pass must never stop the other passes or the table commit
        print(f"noprog plateau act failed: {e!r}", file=sys.stderr)
    if vis_queue_append(rows, now, post):
        files.append("lanes/VIS-QUEUE.tsv")
    try:
        if (vis_status_sync() + vis_type_backfill() + vis_sta_sync(post=post)) and "lanes/VIS-QUEUE.tsv" not in files:
            files.append("lanes/VIS-QUEUE.tsv")
    except Exception as e:
        print(f"noprog vis status sync failed: {e!r}", file=sys.stderr)
    if qlines:
        with open(os.path.join(COORD, "lanes/COORD-REVIEW-QUEUE.md"), "a") as f:
            f.write("\n".join(qlines) + "\n")
        files.append("lanes/COORD-REVIEW-QUEUE.md")
    # Save watchdog decisions before publishing so a commit failure cannot repeat a stop.
    # Advance ledger offsets only after the exact receipt rows are in the pushed branch.
    save_json(seen_path, seen)
    action_file = "lanes/NOPROG-ACTIONS.tsv"
    action_rows = [action_tsv(a) for a in new_actions]
    if action_rows:
        path = os.path.join(COORD, action_file)
        known = set(read_lines(path))
        with open(path, "a") as f:
            if not known:
                f.write("time\thost\ttype\tstage\tlast_metric\tkit_dir\tcontainers\twhy\tgb_freed\tcores_reserved\tcores_busy\n")
            for row in dict.fromkeys(action_rows):
                if row not in known:
                    f.write(row + "\n")
        files.append(action_file)
    if post:
        result = subprocess.run(["bash", os.path.join(COORD, "bin/coord-commit.sh"),
                                 f"NOPROG-WATCHDOG {stamp}: {len(flagged)} flagged, {len(new_actions)} no-progress + {len(udone)} unsignable + {len(gdone)} grt-flat + {len(ddone)} design-fail cancelled", *files],
                                capture_output=True, text=True, timeout=600)
        if action_rows:
            pushed = subprocess.run(["git", "show", f"origin/coord/state:{action_file}"], cwd=COORD,
                                    capture_output=True, text=True, timeout=30)
            if pushed.returncode or not set(action_rows).issubset(pushed.stdout.splitlines()):
                print("noprog hub: action receipts not published; retaining source offsets", file=sys.stderr)
                return reports, new_actions
        elif result.returncode:
            return reports, new_actions
        seen["offset"] = offsets
        save_json(seen_path, seen)
    return reports, new_actions


def plan_of(kit):
    m = re.search(r"/kit-wave/([^/]+)/([^/]+)/", kit or "")
    return f"{m.group(1)} {m.group(2)}" if m else "-"


def unsignable_mode(seen=None, now=None):
    """act | report.  FLOW-OPS-0900 (owner 11-21: 'the UNSIGNABLE watchdog acts'): act by default.  The off switch is a COORD file, lanes/UNSIGNABLE-WATCHDOG.off
    (one line why; coord-commit.sh), or NOPROG_UNSIGNABLE_ACT=report.  The old NOPROG_UNSIGNABLE_MODE=report (11-20 drop-in, set while the cancel read stale post-CTS numbers and had no
    owner notice) governed the report-hour path this replaced and is no longer read: every cancel now has a NOTICE to the owning lane and a 30 min KEEP window first."""
    if os.environ.get("NOPROG_UNSIGNABLE_ACT") == "report" or os.path.exists(os.path.join(COORD, "lanes/UNSIGNABLE-WATCHDOG.off")):
        return "report"
    return "act"


def ot_run_cancel(unit, run=subprocess.run):
    """the only cancel path: ot-run --cancel <exact unit>.  -> (rc, last output line)"""
    exe = os.environ.get("OT_RUN_BIN") or os.path.expanduser("~/.local/bin/ot-run")
    r = run([exe, "--cancel", unit, "--reason", "design"], capture_output=True, text=True, timeout=900)      # LAUNCH-GUARD 11-23: every watchdog cancel here is a design verdict
    lines = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()
    return r.returncode, (lines[-1][:200] if lines else "no output")


KEEP_POST_RE = re.compile(r"\bKEEP\s+(oth-[A-Za-z0-9_.-]+)")


def keep_posts(coord=None):
    """-> {unit} named by a 'KEEP <unit>' line in any lanes/posts/*.md (or lanes/NOPROG-KEEP.tsv)"""
    coord = coord or COORD
    out = set()
    for p in glob.glob(os.path.join(coord, "lanes/posts/*.md")) + [os.path.join(coord, "lanes/NOPROG-KEEP.tsv")]:
        try:
            out.update(KEEP_POST_RE.findall(read_text(p)))
        except OSError:
            pass
    return out


def decide_only(ident, coord=None):
    """-> lane that decides this job (never auto-cancelled), else ''"""
    pats = list(DECIDE_ONLY)
    for l in read_lines(os.path.join(coord or COORD, "lanes/UNSIGNABLE-DECIDE.tsv")):
        f = l.split("\t")
        if len(f) >= 2 and not l.startswith("#"):
            pats.append((f[0], f[1].strip()))
    for pat, lane in pats:
        try:
            if re.search(pat, ident or ""):
                return lane
        except re.error:
            continue
    return ""


def functional_bugs(coord=None):
    """lanes/UNSIGNABLE-FUNCTIONAL.tsv: <unit, kit or type substring><TAB><evidence>[<TAB>lane] = a lane-declared functional bug (owner rule: a job with a functional bug cannot sign)."""
    out = []
    for l in read_lines(os.path.join(coord or COORD, "lanes/UNSIGNABLE-FUNCTIONAL.tsv")):
        f = l.split("\t")
        if len(f) >= 2 and f[0].strip() and not l.startswith("#"):
            out.append((f[0].strip(), f[1].strip()))
    return out


LANE_DIR_RE = re.compile(r"/srv/opentallas-scratch\d*/claude/([A-Za-z0-9][A-Za-z0-9._-]*)/")


def lane_from_path(path, coord=None):
    """-> the lane whose post file matches the lane dir of a /srv/opentallas-scratch*/claude/<lane>/ path (case folded), else ''"""
    m = LANE_DIR_RE.search(path or "")
    if not m:
        return ""
    want = m.group(1).lower()
    try:
        for f in os.listdir(os.path.join(coord or COORD, "lanes/posts")):
            if f.endswith(".md") and f[:-3].lower() == want:
                return f[:-3]
    except OSError:
        pass
    return ""


def _private_lane(path, coord=None):
    m = _PRIV_RE.search((path or "").rstrip("/") + "/")
    if not m:
        return ""
    want = m.group(1).lower()
    try:
        for f in os.listdir(os.path.join(coord or COORD, "lanes/posts")):
            if f.endswith(".md") and f[:-3].lower() == want:
                return f[:-3]
    except OSError:
        pass
    return m.group(1)


def legacy_owner_of(rs):
    """the job's OT_LANE, else the lane of its tree / kit path (most units carry no OT_LANE), else COORD (wave jobs)"""
    return (next((r["lane"] for r in rs if r.get("lane")), "") or next((l for r in rs for l in [_private_lane(r.get("kit") or ""), lane_from_path(r.get("kit") or ""), lane_from_path(r.get("ident") or "")] if l), "")
            or "COORD")


_FILE_CACHE = {}


def _cached_file(path, loader):
    """loader(path) cached by (path, mtime): the sweep table is read by every notice of a pass"""
    try:
        mt = os.stat(path).st_mtime
    except OSError:
        return loader(None)
    c = _FILE_CACHE.get(path)
    if not c or c[0] != mt:
        c = _FILE_CACHE[path] = (mt, loader(path))
    return c[1]


def stood_down_lanes(coord=None):
    """lane names whose lanes/LANE-STATUS.tsv row says stood-down"""
    def load(path):
        out = set()
        if path:
            for l in open(path, errors="replace").read().splitlines():
                f = l.split("\t")
                if len(f) >= 2 and f[1].startswith("stood-down"):
                    out.add(f[0])
        return out
    return _cached_file(os.path.join(coord or COORD, "lanes/LANE-STATUS.tsv"), load)


def owner_of(rs):
    """FLEET-WATCH F-15 (COORD FLOW-0930, PLATEAU-ACT 11-25): THE routing path of every noprog notice.  The live OWNERS-SWEEP fresh_owner of the job's (die, type); else the job's own lane (OT_LANE /
    tree path) unless that lane is stood down; else the die's ALLFIX lane; COORD only for a job of no known die."""
    own = legacy_owner_of(rs)
    r0 = rs[0] if rs else {}
    ident = " ".join(str(r0.get(x) or "") for x in ("container", "kit", "work", "ident"))
    tag = DIE_TAG.get(die_of(ident), "")
    sw = owners_sweep()
    if tag and sw:
        lane, state = route_owner(tag, str(r0.get("type") or ""), sw, "")
        if state == "alive":
            return lane
    if own and own != "COORD" and own not in stood_down_lanes():
        return own
    return ALLFIX_LANE.get(tag) or own


def _post(lane_from, txt):
    try:
        subprocess.run(["bash", os.path.join(COORD, "bin/post.sh"), lane_from, txt], capture_output=True, text=True, timeout=300)
        return True
    except (subprocess.SubprocessError, OSError):
        return False


def write_cancel_marks(kits, who, why, now):
    """FLOW-OPS-1300 (FABLE-FLOW-1240 b): the explicit terminal reason of a watchdog cancel, written BEFORE the cancel to autopilot/cancel_marks.tsv (t, kit dir, who, why).
    autopilot.marked_cancel() reads it when the job ends rc 143, so the queue job is CANCELLED with 'CANCEL-UNSIGNABLE: <evidence>' and kit_wave.follow_queue stops that
    plan block -- a bare 143 with no record had been classed CRASH infra-stopped, read as an OOM and resubmitted with place memory x1.5.  -> lines written"""
    path = os.path.join(COORD, "autopilot", "cancel_marks.tsv")
    clean = lambda x: str(x).replace("\t", " ").replace("\n", " ")
    lines = [f"{now:.0f}\t{k.rstrip('/')}\t{clean(who)}\t{clean(why)[:300]}\n" for k in dict.fromkeys(k for k in kits if k)]
    if not lines:
        return 0
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a") as f:
            f.writelines(lines)
    except OSError:
        return 0
    return len(lines)


def unsignable_pass(rows, seen, now, post=True, cancel=ot_run_cancel):
    """HUB half of the rule (FLOW-OPS-0900, owner 11-21).  Per unit (host|unit) whose containers are ALL unsignable (UNSIGNABLE verdict, or a lane-declared functional bug on a job > 3 h):
      1. first listed: state keeps the first-listed time per unit (survives a changing list; forgotten only when unseen 6 h);
      2. NOTICE post to the owning lane (the job's OT_LANE, COORD for wave jobs) with the exact unit, evidence and the cancel time;
         units matched by DECIDE_ONLY / lanes/UNSIGNABLE-DECIDE.tsv get a DECISION post to the named lane instead and are never cancelled here;
      3. >= 30 min after the NOTICE, unless a post says 'KEEP <unit>': ot-run --cancel <unit>, evidence row in lanes/CANCEL-UNSIGNABLE-1120.tsv, CANCELLED post to the owner.
    -> (mode, candidate rows, cancelled [dict])"""
    mode = unsignable_mode()
    poster = os.environ.get("NOPROG_POST_LANE", "FLEET-WATCH-1015")
    stamp = time.strftime("%Y-%m-%d %H:%M PST", time.localtime(now))
    fb = functional_bugs()
    units = {}
    for r in rows:
        if r.get("unit"):
            units.setdefault((r["host"], r["unit"]), []).append(r)
    cand = []
    for (h, u), rs in units.items():
        fev = ""
        for m, e in fb:
            if any(m in " ".join([u, r.get("type", ""), r.get("kit") or "", r.get("ident", "")]) for r in rs):
                fev = f"functional bug declared in lanes/UNSIGNABLE-FUNCTIONAL.tsv: {e}"
        if fev:
            ok = all(r.get("age_h", 0) > UNSIGNABLE_MIN_AGE_H and r.get("verdict") not in ("KEEP", "EXCLUDED") and not unsignable_exempt(r.get("ident", ""), r.get("prio", ""), r.get("kind", "")) for r in rs)
            if ok:
                for r in rs:
                    r.update(verdict=UNSIGNABLE, why=fev)
        if all(r["verdict"] == UNSIGNABLE for r in rs):
            cand.append(((h, u), rs))
    st = seen.setdefault("unsig_units", {})
    for (h, u), rs in cand:
        e = st.setdefault(f"{h}|{u}", {"first": now})
        e.update(last=now, type=rs[0].get("type", ""), evidence=rs[0].get("why", ""), owner=owner_of(rs))
    for k in list(st):
        if now - st[k].get("last", now) > UNSIGNABLE_FORGET_S:
            del st[k]
    keeps = keep_posts()
    notices, decisions, done = {}, {}, []
    for (h, u), rs in sorted(cand):
        k = f"{h}|{u}"
        e = st[k]
        if e.get("done"):
            continue
        ident = " ".join([rs[0].get("container", ""), rs[0].get("ident", ""), rs[0].get("kit") or ""])
        dl = decide_only(ident)
        line = f"{h} {u} {rs[0].get('type', '')} ({e['evidence'][:160]}; {sum(r.get('gb', 0) for r in rs):.0f} GB, listed since {time.strftime('%H:%M', time.localtime(e['first']))})"
        if dl:
            if not e.get("decision_posted"):
                decisions.setdefault(dl, []).append(line)
                e["decision_posted"] = now
            continue
        if u in keeps:
            e["kept"] = e.get("kept") or now
            continue
        if not e.get("notice"):
            if mode == "act" and post:
                if UNSIGNABLE_GRACE_S > 0:
                    notices.setdefault(e["owner"], []).append(line)
                e["notice"] = now
            elif not e.get("reported"):
                notices.setdefault(e["owner"], []).append(line)
                e["reported"] = now
            if mode != "act" or not post or UNSIGNABLE_GRACE_S > 0:
                continue
        if mode != "act" or now - e["notice"] < UNSIGNABLE_GRACE_S:
            continue
        first = rs[0]
        write_cancel_marks([r.get("kit") for r in rs], "UNSIGNABLE watchdog", f"CANCEL-UNSIGNABLE: {first.get('why', '')}", now)
        rc, out = cancel(u)
        rec = {"t": now, "unit": u, "host": h, "type": first["type"], "plan": plan_of(first.get("kit")), "evidence": f"{first['why']}; " + (f"NOTICE to {e['owner']} {time.strftime('%H:%M', time.localtime(e['notice']))}, no KEEP in {UNSIGNABLE_GRACE_S // 60} min" if UNSIGNABLE_GRACE_S > 0 else "first-pass cancel (no KEEP post)"),
               "freed_gb": round(sum(r.get("gb", 0) for r in rs), 1), "class": "UNSIGNABLE-SETUP" if "setup" in first["why"] else "UNSIGNABLE", "cancel_method": f"ot-run --cancel {u} rc={rc}: {out}",
               "owner": e["owner"]}
        done.append(rec)
        e["done"] = now
        seen.setdefault("unsig_cancelled", []).append(k)
    if post:
        for owner, ls in sorted(notices.items()):
            if mode == "act":
                txt = (f"NOTICE [{poster} -> {owner}] UNSIGNABLE watchdog (owner rule 11-20, >3 h and measured unable to sign): {len(ls)} job(s): " + "; ".join(ls[:40])
                       + f". Each is cancelled by ot-run --cancel <unit> {UNSIGNABLE_GRACE_S // 60} min after this post unless {owner} posts 'KEEP <unit> <why>' (bash ~/coord/bin/post.sh {owner} \"KEEP oth-... why\").")
            else:
                txt = f"STATE [{poster} -> {owner}] UNSIGNABLE watchdog (report mode, lanes/UNSIGNABLE-WATCHDOG.off): {len(ls)} job(s) would be noticed: " + "; ".join(ls[:40])
            _post(poster, txt)
        for dl, ls in sorted(decisions.items()):
            _post(poster, f"DECISION [{poster} -> {dl}] UNSIGNABLE watchdog: {len(ls)} job(s) measured unable to sign that the watchdog never cancels by itself (decide-only list): " + "; ".join(ls[:40])
                  + f". {dl}: decide; cancel with ot-run --cancel <unit> yourself, or post 'KEEP <unit> <why>'.")
        by_owner = {}
        for d in done:
            by_owner.setdefault(d["owner"], []).append(d)
        for owner, ds in sorted(by_owner.items()):
            _post(poster, f"CANCELLED [{poster} -> {owner}] UNSIGNABLE watchdog cancelled {len(ds)} job(s) (>3 h, measured unable to sign; ot-run --cancel --reason design): "
                  + "; ".join(f"{d['host']} {d['unit']} {d['type']} ({d['evidence'][:120]}; {d['cancel_method'][-80:]})" for d in ds) + ". Evidence lanes/CANCEL-UNSIGNABLE-1120.tsv; kit dirs kept.")
    if done:
        path = os.path.join(COORD, "lanes/CANCEL-UNSIGNABLE-1120.tsv")
        with open(path, "a") as f:
            for d in done:
                f.write("\t".join(str(d[k]).replace("\t", " ").replace("\n", " ") for k in ("unit", "host", "type", "plan", "evidence", "freed_gb", "class", "cancel_method")) + "\n")
    return mode, [r for _k, rs in cand for r in rs], done


# ---------------------------------------------------------------- GRT flat overflow (FLEET-WATCH-2000, owner rule 11-20)
# A wave kit running > 3 h at GRT whose overflow has been flat for >= 5 iterations, or that carries the NOPROG design-fail label (GRT-LABEL), cannot sign: it is cancelled through the
# wave's own cancel path (kit_wave.py cancel-rows --event --attempt: the row becomes CANCELLED class PLAN with a structural stop, so the wave does not retry it; a bare ot-run --cancel was
# relaunched as INFRA[stopped]) and recorded as class PLAN design:grt_flat_overflow for the die owner.  Exempt: OT_LANE jobs, private kits (not under kit-wave/<die>/<event>/items/<item>/attempt_N),
# re-sign and ECO jobs.  Listed in an earlier pass (MIN_REPORT_AGE_S) first, like every cancel here.
GRT_FLAT_CLASS = "design:grt_flat_overflow"
GRT_FLAT_MIN_AGE_H = 3.0
WAVE_KIT = re.compile(r"/kit-wave/([^/]+)/([^/]+)/items/([^/]+)/attempt_(\d+)")


def wave_identity(kit):
    """-> (die, event, item, attempt) of a wave kit path, else None"""
    m = WAVE_KIT.search(kit or "")
    return m.groups() if m else None


def grt_flat_exempt(r):
    ident = " ".join(str(r.get(k) or "") for k in ("container", "type", "kit", "work", "ident")).lower()
    if r.get("lane"):
        return "OT_LANE job (" + r["lane"] + ")"
    if wave_identity(r.get("kit")) is None:
        return "private kit (not a wave kit)"
    if "resign" in ident or "re-sign" in ident:
        return "re-sign"
    if "eco_" in ident or "-eco" in ident or "/eco" in ident:
        return "ECO"
    return ""


def grt_flat_candidate(r):
    """-> evidence string or ''"""
    if r.get("kind") != "grt" or r.get("age_h", 0) <= GRT_FLAT_MIN_AGE_H or grt_flat_exempt(r):
        return ""
    if grt_repair_progress(r):
        return ""                        # NOPROG-GRTHOLD-1124: routing is done, the repair step is progressing
    if r.get("grt_flat"):
        return r["grt_flat"]
    if r.get("verdict") == GRT_LABEL and not r.get("grt_falling"):     # NOPROG-GRTFALL-1124: a falling overflow is progress
        return "NOPROG label " + str(r.get("why") or "") + "; " + str(r.get("detail") or "")
    return ""


def wave_cancel_rows(ident, why, run=subprocess.run):
    """the wave's own cancel path (hub only).  -> (rc, last output line)"""
    die, event, item, attempt = ident
    exe = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kit_wave.py")
    r = run([sys.executable, "-I", exe, "cancel-rows", "--die", die, "--item", item, "--event", event, "--attempt", attempt, "--owner", "die-owner",
             "--verdict", "STRUCTURAL", "--cls", "PLAN", "--why", why], capture_output=True, text=True, timeout=900)
    lines = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()
    return r.returncode, (lines[-1][:200] if lines else "no output")


def grt_flat_pass(rows, seen, now, post=True, cancel=wave_cancel_rows):
    """HUB: lists candidates (posts once per key) and, in act mode (NOPROG_GRTFLAT_MODE=report forces report), cancels each wave attempt whose containers were all listed >= MIN_REPORT_AGE_S ago.
    Writes lanes/CANCEL-GRT-FLAT.tsv.  -> (mode, candidates, cancelled [dict])"""
    cand = {}
    for r in rows:
        ev = grt_flat_candidate(r)
        if ev:
            cand[f"{r['host']}|{r['key']}"] = (r, ev)
    listed = seen.setdefault("gf_listed", {})
    for k in cand:
        listed.setdefault(k, now)
    for k in list(listed):
        if k not in cand:
            del listed[k]
    mode = "report" if os.environ.get("NOPROG_GRTFLAT_MODE") == "report" else "act"
    done = []
    if mode == "act":
        by_attempt = {}
        for k, (r, ev) in cand.items():
            by_attempt.setdefault(wave_identity(r["kit"]), []).append((k, r, ev))
        for ident, items in sorted(by_attempt.items()):
            if any(now - listed[k] < MIN_REPORT_AGE_S for k, _r, _e in items):
                continue
            # every container of the attempt's unit must be a candidate (a sibling still progressing keeps the unit)
            units = {(r["host"], r["unit"]) for _k, r, _e in items if r.get("unit")}
            sib = [x for x in rows if (x["host"], x.get("unit")) in units and f"{x['host']}|{x['key']}" not in cand]
            if sib or seen.get("gf_cancelled", {}).get("|".join(ident)):
                continue
            first = items[0][1]
            why = f"{GRT_FLAT_CLASS}: {items[0][2]}; job {first['age_h']} h at {first['stage']}; die owner: plan fix, no unchanged retry"
            rc, line = cancel(ident, why)
            seen.setdefault("gf_cancelled", {})["|".join(ident)] = now
            done.append({"t": now, "die": ident[0], "event": ident[1], "item": ident[2], "attempt": ident[3], "host": first["host"], "evidence": why,
                         "freed_gb": round(sum(r["gb"] for _k, r, _e in items), 1), "class": "PLAN " + GRT_FLAT_CLASS, "cancel_method": f"kit_wave cancel-rows rc={rc}: {line}"})
    if done:
        path = os.path.join(COORD, "lanes/CANCEL-GRT-FLAT.tsv")
        with open(path, "a") as f:
            for d in done:
                f.write("\t".join(str(d[k]).replace("\t", " ").replace("\n", " ") for k in ("t", "die", "event", "item", "attempt", "host", "evidence", "freed_gb", "class", "cancel_method")) + "\n")
    if done and post:
        txt = f"GRT-FLAT watchdog cancelled {len(done)} wave attempt(s) (class PLAN {GRT_FLAT_CLASS}): " + "; ".join(f"{d['die']}/{d['item']}@{d['attempt']} {d['freed_gb']} GB" for d in done[:40])
        try:
            subprocess.run(["bash", os.path.join(COORD, "bin/post.sh"), os.environ.get("NOPROG_POST_LANE", "FLEET-WATCH-2000"), txt], capture_output=True, text=True, timeout=300)
        except (subprocess.SubprocessError, OSError):
            pass
    return mode, [v for v in cand.values()], done


# ---------------------------------------------------------------- GRT-LABEL notice (GRT-LABEL-NOTICE-1122, COORD flow review item 3)
# A GRT-LABEL DESIGN-FAIL job is a label only: grt_flat_pass cancels wave attempts, and lane / private kits had no action at all (33 labelled jobs
# on the 22:45 table, some 61-75 h).  The hub now tracks each labelled job's latest overflow; once it has been flat or rising (never 2 % below the
# overflow when the clock started) for >= 3 h, ONE NOTICE goes to the owning lane, the same route as UNSIGNABLE.  Notice only: the owner cancels
# (ot-run --cancel <unit>) or posts KEEP.  A fall of >= 2 % restarts the clock (and allows a later notice).  Wave attempts that grt_flat_pass takes,
# KEEP / EXCLUDED jobs (their verdict is not GRT-LABEL) and keys unseen 6 h are skipped / forgotten.
GRT_LABEL_NOTICE_S = 3 * 3600


def grt_label_notice_pass(rows, seen, now, post=True):
    """-> [(owner, line)] noticed this pass"""
    poster = os.environ.get("NOPROG_POST_LANE", "FLEET-WATCH-1015")
    st = seen.setdefault("grt_label", {})
    out = []
    for r in rows:
        if r.get("verdict") != GRT_LABEL or not str(r.get("why") or "").startswith("DESIGN-FAIL") or r.get("grt_ovf") is None:
            continue
        if grt_flat_candidate(r) or grt_repair_progress(r):
            continue                     # a wave attempt: grt_flat_pass cancels it through the wave
        ov = float(r["grt_ovf"])
        k = f"{r['host']}|{r.get('unit') or r.get('container')}"
        e = st.get(k)
        if e is None or ov < e["ov0"] * (1 - MIN_IMPROVE):
            e = st[k] = {"first": now, "ov0": ov}
        e.update(last=now, ov=ov)
        if now - e["first"] >= GRT_LABEL_NOTICE_S and not e.get("notice"):
            e["notice"] = now
            out.append((owner_of([r]), f"{r['host']} {r.get('unit') or r.get('container')} {r.get('type', '')} ({str(r.get('why'))[:120]}; overflow "
                                       f"{e['ov0']:.0f} -> {ov:.0f} over {(now - e['first']) / 3600:.1f} h; job {r.get('age_h')} h, {r.get('gb', 0):.0f} GB)"))
    for k in list(st):
        if now - st[k].get("last", now) > UNSIGNABLE_FORGET_S:
            del st[k]
    if post:
        by = {}
        for o_, ln in out:
            by.setdefault(o_, []).append(ln)
        for owner, ls in sorted(by.items()):
            _post(poster, f"NOTICE [{poster} -> {owner}] GRT-LABEL watchdog: {len(ls)} job(s) with a GRT DESIGN-FAIL label whose overflow has been flat or "
                          f"rising for >= {GRT_LABEL_NOTICE_S // 3600} h: " + "; ".join(ls[:40])
                  + f". Notice only, the watchdog does not cancel: {owner} decides (ot-run --cancel <unit>) or posts 'KEEP <unit> <why>'.")
    return out


# ---------------------------------------------------------------- DESIGN-FAIL cancel (LAUNCH-GUARD 11-23, COORD FIX 2, post 4cc1854: 20 GRT-LABEL DESIGN-FAIL containers, 0 cancelled)
# A container whose GRT already carries the DESIGN-FAIL label holds cores and memory for a result that cannot sign.  Leak paths found 11-23 01:xx:
#   (1) lane (OT_LANE) and private kits: grt_flat_pass takes wave attempts only, grt_label_notice_pass only posts a notice;
#   (2) wave attempts whose cancel-rows call was recorded (gf_cancelled) but whose container kept running (old-event rows the wave no longer tracks): never retried.
# Rule: GRT-LABEL DESIGN-FAIL and the overflow has not fallen 2 % for DF_FLAT_S (2 h) (NOPROG-GRTFALL-1124: the round-10 threshold alone no longer cancels).
# Wave attempts not yet taken by grt_flat_pass go through it (cancel-rows keeps the wave record right); everything else: ot-run --cancel <unit> --reason design.
# Never: proofs, ECOs, hold-only, LEC, re-sign, HBM, --priority plan/proof, NOPROG-KEEP rows (verdict KEEP), units with a KEEP <unit> post, decide-only lanes.
DF_FLAT_S = 2 * 3600
DF_MIN_AGE_H = 3.0            # NOPROG-GRTHOLD-1124 (COORD): owner rule: cancel only jobs OVER 3 h that are measured unable to sign
DF_OVF_RE = re.compile(r"overflow (\d+) at round (\d+) > (\d+)")


# ---------------------------------------------------------------- STAGE-PLATEAU (COORD 11-25, FABLE flow review 02:4x): DRT-PLATEAU and HOLD-STALL
# (A) detailed route that plateaus (hd_serdes 31 iterations at 1.4-1.8k with -droute_end_iter 64; sle_fw_v2 25k -> 15k -> 63.5k; sle_sc_v1 2761 -> 13398) and
# (B) pregrt_ff_hold with a flat repair_TNS (hours at 145,595 / 275,514) had no cancel rule.  Both are judged on the job's own log; the HUB cancels through
# design_fail_pass (same exemptions, same keep/decide-only posts, same ot-run --cancel --reason design, lanes/CANCEL-DESIGN-FAIL.tsv, actions.jsonl on the host).
# A TNS of 0 or better is converged and is NEVER HOLD-STALL (11-23 incident: converged TNS 0 kits were killed).
DRT_MIN_ITER = 6          # rules (a)/(b) apply only after iteration 6 (DRT-0199 total number 7 or later)
DRT_FLAT_FALL = 0.05      # (a) each of the last 3 iterations falls less than 5 %
DRT_FLAT_ITERS = 3
DRT_FLAT_OVER = 1000      # (a) ... and the count is still over 1k
DRT_HIGH = 10000          # (b) over 10k after iteration 6
DRT_RISE = 3.0            # (c) more than 3x the best total so far
HOLD_STALL = "HOLD-STALL"
DRT_PLATEAU = "DRT-PLATEAU"


def drt_totals(text):
    """DRT-0199 violation totals, one per completed iteration (iteration 0 first).  Pure."""
    return [int(m.group(1)) for m in DRT_ITER.finditer(text)]


def drt_plateau_at(vals):
    """-> evidence text when the detailed-route violation totals VALS (iteration 0 first) match DRT-PLATEAU, else ''.  Pure.
    (a) FLAT: after iteration 6, still > 1k and the total fell < 5 % over the last 3 iterations (v[n] > 0.95 v[n-3]);
    (b) HIGH: after iteration 6, > 10k, unless it fell >= 10 % over the last 3 iterations (the dry run showed 10k+ counts that went on to fall 60-90 %) or just rose / just fell > 5 % in the last step (a spike or its recovery is rule (c)'s);
    (c) RISE: more than 3x the best total, on two consecutive totals (the dry run showed a one-iteration 4x spike that recovered below the best)."""
    n = len(vals) - 1
    if n < 2:
        return ""
    last = vals[-1]
    if n >= 2 and len(vals) >= 3:
        best = min(vals[:-2])
        if best > 0 and last > DRT_RISE * best and vals[-2] > DRT_RISE * best:
            return f"DRT-PLATEAU rise: {vals[-2]} -> {last} violations at iteration {n} = {last / best:.1f}x the best {best} for 2 iterations (> {DRT_RISE:g}x)"
    if n > DRT_MIN_ITER:
        k = DRT_FLAT_ITERS
        ref = vals[n - k]
        if last > DRT_HIGH and vals[-2] * 0.95 < last <= vals[-2] and last > ref * 0.90:
            return f"DRT-PLATEAU high: {last} violations at iteration {n} (> {DRT_HIGH} after iteration {DRT_MIN_ITER}), fell {100 * (1 - last / ref):.1f} % over the last {k} iterations (< 10 %)"
        if last > DRT_FLAT_OVER and vals[-2] * 0.95 < last <= vals[-2] and last > ref * (1 - DRT_FLAT_FALL):
            return (f"DRT-PLATEAU flat: {last} violations at iteration {n}, fell {100 * (1 - last / ref):.1f} % (< {DRT_FLAT_FALL * 100:g} %) over the last {k} iterations "
                    f"({'->'.join(str(v) for v in vals[-k - 1:])}), still > {DRT_FLAT_OVER}")
    return ""


def drt_plateau_evidence(vals):
    """-> evidence of the FIRST iteration at which drt_plateau_at() matched (STICKY, COORD 11-25: sle_fw_v2 matched 'high' at iteration 8, fell 38 % in 8 more
    iterations to 14,980, then jumped to 63,558; the jump made the last-step guards skip it and a 30 h kit looked PROGRESS).  A kit that is on the list stays on it.
    The guards above only keep a falling or recovering count OFF the list; they never take a listed kit off.  Pure."""
    for n in range(2, len(vals) + 1):
        ev = drt_plateau_at(vals[:n])
        if ev:
            return ev
    return ""


def lec_exempt(kind, verdict, why):
    """COORD 11-25 item 41: a LEC job is never NO-PROGRESS (a signed slw_hc3 LEC at 93 % of a core was flagged).  The 24 h advisory LEC cap is separate.  -> (verdict, why)"""
    if kind == "lec" and verdict == "NO-PROGRESS":
        return "PROGRESS", f"LEC exempt from no-progress (COORD 11-25): {why}"
    return verdict, why


PLATEAU5_ITERS = 5
PLATEAU5_CHANGE = 0.02
PLATEAU_REPAIR_MAX = 100        # under this many violations a plateau is a DRC-repair / ECO-route candidate
PLATEAU_SMELL_MIN = 1000        # over this many it is a SMELL (+ render), and a cancel RECOMMENDATION once the job is over 3 h


def drt_plateau5(vals):
    """FLOW-0730 F6: PLATEAU = each of the last 5 iterations changed the DRT total by less than 2 % (either way).  -> last total, or None.  Pure.
    Wider than DRT-PLATEAU (which cancels): this only labels and routes (report-only)."""
    if len(vals) < PLATEAU5_ITERS + 1:
        return None
    t = vals[-(PLATEAU5_ITERS + 1):]
    if all(a > 0 and abs(b - a) / a < PLATEAU5_CHANGE for a, b in zip(t, t[1:])):
        return t[-1]
    return None


def plateau_route(r):
    """-> (class, text) routing of a row with r['plateau5'] (last DRT total) set, else None.  class REPAIR (< 100), SMELL (> 1000), RECOMMEND-CANCEL (> 1000 and job > 3 h), MID (100..1000: label only)"""
    n = r.get("plateau5")
    if n is None:
        return None
    if n < PLATEAU_REPAIR_MAX:
        return "REPAIR", f"DRT plateau at {n:g} violations (5 iterations < 2 % change): DRC-repair / ECO-route candidate"
    if n > PLATEAU_SMELL_MIN:
        if float(r.get("age_h") or 0) > DF_MIN_AGE_H:
            return "RECOMMEND-CANCEL", f"DRT plateau at {n:g} violations (5 iterations < 2 % change), job {r.get('age_h')} h > 3 h: cancel recommended (report-only)"
        return "SMELL", f"DRT plateau at {n:g} violations (5 iterations < 2 % change)"
    return "MID", f"DRT plateau at {n:g} violations (5 iterations < 2 % change)"


def plateau_route_pass(rows, seen, now, post=True):
    """HUB, report-only: post each plateau kit once per class (24 h).  REPAIR -> owner + QC-DRT-TAIL; SMELL / RECOMMEND-CANCEL -> die FP-CONVERGE lane + owner (SMELL also gets its render
    through smell_pass).  Never cancels.  -> [(key, class, text)]"""
    st = seen.setdefault("plateau5", {})
    out = []
    for r in rows:
        pr = plateau_route(r)
        if not pr or smell_exempt(r) or plateau_exempt(r):
            continue
        k = f"{r.get('kit') or r.get('work') or r.get('container')}|{pr[0]}"
        if k in st:
            continue
        st[k] = now
        out.append((k, pr[0], pr[1], r))
    for k in [k for k, t in st.items() if now - float(t) > 86400]:
        del st[k]
    if post and out:
        groups = {}
        for k, cls, txt, r in out:
            die = DIE_TAG.get(die_of(" ".join(str(r.get(x) or "") for x in ("container", "kit", "work", "ident"))), "?")
            to = smell_recipients(die, owner_of([r])) if cls != "REPAIR" else ", ".join(x for x in (owner_of([r]), "QC-DRT-TAIL") if x and x != "COORD") or "QC-DRT-TAIL"
            groups.setdefault((cls, to), []).append(f"{r.get('type', '')} {r.get('host')} {r.get('unit') or r.get('container')}: {txt}")
        for (cls, to), items in sorted(groups.items()):
            _post(os.environ.get("NOPROG_SMELL_LANE", "SMELL-WATCH"), f"PLATEAU-{cls} [SMELL-WATCH -> {to}; cc COORD] {len(items)} kit(s), report-only: " + " | ".join(items[:25]))
    return [(k, c, t) for k, c, t, _ in out]


# ---------------------------------------------------------------- PLATEAU-ACT (COORD FLOW-0930 F-10, 11-25): the plateau rule acts
PLATEAU3_ITERS = 3
PLATEAU3_FALL = 0.05               # a DRT run that fell < 5 % over its last 3 iterations, or rose, is on a plateau
PLATEAU_CANCEL_MIN = 1000          # over this many marks, flat or rising, job > DF_MIN_AGE_H: CANCEL-ELIGIBLE
PLATEAU_OWNER_SILENT_S = 3600      # cancel only when the owner lane is dead or has not posted for this long
PLATEAU_ACT_FILE = "lanes/PLATEAU-ACT.tsv"
PLATEAU_ACT_COLS = ["t", "class", "die", "type", "host", "unit", "marks", "trend", "age_h", "owner", "owner_state", "action", "evidence"]
ALLFIX_LANE = {"QC": "QC-ALLFIX", "KV": "KV-ALLFIX", "S81": "S81-ALLFIX-INT", "HEAD": "HEAD-ALLFIX"}


def drt_plateau3(vals):
    """PLATEAU-ACT: -> (last total, 'flat' | 'rising') when the DRT totals VALS (iteration 0 first) fell by less than 5 % over the last 3 iterations ('flat') or are higher than 3 iterations ago
    ('rising'), else None.  Needs 4 totals and a non-zero last total.  Pure."""
    if len(vals) < PLATEAU3_ITERS + 1:
        return None
    t = vals[-(PLATEAU3_ITERS + 1):]
    if t[-1] <= 0 or t[0] <= 0:
        return None
    if t[-1] > t[0]:
        return t[-1], "rising"
    if (t[0] - t[-1]) / t[0] < PLATEAU3_FALL:
        return t[-1], "flat"
    return None


def owners_sweep(coord=None):
    """lanes/OWNERS-SWEEP.tsv -> {(die tag, type): dict(owner, alive, last_post)}; owner = the first lane of fresh_owner ('A+B').  {} when unreadable"""
    return _cached_file(os.path.join(coord or COORD, "lanes/OWNERS-SWEEP.tsv"), _load_sweep)


def _load_sweep(path):
    out = {}
    try:
        lines = open(path, errors="replace").read().splitlines()
    except (OSError, TypeError):
        return out
    hdr = next((i for i, l in enumerate(lines) if l.startswith("die\ttype\t")), None)
    if hdr is None:
        return out
    cols = lines[hdr].split("\t")
    ix = {c: i for i, c in enumerate(cols)}
    for l in lines[hdr + 1:]:
        f = l.split("\t")
        if len(f) <= ix.get("fresh_owner", 99):
            continue
        g = lambda c: f[ix[c]].strip() if c in ix and ix[c] < len(f) else ""
        out[(g("die"), g("type"))] = dict(owner=g("fresh_owner").split("+")[0].strip(), alive=g("owner_alive"), last_post=g("lane_last_post"))
    return out


def route_owner(tag, typ, sweep, fallback_owner=""):
    """F-15: the live owner of (die tag, type) by OWNERS-SWEEP fresh_owner; no live owner -> the die's ALLFIX lane.  -> (lane, state) state 'alive' | 'dead' | 'unknown'"""
    best = sweep.get((tag, typ))
    if not best:
        base = typ.split("__")[0]
        best = next((v for (d, t), v in sweep.items() if d == tag and (t.split("__")[0] == base)), None)
    if best and best["owner"] and best["alive"] == "yes":
        return best["owner"], "alive"
    if best and best["owner"]:
        return ALLFIX_LANE.get(tag, best["owner"]), "dead"
    return ALLFIX_LANE.get(tag) or (fallback_owner if fallback_owner and fallback_owner != "COORD" else "COORD"), "unknown"


def owner_silent_s(sweep, tag, typ, now):
    """seconds since the owning lane's last post (OWNERS-SWEEP lane_last_post 'MM-DD HH:MM' PST), None when unknown"""
    import datetime as _dt
    best = sweep.get((tag, typ)) or next((v for (d, t), v in sweep.items() if d == tag and t.split("__")[0] == typ.split("__")[0]), None)
    if not best or not best.get("last_post"):
        return None
    try:
        from zoneinfo import ZoneInfo
        z = ZoneInfo("America/Los_Angeles")
        t = _dt.datetime.strptime(best["last_post"], "%m-%d %H:%M")
        ref = _dt.datetime.fromtimestamp(now, z)
        t = t.replace(year=ref.year, tzinfo=z)
        if t > ref:
            t = t.replace(year=ref.year - 1)
        return max(0.0, now - t.timestamp())
    except Exception:
        return None


def plateau_act_class(r):
    """-> (class, text) for a row with r['plateau3'] set: REPAIR-NOTICE (< 100 marks), CANCEL-ELIGIBLE (> 1000, job > 3 h), SPARED-TNS0 (would be CANCEL-ELIGIBLE but its post-CTS TT setup passes the gate: a
    converged / near sign-off kit is never cancelled), else None (100..1000: no action)"""
    n, kind = r.get("plateau3"), r.get("plateau3_kind") or "flat"
    if n is None:
        return None
    if n < PLATEAU_REPAIR_MAX:
        return "REPAIR-NOTICE", f"DRT {kind} at {n:g} violations over the last 3 iterations: hand to DRC repair / ECO-route"
    if n > PLATEAU_CANCEL_MIN and float(r.get("age_h") or 0) > DF_MIN_AGE_H:
        if r.get("setup_ps") is not None and float(r["setup_ps"]) >= GATE_SETUP_PS:
            return "SPARED-TNS0", f"DRT {kind} at {n:g} violations, job {r.get('age_h')} h, but TT setup {r['setup_ps']} ps passes the {GATE_SETUP_PS:g} ps gate: never cancelled"
        return "CANCEL-ELIGIBLE", f"DRT {kind} at {n:g} violations over the last 3 iterations, job {r.get('age_h')} h > 3 h"
    return None


def plateau_act_pass(rows, seen, now, post=True, cancel=None, sweep=None):
    """HUB (PLATEAU-ACT, COORD FLOW-0930 F-10): the plateau rule acts.  Per DRT kit on a plateau (drt_plateau3): < 100 marks -> one 'hand to DRC repair / ECO-route' notice to the owner (OWNERS-SWEEP
    fresh_owner, else the die's ALLFIX lane); > 1000 marks and job > 3 h -> a CANCEL-ELIGIBLE row, and `ot-run --cancel <exact unit>` only when that owner is dead or has been silent for over 1 h
    (and the kit is not KEEP / decide-only / TT-passing).  Rows go to lanes/PLATEAU-ACT.tsv.  NOPROG_PLATEAU_ACT=report or lanes/PLATEAU-ACT.off = rows + notices only.  -> [row dict] written"""
    cancel = cancel or ot_run_cancel
    sweep = owners_sweep() if sweep is None else sweep
    act_off = os.environ.get("NOPROG_PLATEAU_ACT") == "report" or os.path.exists(os.path.join(COORD, "lanes/PLATEAU-ACT.off"))
    st = seen.setdefault("plateau_act", {})
    keeps = keep_posts()
    out, notes = [], []
    for r in rows:
        pc = plateau_act_class(r)
        if not pc or smell_exempt(r) or plateau_exempt(r):
            continue
        cls, text = pc
        ident = " ".join(str(r.get(x) or "") for x in ("container", "kit", "work", "ident"))
        tag = DIE_TAG.get(die_of(ident), "?")
        typ = str(r.get("type") or "")
        owner, ostate = route_owner(tag, typ, sweep, owner_of([r]))
        silent = owner_silent_s(sweep, tag, typ, now)
        k = f"{r.get('host')}|{r.get('unit') or r.get('container')}|{cls}"
        first = k not in st
        if first:
            st[k] = now
        how = ""
        if cls == "CANCEL-ELIGIBLE":
            can = r.get("unit") and r["unit"] not in keeps and not decide_only(ident + " " + str(r.get("kit") or ""))
            gone = ostate != "alive" or (silent is not None and silent > PLATEAU_OWNER_SILENT_S)
            dkey = k + "|done"
            if act_off:
                how = "report-only (switch off)"
            elif not can:
                how = "not cancelled: KEEP / decide-only / no unit"
            elif not gone:
                how = f"owner {owner} alive (last post {int(silent // 60) if silent is not None else '?'} min ago): notice only, cancel when it is dead or silent > 1 h"
            elif dkey in st:
                continue
            else:
                write_cancel_marks([r.get("kit")], "PLATEAU-ACT", f"CANCEL-PLATEAU: {text}", now)
                rc, line = cancel(r["unit"])
                st[dkey] = now
                cls, how = "CANCELLED", f"ot-run --cancel {r['unit']} --reason design rc={rc}: {line}"
        elif not first:
            continue
        if not first and cls == "CANCEL-ELIGIBLE":
            continue                                     # eligible and still waiting for its owner: one row + notice per 24 h
        out.append(dict(t=int(now), **{"class": cls}, die=tag, type=typ, host=r.get("host"), unit=r.get("unit") or r.get("container"), marks=f"{r.get('plateau3'):g}", trend=r.get("plateau3_kind"),
                        age_h=r.get("age_h"), owner=owner, owner_state=ostate + (f", silent {int(silent // 60)} min" if silent is not None else ""), action=how or text, evidence=text))
        notes.append((owner, cls, f"{typ} {r.get('host')} {r.get('unit') or r.get('container')}: {text}" + (f"; {how}" if how else "")))
    for k in [k for k, t in st.items() if now - float(t) > 86400]:
        del st[k]
    if out:
        path = os.path.join(COORD, PLATEAU_ACT_FILE)
        new = not os.path.exists(path)
        with open(path, "a") as f:
            if new:
                f.write("\t".join(PLATEAU_ACT_COLS) + "\n")
            for o in out:
                f.write("\t".join(str(o[c]).replace("\t", " ").replace("\n", " ") for c in PLATEAU_ACT_COLS) + "\n")
    if post and notes:
        by = {}
        for owner, cls, txt in notes:
            by.setdefault((owner, cls), []).append(txt)
        for (owner, cls), items in sorted(by.items()):
            head = "hand to DRC repair / ECO-route" if cls == "REPAIR-NOTICE" else ("cancelled (owner dead or silent > 1 h)" if cls == "CANCELLED" else cls)
            _post(os.environ.get("NOPROG_SMELL_LANE", "PLATEAU-ACT"), f"PLATEAU-ACT [PLATEAU-ACT -> {owner}; cc COORD] {head}: {len(items)} kit(s): " + " | ".join(items[:25]) + f". Evidence {PLATEAU_ACT_FILE}.")
    return out


def hold_stall_evidence(stage, res, verdict, why, detail="", anchors=None, now=None, window=None):
    """-> evidence text when the running step is pregrt_ff_hold, its repair_TNS is still below 0 and has not improved by MIN_IMPROVE in the step window (2 h)
    (judge() says NO-PROGRESS), else ''.  Pure.  A TNS of 0 or better (tns_converged), a young step and a step without a TNS row are never stalled.
    Dry run 11-25: one repair pass prints only its iteration-0 row and then runs for hours (kv3_pv_v3: 10,099 s, TNS -169,360 -> -3,862, then 0), so a flat
    window needs REAL rows: >= 3 rows of the current table, one at least `window` old and one inside it (with anchors given), never a single quiet row."""
    if not str(stage or "").startswith("pregrt_ff_hold") or res.get("name") != "repair_TNS" or not res.get("series"):
        return ""
    if tns_converged(res) or verdict != "NO-PROGRESS" or len(res["series"]) < 3:
        return ""
    if anchors is not None and now is not None and window:
        ts = [interp_time(i, anchors) for i, _ in res["series"]]
        if not (min(ts) <= now - window < max(ts)):
            return ""
    return f"HOLD-STALL pregrt_ff_hold: {why}; {detail}"[:300]


DRC_BLOCK = re.compile(r"^violation type:\s*(.+?)\s*$")
DRC_BBOX = re.compile(r"bbox = \(([-\d.]+), ([-\d.]+)\) - \(([-\d.]+), ([-\d.]+)\) on Layer (\S+)")
DRC_CELL_UM = 50.0


def drc_region_summary(text, top=5):
    """worst layers / violation types and the densest 50 um bbox clusters of an OpenROAD -output_drc report.  -> one line.  Pure."""
    types, layers, cells, n = {}, {}, {}, 0
    cur = ""
    for ln in text.splitlines():
        m = DRC_BLOCK.match(ln)
        if m:
            cur = m.group(1)
            continue
        b = DRC_BBOX.search(ln)
        if b and cur:
            n += 1
            x = (float(b.group(1)) + float(b.group(3))) / 2
            y = (float(b.group(2)) + float(b.group(4))) / 2
            types[cur] = types.get(cur, 0) + 1
            layers[b.group(5)] = layers.get(b.group(5), 0) + 1
            c = (int(x // DRC_CELL_UM) * int(DRC_CELL_UM), int(y // DRC_CELL_UM) * int(DRC_CELL_UM))
            cells[c] = cells.get(c, 0) + 1
    if not n:
        return ""
    fmt = lambda d: ", ".join(f"{k} {v}" for k, v in sorted(d.items(), key=lambda kv: -kv[1])[:top])
    cl = ", ".join(f"({x}..{x + int(DRC_CELL_UM)},{y}..{y + int(DRC_CELL_UM)}) um {v}" for (x, y), v in sorted(cells.items(), key=lambda kv: -kv[1])[:top])
    return f"DRC {n} marks; types: {fmt(types)}; layers: {fmt(layers)}; bbox clusters ({int(DRC_CELL_UM)} um cells): {cl}"


def latest_drc_summary(log):
    """summary of the newest 5_route_drc.rpt-N.rpt next to a 5_2_route log (logs/ -> reports/), '' when none.  The N-th report is written every 5 iterations."""
    if not log:
        return ""
    rdir = os.path.dirname(log).replace("/logs/", "/reports/")
    cands = []
    for p in glob.glob(os.path.join(rdir, "5_route_drc.rpt*")):
        try:
            cands.append((os.stat(p).st_mtime, p))
        except OSError:
            pass
    for _, p in sorted(cands, reverse=True):
        try:
            s = drc_region_summary(read_text(p, cap=64 * 2**20))
        except OSError:
            continue
        if s:
            return f"{os.path.basename(p)}: {s}"
    return ""


def plateau_exempt(r):
    """exemption for the plateau rules.  design_fail_exempt() reads the log path too, and a pregrt_ff_hold.log path matches HOLD_ONLY_RE: judge the NAME / kit only."""
    ident = " ".join(str(r.get(k) or "") for k in ("container", "type", "kit", "work"))
    ex = unsignable_exempt(ident, r.get("prio", ""), r.get("kind", ""))
    if ex:
        return ex
    return "re-sign" if re.search(r"(?i)re-?sign", ident) else ""


def plateau_evidence(r):
    """-> (class, evidence) from the host scan's row (r['plateau'], r['plateau_class']) when the job may be cancelled for it, else None.  Pure."""
    if not r.get("plateau") or r.get("verdict") in ("KEEP", "EXCLUDED") or float(r.get("age_h") or 0) <= DF_MIN_AGE_H or plateau_exempt(r):
        return None
    ev = r["plateau"] + (f"; {r['drc_summary']}" if r.get("drc_summary") else "")
    return r.get("plateau_class") or "PLATEAU", ev


def plateau_mode_off():
    return os.environ.get("NOPROG_PLATEAU_MODE") == "report" or os.path.exists(os.path.join(COORD, "lanes/PLATEAU-WATCHDOG.off"))



# ---------------------------------------------------------------- SMELL (OWNER 04:1x via COORD, 11-25): an EARLY bad-design trigger.  It never cancels.
# A kit that smells gets (a) a render of its current DB next to the kit, (b) a line in lanes/SMELL.tsv, (c) a post to the die's FP-CONVERGE lane and the type
# owner, so the visual review and the structural root-cause fix start while the slow job still runs.  The kit keeps running until it recovers or meets the
# existing unsignable-and-over-3-h cancel rules.  The first SMELL_DRY_S (30 min) after deploy is a dry run: the hub posts the would-fire list, then goes live.
SMELL_DRY_S = int(os.environ.get("NOPROG_SMELL_DRY_S", "1800"))
# CALIBRATED 11-25 on the 24-48 h replay of all 9 hosts (calib.py: 349 DRT logs, 45 bad / 304 good; 272 GRT logs, 95 bad / 177 good; bad = never reached 0 / GRT odb never written
# and the kit ended or ran > 10 h; good = route reached 0 / GRT odb written).  The owner's first-cut triggers fired on kits that finished (DRT iteration-0 > 50k: precision 0.29;
# GRT > 5 iterations: 0.53; M1-M3 share > 60 %: 0.33), so they were replaced:
#   GRT overflow > 1000 at iteration >= 10 : precision 0.72, recall 0.95
#   DRT v0 > 300k OR v3 > 1500 OR v6 > 0.3 v3 (fell < 70 % from it 3 to 6) : precision 0.74, recall 0.76
SMELL_GRT_OVF = 1000
SMELL_GRT_IT = 10
SMELL_DRT_V0 = 300000
SMELL_DRT_V3 = 1500
SMELL_DRT_FALL36 = 0.3
SMELL_CTS_H = 2.0
SMELL_CTS_SETUP = -100.0
SMELL_CTS_HOLD = -50.0
SMELL_PLACE_DENSITY = 0.8
SMELL_PLACE_TD_ITERS = 8       # timing-driven repair looping: more than 8 timing-driven passes in the placement log (uncalibrated: dry run decides)
SMELL_SILENT_H = 1.0
SMELL_DENSITY_RE = re.compile(r"(?i)target[ _]?density\s*[:=]?\s*([0-9]*\.[0-9]+)")
SMELL_TD_RE = re.compile(r"(?i)timing-driven(?:\s+(?:iteration|pass|overflow)|:\s*(?:repair|resiz))")
CTS_POST_RE = re.compile(r"(?m)^OT_CTS_POST_TIMING .*?setup_ws (-?[0-9.]+)(?:.*?hold_ws (-?[0-9.]+))?")
DIE_TAG = {"qwen_compute": "QC", "qwen_kvsys": "KV", "s81": "S81", "s81_head": "HEAD", "hbm": "HBM"}
DIE_INT = {"QC": "QC-ALLFIX", "KV": "KV-ALLFIX", "S81": "S81-ALLFIX-INT", "HEAD": "HEAD-ALLFIX"}


def low_layer_share(drc_text):
    """share of DRC marks on M1-M3 (0..1) and the mark count.  Pure."""
    n = low = 0
    for m in DRC_BBOX.finditer(drc_text or ""):
        n += 1
        if re.fullmatch(r"M[123]", m.group(5)):
            low += 1
    return (low / n if n else 0.0), n


def smell_triggers(kind, stage, log_age_h, stage_age_h, rounds=None, drt_vals=None, drc_text="", log_text="", cts=None):
    """-> [(class, text)] SMELL triggers of one running stage.  Pure.  cts = (setup_ps, hold_ps|None) from the post-CTS timing line, else None."""
    out = []
    rounds = rounds or []
    if kind == "grt" and rounds:
        late = [(n, v) for n, v in rounds if n >= SMELL_GRT_IT and v > SMELL_GRT_OVF]
        if late:
            out.append(("GRT", f"overflow {late[-1][1]} at iteration {late[-1][0]} (> {SMELL_GRT_OVF} at iteration >= {SMELL_GRT_IT})"))
    if kind == "drt" and drt_vals:
        if drt_vals[0] > SMELL_DRT_V0:
            out.append(("DRT", f"iteration-0 violations {drt_vals[0]} (> {SMELL_DRT_V0})"))
        if len(drt_vals) > 3 and drt_vals[3] > SMELL_DRT_V3:
            out.append(("DRT", f"iteration-3 violations {drt_vals[3]} (> {SMELL_DRT_V3})"))
        if len(drt_vals) > 7 and drt_vals[6] > SMELL_DRT_FALL36 * drt_vals[3]:
            out.append(("DRT", f"fell < {100 * (1 - SMELL_DRT_FALL36):.0f} % from iteration 3 to 6: {drt_vals[3]} -> {drt_vals[6]}"))
    if str(stage).startswith("4_1_cts") or kind == "cts":
        if stage_age_h > SMELL_CTS_H:
            out.append(("CTS", f"CTS stage {stage_age_h:.1f} h (> {SMELL_CTS_H:g} h)"))
        if cts:
            if cts[0] is not None and cts[0] < SMELL_CTS_SETUP:
                out.append(("CTS", f"post-CTS setup {cts[0]:.0f} ps (< {SMELL_CTS_SETUP:g})"))
            if len(cts) > 1 and cts[1] is not None and cts[1] < SMELL_CTS_HOLD:
                out.append(("CTS", f"post-CTS hold {cts[1]:.0f} ps (< {SMELL_CTS_HOLD:g})"))
    if kind == "gpl" or "place" in str(stage):
        dens = [float(x) for x in SMELL_DENSITY_RE.findall(log_text or "")]
        if dens and max(dens) > SMELL_PLACE_DENSITY:
            out.append(("PLACE", f"placement density {max(dens):g} (> {SMELL_PLACE_DENSITY:g})"))
        td = len(SMELL_TD_RE.findall(log_text or ""))
        if td > SMELL_PLACE_TD_ITERS:
            out.append(("PLACE", f"timing-driven repair looping: {td} timing-driven passes (> {SMELL_PLACE_TD_ITERS})"))
    if log_age_h > SMELL_SILENT_H:
        out.append(("SILENT", f"log silent {log_age_h:.1f} h (> {SMELL_SILENT_H:g} h)"))
    return out


def smell_exempt(r):
    """rows never smelled: plan/proof jobs, KEEP, LEC, HBM (parked).  The smell is for design review, so a bind/LATCHECK or an advisory LEC has no design to review."""
    return bool(r.get("verdict") in ("KEEP", "EXCLUDED") or r.get("kind") == "lec" or r.get("prio") in ("plan", "proof") or is_hbm(str(r.get("ident") or "")))


def find_current_odb(work):
    """newest *.odb the kit's flow wrote (the DB of the stage that is running or just ended), '' when none"""
    best = ("", 0.0)
    for g in ("run/results/*/*/*/*.odb", "gen/*/run/results/*/*/*/*.odb", "results/*/*/*/*.odb"):
        for p in glob.glob(os.path.join(work, g)):
            try:
                mt = os.stat(p).st_mtime
            except OSError:
                continue
            if mt > best[1]:
                best = (p, mt)
    return best[0]


RENDER_TOOLS = ("autopilot/render_review.sh", "autopilot/render_review.py", "ref_tile/layout_dump.tcl", "ref_tile/layout_png.py", "ref_tile/layout_review.tcl")
RENDER_TOOLS_OPT = ("autopilot/stage_paths.tcl",)      # VIS-REOWN 11-25: worst-50 setup + hold paths of the rendered DB (copied when the tool root has it)
LR_STAGE = (("5_2", "route"), ("5_3", "route"), ("6_", "route"), ("5_1", "grt"), ("4_", "place"), ("3_", "place"))


def kit_smells(work, odb):
    """the kit's own layout_smells result for the rendered DB's stage (<kit>/run/layout_review/{place,grt,route}/smells.one|json, written by
    the KW-FIX-25 autorender hook) -> [one-line strings] for SMELL.txt / the summary.  Falls back to the latest stage that has one, labelled.
    Pure of the hub."""
    base = os.path.basename(odb or "")
    want = next((st for pre, st in LR_STAGE if base.startswith(pre)), "")
    out = []
    for st in [want] + [x for x in ("route", "grt", "place") if x != want]:
        if not st:
            continue
        d = os.path.join(work or "", "run", "layout_review", st)
        one = read_text(os.path.join(d, "smells.one")).strip()
        if not one:
            try:
                one = str(json.load(open(os.path.join(d, "smells.json"))).get("summary") or "")
            except (OSError, ValueError):
                one = ""
        if one:
            out.append(("smells " if st == want else f"smells (kit {st} DB, not this stage) ") + one[:300])
            break
    return out


def odb_snapshot(odb, rev, run=subprocess.run):
    """F5: a private copy of the checkpoint DB in the review dir (cp --reflink=auto), so no stage-cap / resume / rewrite of the kit's file can change it under the render.
    The source must keep its inode, size and mtime across the copy and the copy must have the same size.  -> (snapshot path, '') or ('', why).  render_review.sh deletes it."""
    snap = os.path.join(rev, "snap_" + os.path.basename(odb))
    try:
        a = os.stat(odb)
        if a.st_size == 0:
            return "", "empty DB"
        run(["cp", "--reflink=auto", odb, snap], check=True, timeout=1800, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        b, c = os.stat(odb), os.stat(snap)
    except (OSError, subprocess.SubprocessError) as e:
        b = c = None
        why = f"copy failed: {e}"[:200]
    else:
        if (a.st_ino, a.st_size, a.st_mtime_ns) == (b.st_ino, b.st_size, b.st_mtime_ns) and c.st_size == a.st_size:
            return snap, ""
        why = "DB changed during the copy"
    try:
        os.unlink(snap)          # this function's own partial copy
    except OSError:
        pass
    return "", why


def smell_render(work, kit, stage, image, rid, summary, now=None, popen=subprocess.Popen, tools_roots=None, odb=None, tag="smell_review", nice=False, snapshot=False):
    """HOST half of (a): render the kit's CURRENT DB through the existing render_review.sh (an ot-run --direct job, 2 threads, read-only on the kit).
    Review dir = <work>/smell_review/<stage>-<time> (next to the kit; else ~/.local/state/noprog/smell_review/<id>).  -> (status, review_dir).
    The existing tool draws floorplan + density and, when the kit has a sign-off STA log, the failing-path overlay; it has no congestion heatmap, so the GRT
    congestion reports are named in summary.txt instead."""
    now = now or time.time()
    odb = odb or find_current_odb(work or "")
    if not odb:
        return "no-odb-yet", ""
    bad = host_unfit()
    if bad:
        return f"host-unfit: {bad}", ""      # COORD: no render is parked on a draining / root>95 % host (4 sat NOT RUN on epyc2)
    roots = tools_roots or [os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "/srv/opentallas-scratch2/claude/rt/current/tools",
                            os.path.expanduser("~/.local/lib/noprog/tools")]
    root = next((r for r in roots if all(os.path.isfile(os.path.join(r, t)) for t in RENDER_TOOLS)), None)
    if not root:
        return "no-render-tools", ""
    stamp = pst_stamp(now) + "PST"          # H6: the hosts' clock is UTC; the dir name says PST
    cands = [os.path.join(work, tag, f"{stage}-{stamp}"), os.path.expanduser(f"~/.local/state/noprog/{tag}/{rid}-{stage}-{stamp}")]
    if "/ot-jobs/" in (work or ""):
        cands.reverse()      # 5 of 30 failed renders sat in an ot-jobs work dir that was cleaned with the job: keep those in the persistent state dir
    rev = ""
    for c in cands:
        try:
            os.makedirs(os.path.join(c, "tools"), exist_ok=True)
            rev = c
            break
        except OSError:
            continue
    if not rev:
        return "no-writable-dir", ""
    for t in RENDER_TOOLS + tuple(x for x in RENDER_TOOLS_OPT if os.path.isfile(os.path.join(root, x))):
        with open(os.path.join(root, t), "rb") as f, open(os.path.join(rev, "tools", os.path.basename(t)), "wb") as g:
            g.write(f.read())
    summary = list(summary) + kit_smells(work, odb)          # COORD 11-25: reviewers saw only 'checkpoint' -> the kit's computed smells ride along
    try:
        sz = os.path.getsize(odb)
    except OSError:
        sz = 0
    read_odb = odb
    if snapshot:
        snap, why = odb_snapshot(odb, rev)
        if not snap:
            with open(os.path.join(rev, "SMELL.txt"), "w") as f:
                f.write(f"kit {work}\nstage {stage}\nodb {odb}\n")
            with open(os.path.join(rev, "render.log"), "w") as f:
                f.write(f"AP_REVIEW_ERROR snapshot: odb file {odb} is invalid ({why})\n")      # re-armed by vis_odb_refail
            return f"snapshot-failed: {why}", rev
        read_odb = snap
    mem = min(256, int(-(-max(8, 10 * sz / 2**30 + 4) // 1)))
    sig = os.path.join(rev, "signoff.json")
    with open(sig, "w") as f:
        json.dump({"verdict": "SMELL-MIDSTAGE", "reasons": summary}, f)
    with open(os.path.join(rev, "review.json"), "w") as f:
        json.dump({"id": rid, "kit": work, "odb": read_odb, "src_odb": odb, "signoff": sig, "image": image, "mem_gb": mem, "title": f"SMELL {stage}: " + "; ".join(summary)[:160],
                   "stage_paths": True, "npath": 50, "stamp_tz": "PST"}, f)
    cong = sorted(glob.glob(os.path.join(os.path.dirname(odb).replace("/results/", "/reports/"), "congestion-*.rpt")))
    with open(os.path.join(rev, "SMELL.txt"), "w") as f:
        f.write(f"kit {work}\nstage {stage}\nodb {odb}\n" + "".join(f"smell {x}\n" for x in summary) + "".join(f"congestion report {c}\n" for c in cong[-3:]))
        for lg in glob.glob(os.path.join(os.path.dirname(odb).replace("/results/", "/logs/"), "5_1_grt*.log")):
            lo = grt_layer_overflow(read_text(lg))
            if lo:
                f.write(f"GRT per-layer overflow ({os.path.basename(lg)}): {lo}\n")
    ot_run = shutil.which("ot-run") or os.path.expanduser("~/.local/bin/ot-run")
    argv = [ot_run, "--mem", str(mem), "--threads", "2", "--dir", rev, "--hosts", socket.gethostname(), "--no-spill", "--direct", "--", "bash", os.path.join(rev, "tools/render_review.sh"), rev]      # the review dir exists only on this host: 4 renders died 'NOT RUN ... exists on none of the candidate hosts' when ot-run picked another
    if nice:
        argv = ["nice", "-n", "10"] + argv
    try:
        with open(os.path.join(rev, "render.log"), "w") as lg:
            popen(argv, stdout=lg, stderr=subprocess.STDOUT, start_new_session=True, stdin=subprocess.DEVNULL)
    except OSError as e:
        return f"launch-failed: {e}", rev
    return "rendering", rev


GRT_LAYER_RE = re.compile(r"^(M\d+|V\d+)\s+\d+\s+\d+\s+[\d.]+%\s+(\d+)\s*/\s*(\d+)\s*/\s*(\d+)", re.M)


def grt_layer_overflow(text):
    """per-layer GRT overflow of the LAST congestion table in a GRT log: 'M2 120, M3 15' (total column), '' when none.  Pure."""
    last = {}
    for m in GRT_LAYER_RE.finditer(text or ""):
        last[m.group(1)] = int(m.group(4))
    return ", ".join(f"{k} {v}" for k, v in sorted(last.items()) if v)


# ---------------------------------------------------------------- VIS checkpoints (OWNER 04:3x via COORD): every kit is rendered when global placement ends and when GRT ends
VIS_CHECKPOINTS = (("PLACE-GP", ("3_3_place_gp.odb", "3_place.odb")), ("GRT", ("5_1_grt.odb",)))      # first non-empty name wins (stage_odb_cap emptied 3_3_place_gp.odb on kits started before 11-25)


VIS_SETTLE_S = 180        # the checkpoint DB must be untouched for 3 min: 6 of 28 first renders read a DB still being written (ORD-0054 odb invalid: basic_ios::clear)
VIS_MAX_TRIES = 3
# FABLE-FLOW-1920 F5 (COORD 11-25): 26 checkpoint renders FAILED with ORD-0054 'odb file ... is invalid: basic_ios::clear'.  The 3-min settle was not enough: the DB was read
# while its stage was still running, or a kit's (older, pinned) STAGE-CAP watcher / a resume emptied it under the render (it keeps the mtime, and it cannot see the render's open file
# inside docker).  So a checkpoint DB is rendered only after its stage is done (stage_done), from a private snapshot copy in the review dir (smell_render snapshot=True), and an
# ODB-invalid failure is re-armed (vis_odb_refail) up to VIS_ODB_RETRIES times per DB.
VIS_ODB_INVALID = re.compile(r"ORD-0054|odb file \S+ is invalid|basic_ios::clear")
VIS_ODB_RETRIES = 3
STAGE_NUM_RE = re.compile(r"^(\d)_(?:(\d+)_)?")


def pst_stamp(now, fmt="%m%d-%H%M"):
    """FABLE-FLOW-1920 H6: hosts run in UTC; render dir names carry the PST time (and say so)"""
    try:
        import datetime as _dt
        from zoneinfo import ZoneInfo
        return _dt.datetime.fromtimestamp(now, ZoneInfo("America/Los_Angeles")).strftime(fmt)
    except Exception:
        return time.strftime(fmt, time.localtime(now))


def _stage_key(name):
    m = STAGE_NUM_RE.match(name)
    return (int(m.group(1)), int(m.group(2) or 99)) if m else None


def stage_done(odb):
    """the ORFS stage that wrote odb has ended: its log (results -> logs, <stem>.log) ends with the 'Elapsed time:' line ORFS prints when a stage exits, or a LATER stage's DB or
    log exists that is not older than this DB (a resumed kit re-writes from an earlier stage, so older later-stage files prove nothing).  Pure apart from the filesystem."""
    d, n = os.path.dirname(odb), os.path.basename(odb)
    stem = n[:-4] if n.endswith(".odb") else n
    logd = d.replace("/results/", "/logs/")
    try:
        with open(os.path.join(logd, stem + ".log"), "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 8192))
            if b"Elapsed time:" in f.read():
                return True
    except OSError:
        pass
    me = _stage_key(stem)
    try:
        mt = os.stat(odb).st_mtime
    except OSError:
        return False
    if me is None:
        return False
    for dd, ext in ((d, ".odb"), (logd, ".log")):
        try:
            names = os.listdir(dd)
        except OSError:
            continue
        for x in names:
            if not x.endswith(ext) or x.startswith(stem + "."):
                continue
            k = _stage_key(x)
            if k and k > me:
                try:
                    if os.stat(os.path.join(dd, x)).st_mtime >= mt:
                        return True
                except OSError:
                    pass
    return False


def vis_odb_refail(work, cp, odb, state_root=None):
    """-> True when every earlier checkpoint render of this exact DB failed reading it (ORD-0054 / invalid odb, render.log) and fewer than VIS_ODB_RETRIES did: the render is
    re-armed.  Render dirs: <work>/vis_review/<cp>-* and (ot-jobs kits) ~/.local/state/noprog/vis_review/*-<cp>-*; SMELL.txt names the DB each one read."""
    pats = [os.path.join(work or "", "vis_review", f"{cp.lower()}-*")]
    if "/ot-jobs/" in (work or ""):
        pats.append(os.path.join(state_root or os.path.expanduser("~/.local/state/noprog/vis_review"), f"*-{cp.lower()}-*"))
    bad = 0
    for pat in pats:
        for rd in glob.glob(pat):
            try:
                if f"odb {odb}\n" not in read_text(os.path.join(rd, "SMELL.txt")):
                    continue
                txt = read_text(os.path.join(rd, "render.log"))
            except OSError:
                continue
            if "AP_REVIEW_PNG" in txt or not VIS_ODB_INVALID.search(txt):
                return False            # rendered, still running, or failed for another reason (vis_retry owns those)
            bad += 1
    return 0 < bad < VIS_ODB_RETRIES


def vis_retry(state, now, read=read_text):
    """HOST: a render whose log says NOT RUN (ot-run could not place it), a failed dump or an ERROR is retried (the DB key leaves vis_done) up to VIS_MAX_TRIES times, 20 min apart;
    one that wrote AP_REVIEW_PNG is finished.  state['vis_pending'] = {key: {dir, tries, t}}.  -> [(key, outcome)]"""
    pend = state.setdefault("vis_pending", {})
    done = state.setdefault("vis_done", {})
    out = []
    for key, e in list(pend.items()):
        if now - float(e.get("t", 0)) < 1200:
            continue
        try:
            txt = read(os.path.join(e["dir"], "render.log"))
        except OSError:
            txt = ""
        if "AP_REVIEW_PNG" in txt:
            del pend[key]
            out.append((key, "rendered"))
        elif ("NOT RUN" in txt or "AP_REVIEW_ERROR" in txt or "exit 1" in txt or not txt) and int(e.get("tries", 1)) < VIS_MAX_TRIES:
            done.pop(key, None)
            e["tries"] = int(e.get("tries", 1)) + 1
            e["t"] = now
            out.append((key, "retry"))
        elif "ot-run:" in txt and "RAN" not in txt and "NOT RUN" not in txt:
            continue
        else:
            del pend[key]
            out.append((key, "failed"))
    return out


def vis_candidates(work, done):
    """-> [(checkpoint, odb)] of the kit's checkpoint DBs that exist and were not rendered yet (done: {odb|mtime: t}).  Pure apart from the filesystem."""
    out = []
    for cp, names in VIS_CHECKPOINTS:
        found = False
        for name in names:
            if found:
                break
            for g in (f"run/results/*/*/*/{name}", f"gen/*/run/results/*/*/*/{name}", f"results/*/*/*/{name}"):
                for p_ in glob.glob(os.path.join(work or "", g)):
                    try:
                        stt = os.stat(p_)
                    except OSError:
                        continue
                    if stt.st_size == 0:
                        continue          # a zero-byte placeholder is no DB
                    found = True
                    k = f"{p_}|{int(stt.st_mtime)}"
                    if time.time() - stt.st_mtime < VIS_SETTLE_S or not stage_done(p_):
                        continue          # F5: only a DB whose stage has ended
                    if k not in done or vis_odb_refail(work, cp, p_):
                        out.append((cp, p_, k))
    return out


def vis_running(state_dir, now):
    """one render job per host at a time: the marker holds the pid of the last launch; a live pid (or one launched < 10 min ago) blocks the next"""
    try:
        m = json.load(open(os.path.join(state_dir, "vis_running.json")))
    except (OSError, ValueError):
        return False
    try:
        pid = int(m["pid"])
        if pid > 0:
            os.kill(pid, 0)
            return True
        raise ValueError("no pid")
    except (OSError, KeyError, ValueError, TypeError):
        return now - float(m.get("t", 0)) < 600


PP_DRIVER_ROOTS = (os.path.dirname(os.path.abspath(__file__)), "/srv/opentallas-scratch2/claude/rt/current/tools/autopilot")


ROOT_FULL_PCT = 95
SCRATCH_FLOOR_GB = 150          # ot-run's own scratch floor: a host below it is 'DRAINING' and refuses jobs


def host_unfit(paths=("/", "/srv/opentallas-scratch2"), statvfs=os.statvfs, drain_file=None):
    """COORD: never park a render on a draining host or one whose root is above 95 %.  -> reason or ''.  A host is draining when its scratch free space is under the ot-run floor
    (150 GB) or an ot-run drain marker exists.  Pure given statvfs."""
    for i, p in enumerate(paths):
        try:
            v = statvfs(p)
        except OSError:
            continue
        total, free = v.f_blocks * v.f_frsize, v.f_bavail * v.f_frsize
        if i == 0 and total and 100.0 * (1 - free / total) > ROOT_FULL_PCT:
            return f"root {100.0 * (1 - free / total):.0f} % full (> {ROOT_FULL_PCT} %)"
        if i > 0 and free / 2**30 < SCRATCH_FLOOR_GB:
            return f"{p} has {free / 2**30:.0f} GB free (< {SCRATCH_FLOOR_GB} GB scratch floor: draining)"
    return ""


def pp_launch(item, state_dir, now, popen=subprocess.Popen, roots=None):
    """HOST: run the post-placement review kit (post_place_review.py: ideal-clock top-50 paths, density, RUDY, flight lines, macro/PG overlay -> <kit>/review/) for one queued item,
    nice 10, only while no other render of this host runs.  -> 'launched' | 'no-driver' | 'failed: ...'"""
    bad = host_unfit()
    if bad:
        return f"host-unfit: {bad}"      # stays 'pp_done' with this result; the render is retried by relocating (the hub or a lane copies the DB to a fit host), never parked here
    drv = next((os.path.join(r, "post_place_review.py") for r in (roots or PP_DRIVER_ROOTS) if os.path.isfile(os.path.join(r, "post_place_review.py"))), None)
    if not drv:
        return "no-driver"
    argv = ["nice", "-n", "10", "python3", "-I", drv, "--kit", item["kit"], "--odb", item["odb"], "--image", item.get("image", ""), "--id", item.get("id", "x")]
    try:
        pr = popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True, stdin=subprocess.DEVNULL)
    except OSError as e:
        return f"failed: {e}"
    os.makedirs(state_dir, exist_ok=True)
    save_json(os.path.join(state_dir, "vis_running.json"), {"pid": getattr(pr, "pid", 0), "t": now, "dir": os.path.join(item["kit"], "review")})
    return "launched"


def placed_odb(work):
    """the kit's post-global-placement DB: 3_3_place_gp.odb, else 3_place.odb (first non-empty), '' when none"""
    for name in ("3_3_place_gp.odb", "3_place.odb"):
        for g in (f"run/results/*/*/*/{name}", f"gen/*/run/results/*/*/*/{name}", f"results/*/*/*/{name}"):
            for p_ in glob.glob(os.path.join(work or "", g)):
                try:
                    if os.stat(p_).st_size > 0:
                        return p_
                except OSError:
                    pass
    return ""


def pp_queue_smells(rows, state, now):
    """COORD 06:1x item 3: a kit that SMELLs also gets the post-place review kit (once per kit per 24 h).  -> number queued"""
    todo = state.setdefault("pp_todo", [])
    done = state.setdefault("pp_done", {})
    n = 0
    for r in rows:
        if not r.get("smell") or smell_exempt(r) or not r.get("work") or ECO_RE.search(str(r.get("work"))) or re.search(r"/eco_\d", str(r.get("work"))):
            continue
        key = f"smell|{r['work']}"
        if (key in done and now - float(done[key].get("t", 0)) < 86400) or any(x["key"] == key for x in todo):
            continue
        odb = placed_odb(r["work"])
        if odb:
            todo.append({"key": key, "kit": r["work"], "odb": odb, "image": r.get("image", ""), "id": (r.get("container") or "x")[:40]})
            n += 1
    return n


def vis_pass(rows, state, state_dir, now, render=smell_render, pp=None):
    """HOST: launch at most ONE checkpoint render (nice 10) this pass, when none is running.  Marks row['vis'] = {checkpoint, status, dir} for the hub's lanes/VIS-QUEUE.tsv."""
    done = state.setdefault("vis_done", {})
    vis_retry(state, now)
    if os.environ.get("NOPROG_VIS_MODE") == "off" or vis_running(state_dir, now):
        return None
    todo = state.setdefault("pp_todo", [])
    pp_queue_smells(rows, state, now)
    if todo:
        item = todo.pop(0)
        res = (pp or pp_launch)(item, state_dir, now)
        if res.startswith("host-unfit"):
            todo.insert(0, item)
            return None
        state.setdefault("pp_done", {})[item["key"]] = {"t": now, "res": res}
        if res == "launched":
            return None
    for r in rows:
        if smell_exempt(r) or not r.get("work") or ECO_RE.search(str(r.get("work"))) or ECO_RE.search(str(r.get("container"))) or re.search(r"/eco_\d", str(r.get("work"))):
            continue            # an ECO loop re-runs a kit that was already rendered at its checkpoints (dry run 04:09: eco_2026... containers filled the first queue)
        for cp, odb, key in vis_candidates(r["work"], done):
            box = {}
            def popen(argv, **kw):
                pr = subprocess.Popen(argv, **kw)
                box["pid"] = pr.pid
                return pr
            status, rev = render(r["work"], r.get("kit") or r["work"], cp.lower(), r.get("image", ""), (r.get("container") or "x")[:40], [f"checkpoint {cp}"], now=now,
                                 popen=popen, odb=odb, tag="vis_review", nice=True, snapshot=True)
            if str(status).startswith("host-unfit"):
                return None            # try again on a later tick; never parked and never marked done
            done[key] = now
            if status == "rendering":
                os.makedirs(state_dir, exist_ok=True)
                save_json(os.path.join(state_dir, "vis_running.json"), {"pid": box.get("pid", 0), "t": now, "dir": rev})
                r["vis"] = {"checkpoint": cp, "status": status, "dir": rev, "odb": odb}
                state.setdefault("vis_pending", {})[key] = {"dir": rev, "tries": state.get("vis_pending", {}).get(key, {}).get("tries", 1), "t": now}
                if key not in state.setdefault("pp_done", {}) and not any(x["key"] == key for x in todo):
                    todo.append({"key": key, "kit": r["work"], "odb": odb, "image": r.get("image", ""), "id": (r.get("container") or "x")[:40]})
                return r
    return None


def smell_pending_write(rows, host, path=None):
    """HOST: every scan writes the smelling kits to a local fallback file, so a down hub loses nothing.  -> (path, n)"""
    path = path or os.path.join(STATE_DIR, "smell_pending.tsv")
    ls = [f"{r.get('host')}\t{r.get('type')}\t{r.get('stage')}\t{r.get('container')}\t{'; '.join(t for _, t in r['smell'])[:400]}" for r in rows if r.get("smell")]
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write("# SMELL fallback (hub unreachable or not yet read): host, type, stage, container, triggers\n" + "".join(l + "\n" for l in ls))
    except OSError:
        return path, 0
    return path, len(ls)


SMELL_COLS = ("t", "kit", "die", "type", "stage", "trigger", "value", "render", "owner")


def smell_tsv_append(recs, path=None):
    """lanes/SMELL.tsv, ONE ROW PER TRIGGER (COMPOSE-FAST and the cut lanes read it for the full/probe split): t, kit, die, type, stage, trigger, value, render path, owning lane.
    -> rows written.  Exact duplicate rows are skipped."""
    path = path or os.path.join(COORD, "lanes/SMELL.tsv")
    known = set(read_lines(path))
    out = []
    for d in recs:
        line = "\t".join(str(d.get(c, "")).replace("\t", " ").replace("\n", " ") for c in SMELL_COLS)
        if line not in known:
            out.append(line)
            known.add(line)
    if not out:
        return 0
    new_file = not os.path.exists(path)
    with open(path, "a") as f:
        if new_file:
            f.write("\t".join(SMELL_COLS) + "\n")
        f.write("\n".join(out) + "\n")
    return len(out)


def smell_recipients(tag, owner):
    """lanes a SMELL / RENDER post is addressed to: the die's FP-CONVERGE lane first, then the type owner unless that is COORD (wave kits have no OT_LANE and resolved to COORD:
    29 SMELL rows went to COORD, 06:2x).  A kit of an unknown die falls back to COORD, the only lane left."""
    to = []
    if tag in ("QC", "KV", "S81", "HEAD"):
        to.append(f"FP-CONVERGE-{tag}")
    if owner and owner != "COORD":
        to.append(owner)
    return ", ".join(to) or "COORD"


def smell_pass(rows, seen, now, post=True, render=None, poster=None):
    """HUB: dedupe smelling rows per (host, container, class); dry run for the first SMELL_DRY_S after the first pass (post the would-fire list once), then live:
    render, lanes/SMELL.tsv, post to the die's FP-CONVERGE-<DIE> lane and the type owner.  Never cancels.  -> (mode, fired [dict])"""
    if os.environ.get("NOPROG_SMELL_MODE") == "off" or os.path.exists(os.path.join(COORD, "lanes/SMELL-WATCHDOG.off")):
        return "off", []
    poster = poster or os.environ.get("NOPROG_SMELL_LANE", "SMELL-WATCH")
    st = seen.setdefault("smell", {})
    t0 = seen.setdefault("smell_t0", now)
    live = now - t0 >= SMELL_DRY_S
    new = []
    for r in rows:
        if not r.get("smell") or smell_exempt(r):
            continue
        for cls in sorted({c for c, _ in r["smell"]}):
            k = f"{r.get('kit') or r.get('work') or r.get('container')}|{cls}"      # COORD 06:2x: ONE row per kit + class (a restarted container of the same kit is a repeat)
            e = st.setdefault(k, {"first": now, "fired": False})
            if any(k == n[0] for n in new):
                continue
            e["last"] = now
            if not e["fired"]:
                new.append((k, cls, r))
    for k in [k for k, e in st.items() if now - float(e.get("last", now)) > 24 * 3600]:
        del st[k]
    txt = lambda r, cls: "; ".join(t for c, t in r["smell"] if c == cls)
    if not live:
        if new and not seen.get("smell_dry_posted"):
            seen["smell_dry_posted"] = now
            ls = [f"{r.get('host')} {r.get('type')} {r.get('stage')} [{cls}] {txt(r, cls)[:110]}" for _, cls, r in new]
            if post:
                _post(poster, f"DRYRUN [{poster} -> COORD] SMELL would-fire list ({len(ls)} kit-classes, live in {int((SMELL_DRY_S - (now - t0)) / 60)} min; nothing cancelled, no render yet): " + " | ".join(ls[:60]))
        return "dry", []
    fired, path = [], os.path.join(COORD, "lanes/SMELL.tsv")
    for k, cls, r in new:
        status, rev = ("no-render-hook", "")
        if render:
            status, rev = render(r, [t for c, t in r["smell"] if c == cls])
        die = DIE_TAG.get(die_of(" ".join(str(r.get(x) or "") for x in ("container", "kit", "work", "ident"))), "?")
        rec = {"t": now, "type": canonical_type(r.get("kit") or r.get("work"), r.get("type", "")), "die": die, "stage": r.get("stage", ""), "class": cls, "metric": txt(r, cls)[:300], "host": r.get("host"),
               "render": f"{r.get('host')}:{rev} ({status})" if rev else status, "owner": owner_of([r]), "unit": r.get("unit") or r.get("container"),
               "kit": r.get("kit") or r.get("work") or "", "triggers": [t for c, t in r["smell"] if c == cls]}
        fired.append(rec)
        st[k]["fired"] = True
        st[k]["rec"] = rec["render"]
    if fired:
        try:
            recs = []
            for d in fired:
                for tr in d["triggers"]:
                    recs.append({"t": int(d["t"]), "kit": d["kit"], "die": d["die"], "type": d["type"], "stage": d["stage"], "trigger": d["class"], "value": tr,
                                 "render": d["render"], "owner": d["owner"]})
            smell_tsv_append(recs, path)
        except OSError as e:
            print(f"noprog smell: cannot write {path}: {e}", file=sys.stderr)
        if post:
            fb = os.path.join(STATE_DIR, "smell_fallback.tsv")
            groups = {}
            for d in fired:
                groups.setdefault((d["die"], d["owner"]), []).append(d)
            for (tag, owner), ds in sorted(groups.items()):
                to = smell_recipients(tag, owner)
                body = " | ".join(f"{d['type']} {d['stage']} [{d['class']}] {d['host']}: {d['metric'][:160]}; render {d['render']}" for d in ds[:25])
                msg = (f"SMELL [{poster} -> {to}; cc {DIE_INT.get(tag, 'COORD')}] {len(ds)} kit-class(es): {body}. "
                       f"Early trigger (OWNER 04:1x): start the visual review and the structural root-cause fix now; the kits keep running and are NOT cancelled "
                       f"unless one also meets the unsignable-and-over-3-h rule. Evidence lanes/SMELL.tsv.")
                if not _post_ok(poster, msg):
                    os.makedirs(STATE_DIR, exist_ok=True)
                    with open(fb, "a") as f:
                        f.write(f"{int(now)}\t{msg}\n")
                    print(f"noprog smell: HUB POST FAILED, wrote {fb}", file=sys.stderr)
    return "live", fired


def vis_queue_append(rows, now, post=False):
    """HUB: one lanes/VIS-QUEUE.tsv row per checkpoint render a host launched (row['vis']).  The file is a LOG only (OWNER 04:5x: reviews are self-launched by the
    owning lanes, no central queue); the die's FP-CONVERGE-<DIE> lane and the type owner are told directly, with the render paths.  -> number of rows appended"""
    new = [r for r in rows if r.get("vis")]
    if not new:
        return 0
    path = os.path.join(COORD, "lanes/VIS-QUEUE.tsv")
    known = set(read_lines(path))
    out = []
    posts = {}
    for r in new:
        v = r["vis"]
        die = DIE_TAG.get(die_of(" ".join(str(r.get(x) or "") for x in ("container", "kit", "work", "ident"))), "?")
        line = "\t".join(str(x).replace("\t", " ") for x in (int(now), canonical_type(r.get("kit") or r.get("work"), r.get("type", "")), die, v["checkpoint"], f"{r.get('host')}:{v['dir']}", v["status"], owner_of([r]), r.get("kit", ""), "LOG"))
        if line not in known:
            out.append(line)
            if post:
                posts.setdefault((die, owner_of([r])), []).append(f"{r.get('type', '')} {v['checkpoint']} on {r.get('host')}: {r.get('host')}:{v['dir']}")
    for (die, owner), items in sorted(posts.items()):
        _post(os.environ.get("NOPROG_SMELL_LANE", "SMELL-WATCH"),
              f"RENDER [{os.environ.get('NOPROG_SMELL_LANE', 'SMELL-WATCH')} -> {smell_recipients(die, owner)}; cc {DIE_INT.get(die, 'COORD')}] {len(items)} checkpoint render(s) started: " + " | ".join(items[:25])
              + " (floorplan.png, density.png, SMELL.txt with the GRT per-layer overflow, written when the job ends; render.log there). Launch your own Fable/Opus review (OWNER 04:5x: self-launched, "
                "no central queue; lanes/VIS-QUEUE.tsv is a log). Not in the existing tool: congestion heatmap; the post-place kit (post_place_review.py) adds RUDY, flight lines, macro/PG overlay.")
    if not out:
        return 0
    new_file = not os.path.exists(path)
    with open(path, "a") as f:
        if new_file:
            f.write("t\ttype\tdie\tcheckpoint\trender\tstatus\towner\tkit\treview\n")
        f.write("\n".join(out) + "\n")
    try:
        smell_tsv_append(vis_as_smell_rows(out))
    except OSError:
        pass
    return len(out)


def vis_status_sync(path=None, runner=None):
    """HUB: rows of lanes/VIS-QUEUE.tsv still 'rendering' get their real state from the host that ran them: RENDERED (density.png/floorplan.png written), FAILED (render.log
    says NOT RUN / ERROR / exit 1 and no PNG, retried by the host up to VIS_MAX_TRIES times) or GONE (the render dir is cleaned).  Verdict rows are left alone.  -> rows changed"""
    path = path or os.path.join(COORD, "lanes/VIS-QUEUE.tsv")
    runner = runner or (lambda h, cmd: run_host(h, cmd, timeout=120).stdout)
    try:
        lines = open(path).read().splitlines()
    except OSError:
        return 0
    by = {}
    for ln in lines:
        c = ln.split("\t")
        if len(c) >= 6 and c[5] == "rendering" and ":" in c[4]:
            h, _, d = c[4].partition(":")
            by.setdefault(h, set()).add(d)
    state = {}
    for h, ds in by.items():
        cmd = "; ".join(f"d={shlex.quote(d)}; if [ -f \"$d/density.png\" ] || [ -f \"$d/floorplan.png\" ]; then echo RENDERED $d; elif [ ! -d \"$d\" ]; then echo GONE $d; "
                         f"elif grep -q -E 'NOT RUN|AP_REVIEW_ERROR|exit 1' \"$d/render.log\" 2>/dev/null; then echo FAILED $d; else echo rendering $d; fi" for d in sorted(ds))
        try:
            for ln in runner(h, cmd).splitlines():
                st_, _, d = ln.partition(" ")
                if st_ in ("RENDERED", "GONE", "FAILED"):
                    state[(h, d)] = st_
        except (subprocess.SubprocessError, OSError):
            continue
    if not state:
        return 0
    try:
        cur = open(path).read().splitlines()
    except OSError:
        return 0
    out, n = [], 0
    for ln in cur:
        c = ln.split("\t")
        if len(c) >= 6 and c[5] == "rendering" and ":" in c[4]:
            h, _, d = c[4].partition(":")
            if (h, d) in state:
                c[5] = state[(h, d)]
                n += 1
                ln = "\t".join(c)
        out.append(ln)
    if n:
        tmp = path + f".tmp{os.getpid()}"
        with open(tmp, "w") as f:
            f.write("\n".join(out) + "\n")
        os.replace(tmp, path)
    return n


_COV_CACHE = {}


def coverage_types(path=None):
    """{canonical type} of lanes/VIS-COVERAGE.tsv (col 2), cached per file mtime.  -> (set, {type: die})"""
    path = path or os.path.join(COORD, "lanes/VIS-COVERAGE.tsv")
    try:
        mt = os.stat(path).st_mtime
    except OSError:
        return set(), {}
    if _COV_CACHE.get(path, (None,))[0] != mt:
        types, die = set(), {}
        for ln in read_lines(path):
            c = ln.split("\t")
            if len(c) > 2 and not ln.startswith("#") and c[0] != "die":
                types.add(c[1])
                die[c[1]] = c[0]
        _COV_CACHE[path] = (mt, types, die)
    return _COV_CACHE[path][1], _COV_CACHE[path][2]


def canonical_type(kit, fallback="", cov=None):
    """COORD 06:3x: the VIS-QUEUE type column carries the VIS-COVERAGE type name, not a kit id or a container fragment.  The kit path names it (gen/<type>, or <type>_<timestamp>);
    the longest candidate present in VIS-COVERAGE wins, else the kit's own name without its timestamp.  Pure given cov."""
    types = coverage_types()[0] if cov is None else cov
    parts = [x for x in str(kit or "").rstrip("/").split("/") if x]
    cands = []
    for x in reversed(parts[-4:]):
        for y in (x, re.sub(r"_\d{10,}$", "", x)):
            cands.append(y)
            z = y
            while "__" in z:                      # peel __pv.. / __r.. suffixes
                z = z.rsplit("__", 1)[0]
                cands.append(z)
    for c in cands:
        if c in types:
            return c
    base = re.sub(r"_\d{10,}$", "", parts[-1]) if parts else ""
    if base in ("gen", "i1", "run") and len(parts) > 1:
        base = re.sub(r"_\d{10,}$", "", parts[-2])
    return base or fallback


def vis_type_backfill(path=None, cov=None):
    """HUB: rewrite the type column (col 2) of lanes/VIS-QUEUE.tsv from the kit column (col 8).  -> rows changed"""
    path = path or os.path.join(COORD, "lanes/VIS-QUEUE.tsv")
    try:
        lines = open(path).read().splitlines()
    except OSError:
        return 0
    out, n = [], 0
    for ln in lines:
        c = ln.split("\t")
        if len(c) >= 8 and c[0] != "t" and c[7]:
            t = canonical_type(c[7], c[1], cov)
            if t and t != c[1]:
                c[1] = t
                n += 1
                ln = "\t".join(c)
        out.append(ln)
    if n:
        tmp = path + f".tmp{os.getpid()}"
        with open(tmp, "w") as f:
            f.write("\n".join(out) + "\n")
        os.replace(tmp, path)
    return n


def vis_sta_sync(path=None, runner=None, post=True, now=None):
    """HUB: the quick setup STA of the post-place kit (<kit>/review/summary.json: WNS, TNS, endpoints below -150 ps at the SDC period) goes into column 10 of every VIS-QUEUE row of that
    kit + checkpoint, verdict rows included (COORD 08:xx).  A WNS below -150 ps is a SMELL (trigger STA-WNS in lanes/SMELL.tsv) and the owner + die FP lane are told at once, once per kit.
    -> number of rows changed"""
    path = path or os.path.join(COORD, "lanes/VIS-QUEUE.tsv")
    now = now or time.time()
    runner = runner or (lambda h, cmd: run_host(h, cmd, timeout=120).stdout)
    try:
        lines = open(path).read().splitlines()
    except OSError:
        return 0
    want = {}
    for ln in lines:
        c = ln.split("\t")
        if len(c) >= 8 and c[0] != "t" and c[7] and (len(c) < 10 or not c[9]):
            want.setdefault(c[4].partition(":")[0], set()).add(c[7])
    got = {}
    for h, kits in want.items():
        cmd = "; ".join(f"echo ==={shlex.quote(k)}; cat {shlex.quote(k)}/review/summary.json 2>/dev/null | head -c 20000" for k in sorted(kits))
        try:
            out = runner(h, cmd)
        except (subprocess.SubprocessError, OSError):
            continue
        for blk in out.split("==="):
            k, _, js = blk.partition("\n")
            try:
                d = json.loads(js)
            except ValueError:
                continue
            if d.get("sta_cell"):
                got[(h, k.strip())] = (d["sta_cell"], d.get("sta") or {})
    if not got:
        return 0
    out, n, smelly = [], 0, {}
    for ln in lines:
        c = ln.split("\t")
        if len(c) >= 8 and c[0] != "t" and (c[4].partition(":")[0], c[7]) in got and (len(c) < 10 or not c[9]):
            cell, sta = got[(c[4].partition(":")[0], c[7])]
            c = (c + [""] * 10)[:10] if len(c) < 10 else c
            c[9] = cell
            n += 1
            ln = "\t".join(c)
            if sta.get("wns_ps") is not None and sta["wns_ps"] < -150.0:
                smelly[(c[4].partition(":")[0], c[7])] = (c[1], c[2], c[3], c[6], c[4], sta)
        out.append(ln)
    if n:
        tmp = path + f".tmp{os.getpid()}"
        with open(tmp, "w") as f:
            f.write("\n".join(out) + "\n")
        os.replace(tmp, path)
    if smelly:
        recs, msgs = [], {}
        for (h, k), (typ, die, cp, owner, render, sta) in smelly.items():
            recs.append({"t": int(now), "kit": k, "die": die, "type": typ, "stage": cp, "trigger": "STA-WNS", "value": f"quick setup STA WNS {sta['wns_ps']:.1f} ps (< -150), TNS {sta.get('tns_ps', 0):.0f}, {sta.get('n_below_150', 0)} endpoints below -150, T {sta.get('period_ps', 0):g} ps",
                         "render": render, "owner": owner})
            msgs.setdefault((die, owner), []).append(f"{typ} {cp}: WNS {sta['wns_ps']:.1f} ps, TNS {sta.get('tns_ps', 0):.0f}, {sta.get('n_below_150', 0)} endpoints < -150; {render}")
        smell_tsv_append(recs)
        if post:
            for (die, owner), items in sorted(msgs.items()):
                _post(os.environ.get("NOPROG_SMELL_LANE", "SMELL-WATCH"), f"SMELL [SMELL-WATCH -> {smell_recipients(die, owner)}; cc {DIE_INT.get(die, 'COORD')}] STA-WNS: quick setup STA (TT, placement parasitics, ideal clock) WNS below -150 ps: " + " | ".join(items[:20]) + ". Early trigger: start the structural fix now; the kit keeps running.")
    return n


def vis_as_smell_rows(lines):
    """VIS-QUEUE.tsv lines (t, type, die, checkpoint, render, status, owner, kit, LOG) as SMELL.tsv rows with trigger CHECKPOINT"""
    recs = []
    for l in lines:
        c = l.split("\t")
        if len(c) >= 8:
            recs.append({"t": c[0], "kit": c[7], "die": c[2], "type": c[1], "stage": c[3], "trigger": "CHECKPOINT", "value": c[3] + " render " + c[5], "render": c[4], "owner": c[6]})
    return recs


def _post_ok(lane_from, txt):
    try:
        return subprocess.run(["bash", os.path.join(COORD, "bin/post.sh"), lane_from, txt], capture_output=True, text=True, timeout=300).returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


def host_smell_render(row):
    """hub -> host: run the render half on row['host'] over ssh (nothing runs on the hub itself).  -> (status, review_dir)"""
    h = row.get("host")
    args = [row.get("work") or "", row.get("kit") or "", row.get("stage") or "", row.get("image") or "", (row.get("container") or "x")[:40]]
    smell = [t for _, t in row.get("smell", [])]
    cmd = "python3 -I ~/.local/lib/noprog/noprog_watchdog.py smell-render " + " ".join(shlex.quote(a) for a in args) + " " + shlex.quote(json.dumps(smell))
    try:
        p = run_host(h, cmd, timeout=120)
        line = (p.stdout.strip().splitlines() or ["render-failed: no output"])[-1]
        st, _, rev = line.partition("\t")
        return st, rev
    except (subprocess.SubprocessError, OSError) as e:
        return f"render-failed: {str(e)[:60]}", ""



def design_fail_exempt(r):
    ident = " ".join(str(r.get(k) or "") for k in ("container", "type", "kit", "work", "ident"))
    ex = unsignable_exempt(ident, r.get("prio", ""), r.get("kind", ""))
    if ex:
        return ex
    if re.search(r"(?i)re-?sign", ident):
        return "re-sign"
    return ""


def design_fail_evidence(r, track, now):
    """-> evidence text or ''.  track: the per-unit {first, ov0} overflow clock (reset by a >= 2 % fall).  Pure apart from track."""
    if r.get("verdict") != GRT_LABEL or not str(r.get("why") or "").startswith("DESIGN-FAIL") or design_fail_exempt(r):
        return ""
    why = str(r.get("why") or "")
    # NOPROG-GRTFALL-1124 (COORD): the round-10 'overflow > 1000' label used to cancel on the FIRST pass, so 3 KV HGI GRT kits ~2 h in whose
    # overflow was still falling (28701 -> 12166, 25885 -> 10162) were stopped 'design'.  The label alone is never cancel evidence now:
    # every DESIGN-FAIL label (threshold, GRT-0273, rising) cancels only after the overflow has not fallen 2 % for DF_FLAT_S.
    ov = r.get("grt_ovf")
    if ov is None:
        return ""
    ov = float(ov)
    if grt_repair_progress(r):
        track.update(first=now, ov0=ov, last=now, ov=ov)     # NOPROG-GRTHOLD-1124: GRT routing finished, post-route repair progressing: restart the flat clock
        return ""
    if track.get("ov0") is None or ov < float(track["ov0"]) * (1 - MIN_IMPROVE):
        track.update(first=now, ov0=ov)
    track.update(last=now, ov=ov)
    if float(r.get("age_h") or 0) <= DF_MIN_AGE_H:
        return                                          # NOPROG-GRTHOLD-1124: a job of 3 h or less is never a design cancel (the overflow clock above keeps running)
    # NOPROG-GRTFALL-1124: flat means no 2 % fall for DF_FLAT_S AND for 1.5 GRT rounds (slow FastRoute rounds are not a stall)
    if now - float(track["first"]) >= max(DF_FLAT_S, 1.5 * float(r.get("grt_round_s") or 0)):
        return f"GRT-LABEL {why}; overflow {float(track['ov0']):.0f} -> {ov:.0f}, no 2 % fall in {(now - float(track['first'])) / 3600:.1f} h; {str(r.get('detail') or '')[:100]}"
    return ""


def design_fail_pass(rows, seen, now, post=True, cancel=ot_run_cancel, wave_cancel=wave_cancel_rows):
    """HUB: cancel GRT-LABEL DESIGN-FAIL containers (see above).  -> cancelled [dict]"""
    if os.environ.get("NOPROG_DESIGNFAIL_MODE") == "report" or os.path.exists(os.path.join(COORD, "lanes/DESIGNFAIL-WATCHDOG.off")):
        return []
    poster = os.environ.get("NOPROG_POST_LANE", "FLEET-WATCH-1015")
    track = seen.setdefault("df_track", {})
    gfc = seen.setdefault("gf_cancelled", {})
    done_k = seen.setdefault("df_done", {})
    keeps = keep_posts()
    units = {}
    for r in rows:
        k = f"{r.get('host')}|{r.get('unit') or r.get('container')}"
        units.setdefault(k, []).append(r)
    done = []
    for k, rs in sorted(units.items()):
        pls = [None if plateau_mode_off() else plateau_evidence(r) for r in rs]
        evs = [(p[1] if p else design_fail_evidence(r, track.setdefault(f"{r.get('host')}|{r.get('container')}", {}), now)) for r, p in zip(rs, pls)]
        if not rs[0].get("unit") or not all(evs) or k in done_k:
            continue                                     # every container of the unit must have failed (a sibling stage still running keeps it)
        r, ev = rs[0], evs[0]
        cls = pls[0][0] if pls[0] else "DESIGN-FAIL GRT-LABEL"
        u = r["unit"]
        if u in keeps or decide_only(" ".join([r.get("container", ""), r.get("ident", ""), r.get("kit") or ""])):
            continue
        ident = wave_identity(r.get("kit"))
        how = ""
        if ident and "|".join(ident) in gfc and now - float(gfc["|".join(ident)]) < MIN_REPORT_AGE_S:
            continue                                     # grt_flat_pass / this pass just cancelled it through the wave: give the stop a pass to land
        if ident and "|".join(ident) not in gfc and not r.get("lane"):
            rc, line = wave_cancel(ident, f"{GRT_FLAT_CLASS if cls.startswith('DESIGN') else 'design:' + cls.lower()}: {ev}; die owner: plan fix, no unchanged retry")
            gfc["|".join(ident)] = now                   # a later pass that still sees the container running uses ot-run --cancel (leak path 2)
            how = f"kit_wave cancel-rows rc={rc}: {line}"
        else:
            write_cancel_marks([x.get("kit") for x in rs], "DESIGN-FAIL watchdog", f"CANCEL-DESIGN: {ev}", now)
            rc, line = cancel(u)
            how = f"ot-run --cancel {u} --reason design rc={rc}: {line}"
            done_k[k] = now
        done.append({"t": now, "unit": u, "host": r.get("host"), "type": r.get("type", ""), "plan": plan_of(r.get("kit")), "evidence": ev,
                     "freed_gb": round(sum(x.get("gb", 0) for x in rs), 1), "class": cls, "cancel_method": how, "owner": owner_of(rs),
                     "age_h": r.get("age_h"), "stage": r.get("stage")})
    for k in [k for k, t in done_k.items() if now - t > 3 * 86400]:
        del done_k[k]
    for k in [k for k, e in track.items() if now - float(e.get("last", now)) > UNSIGNABLE_FORGET_S]:
        del track[k]
    if done:
        path = os.path.join(COORD, "lanes/CANCEL-DESIGN-FAIL.tsv")
        new = not os.path.exists(path)
        with open(path, "a") as f:
            if new:
                f.write("t\tunit\thost\ttype\tplan\tstage\tage_h\tevidence\tfreed_gb\tclass\tcancel_method\towner\n")
            for d in done:
                f.write("\t".join(str(d[k]).replace("\t", " ").replace("\n", " ") for k in ("t", "unit", "host", "type", "plan", "stage", "age_h", "evidence", "freed_gb", "class", "cancel_method", "owner")) + "\n")
    if done and post:
        by = {}
        for d in done:
            by.setdefault(d["owner"], []).append(d)
        for owner, ds in sorted(by.items()):
            _post(poster, f"CANCELLED [{poster} -> {owner}] DESIGN-FAIL watchdog (LAUNCH-GUARD 11-23; STAGE-PLATEAU 11-25 DRT-PLATEAU / HOLD-STALL): {len(ds)} container unit(s) measured unable to sign (GRT failed, DRT plateau or flat pregrt_ff_hold TNS) "
                  + "; ".join(f"{d['host']} {d['unit']} {d['type']} {d['stage']} {d['age_h']} h [{d['class']}] ({d['evidence'][:(900 if d['class'] == DRT_PLATEAU else 150)]}; {d['freed_gb']} GB; {d['cancel_method'][-70:]})" for d in ds[:40])
                  + ". Evidence lanes/CANCEL-DESIGN-FAIL.tsv; kit dirs kept; no unchanged retry.")
    return done


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["scan", "hub", "tick", "smell-render", "smell-backfill"])
    ap.add_argument("args", nargs="*")
    ap.add_argument("--act", action="store_true")
    ap.add_argument("--no-post", action="store_true")
    ap.add_argument("--probe", type=float, default=4)
    a = ap.parse_args(argv)
    if not os.environ.get("XDG_RUNTIME_DIR"):
        os.environ["XDG_RUNTIME_DIR"] = f"/run/user/{os.getuid()}"
    if a.cmd == "smell-backfill":
        q = [l for l in read_lines(os.path.join(COORD, "lanes/VIS-QUEUE.tsv")) if l and not l.startswith("t\t")]
        n = smell_tsv_append(vis_as_smell_rows(q))
        print(f"smell-backfill: {n} rows from {len(q)} VIS-QUEUE rows")
        if n and os.path.exists(os.path.join(COORD, "bin/coord-commit.sh")):
            subprocess.run(["bash", os.path.join(COORD, "bin/coord-commit.sh"), "SMELL-WATCH: backfill lanes/SMELL.tsv from VIS-QUEUE", "lanes/SMELL.tsv"], timeout=900)
        return 0
    if a.cmd == "smell-render":
        w, k, st_, im, rid, sm = (a.args + [""] * 6)[:6]
        status, rev = smell_render(w, k, st_, im, rid, json.loads(sm or "[]"))
        print(f"{status}\t{rev}")
        return 0
    if a.cmd in ("scan", "tick"):
        rows, actions = scan(act=a.act or a.cmd == "tick", probe_s=a.probe)
        print(f"noprog scan: {len(rows)} containers, {sum(r['verdict'] in ('NO-PROGRESS', 'CANCEL-NOW') for r in rows)} flagged, {len(actions)} cancelled")
    if a.cmd == "hub" or (a.cmd == "tick" and os.path.exists(os.path.join(COORD, "bin/coord-commit.sh"))):
        reports, acts = hub(post=not a.no_post)
        print(f"noprog hub: {len(reports)} hosts, {len(acts)} new actions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
