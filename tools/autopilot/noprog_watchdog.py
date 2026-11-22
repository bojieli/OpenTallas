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
import argparse, glob, json, os, re, shlex, socket, subprocess, sys, time

WINDOW_S = 6 * 3600
MIN_IMPROVE = 0.02
HUB = os.environ.get("OT_HUB_NAME", "intel2")
HOSTS = ["intel1", "intel2", "epyc2", "epyc7", "epyc8", "epyc9", "epyc10"]
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


def judge(res, anchors, now, window=WINDOW_S, improve=MIN_IMPROVE, exact=False):
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
        if recent and min(recent) == 0:
            return "PROGRESS", f"{res['name']} reached 0", detail
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
UNSIGNABLE_GRACE_S = 1800             # FLOW-OPS-0900 (owner 11-21): NOTICE to the owning lane, cancel 30 min later unless the lane posted KEEP <unit>
UNSIGNABLE_FORGET_S = 6 * 3600        # a unit not seen for 6 h is forgotten; a short gap in the list keeps its first-listed time
PRIVATE_RE = re.compile(r"/private/")
HOLD_ONLY_RE = re.compile(r"(?i)(?:^|[/_\-.])hold(?:[_-]?only|[_-]?fix|[_-]?eco|[_-]?gate)?(?:$|[/_\-.0-9])")
# never auto-cancelled: posted to the named lane for a decision (COORD 11-21 FLOW-OPS-0900 brief); lanes/UNSIGNABLE-DECIDE.tsv (regex<TAB>lane) adds more
DECIDE_ONLY = ((r"ot_s81sl_leaf__t11(?![0-9])", "FABLE-FIX-S81-LEAF-R5"), (r"(?:^|[^A-Za-z0-9])slw_su_c(?![A-Za-z0-9])", "QC-PLAN-R10"))
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
    if PROOF_RE.search(ident) or PRIVATE_RE.search(ident):
        return "proof / private kit"
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


def is_hbm(text):
    return bool(HBM_RE.search(GENERATOR_RE.sub(" ", text)))


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
               "threads": int(th[1]) if th else 1, "gb": round(mem_gb(cg), 1), "prio": prio, "lane": lane, "_cg": cg, "_cpu0": cpu_a}
        ident = " ".join([name, kit or "", work or ""])
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
            exact = len(st["samples"]) > 0 and now - st["samples"][0][0] >= WINDOW_S
            v, why, detail = judge_activity(mt, started, now, "LEC") if kind == "lec" else judge(res, anchors, now, exact=exact)
            special = None
            if kind == "grt" and log:
                rdir = os.path.dirname(log).replace("/logs/", "/reports/")
                rounds_ = grt_rounds(rdir)
                row["grt_flat"] = grt_flat(rounds_)
                special = judge_grt_rounds(rounds_, read_text(log) if os.path.isfile(log) else "")
                if special:
                    # OWNER rule 11-14 deleted the GRT early stop: the round metric is a LABEL (class + trend + NEEDS-LANE), never a cancel
                    special = (GRT_LABEL, f"{special[0]}: {special[1]}", special[2], "GRT-CONGESTION")
            elif kind == "yosys" and log:
                special = synth_mem_stall(read_text(log) if os.path.isfile(log) else "", now - mt)
            if special:
                v, why, detail, row["klass"] = special
            if kind == "grt" and log:
                ev = grt_stuck(rounds_, (now - max(birth(log) or started, started)) / 3600)
                if ev:
                    spare = grt_stuck_spare(dict(row, ident=" ".join([name, kit or "", work or ""]), lane=lane), prot_paths, posts, now)
                    if spare:
                        row["grt_stuck_spared"] = spare[:160]
                    else:
                        v, why, row["klass"] = GRT_STUCK, ev, "GRT-CONGESTION"
                        detail = detail or ""
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
            if ev and row["verdict"] not in BAD_VERDICTS:
                row.update(verdict=UNSIGNABLE, why=ev, action="UNSIGNABLE (hub: NOTICE to the owning lane, cancel 30 min later unless KEEP)")
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
    if gdone:
        files.append("lanes/CANCEL-GRT-FLAT.tsv")
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
                                 f"NOPROG-WATCHDOG {stamp}: {len(flagged)} flagged, {len(new_actions)} cancelled", *files],
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
    r = run([exe, "--cancel", unit], capture_output=True, text=True, timeout=900)
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


def owner_of(rs):
    """the job's OT_LANE, else the lane of its tree / kit path (most units carry no OT_LANE), else COORD (wave jobs)"""
    return (next((r["lane"] for r in rs if r.get("lane")), "") or next((l for r in rs for l in [_private_lane(r.get("kit") or ""), lane_from_path(r.get("kit") or ""), lane_from_path(r.get("ident") or "")] if l), "")
            or "COORD")


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
                notices.setdefault(e["owner"], []).append(line)
                e["notice"] = now
            elif not e.get("reported"):
                notices.setdefault(e["owner"], []).append(line)
                e["reported"] = now
            continue
        if mode != "act" or now - e["notice"] < UNSIGNABLE_GRACE_S:
            continue
        first = rs[0]
        write_cancel_marks([r.get("kit") for r in rs], "UNSIGNABLE watchdog", f"CANCEL-UNSIGNABLE: {first.get('why', '')}", now)
        rc, out = cancel(u)
        rec = {"t": now, "unit": u, "host": h, "type": first["type"], "plan": plan_of(first.get("kit")), "evidence": f"{first['why']}; NOTICE to {e['owner']} {time.strftime('%H:%M', time.localtime(e['notice']))}, no KEEP in 30 min",
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
            _post(poster, f"CANCELLED [{poster} -> {owner}] UNSIGNABLE watchdog cancelled {len(ds)} job(s) after NOTICE + 30 min without KEEP: "
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
    if r.get("grt_flat"):
        return r["grt_flat"]
    if r.get("verdict") == GRT_LABEL:
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


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["scan", "hub", "tick"])
    ap.add_argument("--act", action="store_true")
    ap.add_argument("--no-post", action="store_true")
    ap.add_argument("--probe", type=float, default=4)
    a = ap.parse_args(argv)
    if not os.environ.get("XDG_RUNTIME_DIR"):
        os.environ["XDG_RUNTIME_DIR"] = f"/run/user/{os.getuid()}"
    if a.cmd in ("scan", "tick"):
        rows, actions = scan(act=a.act or a.cmd == "tick", probe_s=a.probe)
        print(f"noprog scan: {len(rows)} containers, {sum(r['verdict'] in ('NO-PROGRESS', 'CANCEL-NOW') for r in rows)} flagged, {len(actions)} cancelled")
    if a.cmd == "hub" or (a.cmd == "tick" and os.path.exists(os.path.join(COORD, "bin/coord-commit.sh"))):
        reports, acts = hub(post=not a.no_post)
        print(f"noprog hub: {len(reports)} hosts, {len(acts)} new actions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
