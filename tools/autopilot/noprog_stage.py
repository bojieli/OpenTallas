#!/usr/bin/env python3
"""noprog_stage.py -- per-stage progress advisor for every running flow job (NOPROG-FIX-1115, COORD r178, FABLE-FLOW-1600 class 4).

noprog_watchdog.py judges only what it does not exclude (66 of 109 rows on 11-15: plan-priority text matches, HBM, YOUNG on a series
restart) and it cancels.  This tool is ADVISORY ONLY: it never cancels, kills or limits anything.  It looks at EVERY container that runs
a flow stage (no exclusion list), reads that stage's own log, and classifies it:

  PROGRESSING  the stage's metric improved >= 2 % in the last 6 h (or reached 0), or the stage is still young, or its log is alive
  SLOW         alive but flat for >= 2 h (cpu busy / log still growing / metric within 2 %), not yet 6 h of evidence
  NO-PROGRESS  >= 6 h of evidence and the metric did not improve by 2 % from its best (best taken across series restarts), or no new
               meaningful log line / LEC file for 6 h, or the log is silent >= 1 h and the cpu is idle (hung)

Evidence age never exceeds the job's own age and the stage's log birth (a restarted series cannot make a 13 h job "young").
Per-stage metric (all read from the stage log):
  synth     1_*          yosys pass headers (events)
  floorplan 2_*          repair_timing table (Viol/TNS), else log events
  place_gp  3_1 3_3      GPL overflow rows; the timing-driven repair table (Remaining) while it runs
  place_rs  3_4          repair_design table (Remaining)
  place_dp  3_5          DPL independent-set-matching objective per pass
  cts       4_*          repair_timing table when active, else log events (CTS tap/clock lines)
  grt       5_1          repair tables (Remaining/Viol/TNS); GRT-0096 congestion total; the GRT-0102 extra-iteration loop counter (k/N)
                         is an event (epyc9 col_h9_r0_p5 jobs at iteration 19/30 were wrongly NO-PROGRESS when it was noise)
  route     5_2 drt.log  DRT-0199 completed totals; `Completing N%` counts within the active iteration are a separate metric
  sta       6_* signoff  log events (STA/report steps write a line per command)
  lec       lec          newest write of lec/* and *lec*.log (LEC has no metric)
  other     prep, lint.. log events

Commands (same file on every host, with noprog_watchdog.py beside it):
  scan   one host: -> JSON rows on stdout (state in ~/.local/state/noprog/stage_state.json)
  hub    on the hub: push both files to every host, scan each, write lanes/NOPROG.tsv (refreshed), post an hourly summary line
  tick   hub, as the systemd user timer runs it (every 15 min)
"""
import argparse, concurrent.futures as cf, glob, importlib.util, json, os, re, socket, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))


def _load_watchdog():
    for d in (HERE, os.path.expanduser("~/.local/lib/noprog")):
        p = os.path.join(d, "noprog_watchdog.py")
        if os.path.isfile(p):
            spec = importlib.util.spec_from_file_location("noprog_watchdog", p)
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            return m
    raise SystemExit("noprog_stage: noprog_watchdog.py not found beside this file or in ~/.local/lib/noprog")


W = _load_watchdog()

WINDOW_S = W.WINDOW_S            # 6 h: no 2 % improvement from best -> NO-PROGRESS
SLOW_S = 2 * 3600                # flat this long -> SLOW
HUNG_S = 3600                    # silent this long with an idle cpu -> NO-PROGRESS (hung)
MIN_IMPROVE = W.MIN_IMPROVE
HUB = W.HUB
HOSTS = W.HOSTS
STATE_DIR = os.path.expanduser(os.environ.get("NOPROG_DIR", "~/.local/state/noprog"))
COORD = os.path.expanduser(os.environ.get("OT_COORD_DIR", "~/coord"))
POST_LANE = os.environ.get("NOPROG_POST_LANE", "NOPROG-FIX-1115")
LIB = "~/.local/lib/noprog"
CLASSES = ["NO-PROGRESS", "SLOW", "PROGRESSING"]

# ---------------------------------------------------------------- stage kinds (pure)
KIND_BY_NAME = [
    (re.compile(r"^1_|yosys|synth"), "synth"),
    (re.compile(r"^2_"), "floorplan"),
    (re.compile(r"^3_[13]_|place_gp"), "place_gp"),
    (re.compile(r"^3_4_|resized"), "place_rs"),
    (re.compile(r"^3_5_|place_dp"), "place_dp"),
    (re.compile(r"^3_"), "place_other"),
    (re.compile(r"^4_|cts"), "cts"),
    (re.compile(r"^5_1_|grt|fabric\.log"), "grt"),
    (re.compile(r"^5_2_|^drt|route"), "route"),
    (re.compile(r"^6_|signoff|(^|[_.])sta([_.]|$)"), "sta"),
    (re.compile(r"lec"), "lec"),
]
DPL_PASS = re.compile(r"DPL-0301\]\s+Pass\s+(\d+) of matching; objective is ([0-9.]+e[+-]?\d+|[0-9.]+)")
DRT_PCT = re.compile(r"Completing (\d+)% with (\d+) violations")
DRT_ITER_START = re.compile(r"DRT-0195\]\s+Start (\d+)\w* optimization iteration")
YOSYS_PASS = re.compile(r"^\d+(\.\d+)*\. Executing ")
NOISE = re.compile(r"GRT-0273|RSZ-0104|DRT-0036|DRT-0028|DRT-0035|^\s*$")      # GRT-0102 "Start extra iteration k/N" is the loop counter: news


def stage_kind(logname, cmd=""):
    n = os.path.basename(logname or "")
    n = n.replace(".tmp.log", "").replace(".log", "") if n.startswith(("1_", "2_", "3_", "4_", "5_", "6_")) else n
    for rx, kind in KIND_BY_NAME:
        if rx.search(n):
            return kind
    if "drt.tcl" in cmd:
        return "route"
    return "other"


def meaningful(lines):
    return [i for i, ln in enumerate(lines) if not NOISE.search(ln)]


def parse_stage(kind, text):
    """-> dict(name, series=[(line_idx, v)] lower is better (the quality metric, or []), events=[line_idx] forward steps,
    n=lines, last=text of the last meaningful line, table=bool the quality series is a live repair table)"""
    lines = text.splitlines()
    mean = meaningful(lines)
    res = {"name": None, "series": [], "events": mean, "n": len(lines), "table": False,
           "last": lines[mean[-1]].strip()[:100] if mean else ""}
    if kind == "lec":
        return res
    tbls = W.parse_tables(lines)
    act = tbls[-1] if tbls and not tbls[-1]["final"] else None
    if act is not None:
        ts = W.table_series(act, kind)
        if ts:
            res.update(name="repair_" + ts[0], series=ts[1], table=True, events=[i for i, _ in ts[1]] + mean[-1:])
            return res
    if kind in ("place_gp", "place_other"):
        ser = []
        for i, ln in enumerate(lines):
            m = W.GPL_ROW.match(ln) or W.GPL_ROW_OLD.search(ln)
            if m:
                ser.append((i, float(m.group(2))))
        if ser:
            res.update(name="gpl_overflow", series=ser)
    elif kind == "place_dp":
        ser = [(i, float(m.group(2))) for i, ln in enumerate(lines) for m in [DPL_PASS.search(ln)] if m]
        res.update(name="dpl_objective", series=ser)
    elif kind == "route":
        ser = [(i, float(m.group(1))) for i, ln in enumerate(lines) for m in [W.DRT_ITER.search(ln)] if m]
        pct = [i for i, ln in enumerate(lines) if DRT_PCT.search(ln) or DRT_ITER_START.search(ln)]
        # A long optimization iteration can improve for hours before DRT-0199.
        # Compare its partial counts only with one another, never with another
        # iteration or a completed total (partial route states are different).
        partial, previous_pct = [], -1
        for i, ln in enumerate(lines):
            if DRT_ITER_START.search(ln) or W.DRT_ITER.search(ln):
                partial, previous_pct = [], -1
            m = DRT_PCT.search(ln)
            if m:
                progress, violations = int(m.group(1)), float(m.group(2))
                if progress <= previous_pct:
                    partial = []             # restart/rewind without a header
                partial.append((i, violations))
                previous_pct = progress
        res.update(name="drt_violations", series=ser, events=pct or mean, partial_series=partial)
    elif kind == "grt":
        tot = [(i, float(m.group(3))) for i, ln in enumerate(lines) for m in [W.GRT_TOTAL.match(ln)] if m]
        if tot and (not mean or tot[-1][0] >= mean[-1] - 40):
            res.update(name="grt_overflow", series=tot)
    elif kind == "synth":
        ev = [i for i, ln in enumerate(lines) if YOSYS_PASS.match(ln)]
        res["events"] = ev or mean
    return res


# ---------------------------------------------------------------- classification (pure)
def row_times(res, anchors):
    return [(W.interp_time(i, anchors), v) for i, v in res["series"]]


def quality_verdict(res, anchors, now, window, span):
    """-> (improvement_in_window | None, stagnant_s, detail) for a series.  best is taken across series restarts of the metric; a restart
    that improves inside the window counts too."""
    pts = row_times(res, anchors)
    best_all = min(v for _, v in pts)
    last = pts[-1][1]
    before = [v for t, v in pts if t <= now - window]
    recent = [(t, v) for t, v in pts if t > now - window]
    bb = min(before) if before else pts[0][1]
    rb = min(v for _, v in recent) if recent else None
    imp = 0.0
    if rb is not None:
        if rb == 0 and bb > 0:
            imp = 1.0
        else:
            if bb > 0:
                imp = max(imp, 1 - rb / bb)
            first = recent[0][1]
            if first > 0:
                imp = max(imp, 1 - rb / first)       # a restart inside the window that improves
    # stagnation: time since the best value (within MIN_IMPROVE) was first reached; bounded by the evidence span
    tol = best_all * (1 + MIN_IMPROVE) if best_all > 0 else 0
    t_best = next(t for t, v in pts if v <= tol)
    stagnant = min(now - t_best, span)
    t_last2 = [v for t, v in pts if t > now - SLOW_S]
    imp2 = (1 - min(t_last2) / bb) if t_last2 and bb > 0 else 0.0
    detail = f"{res['name']} best {best_all:g} last {last:g} rows {len(pts)} window-gain {100 * imp:.1f}%"
    return imp, stagnant, imp2, detail


def classify(kind, res, anchors, now, job_age_s, log_mtime, cores_now=None, exact=True, window=WINDOW_S, lec_mt=0.0):
    """-> (class, evidence).  `anchors` = [(time, line_count)] piecewise line clock; `exact` False stretches the window x1.25 for
    metric judgments made only on interpolated line times."""
    start = min(a[0] for a in anchors)
    span = min(now - start, job_age_s)                     # evidence never exceeds the job's own age
    win = window if exact else window * 1.25
    idle = cores_now is not None and cores_now < 0.05
    if kind == "lec":
        last = max(log_mtime, lec_mt)
        silent = now - last
        ev = f"LEC last file/log write {silent / 3600:.1f} h ago"
        if silent >= window and span >= window:
            return "NO-PROGRESS", ev
        if silent >= HUNG_S and idle:
            return "NO-PROGRESS", ev + ", cpu idle (hung)"
        return ("SLOW" if silent >= SLOW_S else "PROGRESSING"), ev
    ev_idx = res["events"][-1] if res["events"] else -1
    last_ev_age = now - (W.interp_time(ev_idx, anchors) if ev_idx >= 0 else start)
    # the newest meaningful line cannot be older than the log's own last write; if the log is silent the age is the mtime age
    silent = max(0.0, now - log_mtime)
    last_ev_age = max(last_ev_age, silent) if ev_idx >= res["n"] - 1 else last_ev_age
    base = f"last event {last_ev_age / 3600:.1f} h ago, log write {silent / 3600:.1f} h ago ({res['n']} lines)"
    if res["n"] == 0:
        return ("NO-PROGRESS", "empty log, cpu idle (hung)") if idle and span >= HUNG_S else ("PROGRESSING", "no log output yet")
    if silent >= HUNG_S and idle:
        return "NO-PROGRESS", f"{base}, cpu idle (hung)"
    partial = res.get("partial_series", []) if kind == "route" else []
    if len(partial) >= 2:
        part = dict(res, name="drt_active_iteration_violations", series=partial)
        imp, stagnant, imp2, detail = quality_verdict(part, anchors, now, win, span)
        if imp >= MIN_IMPROVE:
            # A partial count is a progress witness, not sign-off or a replacement
            # for completed totals. A stale witness cannot keep a flat job alive.
            return ("SLOW" if imp2 <= 0 and stagnant >= SLOW_S else "PROGRESSING"), f"{detail}; {base}"
    if res["series"] and len(res["series"]) >= 2:
        imp, stagnant, imp2, detail = quality_verdict(res, anchors, now, win, span)
        ev = f"{detail}; stagnant {stagnant / 3600:.1f} h; {base}"
        if imp >= 1.0 or imp >= MIN_IMPROVE:
            return ("SLOW" if (imp2 <= 0 and stagnant >= SLOW_S) else "PROGRESSING"), ev
        if span >= win and stagnant >= win:
            return "NO-PROGRESS", ev
        return ("SLOW" if stagnant >= SLOW_S or silent >= SLOW_S else "PROGRESSING"), ev
    # no usable series (milestone / log-event stages, or < 2 rows): the newest meaningful line decides
    if last_ev_age >= win and span >= win:
        return "NO-PROGRESS", f"no new meaningful log line for {last_ev_age / 3600:.1f} h; last: {res['last']}"
    if last_ev_age >= SLOW_S:
        return "SLOW", f"{base}; last: {res['last']}"
    return "PROGRESSING", f"{base}; last: {res['last']}"


def classify_nolog(job_age_s, cores_now):
    """a container with no stage log at all (its work dir has none, no redirect target): the cpu and the job age decide"""
    if cores_now is not None and cores_now < 0.05 and job_age_s >= HUNG_S:
        return "NO-PROGRESS", f"no stage log, cpu idle {cores_now} cores, job {job_age_s / 3600:.1f} h (hung)"
    if job_age_s >= WINDOW_S:
        return "SLOW", f"no stage log found after {job_age_s / 3600:.1f} h, cpu {cores_now} cores: no progress evidence"
    return "PROGRESSING", f"no stage log yet, job {job_age_s / 3600:.1f} h, cpu {cores_now} cores"


# ---------------------------------------------------------------- host scan
def redirect_logs(cmd, mounts):
    """host paths of `> /dest/x.log` redirections in the container command (dhr1 jobs write drt.log / prep.log that way)"""
    out = []
    for m in re.finditer(r">\s*(/[\w./-]+\.log)", cmd):
        for mt in mounts:
            d = mt["Destination"].rstrip("/") + "/"
            if m.group(1).startswith(d):
                out.append(mt["Source"].rstrip("/") + "/" + m.group(1)[len(d):])
    return out


def load_state():
    try:
        return json.load(open(os.path.join(STATE_DIR, "stage_state.json")))
    except (OSError, ValueError):
        return {"jobs": {}}


def scan(now=None, probe_s=4):
    now = now or time.time()
    host = os.environ.get("NOPROG_HOST") or socket.gethostname()
    state = load_state()
    ids = W.sh("docker", "ps", "-q").split()
    insp = json.loads(W.sh("docker", "inspect", *ids) or "[]") if ids else []
    sc = W.scopes()
    pid2unit = {p: u for u, ps in sc.items() for p in ps}
    cg0 = {}
    for c in insp:
        cg = W.cgroup_dir(c["State"]["Pid"])
        cg0[c["Id"]] = (cg, W.cpu_usec(cg))
    t_probe = time.time()
    rows = []
    for c in insp:
        name = c["Name"].lstrip("/")
        started = time.mktime(time.strptime(c["State"]["StartedAt"][:19], "%Y-%m-%dT%H:%M:%S")) - time.timezone
        mounts = [{"Source": m["Source"], "Destination": m["Destination"]} for m in c.get("Mounts", [])]
        cmd = " ".join(c["Config"].get("Cmd") or [])
        work = W.work_dir(mounts)
        unit = pid2unit.get(W.owner_pid(name))
        kit = work
        if unit:
            for p in sc[unit]:
                pcmd, cwd = W.proc_info(p)
                if "run_kit.sh" in pcmd and kit == work and cwd and not cwd.rstrip("/").endswith("/ot-jobs"):
                    kit = cwd
        log, mt = W.candidate_logs(work, mounts, name, started)
        for p in redirect_logs(cmd, mounts):
            try:
                if os.stat(p).st_mtime >= started - 120 and os.stat(p).st_mtime >= mt:
                    log, mt = p, os.stat(p).st_mtime
            except OSError:
                pass
        kind = stage_kind(log, cmd) if log else "other"
        lec_mt = W.lec_activity(work, started) if work and (name.endswith("-lec") or "lec.py" in cmd) else 0.0
        if lec_mt and (name.endswith("-lec") or (not (log or "").endswith(".tmp.log") and lec_mt >= mt)):
            kind = "lec"
        stage = "lec" if kind == "lec" else (os.path.basename(log).replace(".tmp.log", "").replace(".log", "") if log else "-")
        cg, cpu_a = cg0[c["Id"]]
        row = {"host": host, "container": name, "type": W.base_type(name), "kit": kit, "stage": stage, "kind": kind,
               "job_h": round((now - started) / 3600, 1), "gb": round(W.mem_gb(cg), 1), "_cg": cg, "_cpu0": cpu_a}
        if not log and not lec_mt:
            row.update(stage_h=0.0, _ctx=("nolog", now - started))
            rows.append(row)
            continue
        lbirth = max(W.birth(log) or started, started) if log else started
        st = state["jobs"].setdefault(f"{c['Id'][:12]}|{log}", {"samples": []})
        text = W.read_text(log) if log and os.path.isfile(log) else ""
        res = parse_stage(kind, text)
        anchors = [(lbirth, 0)]
        for s in st["samples"]:
            if s[0] > anchors[-1][0] and anchors[-1][1] <= s[1] <= res["n"]:
                anchors.append((s[0], s[1]))
        anchors.append((max(mt, anchors[-1][0] + 1), res["n"]))
        exact = bool(st["samples"]) and now - st["samples"][0][0] >= WINDOW_S
        row["_ctx"] = (kind, res, anchors, mt, started, exact, lec_mt)
        row.update(stage_h=round((now - lbirth) / 3600, 1), lines=res["n"])
        st["samples"].append([now, res["n"], cpu_a])
        st["samples"] = st["samples"][-80:]
        st["seen"] = now
        rows.append(row)
    time.sleep(max(0.0, probe_s - (time.time() - t_probe)))
    t1 = time.time()
    for r in rows:
        cg, c0 = r.pop("_cg", None), r.pop("_cpu0", None)
        cores = None
        if cg and c0 is not None:
            c1 = W.cpu_usec(cg)
            if c1 is not None:
                cores = round((c1 - c0) / 1e6 / max(t1 - t_probe, 1e-3), 2)
        r["cores_now"] = cores
        ctx = r.pop("_ctx", None)
        if ctx and ctx[0] == "nolog":
            r["cls"], r["evidence"] = classify_nolog(ctx[1], cores)
        elif ctx:
            kind, res, anchors, mt, started, exact, lec_mt = ctx
            r["cls"], r["evidence"] = classify(kind, res, anchors, now, now - started, mt, cores, exact, lec_mt=lec_mt)
    for sk in list(state["jobs"]):
        if now - state["jobs"][sk].get("seen", 0) > 3 * 86400:
            del state["jobs"][sk]
    W.save_json(os.path.join(STATE_DIR, "stage_state.json"), state)
    return rows


# ---------------------------------------------------------------- hub
TSV_COLS = ["cls", "host", "kit", "type", "stage", "stage_h", "job_h", "cores_now", "gb", "container", "evidence"]


def tsv(rows, stamp, missing):
    rows = sorted(rows, key=lambda r: (CLASSES.index(r["cls"]), -float(r.get("stage_h") or 0), r["host"], r["container"]))
    n = {c: sum(1 for r in rows if r["cls"] == c) for c in CLASSES}
    out = [f"# NOPROG (NOPROG-FIX-1115, advisory only, generated {stamp}): {len(rows)} running jobs {n}; hosts without report: {missing or 'none'}",
           "\t".join("class" if c == "cls" else c for c in TSV_COLS)]
    for r in rows:
        out.append("\t".join(str(r.get(c, "")).replace("\t", " ").replace("\n", " ") for c in TSV_COLS))
    return "\n".join(out) + "\n"


def summary(rows, stamp, missing):
    n = {c: sum(1 for r in rows if r["cls"] == c) for c in CLASSES}
    bad = sorted((r for r in rows if r["cls"] == "NO-PROGRESS"), key=lambda r: -float(r.get("stage_h") or 0))
    head = (f"STATE [{POST_LANE} -> COORD] NOPROG hourly {stamp}: {len(rows)} running jobs, PROGRESSING {n['PROGRESSING']}, "
            f"SLOW {n['SLOW']}, NO-PROGRESS {n['NO-PROGRESS']} (advisory, no cancel); table lanes/NOPROG.tsv")
    if missing:
        head += f"; hosts without report {missing}"
    lines = [head]
    for r in bad[:40]:
        lines.append(f"NO-PROGRESS {r['host']} {os.path.basename((r.get('kit') or '').rstrip('/'))} {r['stage']} stage {r.get('stage_h')} h "
                     f"job {r['job_h']} h: {r['evidence'][:150]}")
    if len(bad) > 40:
        lines.append(f"... and {len(bad) - 40} more in lanes/NOPROG.tsv")
    return "\n".join(lines)


def run_host(host, cmd, inp=None, timeout=120):
    if host == HUB or host == socket.gethostname():
        return subprocess.run(["bash", "-c", cmd], input=inp, capture_output=True, text=True, timeout=timeout)
    return subprocess.run(["ssh", "-o", "ControlPath=none", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", host, cmd],
                          input=inp, capture_output=True, text=True, timeout=timeout)


RT_CURRENT = os.environ.get("NOPROG_SRC", "/srv/opentallas-scratch2/claude/rt/current/tools/autopilot")


def push_src_dir():
    """FLOW-FIX-0100 (FABLE-FLOW-2350 f): the hub tick runs from ~/.local/lib/noprog, so HERE is that lib copy and it pushed ITSELF to every host forever
    (the 22:04 STAGE-CAP / log fix never reached any of the 7 hosts).  Push rt/current's pair (main) when both files are there, else HERE."""
    if all(os.path.isfile(os.path.join(RT_CURRENT, fn)) for fn in ("noprog_watchdog.py", "noprog_stage.py")):
        return RT_CURRENT
    return HERE


def push_and_scan(host):
    d = LIB
    try:
        for fn in ("noprog_watchdog.py", "noprog_stage.py"):
            src = open(os.path.join(push_src_dir(), fn)).read()
            run_host(host, f"mkdir -p {d} && cat > {d}/{fn}.new && mv {d}/{fn}.new {d}/{fn}", inp=src, timeout=60)
        p = run_host(host, f"OT_HUB_NAME={HUB} python3 -I {d}/noprog_stage.py scan", timeout=180)
        rows = json.loads(p.stdout)
        for r in rows:
            r["host"] = host
        return host, rows
    except (subprocess.SubprocessError, OSError, ValueError):
        return host, None


def coord_commit(msg, files):
    return subprocess.run(["bash", os.path.join(COORD, "bin/coord-commit.sh"), msg, *files], capture_output=True, text=True, timeout=600)


def hub(now=None, post=True, force_post=False):
    now = now or time.time()
    with cf.ThreadPoolExecutor(max_workers=len(HOSTS)) as ex:
        results = list(ex.map(push_and_scan, HOSTS))
    rows = [r for _, rs in results if rs for r in rs]
    missing = [h for h, rs in results if rs is None]
    stamp = time.strftime("%Y-%m-%d %H:%M PST", time.localtime(now))
    path = os.path.join(COORD, "lanes/NOPROG.tsv")
    old = ""
    try:
        old = open(path).read()
    except OSError:
        pass
    # the pre-NOPROG-FIX file was the watchdog's append-only action log: keep it as lanes/NOPROG-ACTIONS.tsv
    files = ["lanes/NOPROG.tsv"]
    ap = os.path.join(COORD, "lanes/NOPROG-ACTIONS.tsv")
    if old.startswith("time\thost\ttype") and not os.path.exists(ap):
        open(ap, "w").write(old)
        files.append("lanes/NOPROG-ACTIONS.tsv")
    new = tsv(rows, stamp, missing)
    seen_path = os.path.join(STATE_DIR, "stage_hub.json")
    try:
        seen = json.load(open(seen_path))
    except (OSError, ValueError):
        seen = {}
    sig = json.dumps(sorted(f"{r['host']}|{r['container']}|{r['cls']}" for r in rows if r["cls"] != "PROGRESSING"))
    if sig != seen.get("sig") or now - seen.get("commit_t", 0) >= 3600 or len(files) > 1:
        # FABLE-FLOW-1900 (E): lanes/NOPROG.tsv is a tracked file; it is written only together with its commit (it used to be rewritten every tick and
        # committed hourly, so the hub checkout carried local edits between commits -> HUB-SYNC-FAILED).  A failed commit puts the old text back.
        open(path, "w").write(new)
        r = coord_commit("NOPROG-FIX-1115: NOPROG.tsv refresh", files)
        if getattr(r, "returncode", 0) not in (0, None):
            open(path, "w").write(old)
        else:
            seen.update(sig=sig, commit_t=now)
    if post and (force_post or now - seen.get("post_t", 0) >= 3500):
        subprocess.run(["bash", os.path.join(COORD, "bin/post.sh"), POST_LANE, summary(rows, stamp, missing)],
                       capture_output=True, text=True, timeout=600)
        seen["post_t"] = now
    W.save_json(seen_path, seen)
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["scan", "hub", "tick"])
    ap.add_argument("--no-post", action="store_true")
    ap.add_argument("--force-post", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "scan":
        json.dump(scan(), sys.stdout)
        return 0
    rows = hub(post=not a.no_post, force_post=a.force_post)
    print(f"noprog_stage hub: {len(rows)} rows", {c: sum(1 for r in rows if r['cls'] == c) for c in CLASSES})
    return 0


if __name__ == "__main__":
    sys.exit(main())
