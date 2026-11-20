#!/usr/bin/env python3
"""route_results: the real failure rate past setup, read from the kits themselves (ROUTE-RESULTS block of the hourly write-up).

Owner request (COORD 11-19): per die, how many builds finished CTS / GRT / route / sign-off in a window, how many passed the gate
(DRC 0, TT setup >= -42 ps, FF hold >= 0) and how many failed, by class (setup timing, hold, congestion/overflow, DRC, tool crash).
Sources are the ORFS run of each build, never the wave log:
  <kit>/run/logs/asap7/<design>/base/{4_1_cts,5_1_grt,5_2_route}.{json,log}   stage metrics + logs (mtime = stage end)
  <kit>/signoff/signoff.json                                                   sign-off verdict (route.drc, checks, profile_gates)
A build counts in a stage row when that stage's file was written inside the window.  A build ENDS in the window when its last
event is inside it:  sign-off.json written (pass / fail class),  route finished with DRC > 0 (DRC),  a stage log with a crash or
overflow signature and no result (tool crash / congestion),  a stage log with no result idle for --stale-min (tool crash, shown apart as "no signature": the
run died or was cancelled; dated when the idle time ran out),  or route finished with no sign-off yet (pending, not a failure).  A build still writing its log is running and is
not counted.  A build that fails more than one gate is counted once, by its first failing gate in the order DRC, setup, hold.

Dead builds are split so the fail rate is honest:  "crash" = a crash signature is in the stage log (real tool crash);  "cancelled" = the
build was cancelled or superseded (an ot-run cancel signal for its dir in ~/.local/state/ot-run/signals.log, or a CANCELLED row in the
wave state kit_wave_state.json, matched on die/event/item/attempt);  "dead" = no process, log idle, and neither record (unexplained).
Only setup, hold, congestion, DRC and real crash count as failures in the fail rate; cancelled and dead are shown apart.

usage: route_results.py [--since 'YYYY-MM-DD HH:MM'] [--until 'YYYY-MM-DD HH:MM'] [--hours N] [--hosts h1,h2,...] [--roots d1,d2] [--extra f1.json,...]
                        [--stale-min N] [--wave-state F] [--fast] [--json] [--collect]
  --hosts   'all' = the live fleet; epyc4 (terminated) is always dropped; fan out over ssh ('local' = this host, no ssh) (this script is piped to `python3 -I -` on each host, --collect), then merge
  --fast    hourly mode: only the wave run trees (claude/kw*/runs) and private build dirs in use now or touched in the last 24 h
  --collect internal: print the raw per-build records of this host as JSON
Times are local time (hosts run PST).  Default window: 00:00 today to now.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

STAGES = ("cts", "grt", "route", "signoff")
STAGE_FILE = {"cts": "4_1_cts", "grt": "5_1_grt", "route": "5_2_route"}
CLASSES = ("setup", "hold", "congestion", "drc", "crash")     # the failures
APART = ("cancelled", "dead")                                   # not failures: cancelled/superseded, unexplained dead
SIGNALS_LOG = os.path.expanduser("~/.local/state/ot-run/signals.log")
WAVE_STATE = os.path.expanduser("~/coord/autopilot/kit_wave_state.json")
CANCEL_RE = re.compile(r"signal (?:15|9|2) from .* -> ot-run .* dir (/[^\s:,]+)")
KIT_RE = re.compile(r"/kit-wave/(?P<die>[^/]+)/(?P<event>[^/]+)/items/(?P<item>[^/]+)/(?:attempt_(?P<n>\d+)/)?gen/")
CLASS_LABEL = {"setup": "setup timing", "hold": "hold", "congestion": "congestion/overflow", "drc": "DRC", "crash": "real tool crash (signature)",
               "cancelled": "cancelled/superseded", "dead": "dead, unexplained"}
DIES = ("s81", "head", "qc", "kv", "hbm", "other")
SETUP_MIN_PS = -42.0     # academic profile: TT setup >= -42 ps
HOLD_MIN_PS = 0.0        # FF hold >= 0
STALE_MIN = 120
SETTLE_S = 300           # a crash/congestion signature counts once the log has been quiet this long
ACTIVE_S = 1800          # any log of the build written in the last 30 min: alive (sealed ot-job / bwrap / docker runs hide their processes)
DEFAULT_HOSTS = "local,epyc2,epyc7,epyc8,epyc9,epyc10,intel1"
RETIRED_HOSTS = {"epyc4"}   # terminated (COORD 11-20)          # a stage log with no result and no write for this long: the run died
SKIP_DIRS = {"results", "objects", "rtl", "reports", ".git", "__pycache__", "node_modules", "plandir", "future_lec", "geom"}
MAX_DEPTH = 14
CRASH_RE = re.compile(r"Segmentation fault|terminate called|std::bad_alloc|\bKilled\b|Traceback \(most recent|core dumped|"
                      r"\[ERROR (?!GRT-0116)[A-Z]+-\d+\]|signal \d+ received|Out of memory", re.I)
CONG_RE = re.compile(r"GRT-0116|GRT-0183|Global routing finished with (?:overflow|congestion)|routing congestion", re.I)


KEY_DIE = {"s81": "s81", "s81_head": "head", "qwen_compute": "qc", "qwen_kvsys": "kv", "hbm": "hbm"}


def die_of(path):
    """die of a kit path: the kit-wave/<die>/ component when there is one, else private-build name hints."""
    m = re.search(r"/kit-wave/([a-z0-9_]+)/", path)
    if m and m.group(1) in KEY_DIE:
        return KEY_DIE[m.group(1)]
    low = path.lower()
    for die, rx in (("head", r"/hd_|head"), ("kv", r"/kv3?_|kvsys|/kv-|-kv-"), ("hbm", r"/hbm|/hfd_|/hgi_|/hnx_|-hbm-"),
                    ("s81", r"/col_h|slice_station|ot_s81|bk_sel|dsdv_|s81"), ("qc", r"/(slw|sle|cbf|cbn|cbx)_|qwen_compute|-qc-|/qc-")):
        if re.search(rx, low):
            return die
    return "other"


def mtime(p):
    try:
        return os.stat(p).st_mtime
    except OSError:
        return None


def load_json(p):
    try:
        with open(p) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def tail(p, n=4000):
    try:
        with open(p, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - n))
            return f.read().decode("utf-8", "replace")
    except OSError:
        return ""


def find_bases(root):
    """every .../logs/asap7/<design>/base directory under root (bounded depth, heavy result trees pruned)."""
    out = []
    root = root.rstrip("/")
    base_depth = root.count("/")
    for dp, dns, _ in os.walk(root, followlinks=False):
        if dp.count("/") - base_depth >= MAX_DEPTH:
            dns[:] = []
            continue
        if dp.endswith("/logs/asap7"):
            for d in dns:
                b = os.path.join(dp, d, "base")
                if os.path.isdir(b):
                    out.append(b)
            dns[:] = []
            continue
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        # inside a kit only run/logs/asap7 matters (signoff.json is read by path): skip the other thousands of kit files
        if os.path.basename(os.path.dirname(dp)) == "gen":
            dns[:] = [d for d in dns if d == "run"]
        elif os.path.basename(dp) == "run":
            dns[:] = [d for d in dns if d == "logs"]
        elif os.path.basename(dp) == "logs":
            dns[:] = [d for d in dns if d == "asap7"]
    return out


def live_snapshot():
    """one string of every process cwd + command line on this host: a build whose kit path appears in it is still running."""
    parts = []
    for pid in os.listdir("/proc") if os.path.isdir("/proc") else []:
        if not pid.isdigit():
            continue
        try:
            parts.append(os.readlink("/proc/%s/cwd" % pid))
            with open("/proc/%s/cmdline" % pid, "rb") as f:
                parts.append(f.read().replace(b"\0", b" ").decode("utf-8", "replace"))
        except OSError:
            continue
    return "\n".join(parts)


def cancel_dirs(path=SIGNALS_LOG, tail_bytes=60_000_000):
    """dirs of ot-run clients that got a kill signal (ot-run --cancel, the wave's reap): kits cancelled on this host."""
    out = set()
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - tail_bytes))
            for ln in f.read().decode("utf-8", "replace").splitlines():
                m = CANCEL_RE.search(ln)
                if m:
                    out.add(m.group(1).rstrip("/"))
    except OSError:
        pass
    return out


def wave_cancelled(path=WAVE_STATE):
    """{(die, event, item, attempt)} of every CANCELLED row of the wave state (SUPERSEDED, reaped)."""
    try:
        with open(path) as f:
            items = (json.load(f) or {}).get("items") or {}
    except (OSError, ValueError):
        return set()
    out = set()
    for key, v in items.items():
        if isinstance(v, dict) and v.get("status") == "CANCELLED":
            parts = key.split("|")
            if len(parts) >= 2:
                out.add((parts[0], str(v.get("event")), parts[1], v.get("attempt")))
    return out


def is_cancelled(rec, wave):
    """wave CANCELLED row for this kit's die/event/item (and attempt when the path has one), or an ot-run cancel signal on its host."""
    if rec.get("cancel_sig"):
        return True
    m = KIT_RE.search(rec["kit"] + "/")
    if not m:
        return False
    n = int(m.group("n")) if m.group("n") else None
    return any(w[0] == m.group("die") and w[1] == m.group("event") and w[2] == m.group("item") and (n is None or w[3] == n) for w in wave)


def record(base, live="", cancel=()):
    """one build: stage times + the facts the classifier needs.  base = <kit>/run/logs/asap7/<design>/base"""
    design = os.path.basename(os.path.dirname(base))
    kit = base.split("/run/logs/asap7/")[0]
    rec = {"kit": kit, "design": design, "die": die_of(kit), "item": design[3:] if design.startswith("dp_") else design,
           "t": {}, "log_t": {}, "res": {}, "live": bool(live) and kit in live,
           "cancel_sig": kit in cancel or (kit + "/run") in cancel}
    for st, f in STAGE_FILE.items():
        j = mtime(os.path.join(base, f + ".json"))
        l = mtime(os.path.join(base, f + ".log"))
        if j is not None:
            rec["t"][st] = j
        if l is not None:
            rec["log_t"][st] = l
    # newest sign of life: stage logs, other logs in the stage dir, and the kit root's own logs (run_route.log, tt_setup_repair.log, ...);
    # a sealed ot-job (bwrap) keeps these in <ot-jobs>/<job>/work, where the host process-path check cannot see the run
    act = [v for v in rec["log_t"].values()]
    for d in (base, kit):
        try:
            for e in os.scandir(d):
                if e.name.endswith(".log"):
                    act.append(e.stat().st_mtime)
        except OSError:
            pass
    rec["act"] = max(act) if act else None
    sj = os.path.join(kit, "signoff", "signoff.json")
    t = mtime(sj)
    if t is not None:
        rec["t"]["signoff"] = t
        d = load_json(sj) or {}
        rec["res"]["signoff"] = {
            "verdict": d.get("verdict"),
            "drc": (d.get("route") or {}).get("drc"),
            "setup": ((d.get("checks") or {}).get("setup_tt") or {}).get("wns_ps"),
            "hold": ((d.get("checks") or {}).get("hold_ff") or {}).get("wns_ps"),
            "gates": d.get("profile_gates") or {},
        }
    if "route" in rec["t"]:
        d = load_json(os.path.join(base, "5_2_route.json")) or {}
        rec["res"]["route_drc"] = d.get("detailedroute__route__drc_errors")
    # a stage that wrote a log but no result: keep the tail verdict (crash / congestion signature)
    for st, f in STAGE_FILE.items():
        if st in rec["log_t"] and st not in rec["t"]:
            tx = tail(os.path.join(base, f + ".log"))
            rec["res"]["fail_" + st] = "congestion" if CONG_RE.search(tx) else ("crash" if CRASH_RE.search(tx) else "")
    return rec


def gate_eval(sres):
    """(passed, first failing class) from a sign-off record; the profile's own gates win, raw thresholds are the fallback."""
    gates = sres.get("gates") or {}

    def ok(name, raw, test):
        g = gates.get(name)
        if g is not None:
            return str(g).upper() == "PASS"
        return raw is not None and test(raw)

    drc_ok = ok("drc", sres.get("drc"), lambda v: v == 0)
    setup_ok = ok("setup_tt", sres.get("setup"), lambda v: v >= SETUP_MIN_PS)
    hold_ok = ok("hold_ff", sres.get("hold"), lambda v: v >= HOLD_MIN_PS)
    if not drc_ok:
        return False, "drc"
    if not setup_ok:
        return False, "setup"
    if not hold_ok:
        return False, "hold"
    return True, None


def outcome(rec, now, stale_s, cancelled=False):
    """terminal state of a build -> (time, kind), kind in pass, setup, hold, drc, congestion, crash, cancelled, dead, pending;
    None = running/unstarted."""
    t = rec["t"]
    if "signoff" in t:
        passed, cls = gate_eval(rec["res"].get("signoff") or {})
        return t["signoff"], "pass" if passed else cls
    if "route" in t:
        drc = rec["res"].get("route_drc")
        if drc:
            return t["route"], "drc"
        return t["route"], "pending"
    if rec.get("live"):
        return None      # a process still works in this kit: running, not failed
    act = rec.get("act")
    recent = act is not None and now - act < ACTIVE_S      # sealed ot-job / bwrap / docker runs hide their processes: a fresh log means alive
    for st in ("route", "grt", "cts"):
        lt = rec["log_t"].get(st)
        if lt is None or st in t:
            continue
        if cancelled:
            return lt, "cancelled"
        kind = rec["res"].get("fail_" + st, "")
        if kind and (act is None or now - act >= SETTLE_S):      # a signature in a log that is still being written is not final
            return lt, kind
        if recent:
            return None
        la = max(lt, act or 0)
        if now - la > stale_s:
            return la + stale_s, "dead"      # declared dead when the idle time ran out, so it lands in that hour once
        return None
    return None


def collect(roots, live=None):
    """records of every build under roots; roots are walked in parallel (the trees are large, the walk is I/O bound)."""
    live = live_snapshot() if live is None else live
    cancel = cancel_dirs()
    roots = [r for r in roots if os.path.isdir(r)]
    with ThreadPoolExecutor(max_workers=8) as ex:
        found = list(ex.map(find_bases, roots))
    seen, recs = set(), []
    for bases in found:
        for b in bases:
            real = os.path.realpath(b)
            if real not in seen:
                seen.add(real)
                recs.append(record(b, live, cancel))
    return recs


def default_roots():
    roots = []
    for sc in sorted(os.listdir("/srv")) if os.path.isdir("/srv") else []:
        if not sc.startswith("opentallas-scratch"):
            continue
        c = os.path.join("/srv", sc, "claude")
        if os.path.isdir(c):
            roots += [os.path.join(c, d) for d in sorted(os.listdir(c)) if os.path.isdir(os.path.join(c, d))]
    return roots


def fast_roots(since, live=None, srv="/srv"):
    """hourly roots: wave run trees plus the private build dirs in use now or touched in the last 24 h (not the whole disk)."""
    live = live_snapshot() if live is None else live
    roots = []
    for sc in sorted(os.listdir(srv)) if os.path.isdir(srv) else []:
        c = os.path.join(srv, sc, "claude")
        if not sc.startswith("opentallas-scratch") or not os.path.isdir(c):
            continue
        used = set(re.findall(re.escape(c) + r"/([^/\s:]+)", live))
        for d in sorted(os.listdir(c)):
            p = os.path.join(c, d)
            if not os.path.isdir(p):
                continue
            if d.startswith("kw"):
                roots += [r for r in (os.path.join(p, "runs"),) if os.path.isdir(r)]
            elif d in used or (mtime(p) or 0) >= since - 86400:
                roots.append(p)
    return roots


def aggregate(recs, since, until, now, stale_s, wave=frozenset()):
    tab = {d: {"cts": 0, "grt": 0, "route": 0, "signoff": 0, "pass": 0, "pending": 0,
               **{c: 0 for c in CLASSES + APART}, "ended": 0, "names": {}} for d in DIES}
    seen = set()
    # a design that runs somewhere right now (sealed ot-job copy, another host) is not dead in its other, older kit dirs
    running = {r["design"] for r in recs if r.get("live") or (r.get("act") is not None and now - r["act"] < ACTIVE_S)}
    for r in recs:
        key = (r["die"], r["design"], tuple(sorted(r["t"].items())))
        if key in seen:
            continue
        seen.add(key)
        row = tab[r["die"] if r["die"] in tab else "other"]
        for st in STAGES:
            if st in r["t"] and since <= r["t"][st] < until:
                row[st] += 1
        oc = outcome(r, now, stale_s, is_cancelled(r, wave))
        if oc is not None and oc[1] in ("dead", "crash", "cancelled") and r["design"] in running and not (r.get("live") or (r.get("act") is not None and now - r["act"] < ACTIVE_S)):
            continue
        if oc is None or not (since <= oc[0] < until):
            continue
        kind = oc[1]
        row["ended"] += 1
        if kind == "pass":
            row["pass"] += 1
        elif kind == "pending":
            row["pending"] += 1
        else:
            row[kind] += 1
            row["names"].setdefault(kind, []).append(r["item"])
    return tab


def render(tab, since, until, hosts_note=""):
    f = lambda t: time.strftime("%m-%d %H:%M", time.localtime(t))
    cols = ("cts", "grt", "route", "signoff", "pass", "setup", "hold", "congestion", "drc", "crash", "cancelled", "dead", "pending")
    lines = ["ROUTE-RESULTS %s to %s (from kit run logs + signoff.json; gate = DRC 0, TT setup >= %d ps, FF hold >= 0)%s"
             % (f(since), f(until), SETUP_MIN_PS, hosts_note),
             "| die | CTS | GRT | route | sign-off | pass | fail setup | fail hold | fail congestion | fail DRC | fail real crash | cancelled/superseded | dead, unexplained | routed, no sign-off |",
             "|" + "---|" * 14]
    tot = {k: 0 for k in cols}
    for d in DIES:
        r = tab[d]
        if not any(r[k] for k in cols):
            continue
        lines.append("| %s | %s |" % (d, " | ".join(str(r[k]) for k in cols)))
        for k in cols:
            tot[k] += r[k]
    lines.append("| all | %s |" % " | ".join(str(tot[k]) for k in cols))
    fails = sum(tot[c] for c in CLASSES)
    done = tot["pass"] + fails
    lines.append("decided past CTS: %d  passed %d  failed %d%s;  not failures: %d cancelled/superseded, %d dead unexplained, %d routed awaiting sign-off"
                 % (done, tot["pass"], fails, "  (fail rate %.0f%%)" % (100.0 * fails / done) if done else "",
                    tot["cancelled"], tot["dead"], tot["pending"]))
    if tot["dead"]:
        lines.append("  dead unexplained = no process, no crash signature, log idle >= %d min, no ot-run cancel or wave CANCELLED row" % STALE_MIN)
    for d in DIES:
        for c, names in sorted(tab[d]["names"].items()):
            lines.append("  %s %s: %d (%s%s)" % (d, CLASS_LABEL[c], len(names), ", ".join(sorted(names)[:4]), ", ..." if len(names) > 4 else ""))
    return "\n".join(lines)


def parse_time(s):
    return time.mktime(time.strptime(s, "%Y-%m-%d %H:%M"))


def fan_out(hosts, since, roots, timeout, fast=False):
    src = open(os.path.abspath(__file__)).read()

    def one(h):
        if h == "local":      # the hub itself: no ssh to self
            try:
                return h, [r for r in collect(roots or (fast_roots(since) if fast else default_roots())) if any(v >= since for v in list(r["t"].values()) + list(r["log_t"].values()))], None
            except Exception as e:
                return h, [], "local: %s" % str(e)[:80]
        cmd = ["ssh", "-o", "ControlPath=none", "-o", "BatchMode=yes", h, "python3", "-I", "-", "--collect", "--since-epoch", str(since)]
        if roots:
            cmd += ["--roots", ",".join(roots)]
        if fast:
            cmd += ["--fast"]
        try:
            p = subprocess.run(cmd, input=src, capture_output=True, text=True, timeout=timeout)
            return h, json.loads(p.stdout), None
        except Exception as e:   # one dead host must not hide the rest
            return h, [], "%s: %s" % (h, str(e)[:80])
    with ThreadPoolExecutor(max_workers=len(hosts)) as ex:
        return list(ex.map(one, hosts))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--since")
    ap.add_argument("--until")
    ap.add_argument("--since-epoch", type=float)
    ap.add_argument("--hours", type=float)
    ap.add_argument("--hosts")
    ap.add_argument("--roots")
    ap.add_argument("--extra", help="comma list of --collect JSON files from hosts the hub cannot ssh to (the operator's own machine)")
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--wave-state", default=WAVE_STATE)
    ap.add_argument("--stale-min", type=float, default=STALE_MIN)
    ap.add_argument("--timeout", type=float, default=540)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--collect", action="store_true")
    a = ap.parse_args(argv)
    if a.hosts:
        a.hosts = ",".join(h for h in (DEFAULT_HOSTS if a.hosts == "all" else a.hosts).split(",") if h and h not in RETIRED_HOSTS)
    now = time.time()
    lt = time.localtime(now)
    midnight = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 0, 0, 0, 0, 0, -1))
    until = parse_time(a.until) if a.until else now
    since = a.since_epoch if a.since_epoch is not None else (parse_time(a.since) if a.since else (until - a.hours * 3600 if a.hours else midnight))
    roots = [r for r in a.roots.split(",") if r] if a.roots else None
    pick = lambda: roots or (fast_roots(since) if a.fast else default_roots())
    if a.collect:
        json.dump([r for r in collect(pick()) if any(v >= since for v in list(r["t"].values()) + list(r["log_t"].values()))], sys.stdout)
        return 0
    note = ""
    if a.hosts:
        recs, errs = [], []
        for h, rs, err in fan_out([h for h in a.hosts.split(",") if h], since, roots, a.timeout, a.fast):
            recs += rs
            if err:
                errs.append(err)
        note = "  hosts %s%s" % (a.hosts, "  UNREACHED: " + "; ".join(errs) if errs else "")
    else:
        recs = collect(pick())
    for fn in [x for x in (a.extra or "").split(",") if x]:
        with open(fn) as fh:
            recs += json.load(fh)
    tab = aggregate(recs, since, until, now, a.stale_min * 60, wave_cancelled(a.wave_state))
    if a.json:
        print(json.dumps({"since": since, "until": until, "table": tab}))
    else:
        print(render(tab, since, until, note))
    return 0


if __name__ == "__main__":
    sys.exit(main())
