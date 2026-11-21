#!/usr/bin/env python3
"""failfast_rules.py -- progress-based stop rules for a kit's route stages (lane FAILFAST-1, 2026-11-11).

Why: a successful type build takes ~10 h; the 24-49 h tail is a congested build looping (GRT "extra iterations to remove
congestion" 3-15 rounds, GRT-0273 "Disabled NDR"; DRT at pass 27; hold repair that hits the buffer cap and then routes anyway).
The 2-h hung-job watchdog never fires on them because the log keeps growing.  Each rule below stops on PROGRESS, not on
silence.  Pure functions here; `judge` (CLI) is what grt183_make.sh polls every OT_GRT_STALL_POLL seconds inside the kit.
Stdlib only, no repo imports: the file is copied into every kit as /work/failfast_rules.py (core_flow.stage_grt183) and
sent verbatim to a host by tools/autopilot/failfast_scan.py (read-only dry run on live jobs).

Rules (config key, default; env wins over `export KEY = value` in the kit's config.mk; OT_FAILFAST=0 turns all off):
  (a) [GRT overflow / no-progress rule DELETED 11-14, OWNER: delete the conservative limits; GRT is not stopped for overflow or elapsed wall time;
      grt183_make.sh's optional OT_GRT_POST_MAX_S threshold is advisory logging only.]
  (d) NOCONVERGE        OT_FF_NOCONV=1  OT_FF_NOCONV_RESTARTS=2  OT_FF_NOCONV_MIN_GAIN_PCT=20     (MEM-RECLAIM-2200, OWNER 11-20 flat-congestion case)
      GRT restarts its 30-iteration congestion loop (rounds); 28 jobs sat 3-9 rounds, 12-60 h, at flat overflow.  Stop when 2 consecutive
      restarts each lowered the round-best overflow (congestion-N.rpt totals) by less than 20 %.  Measured, not a time or level limit;
      an open round is never judged.  Class line OT_GRT_NOCONVERGE, wave class PLAN design:grt_flat_overflow (no retry).
  (b) DRT_NO_PROGRESS   OT_FF_DRT=1  OT_FF_DRT_ITER=20  OT_FF_DRT_MAX_VIOL=10000  OT_FF_DRT_MIN_DROP_PCT=5  OT_FF_DRT_WINDOW=3
      From completed iteration OT_FF_DRT_ITER: stop when the violation count is above OT_FF_DRT_MAX_VIOL and over the last
      OT_FF_DRT_WINDOW iterations it fell by less than OT_FF_DRT_MIN_DROP_PCT % per iteration (compound: v_last >
      v_before * (1 - pct/100) ** window).
  (c) HOLD_STRUCTURAL   OT_FF_HOLD=1  OT_FF_HOLD_CAPS=0 (COORD 11-11: cap clause OFF by default; N > 0 = stop at N cap hits)
      An OT_HOLD_STALL NEEDS_RTL line, or (only when OT_FF_HOLD_CAPS > 0) hold repair that reports the buffer cap (RSZ-0060)
      OT_FF_HOLD_CAPS times in this run's CTS + GRT logs: the run ends as hold-structural instead of continuing to route.  A kit with
      'export OT_HOLD_STRUCTURAL_ADVISORY = 1' is exempt (owner: advisory kits keep going).
Classes (the first token of the stop line, read by tools/autopilot/autopilot.py):
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
    "OT_FF_DRT": 1, "OT_FF_DRT_ITER": 20, "OT_FF_DRT_MAX_VIOL": 10000, "OT_FF_DRT_MIN_DROP_PCT": 5, "OT_FF_DRT_WINDOW": 3,
    # FLOW-FIX-2045 (LONG-RUN-0300: KV kv3_io_cor 38 h in detail_route, iteration 51, violations bobbing around 250, no cap): (b2) DRT_STALL, below the 10000-violation floor of (b)
    "OT_FF_DRT_STALL": 1, "OT_FF_DRT_STALL_ITER": 40, "OT_FF_DRT_STALL_WINDOW": 12, "OT_FF_DRT_STALL_MIN_DROP_PCT": 1,
    "OT_FF_HOLD": 1, "OT_FF_HOLD_CAPS": 0,
    # MEM-RECLAIM-2200 (OWNER 11-20, flat-congestion case of the unsignable-job rule): (d) NOCONVERGE, see below
    "OT_FF_NOCONV": 1, "OT_FF_NOCONV_RESTARTS": 2, "OT_FF_NOCONV_MIN_GAIN_PCT": 20,
    # FLOW-FIX-0100 (FABLE-FLOW-2350 f): per-round wall budget (seconds, 0 = off; with 10 iterations a round is ~3 h on S81 leaf / KV hgi at 17-19 min each)
    # and the repair_timing no-progress stop (a pass = OT_FF_RT_ROWS table rows; OT_FF_RT_PASSES consecutive passes with < OT_FF_RT_MIN_GAIN_PCT WNS and TNS gain)
    "OT_GRT_ROUND_WALL_S": 14400,
    "OT_FF_RT": 1, "OT_FF_RT_ROWS": 100, "OT_FF_RT_PASSES": 2, "OT_FF_RT_MIN_GAIN_PCT": 5,
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


# ------------------------------------------------------------------------------------------------ (b) DRT
def drt_stall(series, c):
    """(b2) FLOW-FIX-2045: from completed iteration OT_FF_DRT_STALL_ITER (40), stop when the best violation count of the last OT_FF_DRT_STALL_WINDOW (12) iterations is not lower than the best before
    them by OT_FF_DRT_STALL_MIN_DROP_PCT (1 %): the route is bobbing, not converging, whatever the count.  A count of 0 ends the stage by itself.  -> None or the stop record"""
    if not c["OT_FF_DRT"] or not c.get("OT_FF_DRT_STALL"):
        return None
    w, n = c["OT_FF_DRT_STALL_WINDOW"], len(series)
    if n < max(c["OT_FF_DRT_STALL_ITER"], w + 1):
        return None
    best_before = min(v for _l, v in series[:-w])
    best_win = min(v for _l, v in series[-w:])
    pct = c["OT_FF_DRT_STALL_MIN_DROP_PCT"]
    if best_before <= 0 or best_win <= best_before * (1 - pct / 100.0):
        return None
    return {"rule": "DRT_STALL", "iteration": n, "violations": series[-1][1], "best": best_before, "window": w, "min_drop_pct": pct,
            "tail": [v for _l, v in series[-w:]]}


def drt_decide(series, c):
    """series [(label, violations)] of completed iterations -> None or the stop record"""
    if not c["OT_FF_DRT"]:
        return None
    d = _drt_floor(series, c)
    return d or drt_stall(series, c)


def _drt_floor(series, c):
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
    if d.get("rule") == "DRT_STALL":
        return ("OT_DRT_NO_PROGRESS stage=route class=DRT_STALL: iteration %d has %d violations and none of the last %d iterations beat the earlier best %d by %g%%: %s; stopping the stage (FLOW-FIX-2045)%s"
                % (d["iteration"], d["violations"], d["window"], d["best"], d["min_drop_pct"], " ".join(str(v) for v in d["tail"]),
                   time.strftime(" %Y-%m-%d %H:%M:%S", time.gmtime()) if stamp else ""))
    return ("OT_DRT_NO_PROGRESS stage=route class=DRT_NO_PROGRESS: iteration %d has %d violations > %d and the last %d iterations fell "
            "%.1f%% in all (< %g%% per iteration): %s; stopping the stage (FAILFAST-1)%s"
            % (d["iteration"], d["violations"], d["max"], d["window"], d["fall_pct"], d["min_drop_pct"],
               " -> ".join(str(v) for v in d["tail"]), time.strftime(" %Y-%m-%d %H:%M:%S", time.gmtime()) if stamp else ""))


# ------------------------------------------------------------------------------------------------ (d) GRT restarts without gain
def congestion_rounds(hist):
    """[[idx, mtime, total], ...] (the congestion-<idx>.rpt snapshots this run has written, any order) -> [best total of each round, oldest first].
    A new round starts when the report index does not increase in time order (OpenROAD restarts at extra iteration 1/N; the report files are
    overwritten by index, so only the history kept by judge() shows the earlier rounds)."""
    out, prev = [], None
    for idx, _mt, tot in sorted(hist, key=lambda h: (h[1], h[0])):
        if prev is None or idx <= prev:
            out.append(tot)
        else:
            out[-1] = min(out[-1], tot)
        prev = idx
    return out


def noconverge_decide(hist, c):
    """(d) MEM-RECLAIM-2200 (OWNER 11-20: cancel a job measured unable to route; flat congestion across restarts is measured, not a time limit).
    The restart loop of GRT ('extra iteration' rounds) stops after OT_FF_NOCONV_RESTARTS (2) consecutive restarts that each lowered the best
    overflow of the round by less than OT_FF_NOCONV_MIN_GAIN_PCT (20 %) against the round before.  Needs RESTARTS + 1 completed rounds (the
    open last round is not judged), so a round that is still falling is never cut.  -> None or the stop record"""
    if not c["OT_FF_NOCONV"]:
        return None
    k, pct = c["OT_FF_NOCONV_RESTARTS"], c["OT_FF_NOCONV_MIN_GAIN_PCT"]
    rounds = congestion_rounds(hist)[:-1]            # completed rounds only
    if len(rounds) < k + 1 or rounds[-1] <= 0:
        return None
    tail = rounds[-(k + 1):]
    if all(tail[i] > tail[i - 1] * (1 - pct / 100.0) for i in range(1, len(tail))):
        return {"rule": "NOCONVERGE", "restarts": k, "min_gain_pct": pct, "rounds": len(rounds), "tail": tail}
    return None


def _round_spans(hist):
    """congestion snapshots -> [[best total, first mtime, last mtime], ...] per round, oldest first (same round split as congestion_rounds)"""
    out, prev = [], None
    for idx, mt, tot in sorted(hist, key=lambda h: (h[1], h[0])):
        if prev is None or idx <= prev:
            out.append([tot, mt, mt])
        else:
            out[-1][0] = min(out[-1][0], tot)
            out[-1][2] = mt
        prev = idx
    return out


def round_wall_decide(hist, now, c):
    """FLOW-FIX-0100 (FABLE-FLOW-2350 f): per-round wall budget as NOCONVERGE evidence.  The open round started when the previous round's last
    snapshot was written; when it has run OT_GRT_ROUND_WALL_S (0 = off) and its best overflow so far is not OT_FF_NOCONV_MIN_GAIN_PCT below the
    previous completed round, the round is flat evidence and the stage stops.  A round that is falling fast is never cut.  -> None or the stop record"""
    wall = c.get("OT_GRT_ROUND_WALL_S", 0)
    if not c["OT_FF_NOCONV"] or wall <= 0:
        return None
    sp = _round_spans(hist)
    if len(sp) < 2 or sp[-2][0] <= 0:
        return None
    prev, cur = sp[-2], sp[-1]
    age = now - prev[2]
    pct = c["OT_FF_NOCONV_MIN_GAIN_PCT"]
    if age >= wall and cur[0] > prev[0] * (1 - pct / 100.0):
        return {"rule": "NOCONVERGE", "kind": "round_wall", "wall_s": wall, "age_s": int(age), "min_gain_pct": pct, "tail": [prev[0], cur[0]]}
    return None


RT_HEAD_RE = re.compile(r"^\s*Iter\s*\|\s*Removed\s*\|")
RT_ROW_RE = re.compile(r"^\s*(\d+)\*?\s*\|(?:[^|]*\|){6}\s*(-?[\d.]+)\s*\|\s*(-?[\d.]+)\s*\|\s*(-?[\d.]+)\s*\|\s*(\d+)\s*\|")


def rt_rows(lines):
    """repair_timing setup table rows of the LAST table in a log -> [(wns, tns, viol)]  (columns Iter|Removed|Resized|Inserted|Cloned|Pin|Area|WNS|StTNS|EnTNS|Viol|Worst)"""
    rows = []
    for ln in lines:
        if RT_HEAD_RE.match(ln):
            rows = []
            continue
        m = RT_ROW_RE.match(ln)
        if m:
            rows.append((float(m[2]), float(m[3]), int(m[5])))
    return rows


def _gain_pct(old, new):
    """improvement of a slack-like value (higher = better) in percent of |old|; 0 when old is already >= 0"""
    if old >= 0:
        return 0.0
    return 100.0 * (new - old) / abs(old)


def rt_decide(rows, c):
    """FLOW-FIX-0100 (FABLE-FLOW-2350 f): repair_timing no-progress stop.  Rows are cut into passes of OT_FF_RT_ROWS rows; a pass gains when its best WNS or
    best TNS is >= OT_FF_RT_MIN_GAIN_PCT better than the best before it.  OT_FF_RT_PASSES (2) consecutive passes without a gain after the first
    (baseline) pass stop the stage.  A met endpoint (WNS and TNS >= 0) never stops.  -> None or the stop record"""
    if not c["OT_FF_RT"]:
        return None
    n, k, pct = max(1, c["OT_FF_RT_ROWS"]), c["OT_FF_RT_PASSES"], c["OT_FF_RT_MIN_GAIN_PCT"]
    blocks = [rows[i:i + n] for i in range(0, len(rows) - len(rows) % n, n)]
    if len(blocks) < k + 1:
        return None
    bw, bt = max(r[0] for r in blocks[0]), max(r[1] for r in blocks[0])
    flat, last = 0, None
    for b in blocks[1:]:
        w, t = max(r[0] for r in b), max(r[1] for r in b)
        gw, gt = _gain_pct(bw, w), _gain_pct(bt, t)
        flat = 0 if (gw >= pct or gt >= pct) else flat + 1
        last = {"wns": w, "tns": t, "viol": min(r[2] for r in b)}
        bw, bt = max(bw, w), max(bt, t)
    if flat >= k and (bw < 0 or bt < 0):
        return {"rule": "NOCONVERGE", "kind": "repair_timing", "passes": k, "rows_per_pass": n, "min_gain_pct": pct,
                "wns": bw, "tns": bt, "viol": last["viol"] if last else None}
    return None


def noconverge_line(d, stamp=True):
    stp = time.strftime(" %Y-%m-%d %H:%M:%S", time.gmtime()) if stamp else ""
    if d.get("kind") == "round_wall":
        return ("OT_GRT_NOCONVERGE stage=grt class=GRT_NOCONVERGE: GRT round wall budget %d s exceeded (open round %d s old) with round-best overflow %s "
                "(< %g%% gain); stopping the stage (FLOW-FIX-0100, design:grt_flat_overflow)%s"
                % (d["wall_s"], d["age_s"], " -> ".join(str(v) for v in d["tail"]), d["min_gain_pct"], stp))
    if d.get("kind") == "repair_timing":
        return ("OT_GRT_NOCONVERGE stage=grt class=GRT_NOCONVERGE: repair_timing no progress, %d consecutive passes of %d rows gained less than %g%% "
                "WNS/TNS (best WNS %s TNS %s, %s violating endpoints); stopping the stage (FLOW-FIX-0100, design:grt_flat_overflow)%s"
                % (d["passes"], d["rows_per_pass"], d["min_gain_pct"], d["wns"], d["tns"], d["viol"], stp))
    return ("OT_GRT_NOCONVERGE stage=grt class=GRT_NOCONVERGE: %d consecutive GRT restarts each gained less than %g%% of the round-best overflow "
            "(best per round %s, %d completed rounds); stopping the stage (MEM-RECLAIM-2200, design:grt_flat_overflow)%s"
            % (d["restarts"], d["min_gain_pct"], " -> ".join(str(v) for v in d["tail"]), d["rounds"], stp))


def _noconv_history(rp, t0, state_path, settle_s):
    """the persisted congestion snapshots of this run plus the new settled ones -> list; written back to state_path"""
    st = {}
    if state_path:
        try:
            st = json.load(open(state_path))
        except (OSError, ValueError):
            st = {}
    seen = {(h[0], h[1]) for h in st.get("cong", [])}
    for n, mt, p in reports_now(rp, t0, settle_s):
        if (n, mt) not in seen:
            try:
                st.setdefault("cong", []).append([n, mt, parse_report(open(p, errors="replace").read())["total"]])
            except OSError:
                continue
    if state_path and st.get("cong"):
        try:
            with open(state_path + ".tmp", "w") as f:
                json.dump(st, f)
            os.replace(state_path + ".tmp", state_path)
        except OSError:
            pass
    return st.get("cong", [])


# ------------------------------------------------------------------------------------------------ (c) hold
def hold_decide(caps, stall, c, config_text=""):
    if not c["OT_FF_HOLD"] or advisory(config_text):
        return None
    if stall:
        return {"rule": "HOLD_STRUCTURAL", "why": "OT_HOLD_STALL: " + stall[:200]}
    if c["OT_FF_HOLD_CAPS"] > 0 and caps >= c["OT_FF_HOLD_CAPS"]:
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
    # (d) GRT restarts with no overflow gain (OWNER 11-20); an overflow value alone, or elapsed time, never stops GRT (OWNER 11-14)
    if c["OT_FF_NOCONV"] and grt:
        hist = _noconv_history(rp, t0, state_path, settle_s)
        d = noconverge_decide(hist, c) or round_wall_decide(hist, time.time() if now is None else now, c)
        if d:
            return [noconverge_line(d)]
        # FLOW-FIX-0100: repair_timing no-progress (setup tables of this run's GRT logs)
        if c["OT_FF_RT"]:
            for p in sorted(grt):
                d = rt_decide(rt_rows(_read_lines(p)), c)
                if d:
                    return [noconverge_line(d)]
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
