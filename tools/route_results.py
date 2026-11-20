#!/usr/bin/env python3
"""route_results: the real failure rate past setup, read from the kits themselves (ROUTE-RESULTS block of the hourly write-up).

Owner request (COORD 11-19): per die, how many builds finished CTS / GRT / route / sign-off in a window, how many passed the gate
(DRC 0, TT setup >= -42 ps, FF hold >= 0) and how many failed, by class (setup timing, hold, congestion/overflow, DRC, tool crash).
Sources are the ORFS run of each build, never the wave log:
  <kit>/run/logs/asap7/<design>/base/{4_1_cts,5_1_grt,5_2_route}.{json,log}   stage metrics + logs (mtime = stage end)
  <kit>/signoff/signoff.json                                                   sign-off verdict (route.drc, checks, profile_gates)
A build counts in a stage row when that stage's file was written inside the window.  A build ENDS in the window when its last
event is inside it:  sign-off.json written (pass / fail class),  route finished with DRC > 0 (DRC),  a stage log with a crash or
overflow signature and no result (tool crash / congestion),  a stage log with no result idle for --stale-min (tool crash: the
run died; dated when the idle time ran out),  or route finished with no sign-off yet (pending, not a failure).  A build still writing its log is running and is
not counted.  A build that fails more than one gate is counted once, by its first failing gate in the order DRC, setup, hold.

usage: route_results.py [--since 'YYYY-MM-DD HH:MM'] [--until 'YYYY-MM-DD HH:MM'] [--hours N] [--hosts h1,h2,...] [--roots d1,d2] [--extra f1.json,...]
                        [--stale-min N] [--json] [--collect]
  --hosts   fan out over ssh (this script is piped to `python3 -I -` on each host, --collect), then merge
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
CLASSES = ("setup", "hold", "congestion", "drc", "crash")
CLASS_LABEL = {"setup": "setup timing", "hold": "hold", "congestion": "congestion/overflow", "drc": "DRC", "crash": "tool crash"}
DIES = ("s81", "head", "qc", "kv", "hbm", "other")
SETUP_MIN_PS = -42.0     # academic profile: TT setup >= -42 ps
HOLD_MIN_PS = 0.0        # FF hold >= 0
STALE_MIN = 120          # a stage log with no result and no write for this long: the run died
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
    return out


def record(base):
    """one build: stage times + the facts the classifier needs.  base = <kit>/run/logs/asap7/<design>/base"""
    design = os.path.basename(os.path.dirname(base))
    kit = base.split("/run/logs/asap7/")[0]
    rec = {"kit": kit, "design": design, "die": die_of(kit), "item": os.path.basename(kit),
           "t": {}, "log_t": {}, "res": {}}
    for st, f in STAGE_FILE.items():
        j = mtime(os.path.join(base, f + ".json"))
        l = mtime(os.path.join(base, f + ".log"))
        if j is not None:
            rec["t"][st] = j
        if l is not None:
            rec["log_t"][st] = l
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


def outcome(rec, now, stale_s):
    """terminal state of a build -> (time, kind) with kind in pass, setup, hold, drc, congestion, crash, pending; None = running/unstarted."""
    t = rec["t"]
    if "signoff" in t:
        passed, cls = gate_eval(rec["res"].get("signoff") or {})
        return t["signoff"], "pass" if passed else cls
    if "route" in t:
        drc = rec["res"].get("route_drc")
        if drc:
            return t["route"], "drc"
        return t["route"], "pending"
    # no route result: look at the newest stage without a result
    for st in ("route", "grt", "cts"):
        lt = rec["log_t"].get(st)
        if lt is None or st in t:
            continue
        kind = rec["res"].get("fail_" + st, "")
        if kind:
            return lt, kind
        if now - lt > stale_s:
            return lt + stale_s, "crash"      # declared dead when the idle time ran out, so it lands in that hour once
        return None
    return None


def collect(roots):
    seen, recs = set(), []
    for r in roots:
        if not os.path.isdir(r):
            continue
        for b in find_bases(r):
            real = os.path.realpath(b)
            if real in seen:
                continue
            seen.add(real)
            recs.append(record(b))
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


def aggregate(recs, since, until, now, stale_s):
    tab = {d: {"cts": 0, "grt": 0, "route": 0, "signoff": 0, "pass": 0, "pending": 0,
               **{c: 0 for c in CLASSES}, "ended": 0, "names": {}} for d in DIES}
    seen = set()
    for r in recs:
        key = (r["die"], r["design"], tuple(sorted(r["t"].items())))
        if key in seen:
            continue
        seen.add(key)
        row = tab[r["die"] if r["die"] in tab else "other"]
        for st in STAGES:
            if st in r["t"] and since <= r["t"][st] < until:
                row[st] += 1
        oc = outcome(r, now, stale_s)
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
    lines = ["ROUTE-RESULTS %s to %s (from kit run logs + signoff.json; gate = DRC 0, TT setup >= %d ps, FF hold >= 0)%s"
             % (f(since), f(until), SETUP_MIN_PS, hosts_note),
             "| die | CTS | GRT | route | sign-off | pass | fail setup | fail hold | fail congestion | fail DRC | fail crash | routed, no sign-off |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    tot = {k: 0 for k in ("cts", "grt", "route", "signoff", "pass", "pending", *CLASSES)}
    for d in DIES:
        r = tab[d]
        if not any(r[k] for k in tot):
            continue
        lines.append("| %s | %d | %d | %d | %d | %d | %d | %d | %d | %d | %d | %d |" % (
            d, r["cts"], r["grt"], r["route"], r["signoff"], r["pass"], r["setup"], r["hold"], r["congestion"], r["drc"], r["crash"], r["pending"]))
        for k in tot:
            tot[k] += r[k]
    lines.append("| all | %d | %d | %d | %d | %d | %d | %d | %d | %d | %d | %d |" % (
        tot["cts"], tot["grt"], tot["route"], tot["signoff"], tot["pass"], tot["setup"], tot["hold"], tot["congestion"], tot["drc"], tot["crash"], tot["pending"]))
    fails = sum(tot[c] for c in CLASSES)
    done = tot["pass"] + fails
    lines.append("ended past CTS: %d  passed %d  failed %d%s" % (done + tot["pending"], tot["pass"], fails,
                 "  (fail rate %.0f%% of %d decided)" % (100.0 * fails / done, done) if done else ""))
    for d in DIES:
        for c, names in sorted(tab[d]["names"].items()):
            lines.append("  %s %s: %d (%s%s)" % (d, CLASS_LABEL[c], len(names), ", ".join(sorted(names)[:4]), ", ..." if len(names) > 4 else ""))
    return "\n".join(lines)


def parse_time(s):
    return time.mktime(time.strptime(s, "%Y-%m-%d %H:%M"))


def fan_out(hosts, since, roots, timeout):
    src = open(os.path.abspath(__file__)).read()

    def one(h):
        cmd = ["ssh", "-o", "ControlPath=none", "-o", "BatchMode=yes", h, "python3", "-I", "-", "--collect", "--since-epoch", str(since)]
        if roots:
            cmd += ["--roots", ",".join(roots)]
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
    ap.add_argument("--stale-min", type=float, default=STALE_MIN)
    ap.add_argument("--timeout", type=float, default=540)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--collect", action="store_true")
    a = ap.parse_args(argv)
    now = time.time()
    lt = time.localtime(now)
    midnight = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 0, 0, 0, 0, 0, -1))
    until = parse_time(a.until) if a.until else now
    since = a.since_epoch if a.since_epoch is not None else (parse_time(a.since) if a.since else (until - a.hours * 3600 if a.hours else midnight))
    roots = [r for r in a.roots.split(",") if r] if a.roots else None
    if a.collect:
        json.dump([r for r in collect(roots or default_roots()) if any(v >= since for v in list(r["t"].values()) + list(r["log_t"].values()))], sys.stdout)
        return 0
    note = ""
    if a.hosts:
        recs, errs = [], []
        for h, rs, err in fan_out([h for h in a.hosts.split(",") if h], since, roots, a.timeout):
            recs += rs
            if err:
                errs.append(err)
        note = "  hosts %s%s" % (a.hosts, "  UNREACHED: " + "; ".join(errs) if errs else "")
    else:
        recs = collect(roots or default_roots())
    for fn in [x for x in (a.extra or "").split(",") if x]:
        with open(fn) as fh:
            recs += json.load(fh)
    tab = aggregate(recs, since, until, now, a.stale_min * 60)
    if a.json:
        print(json.dumps({"since": since, "until": until, "table": tab}))
    else:
        print(render(tab, since, until, note))
    return 0


if __name__ == "__main__":
    sys.exit(main())
