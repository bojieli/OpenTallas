#!/usr/bin/env python3
"""OpenTallas scripted closure loop (owner-approved 2026-10-06): block closure that keeps running with no AI in the loop.

A job is ONE JSON file (tools/closure_loop/jobs/<name>.json on origin/main, or the drop dir
/tmp/claude-review-20261003/closure_jobs/<name>.json, or this checkout's jobs/ dir; see README.md).  The daemon
(systemd --user unit closure-loop.service on localhost; it only dispatches over ssh) takes each job through

    sync source (git archive of the pinned commit -> <host base>/<name>/src)
    -> bench stages (each: expect pass | fail; an exact bench must PASS, a negative control must FAIL)
    -> calibrate (default ON): synth -> floorplan -> place -> CTS only, measure the real SS/FF clock insertion at
       the boundary registers (ck_insertion.py), regenerate the IO SDC from it (job's sdc_cmd, env CK_*), so the
       route's IO budgets match the block's own tree (no 10^5 hold buffers from a guessed insertion)
    -> route -> signoff -> VERDICT (SS >= +15 ps, FF >= +15 ps at 833.333, DRC 0, extra checks)
    -> collect -> export -> commit the record + view on the job's branch (explicit-path staging),
       trial-merge the branch into its merge target in a scratch worktree, push, ledger line
    or -> failure summary (worst 10 path classes per failing check) -> NEEDS_RTL
    or (stage crash) -> retry ONCE (another host if resource-related) -> NEEDS_HUMAN

Rules it enforces: load cap (load1 + pending + threads <= host cap = 1.2 x cores; MemAvailable >= peak + 32 GB),
NVMe run roots (hosts.json), one route per (block, source commit), it never kills a process it did not start
(cancel only stops its own stage process group and containers mounting its own run dir), every run registered in
/home/ubuntu/opentallas-monitor/experiment.py (owner Claude:closure-loop).

    closure_loop.py daemon [--interval 60]     # the service
    closure_loop.py tick                       # one pass (debug)
    closure_loop.py status                     # table of jobs
    closure_loop.py validate <job.json>        # check a spec before dropping it
    closure_loop.py retry <name>               # human: re-queue a NEEDS_HUMAN job from its failed stage
    closure_loop.py cancel <name>              # stop this loop's own stage for <name>; status CANCELLED
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import glob
import json
import os
import re
import shlex
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
import subprocess
import tempfile
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = Path(os.environ.get("CL_REPO", "/home/ubuntu/OpenTallas"))          # git object store for archive/commit/merge
STATE = Path(os.environ.get("CL_STATE", str(Path.home() / ".local/state/closure_loop")))
REVIEW = Path(os.environ.get("CL_REVIEW", "/tmp/claude-review-20261003"))
DROP = REVIEW / "closure_jobs"
LEDGER = REVIEW / "CLOSURE_LOOP_LEDGER.md"
STATUS_MD = REVIEW / "CLOSURE_LOOP_STATUS.md"
EXPERIMENT = Path("/home/ubuntu/opentallas-monitor/experiment.py")
OWNER = "Claude:closure-loop"
SS_MIN, FF_MIN = 15.0, 15.0           # OWNER 2026-10-06 18:15: closed at SS >= +15 / FF >= +15 at 833.333
RAM_HEADROOM_GB = 32
PENDING_WINDOW_S = 180                # load1 lags a launch: count own launches of the last 5 min as load
TERMINAL = {"CLOSED", "NEEDS_RTL", "NEEDS_HUMAN", "NEEDS_BUDGET", "REFUSED", "CANCELLED", "INVALID"}
RESOURCE_RE = re.compile(r"Cannot allocate memory|[Oo]ut of memory|\bOOM\b|oom-kill|No space left|ENOSPC|std::bad_alloc|"
                         r"Resource temporarily unavailable|Killed\b|signal 9|exit code 137|MemoryError|"
                         r"admission (?:timed out|refused)", re.M)
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")
DEFAULT_SRC_PATHS = ["tools", "rtl", "physical", "Makefile"]
FLEET_LOCK = threading.RLock()     # host choice / capacity check / launch are atomic across job threads
GIT_LOCK = threading.Lock()        # fetches into the shared object store
PUBLISH_LOCK = threading.Lock()    # one commit/merge at a time
WORKERS = 16
STAGE_DEFAULTS = {"bench": (4, 16), "route": None, "signoff": (4, 16), "collect": (2, 8), "export": (2, 8),
                  "summary": (2, 16)}


# ----------------------------------------------------------------------------------------------------- utilities
def now_iso():
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def log(msg):
    print(f"{now_iso()} {msg}", flush=True)


def sh(cmd, timeout=600, check=False, input=None, cwd=None):
    r = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True, timeout=timeout,
                       input=input, cwd=cwd)
    if check and r.returncode:
        raise RuntimeError(f"command failed rc={r.returncode}: {cmd if isinstance(cmd, str) else ' '.join(cmd)}\n"
                           f"{r.stdout[-1500:]}\n{r.stderr[-1500:]}")
    return r


def ssh(host, script, timeout=120, check=False, input=None):
    """Run a shell script on host.  Without input the script goes in on stdin (bash -s); with input, the script is
    the remote command line and input is piped to it."""
    base = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "-o", "ServerAliveInterval=30", host]
    if input is None:
        return sh(base + ["bash -s"], timeout=timeout, check=check, input=script)
    return sh(base + [script], timeout=timeout, check=check, input=input)


def gfetch(*refs, timeout=600):
    with GIT_LOCK:
        return sh(["git", "-C", str(REPO), "fetch", "-q", "origin", *refs], timeout=timeout)


def git(*args, timeout=900, check=True, cwd=None):
    return sh(["git", "-C", str(cwd or REPO), *args], timeout=timeout, check=check)


def append_locked(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(text)


def hosts_table():
    return json.loads((HERE / "hosts.json").read_text())["hosts"]


def host_cfg(name):
    return next(h for h in hosts_table() if h["name"] == name)


# ------------------------------------------------------------------------------------------------- job specs
def validate(spec: dict) -> list[str]:
    e = []
    for k in ("name", "block", "owner", "source", "stages"):
        if k not in spec:
            e.append(f"missing '{k}'")
    if e:
        return e
    if not NAME_RE.match(spec["name"]):
        e.append("name must match " + NAME_RE.pattern)
    src = spec["source"]
    if not isinstance(src, dict) or not src.get("branch") or not re.match(r"^[0-9a-f]{7,40}$", str(src.get("commit", ""))):
        e.append("source needs branch and a hex commit")
    st = spec["stages"]
    if not isinstance(st, dict) or not st.get("route", {}).get("cmd"):
        e.append("stages.route.cmd is required")
    for b in st.get("bench", []) if isinstance(st, dict) else []:
        if b.get("expect") not in ("pass", "fail") or not b.get("cmd") or not b.get("name"):
            e.append(f"bench entry needs name, cmd and expect pass|fail: {b}")
    benches = st.get("bench", []) if isinstance(st, dict) else []
    if not spec.get("no_bench_reason") and not (any(b.get("expect") == "pass" for b in benches)
                                                and any(b.get("expect") == "fail" for b in benches)):
        e.append("need >= 1 bench expect=pass and >= 1 expect=fail (or no_bench_reason: e.g. pure re-route of a "
                 "benched commit, naming the bench record)")
    cal = st.get("calibrate") if isinstance(st, dict) else None
    if cal is None or (cal.get("enabled", True) and not (cal.get("cmd") and cal.get("base"))):
        if not (cal and cal.get("enabled") is False and cal.get("reason")):
            e.append("stages.calibrate is on by default: give cmd (the CTS-only run; route_view.sh jobs: the route "
                     "command with ${CL_LABEL_SUFFIX} on the label and $CL_STOP_AFTER appended) + base (glob of its "
                     "ORFS results/.../base) [+ clock, sdc_cmd], or {\"enabled\": false, \"reason\": \"...\"}")
    for sk in ("calibrate", "route", "signoff"):
        cmd = (st.get(sk) or {}).get("cmd", "") if isinstance(st, dict) else ""
        dummy = {k: "x" for k in ("RUN", "SRC", "CL", "HOST", "BLOCK", "COMMIT", "THREADS", "RAW_NAME")}
        dummy.update(NAME=label(spec["name"]), LABEL=label(spec["name"]))
        for k, val in dummy.items():
            cmd = cmd.replace("{" + k + "}", val)
        cmd = cmd.replace("${CL_LABEL_SUFFIX}", "_cal").replace("$CL_LABEL_SUFFIX", "_cal")
        for m in re.finditer(r"(?:route_view\.sh|stn_route\.sh\s+\S+\s+\S+)\s+(\S+)|--nickname-tag[ =](\S+)", cmd):
            lab = (m.group(1) or m.group(2) or "").strip("'\"")
            if lab and not re.fullmatch(r"[A-Za-z0-9_]*(\$\{?[A-Za-z_][A-Za-z0-9_]*\}?[A-Za-z0-9_]*)*", lab):
                e.append(f"stages.{sk}: route label '{lab}' is not [A-Za-z0-9_]+ (run_abi3_physical --nickname-tag "
                         f"rejects it): use {{LABEL}}${{CL_LABEL_SUFFIX}}")
    snippets = []
    if isinstance(st, dict):
        for b in st.get("bench", []):
            snippets += [(f"bench {b.get('name')}", b.get("cmd")), (f"bench {b.get('name')} ok", b.get("ok"))]
        for k in ("calibrate", "route", "signoff", "collect", "export"):
            x = st.get(k) or {}
            snippets += [(k, x.get("cmd")), (f"{k} ok", x.get("ok")), (f"{k} sdc_cmd", x.get("sdc_cmd"))]
    vv = spec.get("verdict", {})
    snippets += [("verdict metrics_cmd", vv.get("metrics_cmd"))] + [(f"check {c.get('name')}", c.get("cmd")) for c in vv.get("checks", [])]
    for where, cmd in snippets:
        if not cmd:
            continue
        r = sh(["bash", "-n"], input=cmd, timeout=30)
        if r.returncode:
            e.append(f"{where}: bash -n syntax error: {(r.stderr or r.stdout).strip()[-300:]}")
    v = spec.get("verdict", {})
    if not v.get("corner_sta") and not v.get("metrics_cmd"):
        e.append("verdict.corner_sta (glob of a tools/w18/corner_sta.py JSON) or verdict.metrics_cmd is required")
    if not v.get("drc_metrics") and not v.get("metrics_cmd") and v.get("drc") != "skip":
        e.append("verdict.drc_metrics (glob of ORFS 5_2_route.json) is required")
    bud = spec.get("budget")
    if bud is None and has_sheet(spec.get("block", "")):
        e.append(f"block {spec['block']} has a budget sheet ({BUDGET_SHEETS}/{spec['block']}.json on origin/main): budget is "
                 f"the default -- add \"budget\": {{\"master\": \"{spec['block']}\"}} and take the IO SDCs from "
                 f"$BUDGET_SDC (route) / $BUDGET_SDC_SIGNOFF / $BUDGET_SDC_FF, or opt out with "
                 f"\"budget\": {{\"enabled\": false, \"reason\": \"...\"}}")
    if isinstance(bud, dict) and bud.get("enabled") is False:
        if not bud.get("reason"):
            e.append("budget.enabled false needs a reason")
        bud = None
    elif isinstance(bud, dict) and isinstance(st, dict) and "BUDGET_SDC" not in json.dumps(st):
        e.append("budget is set but no stage command uses $BUDGET_SDC / $BUDGET_SDC_SIGNOFF / $BUDGET_SDC_FF")
    if bud is not None:
        if not isinstance(bud, dict) or not bud.get("master"):
            e.append("budget needs {master[, clock, domain_clock[], on_deviation flag|continue, sheets_ref]}")
        elif bud.get("on_deviation", "flag") not in ("flag", "continue"):
            e.append("budget.on_deviation must be flag or continue")
        else:
            try:
                budget_files(bud, check_only=True)
            except Exception as ex:  # noqa: BLE001
                e.append(f"budget: {str(ex)[:300]}")
    for h in spec.get("hosts", []):
        if h not in [x["name"] for x in hosts_table()]:
            e.append(f"unknown host {h}")
    for r in spec.get("record", []):
        if not r.get("from") or not r.get("to") or r["to"].startswith("/") or ".." in r["to"]:
            e.append(f"record entry needs from (remote, may use {{RUN}}) and a repo-relative to: {r}")
    if spec.get("merge_target") is not None and not isinstance(spec.get("merge_target"), str):
        e.append("merge_target must be a branch name or null")
    for k in ("threads", "peak_ram_gb"):
        if not isinstance(spec.get(k, 1), (int, float)) or spec.get(k, 1) <= 0:
            e.append(f"{k} must be a positive number")
    return e


def stage_list(spec):
    st = spec["stages"]
    out = []
    for b in st.get("bench", []):
        t, r = STAGE_DEFAULTS["bench"]
        out.append(dict(key="bench_" + re.sub(r"[^A-Za-z0-9_-]", "_", b["name"]), kind="bench", cmd=b["cmd"],
                        expect=b["expect"], ok=b.get("ok"), fail_regex=b.get("fail_regex"), pass_regex=b.get("pass_regex"),
                        threads=b.get("threads", t), ram=b.get("peak_ram_gb", r)))
    cal = st.get("calibrate") or {}
    if cal.get("enabled", True) and cal.get("cmd"):
        base = cal["base"]
        tail = (f"\nB=$(ls -d {base} 2>/dev/null | tail -1); [ -n \"$B\" ] || {{ echo 'calibrate: no ORFS base {base}'; exit 3; }}"
                f"\npython3 {{CL}}/ck_insertion.py --base \"$B\" --clock {cal.get('clock', 'ck')} --output {{CL}}/calib.json"
                f" > {{CL}}/calib.env || exit 4\ncat {{CL}}/calib.env\nset -a; . {{CL}}/calib.env; set +a")
        if cal.get("sdc_cmd"):
            tail += "\n" + cal["sdc_cmd"]
        out.append(dict(key="calibrate", kind="calibrate", cmd=cal["cmd"] + tail, ok=cal.get("ok"),
                        threads=cal.get("threads", spec.get("threads", 16)), ram=cal.get("peak_ram_gb", spec.get("peak_ram_gb", 32)),
                        logs=cal.get("logs", [])))
    for k in ("route", "signoff"):
        if st.get(k, {}).get("cmd"):
            t, r = STAGE_DEFAULTS[k] or (spec.get("threads", 16), spec.get("peak_ram_gb", 32))
            out.append(dict(key=k, kind=k, cmd=st[k]["cmd"], ok=st[k].get("ok"),
                            threads=st[k].get("threads", t), ram=st[k].get("peak_ram_gb", r),
                            logs=st[k].get("logs", [])))
    out.append(dict(key="verdict", kind="verdict"))
    for k in ("collect", "export"):
        if st.get(k, {}).get("cmd"):
            t, r = STAGE_DEFAULTS[k]
            out.append(dict(key=k, kind=k, cmd=st[k]["cmd"], ok=st[k].get("ok"),
                            threads=st[k].get("threads", t), ram=st[k].get("peak_ram_gb", r), logs=st[k].get("logs", [])))
    out.append(dict(key="commit", kind="commit"))
    return out


def load_sources():
    """(origin, spec) for every job file the loop can see."""
    found = []
    for p in sorted(glob.glob(str(DROP / "*.json"))) + sorted(glob.glob(str(HERE / "jobs" / "*.json"))):
        if p.endswith(".example.json"):
            continue
        try:
            found.append((p, json.loads(Path(p).read_text())))
        except Exception as ex:  # noqa: BLE001
            found.append((p, {"_parse_error": str(ex)}))
    r = sh(["git", "-C", str(REPO), "ls-tree", "--name-only", "origin/main", "tools/closure_loop/jobs/"], timeout=60)
    for p in r.stdout.split():
        if not p.endswith(".json") or p.endswith(".example.json"):
            continue
        s = sh(["git", "-C", str(REPO), "show", f"origin/main:{p}"], timeout=60)
        try:
            found.append((f"origin/main:{p}", json.loads(s.stdout)))
        except Exception as ex:  # noqa: BLE001
            found.append((f"origin/main:{p}", {"_parse_error": str(ex)}))
    return found


# ------------------------------------------------------------------------------------------------ job state
def jpath(name):
    return STATE / "jobs" / f"{name}.json"


def load_job(name):
    return json.loads(jpath(name).read_text())


def save_job(j):
    j["updated"] = now_iso()
    p = jpath(j["name"])
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(j, indent=1) + "\n")
    os.replace(tmp, p)


def all_jobs():
    return [json.loads(p.read_text()) for p in sorted((STATE / "jobs").glob("*.json"))]


def keys_path():
    return STATE / "route_keys.json"


def route_keys():
    return json.loads(keys_path().read_text()) if keys_path().exists() else {}


def event(j, msg):
    j.setdefault("events", []).append(f"{now_iso()} {msg}")
    j["events"] = j["events"][-60:]
    log(f"[{j['name']}] {msg}")


def experiment(j, status, register=False):
    if not EXPERIMENT.exists() or os.environ.get("CL_NO_EXPERIMENT"):
        return
    rid = f"closure-loop:{j['name']}"
    host = host_cfg(j["host"])["label"] if j.get("host") else "pending"
    args = ["--name", rid, "--host", host, "--owner", OWNER, "--worktree", f"{j.get('host', '-')}:{j.get('run', '-')}",
            "--purpose", f"{j['spec']['block']} @ {j['spec']['source']['commit'][:9]} bench/route/signoff/merge "
                         f"(job owner {j['spec']['owner']})", "--status", status]
    r = sh([sys.executable, str(EXPERIMENT), "update", *args], timeout=60)
    if r.returncode and "Unknown experiment" in (r.stderr + r.stdout):
        sh([sys.executable, str(EXPERIMENT), "register", *args], timeout=60)


def ingest():
    try:
        gfetch("main", timeout=300)
    except subprocess.TimeoutExpired:
        pass
    keys = route_keys()
    for origin, spec in load_sources():
        name = spec.get("name") or Path(origin.split(":")[-1]).stem
        if spec.get("enabled") is False:
            continue
        p = jpath(name) if NAME_RE.match(str(name)) else None
        if p is not None and p.exists():
            j = load_job(name)
            frozen = {k: v for k, v in j["spec"].items()}
            if json.dumps(frozen, sort_keys=True) != json.dumps(spec, sort_keys=True) and not j.get("spec_change_noted"):
                j["spec_change_noted"] = True
                event(j, f"NOTE spec in {origin} changed after ingest: ignored (frozen at first sight; a new source "
                         f"commit needs a new job name)")
                save_job(j)
            continue
        if "_parse_error" in spec:
            bad = STATE / "invalid" / (re.sub(r"[^A-Za-z0-9._-]", "_", origin) + ".txt")
            if not bad.exists():
                bad.parent.mkdir(parents=True, exist_ok=True)
                bad.write_text(spec["_parse_error"])
                log(f"INVALID job file {origin}: {spec['_parse_error']}")
            continue
        errs = validate(spec)
        j = dict(name=name, spec=spec, origin=origin, created=now_iso(), status="QUEUED", stage_idx=0, attempt=1,
                 retries_used=0, benches={}, hosts_tried=[], events=[])
        if errs:
            j["status"] = "INVALID"
            j["reason"] = "; ".join(errs)
            event(j, f"INVALID: {j['reason']}")
            ledger(j, f"INVALID spec ({origin}): {j['reason']}")
        else:
            key = f"{spec['block']}@{spec['source']['commit'][:12]}"
            if key in keys and keys[key] != name:
                j["status"] = "REFUSED"
                j["reason"] = f"one route per source commit: {key} already routed by job {keys[key]}"
                event(j, j["reason"])
                ledger(j, f"REFUSED: {j['reason']}")
            else:
                event(j, f"ingested from {origin}")
        save_job(j)


# --------------------------------------------------------------------------------------------- host capacity
class Fleet:
    def __init__(self):
        self.pending = {}      # host -> [(t, threads, ram)]
        self.probe_cache = {}
        self.tool_cache = {}

    def probe(self, host):
        c = self.probe_cache.get(host)
        if c and time.time() - c[0] < 45:
            return c[1]
        cfg = host_cfg(host)
        r = ssh(host, f"""cat /proc/loadavg; awk '/MemAvailable/{{print int($2/1048576)}}' /proc/meminfo
mkdir -p {cfg['base']} && df -P -BG {cfg['base']} | awk 'NR==2{{gsub("G","",$4);print $4}}'""", timeout=40)
        if r.returncode:
            info = None
        else:
            v = r.stdout.split()
            info = dict(load1=float(v[0]), mem_gb=int(v[5]), disk_gb=int(v[6]))
        self.probe_cache[host] = (time.time(), info)
        return info

    def own_pending(self, host):
        t0 = time.time() - PENDING_WINDOW_S
        self.pending[host] = [p for p in self.pending.get(host, []) if p[0] >= t0]
        return sum(p[1] for p in self.pending[host]), sum(p[2] for p in self.pending[host])

    def fits(self, host, threads, ram):
        with FLEET_LOCK:
            return self._fits(host, threads, ram)

    def _fits(self, host, threads, ram):
        cfg = host_cfg(host)
        if threads > cfg["max_job_threads"] or ram > cfg["max_job_ram_gb"]:
            return False, f"job {threads} thr / {ram} GB exceeds {cfg['label']} per-job limit"
        info = self.probe(host)
        if info is None:
            return False, f"{cfg['label']} unreachable"
        pt, pr = self.own_pending(host)
        if info["load1"] + pt + threads > cfg["cap"]:
            return False, f"{cfg['label']} load {info['load1']:.0f}+{pt}+{threads} > cap {cfg['cap']}"
        if info["mem_gb"] - pr < ram + RAM_HEADROOM_GB:
            return False, f"{cfg['label']} MemAvailable {info['mem_gb']}-{pr} GB < {ram}+{RAM_HEADROOM_GB}"
        if info["disk_gb"] < cfg["min_free_disk_gb"]:
            return False, f"{cfg['label']} run root has {info['disk_gb']} GB free < {cfg['min_free_disk_gb']}"
        return True, "ok"

    def launched(self, host, threads, ram):
        with FLEET_LOCK:
            self._launched(host, threads, ram)

    def _launched(self, host, threads, ram):
        self.pending.setdefault(host, []).append((time.time(), threads, ram))
        self.probe_cache.pop(host, None)

    def choose(self, spec, exclude=()):
        with FLEET_LOCK:
            return self._choose(spec, exclude)

    def toolchain(self, host):
        """ORFS image digests + bench tool versions of a host (cached 1 h)."""
        c = self.tool_cache.get(host)
        if c and time.time() - c[0] < 3600:
            return c[1]
        r = ssh(host, TOOLPROBE, timeout=60)
        info = dict(l.split("=", 1) for l in r.stdout.splitlines() if "=" in l) if r.returncode == 0 else None
        self.tool_cache[host] = (time.time(), info)
        return info

    def compatible(self, host, spec):
        """the host's toolchain matches the reference host's for every tool the job's commands use"""
        ref, mine = self.toolchain(TOOL_REF_HOST), self.toolchain(host)
        if not ref or not mine:
            return False
        return all(mine.get(k) == ref.get(k) for k in job_tools(spec))

    def _choose(self, spec, exclude=()):
        threads, ram = spec.get("threads", 16), spec.get("peak_ram_gb", 32)
        allh = [h["name"] for h in hosts_table()]
        order = list(spec.get("hosts") or allh)
        if ram <= SMALL_JOB_GB:      # small jobs may run on any host with the same toolchain (coordinator 2026-10-06)
            order += [h for h in allh if h not in order]
        order = [h for h in order if h not in exclude and self.compatible(h, spec)]

        def frac(h):
            info = self.probe(h)
            return 9e9 if info is None else (info["load1"] + self.own_pending(h)[0]) / host_cfg(h)["cap"]
        order.sort(key=frac)         # least loaded host first
        why = []
        for h in order:
            ok, msg = self.fits(h, threads, ram)
            if ok:
                return h, None
            why.append(msg)
        return None, "; ".join(why)


TOOL_REF_HOST = "ot-epyc3"
SMALL_JOB_GB = 40
TOOLPROBE = r"""
echo img_latest=$(docker image inspect openroad/orfs:latest --format '{{.Id}}' 2>/dev/null)
echo img_asap7lock=$(docker image inspect openroad/orfs:asap7lock --format '{{.Id}}' 2>/dev/null)
echo iverilog=$(iverilog -V 2>/dev/null | head -1)
echo verilator=$(verilator --version 2>/dev/null | head -1)
echo yosys=$(yosys -V 2>/dev/null | head -1)
"""


def job_tools(spec):
    t = json.dumps(spec.get("stages", {})) + json.dumps(spec.get("verdict", {}))
    need = {"img_latest"}
    for key, rx in (("img_asap7lock", r"asap7lock"), ("iverilog", r"\b(iverilog|vvp)\b"), ("verilator", r"\bverilator\b"),
                    ("yosys", r"\byosys\b")):
        if re.search(rx, t):
            need.add(key)
    return need


# ------------------------------------------------------------------------------------------------ remote ops
RUNNER = r"""#!/bin/bash
# closure-loop stage runner: <stage tag>.  pid/start/log/rc files next to this script.
st=$1; d=$(cd "$(dirname "$0")" && pwd)
echo $$ > $d/$st.pid; date +%s > $d/$st.start
cd "$(cat $d/SRC_DIR)"
bash $d/$st.sh > $d/$st.log 2>&1
rc=$?
echo $rc > $d/$st.rc.tmp && mv $d/$st.rc.tmp $d/$st.rc
"""


def label(name):
    """Route label of a job: run_abi3_physical --nickname-tag (and ORFS design nicknames) accept [A-Za-z0-9_]+ only, so
    {NAME} and {LABEL} in commands both expand to the job name with every other character as '_' ({RAW_NAME} = raw)."""
    return re.sub(r"[^A-Za-z0-9_]", "_", name)


def subst(text, j):
    m = dict(RUN=j["run"], SRC=f"{j['run']}/src", CL=f"{j['run']}/cl", HOST=j["host"], NAME=label(j["name"]),
             LABEL=label(j["name"]), RAW_NAME=j["name"],
             BLOCK=j["spec"]["block"], COMMIT=j["spec"]["source"]["commit"], THREADS=str(j["spec"].get("threads", 16)))
    for k, v in m.items():
        text = text.replace("{" + k + "}", v)
    return text


# ------------------------------------------------------------------------------------------------ budget sheets
BUDGET_SHEETS = "results/rtl/budgets_20261006/sheets"


def budget_files(bud, check_only=False):
    """budget SDCs of the job's master from its sheet at sheets_ref (default origin/main; tools/budgets/make_block_sdc.py
    of the same ref): {name: text} + the sheet.  The SDC is generated HERE (localhost, from the published sheet), so
    every job uses the same sheet whatever its own branch carries."""
    ref = bud.get("sheets_ref", "origin/main")
    with tempfile.TemporaryDirectory() as td:
        arch = sh(["bash", "-c", f"git -C {REPO} archive {ref} tools/budgets {BUDGET_SHEETS}/{bud['master']}.json | tar -x -C {td}"],
                  timeout=300)
        sheet = Path(td) / BUDGET_SHEETS / f"{bud['master']}.json"
        if arch.returncode or not sheet.exists():
            raise ValueError(f"no budget sheet {bud['master']} at {ref} ({arch.stderr[-300:]})")
        if check_only:
            return {}
        tool = Path(td) / "tools/budgets/make_block_sdc.py"
        clk = bud.get("clock", "core_clk")
        dc = sum((["--domain-clock", x] for x in bud.get("domain_clock", [])), [])
        out = {}
        for name, args in (("budget_route.sdc", ["sdc", "--route-mode", "route"] + dc),
                           ("budget_signoff.sdc", ["sdc", "--route-mode", "signoff"] + dc), ("budget_ff.sdc", ["ff"])):
            r = sh(["python3", str(tool), args[0], bud["master"], "--sheets", str(sheet.parent), "--clock", clk] + args[1:],
                   timeout=120)
            if r.returncode:
                raise ValueError(f"make_block_sdc {name}: {r.stderr[-300:]}")
            out[name] = r.stdout
        out["budget_sheet.json"] = sheet.read_text()
        out["_ref"] = git("rev-parse", ref).stdout.strip()
        return out


def active_budget(spec):
    b = spec.get("budget")
    return b if isinstance(b, dict) and b.get("enabled", True) is not False and b.get("master") else None


def has_sheet(block):
    if not block:
        return False
    return sh(["git", "-C", str(REPO), "cat-file", "-e", f"origin/main:{BUDGET_SHEETS}/{block}.json"], timeout=60).returncode == 0


def budget_check(j):
    """calibrate CHECK against the sheet (never a re-calibration): None if within tolerance, else the reason"""
    bud = active_budget(j["spec"])
    if not bud or not j.get("budget") or not j.get("calibration"):
        return None
    ins = j["budget"]["insertion"]
    m = float(j["calibration"]["env"]["CK_SS_MEAN"])
    tol = ins["tolerance_ps"]
    why = []
    if abs(m - ins["ss"]) > tol:
        why.append(f"measured SS insertion {m:g} vs sheet {ins['ss']:g} ({ins['grade']}): {m - ins['ss']:+.0f} > {tol:g} ps")
    if m - ins["target_ss"] > tol:
        why.append(f"exceeds the block insertion TARGET {ins['target_ss']:g} by {m - ins['target_ss']:+.0f} ps")
    j["budget"]["check"] = dict(measured_ss=m, ok=not why, reasons=why)
    return "; ".join(why) or None


def sync_source(j):
    spec, host = j["spec"], j["host"]
    src = spec["source"]
    gfetch(src["branch"], timeout=600)
    full = git("rev-parse", "--verify", f"{src['commit']}^{{commit}}").stdout.strip()
    anc = sh(["git", "-C", str(REPO), "merge-base", "--is-ancestor", full, f"origin/{src['branch']}"], timeout=120)
    if anc.returncode:
        raise ValueError(f"source commit {full[:12]} is not on origin/{src['branch']}")
    j["commit_full"] = full
    paths = list(src.get("paths", DEFAULT_SRC_PATHS)) + list(src.get("extra_paths", []))
    run = j["run"]
    ssh(host, f"set -e; mkdir -p {run}/src {run}/cl; test ! -e {run}/src/SOURCE_COMMIT || "
              f"grep -q {full} {run}/src/SOURCE_COMMIT", timeout=60, check=True)
    arch = subprocess.Popen(["git", "-C", str(REPO), "archive", "--format=tar", full, "--", *paths],
                            stdout=subprocess.PIPE)
    gz = subprocess.Popen(["gzip", "-1"], stdin=arch.stdout, stdout=subprocess.PIPE)
    arch.stdout.close()
    put = subprocess.run(["ssh", "-o", "BatchMode=yes", host, f"tar -xzf - -C {run}/src"], stdin=gz.stdout,
                         capture_output=True, text=True, timeout=1800)
    gz.wait(); arch.wait()
    if put.returncode or arch.returncode:
        raise RuntimeError(f"source sync failed: {put.stderr[-800:]}")
    for helper in ("path_summary.py", "ck_insertion.py"):
        ssh(host, f"cat > {run}/cl/{helper}", input=(HERE / helper).read_text(), timeout=60, check=True)
    ssh(host, f"echo {full} > {run}/src/SOURCE_COMMIT && echo {run}/src > {run}/cl/SRC_DIR", timeout=60, check=True)
    ssh(host, f"cat > {run}/cl/run.sh && chmod +x {run}/cl/run.sh", input=RUNNER, timeout=60, check=True)
    ssh(host, f"cat > {run}/cl/job.json", input=json.dumps(spec, indent=1), timeout=60, check=True)
    if active_budget(spec):
        files = budget_files(spec["budget"])
        for fn, text in files.items():
            if not fn.startswith("_"):
                ssh(host, f"cat > {run}/cl/{fn}", input=text, timeout=60, check=True)
        sheet = json.loads(files["budget_sheet.json"])
        j["budget"] = dict(master=spec["budget"]["master"], sheets_ref=files["_ref"],
                           insertion=sheet["clock"]["internal_insertion"],
                           entry_target_ss=sheet["clock"].get("entry_target_ss_ps"))


def tag(st, j):
    return f"{st['key']}.a{j['attempt']}"


def launch_stage(j, st, cmd):
    t = tag(st, j)
    env = "".join(f"export {k}={shlex.quote(v)}\n" for k, v in dict(
        RUN=j["run"], SRC=f"{j['run']}/src", CL=f"{j['run']}/cl", HOST=j["host"], NAME=label(j["name"]),
        LABEL=label(j["name"]), RAW_NAME=j["name"],
        BLOCK=j["spec"]["block"], COMMIT=j["commit_full"], THREADS=str(st.get("threads", 4)),
        CL_PHASE=st["kind"], CL_LABEL_SUFFIX="_cal" if st["kind"] == "calibrate" else "",
        CL_STOP_AFTER="--pnr-stop-after cts" if st["kind"] == "calibrate" else "").items())
    if j.get("budget"):          # budget SDCs (tools/budgets/make_block_sdc.py from the published sheet)
        env += "".join(f"export {k}={j['run']}/cl/{v}\n" for k, v in (
            ("BUDGET_SDC", "budget_route.sdc"), ("BUDGET_SDC_SIGNOFF", "budget_signoff.sdc"), ("BUDGET_SDC_FF", "budget_ff.sdc"),
            ("BUDGET_SHEET", "budget_sheet.json")))
        env += f"export BUDGET_LINT_SS={j['budget']['insertion']['ss']}\nexport BUDGET_LINT_FF={j['budget']['insertion']['ff']}\n"
    # a job without calibrate still gets a {CL}/calib.json (records copy it)
    if st["kind"] != "calibrate":
        env += f"[ -f {j['run']}/cl/calib.json ] || echo '{{\"calibrate\": \"disabled\"}}' > {j['run']}/cl/calib.json\n"
    # every stage after calibrate sees the measured insertion (CK_SS_MEAN/MIN/MAX, CK_FF_*; *_ALL_* = all registers)
    env += f"[ -f {j['run']}/cl/calib.env ] && {{ set -a; . {j['run']}/cl/calib.env; set +a; }}\n" \
        if st["kind"] != "calibrate" else ""
    body = f"#!/bin/bash\n# closure-loop {j['name']} stage {st['key']} attempt {j['attempt']}\nset -o pipefail\n{env}{subst(cmd, j)}\n"
    run = j["run"]
    ssh(j["host"], f"cat > {run}/cl/{t}.sh && rm -f {run}/cl/{t}.rc", input=body, timeout=60, check=True)
    ssh(j["host"], f"nohup setsid bash {run}/cl/run.sh {t} > /dev/null 2>&1 < /dev/null & echo launched", timeout=60,
        check=True)
    j["stage_tag"] = t
    j["stage_started"] = now_iso()


def poll_stage(j):
    t, run = j["stage_tag"], j["run"]
    r = ssh(j["host"], f"""if [ -f {run}/cl/{t}.rc ]; then echo RC $(cat {run}/cl/{t}.rc)
elif [ -f {run}/cl/{t}.pid ] && kill -0 $(cat {run}/cl/{t}.pid) 2>/dev/null; then echo RUNNING
elif [ -f {run}/cl/{t}.pid ]; then echo LOST; else echo STARTING; fi""", timeout=40)
    if r.returncode:
        return "UNREACHABLE", None
    w = r.stdout.split()
    if not w:
        return "UNREACHABLE", None
    return (w[0], int(w[1])) if w[0] == "RC" else (w[0], None)


def remote_ok(j, cmd):
    if not cmd:
        return True, ""
    r = ssh(j["host"], f"cd {j['run']}/src && {subst(cmd, j)}", timeout=300)
    return r.returncode == 0, (r.stdout + r.stderr)[-400:]


def bench_outcome(j, st, rc, ok_extra=True):
    """pass: rc 0 (+ ok, + pass_regex); fail: rc != 0 (+ fail_regex).  Regexes are MULTILINE over the whole stage log
    (last 20000 lines), so ^FAIL matches any line."""
    full = ssh(j["host"], f"tail -n 20000 {j['run']}/cl/{j['stage_tag']}.log 2>/dev/null; true", timeout=120).stdout
    if st["expect"] == "pass":
        return rc == 0 and ok_extra and (not st.get("pass_regex") or re.search(st["pass_regex"], full, re.M) is not None)
    return rc != 0 and (not st.get("fail_regex") or re.search(st["fail_regex"], full, re.M) is not None)


def stage_tail(j, st, n=40):
    extra = " ".join(subst(x, j) for x in st.get("logs", []))
    r = ssh(j["host"], f"tail -n {n} {j['run']}/cl/{j['stage_tag']}.log 2>/dev/null; for f in {extra}; do "
                       f"[ -f \"$f\" ] && tail -n {n} \"$f\"; done; true", timeout=60)
    return r.stdout


def get_metrics(j):
    v = j["spec"].get("verdict", {})
    if v.get("metrics_cmd"):
        r = ssh(j["host"], f"cd {j['run']}/src && {subst(v['metrics_cmd'], j)}", timeout=600)
        last = [x for x in r.stdout.splitlines() if x.strip().startswith("{")]
        m = json.loads(last[-1]) if last else {}
        return dict(ss_ps=m.get("ss_ps"), ff_ps=m.get("ff_ps"), drc=m.get("drc"), orfs_dir=m.get("orfs_dir"),
                    raw=m)
    py = r"""
import glob,json,sys
cs=sorted(glob.glob(sys.argv[1])); dm=sorted(glob.glob(sys.argv[2])) if sys.argv[2] else []
o={'corner_sta':cs,'drc_metrics':dm}
if cs:
  d=json.load(open(cs[-1])); o['ss_ps']=d['setup_ss']['worst_slack_ps']; o['ff_ps']=d['hold_ff']['worst_slack_ps']
  o['orfs_dir']=d.get('orfs_dir'); o['errors']=d['setup_ss'].get('errors',[])+d['hold_ff'].get('errors',[])
  o['ss_tns_ps']=d['setup_ss'].get('tns_ps'); o['post_sdc']=list(d.get('post_sdc',{}))
if dm:
  m=json.load(open(dm[-1])); o['drc']=m.get('detailedroute__route__drc_errors')
print(json.dumps(o))
"""
    r = ssh(j["host"], f"cd {j['run']}/src && python3 - {shlex.quote(subst(v['corner_sta'], j))} "
                       f"{shlex.quote(subst(v.get('drc_metrics', ''), j))}", input=py, timeout=120)
    try:
        m = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        m = {"error": (r.stdout + r.stderr)[-400:]}
    if v.get("drc") == "skip":
        m["drc"] = 0
        m["drc_skipped"] = True
    return m


# ------------------------------------------------------------------------------------------------ git publish
def wt_add(path, ref, sparse):
    if path.exists():
        git("worktree", "remove", "--force", str(path), check=False)
        shutil.rmtree(path, ignore_errors=True)
    git("worktree", "prune", check=False)
    git("worktree", "add", "--no-checkout", "--detach", str(path), ref)
    git("sparse-checkout", "set", "--no-cone", *sparse, cwd=path)
    git("checkout", "-q", cwd=path, timeout=1800)


def wt_rm(path):
    git("worktree", "remove", "--force", str(path), check=False)
    shutil.rmtree(path, ignore_errors=True)


def publish(j, metrics):
    """Commit record + view on the job branch (explicit paths), trial-merge into merge_target, push."""
    spec = j["spec"]
    branch, target = spec["source"]["branch"], spec.get("merge_target")
    rec_dir = f"results/closure_loop/{j['name']}"
    tos = [r["to"] for r in spec.get("record", [])] + [rec_dir]
    sparse = ["/" + t.rstrip("/") for t in tos] + ["/tools/closure_loop/"]
    gdir = STATE / "git"
    gdir.mkdir(parents=True, exist_ok=True)
    cwt, mwt = gdir / f"{j['name']}-commit", gdir / f"{j['name']}-merge"
    dry = spec.get("dry_run_git", False)
    out = {}
    for attempt in range(4):
        gfetch(branch, timeout=600)
        wt_add(cwt, f"origin/{branch}", sparse)
        for r in spec.get("record", []):
            src = subst(r["from"], j)
            dst = cwt / r["to"]
            isdir = ssh(j["host"], f"test -d {shlex.quote(src)}", timeout=30).returncode == 0
            dst.parent.mkdir(parents=True, exist_ok=True)
            excl = sum((["--exclude", x] for x in r.get("exclude", [])), [])
            if isdir:
                dst.mkdir(parents=True, exist_ok=True)
                sh(["rsync", "-a", *excl, f"{j['host']}:{src.rstrip('/')}/", f"{dst}/"], timeout=1800, check=True)
            else:
                sh(["rsync", "-a", f"{j['host']}:{src}", str(dst)], timeout=1800, check=True)
        (cwt / rec_dir).mkdir(parents=True, exist_ok=True)
        verdict = dict(schema="opentallas.closure_loop.verdict.v1", job=j["name"], block=spec["block"],
                       owner=spec["owner"], source_branch=branch, source_commit=j["commit_full"],
                       host=j["host"], run_dir=j["run"], acceptance=dict(ss_min_ps=SS_MIN, ff_min_ps=FF_MIN, drc=0,
                       rule="OWNER 2026-10-06 18:15: closed at SS >= +15 / FF >= +15 at 833.333 (60/25 corners), "
                            "agreed die-clock IO budgets, DRC 0"),
                       metrics={k: metrics.get(k) for k in ("ss_ps", "ff_ps", "drc", "ss_tns_ps", "post_sdc", "corner_sta",
                                                            "drc_metrics", "drc_skipped")},
                       benches=j.get("benches", {}), no_bench_reason=spec.get("no_bench_reason"),
                       checks=j.get("checks", {}), calibration=j.get("calibration"), cycles_added=spec.get("cycles_added"), status="CLOSED",
                       closed_at=now_iso(), job_spec=spec)
        (cwt / rec_dir / "verdict.json").write_text(json.dumps(verdict, indent=1) + "\n")
        git("add", "--sparse", "--", *tos, cwd=cwt)
        staged = sh(["git", "-C", str(cwt), "diff", "--cached", "--name-only"], timeout=120).stdout.split()
        msg = (f"closure-loop: {spec['block']} CLOSED SS {metrics['ss_ps']:+.2f} / FF {metrics['ff_ps']:+.2f} ps DRC "
               f"{metrics['drc']} at 833.333 (source {j['commit_full'][:9]}, {host_cfg(j['host'])['label']} "
               f"{j['run']}); job {j['name']}, owner {spec['owner']}\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n")
        if staged:
            git("-c", "user.name=OpenTallas closure-loop", "-c", "user.email=boj@01.me", "commit", "-q", "-m", msg,
                cwd=cwt)
        out["branch_commit"] = git("rev-parse", "HEAD", cwd=cwt).stdout.strip()
        out["files"] = len(staged)
        if dry:
            break
        p = sh(["git", "-C", str(cwt), "push", "-q", "origin", f"HEAD:refs/heads/{branch}"], timeout=900)
        if p.returncode == 0:
            break
        log(f"[{j['name']}] push to {branch} rejected (attempt {attempt}); refetch: {p.stderr[-300:]}")
    else:
        raise RuntimeError(f"could not push the record to {branch}")
    wt_rm(cwt)
    if target:
        for attempt in range(4):
            gfetch(target, timeout=600)
            wt_add(mwt, f"origin/{target}", sparse)
            mref = out["branch_commit"] if dry else f"origin/{branch}"
            if not dry:
                gfetch(branch, timeout=600)
            m = sh(["git", "-C", str(mwt), "-c", "user.name=OpenTallas closure-loop", "-c", "user.email=boj@01.me",
                    "merge", "--no-ff", "--no-edit", "-m",
                    f"Merge {branch} into {target} (closure-loop {j['name']}: {spec['block']} CLOSED)\n\n"
                    f"Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>", mref], timeout=1800)
            if m.returncode:
                conf = sh(["git", "-C", str(mwt), "diff", "--name-only", "--diff-filter=U"], timeout=120).stdout.split()
                sh(["git", "-C", str(mwt), "merge", "--abort"], timeout=300)
                wt_rm(mwt)
                out["merge"] = f"CONFLICT ({len(conf)} files: {', '.join(conf[:6])})"
                return out
            out["merge_commit"] = git("rev-parse", "HEAD", cwd=mwt).stdout.strip()
            if dry:
                out["merge"] = f"dry-run merged locally {out['merge_commit'][:9]} (not pushed)"
                break
            p = sh(["git", "-C", str(mwt), "push", "-q", "origin", f"HEAD:refs/heads/{target}"], timeout=900)
            if p.returncode == 0:
                out["merge"] = f"merged into {target} {out['merge_commit'][:9]}"
                break
            log(f"[{j['name']}] push to {target} rejected (attempt {attempt}): {p.stderr[-300:]}")
            wt_rm(mwt)
        else:
            out["merge"] = f"PUSH-RACE: could not push the merge into {target}"
        wt_rm(mwt)
    else:
        out["merge"] = "no merge target"
    return out


# ------------------------------------------------------------------------------------------------ ledger/status
def ledger(j, text):
    spec = j["spec"]
    c = str(spec.get("source", {}).get("commit", "?"))[:9]
    where = f"{host_cfg(j['host'])['label']}:{j['run']}" if j.get("host") else "-"
    if not LEDGER.exists():
        append_locked(LEDGER, "# CLOSURE LOOP LEDGER (tools/closure_loop; one line per verdict, newest last)\n"
                              "Format: time | job | block @ source commit | verdict | host:run dir | detail\n\n")
    first, *rest = text.split("\n")
    append_locked(LEDGER, f"- {now_iso()} | {j['name']} | {spec.get('block', '?')} @ {c} | {first} | {where}\n"
                  + "".join(f"    {x}\n" for x in rest if x))


def write_status(fleet_note=""):
    rows = all_jobs()
    act = [r for r in rows if r["status"] not in TERMINAL]
    done = [r for r in rows if r["status"] in TERMINAL][-25:]
    L = [f"# CLOSURE LOOP STATUS (auto, {now_iso()}; daemon tools/closure_loop/closure_loop.py, unit closure-loop.service)",
         f"Active {len(act)} | terminal {len(rows) - len(act)} | ledger {LEDGER} | how-to {REVIEW}/CLOSURE_LOOP_HOWTO.md",
         fleet_note, "", "## Active"]
    for r in act:
        h = host_cfg(r["host"])["label"] if r.get("host") else "-"
        L.append(f"- {r['name']} [{r['spec']['block']}] {r['status']} stage={r.get('stage_key', '-')} host={h} "
                 f"run={r.get('run', '-')} since={r.get('stage_started', r['created'])} "
                 f"{('| ' + r['wait']) if r.get('wait') else ''}")
    L += ["", "## Recent terminal"]
    for r in done:
        L.append(f"- {r['name']} [{r['spec'].get('block', '?')}] {r['status']} {r.get('reason', '')[:200]}")
    tmp = STATUS_MD.with_suffix(".tmp")
    tmp.write_text("\n".join(L) + "\n")
    os.replace(tmp, STATUS_MD)


# ------------------------------------------------------------------------------------------------ state machine
def finish(j, status, reason, ledger_text):
    j["status"], j["reason"] = status, reason
    event(j, f"{status}: {reason}")
    ledger(j, ledger_text)
    term = {"CLOSED": "completed: CLOSED", "NEEDS_RTL": "failed: NEEDS_RTL", "NEEDS_HUMAN": "failed: NEEDS_HUMAN",
            "NEEDS_BUDGET": "failed: NEEDS_BUDGET", "CANCELLED": "cancelled"}.get(status, "stopped: " + status)
    experiment(j, f"{term} {reason[:120]}")


def crash(j, st, fleet, why):
    tail = stage_tail(j, st) if j.get("stage_tag") else ""
    resource = bool(RESOURCE_RE.search(tail)) or why.startswith("LOST")
    j.setdefault("crashes", []).append(dict(stage=st["key"], host=j["host"], attempt=j["attempt"], why=why,
                                            resource=resource, tail=tail[-1500:]))
    if j["retries_used"] >= 1:
        finish(j, "NEEDS_HUMAN", f"{st['key']} crashed twice ({why}; resource={resource})",
               f"NEEDS_HUMAN: {st['key']} crashed twice ({why}); last log tail:\n" +
               "\n".join(tail.strip().splitlines()[-6:]))
        return
    j["retries_used"] = 1
    j["attempt"] += 1
    if resource:
        h, _ = fleet.choose(j["spec"], exclude=j["hosts_tried"])
        if h:
            event(j, f"{st['key']} crashed ({why}); resource-related -> retry once on {host_cfg(h)['label']}")
            j["hosts_tried"].append(h)
            j["host"], j["run"] = h, f"{host_cfg(h)['base']}/{j['name']}"
            j["status"] = "SYNC"
            # benches are host independent: resume at the first non-bench stage
            stl = stage_list(j["spec"])
            j["stage_idx"] = next(i for i, s in enumerate(stl) if s["kind"] != "bench")
            return
        event(j, f"{st['key']} crashed ({why}); resource-related but no other host fits now -> retry on the same host")
    else:
        event(j, f"{st['key']} crashed ({why}) -> retry once on the same host")
    j["status"] = "READY"


def summarize_failure(j, fleet, metrics):
    """Launch the path-summary stage (remote, detached); the next ticks poll it."""
    v = j["spec"].get("verdict", {})
    base = subst(v["summary_base"], j) if v.get("summary_base") else None
    orfs = metrics.get("orfs_dir")
    fail_corners = [c for c, k, lim in (("ss", "ss_ps", SS_MIN), ("ff", "ff_ps", FF_MIN))
                    if metrics.get(k) is None or metrics[k] < lim]
    if not fail_corners or (not base and not orfs):
        return False
    basearg = f"--base $(ls -d {base} | tail -1)" if base else f"--orfs-dir {orfs}"
    extra = "".join(f" --macro {m}" for m in v.get("macros", [])) + \
        "".join(f" --post-sdc {p}" for p in v.get("post_sdc", []))
    cmd = (f"python3 {j['run']}/cl/path_summary.py {basearg} --src {j['run']}/src{extra} --corners "
           f"{','.join(fail_corners)} --output {j['run']}/cl/path_summary.json")
    st = dict(key="summary", kind="summary", threads=2, ram=16)
    launch_stage(j, st, cmd)
    fleet.launched(j["host"], 2, 16)
    j["status"], j["stage_key"] = "SUMMARY", "summary"
    return True


def failure_text(j):
    m = j.get("metrics", {})
    head = (f"NEEDS_RTL: SS {m.get('ss_ps')} / FF {m.get('ff_ps')} ps / DRC {m.get('drc')} "
            f"(line SS >= +{SS_MIN:g} / FF >= +{FF_MIN:g} / DRC 0){'; checks failed: ' + ', '.join(j['failed_checks']) if j.get('failed_checks') else ''}")
    lines = [head]
    r = ssh(j["host"], f"cat {j['run']}/cl/path_summary.json 2>/dev/null", timeout=60)
    try:
        s = json.loads(r.stdout)
        for key in ("setup_ss", "hold_ff"):
            if key in s:
                lines.append(f"{key} worst {s[key]['worst_slack_ps']} ps over {s[key]['paths_seen']} endpoints; worst classes:")
                for e in s[key]["classes"][:10]:
                    lines.append(f"  {e['worst_slack_ps']:+.1f} ps n={e['paths']} lv={e['max_levels']} "
                                 f"{e['start_class']} -> {e['end_class']}")
    except Exception:  # noqa: BLE001
        lines.append("(no path summary: timing passed or the summary failed; see the run dir)")
    return "\n".join(lines)


def launch_ready(j, fleet, spec, stl, st):
    """READY at a remote stage: capacity check, optional host move, launch (caller holds FLEET_LOCK)."""
    if True:
        ok, why = fleet.fits(j["host"], st["threads"], st["ram"])
        if not ok:
            j.setdefault("wait_since", time.time())
        if not ok and st["kind"] in ("calibrate", "route") and time.time() - j["wait_since"] >= 600:
            # nothing of this job is in flight: move it to another allowed host that fits now (re-sync, re-calibrate)
            h, _ = fleet.choose(spec, exclude=[j["host"]])
            if h:
                event(j, f"{st['key']} cannot start on {host_cfg(j['host'])['label']} ({why}); moving to {host_cfg(h)['label']}")
                j["hosts_tried"].append(h)
                j["host"], j["run"], j["status"], j["wait"] = h, f"{host_cfg(h)['base']}/{j['name']}", "SYNC", None
                j.pop("wait_since", None)
                cal = next((i for i, x in enumerate(stl) if x["kind"] == "calibrate"), None)
                j["stage_idx"] = cal if cal is not None else j["stage_idx"]
                experiment(j, f"running: moved to {host_cfg(h)['label']}")
                return
        if not ok:
            if j.get("wait") != why:
                j["wait"] = why
                event(j, f"{st['key']} waiting for capacity: {why}")
            return
        j["wait"] = None
        j.pop("wait_since", None)
        if st["kind"] == "route":   # one route per (block, source commit): the key is taken when the route launches
            keys, key = route_keys(), f"{spec['block']}@{spec['source']['commit'][:12]}"
            if keys.get(key, j["name"]) != j["name"]:
                finish(j, "REFUSED", f"one route per source commit: {key} already routed by job {keys[key]}",
                       f"REFUSED: {key} already routed by job {keys[key]}")
                return
            keys[key] = j["name"]
            keys_path().write_text(json.dumps(keys, indent=1) + "\n")
        launch_stage(j, st, st["cmd"])
        fleet.launched(j["host"], st["threads"], st["ram"])
        j["status"] = "RUNNING"
        event(j, f"launched {st['key']} (attempt {j['attempt']}) on {j['host']}")
        experiment(j, f"running: {st['key']} on {host_cfg(j['host'])['label']}")
        return


def step(j, fleet):
    spec = j["spec"]
    stl = stage_list(spec)
    s = j["status"]
    if s == "QUEUED":
        with FLEET_LOCK:
            h, why = fleet.choose(spec, exclude=[])
            if h:   # claim capacity now so parallel job threads do not pick the same headroom
                fleet.launched(h, 0, 0)
        if not h:
            if j.get("wait") != why:
                j["wait"] = why
                event(j, f"waiting for capacity: {why}")
            return
        j["wait"] = None
        j["host"], j["run"] = h, f"{host_cfg(h)['base']}/{j['name']}"
        j["hosts_tried"].append(h)
        j["status"] = "SYNC"
        experiment(j, "running: sync source", register=True)
        s = "SYNC"
    if s == "SYNC":
        try:
            sync_source(j)
        except ValueError as ex:
            finish(j, "NEEDS_HUMAN", str(ex), f"NEEDS_HUMAN: {ex}")
            return
        event(j, f"source {j['commit_full'][:12]} synced to {j['host']}:{j['run']}/src")
        j["status"] = "READY"
        return
    if s == "READY":
        st = stl[j["stage_idx"]]
        j["stage_key"] = st["key"]
        if st["kind"] == "verdict":
            return do_verdict(j, fleet, stl)
        if st["kind"] == "commit":
            return do_commit(j)
        with FLEET_LOCK:
            return launch_ready(j, fleet, spec, stl, st)
    if s == "RUNNING":
        st = stl[j["stage_idx"]]
        state, rc = poll_stage(j)
        if state in ("RUNNING", "STARTING"):
            return
        if state == "UNREACHABLE":
            j["unreachable"] = j.get("unreachable", 0) + 1
            if j["unreachable"] in (1, 30):
                event(j, f"{j['host']} unreachable while polling {st['key']} (will keep polling)")
            return
        j["unreachable"] = 0
        if state == "LOST":
            return crash(j, st, fleet, "LOST: stage wrapper gone without an rc file")
        ok_extra, okout = remote_ok(j, st.get("ok"))
        if st["kind"] == "bench":
            tail = stage_tail(j, st, 40)
            if st["expect"] == "fail" and (rc in (124, 137, 139, 143) or RESOURCE_RE.search(tail)):
                return crash(j, st, fleet, f"negative control rc={rc} looks like a crash, not a FAIL")
            passed = bench_outcome(j, st, rc, ok_extra)
            j["benches"][st["key"]] = dict(expect=st["expect"], rc=rc, ok=passed, tail=tail[-600:])
            if not passed:
                finish(j, "NEEDS_RTL", f"{st['key']} expected {st['expect'].upper()} but rc={rc}",
                       f"NEEDS_RTL: bench {st['key']} expected {st['expect'].upper()}, got rc={rc}\n" +
                       "\n".join(tail.strip().splitlines()[-5:]))
                return
            event(j, f"{st['key']} {('PASS' if st['expect'] == 'pass' else 'FAIL as expected')} (rc={rc})")
        else:
            if rc != 0 or not ok_extra:
                return crash(j, st, fleet, f"rc={rc}{'' if ok_extra else ' ok-check failed: ' + okout.strip()[-200:]}")
            event(j, f"{st['key']} done (rc=0)")
            if st["kind"] == "calibrate":
                r = ssh(j["host"], f"cat {j['run']}/cl/calib.json", timeout=60)
                try:
                    c = json.loads(r.stdout)
                    j["calibration"] = {k: c[k] for k in ("ss", "ff", "env", "db", "clock", "parasitics")}
                    event(j, "calibrated insertion " + " ".join(f"{k}={v}" for k, v in c["env"].items() if "ALL" not in k))
                except Exception:  # noqa: BLE001
                    return crash(j, st, fleet, "calibrate produced no calib.json")
                dev = budget_check(j)
                if dev:
                    if j["spec"]["budget"].get("on_deviation", "flag") == "flag":
                        finish(j, "NEEDS_BUDGET", dev[:200],
                               f"NEEDS_BUDGET: {j['budget']['master']} block clock insertion off its budget sheet ({dev}). "
                               "Re-plan the die entry target (tools/budgets) or fix the block tree, then retry; the IO SDC "
                               "is NOT re-calibrated silently.")
                        return
                    event(j, f"BUDGET FLAG (continuing on the sheet SDC): {dev}")
                    ledger(j, f"BUDGET FLAG {j['budget']['master']}: {dev} (on_deviation=continue)")
                elif j.get("budget"):
                    event(j, f"budget check OK: insertion {j['budget']['check']['measured_ss']:g} within "
                             f"{j['budget']['insertion']['tolerance_ps']:g} ps of the sheet")
        j["stage_idx"] += 1
        j["status"] = "READY"
        return
    if s == "SUMMARY":
        state, rc = poll_stage(j)
        if state in ("RUNNING", "STARTING", "UNREACHABLE"):
            return
        text = failure_text(j)
        finish(j, "NEEDS_RTL", text.split("\n")[0][11:], text)


def do_verdict(j, fleet, stl):
    v = j["spec"].get("verdict", {})
    m = get_metrics(j)
    j["metrics"] = m
    checks, failed = {}, []
    for c in v.get("checks", []):
        ok, out = remote_ok(j, c["cmd"])
        checks[c["name"]] = dict(ok=ok, out=out[-300:])
        if not ok:
            failed.append(c["name"])
    j["checks"], j["failed_checks"] = checks, failed
    ss, ff, drc = m.get("ss_ps"), m.get("ff_ps"), m.get("drc")
    if ss is None or ff is None or drc is None:
        finish(j, "NEEDS_HUMAN", f"verdict inputs missing ({json.dumps(m)[:300]})",
               f"NEEDS_HUMAN: verdict inputs missing: {json.dumps(m)[:400]}")
        return
    benches_ok = all(b["ok"] for b in j["benches"].values())
    closed = ss >= SS_MIN and ff >= FF_MIN and drc == 0 and not failed and benches_ok and not m.get("errors")
    event(j, f"verdict SS {ss:+.2f} / FF {ff:+.2f} / DRC {drc} / checks failed {failed} -> "
             f"{'CLOSED' if closed else 'NOT CLOSED'}")
    if closed:
        j["stage_idx"] += 1
        j["status"] = "READY"
        experiment(j, f"running: collect/export/merge (SS {ss:+.1f} / FF {ff:+.1f})")
        return
    if not summarize_failure(j, fleet, m):
        text = failure_text(j)
        finish(j, "NEEDS_RTL", text.split("\n")[0][11:], text)


def do_commit(j):
    m = j["metrics"]
    try:
        with PUBLISH_LOCK:
            out = publish(j, m)
    except Exception as ex:  # noqa: BLE001
        finish(j, "NEEDS_HUMAN", f"publish failed: {str(ex)[:300]}", f"NEEDS_HUMAN: CLOSED but publish failed: {str(ex)[:400]}")
        return
    j["publish"] = out
    merge = out.get("merge", "")
    detail = (f"CLOSED SS {m['ss_ps']:+.2f} / FF {m['ff_ps']:+.2f} ps DRC {m['drc']} | record "
              f"{j['spec']['source']['branch']} {out.get('branch_commit', '')[:9]} ({out.get('files')} files) | {merge}")
    if merge.startswith(("CONFLICT", "PUSH-RACE")):
        finish(j, "NEEDS_HUMAN", f"closed and recorded, merge failed: {merge}", detail)
    else:
        finish(j, "CLOSED", detail, detail)


# ------------------------------------------------------------------------------------------------ commands
FIXED_SIGNATURES = [
    # (fix id, stage kind, regex over the crash log tail) -- a job that died on one of these is re-queued ONCE
    ("label-sanitise-20261006", "calibrate", re.compile(r"nickname-tag|no ORFS base")),
    ("calib-json-placeholder-20261006", "collect", re.compile(r"cl/calib\.json'?: No such file")),
    ("calib-json-placeholder-20261006", "export", re.compile(r"cl/calib\.json'?: No such file")),
]


BENCH_RE = re.compile(r"^(bench_\S+) expected (FAIL|PASS) but rc=(-?\d+)")


def reevaluate_benches(jobs):
    """Fix bench-regex-multiline (2026-10-06): bench verdicts were taken on 20 log lines without re.M.  Re-judge every
    job that stopped on a bench verdict with the fixed rule; a bench that now passes resumes the job at the next stage."""
    fid = "bench-regex-multiline-20261006"
    for j in jobs:
        m = BENCH_RE.match(j.get("reason") or "")
        if j["status"] not in ("NEEDS_RTL", "NEEDS_HUMAN") or not m or fid in j.get("fix_requeued", []):
            continue
        j.setdefault("fix_requeued", []).append(fid)
        stl = stage_list(j["spec"])
        idx = next((i for i, x in enumerate(stl) if x["key"] == m.group(1)), None)
        if idx is None or not j.get("stage_tag", "").startswith(m.group(1) + "."):
            save_job(j)
            continue
        st = stl[idx]
        if bench_outcome(j, st, int(m.group(3))):
            j["benches"][st["key"]] = dict(expect=st["expect"], rc=int(m.group(3)), ok=True, rejudged=fid)
            j["status"], j["stage_idx"], j["reason"] = "READY", idx + 1, None
            event(j, f"{st['key']} re-judged {('PASS' if st['expect'] == 'pass' else 'FAIL as expected')} under {fid}; resumed")
            ledger(j, f"REQUEUED automatically: {st['key']} re-judged correct under loop fix {fid} (MULTILINE regex over the whole log)")
            experiment(j, f"running: resumed after {fid}")
        else:
            event(j, f"{st['key']} re-judged under {fid}: verdict stands")
        save_job(j)


def auto_requeue(jobs):
    live_blocks = {(x["spec"].get("block"), str(x["spec"].get("source", {}).get("commit", ""))[:9])
                   for x in jobs if x["status"] not in TERMINAL}
    for j in jobs:
        if j["status"] not in ("NEEDS_HUMAN", "CANCELLED") or not j.get("crashes"):
            continue
        c = j["crashes"][-1]
        stl = stage_list(j["spec"])
        kind = next((x["kind"] for x in stl if x["key"] == c["stage"]), None)
        for fid, k, rx in FIXED_SIGNATURES:
            if kind != k or not rx.search(c.get("tail", "") + c.get("why", "")) or fid in j.get("fix_requeued", []):
                continue
            if (j["spec"]["block"], str(j["spec"]["source"]["commit"])[:9]) in live_blocks:
                continue   # its owner already re-dropped it under another name
            j.setdefault("fix_requeued", []).append(fid)
            j["status"], j["retries_used"], j["attempt"], j["errors"], j["reason"] = "READY", 0, j["attempt"] + 1, [], None
            j["stage_idx"] = next(i for i, x in enumerate(stl) if x["key"] == c["stage"])
            event(j, f"auto re-queued after loop fix {fid} (died in {c['stage']} on that signature)")
            ledger(j, f"REQUEUED automatically: loop fix {fid} (failed in {c['stage']}: {c.get('why', '')[:80]})")
            experiment(j, f"running: re-queued after fix {fid}")
            live_blocks.add((j["spec"]["block"], str(j["spec"]["source"]["commit"])[:9]))
            save_job(j)
            break


def tick(fleet):
    try:
        ingest()
    except Exception:  # noqa: BLE001
        log("ingest error:\n" + traceback.format_exc())
    try:
        reevaluate_benches(all_jobs())
        auto_requeue(all_jobs())
    except Exception:  # noqa: BLE001
        log("auto_requeue error:\n" + traceback.format_exc())
    def one(j):
        try:
            step(j, fleet)
        except Exception as ex:  # noqa: BLE001
            j.setdefault("errors", []).append(f"{now_iso()} {type(ex).__name__}: {str(ex)[:500]}")
            j["errors"] = j["errors"][-10:]
            log(f"[{j['name']}] step error:\n{traceback.format_exc()}")
            if len(j["errors"]) >= 10 and j["status"] in ("SYNC", "READY"):
                finish(j, "NEEDS_HUMAN", f"10 consecutive loop errors: {str(ex)[:200]}",
                       f"NEEDS_HUMAN: loop errors at {j['status']}: {str(ex)[:300]}")
        save_job(j)
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        list(ex.map(one, [j for j in all_jobs() if j["status"] not in TERMINAL]))
    write_status()


def cmd_daemon(a):
    STATE.mkdir(parents=True, exist_ok=True)
    lock = open(STATE / "daemon.lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        sys.exit("another closure-loop daemon holds the lock")
    lock.write(str(os.getpid()))
    lock.flush()
    DROP.mkdir(parents=True, exist_ok=True)
    fleet = Fleet()
    log(f"closure-loop daemon up (pid {os.getpid()}, interval {a.interval}s, state {STATE})")
    recon = None
    last_recon = 0.0
    while True:
        t0 = time.time()
        # hourly: reconcile the shared experiment register (reconcile.py; never kills anything), in the background
        if (recon is None or recon.poll() is not None) and t0 - last_recon >= 3600:
            last_recon = t0
            out = open(STATE / "reconcile_last.json", "w")
            recon = subprocess.Popen([sys.executable, str(HERE / "reconcile.py")], stdout=out,
                                     stderr=subprocess.STDOUT)
            log("register reconcile started (hourly)")
        tick(fleet)
        (STATE / "heartbeat").write_text(now_iso() + "\n")
        time.sleep(max(5, a.interval - (time.time() - t0)))


def cmd_status(a):
    for r in all_jobs():
        h = host_cfg(r["host"])["label"] if r.get("host") else "-"
        print(f"{r['name']:40s} {r['status']:12s} {r.get('stage_key', '-'):16s} {h:8s} "
              f"{(r.get('reason') or r.get('wait') or '')[:90]}")
    hb = STATE / "heartbeat"
    print("heartbeat:", hb.read_text().strip() if hb.exists() else "none")


def cmd_validate(a):
    spec = json.loads(Path(a.file).read_text())
    errs = validate(spec)
    print("\n".join(errs) if errs else "OK")
    sys.exit(1 if errs else 0)


def cmd_retry(a):
    j = load_job(a.name)
    if j["status"] not in ("NEEDS_HUMAN", "NEEDS_BUDGET"):
        sys.exit(f"{a.name} is {j['status']}; only NEEDS_HUMAN / NEEDS_BUDGET jobs can be retried")
    if j["status"] == "NEEDS_BUDGET" and j.get("budget"):
        j["budget"]["override"] = "human retry after NEEDS_BUDGET"
        j["spec"].setdefault("budget", {})["on_deviation"] = "continue"
        j["stage_idx"] += 1           # the calibration is kept: continue after it, on the sheet SDC
    j["status"], j["retries_used"], j["attempt"] = "READY" if j.get("host") else "QUEUED", 0, j["attempt"] + 1
    j["errors"] = []
    event(j, "human retry: re-queued from stage " + str(j.get("stage_key")))
    save_job(j)
    ledger(j, "RETRY (human) from stage " + str(j.get("stage_key")))


def cmd_cancel(a):
    j = load_job(a.name)
    if j["status"] in TERMINAL:
        sys.exit(f"{a.name} already {j['status']}")
    if j.get("stage_tag") and j.get("host"):
        run, t = j["run"], j["stage_tag"]
        # only this loop's own stage process group, and only containers that mount this job's own run dir
        ssh(j["host"], f"""p=$(cat {run}/cl/{t}.pid 2>/dev/null); [ -n "$p" ] && kill -TERM -- -$p 2>/dev/null
for c in $(docker ps -q); do docker inspect --format '{{{{range .Mounts}}}}{{{{.Source}}}} {{{{end}}}}' $c | grep -q '{run}/' && docker stop -t 5 $c; done; true""",
            timeout=180)
    finish(j, "CANCELLED", "cancelled by a human", "CANCELLED by a human")
    save_job(j)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("daemon"); d.add_argument("--interval", type=int, default=60)
    sub.add_parser("tick"); sub.add_parser("status")
    v = sub.add_parser("validate"); v.add_argument("file")
    r = sub.add_parser("retry"); r.add_argument("name")
    c = sub.add_parser("cancel"); c.add_argument("name")
    a = ap.parse_args()
    if a.cmd == "daemon":
        cmd_daemon(a)
    elif a.cmd == "tick":
        STATE.mkdir(parents=True, exist_ok=True)
        tick(Fleet())
    elif a.cmd == "status":
        cmd_status(a)
    elif a.cmd == "validate":
        cmd_validate(a)
    elif a.cmd == "retry":
        cmd_retry(a)
    elif a.cmd == "cancel":
        cmd_cancel(a)


if __name__ == "__main__":
    main()
