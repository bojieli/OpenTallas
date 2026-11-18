#!/usr/bin/env python3 -I
"""flow_health.py -- FLOW-HEALTH-1 (COORD 11-15): hourly flow report, no LLM.  Cron on intel2 (see FLOW_HEALTH_CRON below).

Writes lanes/FLOW-HEALTH.tsv (committed with coord-commit.sh) with two sections:
  1. one row per hour (last --hours): launches, fails BEFORE place and route by class (stage in kit_wave.PRE_PR_STAGES, or a class with
     no stage), fails IN P&R by stage, passes (KIT-WAVE ENQUEUE = the kit reached the queue), preflight refusals (state flow_guard.refused),
     and the class breakers open now (current hour row).  Source: autopilot/log.txt KIT-WAVE LAUNCH / FAIL / ENQUEUE lines.
  2. '# SKEW <time>': per die tree per host, the modules of gen_phys / gen / bind's import closure whose content differs from main
     (main = origin/main of the merge-queue repo; closure from main's own imports), plus ot-src-refresh `compare` cross-host
     differences restricted to those modules.  A missing file counts as a difference.
COORD reads the file each hour."""
import argparse
import collections
import datetime
import hashlib
import importlib.machinery
import importlib.util
import json
import os
import re
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flow_guard as FG  # noqa: E402

HOME = Path.home()
COORD = Path(os.environ.get("FH_COORD", HOME / "coord"))
LOG = Path(os.environ.get("FH_LOG", COORD / "autopilot/log.txt"))
STATE = Path(os.environ.get("FH_STATE", COORD / "autopilot/kit_wave_state.json"))
CFG = Path(os.environ.get("FH_CFG", COORD / "autopilot/kit_wave.json"))
OUT_REL = "lanes/FLOW-HEALTH.tsv"
REPO = os.environ.get("FH_REPO", "/srv/opentallas-scratch2/claude/mq1/repo")
SRC_REFRESH = os.environ.get("FH_SRC_REFRESH", "/srv/opentallas-scratch2/claude/rt/current/tools/fleet/ot-src-refresh")
TAIL_BYTES = 120 * 2**20
PRE_PR = ("mkdir", "bind", "bind_fetch", "kit_rtl", "gen", "gen_lint", "kit_topology", "preflight", "prov_views", "lec_tools",
          "views", "cells", "relay_bay", "sync_hub", "pipeline", "selfcontained", "type_overlay", "unit")
LINE = re.compile(r"^(\d{4}-\d\d-\d\d \d\d):\d\d:\d\d \S+ AUTOPILOT: KIT-WAVE (LAUNCH|FAIL|ENQUEUE) (\S+)(.*)$")
HEAD = ["hour", "launches", "fail_pre_pr", "fail_pre_pr_by_class", "fail_in_pr", "fail_in_pr_by_stage", "passes", "preflight_refused",
        "breakers_open"]


def read_tail(path, n=TAIL_BYTES):
    with open(path, "rb") as f:
        f.seek(0, 2)
        size = f.tell()
        f.seek(max(0, size - n))
        data = f.read()
    return data.decode("utf-8", "replace").splitlines()[1 if size > n else 0:]


def hourly(lines, hours, now=None):
    """-> {hour: {"launch": n, "pass": n, "pre": Counter(class), "pr": Counter(stage)}} for the last `hours` hours"""
    now = time.time() if now is None else now
    keep = {time.strftime("%Y-%m-%d %H", time.localtime(now - i * 3600)) for i in range(hours + 1)}
    out = {}
    for ln in lines:
        m = LINE.match(ln)
        if not m or m.group(1) not in keep:
            continue
        h = out.setdefault(m.group(1), {"launch": 0, "pass": 0, "pre": collections.Counter(), "pr": collections.Counter()})
        kind, rest = m.group(2), m.group(4)
        if kind == "LAUNCH":
            h["launch"] += 1
        elif kind == "ENQUEUE":
            h["pass"] += 1
        else:
            cls, _, why = rest.strip().partition(": ")
            stage = FG.fail_stage(why)
            if stage and stage not in PRE_PR:
                h["pr"][stage] += 1
            else:
                h["pre"][FG.norm_class(cls, why)[:110]] += 1
    return out


def fmt_counter(c, n=6):
    top = c.most_common(n)
    s = "; ".join(f"{v}x {k}" for k, v in top)
    return s + (f"; +{len(c) - n} more class(es)" if len(c) > n else "")


def state_info(state):
    g = (state or {}).get("flow_guard") or {}
    ref = collections.Counter(time.strftime("%Y-%m-%d %H", time.localtime(r[0])) for r in g.get("refused") or [])
    return ref, sorted((g.get("open") or {}))


def render(hours_data, refused, open_now, now=None):
    now = time.time() if now is None else now
    cur = time.strftime("%Y-%m-%d %H", time.localtime(now))
    rows = ["\t".join(HEAD)]
    for hr in sorted(set(hours_data) | set(refused)):
        h = hours_data.get(hr) or {"launch": 0, "pass": 0, "pre": collections.Counter(), "pr": collections.Counter()}
        rows.append("\t".join(str(x) for x in (hr, h["launch"], sum(h["pre"].values()), fmt_counter(h["pre"]), sum(h["pr"].values()),
                                              fmt_counter(h["pr"]), h["pass"], refused.get(hr, 0),
                                              " | ".join(open_now) if hr == cur else "")))
    return rows


# ---------------------------------------------------------------- skew

def is_local_host(h, fleet_table=os.path.join(str(COORD), "tools/fleet_hosts.tsv"), nodename=None):
    """FLOW-HEALTH-1 11-15 (COORD): True when `h` (fleet alias, cherry name, localhost) names this machine: a per-host scan of it reads locally
    instead of `ssh <itself>` (intel2 does not resolve on intel2)."""
    me = nodename or os.uname().nodename
    me = {me, me.split(".")[0]}
    if h in ("local", "localhost") or h in me:
        return True
    try:
        for ln in open(fleet_table).read().splitlines():
            f = ln.split("\t")
            if len(f) >= 2 and not ln.startswith("#") and f[0] == h and f[1] in me:
                return True
    except OSError:
        pass
    return False


def ssh_rpy(host, code, args, timeout=180):
    if is_local_host(host):
        cmd = [sys.executable, "-I", "-", json.dumps(args)]
    else:
        cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", "-o", "ControlPath=none", host, "python3", "-I", "-", shlex.quote(json.dumps(args))]
    try:
        p = subprocess.run(cmd, input=code, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"error": type(e).__name__}
    for line in reversed(p.stdout.splitlines()):
        if line.startswith("AP_JSON "):
            return json.loads(line[8:])
    return {"error": f"rc {p.returncode}: {(p.stderr or p.stdout).strip()[-200:]}"}


def main_reader(repo=REPO):
    def blob(rel):
        p = subprocess.run(["git", "-C", repo, "show", f"origin/main:{rel}"], capture_output=True)
        return p.stdout if p.returncode == 0 else None
    return blob


def trees_of(cfg, state=None, now=None, live_h=12.0):
    """[(die, tree)] and {die: [hosts]} of the LIVE wave trees (FABLE-FLOW-0015 b): the die's kit_wave.json src, plus the src named by the spec.json of every
    wave attempt that was active in the last live_h hours (a row still on an older tree is the skew to see) and the item_inputs src of items with such an
    attempt.  Old plans' item_inputs trees of finished items are no longer probed."""
    now = time.time() if now is None else now
    trees, hosts = [], {}
    live = collections.defaultdict(set)
    for r in ((state or {}).get("items") or {}).values():
        if not isinstance(r, dict) or now - float(r.get("updated") or 0) > live_h * 3600:
            continue
        if r.get("status") in ("RUNNING", "LAUNCHING", "ROUTE-HELD", "RETRY-INFRA", "ENQUEUED", "FAIL", "PASS") and r.get("dir"):
            try:
                s = json.loads((Path(r["dir"]) / "spec.json").read_text()).get("src")
            except (OSError, ValueError, TypeError):
                s = None
            if isinstance(s, str) and s.startswith("/"):
                live[r.get("die")].add(s)
            live[(r.get("die"), "items")].add(r.get("item"))
    for die, d in sorted((cfg.get("dies") or {}).items()):
        if not isinstance(d, dict) or not d.get("enabled") or not d.get("gen_host"):
            continue
        hosts[die] = [h for h in dict.fromkeys([d["gen_host"]] + list(d.get("gen_hosts") or [])) if h]
        act = live.get((die, "items"))
        ii = [v.get("src") for k, v in (d.get("item_inputs") or {}).items() if isinstance(v, dict) and (act is None or k in act or state is None)]
        srcs = [d.get("src")] + sorted(live.get(die, ())) + ii
        for s in dict.fromkeys(x for x in srcs if isinstance(x, str) and x.startswith("/")):
            trees.append((die, s))
    return trees, hosts


def compare_budget(mod, hosts, src, seconds=240):
    """ot-src-refresh compare() with a wall budget -> (problems, diffs) or ([note], {})"""
    import threading
    if threading.current_thread() is not threading.main_thread():      # SIGALRM only works in the main thread; compare() has its own ssh timeouts
        try:
            return mod.compare(hosts, src)
        except Exception as e:
            return [f"compare {type(e).__name__}"], {}

    def _h(sig, frm):
        raise TimeoutError()
    old = signal.signal(signal.SIGALRM, _h)
    signal.alarm(seconds)
    try:
        return mod.compare(hosts, src)
    except Exception as e:                          # a report never dies on one tree
        return [f"compare {type(e).__name__}"], {}
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


def skew_section(cfg, rpy=ssh_rpy, blob=None, compare_mod=None, now=None):
    now = time.time() if now is None else now
    blob = blob or main_reader()
    try:
        state = json.loads(STATE.read_text())
    except (OSError, ValueError):
        state = None
    trees, hosts = trees_of(cfg, state, now)
    rd = lambda rel: (blob(rel) or b"").decode("utf-8", "replace") if blob(rel) is not None else None   # noqa: E731
    cache = {}

    def text(rel):
        if rel not in cache:
            b = blob(rel)
            cache[rel] = b
        return cache[rel].decode("utf-8", "replace") if cache[rel] is not None else None
    sha = lambda rel: hashlib.sha1(cache[rel]).hexdigest() if text(rel) is not None else None   # noqa: E731
    files = FG.closure_files(text)
    rows = FG.skew_report(trees, sha, text, rpy, hosts)
    out = [f"# SKEW {time.strftime('%Y-%m-%d %H:%M', time.localtime(now))} closure of {', '.join(FG.ENTRY_FILES)} = {len(files)} modules vs origin/main",
           "\t".join(["die", "host", "tree", "n_differ_from_main", "modules"])]
    for die, h, tree, diff in rows:
        out.append("\t".join([die, h, tree, str(len(diff)), " ".join(diff[:20]) + (" ..." if len(diff) > 20 else "")]))
    if not rows:
        out.append("-\t-\t-\t0\tevery probed tree matches main on the closure")
    if compare_mod is not None:
        out.append("\t".join(["die", "tree", "cross_host_compare", "n", "modules"]))
        seen, todo = set(), []
        for die, tree in trees:
            hs = hosts.get(die) or []
            if len(hs) >= 2 and tree not in seen:
                seen.add(tree)
                todo.append((die, tree, hs))
        import concurrent.futures as cf
        with cf.ThreadPoolExecutor(max(1, min(8, len(todo)))) as ex:           # trees are independent: compared in parallel, every one of them
            res = list(ex.map(lambda x: compare_budget(compare_mod, x[2], x[1]), todo))
        for (die, tree, hs), (pb, diffs) in zip(todo, res):
            hit = [r for r in diffs if r in set(files)]
            out.append("\t".join([die, tree, "; ".join(pb)[:120] or "ok", str(len(hit)), " ".join(hit[:20])]))
    return out


HOSTS = ("epyc2", "epyc7", "epyc8", "epyc9", "epyc10", "intel1", "intel2")
RESOLVE_PY = r"""
import json, socket, sys
h = socket.gethostname()
try:
    ips = sorted({x[4][0] for x in socket.getaddrinfo(h, None)})
except OSError as e:
    ips = []
print("AP_JSON " + json.dumps({"host": h, "ips": ips}))
"""


def resolve_ok(ips):
    """a host's own name must resolve to a usable address: an /etc/hosts-style loopback / routable one, not nothing and not only
    link-local fe80:: (epyc7 11-15: ot-run could not resolve its own hostname)"""
    return any(not i.lower().startswith("fe80") for i in ips)


def hostname_section(rpy=ssh_rpy, hosts=HOSTS):
    out = ["# HOSTNAME-RESOLUTION (ot-run needs the host's own name to resolve; fix = append '127.0.1.1 <name>' to /etc/hosts, backup first)",
           "\t".join(["host", "hostname", "ips", "ok"])]
    for h in hosts:
        r = rpy(h, RESOLVE_PY, {}, timeout=60)
        if r.get("error"):
            out.append("\t".join([h, "-", str(r["error"])[:80], "unknown"]))
        else:
            out.append("\t".join([h, r["host"], ",".join(r["ips"])[:80] or "none", "yes" if resolve_ok(r["ips"]) else "NO"]))
    return out


WRAPPER = os.path.expanduser("~/.local/bin/ot-run")
OT_RUN_MAIN = "tools/fleet/ot-run"


def installed_backend(wrapper=WRAPPER):
    """the ot-run backend the installed wrapper execs (its last `exec ... <path>/ot-run` line), or ''"""
    try:
        for ln in reversed(open(wrapper).read().splitlines()):
            m = re.search(r"exec\s+\S*python3?\s+(\S+/ot-run)\b", ln)
            if m:
                return m.group(1)
    except OSError:
        pass
    return ""


def ot_run_drift(installed_text, main_text):
    """-> (state, n_differing_lines): SAME | DIFFERS | NO-INSTALLED | NO-MAIN"""
    if installed_text is None:
        return "NO-INSTALLED", 0
    if main_text is None:
        return "NO-MAIN", 0
    if installed_text == main_text:
        return "SAME", 0
    import difflib
    return "DIFFERS", sum(1 for l in difflib.unified_diff(installed_text.splitlines(), main_text.splitlines(), lineterm="", n=0)
                          if l[:1] in "+-" and l[:3] not in ("+++", "---"))


def ot_run_drift_section(blob=None, wrapper=WRAPPER, host=os.uname().nodename):
    """FLOW-HEALTH-1 11-15 (COORD r196): the installed ot-run backend must equal main's; hand patches that never reached main were nearly
    overwritten by a rollout on 11-15 (261 differing lines).  One row per check; DIFFERS names the number of differing lines."""
    path = installed_backend(wrapper)
    try:
        inst = open(path).read() if path else None
    except OSError:
        inst = None
    b = (blob or main_reader())(OT_RUN_MAIN)
    state, n = ot_run_drift(inst, b.decode("utf-8", "replace") if b is not None else None)
    return ["# OT-RUN-DRIFT installed backend vs origin/main " + OT_RUN_MAIN, "\t".join(["host", "backend", "state", "differing_lines"]),
            "\t".join([host, path or "-", state, str(n)])]


NOPROG_FILES = ("noprog_watchdog.py", "noprog_stage.py")
NOPROG_DIR = "~/.local/lib/noprog"
NOPROG_HOSTS = ("intel2", "intel1", "epyc2", "epyc7", "epyc8", "epyc9", "epyc10")
SHA_PY = r"""
import hashlib, json, os, sys
out = {}
a = json.loads(sys.argv[1])
for f in a["files"]:
    p = os.path.expanduser(os.path.join(a["dir"], f))
    try:
        out[f] = hashlib.sha1(open(p, "rb").read()).hexdigest()
    except OSError:
        out[f] = None
print("AP_JSON " + json.dumps(out))
"""


LOCAL_NAMES = {"localhost", os.uname().nodename, os.environ.get("OT_HUB_NAME", "intel2") if os.path.isdir(os.path.expanduser("~/coord")) else "-"}


def local_sha(args):
    try:
        p = subprocess.run([sys.executable, "-I", "-c", SHA_PY, json.dumps(args)], capture_output=True, text=True, timeout=60)
        for line in reversed(p.stdout.splitlines()):
            if line.startswith("AP_JSON "):
                return json.loads(line[8:])
    except (OSError, subprocess.TimeoutExpired):
        pass
    return {"error": "local"}


def noprog_drift_section(blob=None, rpy=None, hosts=NOPROG_HOSTS):
    """FLOW-HEALTH-1 11-15 (COORD r184): the noprog files the hub pushes to every host must equal main's tools/autopilot copies.
    One row per host and file: SAME | DIFFERS | MISSING | UNREACHABLE."""
    blob = blob or main_reader()
    rpy = rpy or ssh_rpy
    main = {}
    for f in NOPROG_FILES:
        b = blob("tools/autopilot/" + f)
        main[f] = hashlib.sha1(b).hexdigest() if b is not None else None
    out = ["# NOPROG-DRIFT installed ~/.local/lib/noprog vs origin/main tools/autopilot", "\t".join(["host", "file", "state"])]
    for h in hosts:
        args = {"files": list(NOPROG_FILES), "dir": NOPROG_DIR}
        if h in LOCAL_NAMES:                      # the hub cannot ssh to its own fleet name (intel2 does not resolve on intel2)
            r = local_sha(args)
        else:
            r = rpy(h, SHA_PY, args, timeout=60)
        for f in NOPROG_FILES:
            if not isinstance(r, dict) or r.get("error"):
                st = "UNREACHABLE"
            elif r.get(f) is None:
                st = "MISSING"
            elif main[f] is None:
                st = "NO-MAIN"
            else:
                st = "SAME" if r[f] == main[f] else "DIFFERS"
            out.append("\t".join([h, f, st]))
    return out


LISTING = os.path.expanduser("~/.local/state/fleet-viz/agidock_archive_index.json")
COUNT_CACHE = os.path.expanduser("~/.local/state/fleet-viz/release_tree_plan_cache.json")


def count_gap_rows(listing, cache):
    """FLOW-HEALTH-1 11-15 (FABLE-CENSUS-1815 class 10): INDEX.tsv rows of the AGIdock archive (ARCHIVED-BOTH core / type) whose die's count does
    not credit the name.  -> [(die, name, kind, state, note)].  3 QC n9 cores sat here for 5 h before anybody noticed."""
    credited, planned = {}, {}
    for e in (cache.get("plans") or {}).values():
        s = credited.setdefault(e.get("die"), set())
        pl = planned.setdefault(e.get("die"), set())
        for a in ("signed_types", "signed_cores", "signed_designs"):
            s.update((e.get(a) or {}).keys())
        pl.update(e.get("hard_cores") or [])
        pt = e.get("plan_types")
        pl.update(pt.keys() if isinstance(pt, dict) else (pt or []) if not isinstance(pt, int) else [])
        pl.update((e.get("designs") or {}).keys() if isinstance(e.get("designs"), dict) else [])
    out = []
    for ln in (listing.get("agidock_index_tsv") or "").splitlines():
        f = ln.split("\t")
        if len(f) < 11 or ln.startswith("#"):
            continue
        die, name, kind, state = f[0], f[1], f[2], f[10]
        if state != "ARCHIVED-BOTH" or kind not in ("core", "type", "design"):
            continue
        if name not in credited.get(die, set()) and name in planned.get(die, set()):      # only names of the die's CURRENT plan: retired masters / ring children are not a count gap
            out.append((die, name, kind, state, (f[11] if len(f) > 11 else "")[:100]))
    return out


def count_gap_section(listing_path=LISTING, cache_path=COUNT_CACHE):
    try:
        rows = count_gap_rows(json.load(open(listing_path)), json.load(open(cache_path)))
    except (OSError, ValueError) as e:
        return ["# COUNT-GAP not computed: %s" % type(e).__name__]
    out = ["# COUNT-GAP archived (AGIdock INDEX.tsv ARCHIVED-BOTH) but not credited by the count: %d" % len(rows), "\t".join(["die", "name", "kind", "state", "note"])]
    out += ["\t".join(r) for r in rows]
    return out


def load_src_refresh(path=SRC_REFRESH):
    if not os.path.isfile(path):
        return None
    loader = importlib.machinery.SourceFileLoader("ot_src_refresh_fh", path)
    spec = importlib.util.spec_from_loader("ot_src_refresh_fh", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def build(args, now=None):
    now = time.time() if now is None else now
    lines = read_tail(LOG) if LOG.exists() else []
    try:
        state = json.loads(STATE.read_text())
    except (OSError, ValueError):
        state = {}
    refused, open_now = state_info(state)
    rows = render(hourly(lines, args.hours, now), refused, open_now, now)
    if not args.no_skew:
        try:
            cfg = json.loads(CFG.read_text())
            cm = None if args.no_compare else load_src_refresh()
            rows += [""] + skew_section(cfg, compare_mod=cm, now=now)
        except Exception as e:
            rows += ["", f"# SKEW not computed: {type(e).__name__}: {str(e)[:200]}"]
    if not args.no_skew:
        try:
            rows += [""] + count_gap_section()
        except Exception as e:
            rows += ["", f"# COUNT-GAP not computed: {type(e).__name__}"]
        try:
            rows += [""] + noprog_drift_section()
        except Exception as e:
            rows += ["", f"# NOPROG-DRIFT not computed: {type(e).__name__}"]
        try:
            rows += [""] + ot_run_drift_section()
        except Exception as e:
            rows += ["", f"# OT-RUN-DRIFT not computed: {type(e).__name__}"]
        try:
            rows += [""] + hostname_section()
        except Exception as e:
            rows += ["", f"# HOSTNAME-RESOLUTION not computed: {type(e).__name__}"]
    return "\n".join(rows) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hours", type=int, default=48)
    ap.add_argument("--no-skew", action="store_true")
    ap.add_argument("--no-compare", action="store_true")
    ap.add_argument("--no-commit", action="store_true")
    ap.add_argument("--out", default="")
    a = ap.parse_args(argv)
    text = build(a)
    out = Path(a.out) if a.out else COORD / OUT_REL
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    tmp.write_text(text)
    os.replace(tmp, out)                            # copy+mv: a reader never sees half a file
    if not a.no_commit and not a.out:
        subprocess.run(["bash", str(COORD / "bin/coord-commit.sh"), "FLOW-HEALTH hourly report", OUT_REL], cwd=str(COORD), timeout=900)
    print(text[:3000])
    return 0


FLOW_HEALTH_CRON = ("7 * * * * cd / && /usr/bin/flock -n /tmp/flow-health.lock /usr/bin/timeout 1500 /usr/bin/python3 -I "
                    "/srv/opentallas-scratch2/claude/rt/current/tools/autopilot/flow_health.py >> $HOME/.local/state/flow-health.log 2>&1")

if __name__ == "__main__":
    sys.exit(main())
