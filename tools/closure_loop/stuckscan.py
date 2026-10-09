#!/usr/bin/env python3
"""Stuck / slow / hopeless / redundant route scanner for the closure loop (OWNER 2026-10-08, stream stuckscan).

Run by the 15-min closure drive.  For every live loop job (RUNNING / ECO / ECO_INSTALL) it probes the job's run dir on
its host (one ssh per host) and diagnoses:
  hung       no log / stage-output write for > HUNG_QUIET_S AND the job's processes use < 0.2 cores
  slow       time in the current ORFS step > 2x the p90 duration of that step on finished jobs (scaled by floorplan
             ODB size), or the step log is quiet > HUNG_QUIET_S while the processes still burn CPU
  hopeless   the early-fail gates (shared with the daemon, closure_loop.early_fail_gate):
               EARLY_FAIL_SETUP       post-CTS (else post-placement) TT setup far past what DRT/opt ever recovered
               EARLY_FAIL_HOLD        FF hold repair NOT converging: buffers past a cap, WNS < 0 frozen over 2000 it, or
                                      real WNS < -150 ps after 1 h with < 5 ps gained over 2000 it
               EARLY_FAIL_CONGESTION  GRT past extra iteration 20 with the congestion markers not decreasing
               EARLY_FAIL_DRC         DRT past iteration 20 with the violation count not decreasing over K iterations
  hold_stop  a non-converging hold repair already within hold_nearmiss_ps (-15 ps) with the setup gate clear: NOT an
             early fail; `closure_loop.py hold-stop` resumes the route from its checkpoint with the hold repair cut
  stalled    old-flow (no OT_HOLD_GUARD) hold repair with hold already >= 0 and WNS frozen for > 3 h (margin chase)
  redundant  the block already CLOSED (a counting, TT-era closure), or a newer descendant commit of the same variant of
             the same block is RUNNING
Output: JSON (per-job diagnosis + recommended action: cancel | early_fail | kill_stage | let_run).
--apply executes the unambiguous ones: redundant -> `closure_loop.py cancel --why`; hopeless -> `closure_loop.py
early-fail` (terminal EARLY_FAIL_* verdict, worst-path summary in {CL}/early_fail.json, picked up by failtrig/scan.py
as redesign work and written as an item into failtrig/stuck/); hung / stalled margin chase -> `closure_loop.py
kill-stage` (the loop's crash path retries the stage once under the current flow).

    stuckscan.py [--apply] [--out FILE] [--only NAME ...] [--no-cpu]
    stuckscan.py --calibrate      # refresh the history cache and print the setup-gate calibration
"""
import argparse, concurrent.futures as cf, datetime as dt, json, os, re, statistics, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import closure_loop as cl  # noqa: E402

TAKEOVER = Path(os.environ.get("CL_TAKEOVER", "/home/ubuntu/claude-takeover-20261007"))
FAILTRIG = TAKEOVER / "failtrig"
HIST = cl.STATE / "stuckscan_hist.json"
LIVE = ("RUNNING", "ECO", "ECO_INSTALL")
SIGNOFF_PS = 833.333
HUNG_QUIET_S = 45 * 60
# coordinator 2026-10-08: CRITICAL_PATH item 1 (S81 BF and its half-rate fallbacks) is never auto-stopped: report only
PROTECTED_NAME = re.compile(r"^(bfh|bfi|bf_)|halfphl")
PROTECTED_BLOCKS = {"ot_s81_bf_native"}
ASSUME_DELTA_PS = 100.0


def protected(j):
    return bool(PROTECTED_NAME.search(j["name"])) or j["spec"].get("block") in PROTECTED_BLOCKS


def insertion_untrusted(j):
    """why the route's IO model may be off (coordinator 2026-10-08, bfh_halfphl: route started on another variant's
    insertion, SS 1169 vs measured 1546): the parallel calibrate measured > 100 ps off the assumption, or has not
    measured yet and the assumption came from another job's variant.  None = trusted (no assumption, or confirmed)."""
    ct = j.get("ctrack") or {}
    a = ct.get("assumed")
    if not a:
        return None
    m = ct.get("measured")
    if m:
        d = max(abs(float(m.get(k, a.get(k, 0))) - float(a.get(k, 0))) for k in ("CK_SS_MEAN", "CK_FF_MEAN") if k in a)
        return f"measured insertion {d:.0f} ps off the assumption ({ct.get('source')})" if d > ASSUME_DELTA_PS else None
    src = re.search(r"\(([A-Za-z0-9._-]+)[,)]", ct.get("source") or "")
    c = j.get("commit_full") or ""
    if src and variant(src.group(1), "") != variant(j["name"], "") and \
            re.sub(r"[-_]?[0-9a-f]{9}.*$", "", src.group(1)) != re.sub(r"[-_]?[0-9a-f]{9}.*$", "", j["name"]):
        return f"assumed insertion from another variant ({ct.get('source')}), not yet measured"
    return None
HUNG_CPU = 0.2

# ---- early-fail thresholds (calibrated 2026-10-08 on the loop's finished TT-corner routes, see --calibrate and the
# README "Early-fail gates"; sign-off-normalised slack = route-period WNS + (833.333 - route period)).
GATES = dict(
    setup_cts_ws_ps=-400.0,      # post-CTS TT WNS (normalised to 833.333) below this ...
    setup_cts_count=500,         # ... with more failing endpoints than this (at the route period) ...
    setup_tns_ps=-1.0e6,         # ... or TNS beyond this (count-free bound)
    setup_place_ws_ps=-900.0,    # post-placement (ideal clocks) bound, used only before CTS finishes
    setup_place_count=2000,
    # hold (drive-2140): the endpoint count in margin is NOT a gate; only a non-converging repair is (hold_verdict)
    hold_buf_cap=100000,         # hold buffers inserted in the step (rx128: 146k -> DPL-0033) ...
    hold_buf_frac=0.30,          # ... or this fraction of the placed instance count ...
    hold_buf_min=20000,          # ... (never below this many buffers)
    hold_buf_improve_dwns=5.0,   # real WNS < 0 gaining >= this over hold_stall_it iterations: improving, so the cap's
    hold_buf_improve_frac=0.60,  # ... fraction and ...
    hold_buf_improve_min=60000,  # ... floor are raised to these (drive-2155: never kill a converging repair on buffers)
    hold_stall_it=2000,          # real WNS < 0 gaining < hold_stall_dwns ps over this many iterations: stalled
    hold_stall_dwns=1.0,
    hold_stall_tns_pct=2.0,      # ... AND hold TNS improving < this % over the same window (the flow guard's rule): a
                                 # flat WNS with TNS falling is one stubborn endpoint, not a stall (drive-2155: su_full
                                 # TNS -30.8k -> -2.9k, selt_c -12.7k -> -18 were killed on a flat WNS)
    hold_real_ws_ps=-150.0,      # real hold WNS still below this ...
    hold_real_after_s=3600,      # ... after this long in repair ...
    hold_deep_it=2000,           # ... gaining < hold_deep_dwns ps over this many iterations
    hold_deep_dwns=5.0,
    hold_nearmiss_ps=-15.0,      # drive-resume (coordinator APPROVED 2026-10-09): a non-converging hold repair whose real
                                 # WNS is already >= this, with the setup gate not firing, is HOLD_STOP (stop the hold
                                 # repair, resume the route from its checkpoint; the post-route hold ECO fixes the residue),
                                 # never EARLY_FAIL_HOLD.  qfd_tile_rp1p was killed at -3.6 after 8.7 h, tile_e at -7.8.
    grt_min_iter=20, grt_markers=1000, grt_flat=0.95,
    drt_min_iter=20, drt_k=8, drt_min_viol=100,
    stall_after_s=3 * 3600,
)

PROBE = r'''
import json, os, re, glob, time, subprocess, sys
REQ = json.loads(sys.stdin.readline())
KEYS = re.compile(r"timing__(setup|hold)__(ws|tns)$|violation_count$|instance__count$|core__util$|drc_errors|overflow")
def jload(p):
    try: return json.load(open(p))
    except Exception: return None
def rd(p, n=None):
    try:
        with open(p, "rb") as f:
            if n:
                f.seek(0, 2); sz = f.tell(); f.seek(max(0, sz - n))
            return f.read().decode("utf-8", "replace")
    except Exception: return ""
def mt(p):
    try: return os.stat(p).st_mtime
    except Exception: return None
def bases(item):
    if item.get("orfs"):
        return sorted(glob.glob(item["orfs"] + "/logs/asap7/*/base"))
    r = item["run"]; out = set()
    for pat in ("routes/*/work/orfs/logs/asap7/*/base", "routes/*/logs/asap7/*/base", "*/work/orfs/logs/asap7/*/base",
                "routes/*/*/work/orfs/logs/asap7/*/base", "routes/*/*/logs/asap7/*/base"):
        out |= set(glob.glob(r + "/" + pat))
    return sorted(out)
HOLD_ROW = re.compile(r"^\s*(\d+|final)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([+-]?[\d.]+)%\s*\|\s*([-+\d.e]+)\s*\|\s*([-+\d.e]+)\s*\|", re.M)
def worst_paths(rpt):
    t = rd(rpt)
    i = t.find("report_checks -path_delay max\n")
    if i < 0: return []
    sec = t[i:]; j = sec.find("\n=====", 10); sec = sec[:j] if j > 0 else sec
    PIN = re.compile(r"^\s*(?:(\d+)\s+([\d.]+)\s+)?([\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+[\^v]\s+(\S+)\s*(\(\S+\))?")
    out = []
    for blk in sec.split("Startpoint: ")[1:]:
        l2 = blk.split("\n")[:2] + [""]
        sp = (l2[0].split() or ["?"])[0]
        m = re.search(r"Endpoint: (\S+)", blk); ep = m.group(1) if m else "?"
        sk = re.search(r"\((.*?)\)", l2[0]) or re.search(r"^\s*\((.*?)\)", l2[1]); sk = sk.group(1) if sk else ""
        ek = re.search(r"Endpoint: \S+\s*\n?\s*\((.*?)\)", blk); ek = ek.group(1) if ek else ""
        grp = re.search(r"Path Group: (\S+)", blk); sl = re.search(r"([-\d.]+)\s+slack", blk)
        arr = blk.split("data arrival time")[0]
        req = blk.split("data arrival time", 1)[1] if "data arrival time" in blk else ""
        vl = re.search(r"([-\d.]+)\s+[-\d.]+\s+clock network delay \(ideal\)", arr)
        vc = re.search(r"([-\d.]+)\s+[-\d.]+\s+clock network delay \(ideal\)", req)
        side = req if vl else arr      # the register end of an IO path: capture side of in->reg, launch side of reg->out
        ce = re.search(r"[-\d.]+\s+([-\d.]+)\s+clock \S+ \((?:rise|fall) edge\)", side)
        ck = re.search(r"\s([-\d.]+)\s+[\^v]\s+\S+/(?:CLK|CK|CLKN|GCLK)\s", side)
        wire = cell = 0.0; fo = 0; after_net = started = False; scell = ecell = ""
        for ln in arr.split("\n"):
            if ln.rstrip().endswith("(net)"):
                after_net = True; continue
            if "input external delay" in ln:
                started = True; continue
            m2 = PIN.match(ln)
            if not m2: continue
            name, c = m2.group(6), (m2.group(7) or "")
            if not started:
                if name == sp or name.startswith(sp + "/"):
                    started = True; scell = c
                    if name == sp or after_net:
                        after_net = False; continue
                else:
                    after_net = False; continue
            d = float(m2.group(4))
            if after_net: wire += d
            else: cell += d
            if m2.group(1): fo = max(fo, int(m2.group(1)))
            ecell = c; after_net = False
        out.append(dict(group=grp.group(1) if grp else "?", start=sp, start_kind=sk, start_cell=scell.strip("()"),
                        end=ep, end_kind=ek, end_cell=ecell.strip("()"), slack_ps=float(sl.group(1)) if sl else None,
                        wire_ps=round(wire, 1), cell_ps=round(cell, 1), max_fanout=fo,
                        vlat_launch=float(vl.group(1)) if vl else None, vlat_capture=float(vc.group(1)) if vc else None,
                        flop_ck_ps=round(float(ck.group(1)) - float(ce.group(1)), 1) if (ck and ce) else None))
    return out
def probe_base(b, live):
    root = b.rsplit("/logs/asap7/", 1)[0]; d = b.split("/logs/asap7/", 1)[1].split("/")[0]
    rep = f"{root}/reports/asap7/{d}/base"; res = f"{root}/results/asap7/{d}/base"
    logs = []
    for f in glob.glob(b + "/*.log"):
        try: s = os.stat(f); logs.append((os.path.basename(f), s.st_mtime, s.st_size))
        except Exception: pass
    met = {}
    for f in glob.glob(b + "/*.json"):
        j = jload(f)
        if isinstance(j, dict):
            met[os.path.basename(f)[:-5]] = {k: v for k, v in j.items() if KEYS.search(k)}
    corner = None
    for f in ("1_2_yosys.log", "1_1_yosys_canonicalize.log", "1_synth.log", "2_1_floorplan.log"):
        m = re.search(r"_[RLS]*VT_(TT|SS|FF)_", rd(b + "/" + f, 400000) if os.path.exists(b + "/" + f) else "")
        if m: corner = m.group(1); break
    per = rd(res + "/clock_period.txt").strip()
    o = dict(base=b, root=root, design=d, logs=logs, metrics=met, corner=corner,
             period=float(per) if re.match(r"^[\d.]+$", per or "x") else None,
             odb_mb=round((os.path.getsize(res + "/2_floorplan.odb") if os.path.exists(res + "/2_floorplan.odb") else 0) / 1e6, 2))
    if not live: return o
    tmp = sorted([l for l in logs if l[0].endswith(".tmp.log")], key=lambda x: -x[1])
    cur = tmp[0][0] if tmp else None
    o["current"] = cur
    if cur:
        t = rd(b + "/" + cur, 40000000)
        rows = HOLD_ROW.findall(t)
        hold = dict(found=[int(x) for x in re.findall(r"Found (\d+) endpoints with hold violations", t)][-3:],
                    guard=("OT_HOLD_GUARD start" in t), hm_auto=re.findall(r"OT_HM_AUTO.*", t)[-1:],
                    sync=re.findall(r"OT_HOLD_MM sync: SS setup ws ([-\d.]+) / FF hold ws ([-\d.]+)", t)[-1:],
                    stall=("OT_HOLD_STALL" in t))
        if rows:
            hold["rows"] = len(rows)
            hold["first"] = [rows[0][0], int(rows[0][2]), float(rows[0][5]), float(rows[0][6])]
            # rows of the CURRENT repair: after the last "Found N endpoints with hold" line
            k = t.rfind("endpoints with hold violations")
            cur_rows = HOLD_ROW.findall(t[k:]) if k >= 0 else rows
            if cur_rows:
                hold["cur_first"] = [cur_rows[0][0], int(cur_rows[0][2]), float(cur_rows[0][5]), float(cur_rows[0][6])]
                hold["cur_last"] = [cur_rows[-1][0], int(cur_rows[-1][2]), float(cur_rows[-1][5]), float(cur_rows[-1][6])]
                its = [r for r in cur_rows if r[0] != "final"]
                if len(its) >= 2:
                    last_it = int(its[-1][0]); w_last = float(its[-1][5])
                    back = [r for r in its if int(r[0]) <= last_it - 1000]
                    if back: hold["dwns_1000"] = round(w_last - float(back[-1][5]), 3)
            # whole-step convergence series [cumulative iteration, cumulative buffers, WNS] over every hold repair call of
            # the step (the HM/stall guard runs chunks of 1000 iterations, each restarting the iteration / buffer columns)
            ser = []; off = boff = 0; pit = pb = -1
            for r in rows:
                if r[0] == "final": continue
                it_, b_ = int(r[0]), int(r[2])
                if it_ < pit or (it_ == pit == 0):
                    off += max(pit, 0); boff += max(pb, 0)
                pit, pb = it_, b_
                ser.append([off + it_, boff + b_, float(r[5]), float(r[6])])
            if len(ser) > 400:
                ser = [ser[int(i * (len(ser) - 1) / 399)] for i in range(400)]
            hold["series"] = ser
        hold["chunks"] = [[int(a), float(w), float(g)] for a, w, g in
                          re.findall(r"OT_HOLD_GUARD chunk (\d+): hold ws ([-\d.]+) \([-+\d.]+\) tns [-\d.]+ \(([-+\d.]+)%\)", t)][-20:]
        o["hold"] = hold
        g = re.findall(r"Start extra iteration (\d+)/(\d+)", t)
        if g: o["grt_iter"] = [int(g[-1][0]), int(g[-1][1])]
        dv = re.findall(r"Start (\d+)(?:st|nd|rd|th) optimization iteration|Number of violations = (\d+)", t)
        it = None; seq = []
        for a, v in dv:
            if a: it = int(a)
            elif it is not None: seq.append([it, int(v)])
        if seq: o["drt"] = seq[-40:]
    cg = []
    for f in glob.glob(rep + "/congestion-*.rpt"):
        m = re.search(r"congestion-(\d+)\.rpt$", f)
        if m:
            try: n = rd(f).count("violation type:")
            except Exception: n = None
            cg.append([int(m.group(1)), n, mt(f)])
    o["congestion"] = sorted(cg)
    for r in ("4_cts_final.rpt", "3_detailed_place.rpt"):
        if os.path.exists(rep + "/" + r):
            o["worst"] = dict(report=r, paths=worst_paths(rep + "/" + r)); break
    return o
def tree_cpu(roots):
    kids = {}
    for p in os.listdir("/proc"):
        if not p.isdigit(): continue
        try:
            f = open(f"/proc/{p}/stat").read(); pp = int(f.rsplit(")", 1)[1].split()[1])
            kids.setdefault(pp, []).append(int(p))
        except Exception: pass
    def desc(r):
        out = [r]; st = [r]
        while st:
            x = st.pop()
            for c in kids.get(x, []): out.append(c); st.append(c)
        return out
    return {k: desc(v) for k, v in roots.items()}
def ticks(pids):
    s = 0
    for p in pids:
        try:
            f = open(f"/proc/{p}/stat").read().rsplit(")", 1)[1].split(); s += int(f[11]) + int(f[12])
        except Exception: pass
    return s
now = time.time(); out = {}
cont = {}
if REQ.get("cpu"):
    try:
        ids = subprocess.run(["docker", "ps", "-q"], capture_output=True, text=True, timeout=60).stdout.split()
        if ids:
            r = subprocess.run(["docker", "inspect", "-f", "{{.State.Pid}} {{range .Mounts}}{{.Source}} {{end}}"] + ids,
                               capture_output=True, text=True, timeout=120).stdout
            for ln in r.splitlines():
                w = ln.split()
                if w: cont[int(w[0])] = " ".join(w[1:])
    except Exception: pass
roots = {}
for it in REQ["items"]:
    n = it["name"]; o = dict(name=n)
    try:
        o["bases"] = [probe_base(b, it.get("live", False)) for b in bases(it)]
        if it.get("live"):
            run = it["run"]; tag = it.get("tag")
            fresh = []
            for dp, dn, fn in os.walk(run + "/cl"):
                if dp.count("/") - run.count("/") > 3: dn[:] = []; continue
                for f in fn:
                    m_ = mt(os.path.join(dp, f))
                    if m_: fresh.append(m_)
            for b in o["bases"]:
                fresh += [l[1] for l in b["logs"]] + [c[2] for c in b.get("congestion", []) if c[2]]
            o["fresh"] = max(fresh) if fresh else None
            pidf = f"{run}/cl/{tag}.pid"
            pid = rd(pidf).strip()
            o["pid_alive"] = bool(pid) and os.path.exists(f"/proc/{pid}")
            o["stage_log_mtime"] = mt(f"{run}/cl/{tag}.log")
            rl = []
            if pid.isdigit(): rl.append(int(pid))
            rl += [p for p, m in cont.items() if run + "/" in m + " " or m.find(run + " ") >= 0 or (run + "/") in m]
            roots[n] = rl
    except Exception as e:
        o["error"] = repr(e)
    out[n] = o
if REQ.get("cpu") and roots:
    trees = {}
    for n, rl in roots.items():
        s = set()
        for r in rl: s |= set(tree_cpu({0: r})[0])
        trees[n] = s
    t0 = {n: ticks(p) for n, p in trees.items()}; time.sleep(5); t1 = {n: ticks(p) for n, p in trees.items()}
    hz = os.sysconf("SC_CLK_TCK")
    for n in trees:
        out[n]["cpu_cores"] = round((t1[n] - t0[n]) / hz / 5.0, 2); out[n]["nproc"] = len(trees[n])
print(json.dumps(dict(now=now, jobs=out)))
'''


def probe(host, items, cpu=True, timeout=900):
    req = json.dumps(dict(items=items, cpu=cpu))
    r = cl.ssh(host, "python3 -c " + _q(PROBE), input=req + "\n", timeout=timeout)
    if r.returncode:
        return None, (r.stderr or r.stdout)[-400:]
    try:
        return json.loads(r.stdout.strip().splitlines()[-1]), None
    except Exception as ex:  # noqa: BLE001
        return None, f"bad probe output: {ex}: {r.stdout[-300:]} {r.stderr[-300:]}"


def _q(s):
    import shlex
    return shlex.quote(s)


# ------------------------------------------------------------------------------------------------- history (learned)
def step_durations(logs):
    """{step: seconds} from the finish mtimes of consecutive ORFS step logs (a step's duration = its log's mtime minus
    the previous step log's mtime)."""
    done = sorted([(m, n[:-4]) for n, m, _ in logs if n.endswith(".log") and not n.endswith(".tmp.log")])
    return {done[i][1]: done[i][0] - done[i - 1][0] for i in range(1, len(done))}


def norm_ws(ws, period):
    """route-period WNS -> sign-off (833.333) WNS for the 1.2 GHz domain (routes at 730-833 ps); a block on another
    clock (half-rate 1111 / 1666 ps ...) is signed off at its own period: no shift"""
    if ws is None or period is None:
        return None
    return ws + (SIGNOFF_PS - period) if 700.0 <= period <= SIGNOFF_PS + 0.5 else ws


def gate_metrics(b, only=None):
    """(stage, ws_norm, count, tns) of the latest post-CTS (else post-placement) setup metrics of one ORFS base."""
    m = b.get("metrics") or {}
    for stage, key, pre in (("cts", "4_1_cts", "cts"), ("place", "3_5_place_dp", "detailedplace")):
        if only and stage != only:
            continue
        x = m.get(key) or {}
        ws = x.get(f"{pre}__timing__setup__ws")
        if ws is None:
            continue
        return dict(stage=stage, ws=norm_ws(ws, b.get("period")), raw_ws=ws, period=b.get("period"),
                    count=x.get(f"{pre}__timing__drv__setup_violation_count"), tns=x.get(f"{pre}__timing__setup__tns"))
    return None


def load_hist():
    try:
        return json.loads(HIST.read_text())
    except Exception:  # noqa: BLE001
        return {}


def refresh_hist(jobs, max_new=2000):
    """Collect the step durations / gate metrics of finished jobs not yet in the cache (one ssh per host)."""
    h = load_hist()
    want = {}
    for j in jobs:
        m = j.get("metrics") or {}
        od = m.get("orfs_dir")
        if j["status"] in LIVE or not od or not j.get("host") or j["name"] in h:
            continue
        want.setdefault(j["host"], []).append(dict(name=j["name"], run=j.get("run"), orfs=od))
    hosts = {x["name"] for x in cl.hosts_table()}
    todo = {k: v[:max_new] for k, v in want.items() if k in hosts}

    def one(host):
        res, err = probe(host, todo[host], cpu=False, timeout=1800)
        return host, res, err
    with cf.ThreadPoolExecutor(8) as ex:
        for host, res, err in ex.map(one, todo):
            if not res:
                print(f"hist probe {host} failed: {err}", file=sys.stderr)
                continue
            for n, o in res["jobs"].items():
                j = next(x for x in jobs if x["name"] == n)
                m = j.get("metrics") or {}
                bs = [b for b in o.get("bases", []) if not b["design"].endswith("_cal")]
                b = bs[0] if bs else None
                h[n] = dict(status=j["status"], host=host, block=j["spec"].get("block"),
                            tt=m.get("ss_ps") if m.get("setup_corner") == "tt" else None,
                            ss=m.get("ss_ps") if m.get("setup_corner") != "tt" else m.get("ss_sensitivity_ps"),
                            ff=m.get("ff_ps"), drc=m.get("drc"), eco=bool(m.get("eco")),
                            corner=b and b.get("corner"), period=b and b.get("period"), odb_mb=b and b.get("odb_mb"),
                            steps=step_durations(b["logs"]) if b else {},
                            gates={st: gate_metrics(b, st) for st in ("cts", "place")} if b else {},
                            missing=not bs)
    HIST.write_text(json.dumps(h))
    return h


def expected_step(hist, step, odb_mb):
    """p90 of (step seconds per floorplan-ODB MB) over finished jobs x this job's ODB size; None without data."""
    rates = [v["steps"][step] / max(v["odb_mb"] or 1, 1) for v in hist.values()
             if (v.get("steps") or {}).get(step) and v.get("odb_mb")]
    if len(rates) < 8:
        return None
    rates.sort()
    return rates[int(0.9 * (len(rates) - 1))] * max(odb_mb or 1, 1)


def calibrate(hist):
    """Setup-gate calibration: for finished TT routes with post-CTS metrics, the recovery (final TT - post-CTS normalised
    WNS) and the worst post-CTS WNS of any job that later CLOSED (the gate must sit below it)."""
    rows = []
    for n, v in hist.items():
        for g in (v.get("gates") or {}).values():
            if v.get("corner") != "TT" or v.get("tt") is None or abs(v["tt"]) > 1e5 or not g or g.get("ws") is None:
                continue
            rows.append((n, g["stage"], round(g["ws"], 1), g.get("count"), g.get("tns"), v["tt"], v["status"]))
    out = {}
    for stage in ("cts", "place"):
        r = [x for x in rows if x[1] == stage]
        if not r:
            continue
        closed = [x for x in r if x[5] >= 0]
        rec = [x[5] - x[2] for x in r]
        killed = [x for x in r if x[2] < GATES[f"setup_{stage}_ws_ps"] and ((x[3] or 0) > GATES[f"setup_{stage}_count"] or
                                                                    (x[4] or 0) < GATES["setup_tns_ps"])]
        out[stage] = dict(
            n=len(r), closed_tt=len(closed),
            worst_ws_of_closed=min([x[2] for x in closed], default=None),
            worst_closed=sorted(closed, key=lambda x: x[2])[:5],
            recovery_ps=dict(p50=statistics.median(rec), p90=sorted(rec)[int(0.9 * (len(rec) - 1))], max=max(rec)),
            gate=dict(ws=GATES[f"setup_{stage}_ws_ps"], count=GATES[f"setup_{stage}_count"]),
            would_kill=len(killed), would_kill_closed=[x for x in killed if x[5] >= 0],
            would_kill_best_final=max([x[5] for x in killed], default=None))
    return out


# ------------------------------------------------------------------------------------------------- diagnosis
def hopeless(b, j, now):
    """[(verdict, why)] from the early-fail gates of one live ORFS base (shared with the daemon gate)."""
    out = []
    g = gate_metrics(b)
    tt = b.get("corner") == "TT"
    cur = b.get("current") or ""
    # the setup gate stops a run BEFORE it spends GRT/DRT; a run already past detail route keeps its final numbers
    if g and tt and g["ws"] is not None and not cur.startswith(("5_3", "6_")):
        st = g["stage"]
        cnt = g.get("count") or 0
        unt = insertion_untrusted(j) if j else None
        if unt:
            # IO slack is fake on a wrong insertion: judge reg->reg/macro paths only (worst per path group of the report)
            r2r = [p for p in path_classes(b) if p["cls"].split("->")[0] in ("reg", "macro")
                   and p["cls"].split("->")[1] in ("reg", "macro") and p["slack_ps"] is not None]
            w = min([norm_ws(p["slack_ps"], b.get("period")) for p in r2r], default=None)
            g = dict(g, ws=w, raw_ws=min(p["slack_ps"] for p in r2r) if r2r else None, io_excluded=unt)
            if w is None:
                g = None
    if g and tt and g["ws"] is not None and not cur.startswith(("5_3", "6_")) and not g.get("io_excluded") and \
            g["ws"] < GATES[f"setup_{st}_ws_ps"]:
        adj = ioref_rejudge(b, j)
        if adj is not None:
            g = dict(g, ws=adj["ws"], ioref=adj)
    if g and tt and g["ws"] is not None and not cur.startswith(("5_3", "6_")):
        if g["ws"] < GATES[f"setup_{st}_ws_ps"] and (cnt > GATES[f"setup_{st}_count"] or
                                                     (g.get("tns") or 0) < GATES["setup_tns_ps"]):
            out.append(("EARLY_FAIL_SETUP", f"post-{st} TT setup WNS {g['ws']:+.1f} ps at 833.333 (route-period "
                                            f"{g['raw_ws']:+.1f} at {g['period']:g}), {cnt} failing endpoints, TNS "
                                            f"{g.get('tns')}; gate WNS < {GATES[f'setup_{st}_ws_ps']:g} with > "
                                            f"{GATES[f'setup_{st}_count']} endpoints"
                                            + (f"; IO excluded, reg->reg/macro only ({g['io_excluded']})"
                                               if g.get("io_excluded") else "")
                                            + (f"; IO paths re-judged at the IO-reference insertion "
                                               f"({g['ioref']['source']}{'' if g['ioref']['ref_ps'] != g['ioref']['ref_ps'] else ' %.0f ps' % g['ioref']['ref_ps']})"
                                               if g.get("ioref") else "")))
    elapsed = now - step_start(b)
    hd = b.get("hold") or {}
    if cur.startswith(("4_1_cts", "5_1_grt")) and (hd.get("found") or hd.get("series")):
        hv = hold_verdict(hd, b, elapsed, bool(j and insertion_untrusted(j)))
        if hv:
            plan = hold_stop_plan(b)
            done = {x.get("stage") for x in (j or {}).get("hold_stop_log") or []}
            if plan and plan["stage"] not in done and not any(v == "EARLY_FAIL_SETUP" for v, _ in out):
                out.append(("HOLD_STOP", f"{cur[:-8]} near-miss hold stall (WNS {plan['ws']:+.1f} >= "
                                         f"{GATES['hold_nearmiss_ps']:g} ps, setup gate clear): stop the {plan['stage']} "
                                         f"hold repair at {plan['buffers']} buffers and continue to route; {hv}"))
            else:
                out.append(("EARLY_FAIL_HOLD", f"{cur[:-8]} {hv}"))
    cg = [c for c in b.get("congestion") or [] if c[1] is not None]
    gi = b.get("grt_iter")
    if cur.startswith("5_1_grt") and gi and gi[0] >= GATES["grt_min_iter"] and len(cg) >= 3:
        # GRT congestion oscillates between reports: hopeless = still above the marker bound AND no new best (by 5%)
        # in the last two reports (10 extra iterations)
        best_before = min(x[1] for x in cg[:-2])
        c = cg[-1][1]
        if c > GATES["grt_markers"] and min(cg[-1][1], cg[-2][1]) >= GATES["grt_flat"] * best_before:
            out.append(("EARLY_FAIL_CONGESTION", f"GRT extra iteration {gi[0]}/{gi[1]}: congestion markers "
                                                 f"{' -> '.join(str(x[1]) for x in cg[-4:])} (iterations "
                                                 f"{', '.join(str(x[0]) for x in cg[-4:])}): not decreasing"))
    dr = b.get("drt") or []
    if cur.startswith("5_2_route") and dr and dr[-1][0] >= GATES["drt_min_iter"]:
        k = GATES["drt_k"]
        last = [v for i, v in dr if i > dr[-1][0] - k]
        before = [v for i, v in dr if i <= dr[-1][0] - k]
        if before and last and min(last) >= min(before) and last[-1] > GATES["drt_min_viol"]:
            out.append(("EARLY_FAIL_DRC", f"DRT iteration {dr[-1][0]}: {last[-1]} violations, no decrease over the "
                                          f"last {k} iterations (best before {min(before)}, since {min(last)})"))
    return out


def ioref_insertion(j):
    """(ps, source) of the IO-reference insertion: the measured route-corner boundary mean (calibrate CK_SS_MEAN, the
    io_ref_routed.sdc definition), else None"""
    env = ((j or {}).get("calibration") or {}).get("env") or {}
    v = env.get("CK_SS_MEAN")
    return (float(v), "calibrate CK_SS_MEAN") if isinstance(v, (int, float)) else None


def ioref_rejudge(b, j):
    """DRV6 (review-0725, coordinator APPROVED 2026-10-09): the post-CTS setup gate judged IO paths against the virtual
    clock's IDEAL latency (an assumed insertion), not the IO reference: hbm_coll_port2_rows hm0-bal was early-failed at
    -491.6 (reg->out with ot_lb_v_core_clk at 1039.8 ps vs the measured 1221 ps tree).  Re-judge every reported path the
    way io_ref_routed.sdc times it: the virtual clock moves to the IO-reference insertion M (measured boundary mean,
    else the path's own register clock arrival), so reg->out slack += M - L_capture and in->reg slack -= M - L_launch
    (in->out unchanged).  Returns {"ws" (normalised, worst over all reported paths), ref_ps, source, paths} or None when
    no reported path carries an ideal virtual-clock latency."""
    paths = [p for p in (b.get("worst") or {}).get("paths") or [] if p.get("slack_ps") is not None]
    if not any(p.get("vlat_launch") is not None or p.get("vlat_capture") is not None for p in paths):
        return None
    ref = ioref_insertion(j)
    out, refs = [], set()
    for p in paths:
        s = p["slack_ps"]
        m, src = ref if ref else ((p.get("flop_ck_ps"), "path register clock arrival") if p.get("flop_ck_ps") is not None
                                  else (None, None))
        inp, outp = "input port" in (p.get("start_kind") or ""), "output port" in (p.get("end_kind") or "")
        if m is not None and inp != outp:
            if outp and p.get("vlat_capture") is not None:
                s = s + (m - p["vlat_capture"]); refs.add(src)
            elif inp and p.get("vlat_launch") is not None:
                s = s - (m - p["vlat_launch"]); refs.add(src)
        out.append(dict(start=p.get("start"), end=p.get("end"), group=p.get("group"), raw_ps=p["slack_ps"],
                        ioref_ps=round(s, 1)))
    w = min(x["ioref_ps"] for x in out)
    return dict(ws=norm_ws(w, b.get("period")), ref_ps=ref[0] if ref else float("nan"),
                source=", ".join(sorted(refs)) or "no IO path moved", paths=out)


def hold_gain(series, window):
    """WNS gained (ps) over the last `window` cumulative hold-repair iterations of the step; None while the series
    spans fewer iterations than the window."""
    if not series:
        return None
    last = series[-1]
    back = [p for p in series if p[0] <= last[0] - window]
    return round(last[2] - back[-1][2], 3) if back else None


def hold_tns_gain_pct(series, window):
    """hold TNS improvement (% of |TNS| at the window start) over the last `window` cumulative iterations; None when the
    series carries no TNS (older probe) or spans fewer iterations than the window."""
    if not series or len(series[-1]) < 4:
        return None
    last = series[-1]
    back = [p for p in series if p[0] <= last[0] - window]
    if not back or len(back[-1]) < 4:
        return None
    t0 = back[-1][3]
    return round(100.0 * (last[3] - t0) / abs(t0), 3) if t0 < 0 else 0.0


def place_instances(b):
    for k in ("3_5_place_dp", "3_4_place_resized", "3_3_place_gp"):
        for kk, v in ((b.get("metrics") or {}).get(k) or {}).items():
            if kk.endswith("design__instance__count") and isinstance(v, (int, float)):
                return v
    return None


def hold_verdict(hd, b, elapsed, untrusted=False):
    """EARLY_FAIL_HOLD only when the hold repair is NOT converging (drive-2140, 2026-10-08).  The endpoint count inside
    the margin (RSZ-0046) is NOT a verdict: at HM 10-25 a big block routinely has 30k-70k endpoints in margin with real
    WNS -20..-40 ps, and the repair converges (qfd_tile_rp1p / hbm_su_full / hbm_quant outline were killed at 10
    iterations while improving).  NEVER fires once real hold WNS >= 0 (drive-2155, OWNER: the margin is a design target,
    HM 0 allowed; hbm_su_ctlh vf-lvt was killed at +4.4 ps for filling toward HM): such a run proceeds (the flow's
    MET-FIRST guard stops the chase on new routes).  Fires on
      (1) buffers: hold buffers inserted in the step > hold_buf_cap, or > hold_buf_frac x placed instances (floor
          hold_buf_min); while real WNS is improving (>= hold_buf_improve_dwns ps over hold_stall_it iterations) the
          fraction / floor rise to hold_buf_improve_frac / hold_buf_improve_min;
      (2) stall: real WNS < 0 and < hold_stall_dwns ps gained over the last hold_stall_it cumulative iterations;
      (3) deep: real WNS < hold_real_ws_ps after hold_real_after_s with < hold_deep_dwns ps gained over the last
          hold_deep_it iterations.
    (2)/(3) are skipped on an untrusted clock insertion (IO hold may be fake there)."""
    ser = hd.get("series") or []
    last = hd.get("cur_last")
    ws = ser[-1][2] if ser else (last[2] if last else None)
    if ws is None or ws >= 0:
        return None
    its, bufs = (ser[-1][0], ser[-1][1]) if ser else (0, 0)
    n = (hd.get("found") or [None])[-1]
    start = ((hd.get("sync") or [[None, None]])[-1])[1]
    ctx = (f"hold WNS now {ws:+.1f} ps (start {start}), {its} it / {bufs} buffers, {n} endpoints in margin, "
           f"{elapsed / 3600:.1f} h in step, {'HM guard present' if hd.get('guard') else 'old flow without the HM/stall guard'}")
    g = hold_gain(ser, GATES["hold_stall_it"])
    cap = hold_buf_cap(place_instances(b), g)
    if bufs > cap:
        return f"hold repair past the buffer cap: {bufs} buffers > {cap:.0f} (cap {GATES['hold_buf_cap']}, " \
               f"{place_instances(b)} instances, WNS gain {g} ps / {GATES['hold_stall_it']} it); {ctx}"
    if untrusted:
        return None
    tg = hold_tns_gain_pct(ser, GATES["hold_stall_it"])
    if g is not None and g < GATES["hold_stall_dwns"] and (tg is None or tg < GATES["hold_stall_tns_pct"]):
        return f"hold repair not converging: WNS gained {g:+.2f} ps" \
               + (f" and TNS {tg:+.1f}%" if tg is not None else "") + \
               f" over the last {GATES['hold_stall_it']} iterations (< {GATES['hold_stall_dwns']:g} ps / " \
               f"{GATES['hold_stall_tns_pct']:g}%); {ctx}"
    if ws < GATES["hold_real_ws_ps"] and elapsed > GATES["hold_real_after_s"]:
        g = hold_gain(ser, GATES["hold_deep_it"])
        tg = hold_tns_gain_pct(ser, GATES["hold_deep_it"])
        if g is not None and g < GATES["hold_deep_dwns"] and (tg is None or tg < GATES["hold_stall_tns_pct"]):
            return f"real FF hold WNS {ws:+.1f} ps (< {GATES['hold_real_ws_ps']:g}) with no progress: {g:+.2f} ps over " \
                   f"the last {GATES['hold_deep_it']} iterations (< {GATES['hold_deep_dwns']:g}); {ctx}"
    return None


def hold_stop_plan(b):
    """HOLD-STOP plan of a live base whose hold repair is judged non-converging: {stage, buffers, ws} when the real hold
    WNS is >= hold_nearmiss_ps, else None.  buffers = the buffer count at which the repair first reached (within
    0.05 ps) its current WNS, +2% and +10 (the replay keeps the converging part, the flat tail is cut)."""
    cur = (b.get("current") or "")
    stage = "cts" if cur.startswith("4_1_cts") else "grt" if cur.startswith("5_1_grt") else None
    hd = b.get("hold") or {}
    ser = hd.get("series") or []
    last = hd.get("cur_last")
    ws = ser[-1][2] if ser else (last[2] if last else None)
    if stage is None or ws is None or ws >= 0 or ws < GATES["hold_nearmiss_ps"]:
        return None
    first = next((p for p in ser if p[2] >= ws - 0.05), None)
    n = int(first[1] * 1.02) + 10 if first and first[1] else 0
    return dict(stage=stage, buffers=n, ws=ws)


def hold_buf_cap(inst, gain):
    """the hold-buffer cap of a step: min(hold_buf_cap, max(floor, frac x placed instances)); frac / floor are raised
    while real WNS improves by >= hold_buf_improve_dwns over the last hold_stall_it iterations."""
    improving = gain is not None and gain >= GATES["hold_buf_improve_dwns"]
    frac = GATES["hold_buf_improve_frac" if improving else "hold_buf_frac"]
    floor = GATES["hold_buf_improve_min" if improving else "hold_buf_min"]
    cap = GATES["hold_buf_cap"]
    return min(cap, max(floor, frac * inst)) if inst else cap


def step_start(b):
    done = [m for n, m, _ in b.get("logs") or [] if not n.endswith(".tmp.log")]
    return max(done) if done else time.time()


def path_classes(b):
    """worst max-delay path per path group of the post-CTS (else post-placement) report, classed start->end
    (input / reg / macro -> reg / macro / out), wire- vs logic-dominated, max fanout on the path."""
    out = []
    for p in (b.get("worst") or {}).get("paths") or []:
        sk, ek = p.get("start_kind", ""), p.get("end_kind", "")
        s = "input" if "input port" in sk else ("reg" if "ASAP7" in p.get("start_cell", "ASAP7") else "macro")
        e = "out" if "output port" in ek else ("reg" if "ASAP7" in p.get("end_cell", "ASAP7") else "macro")
        out.append(dict(cls=f"{s}->{e}", slack_ps=p["slack_ps"], group=p["group"],
                        dominated="wire" if p["wire_ps"] > p["cell_ps"] else "logic", wire_ps=p["wire_ps"],
                        cell_ps=p["cell_ps"], max_fanout=p["max_fanout"], start=p["start"], end=p["end"],
                        check=ek))
    return sorted(out, key=lambda x: x["slack_ps"] if x["slack_ps"] is not None else 1e9)


def variant(name, commit):
    """the job name with its source sha (and the separators around it) folded: qfd_hub-172d343d8-tt ~ qfd_hub-3d5ad2a4ftt"""
    return re.sub(r"[-_]?" + re.escape(commit[:9]) + r"[-_]?", "#", name) if commit else name


def is_ancestor(old, new):
    if old == new:
        return False
    r = cl.sh(["git", "-C", str(cl.REPO), "merge-base", "--is-ancestor", old, new], timeout=60)
    return r.returncode == 0


def redundant(j, jobs, closed, any_variant=False):
    """(why, sure): sure = cancel without asking.  A counting CLOSED job of the block on the same or a NEWER commit makes
    this job redundant (sure); a closure on an OLDER commit only flags it (the newer source may carry a fix the
    adopted record needs).  Else a RUNNING job of the same block and variant (any variant with any_variant) on a
    descendant commit makes it redundant (sure)."""
    blk = j["spec"].get("block")
    c = j.get("commit_full") or j["spec"]["source"].get("commit", "")
    if blk in closed:
        rv = cl.revoked_closures()
        cj = [x for x in jobs if x["spec"].get("block") == blk and cl.closure_counts(x, rv)]
        newer = [x for x in cj if (x.get("commit_full") or "") == c or is_ancestor(c, x.get("commit_full") or "")]
        names = ", ".join(x["name"] for x in (newer or cj)[-2:])
        if newer:
            return f"block {blk} already CLOSED on this or a newer commit ({names})", True
        return f"block {blk} already CLOSED on an older commit ({names}); this job carries newer source", False
    v = variant(j["name"], c)
    for x in jobs:
        if x is j or x["status"] != "RUNNING" or x["spec"].get("block") != blk:
            continue
        xc = x.get("commit_full") or x["spec"]["source"].get("commit", "")
        if not xc or not c or xc == c or (variant(x["name"], xc) != v and not any_variant):
            continue
        if (x.get("created") or "") > (j.get("created") or "") and is_ancestor(c, xc):
            return f"newer commit {xc[:9]} of the {'same variant' if variant(x['name'], xc) == v else 'block'} is RUNNING " \
                   f"({x['name']})", True
    return None, False


def diagnose(j, o, hist, jobs, closed, now):
    d = dict(name=j["name"], host=j.get("host"), status=j["status"], stage=j.get("stage_key"),
             block=j["spec"].get("block"), owner=j["spec"].get("owner"), action="let_run", why=[])
    if not o or o.get("error"):
        d["why"].append(f"probe failed: {(o or {}).get('error', 'no data')}")
        return d
    bs = o.get("bases") or []
    stage_is_cal = j.get("stage_key") == "calibrate"
    main = [b for b in bs if b["design"].endswith("_cal") == stage_is_cal and b.get("current")]
    main = main or [b for b in bs if b["design"].endswith("_cal") == stage_is_cal]
    b = max(main, key=lambda x: max([l[1] for l in x["logs"]] or [0])) if main else None
    d["fresh_min"] = round((now - o["fresh"]) / 60, 1) if o.get("fresh") else None
    d["cpu_cores"] = o.get("cpu_cores")
    if b:
        d["orfs"] = b["root"]
        d["step"] = (b.get("current") or "")[:-8] or None
        d["step_h"] = round((now - step_start(b)) / 3600, 2)
        d["corner"] = b.get("corner")
        g = gate_metrics(b)
        if g:
            d["setup"] = {k: (round(v, 1) if isinstance(v, float) else v) for k, v in g.items()}
        if b.get("hold"):
            d["hold"] = {k: b["hold"][k] for k in ("found", "cur_last", "dwns_1000", "guard", "sync") if k in b["hold"]}
        if b.get("grt_iter"):
            d["grt_iter"] = b["grt_iter"]
            d["congestion"] = [[c[0], c[1]] for c in b.get("congestion") or []]
        if b.get("drt"):
            d["drt_last"] = b["drt"][-3:]
        exp = expected_step(hist, d["step"], b.get("odb_mb")) if d["step"] else None
        d["expected_h"] = round(exp / 3600, 2) if exp else None
    if protected(j):
        hp = hopeless(b, j, now) if b and j.get("stage_key") == "route" and j["status"] == "RUNNING" else []
        d["kind"] = "critical"
        d["why"].append("CRITICAL_PATH 1 (BF): never auto-stopped, report only" +
                        (": WOULD early-fail: " + "; ".join(w for _, w in hp) if hp else ""))
        return d
    # 1) redundant
    r, sure = redundant(j, jobs, closed)
    if r and sure and j["status"] != "ECO_INSTALL":
        d.update(action="cancel", kind="redundant")
        d["why"].append(r)
        return d
    if r:
        d["kind"] = "redundant?"
        d["why"].append(r + " -> owner decides")
    # 2) hopeless (route stage only: calibrate is CTS-only with no repair)
    if b and j.get("stage_key") == "route" and j["status"] == "RUNNING":
        hp = hopeless(b, j, now)
        if hp and hp[0][0] == "HOLD_STOP":
            d.update(action="hold_stop", kind="hold_nearmiss", hold_stop=hold_stop_plan(b))
            d["why"] += [w for _, w in hp]
            return d
        if hp:
            d.update(action="early_fail", kind="hopeless", verdict=hp[0][0])
            d["why"] += [w for _, w in hp]
            d["paths"] = path_classes(b)[:6]
            return d
    quiet = (now - o["fresh"]) if o.get("fresh") else None
    cpu = o.get("cpu_cores")
    # 3) hung: nothing written for > 45 min and no CPU
    if quiet is not None and quiet > HUNG_QUIET_S:
        if cpu is not None and cpu < HUNG_CPU and o.get("pid_alive"):
            d.update(action="kill_stage", kind="hung")
            d["why"].append(f"no write for {quiet / 60:.0f} min and {cpu} cores busy: hung (the loop retries the stage once)")
            return d
        d["why"].append(f"quiet {quiet / 60:.0f} min but {cpu} cores busy")
        d["kind"] = "quiet_busy"
    # 4) stalled margin chase (old flow, no hold guard)
    hd = (b or {}).get("hold") or {}
    if b and hd.get("cur_last") and not hd.get("guard") and (b.get("current") or "").startswith(("4_1_cts", "5_1_grt")):
        el = now - step_start(b)
        if hd["cur_last"][2] >= 0 and (hd.get("dwns_1000") is not None and abs(hd["dwns_1000"]) < 1.0) and \
                el > GATES["stall_after_s"]:
            r2, _ = redundant(j, jobs, set(), any_variant=True)
            if r2:      # a newer commit of the block is live: do not re-run this one
                d.update(action="cancel", kind="stalled")
                d["why"].append(f"{b['current'][:-8]} hold repair margin chase (hold WNS {hd['cur_last'][2]:+.1f} >= 0, "
                                f"frozen, {el / 3600:.1f} h, old flow) and {r2}")
                return d
            d.update(action="kill_stage", kind="stalled")
            d["why"].append(f"{b['current'][:-8]} hold repair margin chase: hold WNS {hd['cur_last'][2]:+.1f} ps >= 0, "
                            f"frozen (dWNS {hd['dwns_1000']} over 1000 it) after {el / 3600:.1f} h, no OT_HOLD_GUARD "
                            f"(old flow): kill -> loop retry under the guarded flow")
            return d
    # 4b) stage never started: launched, but no pid file and no stage log long after the launch (run dir lost)
    try:
        started = dt.datetime.fromisoformat(j.get("stage_started")).timestamp()
    except Exception:  # noqa: BLE001
        started = None
    if j["status"] == "RUNNING" and not o.get("pid_alive") and o.get("stage_log_mtime") is None and started and \
            now - started > 1800:
        d["kind"] = "never_started"
        d["why"].append(f"{j.get('stage_tag')} launched {(now - started) / 3600:.1f} h ago but has no pid file or log "
                        f"(run dir lost?): the loop's STARTING timeout re-launches it")
        return d
    # 5) slow
    if d.get("expected_h") and d.get("step_h") and d["step_h"] > max(2 * d["expected_h"], 1.0):
        d["kind"] = "slow" if d.get("kind") != "quiet_busy" else "slow_quiet"
        d["why"].append(f"{d['step']} running {d['step_h']} h vs p90 {d['expected_h']} h for its size")
    return d


def scan(only=None, cpu=True):
    jobs = cl.all_jobs()
    now = time.time()
    hist = load_hist()
    closed = cl.closed_blocks(jobs)
    live = [j for j in jobs if j["status"] in LIVE and j.get("host") and j.get("run") and (not only or j["name"] in only)]
    by = {}
    for j in live:
        by.setdefault(j["host"], []).append(dict(name=j["name"], run=j["run"], tag=j.get("stage_tag"), live=True))
    res = {}

    def one(host):
        return host, *probe(host, by[host], cpu=cpu)
    with cf.ThreadPoolExecutor(8) as ex:
        for host, r, err in ex.map(one, by):
            if r is None:
                for it in by[host]:
                    res[it["name"]] = dict(error=f"{host}: {err}")
            else:
                res.update(r["jobs"])
    return [diagnose(j, res.get(j["name"]), hist, jobs, closed, now) for j in live]


def failtrig_item(d):
    p = FAILTRIG / "stuck"
    p.mkdir(parents=True, exist_ok=True)
    (p / f"{d['name']}.json").write_text(json.dumps(dict(d, at=cl.now_iso(), source="stuckscan"), indent=1))


def apply(diags, log):
    done = []
    for d in diags:
        a = d["action"]
        if a == "let_run":
            continue
        why = "stuckscan: " + "; ".join(d["why"])[:600]
        if a == "cancel":
            cmd = ["cancel", d["name"], "--why", why]
        elif a == "early_fail":
            det = cl.STATE / "early_fail" / f"{d['name']}.json"
            det.parent.mkdir(parents=True, exist_ok=True)
            det.write_text(json.dumps(d, indent=1))
            cmd = ["early-fail", d["name"], "--verdict", d["verdict"], "--why", why, "--detail", str(det)]
        elif a == "kill_stage":
            cmd = ["kill-stage", d["name"], "--why", why]
        elif a == "hold_stop":
            cmd = ["hold-stop", d["name"], "--stage", d["hold_stop"]["stage"], "--buffers",
                   str(d["hold_stop"]["buffers"]), "--why", why]
        else:
            continue
        r = cl.sh([sys.executable, str(HERE / "closure_loop.py"), *cmd], timeout=900)
        ok = r.returncode == 0
        if ok and a == "early_fail":
            failtrig_item(d)
        line = f"{cl.now_iso()} {a.upper()} {'ok' if ok else 'FAILED rc=' + str(r.returncode)} {d['name']} [{d.get('kind')}] {why[11:300]}"
        if not ok:
            line += " :: " + (r.stderr or r.stdout).strip()[-200:]
        log.append(line)
        done.append(dict(name=d["name"], action=a, ok=ok))
    return done


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--no-cpu", action="store_true")
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--no-hist", action="store_true", help="skip the history refresh")
    a = ap.parse_args()
    if a.calibrate:
        h = refresh_hist(cl.all_jobs())
        print(json.dumps(calibrate(h), indent=1, default=str))
        return
    if not a.no_hist:
        try:
            refresh_hist(cl.all_jobs(), max_new=300)
        except Exception as ex:  # noqa: BLE001
            print(f"history refresh failed: {ex}", file=sys.stderr)
    diags = scan(a.only, cpu=not a.no_cpu)
    rep = dict(at=cl.now_iso(), gates=GATES, jobs=diags,
               counts={k: sum(1 for d in diags if d["action"] == k) for k in ("cancel", "early_fail", "hold_stop", "kill_stage", "let_run")})
    if a.apply:
        log = []
        rep["applied"] = apply(diags, log)
        with open(TAKEOVER / "stuckscan.log", "a") as f:
            f.write("".join(x + "\n" for x in log))
        print("\n".join(log))
    out = Path(a.out) if a.out else cl.STATE / "stuckscan_last.json"
    out.write_text(json.dumps(rep, indent=1, default=str))
    print(f"{len(diags)} live jobs: {rep['counts']}; report {out}")
    for d in diags:
        if d["action"] != "let_run" or d.get("kind"):
            print(f"  {d['action']:10s} {d.get('kind', ''):10s} {d['name']:55s} {d.get('step') or d.get('stage')} "
                  f"{d.get('step_h')}h | {'; '.join(d['why'])[:220]}")


if __name__ == "__main__":
    main()
