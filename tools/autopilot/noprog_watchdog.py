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
NOISE = re.compile(r"GRT-0102|GRT-0273|RSZ-0104|^\s*$")
METRIC_COLS = ["Remaining", "Violations", "Viol", "TNS"]     # priority; TNS is taken as |TNS|


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
            g = [i for i, ln in enumerate(lines) if re.search(r"\bGRT-0\d+\]", ln) and not NOISE.search(ln)]
            if g:
                res["growth_idx"] = g[-1]
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
UNSIGNABLE_REPORT_ONLY_S = 3600       # the hub lists (and posts) for one hour before it cancels anything
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
    """-> WNS (ps) of the LAST setup repair_timing table of a log (header with WNS and StTNS; hold tables and repair_design are never read), else None.  A table still being written counts only
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
            last = vals[-1]
        elif len(vals) >= FLAT_ROWS and (max(vals[-FLAT_TAIL:]) - min(vals[-FLAT_TAIL:])) <= FLAT_FRAC * abs(vals[-1]):
            last = vals[-1]
        else:
            last = None            # still improving: a number that is not the stage result
    return last


def latest_setup(dirs, started):
    """COORD 11-20 (FABLE-FLOW-1200: cancels on the post-CTS number while GRT repair had moved one job to -0.494 ps): the NEWEST setup number THIS job wrote (mtime >= its container start - 60 s, so a resumed
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
                    cands.append((mt, float(v), p))
        for g in TT_LOG_GLOBS:
            for p in glob.glob(os.path.join(d, g)):
                mt = fresh(p)
                if mt is None:
                    continue
                ms = TT_WNS_RE.findall(read_text(p))
                if ms:
                    a, b = ms[-1]
                    cands.append((mt, float(b or a), p))
                else:
                    newest_unread = max(newest_unread, mt)
        for g in SETUP_LOG_GLOBS:
            for p in glob.glob(os.path.join(d, g)):
                mt = fresh(p)
                if mt is None:
                    continue
                v = setup_table_wns(read_text(p))
                if v is None:
                    newest_unread = max(newest_unread, mt)
                else:
                    cands.append((mt, v, p))
    if not cands:
        return None
    mt, v, p = max(cands)
    if newest_unread > mt:
        return None                      # a newer stage file carries no setup number yet: unmeasured, never the stale one
    return v, p


def unsignable_evidence(ident, prio, kind, age_h, setup):
    """-> evidence text when the rule applies, else None.  Pure."""
    if setup is None or age_h <= UNSIGNABLE_MIN_AGE_H or setup[0] >= UNSIGNABLE_SETUP_PS:
        return None
    if prio in ("plan", "proof") or kind == "lec" or ECO_RE.search(ident) or PROOF_RE.search(ident) or is_hbm(ident):
        return None
    return f"{os.path.basename(setup[1])} latest setup WNS {setup[0]:.2f} ps (< {UNSIGNABLE_SETUP_PS:.0f}, gate TT >= -42); job age {age_h} h > {UNSIGNABLE_MIN_AGE_H:g} h"


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


def proc_env_prio(pid):
    try:
        for kv in open(f"/proc/{pid}/environ", "rb").read().split(b"\0"):
            if kv.startswith(b"OT_HEAVY_PRIO="):
                return kv.split(b"=", 1)[1].decode()
    except OSError:
        pass
    return ""


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
    if work:
        cands += glob.glob(f"{work}/run/logs/*/*/*/*.log")        # *.tmp.log = the running OpenROAD stage; yosys writes its *.log directly
    if cname.endswith("-lec"):
        for root in {work} | {m["Source"] for m in mounts}:
            if root:
                cands += glob.glob(f"{root}/*lec*.log") + glob.glob(f"{root}/*/*lec*.log") + glob.glob(f"{root}/lec/*.log")
    else:
        if work:        # a kit step's own log (pregrt_ff_hold.log, hold_gate.log ...); run_*.log is the aggregate runner stdout: fallback only
            cands += [p for p in glob.glob(f"{work}/*.log") + glob.glob(f"{work}/run/*.log") if not os.path.basename(p).startswith("run_")]
        if not cands and work:
            cands += glob.glob(f"{work}/run_*.log")
        if not cands:
            for m in mounts:
                cands += glob.glob(f"{m['Source']}/*.log") + glob.glob(f"{m['Source']}/*/*.log")
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


BAD_VERDICTS = ("NO-PROGRESS", "CANCEL-NOW", "DESIGN-FAIL")      # GRT_LABEL is deliberately NOT here: it never cancels


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
        kit, prio, text = work, "", name
        if unit:
            for p in sc[unit]:
                cmd, cwd = proc_info(p)
                text += " " + cmd[:600] + " " + cwd
                if "run_kit.sh" in cmd and kit == work and cwd and not cwd.rstrip("/").endswith("/ot-jobs"):
                    kit = cwd
                prio = prio or proc_env_prio(p)
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
               "threads": int(th[1]) if th else 1, "gb": round(mem_gb(cg), 1), "prio": prio, "_cg": cg, "_cpu0": cpu_a}
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
                special = judge_grt_rounds(grt_rounds(rdir), read_text(log) if os.path.isfile(log) else "")
                if special:
                    # OWNER rule 11-14 deleted the GRT early stop: the round metric is a LABEL (class + trend + NEEDS-LANE), never a cancel
                    special = (GRT_LABEL, f"{special[0]}: {special[1]}", special[2], "GRT-CONGESTION")
            elif kind == "yosys" and log:
                special = synth_mem_stall(read_text(log) if os.path.isfile(log) else "", now - mt)
            if special:
                v, why, detail, row["klass"] = special
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
            ms = latest_setup([kit, work], started)
            ev = unsignable_evidence(ident, prio, kind, row["age_h"], ms)
            if ms:
                row["setup_ps"] = ms[0]
            if ev and row["verdict"] not in BAD_VERDICTS:
                row.update(verdict=UNSIGNABLE, why=ev, action="UNSIGNABLE (hub cancels after the report hour)")
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
ORDER = {UNSIGNABLE: 0, "GRT-LABEL": 1, "DESIGN-FAIL": 0, "NO-PROGRESS": 0, "CANCEL-NOW": 0, "NO-DATA": 2, "YOUNG": 2, "EXCLUDED": 3, "KEEP": 3, "PROGRESS": 4}


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


def hub(now=None, post=True):
    now = now or time.time()
    keep = read_lines(os.path.join(COORD, "lanes/NOPROG-KEEP.tsv"))
    for h in HOSTS:
        for fname, lines in (("keep.tsv", keep),):
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
    flagged = [r for r in rows if r["verdict"] in ("NO-PROGRESS", "CANCEL-NOW", "DESIGN-FAIL", GRT_LABEL, UNSIGNABLE)]
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
    for h in HOSTS:
        lines = [l for l in run_host(h, f"cat {STATE_DIR}/actions.jsonl 2>/dev/null", timeout=40).stdout.splitlines() if l.strip()]
        for l in lines[seen["offset"].get(h, 0):]:
            try:
                a = json.loads(l)
                a["host"] = h
                new_actions.append(a)
            except ValueError:
                pass
        seen["offset"][h] = len(lines)
    files = ["lanes/NOPROG-TABLE.md"]
    if new_actions:
        np_path = os.path.join(COORD, "lanes/NOPROG-ACTIONS.tsv")
        fresh = not os.path.exists(np_path)
        with open(np_path, "a") as f:
            if fresh:
                f.write("time\thost\ttype\tstage\tlast_metric\tkit_dir\tcontainers\twhy\tgb_freed\tcores_reserved\tcores_busy\n")
            for a in new_actions:
                f.write("\t".join(str(x) for x in [time.strftime("%F %T", time.localtime(a["t"])), a["host"], a["type"], a["stage"],
                                                   a["metric"].replace("\t", " "), a["kit"], ",".join(a["containers"]), a["why"],
                                                   a["gb"], a["cores"], a["cores_busy"]]) + "\n")
        files.append("lanes/NOPROG-ACTIONS.tsv")
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
    if qlines:
        with open(os.path.join(COORD, "lanes/COORD-REVIEW-QUEUE.md"), "a") as f:
            f.write("\n".join(qlines) + "\n")
        files.append("lanes/COORD-REVIEW-QUEUE.md")
    save_json(seen_path, seen)
    if post:
        subprocess.run(["bash", os.path.join(COORD, "bin/coord-commit.sh"), f"NOPROG-WATCHDOG {stamp}: {len(flagged)} flagged, {len(new_actions)} cancelled"] + files,
                       capture_output=True, text=True, timeout=600)
    return reports, new_actions


def plan_of(kit):
    m = re.search(r"/kit-wave/([^/]+)/([^/]+)/", kit or "")
    return f"{m.group(1)} {m.group(2)}" if m else "-"


def unsignable_mode(seen, now):
    """report | act.  NOPROG_UNSIGNABLE_MODE=report|act forces it; auto (default): report for UNSIGNABLE_REPORT_ONLY_S after the first pass AND only once the list was posted."""
    forced = os.environ.get("NOPROG_UNSIGNABLE_MODE", "auto")
    if forced in ("report", "act"):
        return forced
    first = seen.setdefault("unsig_first", now)
    return "act" if seen.get("unsig_posted") and now - first >= UNSIGNABLE_REPORT_ONLY_S else "report"


def ot_run_cancel(unit, run=subprocess.run):
    """the only cancel path: ot-run --cancel <exact unit>.  -> (rc, last output line)"""
    exe = os.environ.get("OT_RUN_BIN") or os.path.expanduser("~/.local/bin/ot-run")
    r = run([exe, "--cancel", unit], capture_output=True, text=True, timeout=900)
    lines = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()
    return r.returncode, (lines[-1][:200] if lines else "no output")


def unsignable_pass(rows, seen, now, post=True, cancel=ot_run_cancel):
    """HUB half of the rule.  rows = every host's rows.  Lists UNSIGNABLE jobs (first time: posts the list, starts the report hour), and in act mode cancels every unit whose containers are ALL
    UNSIGNABLE and that has been listed >= MIN_REPORT_AGE_S.  Appends the evidence rows to lanes/CANCEL-UNSIGNABLE-1120.tsv.  -> (mode, listed rows, cancelled [dict])"""
    cand = [r for r in rows if r["verdict"] == UNSIGNABLE]
    listed = seen.setdefault("unsig_listed", {})
    keys = {f"{r['host']}|{r['key']}" for r in cand}
    for k in keys:
        listed.setdefault(k, now)
    for k in list(listed):
        if k not in keys:
            del listed[k]
    mode = unsignable_mode(seen, now)
    stamp = time.strftime("%Y-%m-%d %H:%M PST", time.localtime(now))
    if cand and post and (not seen.get("unsig_posted") or set(keys) - set(seen.get("unsig_posted_keys", []))):
        txt = (f"UNSIGNABLE watchdog ({mode} mode; cancels only after the report hour {UNSIGNABLE_REPORT_ONLY_S // 60} min from the first list): {len(cand)} job(s) over {UNSIGNABLE_MIN_AGE_H:g} h with post-CTS setup < "
               f"{UNSIGNABLE_SETUP_PS:.0f} ps: " + "; ".join(f"{r['host']} {r['type']} {r['setup_ps']:.0f} ps {r['age_h']} h {r['gb']} GB" for r in cand[:60]))
        try:
            subprocess.run(["bash", os.path.join(COORD, "bin/post.sh"), os.environ.get("NOPROG_POST_LANE", "FLEET-WATCH-1015"), txt], capture_output=True, text=True, timeout=300)
            seen["unsig_posted"] = seen.get("unsig_posted") or now
            seen["unsig_posted_keys"] = sorted(set(seen.get("unsig_posted_keys", [])) | keys)
        except (subprocess.SubprocessError, OSError):
            pass
    done = []
    if mode == "act":
        units = {}
        for r in rows:
            if r.get("unit"):
                units.setdefault((r["host"], r["unit"]), []).append(r)
        for (h, u), rs in sorted(units.items()):
            if not all(r["verdict"] == UNSIGNABLE and now - listed.get(f"{r['host']}|{r['key']}", now) >= MIN_REPORT_AGE_S for r in rs):
                continue
            rc, line = cancel(u)
            first = rs[0]
            rec = {"t": now, "unit": u, "host": h, "type": first["type"], "plan": plan_of(first["kit"]), "evidence": first["why"], "freed_gb": round(sum(r["gb"] for r in rs), 1),
                   "class": "UNSIGNABLE-SETUP", "cancel_method": f"ot-run --cancel {u} rc={rc}: {line}"}
            done.append(rec)
            seen.setdefault("unsig_cancelled", []).append(f"{h}|{u}")
        if done:
            path = os.path.join(COORD, "lanes/CANCEL-UNSIGNABLE-1120.tsv")
            with open(path, "a") as f:
                for d in done:
                    f.write("\t".join(str(d[k]).replace("\t", " ").replace("\n", " ") for k in ("unit", "host", "type", "plan", "evidence", "freed_gb", "class", "cancel_method")) + "\n")
    return mode, cand, done


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
