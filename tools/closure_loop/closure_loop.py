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
    closure_loop.py submit-recheck --since ISO [--requeue] [--log F]   # re-judge FLOORPLAN_MARGIN jobs at submit
    closure_loop.py retry <name>               # human: re-queue a NEEDS_HUMAN job from its failed stage
    closure_loop.py retry-eco <name> [--why]   # human: re-run the hold ECO (current rev) on a hold-only NEEDS_RTL job
    closure_loop.py ioref-rejudge <name>       # human: re-judge a NEEDS_RTL job at its ROUTED clock insertion (no re-route)
    closure_loop.py rebudget-rejudge <name> --rb budget_rbN --sdc F [--dry]   # re-judge under a re-derived die-link IO budget
    closure_loop.py cancel <name>              # stop this loop's own stage for <name>; status CANCELLED
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import glob
import json
import hashlib
import os
import re
import shlex
import math
from contextlib import contextmanager, ExitStack
from functools import wraps
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
import subprocess
import tempfile
import sys
import time
import traceback
from pathlib import Path

from ssh_transport import command as transport_command
from source_archive import build_archive, repo_path
from postroute_recovery import remote_command as postroute_probe_command
import submit_lint

HERE = Path(__file__).resolve().parent
REPO = Path(os.environ.get("CL_REPO", "/home/ubuntu/OpenTallas"))          # git object store for archive/commit/merge
STATE = Path(os.environ.get("CL_STATE", str(Path.home() / ".local/state/closure_loop")))
REVIEW = Path(os.environ.get("CL_REVIEW", "/tmp/claude-review-20261003"))
DROP = REVIEW / "closure_jobs"
LEDGER = REVIEW / "CLOSURE_LOOP_LEDGER.md"
STATUS_MD = REVIEW / "CLOSURE_LOOP_STATUS.md"
EXPERIMENT = Path("/home/ubuntu/opentallas-monitor/experiment.py")
OWNER = "Claude:closure-loop"
SS_MIN, FF_MIN = 0.0, 0.0             # OWNER DECISION 2026-10-07 20:1x: ACCEPT at SS >= 0 / FF >= 0 / DRC 0 at 833.333 sign-off (+15 is the DESIGN target: route 770, repair hold margin 50; was +15/+15 since 10-06 18:15)
RAM_HEADROOM_GB = 32
LIGHT_STAGE_RAM_GB = 8      # drive-0849: bench / collect / export stages
LIGHT_DISK_FLOOR_GB = 30    # their run-root / disk-root floor (full floor for route / calibrate / ECO)
ADMIT_SAFETY_GB = 16          # fixed safety over a job's own RAM request (owner: no reservation for future growth)
PENDING_WINDOW_S = 600
PENDING_RAM_WINDOW_S = 180    # RAM reservation of a launch (threads keep the 10-min ramp allowance)
# EARLY_FAIL_* (stuckscan 2026-10-08): a route stopped by an early-fail gate (stuckscan.py hopeless()): redesign work
EARLY_FAIL = ("EARLY_FAIL_SETUP", "EARLY_FAIL_HOLD", "EARLY_FAIL_CONGESTION", "EARLY_FAIL_DRC")
TERMINAL = {"SMOKE_OK", "CLOSED", "NEEDS_RTL", "NEEDS_HUMAN", "NEEDS_BUDGET", "REFUSED", "CANCELLED", "INVALID",
            "FLOORPLAN_MARGIN", "PREROUTE_MARGIN", *EARLY_FAIL}
RESOURCE_RE = re.compile(r"Cannot allocate memory|[Oo]ut of memory|\bOOM\b|oom-kill|No space left|ENOSPC|std::bad_alloc|"
                         r"Resource temporarily unavailable|Killed\b|signal 9|exit code 137|MemoryError|"
                         r"admission (?:timed out|refused)|[Bb]us error|SIGBUS|Segmentation fault|internal compiler error|"
                         r"g\+\+: fatal error|cc1plus: .*(?:killed|error)", re.M)
# a bench whose TOOLS crashed (compiler bus error, segfault, OOM) is not a verdict on the RTL (hbm_su_red_slice_6f2d14e36:
# g++ bus error on EPYC2 -> NEEDS_RTL although the bench never ran): crash -> retry once on another host -> NEEDS_HUMAN
BENCH_CRASH_RC = (124, 134, 135, 137, 139, 143)


def bench_crashed(st, rc, tail):
    if rc in BENCH_CRASH_RC or RESOURCE_RE.search(tail):
        return st["expect"] == "fail" or not WORK_RE.search(tail)
    return False
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")
DEFAULT_SRC_PATHS = ["tools", "rtl", "physical", "Makefile"]
FLEET_LOCK = threading.RLock()     # host choice / capacity check / launch are atomic across job threads
GIT_LOCK = threading.Lock()        # fetches into the shared object store
PUBLISH_LOCK = threading.Lock()    # one commit/merge at a time
WORKERS = 192
SYNC_SLOTS = 64          # workers QUEUED/SYNC jobs may hold at once (the rest keep READY / RUNNING / ECO moving)
# declared threads of own running stages count at 0.6 against the cap: full declared threads blocked EPYC2 at load1 40
# (7 calibrates in synth/place, ~1 core each), load1 alone let EPYC3 reach 342 (27 routes ramping into DRT together)
OWN_RUNNING_WEIGHT = 0.6
HM_DEFAULT_SINCE = "2026-10-06T20:40"
HM_LOW_SINCE = "2026-10-07T04:17"      # new jobs from here: route hold margin 10 ps, hold closed by the post-route ECO
# FLOW-HOLD (2026-10-07): jobs created from here route with multi-mode hold repair (OT_ROUTE_HOLD_CORNERS=mm: SS setup +
# FF hold under the FF sign-off constraints at CTS / global route) and HM_MM route hold margin (applies at FF only)
MM_SINCE = "2026-10-07T21:00"
# OWNER OPTION B (2026-10-07 20:45): closure = setup at TT + hold at FF + DRC 0.  Every calibrate / route launched from
# here routes with CORNER=TC (setup repair at TT; with mm, hold at FF) unless spec "route_corner" names another corner;
# hold ECOs time the setup scene at TT.  SS setup is recorded as a sensitivity (ss_sensitivity_ps).
OPTB_SINCE = "2026-10-07T20:20"
# CALIB-CORNER (2026-10-08, orphans-2 finding): jobs created from here calibrate at the ROUTE corner and reference the
# route-time IO SDC to the route-corner insertion.  Every recipe builds its route IO SDC from CK_SS_* (io_vclk_m_$CK_SS_MEAN,
# make_sdc.py --l-ss-*, budget SDCs); a TC route signs off at the routed TT reference, so with CK_SS_* at the SS insertion
# the router saw ~190 ps of output setup credit that sign-off removed (hfd_router h1c: route TT -71.83, routed reference
# -152.67).  For a TC/TT route: calibrate runs with OT_ORFS_CORNER=<corner> (CTS at TT), ck_insertion.py --route-corner
# puts the TT insertion in CK_SS_* (SS values in CK_SSLIB_*), the parallel-calibrate assumption is the block's TT
# (routed grade, else calibrate TT) from measured_insertion.json, and a TC job with no TT value calibrates sequentially
# (CTS-only, minutes).  SS-corner routes keep the SS reference.  Earlier jobs keep their behaviour.
ROUTE_REF_SINCE = "2026-10-08T19:05"
SETUP_LIB = "TT"
# VT-SWAP ECO (merge-eco 2026-10-09, from eco-sweep e494ff8ac): a route whose only miss is a THIN TT setup miss
# (TT in [VTSWAP_TT_FLOOR, 0), FF >= 0, DRC 0, checks/benches clean) runs vtswap_eco.sh (RVT->LVT master swaps on the
# TT paths, prospective <= VTSWAP_CAP_PCT % LVT, FF hold guard, no re-route) as its ECO stage before it is judged
# NEEDS_RTL.  Targets are tried in order (a miss at 10 ps re-runs once at 5 ps: fewer swaps, under the cap -- eco-sweep
# wfc_lnk / topk closed on the 5 ps rerun).  spec hold_eco.vtswap: false turns it off; vtswap_targets / vtswap_cap_pct override.
VTSWAP_TT_FLOOR = -45.0
VTSWAP_TARGETS = (10.0, 5.0)
VTSWAP_CAP_PCT = 2.0
# COMBO ECO (drive-0849 2026-10-09, coordinator-approved): a route that misses BOTH thinly -- TT in [COMBO_TT_FLOOR, 0) AND FF
# in [COMBO_FF_FLOOR, 0), DRC 0, checks/benches clean -- gets neither the VT-swap ECO (needs FF >= 0) nor the hold ECO (needs
# TT >= 0).  It runs vtswap_eco.sh (RVT->LVT on TT paths, <= VTSWAP_CAP_PCT % LVT) and then hold_eco.sh stacked on the
# VT-swap result (ECO_RB_DB=6_final.odb) as ONE ECO stage; the hold-ECO completion path judges / installs / re-verdicts it.
# (The manual /tmp/sc/combo_eco.py launches, made automatic.)  spec hold_eco.combo: false turns it off.
COMBO_TT_FLOOR = -45.0
COMBO_FF_FLOOR = -30.0
HM_MM = 0.050
DEFAULT_NEEDS = {"bench": ["verilator", "iverilog", "yosys"], "calibrate": ["orfs"], "route": ["orfs"],
                 "signoff": ["orfs"], "collect": [], "export": [], "summary": ["orfs"]}
STAGE_DEFAULTS = {"bench": (4, 16), "route": None, "signoff": (4, 16), "collect": (1, 1), "export": (1, 1),
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
    if is_local(host):          # localhost runs loop jobs directly (OWNER 2026-10-07 05:00), no ssh to itself
        if input is None:
            return sh(["bash", "-s"], timeout=timeout, check=check, input=script)
        return sh(["bash", "-c", script], timeout=timeout, check=check, input=input)
    try:
        with transport_command(host) as base:
            if input is None:
                return sh(base + ["bash -s"], timeout=timeout, check=check, input=script)
            return sh(base + [script], timeout=timeout, check=check, input=input)
    except RuntimeError as e:
        # an unreachable host (ssh master refused, e.g. PVE1 kex reset 2026-10-08 00:50) is an rc=255 ssh failure that
        # every caller already handles, not a daemon crash (the daemon crash-looped on the toolchain probe for ~45 min)
        if check or not str(e).startswith("ssh: master connection failed"):
            raise
        return subprocess.CompletedProcess(args=[host], returncode=255, stdout="", stderr=str(e))


def is_local(host):
    return host in ("localhost", "local")


def rpath(host, path):
    """rsync source spec of a path on host"""
    return path if is_local(host) else f"{host}:{path}"


def gfetch(*refs, timeout=600, tries=3):
    """Fetch refs into origin/<ref>.  The object store is the shared checkout, where another git process can hold a
    ref lock; an unchecked failed fetch left origin/main stale and sent pq_r128_expanded_b1528203c to NEEDS_HUMAN
    "not on origin/main" for a commit already on main (10-07 11:43).  Retry, update the tracking refs explicitly,
    and log a fetch that still fails."""
    spec = [f"+refs/heads/{r}:refs/remotes/origin/{r}" for r in refs]
    r = None
    for attempt in range(tries):
        with GIT_LOCK:
            r = sh(["git", "-C", str(REPO), "fetch", "-q", "origin", *spec], timeout=timeout)
        if r.returncode == 0:
            return r
        if attempt + 1 < tries:
            time.sleep(5 * (attempt + 1))
    log(f"git fetch {' '.join(refs)} failed after {tries} tries (rc={r.returncode}): {r.stderr.strip()[-300:]}")
    return r


def git(*args, timeout=900, check=True, cwd=None):
    return sh(["git", "-C", str(cwd or REPO), *args], timeout=timeout, check=check)


def append_locked(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(text)


def hosts_table():
    return json.loads((HERE / "hosts.json").read_text())["hosts"]


def disk_roots(cfg):
    """{path: min free GB} for every filesystem a host's jobs write besides the run root (hosts.json disk_roots;
    fleet disk guard 2026-10-07: the run-root floor alone let / fill on AGIdock and localhost)"""
    return dict(cfg.get("disk_roots", {}))


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
    required = spec.get("host_require")
    if required is not None and (not isinstance(required, list) or not required
                                or any(not isinstance(x, str) for x in required)):
        e.append("host_require must be a nonempty list of host names, not a boolean")
    elif required and any(x not in {h["name"] for h in hosts_table()} for x in required):
        e.append("host_require contains an unknown host")
    src = spec["source"]
    if not isinstance(src, dict) or not src.get("branch") or not re.match(r"^[0-9a-f]{7,40}$", str(src.get("commit", ""))):
        e.append("source needs branch and a hex commit")
    if isinstance(src, dict) and "required_files" in src:
        files = src["required_files"]
        if not isinstance(files, list) or not files:
            e.append("source.required_files must be a nonempty list of literal repository paths")
        else:
            try:
                for value in files:
                    repo_path(value)
            except ValueError as ex:
                e.append(str(ex))
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
    allcaps = set().union(*(set(x.get("caps", [])) for x in hosts_table()))
    if isinstance(st, dict):
        for x in list(st.get("bench", [])) + [st.get(k) or {} for k in ("calibrate", "route", "signoff", "collect", "export")]:
            if "needs" in x and not (isinstance(x["needs"], list) and set(x["needs"]) <= allcaps):
                e.append(f"needs must be a list from {sorted(allcaps)}: {x.get('needs')}")
        if not any(job_needs(spec) <= set(x.get("caps", [])) for x in hosts_table()
                   if not spec.get("hosts") or x["name"] in spec["hosts"] or spec.get("peak_ram_gb", 32) <= SMALL_JOB_GB):
            e.append(f"no allowed host has every capability this job needs ({sorted(job_needs(spec))})")
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
                        min_count_regex=b.get("min_count_regex"),
                        threads=b.get("threads", t), ram=b.get("peak_ram_gb", r)))
    cal = st.get("calibrate") or {}
    # OWNER 2026-10-08: a recipe that references IO in-run to its own propagated clock (io_ref_skew.sdc) needs no
    # calibrate at all
    in_run_ref = "io_ref_skew" in str((st.get("route") or {}).get("cmd", ""))
    if cal.get("enabled", True) and cal.get("cmd") and not in_run_ref:
        base = cal["base"]
        tail = (f"\nB=$(ls -d {base} 2>/dev/null | tail -1); [ -n \"$B\" ] || {{ echo 'calibrate: no ORFS base {base}'; "
                f"bash {{CL}}/cal_classify.sh '{base}'; exit 3; }}"
                f"\n[ -f \"$B/4_1_cts.odb\" ] || {{ echo \"calibrate: no 4_1_cts.odb under $B\"; bash {{CL}}/cal_classify.sh '{base}'; exit 4; }}"
                f"\npython3 {{CL}}/ck_insertion.py --base \"$B\" --clock {cal.get('clock', 'ck')} --output {{CL}}/calib.json"
                f" --route-corner \"${{OT_CAL_ROUTE_CORNER:-}}\""
                f" > {{CL}}/calib.env || exit 4\ncat {{CL}}/calib.env\nset -a; . {{CL}}/calib.env; set +a")
        if cal.get("sdc_cmd"):
            tail += "\n" + cal["sdc_cmd"]
        out.append(dict(key="calibrate", kind="calibrate", cmd=cal["cmd"] + tail, ok=cal.get("ok"), sdc_cmd=cal.get("sdc_cmd"),
                        threads=cal.get("threads", spec.get("threads", 16)), ram=cal.get("peak_ram_gb", spec.get("peak_ram_gb", 32)),
                        logs=cal.get("logs", []), out_dir=cal.get("out_dir")))
    for k in ("route", "signoff"):
        if st.get(k, {}).get("cmd"):
            t, r = STAGE_DEFAULTS[k] or (spec.get("threads", 16), spec.get("peak_ram_gb", 32))
            out.append(dict(key=k, kind=k, cmd=st[k]["cmd"], ok=st[k].get("ok"),
                            threads=st[k].get("threads", t), ram=st[k].get("peak_ram_gb", r),
                            logs=st[k].get("logs", []), out_dir=st[k].get("out_dir")))
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


# Hold this across read/transition/remote launch/save, not just os.replace.  A cancellation
# must see the stage actually launched by an in-flight worker, including a host move.
_JOB_LOCKS = threading.local()


@contextmanager
def job_lock(name):
    if not NAME_RE.fullmatch(name):
        raise ValueError(f"invalid job name: {name}")
    held = getattr(_JOB_LOCKS, "held", None)
    if held is None:
        held = _JOB_LOCKS.held = set()
    if name in held:
        yield
        return
    directory = STATE / "job_locks"
    directory.mkdir(parents=True, exist_ok=True)
    with open(directory / f"{name}.lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        held.add(name)
        try:
            yield
        finally:
            held.remove(name)


def locked_job_command(fn):
    @wraps(fn)
    def command(a):
        with job_lock(a.name):
            return fn(a)
    return command


class JobState(dict):
    """A job dict that remembers the file version it was read from (raw text + mtime_ns; never serialised).

    STALE-SAVE 2026-10-09 (flow-fix-0410): a worker that loaded a job, ran a long step (bench relaunch, verdict) and
    then saved it overwrote a hand edit made meanwhile: pi-ta15prod hm10/hm25 went back to a ~45-min-old snapshot
    twice (03:00:51 and earlier; drive-0212.log).  Hand edits do not take the job flock, so the lock alone cannot
    prevent it.  save_job now does read-modify-write against the version this dict was read from."""
    __slots__ = ("cl_mtime", "cl_raw")


def _stamp(j, mtime, raw):
    if not isinstance(j, JobState):
        return j
    j.cl_mtime, j.cl_raw = mtime, raw
    return j


def _read_state(p):
    """(mtime_ns, raw) with the stat taken BEFORE the read: a change racing the read looks newer, never older."""
    st = p.stat()
    return st.st_mtime_ns, p.read_text()


def load_job(name):
    mtime, raw = _read_state(jpath(name))
    return _stamp(JobState(json.loads(raw)), mtime, raw)


STALE_SAVE_LOG = "stale_save.log"


def _stale_log(name, line):
    try:
        with open(STATE / STALE_SAVE_LOG, "a") as f:
            f.write(f"{now_iso()} {name} {line}\n")
    except OSError:
        pass
    log(f"STALE-SAVE {name}: {line}")


def _merge_newer(j, current, cur_mtime):
    """The file changed since j was read.  Returns the dict to write, or None to refuse (j then becomes the file).

    Three-way merge on top-level keys against the version j was read from: the keys this writer changed are applied
    over the newer file when the external writer changed none of them; any overlap (or no known base) refuses."""
    base = None
    raw = getattr(j, "cl_raw", None)
    if raw is not None:
        try:
            base = json.loads(raw)
        except ValueError:
            base = None
    ignore = {"updated"}
    if base is None:
        _stale_log(j["name"], f"REFUSED: file changed (mtime {cur_mtime}) and this copy has no base version; kept the file")
        return None
    mine = {k for k in set(base) | set(j) if k not in ignore and base.get(k) != j.get(k)}
    theirs = {k for k in set(base) | set(current) if k not in ignore and base.get(k) != current.get(k)}
    if mine & theirs:
        _stale_log(j["name"], f"REFUSED: newer file (mtime {cur_mtime}) changed {sorted(theirs)}; this writer changed "
                              f"{sorted(mine)} from an older version; kept the file, dropped this save")
        return None
    merged = dict(current)
    for k in mine:
        if k in j:
            merged[k] = j[k]
        else:
            merged.pop(k, None)
    if mine:
        _stale_log(j["name"], f"MERGED: newer file changed {sorted(theirs)}; applied this writer's {sorted(mine)} on top")
    return merged


def save_job(j):
    with job_lock(j["name"]):
        p = jpath(j["name"])
        if p.exists():
            cur_mtime, cur_raw = _read_state(p)
            current = json.loads(cur_raw)
            # Auto-requeue/ingest may have taken their snapshot before cancel.  CANCELLED
            # is absorbing: another attempt needs a new job name, never a stale save.
            if current["status"] == "CANCELLED" and j["status"] != "CANCELLED":
                j.clear()
                j.update(current)
                _stamp(j, cur_mtime, cur_raw)
                return
            # version check on the exact text read (every save rewrites "updated"); mtime_ns alone is not enough:
            # ext4 stamps with the coarse kernel clock, so two writes a few ms apart can share one mtime
            known = getattr(j, "cl_raw", None)
            if isinstance(j, JobState) and known is not None and known != cur_raw:
                merged = _merge_newer(j, current, cur_mtime)
                if merged is None:
                    j.clear()
                    j.update(current)
                    _stamp(j, cur_mtime, cur_raw)
                    return
                j.clear()
                j.update(merged)
        j["updated"] = now_iso()
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        raw = json.dumps(j, indent=1) + "\n"
        tmp.write_text(raw)
        os.replace(tmp, p)
        _stamp(j, p.stat().st_mtime_ns, raw)


_STATE_READ_WARNINGS = set()


def all_jobs():
    """Keep unrelated fleet work running if an externally written state is malformed.

    Leave the offending file untouched for owner recovery; never infer a fresh
    status or resubmit it, since it could have a live producer outside the loop.
    """
    jobs = []
    for p in sorted((STATE / "jobs").glob("*.json")):
        raw = None
        try:
            mtime, raw = _read_state(p)
            j = _stamp(JobState(json.loads(raw)), mtime, raw) if raw.lstrip().startswith("{") else json.loads(raw)
            if not isinstance(j, dict) or not isinstance(j.get("spec"), dict) or \
                    j.get("name") != p.stem or not isinstance(j.get("status"), str) or not j["status"]:
                raise ValueError("job state requires matching name, nonempty status and object spec")
        except (OSError, ValueError) as exc:
            # One warning per distinct bad content; a persistent malformed file
            # must not flood the daemon log on every status query and tick.
            key = (str(p), str(exc), hashlib.sha256((raw or "").encode()).hexdigest())
            if key not in _STATE_READ_WARNINGS:
                _STATE_READ_WARNINGS.add(key)
                log(f"MALFORMED job state {p}: {exc}; preserved, excluded from scheduling")
            continue
        jobs.append(j)
    return jobs



def keys_path():
    return STATE / "route_keys.json"


MAX_ROUTES_PER_KEY = 3     # OWNER 2026-10-07 05:00: small + aggressive + half-rate variants of one design in parallel


def route_keys():
    """{block@commit: [job names]} (older files hold one name per key)"""
    k = json.loads(keys_path().read_text()) if keys_path().exists() else {}
    return {key: (v if isinstance(v, list) else [v]) for key, v in k.items()}


def route_key_full(keys, key, name):
    """None if name may route under key, else the holders that fill it"""
    held = keys.get(key, [])
    return None if name in held or len(held) < MAX_ROUTES_PER_KEY else held


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


# LINT-AT-SUBMIT (stream lint-at-submit 2026-10-09): pin density (and utilisation where a measurement of the same
# synthesis input exists) estimated from the job's pin plan + outline at intake (submit_lint.py), before a queue slot or
# synthesis is spent.  Fails on one layer but passes with the approved two-layer spread -> the spread (PIN_H 'M4 M6' /
# PIN_V 'M5 M7') is added to the route_master stage commands and recorded in spec.submit_lint (the submitted spec is
# kept in spec_submitted); fails even spread -> REFUSED "SUBMIT_LINT FLOORPLAN_MARGIN: ..." with no compute spent.
# Spec "submit_lint": false (or "fp_lint": false) opts out; fp_lint {"set": {...}} / warn_only apply as in the flow lint.
def util_db_path():
    return STATE / "submit_lint_util.json"


def util_db():
    try:
        return json.loads(util_db_path().read_text())
    except (OSError, ValueError):
        return {}


def util_db_add(key, rec):
    p = util_db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(str(p) + ".lock", "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        db = util_db()
        db[key] = rec
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(db, indent=1, sort_keys=True) + "\n")
        os.replace(tmp, p)


def submit_check(spec, force=False):
    git_ = submit_lint.Git(REPO)
    commit = str((spec.get("source") or {}).get("commit", ""))
    if commit and git_.blob(commit, "") is None and (spec.get("source") or {}).get("branch"):
        gfetch(spec["source"]["branch"], timeout=300)
    return submit_lint.check(spec, git_, util_db(), force=force)


BENCH_PATH_RE = re.compile(r"(?<![\w./$}{-])((?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+\.[A-Za-z0-9]+)\b")
BENCH_SCRIPT_RE = re.compile(r"[\w./-]+\.(?:sh|py|tcl)\b")


def bench_missing_paths(spec, git_=None):
    """drive-0212 2026-10-09: repo files a bench needs that the job's source sync would not carry (it syncs
    source.paths, default tools rtl physical Makefile, + extra_paths).  pi-ta15prod-c7c53c4c2-*: bench.sh read
    tests/rtl/tb_hbm_production_clock_control.sv -> rc=2 'No such file' after a full route.  Scans the bench commands
    and the scripts they call (one level, at the source commit) for literal relative paths that exist at the commit.
    Returns the sorted parent directories to add to source.extra_paths."""
    src = spec.get("source") or {}
    commit = str(src.get("commit", ""))
    benches = ((spec.get("stages") or {}).get("bench") or [])
    if not commit or not benches:
        return []
    git_ = git_ or submit_lint.Git(REPO)
    synced = [str(x).rstrip("/") for x in list(src.get("paths", DEFAULT_SRC_PATHS)) + list(src.get("extra_paths", []))]

    def covered(path):
        return any(path == x or path.startswith(x + "/") for x in synced)

    texts = []
    for b in benches:
        cmd = b.get("cmd") or ""
        texts.append(cmd)
        for sc in sorted(set(BENCH_SCRIPT_RE.findall(cmd))):
            body = git_.show(commit, sc.lstrip("./"))
            if body:
                texts.append(body)
    need = set()
    for t in texts:
        for path in BENCH_PATH_RE.findall(t):
            path = path.lstrip("./") if path.startswith("./") else path
            if path.startswith("/") or covered(path) or ".." in path.split("/"):
                continue
            if git_.blob(commit, path) is not None:
                need.add(path.rsplit("/", 1)[0])
    return sorted(need)


def bench_paths_at_submit(j):
    """intake: add the directories the benches need to source.extra_paths (recorded in an event)"""
    try:
        need = bench_missing_paths(j["spec"])
    except Exception as ex:  # noqa: BLE001  (never block intake on the scan itself)
        event(j, f"bench path scan skipped: {type(ex).__name__}: {str(ex)[:200]}")
        return
    if need:
        j.setdefault("spec_submitted", json.loads(json.dumps(j["spec"])))
        src = j["spec"]["source"]
        src["extra_paths"] = list(src.get("extra_paths", [])) + need
        event(j, f"bench needs repo paths outside the source sync: added {need} to source.extra_paths")


def lint_at_submit(j):
    """run the submit lint on a freshly ingested QUEUED job: may add the pin spread or REFUSE it"""
    try:
        res = submit_check(j["spec"])
    except Exception as ex:  # noqa: BLE001  (never block intake on the estimate itself)
        event(j, f"submit lint skipped: {type(ex).__name__}: {str(ex)[:200]}")
        return
    v = res["verdict"]
    if v == "SKIP":
        return
    if v == "PASS":
        event(j, f"submit lint PASS (estimate {res.get('est')} b/um, limit {res.get('limit')}"
                 + (f", util {res['util_est']['util']:.1%}" if res.get("util_est") else "") + ")"
                 + (f"; {res['rtl_boundary']['verdict']} {res['rtl_boundary']['message'][:400]}" if res.get("rtl_boundary") else ""))
    elif v == "FIX":
        j["spec_submitted"] = j["spec"]
        j["spec"] = submit_lint.apply_fix(j["spec"], res, now_iso())
        event(j, f"submit lint FIX {res['fix']}: {res['message'][:500]}; settings added to the route_master stage "
                 f"commands (spec.submit_lint)")
        ledger(j, f"SUBMIT_LINT {res['fix']} applied: {res['message'][:300]}")
    elif v == "REFUSE":
        j["status"] = "REFUSED"
        kind = "RTL_BOUNDARY" if (res.get("rtl_boundary") or {}).get("verdict") == "REFUSE" else "FLOORPLAN_MARGIN"
        j["reason"] = f"SUBMIT_LINT {kind}: {res['message']}"[:1500]
        j["submit_lint"] = res
        event(j, j["reason"])
        ledger(j, f"REFUSED at submit (no compute spent): {j['reason'][:400]}")


def ingest():
    try:
        gfetch("main", timeout=300)
    except subprocess.TimeoutExpired:
        pass
    keys = route_keys()
    for origin, spec in load_sources():
        name = spec.get("name") or Path(origin.split(":")[-1]).stem
        policy_path = STATE / 'main_publish_owner.json'
        policy = json.loads(policy_path.read_text()) if policy_path.exists() else {}
        if any(str(name).startswith(prefix) for prefix in policy.get('retired_job_prefixes', [])):
            archive = STATE / 'retired_sources'
            archive.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()
            retired = archive / (str(name) + '-' + digest[:12] + '.json')
            if not retired.exists():
                retired.write_text(json.dumps(dict(at=now_iso(), origin=origin, spec=spec,
                    reason=policy.get('retired_scope_reason', 'Owner retired scope')), indent=1) + '\n')
            continue
        if spec.get("enabled") is False:
            continue
        p = jpath(name) if NAME_RE.match(str(name)) else None
        if p is not None and p.exists():
            j = load_job(name)
            frozen = {k: v for k, v in j.get("spec_submitted", j["spec"]).items()}
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
            if route_key_full(keys, key, name):
                j["status"] = "REFUSED"
                j["reason"] = f"{MAX_ROUTES_PER_KEY} routes per source commit: {key} already routed by jobs {keys[key]}"
                event(j, j["reason"])
                ledger(j, f"REFUSED: {j['reason']}")
            else:
                event(j, f"ingested from {origin}")
                lint_at_submit(j)
                if j["status"] == "QUEUED":
                    bench_paths_at_submit(j)
        save_job(j)


# --------------------------------------------------------------------------------------------- host capacity
# ADMIT-PAUSE (drive-resume 2026-10-09): a host's own admission gate (/srv/opentallas-scratch/admit.sh, used inside many
# route recipes) refuses every new job while admit.pause_new.json exists (owner, EPYC2 00:25 memory pressure).  The loop
# did not read it: it kept launching onto EPYC2, the recipe's admit.sh waited forever with 0 CPU and no writes, and
# stuckscan killed the "hung" stage 51 min later (hbm_sfu_lane_rstr x2).  The loop now treats the file as "host paused".
ADMIT_PAUSE = "/srv/opentallas-scratch/admit.pause_new.json"
# STOPPED-WAITERS (drive-resume 2026-10-09): an admission waiter SIGSTOPped by a paused_waiters file (EPYC2 pid 430473,
# state T from 00:26 to 07:00) never resumes on its own; every probe lists stopped (state T) admit.sh / admit_core.py
# processes, logs them once per pid and keeps STATE/stopped_waiters.json current (one row per host).
STOPPED_PROBE = ("ps -eo pid=,stat=,etimes=,args= | awk '$2 ~ /^T/ && /admit(_core)?\\.(sh|py)/ "
                 "{printf \"OT_STOPPED_WAITER %s %s %ss \", $1, $2, $3; for (i = 4; i <= NF && i < 12; i++) printf \"%s \", $i; print \"\"}'")
STOPPED_JSON = STATE / "stopped_waiters.json"
_stopped_seen = set()


def report_stopped_waiters(host, rows):
    """log each stopped admission waiter once (per host/pid) and record the host's current list"""
    for r in rows:
        k = (host, r.split()[0])
        if k not in _stopped_seen:
            _stopped_seen.add(k)
            log(f"STOPPED ADMISSION WAITER on {host}: {r[:240]} (state T: SIGSTOPped, it will never admit; "
                f"resume with kill -CONT or remove it)")
    try:
        cur = json.loads(STOPPED_JSON.read_text()) if STOPPED_JSON.exists() else {}
        cur[host] = dict(at=now_iso(), waiters=rows)
        STOPPED_JSON.write_text(json.dumps(cur, indent=1))
    except Exception:  # noqa: BLE001
        pass


PAUSE_PROBE = f"[ -f {ADMIT_PAUSE} ] && echo OT_ADMIT_PAUSED $(head -c 200 {ADMIT_PAUSE} | tr '\\n' ' '); true"


class Fleet:
    def __init__(self):
        self.pending = {}      # host -> [(t, threads, ram)]
        self.probe_cache = {}
        self.tool_cache = {}
        self.own_running = {}    # host -> declared threads of this loop's running stages
        self.last_good = {}      # host -> (t, last successful probe): used for PROBE_LAST_GOOD_S when a probe fails
        self.tool_good = {}      # host -> (t, last successful toolchain probe)

    def probe(self, host):
        c = self.probe_cache.get(host)
        if c and time.time() - c[0] < 45:
            return c[1]
        info = self._probe_once(host)
        for delay in (2, 5):            # a busy / just-expired ssh master is not an unreachable host (20:33)
            if info is not None:
                break
            time.sleep(delay)
            info = self._probe_once(host)
        if info is None:
            good = self.last_good.get(host)
            if good and time.time() - good[0] < PROBE_LAST_GOOD_S:
                info = dict(good[1], stale_s=round(time.time() - good[0]))
        else:
            self.last_good[host] = (time.time(), info)
        self.probe_cache[host] = (time.time(), info)
        return info

    def _probe_once(self, host):
        cfg = host_cfg(host)
        roots = disk_roots(cfg)
        external = cfg.get("external_jobs", [])
        reservation_probe = ""
        if external:
            probe = """import json, pathlib
jobs = json.loads(__JOBS__)
rows = []
for j in jobs:
    p = pathlib.Path('/proc') / str(j['pid'])
    try:
        cmd = (p / 'cmdline').read_bytes().replace(b'\\0', b' ').decode(errors='replace')
        if j['command_match'] not in cmd:
            continue
        rss = next(int(x.split()[1]) for x in (p / 'status').read_text().splitlines() if x.startswith('VmRSS:')) / 1048576
        rows.append(dict(name=j['name'], pid=j['pid'], rss_gb=rss, peak_ram_gb=j['peak_ram_gb'], remaining_gb=max(0, j['peak_ram_gb']-rss)))
    except (OSError, StopIteration, ValueError):
        continue
print('OT_EXTERNAL_JOBS ' + json.dumps(rows))
""".replace("__JOBS__", repr(json.dumps(external)))
            reservation_probe = "; python3 -c " + shlex.quote(probe)
        dfs = "".join(f"; df -P -BG {shlex.quote(p)} | awk 'NR==2{{gsub(\"G\",\"\",$4);print $4}}'" for p in roots)
        r = ssh(host, f"""cat /proc/loadavg; awk '/MemAvailable/{{print int($2/1048576)}}' /proc/meminfo
mkdir -p {cfg['base']} && df -P -BG {cfg['base']} | awk 'NR==2{{gsub("G","",$4);print $4}}'{dfs}{reservation_probe}
{PAUSE_PROBE}; {STOPPED_PROBE}""", timeout=40)
        if r.returncode:
            info = None
        else:
            v = r.stdout.split()
            info = dict(load1=float(v[0]), mem_gb=int(v[5]), disk_gb=int(v[6]),
                        roots_gb=dict(zip(roots, (int(x) for x in v[7:7 + len(roots)]))))
            external_line = next((x[len("OT_EXTERNAL_JOBS "):] for x in r.stdout.splitlines() if x.startswith("OT_EXTERNAL_JOBS ")), None)
            if external and external_line is None:
                return None  # cannot admit without measuring the declared live reservations
            info["external_jobs"] = json.loads(external_line) if external_line else []
            info["external_remaining_gb"] = sum(x["remaining_gb"] for x in info["external_jobs"])
            paused = next((x[len("OT_ADMIT_PAUSED"):].strip() for x in r.stdout.splitlines() if x.startswith("OT_ADMIT_PAUSED")), None)
            if paused is not None:
                info["admit_paused"] = paused[:200] or "admit.pause_new.json"
            stopped = [x[len("OT_STOPPED_WAITER "):].strip() for x in r.stdout.splitlines() if x.startswith("OT_STOPPED_WAITER ")]
            if stopped:
                info["stopped_waiters"] = stopped
                report_stopped_waiters(host, stopped)
        return info

    def own_pending(self, host, job=None):
        t0 = time.time() - PENDING_WINDOW_S
        self.pending[host] = [p for p in self.pending.get(host, []) if p[0] >= t0]
        # RAM of a launch is held back 3 min (a route reaches its memory over hours).  2026-10-08: a job's own claim
        # (taken when it was chosen/moved) must not count against its own launch -- it made every moved job miss the
        # host it was moved to, move again and re-claim, which held 368 GB of EPYC2 idle while 30 jobs waited
        tr = time.time() - PENDING_RAM_WINDOW_S
        other = [p for p in self.pending[host] if job is None or len(p) < 4 or p[3] != job]
        return sum(p[1] for p in other), sum(p[2] for p in other if p[0] >= tr)

    def fits(self, host, threads, ram, job=None):
        with FLEET_LOCK:
            return self._fits(host, threads, ram, job)

    def _fits(self, host, threads, ram, job=None):
        cfg = host_cfg(host)
        if threads > cfg["max_job_threads"] or ram > cfg["max_job_ram_gb"]:
            return False, f"job {threads} thr / {ram} GB exceeds {cfg['label']} per-job limit"
        info = self.probe(host)
        if info is None:
            return False, f"{cfg['label']} unreachable"
        if info.get("admit_paused"):
            return False, f"{cfg['label']} admission paused ({ADMIT_PAUSE}: {info['admit_paused']})"
        pt, pr = self.own_pending(host, job)
        # OWNER DECISION (2026-10-07 20:10, supersedes the 19:31 1.1 x nproc cap): MEMORY is the only admission limit on
        # the remote hosts -- CPU oversubscription is allowed (jobs wait on reads / run serial phases).  localhost keeps
        # its own guard below (max_loop_threads, min_free_ram_gb) so it stays responsive.
        # OWNER 2026-10-09: NEVER reserve memory for future growth (no reserve_ram_gb, no external-job remaining-peak
        # reservations) -- admit on measured MemAvailable minus own launches of the last few minutes only.
        # drive-resume 2026-10-09 (coordinator, owner rule): admit iff measured MemAvailable >= the job's own request + a
        # fixed safety of ADMIT_SAFETY_GB (16).  The earlier check subtracted the declared peaks of every launch AND every
        # host claim of the last 3 min (waiting jobs re-claim each tick, so it never expired: "EPYC4 MemAvailable 316-224
        # < 40+57") and added 5 % of host RAM -- both reservations for future growth.  Neither is subtracted any more.
        head = min(ADMIT_SAFETY_GB, cfg.get("min_free_ram_gb", ADMIT_SAFETY_GB))
        if cfg.get("max_loop_threads") is not None:      # localhost: loop jobs in total, so ssh stays responsive
            used = self.own_running.get(host, 0) + pt
            if used + threads > cfg["max_loop_threads"]:
                return False, f"{cfg['label']} loop threads {used}+{threads} > {cfg['max_loop_threads']}"
        if ram <= 2:          # 2026-10-08: collect/export copy files; host-local, so they cannot move -- a 16 GB headroom
            head = min(head, 2)   # left PVE1 jobs stuck at collect for 20 min with 13 GB free
        if info["mem_gb"] < ram + head:
            return False, f"{cfg['label']} MemAvailable {info['mem_gb']} GB < {ram}+{head:.0f}"
        # drive-0849 2026-10-09 (coordinator): a light stage (bench / collect / export: ram <= LIGHT_STAGE_RAM_GB) writes a few
        # GB at most; the 200 GB run-root floor held EPYC4's benches + collects for > 1 h at 192-197 GB free while 250 GB
        # of RAM sat idle.  Light stages keep only LIGHT_DISK_FLOOR_GB; routes / calibrates / ECOs keep the full floor.
        dfloor = cfg["min_free_disk_gb"] if ram > LIGHT_STAGE_RAM_GB else min(cfg["min_free_disk_gb"], LIGHT_DISK_FLOOR_GB)
        if info["disk_gb"] < dfloor:
            return False, f"{cfg['label']} run root has {info['disk_gb']} GB free < {dfloor}"
        for path, floor in disk_roots(cfg).items():   # every other root the host's jobs write (docker /, /tmp, ...)
            if ram <= LIGHT_STAGE_RAM_GB:
                floor = min(floor, LIGHT_DISK_FLOOR_GB)
            free = info.get("roots_gb", {}).get(path)
            if free is not None and free < floor:
                return False, f"{cfg['label']} {path} has {free} GB free < {floor}"
        return True, "ok"

    def launched(self, host, threads, ram, job=None):
        with FLEET_LOCK:
            self._launched(host, threads, ram, job)

    def _launched(self, host, threads, ram, job=None):
        if job is not None:   # one claim per job: a launch or a new host choice replaces its earlier claims
            for hh in self.pending:
                self.pending[hh] = [p for p in self.pending[hh] if len(p) < 4 or p[3] != job]
        self.pending.setdefault(host, []).append((time.time(), threads, ram, job))
        self.probe_cache.pop(host, None)

    def choose(self, spec, exclude=()):
        with FLEET_LOCK:
            return self._choose(spec, exclude)

    def toolchain(self, host):
        """ORFS image digests + bench tool versions of a host (cached 1 h)."""
        c = self.tool_cache.get(host)
        if c and time.time() - c[0] < (3600 if c[1] else 15):
            return c[1]
        info = None
        for delay in (0, 5, 15):
            if delay:
                time.sleep(delay)
            try:
                r = ssh(host, TOOLPROBE, timeout=90)
            except subprocess.TimeoutExpired:
                # gaps-design 2026-10-08: an unreachable host (PVE1 'No route to host' 02:1x PT) raised out of tick()
                # and crash-looped the daemon; a timed-out probe is a failed probe (last-good toolchain applies)
                break
            if r.returncode == 0:
                info = dict(l.split("=", 1) for l in r.stdout.splitlines() if "=" in l)
                break
        if info is None:   # a failed probe keeps the last good toolchain (6 h) instead of "no compatible host"
            good = self.tool_good.get(host)
            if good and time.time() - good[0] < TOOL_LAST_GOOD_S:
                info = good[1]
        else:
            self.tool_good[host] = (time.time(), info)
        self.tool_cache[host] = (time.time(), info)
        return info

    def compatible(self, host, spec):
        """host capability table (hosts.json caps) covers every stage's needs, and the ORFS image digest matches the
        reference host's (plus asap7lock when the job names it)"""
        cfg = host_cfg(host)
        # bench_offload (OWNER 2026-10-07: use localhost for ORFS-only route/calibrate): the job's benches run on another
        # host with the bench tools (bench_track -> offload_bench_location), so only the main track's needs count here
        if not job_needs(spec, benches=not cfg.get("bench_offload")) <= set(cfg.get("caps", [])):
            return False
        ref, mine = self.toolchain(TOOL_REF_HOST), self.toolchain(host)
        if not ref or not mine:
            return False
        if not all(mine.get(k) == ref.get(k) for k in job_tools(spec) if k.startswith("img_")):
            return False
        if is_local(host) and bare_image_ids(spec):
            return False     # a docker reference by bare image ID does not exist in the localhost store (see LOCAL_ORFS_REF)
        return True

    def _choose(self, spec, exclude=()):
        threads, ram = spec.get("threads", 16), spec.get("peak_ram_gb", 32)
        allh = [h["name"] for h in hosts_table()]
        pref = set(spec.get("hosts") or [])
        # the job's hosts list is a PREFERENCE (coordinator 2026-10-06 21:15); caps/toolchain/per-job limits still apply
        if spec.get("host_require"):          # smoke tests / pinned runs: only these hosts
            allh = [h for h in allh if h in spec["host_require"]]
        # a host marked smoke_only (hosts.json) admits only smoke-test jobs (spec "smoke": true) until it is re-enabled
        allh = [h for h in allh if not host_cfg(h).get("smoke_only") or spec.get("smoke")]
        order = [h for h in allh if h not in exclude and self.compatible(h, spec)]

        def score(h):
            """higher = better: free cores and free RAM after this job, both as fractions of the host; spillover-only
            hosts (EPYC3, die-top) rank after every other host; listed hosts get a small preference"""
            info, cfg = self.probe(h), host_cfg(h)
            if info is None:
                return -9e9
            pt, pr = self.own_pending(h)
            fc = (cfg["cap"] - info["load1"] - pt - threads) / cfg["cap"]
            fr = (info["mem_gb"] - pr - ram) / cfg.get("ram_gb", 1133)
            # OWNER 2026-10-08: memory is the only ADMISSION limit; ranking sends a job where it runs fastest among hosts
            # that fit -- free CPU weighs 0.5 (was 0.1: AGIdock sat at load 15/64 with 67 GB free while EPYCs ran 4x over)
            return fr + 0.5 * max(fc, -1.0) + (0.02 if h in pref else 0) - (10 if cfg.get("spillover_only") else 0)
        order.sort(key=score, reverse=True)
        why = []
        for h in order:
            ok, msg = self.fits(h, threads, ram)
            if ok:
                return h, None
            why.append(msg)
        return None, "; ".join(why) or "no compatible host (capabilities/image probe unavailable or mismatched)"


TOOL_REF_HOST = "ot-epyc3"
PROBE_LAST_GOOD_S = 300     # memory/disk/load: a failed probe reuses a good one at most 5 min old
TOOL_LAST_GOOD_S = 6 * 3600  # image digests / tool versions change only on a deliberate host update
# LOCALHOST IMAGE (2026-10-07): the fleet image loaded into localhost's overlay2 docker store has another image ID
# (af971398) than in the fleet's containerd stores (16470cea), so a recipe pinning the BARE ID sha256:16470cea... fails
# there with exit 125 (dsrom_softmax_safe_exprc2_09d4d345e).  The registry-digest reference resolves on every host:
# localhost stages export it as OPENTALLAS_ORFS_IMAGE, and jobs whose recipes hard-code a bare ID stay on the fleet.
LOCAL_ORFS_REF = "openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29"
_BARE_ID_CACHE = {}


def bare_image_ids(spec):
    """bare docker image IDs (sha256:<64 hex> not preceded by name@) in the job's stage commands or the scripts they
    name at the job's commit, except an overridable ${OPENTALLAS_ORFS_IMAGE:-...} default"""
    commit = (spec.get("source") or {}).get("commit", "")
    text = json.dumps(spec.get("stages", {}))
    key = (commit, text)
    if key in _BARE_ID_CACHE:
        return _BARE_ID_CACHE[key]
    blobs = [text]
    for path in sorted(set(re.findall(r"((?:physical|tools)/[\w./-]+\.(?:sh|py|tcl))", text))):
        r = sh(["git", "-C", str(REPO), "show", f"{commit}:{path}"], timeout=60)
        if r.returncode == 0:
            blobs.append(r.stdout)
    found = set()
    for b in blobs:
        b = re.sub(r"OPENTALLAS_ORFS_IMAGE:-sha256:[0-9a-f]{64}", "", b)
        found |= set(re.findall(r"(?<![@\w])sha256:[0-9a-f]{64}", b))
    _BARE_ID_CACHE[key] = sorted(found)
    return _BARE_ID_CACHE[key]
SMALL_JOB_GB = 40
# image identity = its registry digest when it has one: the same image loaded into a different docker store reports a
# different .Id (localhost overlay2 af971398 vs fleet containerd 16470cea, both openroad/orfs@sha256:16470cea)
TOOLPROBE = r"""
echo img_latest=$(docker image inspect openroad/orfs:latest --format '{{if .RepoDigests}}{{index .RepoDigests 0}}{{else}}{{.Id}}{{end}}' 2>/dev/null)
echo img_asap7lock=$(docker image inspect openroad/orfs:asap7lock --format '{{if .RepoDigests}}{{index .RepoDigests 0}}{{else}}{{.Id}}{{end}}' 2>/dev/null)
echo iverilog=$(iverilog -V 2>/dev/null | head -1)
echo verilator=$(verilator --version 2>/dev/null | head -1)
echo yosys=$(yosys -V 2>/dev/null | head -1)
"""


def bench_needs(spec):
    return set().union(*(set(b.get("needs", DEFAULT_NEEDS["bench"])) for b in spec.get("stages", {}).get("bench", [])))


def job_needs(spec, benches=True):
    """union of the stage needs of a job (all its stages run on one host); a stage may set "needs": [...].
    benches=False: the main track only (a bench_offload host runs the benches on another host)"""
    st = spec.get("stages", {})
    need = set()
    for b in st.get("bench", []) if benches else ():
        need |= set(b.get("needs", DEFAULT_NEEDS["bench"]))
    for k in ("calibrate", "route", "signoff", "collect", "export"):
        x = st.get(k) or {}
        if x.get("cmd") and x.get("enabled", True) is not False:
            need |= set(x.get("needs", DEFAULT_NEEDS[k]))
    return need | set(DEFAULT_NEEDS["summary"])


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


TT_OVERLAY_REL = "python3 tools/closure_loop/tt_overlay.py "
TT_OVERLAY_FLEET = ("/srv/opentallas-scratch/claude/ttbatch/26f14af32/tools/closure_loop/tt_overlay.py",
                    "/home/ubuntu/closure-loop-local/ttbatch/26f14af32/tools/closure_loop/tt_overlay.py")


def tt_overlay_fallback(cmd):
    """2026-10-08: specs that call the snapshot's own tools/closure_loop/tt_overlay.py on a commit predating it (26f14af32;
    qfd_io_emb_tap-4b111850att, qfd_sp_*-e0370c82ctt: 'can't open file ... tt_overlay.py') run the fleet's tt-batch
    overlay copy (kept at main on every host) instead; a snapshot that carries the file keeps its own."""
    if TT_OVERLAY_REL not in cmd:
        return cmd
    pick = ("python3 \"$(test -f tools/closure_loop/tt_overlay.py && echo tools/closure_loop/tt_overlay.py || "
            f"ls -d {' '.join(TT_OVERLAY_FLEET)} 2>/dev/null | head -1)\" ")
    return cmd.replace(TT_OVERLAY_REL, pick)


def subst(text, j):
    m = dict(RUN=j["run"], SRC=j.get("stage_source", f"{j['run']}/src"), CL=f"{j['run']}/cl", HOST=j["host"], NAME=label(j["name"]),
             LABEL=label(j["name"]), RAW_NAME=j["name"],
             BLOCK=j["spec"]["block"], COMMIT=j["spec"]["source"]["commit"], THREADS=str(j["spec"].get("threads", 16)))
    for k, v in m.items():
        text = text.replace("{" + k + "}", v)
    return text


# ------------------------------------------------------------------------------------------------ budget sheets
BUDGET_SHEETS = "results/rtl/budgets_20261006/sheets"
SDC_GEN_REF = os.environ.get("CL_SDC_GEN_REF", "origin/main")   # make_block_sdc.py always from main (stale-sheets 10-08)
# sign-off post-SDC must carry the sheet latency on vclk ONLY: latency on {<clk> vclk} re-idealises the real clock
IDEAL_SIGNOFF_RE = re.compile(r"set_clock_latency\s+[-0-9.]+\s+\[get_clocks\s+\{\s*(?!vclk\b)\S+\s+vclk\s*\}\]")


def budget_files(bud, check_only=False, insertion_override=None):
    """budget SDCs of the job's master from its sheet at sheets_ref (default origin/main; tools/budgets/make_block_sdc.py
    of the same ref): {name: text} + the sheet.  The SDC is generated HERE (localhost, from the published sheet), so
    every job uses the same sheet whatever its own branch carries."""
    ref = bud.get("sheets_ref", "origin/main")
    with tempfile.TemporaryDirectory() as td:
        # the SHEET is pinned at sheets_ref; the GENERATOR is always SDC_GEN_REF (main).  A job pinned to a ref older
        # than the 2026-10-07 make_block_sdc fix otherwise put the sheet latency on the real clock in budget_signoff.sdc,
        # read after set_propagated_clock: an IDEAL core clock at sign-off (drive-1613: swiglu FF -147.68 fake I2R hold).
        arch = sh(["bash", "-c", f"git -C {REPO} archive {ref} {BUDGET_SHEETS}/{bud['master']}.json | tar -x -C {td} && "
                   f"git -C {REPO} archive {SDC_GEN_REF} tools/budgets | tar -x -C {td}"], timeout=300)
        sheet = Path(td) / BUDGET_SHEETS / f"{bud['master']}.json"
        if arch.returncode or not sheet.exists():
            raise ValueError(f"no budget sheet {bud['master']} at {ref} ({arch.stderr[-300:]})")
        if check_only:
            return {}
        if insertion_override:   # measured insertion below the sheet target: SDC from it + the sheet's per-edge budgets
            sj = json.loads(sheet.read_text())
            sj["clock"]["internal_insertion"].update(insertion_override)
            sheet.write_text(json.dumps(sj, indent=1))
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
        bad = IDEAL_SIGNOFF_RE.search(out["budget_signoff.sdc"])
        if bad:
            raise ValueError(f"budget_signoff.sdc puts the sheet latency on the real clock ({bad.group(0)}): ideal-clock "
                             f"sign-off; generator {SDC_GEN_REF} is older than the 2026-10-07 make_block_sdc fix")
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
    env = j["calibration"]["env"]
    m = float(env["CK_SS_MEAN"])
    why = []
    # coordinator 2026-10-06: only an insertion ABOVE the block's target stops the job; one at or below the target is
    # accepted and the budget SDCs are regenerated from the MEASURED insertion (+ the sheet's per-edge budgets)
    preserve_sheet = bud.get("preserve_full_sheet", False)
    if preserve_sheet:
        for corner in ("SS", "FF"):
            if env[f"CK_{corner}_MAX"] > ins[f"target_{corner.lower()}"]:
                why.append(f"audited full-sheet {corner} boundary maximum {env[f'CK_{corner}_MAX']} "
                           f"exceeds approved {ins[f'target_{corner.lower()}']}; re-plan required")
    if m > ins["target_ss"]:
        why.append(f"measured SS insertion {m:g} exceeds the block insertion TARGET {ins['target_ss']:g} by "
                   f"{m - ins['target_ss']:+.0f} ps (sheet {ins['ss']:g}, {ins['grade']})")
    if why:
        j["budget"]["check"] = dict(measured_ss=m, ok=False, reasons=why)
        return "; ".join(why)
    ov = dict(ss=round(m), ff=round(float(env["CK_FF_MEAN"])), ss_min=round(float(env["CK_SS_MIN"])),
              ss_max=round(float(env["CK_SS_MAX"])), ff_min=round(float(env["CK_FF_MIN"])), ff_max=round(float(env["CK_FF_MAX"])),
              grade="measured", source=f"closure-loop calibrate {j['name']} ({j['host']}:{j['run']})", over_target=False)
    files = budget_files(active_budget(j["spec"]), insertion_override=None if preserve_sheet else ov)
    if preserve_sheet:
        import hashlib
        if hashlib.sha256(files["budget_sheet.json"].encode()).hexdigest() != bud["sheet_sha256"]:
            raise ValueError("audited full budget sheet digest changed")
    for fn, text in files.items():
        if not fn.startswith("_"):
            ssh(j["host"], f"cat > {j['run']}/cl/{fn}", input=text, timeout=60, check=True)
    acc = dict(accepted=("audited complete sheet retained; boundary maxima within approved SS/FF targets"
                         if preserve_sheet else "measured insertion <= sheet target: budget SDCs regenerated from it"), sheet_ss=ins["ss"],
               sheet_grade=ins["grade"], target_ss=ins["target_ss"], measured=ov, sheets_ref=files["_ref"])
    py = ("import json,sys; p=sys.argv[1]; d=json.load(open(p)); d['budget_accepted']=json.loads(sys.argv[2]); "
          "json.dump(d,open(p,'w'),indent=1)")
    ssh(j["host"], f"python3 -c {shlex.quote(py)} {j['run']}/cl/calib.json {shlex.quote(json.dumps(acc))}", timeout=60)
    j["budget"]["insertion_used"] = ins if preserve_sheet else ov
    j["budget"]["check"] = dict(measured_ss=m, ok=True, reasons=[], accepted=acc["accepted"])
    return None


# ---- variant-keyed insertion (bf-insertion 2026-10-08): measured_insertion.json was keyed per BLOCK, and variants of one
# block differ wildly (bfh_halfphl_a730 routed on bfh_recutcgl50's SS 1169 / FF 714; the half-rate tree measured
# 1546 / 875).  A route may start on an ASSUMED insertion only when it was measured on the SAME variant: same block,
# same recipe script and the same insertion-relevant build options in the stage cmd (VAR=value assignments such as
# BF_VAR / OT_CGL_FRAC / OT_MULTI_VT / OT_CTS_FIX_HOOKS / corner overrides, --param K=V, other --flags).  Hold-repair
# knobs, run paths and labels are not part of the key.  No same-variant value -> sequential CTS-only calibrate.
VKEY_IGNORE_VARS = {"OUT", "SRC", "TTB", "OT_TTB_CORNER_MARK", "OT_MM_FF_SDC", "CL_LABEL_SUFFIX", "CL_STOP_AFTER"}
VKEY_IGNORE_FLAGS = {"--hold-margin-ns", "--pnr-stop-after", "--hold-corners", "--hm-guard"}


def variant_key(spec):
    """block + recipe + insertion-relevant options of the route (else calibrate) stage cmd (see above)"""
    stages = spec.get("stages") if isinstance(spec.get("stages"), dict) else {}
    cmd = ""
    for k in ("route", "calibrate"):
        st = stages.get(k)
        if isinstance(st, dict) and st.get("cmd"):
            cmd = st["cmd"]
            break
    toks = []
    for m in re.finditer(r"(?<![\w$])([A-Z][A-Z0-9_]*)=('[^']*'|\"[^\"]*\"|\S*)", cmd):
        if m.group(1) not in VKEY_IGNORE_VARS and not m.group(2).startswith("$("):
            if not re.search(r"--param\s+$", cmd[:m.start()]):
                toks.append(f"{m.group(1)}={m.group(2).rstrip(';&|').strip(chr(39) + chr(34))}")
    words = re.findall(r"\S+", cmd)
    skip = False
    for i, w in enumerate(words):
        if skip:
            skip = False
            continue
        if not w.startswith("--"):
            continue
        nxt = words[i + 1] if i + 1 < len(words) else ""
        has_val = "=" not in w and bool(re.match(r"^[\w.:,+=-]+$", nxt)) and not nxt.startswith("-")
        skip = has_val
        if w.split("=")[0] in VKEY_IGNORE_FLAGS:
            continue
        toks.append(f"{w} {nxt}" if has_val else w)
    scripts = sorted(x for x in set(re.findall(r"[\w./-]+\.(?:sh|py)\b", cmd)) if not x.endswith("tt_overlay.py"))
    return f"{spec.get('block')}|{','.join(scripts)}|{' '.join(sorted(set(toks)))}"


def _entry_variant(m):
    """the variant key of a measured_insertion.json entry: stored, else derived from the measuring job's JSON"""
    if not m:
        return None
    if m.get("variant"):
        return m["variant"]
    try:
        return variant_key(load_job(m["job"])["spec"])
    except Exception:  # noqa: BLE001
        return None


def same_variant_insertion(j):
    """(entry, why_not): the measured_insertion.json entry measured on THIS job's variant, else (None, reason)"""
    vk = variant_key(j["spec"])
    try:
        d = json.loads((STATE / "measured_insertion.json").read_text())
    except (OSError, ValueError):
        return None, "no measured_insertion.json"
    m = (d.get("variants") or {}).get(vk)
    if m:
        return m, None
    b = (d.get("blocks") or {}).get(j["spec"].get("block"))
    if b and _entry_variant(b) == vk:
        return b, None
    return None, (f"block value from another variant ({b.get('job')})" if b else "block never measured")


def _store_variant(d, j, e):
    vk = variant_key(j["spec"])
    e["variant"] = vk
    d.setdefault("variants", {})[vk] = dict(e, block=j["spec"].get("block"))


def _cal_entry(j, measured_at):
    c = j.get("calibration") or {}
    e = c.get("env") or {}
    p_ss = "CK_SSLIB_" if "CK_SSLIB_MEAN" in e else "CK_SS_"     # CK_SS_* is the route-corner value under CALIB-CORNER
    if not all(k in e for k in (p_ss + "MEAN", p_ss + "MIN", p_ss + "MAX", "CK_FF_MEAN", "CK_FF_MIN", "CK_FF_MAX")):
        return None
    return dict(
        job=j["name"], source_commit=j.get("commit_full"), host=j.get("host"), run=j.get("run"), clock=c.get("clock"),
        parasitics=c.get("parasitics"), measured_at=measured_at,
        ss=dict(mean=e[p_ss + "MEAN"], min=e[p_ss + "MIN"], max=e[p_ss + "MAX"]),
        ff=dict(mean=e["CK_FF_MEAN"], min=e["CK_FF_MIN"], max=e["CK_FF_MAX"]),
        **({"tt": dict(mean=e["CK_TT_MEAN"], min=e["CK_TT_MIN"], max=e["CK_TT_MAX"])} if "CK_TT_MEAN" in e else {}),
        route_ref=e.get("CK_ROUTE_REF", "SS"),
        boundary_n=(c.get("ss") or {}).get("boundary", {}) and c["ss"]["boundary"].get("n"),
        budget=(j.get("budget") or {}).get("check"))


_CAL_DONE = re.compile(r"^(\S+) (calibrate done \(rc=0\)|parallel calibrate: measured )")


def backfill_variants():
    """bf-insertion 2026-10-08: measurements taken before the variant table existed (only blocks{} kept the LAST one per
    block) are added to variants{} from every job's calibration, newest measurement per variant; existing variant
    entries are never replaced.  Without it a re-route of e.g. bfh2_recut_lvt (measured SS 951 / FF 556) could not
    find its own variant's value and would calibrate again.  Returns the number of variants added."""
    best = {}
    for j in all_jobs():
        try:
            t = max((m.group(1) for m in map(_CAL_DONE.match, j.get("events") or []) if m), default=None)
            if not t or not j.get("calibration") or not j.get("spec", {}).get("block"):
                continue
            ent = _cal_entry(j, t)
            vk = variant_key(j["spec"])
        except Exception:  # noqa: BLE001
            continue
        if ent and (vk not in best or t > best[vk]["measured_at"]):
            best[vk] = dict(ent, variant=vk, block=j["spec"]["block"], backfilled=True)
    p = STATE / "measured_insertion.json"
    with open(STATE / "measured.lock", "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        d = json.loads(p.read_text()) if p.exists() else {"schema": "opentallas.closure_loop.measured_insertion.v1",
                                                          "blocks": {}}
        v = d.setdefault("variants", {})
        new = {k: e for k, e in best.items() if k not in v}
        if new:
            v.update(new)
            d["updated"] = now_iso()
            p.write_text(json.dumps(d, indent=1) + "\n")
            (STATE / "measured.dirty").write_text(now_iso())
    return len(new)


def record_measured(j):
    """every calibrated block's measured insertion -> STATE/measured_insertion.json (published to main by the daemon
    as results/rtl/budgets_20261006/measured_insertion.json for the die clock plan)"""
    c = j.get("calibration") or {}
    if not c.get("env") or not _cal_entry(j, ""):
        return
    p = STATE / "measured_insertion.json"
    with open(STATE / "measured.lock", "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        d = json.loads(p.read_text()) if p.exists() else {"schema": "opentallas.closure_loop.measured_insertion.v1",
                                                          "blocks": {}}
        d["blocks"][j["spec"]["block"]] = ent = _cal_entry(j, now_iso())
        _store_variant(d, j, ent)
        d["updated"] = now_iso()
        p.write_text(json.dumps(d, indent=1) + "\n")
        (STATE / "measured.dirty").write_text(now_iso())


def claude_owns_main():
    policy = STATE / 'main_publish_owner.json'
    if not policy.exists():
        return False
    try:
        return json.loads(policy.read_text()).get('automatic_main_publish') is False
    except (OSError, ValueError):
        return True  # malformed ownership policy never authorizes a main push


def notify_claude_record(name, branch, commit):
    line = f"{now_iso()} READY {name}: {branch} {commit}; Claude owns main merge.\n"
    root = Path('/home/ubuntu/claude-takeover-20261007')
    root.mkdir(parents=True, exist_ok=True)
    append_locked(root / 'fleet_closure.log', line)
    append_locked(root / 'READY_TO_MERGE.md', '\n- ' + line)


MEASURED_REPO_PATH = "results/rtl/budgets_20261006/measured_insertion.json"


def publish_measured():
    """commit STATE/measured_insertion.json to main (explicit path, sparse scratch worktree); at most every 10 min"""
    dirty = STATE / "measured.dirty"
    if not dirty.exists():
        return
    stamp = STATE / "measured.published"
    if stamp.exists() and time.time() - stamp.stat().st_mtime < 600:
        return
    with PUBLISH_LOCK:
        if claude_owns_main():
            return  # owner consumes durable measured.dirty / measured_insertion.json; no main push
        if (STATE / "main_integration_hold.json").exists():
            return  # central coordinator is integrating; keep all unpublished measurements
        wt = STATE / "git" / "measured-main"
        for attempt in range(3):
            gfetch("main", timeout=600)
            wt_add(wt, "origin/main", ["/" + MEASURED_REPO_PATH])
            (wt / MEASURED_REPO_PATH).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(STATE / "measured_insertion.json", wt / MEASURED_REPO_PATH)
            git("add", "--sparse", "--", MEASURED_REPO_PATH, cwd=wt)
            if not sh(["git", "-C", str(wt), "diff", "--cached", "--name-only"], timeout=60).stdout.strip():
                break
            n = len(json.loads((wt / MEASURED_REPO_PATH).read_text())["blocks"])
            git("-c", "user.name=OpenTallas closure-loop", "-c", "user.email=boj@01.me", "commit", "-q", "-m",
                f"closure-loop: measured block clock insertion ({n} blocks; calibrate CTS-only runs) for the die clock plan\n\n"
                f"Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n", cwd=wt)
            if sh(["git", "-C", str(wt), "push", "-q", "origin", "HEAD:refs/heads/main"], timeout=900).returncode == 0:
                break
        wt_rm(wt)
    dirty.unlink(missing_ok=True)
    stamp.write_text(now_iso())


def checkpoint_location(j):
    """Bind resume work to its actual checkpoint, never merely to synced source."""
    if not j.get("resume"):
        return None
    if j.get("checkpoint_affinity"):
        return j["checkpoint_affinity"]
    resume = j["resume"] if isinstance(j["resume"], dict) else {}
    proof = resume.get("next_stage_dryrun") or {}
    location = dict(host=resume.get("to_host") or proof.get("host") or j.get("host"),
                    run=resume.get("run") or proof.get("run") or j.get("run"))
    if not location["host"] or not location["run"]:
        raise ValueError("checkpoint resume lacks a host/run binding")
    j["checkpoint_affinity"] = location
    return location


def require_checkpoint_location(j):
    location = checkpoint_location(j)
    if location and (j.get("host"), j.get("run")) != (location["host"], location["run"]):
        raise ValueError("checkpoint resume host/run changed without a verified full checkpoint transfer: "
                         f"expected {location['host']}:{location['run']}")
    return location


@contextmanager
def prepared_source_archive(source, commit):
    """Check declared dependencies before remote mutation; yield the exact checked tar."""
    if "required_files" not in source:
        yield None, None
        return
    with tempfile.TemporaryDirectory(prefix="closure-source-") as scratch:
        archive = Path(scratch) / "source.tar"
        receipt = build_archive(REPO, commit, source, archive)
        receipt.pop("archive", None)  # retain hash/inventory, not a transient local path
        yield archive, receipt


# Directories a stage cmd names (OT_CTS_FIX_HOOKS=physical/common_flow/...) that a narrow source.paths list omits:
# the hooks are read from {SRC}, so a spec with paths [tools, rtl, physical/<view>] failed calibrate with
# "OT_CTS_FIX_HOOKS: no such file .../cg_pushdown.tcl" (flow-triage 2026-10-08).
IMPLIED_SRC_DIRS = ["physical/common_flow"]


def implied_src_paths(spec, paths, commit):
    stages = json.dumps(spec.get("stages", {}))
    out = []
    for d in IMPLIED_SRC_DIRS:
        if d not in stages or any(d == p or d.startswith(p.rstrip("/") + "/") for p in paths):
            continue
        if sh(["git", "-C", str(REPO), "cat-file", "-e", f"{commit}:{d}"], timeout=60).returncode == 0:
            out.append(d)
    return out


def sync_source(j):
    require_checkpoint_location(j)
    j["source_synced"] = False
    spec, host = j["spec"], j["host"]
    src = spec["source"]
    gfetch(src["branch"], timeout=600)
    full = git("rev-parse", "--verify", f"{src['commit']}^{{commit}}").stdout.strip()
    anc = sh(["git", "-C", str(REPO), "merge-base", "--is-ancestor", full, f"origin/{src['branch']}"], timeout=120)
    if anc.returncode:   # confirm against a fresh fetch before calling a human: the tracking ref may be stale
        gfetch(src["branch"], timeout=600)
        anc = sh(["git", "-C", str(REPO), "merge-base", "--is-ancestor", full, f"origin/{src['branch']}"],
                 timeout=120)
    if anc.returncode:
        raise ValueError(f"source commit {full[:12]} is not on origin/{src['branch']}")
    j["commit_full"] = full
    paths = list(src.get("paths", DEFAULT_SRC_PATHS)) + list(src.get("extra_paths", []))
    paths += implied_src_paths(spec, paths, full)
    run = j["run"]
    with prepared_source_archive(src, full) as (verified_tar, archive_receipt):
        ssh(host, f"set -e; mkdir -p {run}/src {run}/cl; test ! -e {run}/src/SOURCE_COMMIT || "
                  f"grep -q {full} {run}/src/SOURCE_COMMIT", timeout=60, check=True)
        with transport_command(host) as base:
            if verified_tar is not None:
                # Transfer this exact validated tar, not a second git archive.
                with verified_tar.open("rb") as stream:
                    put = subprocess.run(base + [f"tar -xf - -C {run}/src"], stdin=stream,
                                         capture_output=True, text=True, timeout=1800)
                if put.returncode:
                    raise RuntimeError(f"source sync failed: {put.stderr[-800:]}")
            else:
                arch = subprocess.Popen(["git", "-C", str(REPO), "archive", "--format=tar", full, "--", *paths],
                                        stdout=subprocess.PIPE)
                gz = subprocess.Popen(["gzip", "-1"], stdin=arch.stdout, stdout=subprocess.PIPE)
                arch.stdout.close()
                try:
                    put = subprocess.run(base + [f"tar -xzf - -C {run}/src"], stdin=gz.stdout,
                                         capture_output=True, text=True, timeout=1800)
                finally:
                    gz.stdout.close()
                    gz.wait()
                    arch.wait()
                if put.returncode or arch.returncode or gz.returncode:
                    raise RuntimeError(f"source sync failed: {put.stderr[-800:]}")
    if archive_receipt is not None:
        j["source_archive"] = archive_receipt
        ssh(host, f"cat > {run}/cl/source_archive.json", input=json.dumps(archive_receipt, indent=1), timeout=60, check=True)
    ship_helpers(host, run)
    corner_sta_compat(j, host, run, full)
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

    j["source_synced"] = True

# Commits whose route generator passes `corner_sta.py --sdc-name 6_signoff.sdc` but whose own tools/w18/corner_sta.py
# predates that flag (main 80a11cea9, edd8613d6): the route completes and corner STA dies with "unrecognized arguments:
# --sdc-name" (flow-triage 2026-10-08 03:15, hbm_smh_front_s_ne_prot). Ship the corner_sta.py that honours an explicit
# sign-off SDC (089608310 semantics) into {SRC}; the original is kept as corner_sta.py.orig_<commit>.
CORNER_STA_GENERATORS = ("tools/hbm_accel_smh_physical.py",)
CORNER_STA_COMPAT_REF = "089608310"


def corner_sta_compat(j, host, run, full):
    show = lambda rev, path: sh(["git", "-C", str(REPO), "show", f"{rev}:{path}"], timeout=60)
    sta = show(full, "tools/w18/corner_sta.py")
    if sta.returncode or "--sdc-name" in sta.stdout:
        return
    if not any(g in json.dumps(j["spec"].get("stages", {})) and "--sdc-name" in show(full, g).stdout
               for g in CORNER_STA_GENERATORS):
        return
    new = show(CORNER_STA_COMPAT_REF, "tools/w18/corner_sta.py")
    if new.returncode or "--sdc-name" not in new.stdout:
        raise RuntimeError(f"corner_sta compat source {CORNER_STA_COMPAT_REF} lacks --sdc-name")
    f = f"{run}/src/tools/w18/corner_sta.py"
    ssh(host, f"cp {f} {f}.orig_{full[:9]} && cat > {f}", input=new.stdout, timeout=60, check=True)
    event(j, f"corner_sta.py replaced by {CORNER_STA_COMPAT_REF}'s (generator passes --sdc-name)")


HELPERS = ("eco_recovery.py", "path_summary.py", "ck_insertion.py", "hold_eco.sh", "hold_eco.tcl", "hold_eco_corner.tcl",
           "hold_eco_sdc.py", "hold_eco_window.tcl", "hold_corners_patch.py", "h1_patch.py", "cal_classify.sh", "resume_patch.py", "resume_check.sh",
           "../orfs_hold_mm.py", "../orfs_hold_mm.tcl", "tt_resta.sh", "meas_resta.py", "lane_kh_overlay.py",
           "../../physical/common_flow/io_ref_routed.sdc", "../fp_margin_lint.py", "../fp_margin_lint.tcl",
           "../preroute_gate.py", "../preroute_gate.tcl", "tt_overlay.py", "vtswap_eco.sh", "vtswap_eco.tcl",
           *(f"../../physical/common_flow/{n}" for n in ("cg_pushdown.tcl", "clk_net_protect.tcl", "link_budget_hook.tcl",
                                                          "link_budget_consistent.sdc", "nbr_clk_measured_ttb.sdc")))

# deterministic calibrate (CTS-only) failures: a retry reproduces them, so the job stops at once with an owner action
CAL_OWNER_ACTION = {
    "cts_segv_macro_reg_sinks": "TritonCTS segfaults in separateMacroRegSinks (an inverter/forwarded-clock load on the root "
                                "clock net): add PRECTS=physical/hbm_accel_die_views/common/pre_cts_fclk_root_buf.tcl "
                                "(or your flow's equivalent root-buffer PRE_CTS hook) to calibrate+route, re-drop as a new job",
    "cts_segv": "OpenROAD segfault in CTS: reproduce on 3_place.odb, add a PRE_CTS workaround hook, re-drop",
    "rsz_max_buffer": "CTS timing repair hit the buffer cap (RSZ-0060): the IO SDC insertion/budget is off for this block or "
                      "a net has extreme fanout -- check the IO SDC (budget/calibrated), duplicate high-fanout drivers, re-drop",
    "odb_dont_touch": "CTS must rewire a dont_touch instance (ODB-0370): do not dont_touch cells on clock/repair nets "
                      "(or release them in PRE_CTS), re-drop",
    "est_parasitics": "EST-0104 inconsistent parasitics state in CTS: a step hook (PRE_CTS/POST_PLACE tcl) leaves "
                      "estimate_parasitics in a mixed state -- fix the hook, re-drop",
    "nickname": "route label not [A-Za-z0-9_]: use {LABEL} (the loop now sanitises {NAME} too); re-drop",
    "synth_or_place": "the CTS-only run failed before placement finished (synth/floorplan/place error): see the cal run.log, fix, re-drop",
    "flow_error": "ORFS error before CTS completed: see the CALIBRATE_FAIL detail, fix, re-drop",
}


def ship_helpers(host, run):
    """(re)write the loop's helper scripts into {CL}: jobs synced before a helper existed get it too"""
    # one ssh carrying a tar of all helpers (was one ssh per helper, 13 per launch, made while holding FLEET_LOCK)
    import io, tarfile
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        for helper in HELPERS:
            tf.add(str(HERE / helper), arcname=Path(helper).name)
    if is_local(host):
        os.makedirs(f"{run}/cl", exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(buf.getvalue())) as tf:
            tf.extractall(f"{run}/cl")
        return
    with transport_command(host) as base:
        r = subprocess.run(base + [f"mkdir -p {run}/cl && tar -xf - -C {run}/cl"],
                           input=buf.getvalue(), capture_output=True, timeout=120)
    if r.returncode:
        raise RuntimeError(f"command failed rc={r.returncode}: ship_helpers {host}:{run}/cl {r.stderr[-300:]!r}")


def tag(st, j):
    return f"{st['key']}.a{j['attempt']}"


# LEC OFF EVERYWHERE (drive-1043 2026-10-08): ORFS settings.mk defaults LEC_CHECK to 1 whenever the image carries
# kepler-formal, and kepler-formal is built for AVX-512: on a host without it (PVE1 Xeon E5-2680 v4) CTS dies with SIGILL
# ("child killed: illegal instruction", ha2_relay_tx_internal, drive-1013).  Most generators write LEC_CHECK = 0 into
# their config.mk; a flow that does not inherited the default.  Every non-bench stage now runs with {CL}/bin first on
# PATH, where a docker shim adds -e LEC_CHECK=0 to every `docker run` (settings.mk uses ?=, so the container env wins;
# no flow sets LEC_CHECK = 1).  LEC is not part of block sign-off (benches + STA + DRC are).
DOCKER_SHIM = r"""#!/bin/bash
# closure-loop shim: every container gets LEC_CHECK=0 (kepler-formal needs AVX-512); then the real docker
for e in ${PATH//:/ }; do
  if [ -x "$e/docker" ] && ! [ "$e/docker" -ef "$0" ]; then
    if [ "${1:-}" = run ] && [ -n "${OT_FP_LINT_DIR:-}" ]; then
      # FP-LINT: the floorplan margin lint (ORFS PRE GLOBAL_PLACE) sees OT_FP_LINT and writes its verdict to /ot_fplint
      mkdir -p "$OT_FP_LINT_DIR"; shift
      # PREROUTE-GATE: the pre-route timing gate (ORFS POST DETAIL_PLACE) sees OT_PREROUTE_GATE, writes PREROUTE_FAIL there
      exec "$e/docker" run -e LEC_CHECK=0 -e OT_FP_LINT -e OT_FP_LINT_ARGS -e OT_PREROUTE_GATE -e OT_PREROUTE_GATE_ARGS \
        -e OT_ABC_NO_DCH -e OT_HOLD_STOP -v "$OT_FP_LINT_DIR:/ot_fplint" "$@"
    fi
    # ABC-NODCH (drive-2155): a recipe exporting OT_ABC_NO_DCH=1 gets &synch2 for &dch (tools/orfs_hold_mm.py)
    if [ "${1:-}" = run ]; then shift; exec "$e/docker" run -e LEC_CHECK=0 -e OT_ABC_NO_DCH -e OT_HOLD_STOP "$@"; fi
    exec "$e/docker" "$@"
  fi
done
echo "closure-loop docker shim: no docker on PATH" >&2; exit 127
"""


def docker_lec_off(cl):
    return (f"mkdir -p {cl}/bin && cat > {cl}/bin/docker <<'OT_DOCKER_SHIM'\n{DOCKER_SHIM}OT_DOCKER_SHIM\n"
            f"chmod +x {cl}/bin/docker\nexport PATH={cl}/bin:$PATH\n")


def route_corner(j):
    """the corner a job's route stage repairs setup at: spec route_corner (default TC after option B), or for a "keep"
    recipe its own OT_ORFS_CORNER(_OVERRIDE)=... in the route command, else WC (SS)"""
    rc = j["spec"].get("route_corner", "TC") if (j.get("created") or now_iso()) >= OPTB_SINCE else "keep"
    if rc != "keep":
        return str(rc).upper()
    stages = j["spec"].get("stages")
    cmd = str(((stages or {}).get("route") or {}).get("cmd", "")) if isinstance(stages, dict) else ""
    m = re.search(r"OT_ORFS_CORNER(?:_OVERRIDE)?=['\"]?(\w+)", cmd)
    return m.group(1).upper() if m else "WC"


def route_ref(j):
    """'TT' when the job's route-time IO SDC references the TT (route-corner) insertion (CALIB-CORNER), else None"""
    if (j.get("created") or "") < ROUTE_REF_SINCE or j["spec"].get("route_ref") == "SS":
        return None
    return "TT" if route_corner(j) in ("TC", "TT") else None


# REBUDGET 2026-10-08 (tools/budgets/rebudget.py): new routes use the LATEST re-derived die-link IO budget of their block.
# rebudget.py derive publishes STATE/rebudget/current.json {blocks: {block: {rb, sdc}}}; a calibrate / route stage
# installs that SDC as {SRC}/physical/common_flow/rebudget_block.sdc and makes sure the snapshot's
# link_budget_consistent.sdc sources it last (older snapshots predate the hook).  Spec "rebudget": false opts out.
REBUDGET_CURRENT = STATE / "rebudget" / "current.json"
REBUDGET_HOOK = ("\n# REBUDGET hook (closure loop): the block's re-derived per-port die-link budget, installed beside this file\n"
                 "set ot_rb_hook [file join [file dirname [info script]] rebudget_block.sdc]\n"
                 "if {[file exists $ot_rb_hook]} { puts \"OT_REBUDGET hook $ot_rb_hook\"; source $ot_rb_hook }\n")


def install_rebudget(j):
    if j["spec"].get("rebudget") is False or not REBUDGET_CURRENT.exists():
        return
    try:
        cur = json.loads(REBUDGET_CURRENT.read_text())["blocks"].get(j["spec"].get("block"))
    except (OSError, ValueError, KeyError):
        return
    if not cur or not Path(cur.get("sdc", "")).is_file():
        return
    d = f"{j['run']}/src/physical/common_flow"
    r = ssh(j["host"], f"mkdir -p {d} && cat > {d}/rebudget_block.sdc", input=Path(cur["sdc"]).read_text(), timeout=60)
    if r.returncode:
        return
    ssh(j["host"], f"f={d}/link_budget_consistent.sdc; [ -f $f ] && ! grep -q 'REBUDGET hook' $f && cat >> $f", input=REBUDGET_HOOK,
        timeout=60)
    if j.get("rebudget_route") != cur["rb"]:
        j["rebudget_route"] = cur["rb"]
        event(j, f"route IO budget: {cur['rb']} (re-derived die-link budget of {j['spec'].get('block')}) installed as "
                 f"rebudget_block.sdc, sourced by link_budget_consistent.sdc")


# FP-LINT (owner 2026-10-08): floorplan margin lint before global placement, on by default for calibrate and route.
# tools/orfs_hold_mm.py (run in every run_abi3_physical flow container) hooks ORFS PRE GLOBAL_PLACE; the docker shim
# passes OT_FP_LINT and mounts {CL}/fplint/<tag> at /ot_fplint; a failing floorplan writes FAIL there and stops the
# flow, and crash() / cal_track() finish the job with verdict FLOORPLAN_MARGIN (no retry, no route spent).
# Spec "fp_lint": false opts out; {"set": {"util_max": 0.62, ...}} overrides thresholds (tools/fp_margin_lint.py
# THRESHOLDS); {"warn_only": true} reports without failing.
def gate_args(cfg):
    cfg = cfg if isinstance(cfg, dict) else {}
    args = " ".join(f"--set {k}={v}" for k, v in (cfg.get("set") or {}).items())
    if cfg.get("warn_only"):
        args += " --warn-only"
    return args.strip()


# PREROUTE-GATE (owner 2026-10-08): the pre-route timing gate (tools/preroute_gate.tcl/.py) runs at ORFS POST
# DETAIL_PLACE of a ROUTE stage (never a calibrate) and stops a variant whose placed design is far from closing before
# CTS / GRT / DRT are spent.  The owner allows it only because it is fast: measured 2026-10-08 on the fleet's finished
# routes (preroute-gate.log), the in-flow cost is the path dump alone (timing is already updated by report_metrics), a
# few seconds against routes of hours.  On by default; spec "preroute_gate": false opts out; {"set": {"ws_ps": ...,
# "count": ...}} overrides thresholds (tools/preroute_gate.py THRESHOLDS, calibrated to never reject an eventual closure).
def preroute_gate_on(j, kind):
    return kind == "route" and j["spec"].get("preroute_gate", True) is not False


# drive-2155 2026-10-08: recipes that run the FLOW-HOLD snapshot's hold_corners_patch.py ({FH}/tools/closure_loop, 164
# jobs: every hbm view / vm8 recipe) re-copy {FH}/tools/orfs_hold_mm.{py,tcl} over the helpers shipped here ("always
# refresh").  The FH copy of orfs_hold_mm.py was the pre-guard generation, so those routes ran without the hold-stall
# guard, the HM guard and MET-FIRST.  The FH h1_patch.py / hold_corners_patch.py those recipes run were stale too (no
# h1-audit families: fh_quad / head ioreg / BF / hbglue / attn_tile_r kept the receiver hold term; no TC / CTS-only
# calibrate code).  ship_fpl refreshes the FH snapshots on the launch host (tmp + mv: atomic for a concurrent reader).
FH_DIRS = ("/srv/opentallas-scratch/claude/flowhold/src", "/home/ubuntu/closure-loop-local/flowhold/src")
FH_FILES = (("orfs_hold_mm.py", "tools"), ("orfs_hold_mm.tcl", "tools"), ("h1_patch.py", "tools/closure_loop"),
            ("hold_corners_patch.py", "tools/closure_loop"))
# drive-2155 2026-10-09: the TT-batch overlay snapshot (26f14af32, 635 jobs) has the same failure: tt_overlay.py force-copies
# its physical/common_flow files over the job's source, so even new-commit routes got link_budget_consistent.sdc WITHOUT
# the rebudget hook (budget_rb never applied) and cg_pushdown.tcl without the BF HALF_PHL exclusion, plus a pre-audit
# h1_patch.py.  Every main-vs-snapshot difference is an additive flow fix already on main, so the same refresh applies.
TTB_DIRS = ("/srv/opentallas-scratch/claude/ttbatch/26f14af32", "/home/ubuntu/closure-loop-local/ttbatch/26f14af32")
TTB_FILES = (("tt_overlay.py", "tools/closure_loop"), ("h1_patch.py", "tools/closure_loop"),
             *((n, "physical/common_flow") for n in ("cg_pushdown.tcl", "clk_net_protect.tcl", "link_budget_hook.tcl",
                                                    "link_budget_consistent.sdc", "nbr_clk_measured_ttb.sdc")))
SNAPSHOT_REFRESH = ((FH_DIRS, FH_FILES), (TTB_DIRS, TTB_FILES))


def snapshot_refresh_sh(run):
    """shell: refresh every frozen flow snapshot's copies from the helpers just shipped to {run}/cl (tmp + mv)"""
    out = ""
    for dirs, files in SNAPSHOT_REFRESH:
        out += (f"for fh in {' '.join(dirs)}; do for fd in {' '.join(f + ':' + d for f, d in files)}; do "
                f"f=${{fd%%:*}}; t=$fh/${{fd#*:}}; "
                f"[ -f {run}/cl/$f ] && [ -d $t ] && ! cmp -s {run}/cl/$f $t/$f && "
                f"cp -f {run}/cl/$f $t/.$f.$$ && mv -f $t/.$f.$$ $t/$f; done; done; ")
    return out


def fp_lint_env(j, t, lint=True, prg=False):
    run, d = j["run"], f"{j['run']}/cl/fplint/{t}"
    env = (f"ship_fpl() {{ for f in fp_margin_lint.py fp_margin_lint.tcl orfs_hold_mm.py orfs_hold_mm.tcl "
           f"preroute_gate.py preroute_gate.tcl; do "
           f"[ -f {run}/cl/$f ] && [ -d {run}/src/tools ] && cp -f {run}/cl/$f {run}/src/tools/$f; done; "
           f"{snapshot_refresh_sh(run)}true; }}\nship_fpl\n"
           f"rm -rf {d} && mkdir -p {d} && chmod a+rwx {d}\nexport OT_FP_LINT_DIR={d}\n")
    if lint:
        env += (f"export OT_FP_LINT=1 OT_FP_LINT_DIR={d} "
                f"OT_FP_LINT_ARGS={shlex.quote(gate_args(j['spec'].get('fp_lint', True)))}\n")
    if prg:
        env += (f"export OT_PREROUTE_GATE=1 "
                f"OT_PREROUTE_GATE_ARGS={shlex.quote(gate_args(j['spec'].get('preroute_gate', True)))}\n")
    return env


def fp_lint_failed(host, run, tag):
    """the lint's FAIL text for stage tag (None: no lint failure, or the host could not be read)"""
    try:
        r = ssh(host, f"cat {run}/cl/fplint/{tag}/FAIL 2>/dev/null", timeout=60)
    except Exception:  # noqa: BLE001
        return None
    return r.stdout.strip() if r.returncode == 0 and "FLOORPLAN_MARGIN" in (r.stdout or "") else None


def preroute_failed(host, run, tag):
    """the pre-route gate's FAIL text for stage tag (None: no gate failure, or the host could not be read)"""
    try:
        r = ssh(host, f"cat {run}/cl/fplint/{tag}/PREROUTE_FAIL 2>/dev/null", timeout=60)
    except Exception:  # noqa: BLE001
        return None
    return r.stdout.strip() if r.returncode == 0 and "PREROUTE_MARGIN" in (r.stdout or "") else None


def preroute_finish(j, tag, text):
    reasons = next((l[len("PREROUTE_MARGIN: "):] for l in text.splitlines() if l.startswith("PREROUTE_MARGIN: ")), text)
    kill_own_stage(j)
    finish(j, "PREROUTE_MARGIN", reasons[:600],
           f"PREROUTE_MARGIN ({tag}): the placed design failed the pre-route timing gate (no CTS/route spent; report "
           f"{j['run']}/cl/fplint/{tag}/preroute_gate.json)\n" +
           "\n".join(l for l in text.splitlines() if l.startswith("preroute_gate:"))[:1500] +
           "\nFIX: the placed slack is far beyond what routing has ever recovered: pipeline / restructure the worst "
           "paths (REDESIGN_RULES); spec preroute_gate:false opts out, {\"set\": {\"ws_ps\": ...}} overrides")


def fp_lint_finish(j, tag, text):
    reasons = next((l[len("FLOORPLAN_MARGIN: "):] for l in text.splitlines() if l.startswith("FLOORPLAN_MARGIN: ")), text)
    try:                       # lint-at-submit: the measured area predicts the next job of the same synthesis input
        rec = submit_lint.util_record(j.get("spec_submitted", j["spec"]), reasons, submit_lint.Git(REPO), j["name"])
        if rec:
            util_db_add(*rec)
    except Exception:  # noqa: BLE001
        pass
    kill_own_stage(j)          # a parallel calibrate / route of the same floorplan stops too
    finish(j, "FLOORPLAN_MARGIN", reasons[:600],
           f"FLOORPLAN_MARGIN ({tag}): the floorplan failed the margin lint before global placement (no route spent; "
           f"report {j['run']}/cl/fplint/{tag}/fp_margin_lint.json)\n" +
           "\n".join(l for l in text.splitlines() if l.startswith("fp_margin_lint:"))[:1500] +
           "\nFIX (REDESIGN_RULES 'floorplan margin targets'): <= 55-60% util, <= 6 bits/um/layer, PDN-clear pin "
           "columns, channels sized to the crossing nets; spec fp_lint:false opts out")


def launch_stage(j, st, cmd):
    t = tag(st, j)
    if st["kind"] == "bench":
        # Mutation benches must never write the route's source tree. One private
        # tree per job attempt retains generated inputs shared by bench stages.
        j["stage_source"] = f"{j['run']}/bench_src_a{str(j['attempt']).split('b')[0]}"
    else:
        j.pop("stage_source", None)
    env = "".join(f"export {k}={shlex.quote(v)}\n" for k, v in dict(
        RUN=j["run"], SRC=j.get("stage_source", f"{j['run']}/src"), CL=f"{j['run']}/cl", HOST=j["host"], NAME=label(j["name"]),
        LABEL=label(j["name"]), RAW_NAME=j["name"],
        BLOCK=j["spec"]["block"], COMMIT=j["commit_full"], THREADS=str(st.get("threads", 4)),
        CL_PHASE=st["kind"], CL_LABEL_SUFFIX="_cal" if st["kind"] == "calibrate" else "",
        CL_STOP_AFTER="--pnr-stop-after cts" if st["kind"] == "calibrate" else "").items())
    if st["kind"] != "bench":
        env += docker_lec_off(f"{j['run']}/cl")
    fpl = st["kind"] in ("calibrate", "route") and j["spec"].get("fp_lint", True) is not False
    prg = preroute_gate_on(j, st["kind"])
    if fpl or prg:
        ship_helpers(j["host"], j["run"])
        env += fp_lint_env(j, t, lint=fpl, prg=prg)
    if st["kind"] == "calibrate":
        # UNSTICK (owner 2026-10-08): calibrate measures clock insertion only.  No CTS timing/hold repair
        # (SKIP_CTS_REPAIR_TIMING=1 through hold_corners_patch.py OT_CAL_CTS_ONLY): 40 calibrates sat 4-25 h in CTS hold
        # repair (mm, HM 50) measuring nothing.  Applied to every calibrate, whatever its route_hold_corners.
        ship_helpers(j["host"], j["run"])
        env += f"export OT_CAL_CTS_ONLY=1\npython3 {j['run']}/cl/hold_corners_patch.py {j['run']}/src\n"
        if route_ref(j):
            # CALIB-CORNER: CTS at the route corner, insertion referenced to it (ck_insertion.py --route-corner)
            env += f"export OT_ORFS_CORNER={shlex.quote(route_corner(j))}\nexport OT_CAL_ROUTE_CORNER={shlex.quote(route_corner(j))}\n"
    if st["kind"] in ("calibrate", "route"):
        install_rebudget(j)
    if st["kind"] in ("calibrate", "route") and j.get("created", "") >= HM_DEFAULT_SINCE:
        # default route hold margin (coordinator 2026-10-06: hold-only misses dominate; ctrl_ctr closed at HM 35 ps);
        # route_view.sh reads HM in ns; an inline HM=... in the command, or spec route_hold_margin_ns, overrides it
        # coordinator 2026-10-07: jobs created from HM_LOW_SINCE default to 10 ps -- 35 ps + the 50 ps FF IO hold
        # uncertainty overloaded CTS/GRT hold repair (RSZ-0060 buffer-cap deaths, hours-long GRT hold); the post-route
        # hold ECO (rev 2: setup-preserving) carries hold to +18.  Earlier jobs keep 35 ps (same flow on a retry).
        hm_default = 0.010 if j.get("created", "") >= HM_LOW_SINCE else 0.035
        if j.get("created", "") >= MM_SINCE and j["spec"].get("route_hold_corners", "mm") == "mm":
            hm_default = HM_MM
        env += f"export HM={j['spec'].get('route_hold_margin_ns', hm_default)}\n"
    if is_local(j["host"]):
        env += f"export OPENTALLAS_ORFS_IMAGE={LOCAL_ORFS_REF}\n"
    # bench-track views carry a string attempt ("1b2"): their outputs are not the stage dir, never move them aside
    if isinstance(j["attempt"], int) and j["attempt"] > 1 and not j.get("resume"):
        env += retry_aside(j, st)
    if st["kind"] == "route" and route_ref(j):
        fixed = sorted(set(re.findall(r"io_vclk_m_\d+\.sdc", cmd)))
        if fixed:
            log(f"{j['name']}: CALIB-CORNER WARNING route cmd names fixed IO SDC(s) {', '.join(fixed)}: not referenced to "
                f"the TT insertion (generate them from $CK_SS_MEAN in sdc_cmd)")
    if st["kind"] == "route" and now_iso() >= OPTB_SINCE and j["spec"].get("route_corner", "TC") != "keep":
        env += f"export OT_ORFS_CORNER={shlex.quote(str(j['spec'].get('route_corner', 'TC')))}\n"
    if st["kind"] in ("calibrate", "route"):
        # (calibrate too, 2026-10-07: its CTS-only run repairs hold at CTS and died on RSZ-0060, hbm_stn_r38 / _ck80)
        # ROUTE HOLD CORNERS (2026-10-07, hold_corners_patch.py): place-and-route repairs hold at the primary corner only
        # -- the route SDC's virtual IO clock sits at the SS insertion, so BC showed fake IO hold violations of about the
        # SS-FF insertion difference (thousands of flow hold buffers); FF hold goes to the post-route hold ECO.  Spec
        # "route_hold_corners": "keep" leaves the recipe's own --hold-corners; any other value is passed through.
        # FLOW-HOLD (2026-10-07): jobs created from MM_SINCE default to "mm" -- route-time repair in a multi-mode session,
        # scene WC (SS libs, the route SDC: setup) + scene BC (FF libs, the route SDC refreshed + the FF sign-off SDCs:
        # hold), tools/orfs_hold_mm.tcl.  The FF SDCs are spec "route_ff_sdc" (list), else verdict.post_sdc; a file outside
        # the snapshot is copied into {SRC}/.ot_mm/ (the flow container mounts only the snapshot).
        rhc = j["spec"].get("route_hold_corners", "mm" if j.get("created", "") >= MM_SINCE else "primary")
        if rhc != "keep":
            ship_helpers(j["host"], j["run"])
            env += f"export OT_ROUTE_HOLD_CORNERS={shlex.quote(str(rhc))}\n" \
                   f"python3 {j['run']}/cl/hold_corners_patch.py {j['run']}/src\n"
        if rhc == "mm":
            ff = j["spec"].get("route_ff_sdc")
            if ff is None:
                ff = (j["spec"].get("verdict") or {}).get("post_sdc") or []
            # {NAME}/{LABEL} name the recipe's generated sign-off SDC (route_cl.sh <label>); the calibrate stage runs the
            # recipe on {LABEL}${CL_LABEL_SUFFIX}, so its SDC carries _cal.  Before 2026-10-08 any path with "{" was
            # DROPPED, so the FF scene silently timed the route SDC (vclk at the SS insertion: ~-200 ps output hold,
            # RSZ-0060; tt-fix.log F2).  Paths still holding an unknown placeholder after substitution are dropped loudly.
            sfx = "_cal" if st["kind"] == "calibrate" and "CL_LABEL_SUFFIX" in cmd else ""
            ff_sub = []
            for f in ([ff] if isinstance(ff, str) else ff):
                if not f:
                    continue
                f = subst(f.replace("{NAME}", label(j["name"]) + sfx).replace("{LABEL}", label(j["name"]) + sfx), j)
                if "{" in f:
                    log(f"{j['name']}: route FF SDC {f} has an unknown placeholder: dropped")
                    continue
                ff_sub.append(f)
            ff = ff_sub
            # VM8-TIMING 2026-10-08: the FF hold scene also reads io_ref_routed.sdc LAST (the shipped helper copy in {CL}),
            # so route-time FF hold repair targets the MEAN boundary insertion of the tree being built -- the reference
            # the verdict's routed re-STA uses (routed_ioref).  Without it the scene timed vclk at the MIN insertion
            # (vclk_corner_true.sdc) and every route passed FF at route time, then failed the verdict on output-pin
            # flops by (mean - min) + 50 (hbm_vm8_nws_sp_hm10: 6,906 outputs at -45..-64).  Spec "route_ff_ioref": false
            # opts out; a spec that already lists an io_ref_routed.sdc keeps its own.
            if j["spec"].get("route_ff_ioref", True) and not any(f.rsplit("/", 1)[-1] == "io_ref_routed.sdc" for f in ff):
                ff = ff + [f"{j['run']}/cl/io_ref_routed.sdc"]
            # MMFF-IOREF 2026-10-08: a route cmd that inlines its own `export OT_MM_FF_SDC=...` (43 live jobs: setup_triage
            # requeue, make_lvt_job, mk_jobs) overrode the export above, so the FF scene lost io_ref_routed.sdc and timed
            # the assumed vclk (hbm_quant_ts0spl_tt: fake 4_1_cts hold -334).  The appended reference now travels as a
            # FILE the FF scene reads last whatever the final env says (orfs_hold_mm.tcl ot_mm_sync,
            # {SRC}/.ot_mm/ff_ioref_last.sdc; skipped when the list already holds an io_ref_routed.sdc); the opt-out
            # removes it so an earlier attempt's copy cannot leak in.
            if j["spec"].get("route_ff_ioref", True):
                env += f"mkdir -p {j['run']}/src/.ot_mm && cp {j['run']}/cl/io_ref_routed.sdc {j['run']}/src/.ot_mm/ff_ioref_last.sdc\n"
            else:
                env += f"rm -f {j['run']}/src/.ot_mm/ff_ioref_last.sdc\n"
            if ff:
                env += f"mkdir -p {j['run']}/src/.ot_mm\n"
                rel = []
                for f in ff:
                    if f.startswith("/"):
                        env += f"cp {shlex.quote(f)} {j['run']}/src/.ot_mm/\n"
                        rel.append(".ot_mm/" + f.rsplit("/", 1)[-1])
                    else:
                        rel.append(f)
                env += f"export OT_MM_FF_SDC={shlex.quote(' '.join(rel))}\n"
    if j.get("resume") and st["kind"] in ("route", "calibrate"):
        env += "export OT_CL_RESUME=1\n"
    if st["kind"] == "route" and j.get("hold_stop"):    # HOLD-STOP (drive-resume): see hold_stop_resume
        env += f"export OT_HOLD_STOP={shlex.quote(' '.join(f'{k}:{int(v)}' for k, v in sorted(j['hold_stop'].items())))}\n"    # patched run_abi3_physical in the moved snapshot: resume from the checkpoint
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
    if st["kind"] == "bench":
        private = shlex.quote(j["stage_source"])
        original = shlex.quote(f"{j['run']}/src")
        env += (f"if [ ! -d {private} ]; then\n"
                f"  test ! -e {private}.tmp || exit 9\n"
                f"  cp -a --reflink=auto {original} {private}.tmp || exit $?\n"
                f"  mv {private}.tmp {private} || exit $?\nfi\n"
                f"cd {private} || exit $?\n")
        # A few legacy recipes spell {RUN}/src instead of using {SRC}.
        cmd = cmd.replace("{RUN}/src", "{SRC}")
    if st["kind"] == "route" and (j.get("ctrack") or {}).get("sdc_cmd"):
        # calibrate runs in parallel: the IO SDC the calibrate stage would have generated is made here from the
        # assumed (or, on a re-route, measured) insertion in calib.env
        cmd = f"( {j['ctrack']['sdc_cmd']} ) || exit 5\n" + cmd
    cmd = tt_overlay_fallback(cmd)
    body = f"#!/bin/bash\n# closure-loop {j['name']} stage {st['key']} attempt {j['attempt']}\nset -o pipefail\n{env}{subst(cmd, j)}\n"
    run = j["run"]
    # idempotent launch (2026-10-07): a daemon restart between a launch and the job-state save re-launched the same tag;
    # the second copy overwrote the script and rc (dsrom_softmax_safe_div2b: hold ECO 'rc=10 output exists' while the
    # first ECO was running).  A tag whose process is alive is adopted, never launched twice.
    alive = ssh(j["host"], f"p=$(cat {run}/cl/{t}.pid 2>/dev/null); [ -n \"$p\" ] && kill -0 $p 2>/dev/null && "
                           f"[ ! -f {run}/cl/{t}.rc ] && echo ALIVE; true", timeout=60)
    if "ALIVE" in alive.stdout:
        log(f"[{j['name']}] {t} already running on {j['host']}: adopted, not relaunched")
    else:
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


def remote_ok(j, cmd, timeout=300):
    if not cmd:
        return True, ""
    source = j.get("stage_source", f"{j['run']}/src")
    r = ssh(j["host"], f"cd {shlex.quote(source)} && {subst(cmd, j)}", timeout=timeout)
    return r.returncode == 0, (r.stdout + r.stderr)[-400:]


def bench_outcome(j, st, rc, ok_extra=True):
    """pass: rc 0 (+ ok, + pass_regex); fail: rc != 0 (+ fail_regex).  Regexes are MULTILINE over the whole stage log
    (last 20000 lines), so ^FAIL matches any line."""
    full = ""
    for _ in range(4):  # an ssh hiccup returns an empty log and mis-judged benches (code-pair 10-07); fetch until it reads
        # drive-resume 2026-10-09: a bench that prints nothing (qkd_d2d *_record: a python -c exit-code check) left an
        # EMPTY log, read as an ssh hiccup 10x -> NEEDS_HUMAN.  A marker line proves the file was read: empty is valid.
        r = ssh(j["host"], f"f={j['run']}/cl/{j['stage_tag']}.log; [ -f $f ] && echo OT_BENCH_LOG_READ && tail -n 20000 $f",
                timeout=180)
        if r.returncode == 0 and r.stdout.startswith("OT_BENCH_LOG_READ"):
            full = r.stdout.split("\n", 1)[1] if "\n" in r.stdout else ""
            break
        time.sleep(15)
    else:
        raise RuntimeError(f"bench log unreadable on {j['host']}: {j['run']}/cl/{j['stage_tag']}.log")
    if st["expect"] == "pass":
        ok = rc == 0 and ok_extra and (not st.get("pass_regex") or re.search(st["pass_regex"], full, re.M) is not None)
        if ok:
            work, note = bench_work(full, st.get("min_count_regex"))
            j.setdefault("bench_work", {})[st["key"]] = note
            if work is False:
                return False
        return ok
    return expected_fail_seen(st, rc, full)


def expected_fail_seen(st, rc, full):
    """expect FAIL (negative control): the log's own verdict decides, regardless of rc -- a mutant bench that prints
    FAIL but exits 0 was read as "expected FAIL but rc=0" (LOOP-GAPS 2026-10-08).  With fail_regex: it must match (a
    crash with rc != 0 and no FAIL verdict is not a detected mutant).  Without: rc != 0 or a conventional ^FAIL line."""
    if st.get("fail_regex"):
        return re.search(st["fail_regex"], full, re.M) is not None
    return rc != 0 or re.search(r"^FAIL\b", full, re.M) is not None


WORK_RE = re.compile(r"\b(compared|comparisons|checks?|checked|vectors|cases|tokens|results|matches|transactions|"
                     r"samples|tests|passed|beats|ops)\s*[=:]\s*(\d+)", re.I)


def bench_work(log, min_count_regex=None):
    """VACUOUS-PASS GUARD (2026-10-07: distro Verilator 5.032 ran the SU reducer benches with ZERO reducer results).
    spec min_count_regex (one capture group): a pass needs a match and every captured count > 0.  Without it, generic
    count lines (compared=N, checks: N, ...) all equal to 0 fail the pass; a pass log with no count line passes with a
    warning.  Returns (False | True | None, note)."""
    if min_count_regex:
        m = [int(x) for x in re.findall(min_count_regex, log, re.M) if str(x).isdigit()]
        if not m or min(m) <= 0:
            return False, f"vacuous: min_count_regex {min_count_regex!r} counts {m[:8]}"
        return True, f"work: {m[:8]}"
    m = [(k, int(v)) for k, v in WORK_RE.findall(log)]
    if m and all(v == 0 for _, v in m):
        return False, f"vacuous: every count line is 0 ({m[:6]})"
    if not m:
        return None, "WARN: pass log has no count line (set min_count_regex)"
    return True, f"work: {m[:6]}"


def stage_tail(j, st, n=40):
    extra = " ".join(subst(x, j) for x in st.get("logs", []))
    r = ssh(j["host"], f"tail -n {n} {j['run']}/cl/{j['stage_tag']}.log 2>/dev/null; for f in {extra}; do "
                       f"[ -f \"$f\" ] && tail -n {n} \"$f\"; done; true", timeout=60)
    return r.stdout


TT_STA_SLOTS = threading.BoundedSemaphore(3)   # each holds one of a host's 8 ssh channels for minutes


def get_metrics(j, tt_resta=True):
    v = j["spec"].get("verdict", {})
    if v.get("metrics_cmd"):
        r = ssh(j["host"], f"cd {j['run']}/src && {subst(v['metrics_cmd'], j)}", timeout=600)
        last = [x for x in r.stdout.splitlines() if x.strip().startswith("{")]
        if not last and r.returncode:
            # no JSON and a failed command: an ssh drop (w2-rb-safe-no3 went NEEDS_HUMAN "verdict inputs missing" with
            # raw {} while the same command printed the metrics a minute later) or a real error. Raise: transient ssh
            # errors back off, anything else counts toward the 10-consecutive-errors NEEDS_HUMAN.
            raise RuntimeError(f"verdict metrics_cmd produced no JSON (command failed rc={r.returncode}): "
                               f"{(r.stderr or r.stdout).strip()[-300:]}")
        m = json.loads(last[-1]) if last else {}
        return dict(ss_ps=m.get("ss_ps"), ff_ps=m.get("ff_ps"), drc=m.get("drc"), orfs_dir=m.get("orfs_dir"),
                    setup_corner=m.get("setup_corner"), clock_periods_ps=m.get("clock_periods_ps"),
                    ss_sensitivity_ps=m.get("ss_sensitivity_ps"), raw=m)
    py = r"""
import glob,json,sys,re
cs=sorted(glob.glob(sys.argv[1])); dm=sorted(glob.glob(sys.argv[2])) if sys.argv[2] else []
o={'corner_sta':cs,'drc_metrics':dm}
if cs:
  d=json.load(open(cs[-1])); o['ff_ps']=d['hold_ff']['worst_slack_ps']
  o['clock_periods_ps']={name:float(period) for name,period in re.findall(r'create_clock\s+-name\s+(\S+)\s+-period\s+([0-9.]+)', d.get('extra_sdc',''))}
  o['orfs_dir']=d.get('orfs_dir'); o['post_sdc']=list(d.get('post_sdc',{}))
  o['sdc_name']=d.get('sdc_name') or d['hold_ff'].get('sdc_name') or '6_final.sdc'; o['setup_post_sdc']=list(d.get('setup_post_sdc') or [])
  o['ss_sensitivity_ps']=d['setup_ss']['worst_slack_ps']; o['ss_sensitivity_tns_ps']=d['setup_ss'].get('tns_ps')
  # OWNER OPTION B: setup closes at TT; ss_ps keeps its key for the loop's line checks but now holds the TT setup slack
  tt=d.get('setup_tt')
  if tt is None:
    try: tt=json.load(open(cs[-1]+'.tt.json')).get('setup_tt')
    except Exception: tt=None
  o['setup_corner']='tt'; o['corner_sta_tt']=cs[-1]+'.tt.json' if 'setup_tt' not in d else cs[-1]
  if tt is None:
    o['need_tt']=True; o['ss_ps']=None; o['errors']=d['hold_ff'].get('errors',[])
  else:
    o['ss_ps']=tt.get('worst_slack_ps'); o['ss_tns_ps']=tt.get('tns_ps')
    o['errors']=(tt.get('errors') or [])+d['hold_ff'].get('errors',[])+([tt['error']] if tt.get('error') else [])
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
    if m.get("need_tt") and tt_resta and m.get("orfs_dir") and not m.get("error"):
        with TT_STA_SLOTS:          # TT re-STA of an existing route (option B), at most a few at once fleet-wide
            ship_helpers(j["host"], j["run"])
            ssh(j["host"], f"bash {j['run']}/cl/tt_resta.sh {shlex.quote(m['orfs_dir'])} {j['run']}/src "
                           f"{shlex.quote(m['corner_sta_tt'])}", timeout=6000)
        event(j, "option B: TT setup re-STA of the existing route")
        return get_metrics(j, tt_resta=False)
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


def setup_corner_label(metrics):
    """Label the measured setup scene; ss_ps is a historical compatibility key."""
    corner = str(metrics.get("setup_corner") or "unknown").lower()
    return {"tt": "TT", "tc": "TT", "ss": "SS", "wc": "SS"}.get(corner, corner.upper())


def measured_clock_text(metrics):
    periods = metrics.get("clock_periods_ps") or {}
    if not periods:
        return "under measured clock constraints"
    return "at " + ", ".join(f"{name} {period:g} ps" for name, period in sorted(periods.items()))


def setup_sensitivity_text(metrics):
    value = metrics.get("ss_sensitivity_ps")
    return f"; SS sensitivity {value:+.2f} ps" if isinstance(value, (int, float)) else ""


def defer_record_merge(j, out, sparse, dry=False):
    """Keep the source-branch record durable while the owner's main window is held."""
    if dry or j['spec'].get('merge_target') != 'main' or not (claude_owns_main() or (STATE / 'main_integration_hold.json').exists()):
        return False
    pending = STATE / 'deferred_record_merges'
    pending.mkdir(parents=True, exist_ok=True)
    record = dict(job=dict(name=j['name'], spec=dict(block=j['spec']['block'],
                  source=dict(branch=j['spec']['source']['branch']), merge_target='main')),
                  out=dict(out), sparse=sparse, queued_at=now_iso())
    path = pending / (j['name'] + '.json')
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(record, indent=1) + '\n')
    was_pending = path.exists()
    tmp.replace(path)
    if claude_owns_main() and not was_pending:
        notify_claude_record(j['name'], out.get('record_branch', j['spec']['source']['branch']), out['branch_commit'])
    out['merge'] = ('DEFERRED main merge: Claude owns integration; record committed on source branch' if claude_owns_main() else 'DEFERRED main merge: owner integration window; record committed on source branch')
    return True


def merge_record(j, out, sparse, dry=False):
    spec = j['spec']
    branch, target = out.get('record_branch', j['spec']['source']['branch']), j['spec'].get('merge_target')
    mwt = STATE / 'git' / (j['name'] + '-merge')
    for attempt in range(4):
        if defer_record_merge(j, out, sparse, dry):
            return out
        gfetch(target, timeout=600)
        wt_add(mwt, f"origin/{target}", sparse)
        mref = out["branch_commit"]
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
        if defer_record_merge(j, out, sparse, dry):
            wt_rm(mwt)
            return out
        p = sh(["git", "-C", str(mwt), "push", "-q", "origin", f"HEAD:refs/heads/{target}"], timeout=900)
        if p.returncode == 0:
            out["merge"] = f"merged into {target} {out['merge_commit'][:9]}"
            break
        log(f"[{j['name']}] push to {target} rejected (attempt {attempt}): {p.stderr[-300:]}")
        wt_rm(mwt)
    else:
        out["merge"] = f"PUSH-RACE: could not push the merge into {target}"
    wt_rm(mwt)
    return out


def retry_deferred_record_merges():
    if claude_owns_main() or (STATE / 'main_integration_hold.json').exists():
        return
    for path in sorted((STATE / 'deferred_record_merges').glob('*.json')):
        if (STATE / 'main_integration_hold.json').exists():
            break
        try:
            record = json.loads(path.read_text())
            with PUBLISH_LOCK:
                out = merge_record(record['job'], record['out'], record['sparse'])
            if out.get('merge', '').startswith('merged into '):
                with job_lock(record['job']['name']):
                    j = load_job(record['job']['name'])
                    j['publish'] = out
                    event(j, 'Deferred record ' + out['merge'])
                    save_job(j)
                path.unlink()
        except Exception:
            log('deferred record merge retry error:\n' + traceback.format_exc())


_DEFERRED_MERGE_FUTURE = None
_DEFERRED_MERGE_POOL = ThreadPoolExecutor(max_workers=1)


def schedule_deferred_record_merges():
    global _DEFERRED_MERGE_FUTURE
    if _DEFERRED_MERGE_FUTURE is None or _DEFERRED_MERGE_FUTURE.done():
        _DEFERRED_MERGE_FUTURE = _DEFERRED_MERGE_POOL.submit(retry_deferred_record_merges)


def publish(j, metrics):
    """Commit record + view on the job branch (explicit paths), trial-merge into merge_target, push."""
    spec = j["spec"]
    source_branch, target = spec["source"]["branch"], spec.get("merge_target")
    branch = f"codex/closure-record-{j['name']}" if claude_owns_main() else source_branch
    rec_dir = f"results/closure_loop/{j['name']}"
    tos = [r["to"] for r in spec.get("record", [])] + [rec_dir]
    sparse = ["/" + t.rstrip("/") for t in tos] + ["/tools/closure_loop/"]
    gdir = STATE / "git"
    gdir.mkdir(parents=True, exist_ok=True)
    cwt, mwt = gdir / f"{j['name']}-commit", gdir / f"{j['name']}-merge"
    dry = spec.get("dry_run_git", False)
    out = {}
    for attempt in range(4):
        base = branch
        if branch != source_branch:
            exists = git('ls-remote', '--heads', 'origin', branch).stdout.strip()
            if not exists:
                base = source_branch
        gfetch(base, timeout=600)
        wt_add(cwt, f"origin/{base}", sparse)
        for r in spec.get("record", []):
            src = subst(r["from"], j)
            dst = cwt / r["to"]
            isdir = ssh(j["host"], f"test -d {shlex.quote(src)}", timeout=30).returncode == 0
            dst.parent.mkdir(parents=True, exist_ok=True)
            excl = sum((["--exclude", x] for x in r.get("exclude", [])), [])
            with transport_command(j['host']) as base:
                remote_shell = [] if is_local(j['host']) else ["-e", shlex.join(base[:-1])]
                if isdir:
                    dst.mkdir(parents=True, exist_ok=True)
                    sh(["rsync", "-a", *remote_shell, *excl, rpath(j['host'], src.rstrip('/') + '/'), f"{dst}/"], timeout=1800, check=True)
                else:
                    sh(["rsync", "-a", *remote_shell, rpath(j['host'], src), str(dst)], timeout=1800, check=True)
        (cwt / rec_dir).mkdir(parents=True, exist_ok=True)
        verdict = dict(schema="opentallas.closure_loop.verdict.v1", job=j["name"], block=spec["block"],
                       owner=spec["owner"], source_branch=source_branch, record_branch=branch, source_commit=j["commit_full"],
                       host=j["host"], run_dir=j["run"], acceptance=dict(setup_corner=setup_corner_label(metrics), setup_min_ps=SS_MIN, ff_min_ps=FF_MIN, drc=0, clock_periods_ps=metrics.get("clock_periods_ps"),
                       rule="OWNER 2026-10-08: TT setup >= 0 / FF hold >= 0; SS sensitivity (60/25 uncertainties; +15 design target), "
                            "agreed die-clock IO budgets, DRC 0"),
                       metrics={k: metrics.get(k) for k in ("ss_ps", "ff_ps", "drc", "ss_tns_ps", "clock_periods_ps", "setup_corner", "ss_sensitivity_ps", "ss_sensitivity_tns_ps", "corner_sta_tt", "post_sdc", "corner_sta",
                                                            "drc_metrics", "drc_skipped")},
                       benches=j.get("benches", {}), no_bench_reason=spec.get("no_bench_reason"),
                       checks=j.get("checks", {}), calibration=j.get("calibration"), cycles_added=spec.get("cycles_added"), status="CLOSED",
                       closed_at=now_iso(), job_spec=spec, io_budget=(j.get("rebudget") or {}).get("rb") or "link_budget_consistent (fixed split)",
                       rebudget=j.get("rebudget"))
        (cwt / rec_dir / "verdict.json").write_text(json.dumps(verdict, indent=1) + "\n")
        git("add", "--sparse", "--", *tos, cwd=cwt)
        staged = sh(["git", "-C", str(cwt), "diff", "--cached", "--name-only"], timeout=120).stdout.split()
        msg = (f"closure-loop: {spec['block']} CLOSED {setup_corner_label(metrics)} {metrics['ss_ps']:+.2f} / FF {metrics['ff_ps']:+.2f} ps DRC "
               f"{metrics['drc']}{setup_sensitivity_text(metrics)} {measured_clock_text(metrics)} (source {j['commit_full'][:9]}, {host_cfg(j['host'])['label']} "
               f"{j['run']}); job {j['name']}, owner {spec['owner']}\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n")
        if staged:
            git("-c", "user.name=OpenTallas closure-loop", "-c", "user.email=boj@01.me", "commit", "-q", "-m", msg,
                cwd=cwt)
        out["record_branch"] = branch
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
        return merge_record(j, out, sparse, dry)
    out["merge"] = "no merge target"
    if claude_owns_main():
        notify_claude_record(j["name"], branch, out["branch_commit"])
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
        stage = r.get("stage_key", "-")
        if r["status"] == "READY":
            stages = stage_list(r["spec"])
            stage = stages[min(r.get("stage_idx", 0), len(stages) - 1)]["key"]
        L.append(f"- {r['name']} [{r['spec']['block']}] {r['status']} stage={stage} host={h} "
                 f"run={r.get('run', '-')} since={r.get('stage_started', r['created'])} "
                 f"{('| ' + r['wait']) if r.get('wait') else ''}")
    L += ["", "## Recent terminal"]
    for r in done:
        L.append(f"- {r['name']} [{r['spec'].get('block', '?')}] {r['status']} {r.get('reason', '')[:200]}")
    fl = ["", "## Fleet (measured load1, MemAvailable; admission: load1 + own launches of last 10 min <= 3 x cores, "
          "free RAM >= peak + max(5% RAM, 32 GB))"]
    for h in hosts_table():
        r = ssh(h["name"], "cut -d' ' -f1 /proc/loadavg; awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo", timeout=30)
        v = r.stdout.split()
        if len(v) == 2:
            ld = float(v[0])
            running = sum(1 for x in act if x.get("host") == h["name"] and
                          x["status"] in ("RUNNING", "ECO", "SUMMARY", "ECO_INSTALL"))
            benches = sum(1 for x in act for b in (x.get("btrack") or {}).values()
                          if b.get("host") == h["name"] and b.get("state") == "running")
            fl.append(f"- {h['label']}: load1 {ld:.0f}/{h['cores']} threads (idle {max(0, 100 * (1 - ld / h['cores'])):.0f}%), "
                      f"{v[1]} GB free of {h.get('ram_gb', '?')}, own active stages {running}, parallel benches {benches}")
        else:
            fl.append(f"- {h['label']}: unreachable")
    L[3:3] = fl
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


def preserve_completed_route(j, st, why):
    """Stop infrastructure repair at the existing route; never turn it into a reroute."""
    if st["kind"] != "route":
        return False
    v = j["spec"].get("verdict", {})
    if not v.get("corner_sta") or not v.get("drc_metrics"):
        return False
    root = str(Path(subst(v["corner_sta"], j)).parent)
    metrics = subst(v["drc_metrics"], j)
    if "/logs/" not in metrics:
        return False
    base = str(Path(metrics.replace("/logs/", "/results/", 1)).parent)
    config = dict(route_root=root, odb_patterns=[base + "/6_final.odb", base + "/5_2_route.odb"])
    r = ssh(j["host"], postroute_probe_command(config), timeout=60)
    try:
        if r.returncode:
            raise ValueError(f"probe exited {r.returncode}")
        evidence = json.loads(r.stdout)
    except (ValueError, TypeError):
        j["wait"] = "completed-route evidence unavailable; retry read before crash recovery"
        return True
    if evidence is None:
        return False
    j["postroute_repair"] = dict(host=j["host"], run=j["run"], stage=j["stage_tag"],
                                source_commit=j.get("commit_full"), evidence=evidence, failure=why)
    j["wait"] = None
    finish(j, "NEEDS_HUMAN", "post-route helper failed; completed physical artifacts preserved",
           "NEEDS_HUMAN: repair post-route helper and resume diagnostics against existing route; "
           "no automatic reroute or migration\n" + ", ".join(x["path"] for x in evidence["helper_errors"]))
    return True


def stage_output_dirs(j, st):
    """the directories a stage writes: spec "out_dir" (str or list, placeholders allowed), else for calibrate / route the
    loop's {RUN}/routes/{LABEL}[_cal] convention"""
    out = st.get("out_dir")
    if out:
        return [subst(d, j) for d in ([out] if isinstance(out, str) else out)]
    if st["kind"] in ("calibrate", "route"):
        return [f"{j['run']}/routes/{label(j['name'])}{'_cal' if st['kind'] == 'calibrate' else ''}"]
    return []


def retry_aside(j, st):
    """LOOP-GAPS 2026-10-08: a re-run of a killed / crashed stage (same-host retry, restart) moves the previous attempt's
    output aside as <dir>.attempt<N> (kept as evidence) so the relaunch starts clean: a leftover prep/ masked core_p's
    real error with FileExistsError (flow-triage 10-07), s81 route_view.sh refused existing evidence (rc=73)."""
    prev = j["attempt"] - 1
    return "".join(f"if [ -e {shlex.quote(d)} ]; then a={shlex.quote(f'{d}.attempt{prev}')}; [ -e \"$a\" ] && "
                   f"a=\"$a.$(date +%s)\"; mv {shlex.quote(d)} \"$a\"; fi\n" for d in stage_output_dirs(j, st))


# CRASH-TRIAGE 2026-10-08: twelve routes went NEEDS_HUMAN as "crashed twice (rc=1 ok-check failed: ; ...)" while the
# real errors (yosys Assert, syntax error, [ERROR ODB-0239], a hook's "no room on S", a FileNotFoundError) sat in
# routes/<label>/flow.log, run.log, sta.log, prep/yosys.log or the ORFS step logs.  first_error() reads them on the
# host and returns the first real error line (plus the failing make step) for the crash events and the verdict.
FIRST_ERROR_PY = r"""
import glob, os, re, sys
dirs = sys.argv[1:]
STRONG = re.compile(r"(ERROR: .*|Assert `.*|\[ERROR [A-Z]+-\d+\].*|^Error: .*|.*syntax error.*|^FAILED: .*|"
                    r"^[A-Za-z_.]*(Error|Exception): .*|.*refus(es|ed) .*|.*Killed.*|.*Segmentation fault.*|.*core dumped.*)")
GENERIC = re.compile(r"FlowError: .*(failed with exit|failed)\s*\d*:?\s*$")
MAKE = re.compile(r"\*\*\* \[[^\]]*: (do-[\w.]+)\] Error")
def files(d, late):
    if late:
        return [p for p in (os.path.join(d, n) for n in ("sta.log", "corner.log", "STATUS")) if os.path.isfile(p)]
    pri = [os.path.join(d, n) for n in ("flow.log", "run.log", "prep/yosys.log")]
    orfs = sorted(glob.glob(os.path.join(d, "work/orfs/logs/*/*/*/*.log")) + glob.glob(os.path.join(d, "work/*.log")),
                  key=lambda p: os.path.getmtime(p), reverse=True)[:3]
    return [p for p in pri + orfs if os.path.isfile(p)]
found, step, generic = [], "", ""
def scan(late):
  global step, generic
  for d in dirs:
    for p in files(d, late):
        try:
            lines = open(p, errors="replace").read().splitlines()[-20000:]
        except OSError:
            continue
        for i, ln in enumerate(lines):
            m = MAKE.search(ln)
            if m and not step:
                step = m.group(1)
            t = ln.strip()
            if not t or "WARNING" in t[:12] or t.startswith("Warning"):
                continue
            if t.startswith("Traceback (most recent call last)"):
                tb = next((x.strip() for x in lines[i + 1:i + 200] if re.match(r"^[A-Za-z_.]*(Error|Exception|Exit)\b", x)), "")
                if tb:
                    found.append((p, tb))
                continue
            if GENERIC.search(t):
                generic = generic or t
                continue
            if STRONG.search(t):
                found.append((p, t))
        if found:
            return
scan(False)
if not found:
    # no error-shaped line: a failed flow's own last word (run_abi3_physical refusals print a bare sentence, e.g.
    # "--memory-macro is a place-and-route option ... run --stages pnr"), unless the status says the flow passed
    for d in dirs:
        st = os.path.join(d, "status")
        if os.path.isfile(st) and re.search(r"^flow_rc=0$", open(st, errors="replace").read(), re.M):
            continue
        for n in ("flow.log", "run.log"):
            p = os.path.join(d, n)
            if os.path.isfile(p):
                last = [x.strip() for x in open(p, errors="replace").read().splitlines()[-50:] if x.strip()]
                if last:
                    found.append((p, last[-1]))
                    break
        if found:
            break
if not found:
    scan(True)
if found:
    p, t = found[0]
    print(f"{os.path.relpath(p, os.path.dirname(dirs[0]))}: {t[:240]}" + (f" [step {step}]" if step else ""))
elif generic or step:
    print((generic[:240] + " " if generic else "") + (f"[step {step}]" if step else ""))
"""


def first_error(j, st):
    """The first real error line of a crashed stage, read on its host ('' when none is found or the host is down)."""
    dirs = stage_output_dirs(j, st)
    if not dirs:
        return ""
    try:
        r = ssh(j["host"], "python3 - " + " ".join(shlex.quote(d) for d in dirs), timeout=120, input=FIRST_ERROR_PY)
    except Exception:  # noqa: BLE001 - diagnostics must never turn a crash into a daemon error
        return ""
    return r.stdout.strip().splitlines()[-1][:400] if r.returncode == 0 and r.stdout.strip() else ""


def crash(j, st, fleet, why):
    if preserve_completed_route(j, st, why):
        return
    if st["kind"] in ("calibrate", "route") and j.get("stage_tag") and j.get("host"):
        txt = fp_lint_failed(j["host"], j["run"], j["stage_tag"])
        if txt:
            fp_lint_finish(j, j["stage_tag"], txt)
            return
    if st["kind"] == "route" and j.get("stage_tag") and j.get("host"):
        txt = preroute_failed(j["host"], j["run"], j["stage_tag"])
        if txt:
            preroute_finish(j, j["stage_tag"], txt)
            return
    tail = stage_tail(j, st) if j.get("stage_tag") else ""
    m = re.search(r"CALIBRATE_FAIL class=(\S+) detail=(.*)", tail)
    if st["kind"] == "calibrate" and m and m.group(1) in CAL_OWNER_ACTION:
        j.setdefault("crashes", []).append(dict(stage=st["key"], host=j["host"], attempt=j["attempt"], why=why,
                                                resource=False, cls=m.group(1), tail=tail[-1500:]))
        act = CAL_OWNER_ACTION[m.group(1)]
        finish(j, "NEEDS_HUMAN", f"calibrate {m.group(1)}: {act}"[:300],
               f"NEEDS_HUMAN: calibrate failed, class {m.group(1)} (deterministic, not retried)\n"
               f"detail: {m.group(2).strip()[:200]}\nOWNER ACTION ({j['spec'].get('owner')}): {act}")
        return
    err = first_error(j, st) if st["kind"] != "bench" else ""
    if err:
        why = re.sub(r"ok-check failed: *(;|$)", "ok-check failed;", why)
        why = f"{why}; first error: {err}"
    if st["kind"] == "route" and "GRT-0116" in (err + tail) and not why.startswith("LOST"):
        # stuckscan 2026-10-08: GRT gave up with congestion -- deterministic for this floorplan; a retry re-spends the
        # whole route (hbm_coll_port_big/rows, s81b-vm_bgh-grid: 'retry once on the same host')
        finish(j, "EARLY_FAIL_CONGESTION", f"global route finished with congestion (GRT-0116): {err[:200]}",
               f"EARLY_FAIL_CONGESTION: GRT-0116, not retried (deterministic). Fix the floorplan (util/channels/pins); "
               f"congestion reports in the route's reports dir.\n{err[:300]}")
        return
    resource = bool(RESOURCE_RE.search(tail + " " + err)) or why.startswith(("LOST", "bench tool crash"))
    j.setdefault("crashes", []).append(dict(stage=st["key"], host=j["host"], attempt=j["attempt"], why=why,
                                            resource=resource, tail=tail[-1500:], first_error=err))
    if j["retries_used"] >= 1:
        finish(j, "NEEDS_HUMAN", f"{st['key']} crashed twice ({why}; resource={resource})"[:600],
               f"NEEDS_HUMAN: {st['key']} crashed twice ({why}); last log tail:\n" +
               "\n".join(tail.strip().splitlines()[-6:]))
        return
    j["retries_used"] = 1
    j["attempt"] += 1
    if resource and not checkpoint_location(j):
        h, _ = fleet.choose(j["spec"], exclude=j["hosts_tried"])
        if h:
            event(j, f"{st['key']} crashed ({why}); resource-related -> retry once on {host_cfg(h)['label']}")
            j["hosts_tried"].append(h)
            j["host"], j["run"] = h, f"{host_cfg(h)['base']}/{j['name']}"
            j["status"] = "SYNC"
            # Keep existing bench receipts; the bench chain retains its producer host/run.
            # Resume the migrated physical track at its first non-bench stage.
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
    head = (f"NEEDS_RTL: {setup_corner_label(m)} {m.get('ss_ps')} / FF {m.get('ff_ps')} ps / DRC {m.get('drc')} "
            f"(line {setup_corner_label(m)} >= +{SS_MIN:g} / FF >= +{FF_MIN:g} / DRC 0){'; checks failed: ' + ', '.join(j['failed_checks']) if j.get('failed_checks') else ''}")
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


def job_held(j):
    """STATE/held.json {job name: reason}: a QUEUED job listed there is not admitted (owner option B pause of SS-wall
    work).  Remove the entry to release it."""
    try:
        return json.loads((STATE / "held.json").read_text()).get(j["name"])
    except (FileNotFoundError, ValueError):
        return None


def job_priority(j):
    """STATE/priority.json {job name: int} (coordinator steering; default 0) or spec "priority" """
    return 0    # OWNER 2026-10-08 02:30: priority mechanism REMOVED (377 entries idled EPYC1/2/4); every job equal
    try:
        table = json.loads((STATE / "priority.json").read_text())
    except (FileNotFoundError, ValueError):
        table = {}
    return int(table.get(j["name"], j["spec"].get("priority", 0)) or 0)


def yield_to_priority(j, fleet, host=None):
    """a job below a priority job still waiting for capacity does not take a host THAT JOB CAN USE (host-scoped:
    20:05 a fleet-wide yield idled every host).  host None (QUEUED, no host yet): yield only if every host this job
    could take is wanted by a waiting priority job."""
    return False    # OWNER 2026-10-08 02:30: never yield; fill the fleet
    waits = getattr(fleet, "prio_hosts", {})      # host -> highest waiting priority that can use it
    mine = job_priority(j)
    if host is not None:
        return waits.get(host, 0) > mine
    return bool(waits) and all(waits.get(h["name"], 0) > mine for h in hosts_table()
                               if fleet.compatible(h["name"], j["spec"]))


def launch_ready(j, fleet, spec, stl, st):
    """READY at a remote stage: capacity check + reservation (caller holds FLEET_LOCK); returns the stage to launch
    OUTSIDE the lock (launch_now) or None."""
    require_checkpoint_location(j)
    if True:
        if st["kind"] in ("calibrate", "route") and yield_to_priority(j, fleet, j["host"]):
            why = f"yielding {host_cfg(j['host'])['label']} to a waiting priority job"
            if j.get("wait") != why:
                j["wait"] = why
                event(j, f"{st['key']} {why}")
            return          # neither launches nor moves hosts while it yields
        ok, why = fleet.fits(j["host"], st["threads"], st["ram"], j["name"])
        if not ok:
            j.setdefault("wait_since", time.time())
        if not ok and not checkpoint_location(j) and st["kind"] in ("calibrate", "route") and time.time() - j["wait_since"] >= 120:
            # nothing of this job is in flight: move it to another allowed host that fits now (re-sync, re-calibrate)
            h, _ = fleet.choose(spec, exclude=[j["host"]])
            if h:
                fleet.launched(h, spec.get("threads", 16), spec.get("peak_ram_gb", 32), j["name"])  # 2026-10-08: claim, no herd moves
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
            if route_key_full(keys, key, j["name"]):
                finish(j, "REFUSED", f"{MAX_ROUTES_PER_KEY} routes per source commit: {key} already routed by jobs {keys[key]}",
                       f"REFUSED: {key} already routed by jobs {keys[key]}")
                return
            if j["name"] not in keys.setdefault(key, []):
                keys[key].append(j["name"])
            keys_path().write_text(json.dumps(keys, indent=1) + "\n")
        fleet._launched(j["host"], st["threads"], st["ram"], j["name"])  # reservation (replaces the job's claim)
        return st


def launch_now(j, fleet, st):
    """launch a reserved stage (no FLEET_LOCK held: the ssh calls of one launch no longer stall every other job)"""
    launch_stage(j, st, st["cmd"])
    j["status"] = "RUNNING"
    event(j, f"launched {st['key']} (attempt {j['attempt']}) on {j['host']}")
    experiment(j, f"running: {st['key']} on {host_cfg(j['host'])['label']}")


# ---- parallel bench track (OWNER 2026-10-07 05:00 "LAUNCH IMMEDIATELY"): exactness benches run beside
# calibrate -> route independently; one bench at a time stays beside its first producer artifacts.
# Benches gate ADOPTION, not launch.  A bench with the wrong
# verdict stops the route and ends the job NEEDS_RTL; the verdict waits until every bench has its expected verdict.
# Opt out per job with spec "bench_first": true (benches before the route, as before).


def bench_stages(stl):
    return [x for x in stl if x["kind"] == "bench"]


def bench_par_decide(j, stl):
    """decide once, when the job first leaves QUEUED / its first stage: parallel unless bench_first or no benches"""
    if "bench_par" in j:
        return
    started = bool(j.get("stage_tag")) or j.get("stage_idx", 0) > 0
    j["bench_par"] = bool(bench_stages(stl)) and j["spec"].get("bench_first") is not True and not started
    if j["bench_par"]:
        j["btrack"] = {}
        j["stage_idx"] = next(i for i, x in enumerate(stl) if x["kind"] != "bench")
        event(j, f"benches run in parallel with calibrate/route ({len(bench_stages(stl))} benches; spec bench_first opts out)")


def _bview(j, e):
    """a job view addressing one bench-track stage (its own host / run / tag)"""
    v = dict(j)
    v.update(host=e["host"], run=e["run"], stage_tag=e["tag"])
    if e.get("stage_source"):
        v["stage_source"] = e["stage_source"]
    return v


def benches_done(j, stl):
    return all(k["key"] in j.get("benches", {}) for k in bench_stages(stl))


def bench_location(j, stl):
    """A serial bench chain shares artifacts even if the physical track moves hosts.

    Recover older state from the first launched bench; completed receipts stay
    untouched. Never copy or rerun a producer merely because its route migrated.
    """
    if j.get("bench_location"):
        return j["bench_location"]
    for st in bench_stages(stl):
        entry = (j.get("btrack") or {}).get(st["key"])
        if entry and entry.get("host") and entry.get("run"):
            match = re.search(r"\.a([0-9]+)b[0-9]+$", entry.get("tag", ""))
            location = dict(host=entry["host"], run=entry["run"],
                            attempt=int(match.group(1)) if match else j["attempt"])
            j["bench_location"] = location
            return location
    return dict(host=j["host"], run=j["run"], attempt=j["attempt"])


def vanished_bench_location(j, location):
    """drive-1013 2026-10-08: a bench chain pinned to another host's run (an offload, or the run before a migration)
    outlives that run when a disk purge deletes it.  Every launch then failed 'cat > .../cl/<bench>.sh: No such file'
    until 10 loop errors (qfd_embed_scale_bank_retained-24bd6a53b-tt), and a human retry did not help: it popped
    bench_location, but bench_location() re-derived it from the DONE btrack receipts on the same deleted run.  If the
    run's src is gone (an explicit MISSING, never an ssh failure), forget the location and every receipt made there:
    their artifacts went with it, so the chain re-runs on the job's own run (or a fresh offload)."""
    r = ssh(location["host"], f"test -d {shlex.quote(location['run'])}/src && echo PRESENT || echo MISSING", timeout=60)
    if r.returncode != 0 or "MISSING" not in r.stdout:
        return False
    gone = location["run"]
    tr = j.get("btrack") or {}
    lost = [k for k, e in tr.items() if e.get("run") == gone]
    for k in lost:
        tr.pop(k, None)
        (j.get("benches") or {}).pop(k, None)
    j.pop("bench_location", None)
    event(j, f"bench track: artifact run {location['host']}:{gone} no longer exists (purged); dropped it and the "
             f"receipts made there ({', '.join(lost) or 'none'}): the bench chain restarts")
    return True


def offload_bench_location(j, fleet, st):
    """a host with the job's bench tools and room for one bench; the source is synced there to <base>/<name>-bench"""
    need = bench_needs(j["spec"])
    for cfg in hosts_table():
        h = cfg["name"]
        if h == j["host"] or cfg.get("smoke_only") or not need <= set(cfg.get("caps", [])):
            continue
        if not fleet.compatible(h, dict(j["spec"], stages={"bench": j["spec"].get("stages", {}).get("bench", [])})):
            continue
        with FLEET_LOCK:
            ok, _ = fleet.fits(h, st["threads"], st["ram"])
        if not ok:
            continue
        v = dict(j, host=h, run=f"{cfg['base']}/{j['name']}-bench", resume=None, checkpoint_affinity=None)
        try:
            sync_source(v)
        except Exception as ex:  # noqa: BLE001
            event(j, f"bench offload: source sync to {h} failed: {str(ex)[:200]}")
            continue
        with FLEET_LOCK:
            fleet._launched(h, 0, 0)
        return dict(host=h, run=v["run"], attempt=j["attempt"])
    return None


def bench_track(j, fleet, stl):
    """advance the bench track; returns False if the job ended (bench failure)"""
    if not j.get("bench_par") or j["status"] in TERMINAL or j["status"] in ("QUEUED", "SYNC", "MIGRATING"):
        return True
    tr = j.setdefault("btrack", {})
    for st in bench_stages(stl):
        k = st["key"]
        if k in j["benches"]:
            continue
        e = tr.get(k)
        if e is None or e.get("state") == "retry":
            if any(x.get("state") == "running" for x in tr.values()):
                return True                  # one bench at a time
            location = bench_location(j, stl)
            if location["run"] != j.get("run") and vanished_bench_location(j, location):
                location = bench_location(j, stl)
            caps = next((x.get("caps", []) for x in hosts_table() if x["name"] == location["host"]), None)
            if not j.get("bench_location") and caps is not None and not bench_needs(j["spec"]) <= set(caps):
                off = offload_bench_location(j, fleet, st)
                if off is None:
                    why = f"no host with {sorted(bench_needs(j['spec']))} fits the bench now"
                    if j.get("bwait") != why:
                        j["bwait"] = why
                        event(j, f"bench track: {k} waiting: {why}")
                    return True
                location = off
                j["bench_location"] = location
                event(j, f"bench track: offloaded to {location['host']}:{location['run']} (job host {j['host']} lacks bench tools)")
            host = location["host"]
            fleet.probe(host)
            with FLEET_LOCK:
                ok, why = fleet.fits(host, st["threads"], st["ram"])
                if not ok:
                    if j.get("bwait") != why:
                        j["bwait"] = why
                        event(j, f"bench track: {k} waiting for capacity on artifact host {host}: {why}")
                    return True
                fleet._launched(host, st["threads"], st["ram"])
            n = (e or {}).get("n", 0) + 1
            v = dict(j, host=host, run=location["run"], attempt=f"{location['attempt']}b{n}")
            launch_stage(v, st, st["cmd"])
            j["bench_location"] = location
            tr[k] = dict(state="running", tag=v["stage_tag"], host=host, run=location["run"], n=n, started=now_iso(), stage_source=v.get("stage_source"))
            j["bwait"] = None
            event(j, f"bench track: launched {k} ({v['stage_tag']}) beside {j.get('stage_key')}")
            return True
        v = _bview(j, e)
        state, rc = poll_stage(v)
        if state == "RUNNING":
            to = bench_timed_out(v, st, e.get("started"))
            if to:
                caught, note = to
                e["state"] = "done"
                j["benches"][k] = dict(expect=st["expect"], rc=None, ok=caught, tail=note, track="parallel", timeout=True)
                if caught:
                    event(j, f"bench track: {k} {note}: mutant detected in its log before the hang -> FAIL as expected")
                    return True
                stop_main_for_bench(j)
                finish(j, "NEEDS_RTL", f"{k} {note} without a verdict (bench bug: no cycle cap?)",
                       f"NEEDS_RTL: bench {k} {note}; expect {st['expect'].upper()} but its log shows no verdict -- a bench "
                       "that never terminates is a bench bug (add a cycle cap), not a pass (parallel track; route stopped)")
                return False
        if state in ("RUNNING", "STARTING", "UNREACHABLE"):
            return True
        ok_extra, _ = remote_ok(v, st.get("ok"))
        tail = stage_tail(v, st, 40)
        crashed = state == "LOST" or bench_crashed(st, rc, tail)
        if crashed:
            if e["n"] < 2:
                e["state"] = "retry"
                event(j, f"bench track: {k} crashed (state {state}, rc={rc}); retry once")
                return True
            stop_main_for_bench(j)
            finish(j, "NEEDS_HUMAN", f"{k} crashed twice in the bench track (rc={rc})",
                   f"NEEDS_HUMAN: bench {k} crashed twice (rc={rc}); route stopped\n" + "\n".join(tail.strip().splitlines()[-5:]))
            return False
        passed = bench_outcome(v, st, rc, ok_extra)
        j.setdefault("bench_work", {}).update(v.get("bench_work") or {})
        e["state"] = "done"
        j["benches"][k] = dict(expect=st["expect"], rc=rc, ok=passed, tail=tail[-600:], track="parallel")
        if not passed:
            stop_main_for_bench(j)
            finish(j, "NEEDS_RTL", f"{k} expected {st['expect'].upper()} but rc={rc}",
                   f"NEEDS_RTL: bench {k} expected {st['expect'].upper()}, got rc={rc} (parallel track; route stopped)\n" +
                   "\n".join(tail.strip().splitlines()[-5:]))
            return False
        event(j, f"bench track: {k} {('PASS' if st['expect'] == 'pass' else 'FAIL as expected')} (rc={rc}) "
                 f"{(j.get('bench_work') or {}).get(k, '')}")
    return True


BENCH_TIMEOUT_S = 2 * 3600   # UNSTICK 2026-10-08: per-bench wall clock (spec bench timeout_s overrides)


def bench_timed_out(v, st, started):
    """a bench past its wall clock: kill its process group and read its log.  Returns None (within time), else
    (caught, note): an expect=FAIL bench counts as caught ONLY if its log already shows the detection (fail_regex, or a
    ^FAIL line); a mutant that hangs the design without a cycle cap is a bench bug, never a pass."""
    lim = st.get("timeout_s") or BENCH_TIMEOUT_S
    try:
        el = time.time() - dt.datetime.fromisoformat(started).timestamp()
    except Exception:  # noqa: BLE001
        return None
    if el < lim:
        return None
    ssh(v["host"], f"p=$(cat {v['run']}/cl/{v['stage_tag']}.pid 2>/dev/null); [ -n \"$p\" ] && kill -TERM -- -$p 2>/dev/null; "
                   f"sleep 5; [ -n \"$p\" ] && kill -KILL -- -$p 2>/dev/null; true", timeout=60)
    r = ssh(v["host"], f"tail -n 20000 {v['run']}/cl/{v['stage_tag']}.log", timeout=180)
    full = r.stdout if r.returncode == 0 else ""
    caught = st["expect"] == "fail" and (re.search(st["fail_regex"], full, re.M) is not None if st.get("fail_regex")
                                         else re.search(r"^FAIL\b", full, re.M) is not None)
    return caught, f"timed out after {el / 3600:.1f} h (limit {lim / 3600:.1f} h)"


def stop_main_for_bench(j):
    """a bench failed: stop the job's own main-track stage (route / calibrate / ECO) -- its result cannot be adopted"""
    if j["status"] in ("RUNNING", "ECO", "ECO_INSTALL", "SUMMARY"):
        try:
            kill_own_stage(j)
            event(j, f"bench failed: stopped {j.get('stage_key')} ({j.get('stage_tag')})")
        except Exception as ex:  # noqa: BLE001
            event(j, f"bench failed: could not stop {j.get('stage_key')}: {ex}")


STUCK_S = 3 * 3600          # quiet-output observation threshold, never a kill deadline
STUCK_CHECK_S = 1800


def stuck_watchdog(j, st):
    """Report quiet output without imposing a runtime deadline or restarting work."""
    now = time.time()
    if now - j.get("wd_checked", 0) < STUCK_CHECK_S:
        return
    j["wd_checked"] = now
    try:
        started = dt.datetime.fromisoformat(j.get("stage_started")).timestamp()
    except Exception:  # noqa: BLE001
        return
    if now - started < STUCK_S:
        return
    mins = STUCK_S // 60
    r = ssh(j["host"], f"find {j['run']}/cl {j['run']}/routes {j['run']}/bench -newermt '-{mins} minutes' -type f "
                       f"-print -quit 2>/dev/null; echo END", timeout=300)
    if r.returncode or "END" not in r.stdout:
        return                          # unreachable / slow: no verdict this time
    if r.stdout.replace("END", "").strip():
        return
    # Quiet tool output is not proof that synthesis or routing stopped making progress.
    # Keep the process and all completed objects; the owner can inspect actual CPU/
    # process state. Capacity guards, not elapsed time, protect the host.
    if not j.get("quiet_output_reported"):
        j["quiet_output_reported"] = now_iso()
        event(j, f"observation: {st['key']} wrote no file for {mins // 60} h; process preserved")


EARLY_CHECK_S = 900
STARTING_TIMEOUT_S = 3600


def early_fail_gate(j, st):
    """EARLY-FAIL GATES (OWNER 2026-10-08, stream stuckscan): every 15 min a RUNNING route's ORFS run is probed
    (stuckscan.probe: post-placement / post-CTS TT setup metrics, the live hold repair, GRT congestion reports, DRT
    violation series) and a hopeless run stops at once with EARLY_FAIL_SETUP / _HOLD / _CONGESTION / _DRC plus its
    worst-path summary, instead of spending hours in repair/route.  Thresholds: stuckscan.GATES (calibrated on the
    loop's finished TT routes; README "Early-fail gates").  Spec "early_fail": false opts out."""
    now = time.time()
    if j["spec"].get("early_fail") is False or now - j.get("ef_checked", 0) < EARLY_CHECK_S:
        return
    import stuckscan
    if stuckscan.protected(j):     # CRITICAL_PATH 1 (BF): stuckscan reports it, never auto-stopped
        return
    j["ef_checked"] = now
    try:
        import stuckscan
        stuckscan.cl = sys.modules[__name__]
        res, err = stuckscan.probe(j["host"], [dict(name=j["name"], run=j["run"], tag=j.get("stage_tag"), live=True)],
                                   cpu=False, timeout=300)
        if not res:
            return
        o = res["jobs"].get(j["name"]) or {}
        bs = [b for b in o.get("bases") or [] if not b["design"].endswith("_cal")]
        if not bs:
            return
        b = max(bs, key=lambda x: max([lg[1] for lg in x["logs"]] or [0]))
        hp = stuckscan.hopeless(b, j, res.get("now", now))
    except Exception:  # noqa: BLE001
        log(f"[{j['name']}] early-fail gate error:\n{traceback.format_exc()}")
        return
    if not hp:
        return
    verdict, why = hp[0][0], "; ".join(w for _, w in hp)
    if verdict == "HOLD_STOP":
        plan = stuckscan.hold_stop_plan(b)
        try:
            hold_stop_resume(j, plan["stage"], plan["buffers"], why)
            return
        except Exception as ex:  # noqa: BLE001  (already stopped once / no checkpoint: early-fail as before)
            event(j, f"HOLD-STOP not possible ({ex}); early-fail instead")
            verdict = "EARLY_FAIL_HOLD"
    detail = dict(name=j["name"], verdict=verdict, why=[w for _, w in hp], orfs=b["root"], corner=b.get("corner"),
                  step=(b.get("current") or "")[:-8], setup=stuckscan.gate_metrics(b), hold=b.get("hold"),
                  congestion=b.get("congestion"), drt=(b.get("drt") or [])[-12:], paths=stuckscan.path_classes(b),
                  block=j["spec"].get("block"), owner=j["spec"].get("owner"), gates=stuckscan.GATES)
    (STATE / "early_fail").mkdir(parents=True, exist_ok=True)
    (STATE / "early_fail" / f"{j['name']}.json").write_text(json.dumps(detail, indent=1))
    early_fail_finish(j, verdict, why, detail)
    try:
        stuckscan.failtrig_item(dict(detail, action="early_fail", kind="hopeless"))
    except Exception:  # noqa: BLE001
        pass


# ---- parallel calibrate (OWNER 2026-10-08 "calibration must not gate the route"): the route starts at once on the
# block's previous-measured insertion (STATE/measured_insertion.json), else its budget sheet insertion; the no-repair
# CTS-only calibrate runs beside it (j["ctrack"]).  The verdict waits for it; when the measured insertion differs from
# the route's assumption by more than CAL_REROUTE_PS, the route is redone ONCE on the measured numbers (calib.env now
# holds them).  The loop has no generic measured-clock re-STA, so a CLOSED verdict on an assumption that moved by more
# than the threshold is re-routed as well (conservative: it was never timed at the measured insertion).
# Without an assumption (no measurement, no sheet) calibrate stays sequential (minutes now: no repair).
# SYNTH-RESTA 2026-10-08: the measured-clock re-STA exists now (measured_resta / meas_resta.py): before re-routing, the
# finished route is re-timed at sign-off (TT setup + FF hold) with its IO SDCs regenerated from the MEASURED insertion;
# the route is redone only if that re-STA fails, or if no measured SDC can be derived for the recipe (route scripts
# that write the IO SDC internally: 'echo ...' sdc_cmd).
CAL_REROUTE_PS = 50.0


def measured_sdc_args(j):
    """meas_resta.py arguments that give a finished route its IO model at the MEASURED insertion: (args, None) or
    (None, why).  Budget jobs: the sign-off budget SDCs the loop regenerated from the measurement (budget_check) replace
    the route's copies; sdc_cmd jobs: the recipe's sdc_cmd re-run on the measured env, inserted after the base SDC."""
    env = (j.get("calibration") or {}).get("env")
    if not env:
        return None, "no measured env"
    stages = j["spec"].get("stages")
    rc = (stages.get("route") or {}).get("cmd", "") if isinstance(stages, dict) else ""
    run = j["run"]
    if j.get("budget"):
        if not (j["budget"].get("check") or {}).get("ok") or (j["budget"].get("insertion_used") or {}).get("grade") != "measured":
            return None, "budget SDCs were not regenerated from the measurement (flagged or audited sheet)"
        m1 = re.search(r"cp \$BUDGET_SDC_SIGNOFF (\S+)", rc)
        m2 = re.search(r"cat \$BUDGET_SDC_FF; echo '\}'; \} > (\S+)", rc)
        if not m1:
            return None, "route cmd does not install $BUDGET_SDC_SIGNOFF as a sign-off post-SDC"
        args = ["--replace", f"{m1.group(1)}={run}/cl/budget_signoff.sdc"]
        if m2:
            r = ssh(j["host"], f"{{ echo 'if {{[llength [get_libs -quiet *_FF_*]]}} {{'; cat {run}/cl/budget_ff.sdc; echo '}}'; }} "
                               f"> {run}/cl/meas_budget_ff_guarded.sdc", timeout=60)
            if r.returncode:
                return None, "measured budget_ff.sdc unreadable"
            args += ["--replace", f"{m2.group(1)}={run}/cl/meas_budget_ff_guarded.sdc"]
        return args, None
    sdc_cmd = (j.get("ctrack") or {}).get("sdc_cmd")
    if not sdc_cmd:
        return None, "no sdc_cmd"
    out = re.search(r"--out\s+(\S+)", sdc_cmd)
    cmd = sdc_cmd.replace(out.group(0), f"--out {run}/cl/meas_io.sdc") if out else sdc_cmd
    text = "".join(f"{k}={v}\n" for k, v in env.items())
    r = ssh(j["host"], f"cat > {run}/cl/calib.measured.env", input=text, timeout=60)
    if r.returncode:
        return None, "cannot write calib.measured.env"
    r = ssh(j["host"], f"cd {run}/src && set -a && . {run}/cl/calib.measured.env && set +a && ( {subst(cmd, j)} )", timeout=600)
    if r.returncode:
        return None, f"sdc_cmd failed on the measured env (rc={r.returncode})"
    if out:
        path = f"{run}/cl/meas_io.sdc"
    else:
        last = (r.stdout.strip().splitlines() or [""])[-1].strip()
        if not last.endswith(".sdc"):
            return None, "sdc_cmd names no SDC file (the route script writes its IO SDC internally)"
        path = last if last.startswith("/") else f"{run}/src/{last}"
    if ssh(j["host"], f"test -s {shlex.quote(path)}", timeout=60).returncode:
        return None, f"measured SDC {path} missing"
    return ["--insert", path], None


def measured_resta(j, m):
    """the measured-clock re-STA of the finished route (once per route attempt): None when not needed, else the record
    {available, tt, ff, ...}"""
    c = j.get("ctrack") or {}
    if c.get("state") != "done" or c.get("delta_ps", 0) <= CAL_REROUTE_PS or j.get("cal_rerouted"):
        return None
    mr = j.get("meas_resta")
    if mr and mr.get("attempt") == j["attempt"]:
        return mr
    mr = dict(attempt=j["attempt"], at=now_iso(), delta_ps=c.get("delta_ps"), available=False)
    orfs = m.get("orfs_dir") or (m.get("raw") or {}).get("orfs_dir")
    args, why = (None, "no orfs_dir in the verdict metrics") if not orfs else measured_sdc_args(j)
    if not args:
        mr["why"] = why
    else:
        with TT_STA_SLOTS:
            ship_helpers(j["host"], j["run"])
            r = ssh(j["host"], f"python3 {j['run']}/cl/meas_resta.py --orfs {shlex.quote(orfs)} --src {j['run']}/src "
                               f"--out {j['run']}/cl/meas_resta.a{j['attempt']}.json " + " ".join(shlex.quote(x) for x in args),
                    timeout=12000)
        try:
            res = json.loads([x for x in r.stdout.splitlines() if x.startswith("{")][-1])
            tt, ff = res["setup_tt"].get("worst_slack_ps"), res["hold_ff"].get("worst_slack_ps")
            errs = (res["setup_tt"].get("errors") or []) + (res["hold_ff"].get("errors") or []) + \
                [res[k]["error"] for k in ("setup_tt", "hold_ff") if res[k].get("error")]
            mr.update(available=tt is not None and ff is not None and not errs, tt=tt, ff=ff, errors=errs[:5],
                      args=args, json=f"{j['run']}/cl/meas_resta.a{j['attempt']}.json")
            if not mr["available"]:
                mr["why"] = f"re-STA incomplete (TT {tt} / FF {ff}; {errs[:2]})"
        except (IndexError, ValueError, KeyError, TypeError) as ex:
            mr["why"] = f"re-STA output unreadable ({ex}; rc={r.returncode})"
    j["meas_resta"] = mr
    event(j, f"measured-clock re-STA (insertion moved {c.get('delta_ps', 0):.0f} ps): " +
             (f"TT setup {mr['tt']:+.2f} / FF hold {mr['ff']:+.2f}" if mr["available"] else f"unavailable: {mr['why']}"))
    return mr


# FLOW-IOREF 2026-10-08: every finished route is SIGNED OFF against its OWN routed clock tree.  The IO SDCs carry a
# virtual-clock latency from the calibrate run's CTS (or an assumed / sheet insertion); the routed tree differs (hbm_pkt
# ii1r/ii1rb: FF vclk 363/402 from calibrate vs routed FF mean ~307/314 -> output-port-only hold -43/-45; pre-DRT repair
# reached +50 against the same wrong reference).  The die clock plan aligns every block's NOMINAL insertion, so the
# routed mean is the truth: meas_resta.py re-times the route (TT setup, FF hold; no re-route) with
# physical/common_flow/io_ref_routed.sdc read LAST, which moves every insertion-reference virtual clock (vclk*, ot_lb_v_*,
# nbr_clk) to the mean boundary-register clock arrival of THAT corner (H1 uncertainties unchanged).  Its numbers are the
# verdict; the routed insertion goes to measured_insertion.json as the block's die-plan value; the post-route hold ECO
# gets the same SDC as its last post-SDC.  Spec "routed_ioref": false opts out.
IOREF_SDC = "physical/common_flow/io_ref_routed.sdc"
# FLOW-FIX-0410 2026-10-09: io_ref_routed.sdc reads the ACTIVE-edge insertion (sinks behind an odd clock inversion were
# T/2 late).  The version is part of the routed_ioref cache key, so ioref-rejudge / a verdict re-STA under the new rule
# instead of returning a re-STA cached under the old one.
IOREF_VERSION = "ae0410"


def routed_ioref(j, m):
    """re-STA of the finished route at its own routed insertion (cached per route attempt / installed ECO): None when
    not applicable, else {available, tt, ff, ioref{tt, ff}, ...}"""
    if j["spec"].get("routed_ioref") is False:
        return None
    orfs = m.get("orfs_dir") or (m.get("raw") or {}).get("orfs_dir")
    if not orfs:
        return None
    key = f"{j['attempt']}|{orfs}|{int(bool((j.get('eco') or {}).get('installed')))}|{IOREF_VERSION}"
    rbj = j.get("rebudget") or {}
    if rbj.get("sdc"):
        key += f"|{rbj['rb']}"
    rr = j.get("routed_ioref")
    if rr and rr.get("key") == key:
        return rr
    rr = dict(key=key, at=now_iso(), available=False)
    out = f"{j['run']}/cl/routed_ioref.a{j['attempt']}" + (f".{rbj['rb']}" if rbj.get("sdc") else "") + ".json"
    with TT_STA_SLOTS:
        ship_helpers(j["host"], j["run"])
        ssh(j["host"], f"mkdir -p {j['run']}/src/physical/common_flow && cp {j['run']}/cl/io_ref_routed.sdc "
                       f"{j['run']}/src/{IOREF_SDC}", timeout=60)
        app = f"--append {j['run']}/cl/io_ref_routed.sdc"
        if rbj.get("sdc"):
            # REBUDGET (tools/budgets/rebudget.py): the block's re-derived IO budget (budget_rb<N>) read after the routed
            # reference, so the verdict is the IO paths against the CURRENT die-link budget
            rp = f"{j['run']}/cl/{rbj['rb']}.sdc"
            ssh(j["host"], f"cat > {rp}", input=Path(rbj["sdc"]).read_text(), timeout=60)
            app += f" --append {rp}"
        r = ssh(j["host"], f"python3 {j['run']}/cl/meas_resta.py --orfs {shlex.quote(orfs)} --src {j['run']}/src "
                           f"--out {out} {app}", timeout=12000)
    try:
        res = json.loads([x for x in r.stdout.splitlines() if x.startswith("{")][-1])
        tt, ff = res["setup_tt"].get("worst_slack_ps"), res["hold_ff"].get("worst_slack_ps")
        errs = (res["setup_tt"].get("errors") or []) + (res["hold_ff"].get("errors") or []) + \
            [res[k]["error"] for k in ("setup_tt", "hold_ff") if res[k].get("error")]
        io = dict(tt=res["setup_tt"].get("ioref") or {}, ff=res["hold_ff"].get("ioref") or {})
        rr["ioref_edge"] = dict(tt=res["setup_tt"].get("ioref_edge") or {}, ff=res["hold_ff"].get("ioref_edge") or {})
        rr.update(available=tt is not None and ff is not None and not errs, tt=tt, ff=ff, errors=errs[:5], ioref=io,
                  tt_i2r=res["setup_tt"].get("worst_input_to_reg_slack_ps"), tt_out=res["setup_tt"].get("worst_output_port_slack_ps"),
                  ff_i2r=res["hold_ff"].get("worst_input_to_reg_slack_ps"), ff_out=res["hold_ff"].get("worst_output_port_slack_ps"),
                  ff_r2r=res["hold_ff"].get("worst_reg_to_reg_slack_ps"), json=out)
        if not rr["available"]:
            rr["why"] = f"re-STA incomplete (TT {tt} / FF {ff}; {errs[:2]})"
        # a corner whose SDC has no insertion-reference virtual clock is unchanged by the re-STA: keep the route's own
        # sign-off number there (the bare re-STA does not reproduce every recipe's sign-off: dshead-elemB-safe TT
        # -201 route vs +121 re-STA with no clock moved)
        for c, k in (("tt", "ss_ps"), ("ff", "ff_ps")):
            if rr["available"] and not io[c] and not rbj.get("sdc"):
                rr[c + "_resta_raw"], rr[c] = rr[c], m.get(k)
        if rr["available"] and (rr["tt"] is None or rr["ff"] is None):
            rr.update(available=False, why="route sign-off number missing for an unchanged corner")
    except (IndexError, ValueError, KeyError, TypeError) as ex:
        rr["why"] = f"re-STA output unreadable ({ex}; rc={r.returncode})"
    j["routed_ioref"] = rr
    ref = lambda c: ", ".join(f"{v} {d['mean']:.0f}" for v, d in sorted(rr.get("ioref", {}).get(c, {}).items())) or "none"
    if rbj.get("sdc"):
        rr["rebudget"] = rbj["rb"]
    event(j, "routed-insertion IO re-STA" + (f" under {rbj['rb']}" if rbj.get("sdc") else "") + ": " + (f"TT setup {rr['tt']:+.2f} / FF hold {rr['ff']:+.2f} (route SDC "
             f"{m.get('ss_ps')} / {m.get('ff_ps')}); routed reference TT [{ref('tt')}] FF [{ref('ff')}]"
             if rr["available"] else f"unavailable: {rr['why']}"))
    if rr["available"]:
        record_routed(j, rr)
    return rr


def record_routed(j, rr):
    """the routed insertion (mean boundary-register clock arrival per corner, from the sign-off re-STA) replaces the
    calibrate value in STATE/measured_insertion.json: the die clock plan's per-block nominal insertion"""
    pick = {}
    for c in ("tt", "ff"):
        vs = list((rr.get("ioref") or {}).get(c, {}).values())
        if vs:
            v = max(vs, key=lambda d: d["n"])
            pick[c] = dict(mean=round(v["mean"]), min=round(v["min"]), max=round(v["max"]), n=v["n"], kind=v["kind"],
                           clock=v["clock"])
    if "ff" not in pick:
        return
    p = STATE / "measured_insertion.json"
    with open(STATE / "measured.lock", "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        d = json.loads(p.read_text()) if p.exists() else {"schema": "opentallas.closure_loop.measured_insertion.v1",
                                                          "blocks": {}}
        old = (d.get("variants") or {}).get(variant_key(j["spec"])) or d["blocks"].get(j["spec"]["block"]) or {}
        e = dict(old, job=j["name"], source_commit=j.get("commit_full"), host=j["host"], run=j["run"],
                 parasitics="routed (6_final.spef)", grade="routed", measured_at=now_iso(), ff=pick["ff"],
                 calibrate=old.get("calibrate") or ({k: old.get(k) for k in ("ss", "ff", "parasitics", "job")} if old else None))
        if "tt" in pick:
            e["tt"] = pick["tt"]
        e.pop("block", None)
        d["blocks"][j["spec"]["block"]] = e
        _store_variant(d, j, e)
        d["updated"] = now_iso()
        p.write_text(json.dumps(d, indent=1) + "\n")
        (STATE / "measured.dirty").write_text(now_iso())


def assumed_insertion(j):
    # bf-insertion 2026-10-08: only a SAME-VARIANT measurement is an assumption (see variant_key); the budget-sheet
    # fallback below stays (a sheet is per master/pin contract, not per variant)
    m, why = same_variant_insertion(j)
    if m is None and why and "another variant" in why:
        j["ins_assume_skip"] = why
    if route_ref(j):
        # CALIB-CORNER: a TC/TT route references its IO to the TT insertion: the block's routed TT (grade routed), else
        # a calibrate's TT; none -> no assumption (sequential CTS-only calibrate, minutes)
        if not (m and m.get("tt") and m.get("ff")):
            return None, None
        t = m["tt"]
        env = {}
        for k, key in (("MEAN", "mean"), ("MIN", "min"), ("MAX", "max")):
            env[f"CK_SS_{k}"] = env[f"CK_SS_ALL_{k}"] = env[f"CK_TT_{k}"] = env[f"CK_TT_ALL_{k}"] = round(float(t[key]))
            env[f"CK_FF_{k}"] = env[f"CK_FF_ALL_{k}"] = round(float(m["ff"][key]))
            if m.get("ss"):
                env[f"CK_SSLIB_{k}"] = round(float(m["ss"][key]))
        env["CK_ROUTE_REF"] = "TT"
        return env, (f"measured_insertion.json TT ({m.get('grade') or 'calibrate'}, {m.get('job')}, "
                     f"{m.get('measured_at')})")
    if m and m.get("ss") and m.get("ff"):
        v = dict(ss=m["ss"]["mean"], ss_min=m["ss"]["min"], ss_max=m["ss"]["max"],
                 ff=m["ff"]["mean"], ff_min=m["ff"]["min"], ff_max=m["ff"]["max"])
        src = f"measured_insertion.json ({m.get('job')}, {m.get('measured_at')})"
    else:
        ins = (j.get("budget") or {}).get("insertion") or {}
        if not all(k in ins for k in ("ss", "ff")):
            return None, None
        v = dict(ss=ins["ss"], ss_min=ins.get("ss_min", ins["ss"]), ss_max=ins.get("ss_max", ins["ss"]),
                 ff=ins["ff"], ff_min=ins.get("ff_min", ins["ff"]), ff_max=ins.get("ff_max", ins["ff"]))
        src = f"budget sheet ({ins.get('grade')})"
    env = {}
    for c in ("ss", "ff"):
        for k, key in (("MEAN", c), ("MIN", c + "_min"), ("MAX", c + "_max")):
            env[f"CK_{c.upper()}_{k}"] = env[f"CK_{c.upper()}_ALL_{k}"] = round(float(v[key]))
    return env, src


def start_parallel_calibrate(j, stl, st):
    if j["spec"].get("calibrate_parallel") is False:
        return False
    c0 = j.get("ctrack")
    if c0 and c0.get("state") == "done" and c0.get("measured"):
        # moved back to calibrate (pre-CTS host move): the measurement exists, route on it
        env, src = {**c0["assumed"], **{k: v for k, v in c0["measured"].items() if v is not None}}, "measured (parallel calibrate)"
    else:
        # a pending / running / failed track of an earlier placement (host move) is replaced
        env, src = assumed_insertion(j)
    if not env:
        why = j.pop("ins_assume_skip", None)
        if why:
            event(j, f"no same-variant measured insertion ({why}): calibrate first (CTS-only), route after")
        return False
    if c0 and c0.get("state") == "running":
        try:
            ssh(c0["host"], f"p=$(cat {c0['run']}/cl/{c0['tag']}.pid 2>/dev/null); [ -n \"$p\" ] && kill -TERM -- -$p 2>/dev/null; true",
                timeout=60)
        except Exception:  # noqa: BLE001
            pass
    text = "".join(f"{k}={v}\n" for k, v in env.items())
    r = ssh(j["host"], f"mkdir -p {j['run']}/cl && cat > {j['run']}/cl/calib.env && cp {j['run']}/cl/calib.env "
                       f"{j['run']}/cl/calib.assumed.env", input=text, timeout=60)
    if r.returncode:
        return False
    bud = active_budget(j["spec"])
    if route_ref(j) and bud and j.get("budget") and not bud.get("preserve_full_sheet"):
        # CALIB-CORNER: budget route/sign-off SDCs on the assumed route-corner (TT) insertion, not the sheet's SS one
        try:
            ov = dict(ss=env["CK_SS_MEAN"], ss_min=env["CK_SS_MIN"], ss_max=env["CK_SS_MAX"], ff=env["CK_FF_MEAN"],
                      ff_min=env["CK_FF_MIN"], ff_max=env["CK_FF_MAX"], grade="assumed-tt", source=src, over_target=False)
            for fn, text in budget_files(bud, insertion_override=ov).items():
                if not fn.startswith("_"):
                    ssh(j["host"], f"cat > {j['run']}/cl/{fn}", input=text, timeout=60, check=True)
        except Exception as ex:  # noqa: BLE001
            event(j, f"CALIB-CORNER: budget SDCs at the TT assumption failed ({ex}): sequential calibrate")
            return False
    if c0 and c0.get("state") == "done":
        j["stage_idx"] += 1
        event(j, f"calibrate already measured in parallel: route on {src}")
        return True
    j["ctrack"] = dict(state="pending", assumed=env, source=src, sdc_cmd=st.get("sdc_cmd"), n=0,
                       stage_idx=j["stage_idx"])
    j["stage_idx"] += 1
    event(j, f"calibrate in PARALLEL: route starts now on the assumed insertion ({src}: SS {env['CK_SS_MEAN']} / "
             f"FF {env['CK_FF_MEAN']}); the measurement is checked at the verdict")
    return True


def cal_track(j, fleet, stl):
    c = j.get("ctrack")
    if not c or c.get("state") in ("done", "failed") or j["status"] in TERMINAL or \
            j["status"] in ("QUEUED", "SYNC", "MIGRATING") or not j.get("host"):
        return
    st = stl[c["stage_idx"]] if c["stage_idx"] < len(stl) and stl[c["stage_idx"]]["kind"] == "calibrate" else \
        next((x for x in stl if x["kind"] == "calibrate"), None)
    if st is None:
        c["state"] = "failed"
        return
    if c["state"] == "pending":
        fleet.probe(j["host"])
        with FLEET_LOCK:
            ok, why = fleet.fits(j["host"], st["threads"], st["ram"])
            if not ok:
                return
            fleet._launched(j["host"], st["threads"], st["ram"])
        c["n"] += 1
        v = dict(j, attempt=f"{j['attempt']}c{c['n']}")
        launch_stage(v, st, retry_aside(dict(j, attempt=2), st) + st["cmd"])   # an old _cal dir is moved aside
        c.update(state="running", tag=v["stage_tag"], host=j["host"], run=j["run"], started=now_iso())
        event(j, f"parallel calibrate launched ({c['tag']}) beside {j.get('stage_key')}")
        return
    v = dict(j, host=c["host"], run=c["run"], stage_tag=c["tag"])
    state, rc = poll_stage(v)
    if state in ("RUNNING", "STARTING", "UNREACHABLE"):
        return
    if state == "LOST" or rc != 0:
        c["state"] = "failed"
        txt = fp_lint_failed(c["host"], c["run"], c["tag"]) if state != "LOST" else None
        if txt:
            fp_lint_finish(j, c["tag"], txt)
            return
        event(j, f"parallel calibrate failed ({state}, rc={rc}): the route keeps its assumed insertion")
        return
    r = ssh(c["host"], f"cat {c['run']}/cl/calib.json", timeout=60)
    try:
        cj = json.loads(r.stdout)
        j["calibration"] = {k: cj[k] for k in ("ss", "ff", "env", "db", "clock", "parasitics")}
    except (ValueError, KeyError, TypeError) as ex:
        if r.returncode == 255:
            return
        c["state"] = "failed"
        event(j, f"parallel calibrate: calib.json unreadable ({ex}); the route keeps its assumed insertion")
        return
    menv = j["calibration"]["env"]
    c["measured"] = {k: menv.get(k) for k in c["assumed"] if "ALL" not in k}
    c["delta_ps"] = max(abs(float(menv[k]) - float(c["assumed"][k])) for k in ("CK_SS_MEAN", "CK_FF_MEAN") if k in menv)
    c["state"] = "done"
    event(j, f"parallel calibrate: measured SS {menv.get('CK_SS_MEAN')} / FF {menv.get('CK_FF_MEAN')} vs assumed "
             f"{c['assumed']['CK_SS_MEAN']} / {c['assumed']['CK_FF_MEAN']} (max delta {c['delta_ps']:.0f} ps)")
    record_measured(j)
    try:
        dev = budget_check(j)
    except Exception as ex:  # noqa: BLE001
        dev = f"budget check error {ex}"
    if dev:
        c["budget_dev"] = dev
        event(j, f"BUDGET FLAG (parallel calibrate): {dev}")


def cal_reroute(j, stl, closed):
    c = j.get("ctrack") or {}
    if c.get("state") != "done" or c.get("delta_ps", 0) <= CAL_REROUTE_PS or j.get("cal_rerouted"):
        return False
    ri = next((i for i, x in enumerate(stl) if x["kind"] == "route"), None)
    if ri is None:
        return False
    j["cal_rerouted"] = now_iso()
    j["stage_idx"], j["stage_key"] = ri, "route"
    j["attempt"] = (j["attempt"] if isinstance(j["attempt"], int) else 1) + 1
    j["status"] = "READY"
    mr = j.get("meas_resta") or {}
    how = (f"measured-clock re-STA FAILED: TT {mr.get('tt')} / FF {mr.get('ff')}" if mr.get("available")
           else f"no measured-clock re-STA: {mr.get('why', 'not run')}")
    event(j, f"measured insertion moved {c['delta_ps']:.0f} ps > {CAL_REROUTE_PS:.0f} from the route's assumption "
             f"({'CLOSED' if closed else 'NOT CLOSED'} on the assumption; {how}): re-route on the measured insertion")
    return True


def step(j, fleet):
    spec = j["spec"]
    stl = stage_list(spec)
    s = j["status"]
    if s == "READY" and (not j.get("commit_full") or j.get("source_synced") is False):
        j["status"] = "SYNC" if j.get("host") else "QUEUED"
        event(j, "source synchronization incomplete; preserve stage position and synchronize before launch")
        return
    if s in ("QUEUED", "READY", "SYNC") and "bench_par" not in j:
        bench_par_decide(j, stl)
    if not bench_track(j, fleet, stl):
        return
    cal_track(j, fleet, stl)
    if s == "QUEUED" and checkpoint_location(j):
        require_checkpoint_location(j)
        j["status"] = s = "SYNC"  # stay with preserved stage_idx and checkpoint host
    if s == "QUEUED":
        held = job_held(j)
        if held:            # OWNER OPTION B (2026-10-07): SS-wall jobs paused until re-evaluated at TT
            why = f"HELD ({held})"
            if j.get("wait") != why:
                j["wait"] = why
                event(j, why)
            return
        with FLEET_LOCK:
            h, why = (None, "every usable host is wanted by a waiting priority job") \
                if yield_to_priority(j, fleet) else fleet.choose(spec, exclude=[
                    x for x, p in getattr(fleet, "prio_hosts", {}).items() if p > job_priority(j)])
            if h:   # claim capacity now so parallel job threads do not pick the same headroom
                fleet.launched(h, spec.get("threads", 16), spec.get("peak_ram_gb", 32), j["name"])  # 2026-10-08: claim real size
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
        j["status"], j["reason"] = "READY", None   # drop a stale failure reason (e.g. an earlier "not on origin")
        return
    if s == "READY":
        st = stl[j["stage_idx"]]
        j["stage_key"] = st["key"]
        if st["kind"] == "calibrate" and start_parallel_calibrate(j, stl, st):
            return
        if st["kind"] in ("verdict", "collect", "export", "commit") and adoption_held(j):
            return
        if st["kind"] == "verdict":
            if (j.get("ctrack") or {}).get("state") in ("pending", "running"):
                if j.get("wait") != "calibrate":
                    j["wait"] = "calibrate"
                    event(j, "verdict waits for the parallel calibrate")
                return
            if j.get("bench_par") and not benches_done(j, stl):
                if j.get("wait") != "benches":
                    j["wait"] = "benches"
                    event(j, "verdict waits for the parallel bench track")
                return
            return do_verdict(j, fleet, stl)
        if st["kind"] == "commit":
            if j["spec"].get("smoke"):      # host smoke test: timing verdict passed; nothing is recorded or merged
                m = j.get("metrics", {})
                finish(j, "SMOKE_OK", f"smoke test on {j['host']}: {setup_corner_label(m)} {m.get('ss_ps')} / FF {m.get('ff_ps')} / DRC {m.get('drc')}",
                       f"SMOKE_OK on {j['host']}: {setup_corner_label(m)} {m.get('ss_ps')} / FF {m.get('ff_ps')} / DRC {m.get('drc')} (not published)")
                return
            return do_commit(j)
        fleet.probe(j["host"])                 # (cached 45 s) probe outside the lock
        with FLEET_LOCK:
            go = launch_ready(j, fleet, spec, stl, st)
        if go:
            launch_now(j, fleet, go)
        return
    if s == "RUNNING":
        st = stl[j["stage_idx"]]
        state, rc = poll_stage(j)
        if state == "RUNNING" and st["kind"] == "bench":
            to = bench_timed_out(j, st, j.get("stage_started"))
            if to:
                caught, note = to
                j["benches"][st["key"]] = dict(expect=st["expect"], rc=None, ok=caught, tail=note, timeout=True)
                if not caught:
                    finish(j, "NEEDS_RTL", f"{st['key']} {note} without a verdict (bench bug: no cycle cap?)",
                           f"NEEDS_RTL: bench {st['key']} {note}; expect {st['expect'].upper()} but its log shows no "
                           "verdict -- a bench that never terminates is a bench bug, not a pass")
                    return
                event(j, f"{st['key']} {note}: mutant detected in its log before the hang -> FAIL as expected")
                j["stage_idx"] += 1
                j["status"] = "READY"
                return
        if state == "STARTING" and st["kind"] != "bench":
            # stuckscan 2026-10-08: a stage with no pid file long after its launch never started (hbm_pkt_ii3ref route.a3:
            # run dir emptied by a disk sweep, polled STARTING for 16 h) -> the crash path (LOST: retry once elsewhere)
            try:
                age = time.time() - dt.datetime.fromisoformat(j.get("stage_started")).timestamp()
            except Exception:  # noqa: BLE001
                age = 0
            if age > STARTING_TIMEOUT_S:
                return crash(j, st, fleet, f"LOST: stage {j.get('stage_tag')} never started (no pid file {age / 60:.0f} min "
                                           f"after launch)")
        if state in ("RUNNING", "STARTING"):
            if j.get("unreachable"):     # 2026-10-08: clear a stale "unreachable" as the latest event once polling works
                event(j, f"{j['host']} reachable again; {st['key']} still running")
                j["unreachable"] = 0
            stuck_watchdog(j, st)
            if st["kind"] == "route" and state == "RUNNING":
                early_fail_gate(j, st)
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
            if bench_crashed(st, rc, tail):
                return crash(j, st, fleet, f"bench tool crash: rc={rc} ({'negative control' if st['expect'] == 'fail' else 'positive bench'}"
                                           f" with no verdict evidence)")
            passed = bench_outcome(j, st, rc, ok_extra)
            j["benches"][st["key"]] = dict(expect=st["expect"], rc=rc, ok=passed, tail=tail[-600:])
            if not passed:
                finish(j, "NEEDS_RTL", f"{st['key']} expected {st['expect'].upper()} but rc={rc}",
                       f"NEEDS_RTL: bench {st['key']} expected {st['expect'].upper()}, got rc={rc}\n" +
                       "\n".join(tail.strip().splitlines()[-5:]))
                return
            event(j, f"{st['key']} {('PASS' if st['expect'] == 'pass' else 'FAIL as expected')} (rc={rc}) "
                     f"{(j.get('bench_work') or {}).get(st['key'], '')}")
        else:
            if st["kind"] in ("route", "calibrate"):
                hm_auto_events(j)
            if rc != 0 and ok_extra and st["kind"] == "signoff" and st.get("ok"):
                # a sign-off script that exits non-zero for "not closed" but wrote its evidence (the job's ok check
                # passes) is a verdict, not a crash: w2-rb-safe-no2/no3 exited 1 on SS -18.9 and the retry then refused
                # to overwrite the evidence -> false NEEDS_HUMAN. The verdict stage judges the numbers.
                event(j, f"{st['key']} rc={rc} with its evidence present (ok check passed): judged at the verdict")
            elif rc != 0 or not ok_extra:
                return crash(j, st, fleet, f"rc={rc}{'' if ok_extra else ' ok-check failed: ' + okout.strip()[-200:]}")
            event(j, f"{st['key']} done (rc={rc})")
            if st["kind"] == "calibrate":
                r = ssh(j["host"], f"cat {j['run']}/cl/calib.json", timeout=60)
                if r.returncode == 255:
                    j["wait"] = "completed calibration: artifact transport unavailable"
                    return  # Retry the read, never the completed physical stage.
                try:
                    if r.returncode:
                        raise ValueError(f"artifact read exited {r.returncode}")
                    c = json.loads(r.stdout)
                    j["calibration"] = {k: c[k] for k in ("ss", "ff", "env", "db", "clock", "parasitics")}
                    if not isinstance(c["env"], dict):
                        raise ValueError("calibration env must be an object")
                except (ValueError, KeyError, TypeError) as ex:
                    finish(j, "NEEDS_HUMAN", f"completed calibration artifact invalid: {ex}",
                           "NEEDS_HUMAN: inspect/recover calib.json; completed physical stage preserved")
                    return
                j["wait"] = None
                event(j, "calibrated insertion " + " ".join(f"{k}={v}" for k, v in c["env"].items() if "ALL" not in k))
                record_measured(j)
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
                    event(j, f"budget check OK: measured insertion {j['budget']['check']['measured_ss']:g} <= target "
                             f"{j['budget']['insertion']['target_ss']:g} (sheet {j['budget']['insertion']['ss']:g}); budget SDCs "
                             f"regenerated from the measured insertion")
                    record_measured(j)
        j["stage_idx"] += 1
        j["status"] = "READY"
        return
    if s in ("ECO", "ECO_INSTALL"):
        state, rc = poll_stage(j)
        if state in ("RUNNING", "STARTING", "UNREACHABLE"):
            return
        if s == "ECO":
            r = ssh(j["host"], f"cat {eco_output(j)}/result.json 2>/dev/null", timeout=60)
            try:
                res = json.loads(r.stdout)
            except Exception:  # noqa: BLE001
                res = None
            j["eco"]["result"] = res
            ok = eco_passes(res, rc)
            vt = j["eco"].get("kind") == "vtswap"
            event(j, f"{'VT-swap' if vt else 'hold'} ECO {'PASS' if ok else 'MISS'}: {res if res else 'no result (rc=' + str(rc) + ')'}")
            if not ok:
                ledger(j, f"{'VT-SWAP' if vt else 'HOLD'}-ECO missed: before SS {j['eco']['pre']['ss_ps']:+.2f} / FF {j['eco']['pre']['ff_ps']:+.2f}, "
                          f"after {res}")
                m = j.get("metrics", {})
                prev = j["eco"]
                if vt and vtswap_eligible(j, m, j.get("failed_checks") or []) and start_vtswap_eco(j, fleet, m):
                    if j["eco"] is prev:   # no capacity yet: re-judged at the verdict stage next tick, which relaunches
                        j["status"] = "READY"
                    return             # next VT-swap target launched
                if not summarize_failure(j, fleet, m):
                    text = failure_text(j)
                    finish(j, "NEEDS_RTL", text.split("\n")[0][11:], text)
                return
            st = dict(key="eco_install", kind="eco_install", threads=1, ram=4)
            launch_stage(j, st, eco_install_cmd(j))
            j["status"], j["stage_key"] = "ECO_INSTALL", "eco_install"
            return
        if rc != 0:
            finish(j, "NEEDS_HUMAN", f"hold ECO passed but install/re-export failed (rc={rc})",
                   f"NEEDS_HUMAN: hold ECO passed ({j['eco']['result']}) but install/re-export failed rc={rc}; see {j['run']}/cl")
            return
        j["eco"]["installed"] = now_iso()
        ledger(j, f"HOLD-ECO installed: SS {j['eco']['pre']['ss_ps']:+.2f}/FF {j['eco']['pre']['ff_ps']:+.2f} -> "
                  f"SS {j['eco']['result']['ss_ps']:+.2f}/FF {j['eco']['result']['ff_ps']:+.2f}, DRC {j['eco']['result']['drc']}, "
                  f"{j['eco']['result'].get('cells_added')} cells; re-verdict")
        j["status"] = "READY"          # stage_idx still points at the verdict: re-judged on the ECO sign-off
        return
    if s == "SUMMARY":
        state, rc = poll_stage(j)
        if state in ("RUNNING", "STARTING", "UNREACHABLE"):
            return
        text = failure_text(j)
        finish(j, "NEEDS_RTL", text.split("\n")[0][11:], text)


def adoption_held(j):
    """A live owner hold prevents adoption while physical evidence can finish."""
    path = STATE / "adoption_holds" / f"{j['name']}.json"
    if not path.exists():
        return False
    reason = json.loads(path.read_text())["reason"]
    note = f"adoption hold: {reason}"
    if j.get("wait") != note:
        j["wait"] = note
        event(j, note)
    return True


def hm_auto_lines(text):
    """OT_HM_AUTO report lines (tools/orfs_hold_mm.tcl ot_hm_guard) -> event texts"""
    return [ln.split("OT_HM_AUTO", 1)[1].strip() for ln in text.splitlines() if ln.startswith("OT_HM_AUTO")]


def hm_auto_events(j):
    """HM-GUARD (2026-10-08): a route-time hold repair that auto-reduced its margin (too many endpoints inside HM / too
    much projected buffer area) leaves REPORTS_DIR/ot_hm_auto_<stage>.rpt: one job event per report and attempt"""
    try:
        r = ssh(j["host"], f"cat $(find {j['run']}/routes -name 'ot_hm_auto_*.rpt' 2>/dev/null | head -4) "
                           f"</dev/null 2>/dev/null", timeout=60)
    except Exception as ex:  # an event is informative only: never fail a stage on it
        log(f"[{j['name']}] hm_auto_events: {ex}")
        return
    seen = j.setdefault("hm_auto_seen", [])
    for ln in hm_auto_lines(r.stdout or ""):
        key = f"{j.get('attempt')}|{ln}"
        if key not in seen:
            seen.append(key)
            event(j, ln)
    j["hm_auto_seen"] = seen[-20:]


RECORD_DIR = "{RUN}/record"


def precollect_cmd(spec):
    """drive-0212 2026-10-09: the collect stage runs AFTER the verdict, but a verdict check may read what collect writes
    (s81-dsfd-hstnh-515-pe-4a12f4d5d-tc-cl: lef_check_MATCH on {RUN}/record/check.json, written only by collect's
    s81_die_view_ports check), so the check could never pass (TT +84.94 / FF +8.01 / DRC 0 -> NEEDS_RTL).  When a check
    reads {RUN}/record and the collect command writes it, the verdict runs the collect command first (collect is an
    idempotent export: it runs again after the verdict as before)."""
    col = ((spec.get("stages") or {}).get("collect") or {}).get("cmd") or ""
    checks = (spec.get("verdict") or {}).get("checks") or []
    if RECORD_DIR in col and any(RECORD_DIR in (c.get("cmd") or "") for c in checks):
        return col
    return None


def do_verdict(j, fleet, stl):
    if adoption_held(j):
        return
    v = j["spec"].get("verdict", {})
    m = get_metrics(j)
    if re.search(r"kex_exchange|Connection (reset|refused|closed|timed out)|ssh:", str(m.get("error", ""))):
        j["verdict_ssh_fail"] = j.get("verdict_ssh_fail", 0) + 1
        if j["verdict_ssh_fail"] < 20:
            event(j, f"verdict: ssh to {j['host']} failed, retrying next tick")
            return
    j["metrics"] = m
    checks, failed = {}, []
    pre = precollect_cmd(j["spec"])
    if pre:
        ok, out = remote_ok(j, pre, timeout=3600)
        if not ok and TRANSIENT_RE.search(out):
            raise RuntimeError(f"verdict pre-collect: ssh/network failure: {out.strip()[-200:]}")
        event(j, f"verdict: ran the collect stage first (a check reads {{RUN}}/record): rc {'0' if ok else 'nonzero'}"
                 + ("" if ok else f": {out.strip()[-200:]}"))
    for c in v.get("checks", []):
        # verdict checks may run real tools (stn_pa_check.sh routes a pin-access probe: > 300 s on AGIdock, which put
        # hbm_stn_mcast_r5/r6 into NEEDS_HUMAN as "loop errors"); spec checks[].timeout_s, default 1800
        ok, out = remote_ok(j, c["cmd"], timeout=c.get("timeout_s", 1800))
        if not ok and TRANSIENT_RE.search(out):
            # an ssh failure is not a failed check (hbm_stn_mcast_r6b: 'Connection reset by peer' failed lef_check_MATCH
            # while check.json said MATCH): raise, so the verdict backs off and is re-taken
            raise RuntimeError(f"verdict check {c['name']}: ssh/network failure: {out.strip()[-200:]}")
        checks[c["name"]] = dict(ok=ok, out=out[-300:])
        if not ok and restates_line(c):
            checks[c["name"]]["restates_line"] = True     # judged by the line itself, below (drive-0212)
        elif not ok:
            failed.append(c["name"])
    j["checks"], j["failed_checks"] = checks, failed
    if (j.get("eco") or {}).get("installed"):     # the post-route hold ECO replaced the route: its DRC counts
        m["drc"], m["eco"] = j["eco"]["result"]["drc"], j["eco"]["result"]
    ss, ff, drc = m.get("ss_ps"), m.get("ff_ps"), m.get("drc")
    if ss is None or ff is None or drc is None:
        finish(j, "NEEDS_HUMAN", f"verdict inputs missing ({json.dumps(m)[:300]})",
               f"NEEDS_HUMAN: verdict inputs missing: {json.dumps(m)[:400]}")
        return
    benches_ok = all(b["ok"] for b in j["benches"].values()) and benches_done(j, stl)
    closed = ss >= SS_MIN and ff >= FF_MIN and drc == 0 and not failed and benches_ok and not m.get("errors")
    event(j, f"verdict {setup_corner_label(m)} {ss:+.2f} / FF {ff:+.2f} / DRC {drc} / checks failed {failed} -> "
             f"{'CLOSED' if closed else 'NOT CLOSED'}")
    rr = routed_ioref(j, m)
    if rr and rr.get("available"):
        # FLOW-IOREF: the sign-off IS the routed-insertion re-STA (either direction); the route-SDC numbers are kept
        m.update(setup_corner="tt", ss_ps=rr["tt"], ff_ps=rr["ff"], routed_ioref=rr, route_sdc_clock=dict(ss_ps=ss, ff_ps=ff),
                 post_sdc=list(m.get("post_sdc") or []) + ([IOREF_SDC] if IOREF_SDC not in (m.get("post_sdc") or []) else []))
        if m.get("setup_post_sdc") and IOREF_SDC not in m["setup_post_sdc"]:
            # setup-only post-SDCs (nbr_clk_measured: -source latency) are read after the post-SDCs: re-read it last
            m["setup_post_sdc"] = list(m["setup_post_sdc"]) + [IOREF_SDC]
        ss, ff = rr["tt"], rr["ff"]
        closed = ss >= SS_MIN and ff >= FF_MIN and drc == 0 and not failed and benches_ok and not m.get("errors")
        j["metrics"] = m
        event(j, f"verdict at the ROUTED insertion: TT {ss:+.2f} / FF {ff:+.2f} -> {'CLOSED' if closed else 'NOT CLOSED'}")
    # the calibrate-insertion re-STA / re-route is moot once the route is timed on its own tree
    mr = None if (rr and rr.get("available")) else measured_resta(j, m)
    if mr and mr.get("available"):
        mclosed = mr["tt"] >= SS_MIN and mr["ff"] >= FF_MIN and drc == 0 and not failed and benches_ok
        if mclosed:
            # the finished route signs off on the MEASURED clock: no re-route; its verdict numbers are the measured ones
            m.update(setup_corner="tt", ss_ps=mr["tt"], ff_ps=mr["ff"], measured_resta=mr, assumed_clock=dict(ss_ps=ss, ff_ps=ff))
            j["metrics"], ss, ff, closed = m, mr["tt"], mr["ff"], True
            event(j, f"measured-clock re-STA CLOSES the route (TT {ss:+.2f} / FF {ff:+.2f}): no re-route")
    if not (rr and rr.get("available")) and not (mr and mr.get("available") and closed) and cal_reroute(j, stl, closed):
        return
    if closed:
        j["stage_idx"] += 1
        j["status"] = "READY"
        experiment(j, f"running: collect/export/merge ({setup_corner_label(m)} {ss:+.1f} / FF {ff:+.1f})")
        return
    if ff < FF_MIN:
        # UNSTICK 2026-10-08: route-time hold repair stopped by the hold-stall guard (orfs_hold_mm.tcl): the window is
        # structural (pin registers / input-min / H1 SDC), a hold ECO would crawl the same way -> NEEDS_RTL with it
        r = ssh(j["host"], f"for f in $(find {j['run']}/routes -name 'ot_hold_stall_*.rpt' -not -path '*_cal/*' 2>/dev/null "
                           f"| head -2); do echo \"== $f\"; head -45 $f; done", timeout=120)
        # drive-0828: the guard only holds when the STALLED window explains the sign-off miss.  A repair that stalled at
        # a residue far shallower than the final FF number (h1hm80: CTS stall I2O=2@-0.2, sign-off FF -8.2 on reg->out
        # at the routed reference) left the miss to post-route degradation: that is the post-route hold ECO's job.
        wins = re.findall(r"^([IR]2[OR])\s+(\d+)\s+(-?[\d.]+)", r.stdout, re.M)
        stall_worst = min((float(c) for _, _, c in wins), default=None)
        if "OT_HOLD_STALL" in r.stdout and stall_worst is not None and stall_worst > ff + 2.0:
            event(j, f"hold-stall window worst {stall_worst:+.1f} is shallower than sign-off FF {ff:+.1f}: "
                     f"the miss grew after the stalled repair -> post-route hold ECO, not NEEDS_RTL")
        elif "OT_HOLD_STALL" in r.stdout:
            j["hold_window"] = r.stdout[-6000:]
            cls = " ".join(f"{a}={b}@{c}" for a, b, c in wins)
            finish(j, "NEEDS_RTL", f"FF hold {ff:+.1f}: route hold repair stalled; window {cls}"[:300],
                   f"NEEDS_RTL: FF hold {ff:+.1f} ps after a STALLED route-time hold repair (hold-stall guard). Window by "
                   f"path class: {cls}. Structural fix per REDESIGN_RULES (pin registers / input-min, H1 SDC); no ECO.\n"
                   + r.stdout[-2500:])
            return
    if hold_only(j, m, failed, benches_ok) and start_hold_eco(j, fleet, m):
        return
    if vtswap_eligible(j, m, failed, benches_ok) and start_vtswap_eco(j, fleet, m):
        return
    if combo_eligible(j, m, failed, benches_ok) and start_combo_eco(j, fleet, m):
        return
    if not summarize_failure(j, fleet, m):
        text = failure_text(j)
        finish(j, "NEEDS_RTL", text.split("\n")[0][11:], text)


def eco_passes(res, rc):
    if rc != 0 or not isinstance(res, dict) or res.get("errors"):
        return False
    # option B: setup is judged at TT (tt_ps; older results carry it in ss_ps)
    for key, minimum in (("tt_ps" if "tt_ps" in res else "ss_ps", SS_MIN), ("ff_ps", FF_MIN)):
        value = res.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < minimum:
            return False
    return type(res.get("drc")) in (int, float) and res["drc"] == 0


LINE_COND_RE = re.compile(r"""\b[A-Za-z_]\w*\[["'](setup_tt|hold_ff)["']\]\s*\[["']worst_slack_ps["']\]\s*>=\s*(-?[\d.]+)""")


def restates_line(c):
    """drive-0212 (coordinator APPROVED 2026-10-09): a verdict check that only restates the TT/FF acceptance line
    (owner_TT_FF_nonnegative: corner_sta.json setup_tt / hold_ff worst_slack_ps >= 0, 18 specs) is not an independent
    condition.  Counted as a failed check it blocked the one fix that applies: qfd_emb_pc_00-0ebf67a31-tc, TT +15.99 /
    FF -59.47 / DRC 0, never got its post-route hold ECO.  Such a check is recorded but never counts as failed: the
    line itself is judged on the metrics (route, routed insertion, or the installed ECO).  A check is a restatement
    iff spec says "restates_line": true, or its command only reads corner_sta.json and asserts setup_tt >= SS_MIN /
    hold_ff >= FF_MIN (nothing stricter: owner_SS_FF_15ps keeps counting)."""
    if c.get("restates_line") is True:
        return True
    cmd = c.get("cmd") or ""
    if "corner_sta.json" not in cmd:
        return False
    conds = LINE_COND_RE.findall(cmd)
    if not conds:
        return False
    for key, val in conds:
        if float(val) != (SS_MIN if key == "setup_tt" else FF_MIN):
            return False
    m = re.search(r"\bassert\b(.*?)(?:['\"]\s*$|;|$)", cmd, re.S)
    if not m or not re.fullmatch(r"\s*C(\s+and\s+C)*\s*", LINE_COND_RE.sub("C", m.group(1))):
        return False
    files = set(re.findall(r"[\w{}./-]+\.(?:json|rpt|log|txt|csv)", cmd))
    return bool(files) and all(x.endswith("corner_sta.json") for x in files)


def blocking_checks(j):
    """the job's recorded failed checks minus restatements of the line (records written before drive-0212)"""
    rest = {c.get("name") for c in (j["spec"].get("verdict") or {}).get("checks", []) if restates_line(c)}
    return [x for x in (j.get("failed_checks") or []) if x not in rest]


def hold_only(j, m, failed=(), benches_ok=True):
    return (m.get("ss_ps") is not None and m["ss_ps"] >= SS_MIN and m.get("drc") == 0 and m.get("ff_ps") is not None
            and m["ff_ps"] < FF_MIN and not failed and benches_ok and not (j.get("eco") or {}).get("tried")
            and (j["spec"].get("hold_eco") or {}).get("enabled", True) is not False)


def vtswap_targets(j):
    he = j["spec"].get("hold_eco") or {}
    return [float(t) for t in he.get("vtswap_targets", VTSWAP_TARGETS)]


def vtswap_eligible(j, m, failed=(), benches_ok=True):
    """a thin TT setup miss the VT-swap ECO may close: TT in [VTSWAP_TT_FLOOR, 0), FF >= 0, DRC 0, no failed check /
    bench / metric error, no installed ECO, VT-swap targets left, not turned off by the spec"""
    he = j["spec"].get("hold_eco") or {}
    e = j.get("eco") or {}
    tt, ff = m.get("ss_ps"), m.get("ff_ps")
    if he.get("enabled", True) is False or he.get("vtswap", True) is False:
        return False
    if tt is None or ff is None or isinstance(tt, bool) or isinstance(ff, bool):
        return False
    if not (VTSWAP_TT_FLOOR <= tt < SS_MIN and ff >= FF_MIN and m.get("drc") == 0):
        return False
    if failed or not benches_ok or m.get("errors") or e.get("installed") or j.get("eco_stack"):
        return False
    if e.get("tried") and e.get("kind") != "vtswap":
        return False
    done = sum(1 for x in [*(j.get("eco_history") or []), e] if (x or {}).get("kind") == "vtswap")
    return done < len(vtswap_targets(j))


def start_vtswap_eco(j, fleet, m):
    """launch vtswap_eco.sh as the job's ECO stage (tag hold_eco.aN, status ECO): the hold-ECO completion path installs /
    re-verdicts / records it unchanged (result.json -> eco_passes -> eco_install_cmd -> verdict)"""
    rb, ob = eco_paths(j, m)
    if not rb:
        return False
    ok, why = fleet.fits(j["host"], 8, 16)
    if not ok:
        event(j, f"VT-swap ECO waiting for capacity: {why}")
        return True            # stays at the verdict stage; the next tick retries
    he, v = j["spec"].get("hold_eco") or {}, j["spec"].get("verdict", {})
    e = j.get("eco") or {}
    hist = [x for x in (j.get("eco_history") or []) if x.get("kind") == "vtswap"]
    n = len(hist) + (1 if e.get("kind") == "vtswap" else 0)
    target = vtswap_targets(j)[n]
    cap = float(he.get("vtswap_cap_pct", VTSWAP_CAP_PCT))
    if e:
        j.setdefault("eco_history", []).append(e)
        j["attempt"] += 1          # a fresh stage tag: hold_eco.a<attempt>.rc of the previous ECO stays as evidence
    post_sdcs = list(m["post_sdc"] if "post_sdc" in m else v.get("post_sdc", []))
    tt = m["ss_ps"]
    out = f"{j['run']}/cl/eco-vtswap-t{target:g}" + (f"-r{len(j.get('eco_history') or []) + 1}" if j.get("eco_history") else "")
    env = (f"TARGET={target:g} CAP_PCT={cap:g} DRC0={int(m['drc'])} ACC_SS={SS_MIN:g} ACC_FF={FF_MIN:g} SETUP_LIB={SETUP_LIB} "
           f"SDC_NAME={shlex.quote(m.get('sdc_name') or '6_final.sdc')} THREADS=8 "
           f"MACROS={shlex.quote(' '.join(v.get('macros', [])))} ORFS_W18={shlex.quote(m.get('orfs_dir') or '')}")
    if m.get("setup_post_sdc"):
        env += f" SETUP_POST_SDC={shlex.quote(' '.join(m['setup_post_sdc']))}"
    cmd = f"{env} bash {{CL}}/vtswap_eco.sh {rb} {ob} {out} {j['spec']['block']} " + " ".join(shlex.quote(p) for p in post_sdcs)
    ship_helpers(j["host"], j["run"])
    j["eco"] = dict(tried=True, kind="vtswap", rb=rb, ob=ob, out=out, post_sdc=post_sdcs, sdc_name=m.get("sdc_name") or "6_final.sdc",
                    setup_post_sdc=list(m.get("setup_post_sdc") or []), pre=dict(ss_ps=tt, ff_ps=m["ff_ps"]),
                    started=now_iso(), target_ps=target, lvt_cap_pct=cap, auto=True)
    st = dict(key="hold_eco", kind="hold_eco", threads=8, ram=16)
    launch_stage(j, st, cmd)
    fleet.launched(j["host"], 8, 16)
    j["status"], j["stage_key"] = "ECO", "hold_eco"
    event(j, f"thin TT setup miss ({setup_corner_label(m)} {tt:+.2f} / FF {m['ff_ps']:+.2f} / DRC 0): post-route VT-swap setup ECO "
             f"(RVT->LVT on TT paths, target {target:g} ps, cap {cap:g} % LVT, FF hold guard, no re-route) on {rb}/6_final.odb")
    ledger(j, f"VT-SWAP ECO launched (loop): TT {tt:+.2f} / FF {m['ff_ps']:+.2f}, target {target:g}, LVT cap {cap:g} %")
    experiment(j, "running: post-route VT-swap setup ECO")
    return True


def combo_eligible(j, m, failed=(), benches_ok=True):
    """a thin TT AND thin FF miss: TT in [COMBO_TT_FLOOR, 0), FF in [COMBO_FF_FLOOR, 0), DRC 0, no failed check / bench /
    metric error, no installed ECO, no combo ECO tried yet, not turned off by the spec (hold_eco.enabled / combo false)"""
    he = j["spec"].get("hold_eco") or {}
    e = j.get("eco") or {}
    tt, ff = m.get("ss_ps"), m.get("ff_ps")
    if he.get("enabled", True) is False or he.get("combo", True) is False:
        return False
    if tt is None or ff is None or isinstance(tt, bool) or isinstance(ff, bool):
        return False
    if not (COMBO_TT_FLOOR <= tt < SS_MIN and COMBO_FF_FLOOR <= ff < FF_MIN and m.get("drc") == 0):
        return False
    if failed or not benches_ok or m.get("errors") or e.get("installed") or j.get("eco_stack"):
        return False
    return not any((x or {}).get("kind") == "combo" for x in [*(j.get("eco_history") or []), e])


def start_combo_eco(j, fleet, m):
    """launch vtswap_eco.sh then hold_eco.sh stacked on its result as the job's ECO stage (tag hold_eco.aN, status ECO);
    the hold-ECO completion path reads {out}/result.json, installs and re-verdicts it unchanged"""
    rb, ob = eco_paths(j, m)
    if not rb:
        return False
    ok, why = fleet.fits(j["host"], 8, 16)
    if not ok:
        event(j, f"combo ECO waiting for capacity: {why}")
        return True            # stays at the verdict stage; the next tick retries
    he, v = j["spec"].get("hold_eco") or {}, j["spec"].get("verdict", {})
    e = j.get("eco") or {}
    if e:
        j.setdefault("eco_history", []).append(e)
        j["attempt"] += 1
    post = list(m["post_sdc"] if "post_sdc" in m else v.get("post_sdc", []))
    pq = " ".join(shlex.quote(p) for p in post)
    n = len(j.get("eco_history") or []) + 1
    outv, out = f"{j['run']}/cl/eco-combo{n}-vt", f"{j['run']}/cl/eco-combo{n}"
    sdcn = shlex.quote(m.get("sdc_name") or "6_final.sdc")
    mac = shlex.quote(" ".join(v.get("macros", [])))
    cap = float(he.get("vtswap_cap_pct", VTSWAP_CAP_PCT))
    blk = j["spec"]["block"]
    venv = (f"TARGET=10 CAP_PCT={cap:g} DRC0=1 ACC_SS={SS_MIN:g} ACC_FF={COMBO_FF_FLOOR:g} SETUP_LIB={SETUP_LIB} SDC_NAME={sdcn} "
            f"THREADS=8 MACROS={mac} ORFS_W18=")
    if m.get("setup_post_sdc"):
        venv += f" SETUP_POST_SDC={shlex.quote(' '.join(m['setup_post_sdc']))}"
    henv = (f"ECO_SESSION=mm ALLOW_FRESH_GRT=0 HM=12 SM=40 FILT=40 PASSES=1 RESAWARE=1 HOLDCELLS=1 ACC_SS={SS_MIN:g} "
            f"ACC_FF={FF_MIN:g} SETUP_LIB={SETUP_LIB} KEEPCLK=0 BUF=30 MACROS={mac} THREADS=8 SDC_NAME={sdcn} ECO_RB_DB=6_final.odb")
    cmd = (f"{venv} bash {{CL}}/vtswap_eco.sh {rb} {ob} {outv} {blk} {pq}; "
           f"VB=$(ls -d {outv}/orfs/results/asap7/*/base | head -1); test -f $VB/6_final.odb || {{ echo COMBO: no vtswap base; exit 3; }}; "
           f"[ -f $VB/{sdcn} ] || cp {ob}/{sdcn} $VB/; "
           f"{henv} bash {{CL}}/hold_eco.sh $VB $VB {out} {blk} {pq}")
    ship_helpers(j["host"], j["run"])
    tt, ff = m["ss_ps"], m["ff_ps"]
    j["eco"] = dict(tried=True, kind="combo", rb=rb, ob=ob, combo_vtswap=outv, out=out, post_sdc=post,
                    sdc_name=m.get("sdc_name") or "6_final.sdc", setup_post_sdc=list(m.get("setup_post_sdc") or []),
                    pre=dict(ss_ps=tt, ff_ps=ff), started=now_iso(), lvt_cap_pct=cap, auto=True)
    launch_stage(j, dict(key="hold_eco", kind="hold_eco", threads=8, ram=16), cmd)
    fleet.launched(j["host"], 8, 16)
    j["status"], j["stage_key"] = "ECO", "hold_eco"
    event(j, f"thin TT AND FF miss ({setup_corner_label(m)} {tt:+.2f} / FF {ff:+.2f} / DRC 0): post-route COMBO ECO "
             f"(VT-swap <= {cap:g} % LVT, then hold ECO HM 12 stacked on it, no re-route) on {rb}/6_final.odb; out {out}")
    ledger(j, f"COMBO ECO launched (loop): TT {tt:+.2f} / FF {ff:+.2f}, LVT cap {cap:g} %")
    experiment(j, "running: post-route combo (VT-swap + hold) ECO")
    return True


def eco_output(j):
    return (j.get("eco") or {}).get("out", f"{j['run']}/cl/eco")


def eco_paths(j, m):
    """(routed pre-fill base holding 5_2_route.odb, sign-off ORFS base holding 6_final.sdc)"""
    v = j["spec"].get("verdict", {})
    dm = (m.get("drc_metrics") or [None])[-1]
    rb = dm.replace("/logs/", "/results/").rsplit("/", 1)[0] if dm else None
    ob = None
    if m.get("orfs_dir"):
        r = ssh(j["host"], f"ls -d {m['orfs_dir']}/results/asap7/*/base | tail -1", timeout=60)
        ob = r.stdout.strip() or None
    return rb, ob or rb


def baked_post_sdcs(j, m, cands):
    """spec verdict post-SDCs that the route's own in-run corner STA already read as {orfs}/w18_extra.sdc (byte-equal)"""
    orfs = m.get("orfs_dir") or (m.get("raw") or {}).get("orfs_dir")
    if not cands or not orfs or not j.get("host") or not j.get("run"):
        return []
    r = ssh(j["host"], "; ".join(f"cmp -s {shlex.quote(orfs)}/w18_extra.sdc {shlex.quote(j['run'] + '/src/' + p)} && echo {shlex.quote(p)}"
                                 for p in cands) + "; true", timeout=60)
    hit = set((r.stdout or "").split())
    return [p for p in cands if p in hit]


def start_hold_eco(j, fleet, m):
    rb, ob = eco_paths(j, m)
    if not rb:
        return False
    ok, why = fleet.fits(j["host"], 8, 32)
    if not ok:
        event(j, f"hold ECO waiting for capacity: {why}")
        return True            # stays at the verdict stage; the next tick retries
    v, he = j["spec"].get("verdict", {}), j["spec"].get("hold_eco") or {}
    # rev 2 (2026-10-07): post-route hold goal +18 (coordinator: die-context margin over the +15 line), endpoint filter, sign-off-exact constraints per corner,
    # resistance-aware re-route, up to 2 ECO -> re-route -> sign-off passes (hold_eco.sh header)
    env = f"ECO_SESSION={shlex.quote(he.get('session', 'mm'))} " \
          f"ALLOW_FRESH_GRT={int(he.get('allow_fresh_grt', False))} " \
          f"HM={he.get('hold_margin_ps', 18)} SM={he.get('setup_margin_ps', 40)} FILT={he.get('setup_filter_ps', 40)} " \
          f"PASSES={he.get('passes', 2)} RESAWARE={int(he.get('resistance_aware', True))} HOLDCELLS={int(he.get('hold_cells', True))} " \
          f"ACC_SS={SS_MIN} ACC_FF={FF_MIN} SETUP_LIB={SETUP_LIB} KEEPCLK={he.get('keep_clock', 0)} BUF={he.get('max_buffer_percent', 30)} " \
          f"MACROS={shlex.quote(' '.join(v.get('macros', [])))} THREADS=8"
    if he.get("repair_drv"):
        # mtp-lead 2026-10-09: opt-in DRV repair inside the ECO (hold_eco.tcl OT_REPAIR_DRV); default off
        env += f" REPAIR_DRV=1 DRV_SLEW_MARGIN={float(he.get('drv_slew_margin', 30)):g} " \
               f"DRV_CAP_MARGIN={float(he.get('drv_cap_margin', 20)):g} DRV_MAX_WIRE={float(he.get('drv_max_wire_um', 0)):g}"
    post_sdcs = list(m["post_sdc"] if "post_sdc" in m else v.get("post_sdc", []))
    baked = baked_post_sdcs(j, m, [p for p in v.get("post_sdc", []) if p not in post_sdcs])
    if baked:
        # COREKV-ECO 2026-10-08: a route whose in-run corner STA read a spec verdict post-SDC as w18_extra.sdc (Qwen core
        # signoff833_skew90.sdc) records post_sdc [] -> the routed-ioref step made it [io_ref_routed.sdc] and the ECO was
        # timed at the 770 ps route SDC (core_kv_banked_fullwidth_h1hm80: FF +38.85 there -> 0 cells; TT -97 = route
        # SDC). The verdict read it, so the ECO reads it too, before io_ref_routed (always last).
        post_sdcs = baked + [p for p in post_sdcs if p != IOREF_SDC] + ([IOREF_SDC] if IOREF_SDC in post_sdcs else [])
        event(j, f"hold ECO: verdict post-SDC(s) {baked} were applied in-run (w18_extra.sdc): passed to the ECO")
    post = " ".join(shlex.quote(p) for p in post_sdcs)
    # LOOP-GAPS 2026-10-08: the ECO is timed (TT setup, option B) and judged with the route's OWN sign-off SDC set: its
    # sign-off SDC (corner_sta sdc_name, e.g. 6_signoff.sdc) and its setup-only post-SDCs (setup_post_sdc, e.g. the
    # measured neighbour clock nbr_clk_measured.sdc) -- not 6_final.sdc's planning neighbour clock (redesign-0315 m3f/m3g)
    env += f" SDC_NAME={shlex.quote(m.get('sdc_name') or '6_final.sdc')}"
    if m.get("setup_post_sdc"):
        env += f" SETUP_POST_SDC={shlex.quote(' '.join(m['setup_post_sdc']))}"
    if j.get("eco_stack"):
        # DRIVE-1243: stacked ECO (retry-eco --stack): the installed ECO's db lives in the route base as 6_final.*
        # (5_2_route.odb there is the PRE-ECO route): ECO that db, sign off from the same base
        rb = ob = j["eco_stack"]["base"]
        env += " ECO_RB_DB=6_final.odb"
    recovery = j.get("eco_overlay_recovery") or {}
    hist = len(j.get("eco_history") or [])
    out = recovery.get("out", f"{j['run']}/cl/eco" + (f"-r{hist + 1}" if hist else ""))   # earlier ECOs stay as evidence
    if recovery:
        env += f" ECO_GUARD={shlex.quote(recovery['guard'])}"
    cmd = f"{env} bash {{CL}}/hold_eco.sh {rb} {ob} {out} {j['spec']['block']} {post}"
    ship_helpers(j["host"], j["run"])
    j["eco"] = dict(tried=True, rb=rb, ob=ob, out=out, post_sdc=post_sdcs, sdc_name=m.get("sdc_name") or "6_final.sdc",
                    setup_post_sdc=list(m.get("setup_post_sdc") or []), pre=dict(ss_ps=m["ss_ps"], ff_ps=m["ff_ps"]), started=now_iso())
    st = dict(key="hold_eco", kind="hold_eco", threads=8, ram=32)
    launch_stage(j, st, cmd)
    fleet.launched(j["host"], 8, 32)
    j["status"], j["stage_key"] = "ECO", "hold_eco"
    event(j, f"hold-only miss ({setup_corner_label(m)} {m['ss_ps']:+.2f} / FF {m['ff_ps']:+.2f}, DRC 0): post-route hold ECO launched on "
             f"{rb}/5_2_route.odb")
    experiment(j, "running: post-route hold ECO")
    return True


def eco_install_cmd(j):
    """install the ECO result in place of the route (originals kept as *.pre_eco), point the verdict's corner_sta at
    the ECO sign-off, and re-export the view (hold_eco.reexport, else hbm_fmax_attn_abstract when the route has view/)"""
    e, rb, ob, blk = j["eco"], j["eco"]["rb"], j["eco"]["ob"], j["spec"]["block"]
    cs = subst(j["spec"]["verdict"]["corner_sta"], j)
    he = j["spec"].get("hold_eco") or {}
    out = eco_output(j)
    lines = ["set -e"]
    if j.get("eco_overlay_recovery"):
        lines.append(f"python3 {{CL}}/eco_recovery.py verify {shlex.quote(j['eco_overlay_recovery']['guard'])}")
    lines.append(f"EB=$(ls -d {out}/orfs/results/asap7/*/base)")
    for b in sorted({rb, ob}):
        for f in ("6_final.odb", "6_final.spef", "6_final.v"):
            lines.append(f"[ -f {b}/{f} ] && [ ! -f {b}/{f}.pre_eco ] && mv {b}/{f} {b}/{f}.pre_eco; cp $EB/{f} {b}/{f}")
    lines.append(f"for c in {cs}; do [ -f $c.pre_eco ] || cp $c $c.pre_eco; cp {out}/corner_sta.json $c; done")
    if isinstance(he.get("reexport"), str) and he["reexport"].strip():   # drive-0849: a spec with reexport: true (bool)
        lines.append(he["reexport"])                                      # crashed join(); non-str -> the default re-export
    else:
        W = "/".join(rb.split("/")[:-6])     # <route>/work/orfs/results/asap7/<d>/base -> <route>
        macs = " ".join(f"--macro-view {x}" for x in j["spec"]["verdict"].get("macros", []))
        isdc = f" --interface-sdc {ob}/6_final.sdc" if ob != rb else ""
        lines.append(f"if [ -f {W}/view/{blk}.lef ]; then mv {W}/view {W}/view.pre_eco; python3 tools/hbm_fmax_attn_abstract.py "
                     f"--orfs-dir {W}/work/orfs --name {blk} --out {W}/view {macs}{isdc} --tmp-dir {W}/abs_eco > {W}/export_eco.log 2>&1; fi")
    return "\n".join(lines)


def do_commit(j):
    if adoption_held(j):
        return
    m = j["metrics"]
    try:
        with PUBLISH_LOCK:
            out = publish(j, m)
    except Exception as ex:  # noqa: BLE001
        finish(j, "NEEDS_HUMAN", f"publish failed: {str(ex)[:300]}", f"NEEDS_HUMAN: CLOSED but publish failed: {str(ex)[:400]}")
        return
    j["publish"] = out
    merge = out.get("merge", "")
    rbn = (j.get("rebudget") or {}).get("rb")
    detail = (f"CLOSED {setup_corner_label(m)} {m['ss_ps']:+.2f} / FF {m['ff_ps']:+.2f} ps DRC {m['drc']}" + setup_sensitivity_text(m) + (f" under IO budget {rbn} (re-derived die-link "
              f"budget, no re-route)" if rbn else "") + " | record "
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
    fid = "bench-log-retry-20261007"  # was bench-regex-multiline-20261006; re-judge once more with the retried log fetch

    def eligible(j):
        m = BENCH_RE.match(j.get("reason") or "")
        return m if j["status"] in ("NEEDS_RTL", "NEEDS_HUMAN") and m and fid not in j.get("fix_requeued", []) else None
    for j in jobs:
        m = eligible(j)
        if not m:
            continue
        stl = stage_list(j["spec"])
        idx = next((i for i, x in enumerate(stl) if x["key"] == m.group(1)), None)
        if idx is None or not j.get("stage_tag", "").startswith(m.group(1) + "."):
            # STALE-SAVE 2026-10-09: this branch used to save_job(j) with no change -- a rewrite of the snapshot the
            # recovery pass took at its start (minutes to ~45 min earlier, behind slow historical log reads): it
            # reverted pi-ta15prod's hand re-entry twice.  Nothing to write.
            continue
        st = stl[idx]
        try:
            correct = bench_outcome(j, st, int(m.group(3)))
        except RuntimeError as exc:
            # An unavailable historical log must not starve later jobs or the
            # independent recovery passes. Do not consume this retry until read.
            log(f"[{j['name']}] bench re-judgment deferred: {exc}")
            continue
        with job_lock(j["name"]):
            # read-modify-write: act on the CURRENT file, and only if it is still the same bench verdict
            fresh = load_job(j["name"])
            if eligible(fresh) is None or fresh.get("reason") != j.get("reason") or fresh.get("stage_tag") != j.get("stage_tag"):
                continue
            j = fresh
            reevaluate_bench_apply(j, st, idx, m, fid, correct)


def reevaluate_bench_apply(j, st, idx, m, fid, correct):
    j.setdefault("fix_requeued", []).append(fid)
    if correct:
        j["benches"][st["key"]] = dict(expect=st["expect"], rc=int(m.group(3)), ok=True, rejudged=fid)
        j["status"], j["stage_idx"], j["reason"] = "READY", idx + 1, None
        event(j, f"{st['key']} re-judged {('PASS' if st['expect'] == 'pass' else 'FAIL as expected')} under {fid}; resumed")
        ledger(j, f"REQUEUED automatically: {st['key']} re-judged correct under loop fix {fid}")
        experiment(j, f"running: resumed after {fid}")
    else:
        event(j, f"{st['key']} re-judged under {fid}: verdict stands")
    save_job(j)


def requeue_toolchain(jobs):
    fid = "host-caps-20261006"
    for j in jobs:
        if j["status"] != "NEEDS_RTL" or fid in j.get("fix_requeued", []) or j.get("host") != "ot-agidock128":
            continue
        if not re.match(r"^bench_\S+ expected PASS but rc=2", j.get("reason") or ""):
            continue
        if not any("BUILD_FAIL" in (b.get("tail") or "") for b in j.get("benches", {}).values()):
            continue
        j.setdefault("fix_requeued", []).append(fid)
        j["hosts_tried"].append(j["host"])
        j.update(status="QUEUED", stage_idx=0, attempt=j["attempt"] + 1, retries_used=0, reason=None, errors=[],
                 benches={}, host=None, run=None)
        event(j, f"auto re-queued after loop fix {fid}: bench BUILD_FAIL on AGIdock (toolchain); placed by host caps now")
        ledger(j, f"REQUEUED automatically: loop fix {fid} (bench BUILD_FAIL rc=2 on AGIdock, toolchain mismatch)")
        save_job(j)


def requeue_ssh_verdict(jobs):
    fid = "verdict-ssh-retry-20261006"
    for j in jobs:
        if j["status"] == "NEEDS_HUMAN" and fid not in j.get("fix_requeued", []) and \
                re.search(r"verdict inputs missing.*(kex_exchange|Connection reset)", j.get("reason") or ""):
            j.setdefault("fix_requeued", []).append(fid)
            j.update(status="READY", reason=None, errors=[])
            event(j, f"auto re-queued after loop fix {fid} (transient ssh failure at the verdict)")
            ledger(j, f"REQUEUED automatically: loop fix {fid} (ssh reset while reading the verdict)")
            save_job(j)


def requeue_hold_only(jobs):
    jobs = [j for j in jobs if not j.get("eco_overlay_recovery")]  # explicit recovery is one-shot, including flow errors
    fid = "hold-eco-20261006"
    for j in jobs:   # first ECO attempts that died because the helper was not shipped to older run dirs (rc 127)
        e = j.get("eco") or {}
        if j["status"] == "NEEDS_RTL" and e.get("tried") and e.get("result") is None and "hold-eco-reroute-clock" not in j.get("fix_requeued", []):
            j.setdefault("fix_requeued", []).append("hold-eco-reroute-clock")
            j["eco"] = {}
            stl = stage_list(j["spec"])
            j.update(status="READY", reason=None, errors=[], stage_idx=next(i for i, x in enumerate(stl) if x["kind"] == "verdict"))
            event(j, "hold ECO re-run: helpers shipped; clock wires re-routed (DRT-0206 with kept clock wires); buffer cap 30 %")
            save_job(j)
    busy = {x["spec"].get("block") for x in jobs if x["status"] not in TERMINAL} | closed_blocks(jobs)
    for j in jobs:
        m = j.get("metrics") or {}
        if j["status"] != "NEEDS_RTL" or fid in j.get("fix_requeued", []) or not hold_only(j, m, blocking_checks(j)):
            continue
        j.setdefault("fix_requeued", []).append(fid)
        if j["spec"].get("block") in busy:
            event(j, f"{fid}: hold-only, but block {j['spec']['block']} has a live or closed sibling job; not re-opened")
            save_job(j)
            continue
        stl = stage_list(j["spec"])
        j.update(status="READY", reason=None, errors=[], stage_idx=next(i for i, x in enumerate(stl) if x["kind"] == "verdict"))
        busy.add(j["spec"]["block"])
        event(j, f"auto re-opened for loop fix {fid}: hold-only miss -> post-route hold ECO")
        ledger(j, f"REQUEUED automatically: loop fix {fid} (hold-only: {setup_corner_label(m)} {m['ss_ps']:+.2f} / FF {m['ff_ps']:+.2f})")
        save_job(j)


def requeue_budget(jobs):
    """NEEDS_BUDGET under the old +-tolerance rule whose measured insertion is <= the block target: accept it now"""
    fid = "budget-measured-below-target-20261006"
    for j in jobs:
        if j["status"] != "NEEDS_BUDGET" or fid in j.get("fix_requeued", []) or not j.get("budget") or not j.get("calibration"):
            continue
        j.setdefault("fix_requeued", []).append(fid)
        if budget_check(j) is None:
            stl = stage_list(j["spec"])
            j["stage_idx"] = next(i for i, x in enumerate(stl) if x["kind"] == "calibrate") + 1
            j.update(status="READY", reason=None, errors=[])
            event(j, f"auto re-queued after loop fix {fid}: measured insertion accepted, budget SDCs regenerated")
            ledger(j, f"REQUEUED automatically: loop fix {fid} (measured {j['budget']['check']['measured_ss']:g} <= target "
                      f"{j['budget']['insertion']['target_ss']:g})")
            record_measured(j)
        save_job(j)


def auto_requeue(jobs):
    live_blocks = {(x["spec"].get("block"), str(x["spec"].get("source", {}).get("commit", ""))[:9])
                   for x in jobs if x["status"] not in TERMINAL}
    for j in jobs:
        if j["status"] != "NEEDS_HUMAN" or not j.get("crashes") or j.get("postroute_repair"):
            continue
        with job_lock(j["name"]):
            j = load_job(j["name"])  # cancellation may have won since the tick snapshot
            if j["status"] != "NEEDS_HUMAN" or not j.get("crashes") or j.get("postroute_repair"):
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


def kill_own_stage(j):
    """stop ONLY this loop's own stage process group and containers mounting this job's own run dir (and its running
    parallel-bench stage, if any)"""
    for e in list((j.get("btrack") or {}).values()) + ([j["ctrack"]] if (j.get("ctrack") or {}).get("tag") else []):
        if e.get("state") == "running":
            ssh(e["host"], f"p=$(cat {e['run']}/cl/{e['tag']}.pid 2>/dev/null); [ -n \"$p\" ] && kill -TERM -- -$p 2>/dev/null; true",
                timeout=60)
            e["state"] = "killed"
    if not (j.get("stage_tag") and j.get("host")):
        return
    run, t = j["run"], j["stage_tag"]
    ssh(j["host"], f"""p=$(cat {run}/cl/{t}.pid 2>/dev/null); [ -n "$p" ] && kill -TERM -- -$p 2>/dev/null
for c in $(docker ps -q); do docker inspect --format '{{{{range .Mounts}}}}{{{{.Source}}}} {{{{end}}}}' $c | grep -q '{run}/' && docker stop -t 5 $c; done; true""",
        timeout=300)


def migrate_checkpoint(j, dest):
    """move a RUNNING route WITH its ORFS checkpoint (coordinator 2026-10-06): stop this job's own stage, stream the
    whole run dir (src snapshot + work/orfs results/logs/objects) to the same path on dest (tar keeps mtimes), patch
    the snapshot's run_abi3_physical.py for resume (resume_patch.py), dry-run make to see which stages re-run, and
    relaunch the route stage there with OT_CL_RESUME=1: ORFS reuses every completed stage, only the in-flight one is lost."""
    require_checkpoint_location(j)
    src = j["host"]
    if src == dest or (is_local(src) and is_local(dest)):
        raise ValueError("checkpoint migration requires a different host")
    if host_cfg(src)["base"] != host_cfg(dest)["base"]:
        raise ValueError(f"checkpoint move needs the same run root ({host_cfg(src)['base']} vs {host_cfg(dest)['base']})")
    run = j["run"]
    j["status"] = "MIGRATING"
    save_job(j)
    event(j, f"checkpoint move {host_cfg(src)['label']} -> {host_cfg(dest)['label']}: stopping own stage")
    kill_own_stage(j)
    for _ in range(30):
        r = ssh(src, f"for c in $(docker ps -q); do docker inspect --format '{{{{range .Mounts}}}}{{{{.Source}}}} {{{{end}}}}' $c "
                     f"| grep -q '{run}/' && echo BUSY; done; pgrep -f '{run}/cl/run.sh' >/dev/null && echo BUSY; true", timeout=120)
        if "BUSY" not in r.stdout:
            break
        time.sleep(10)
    t0 = time.time()
    ssh(dest, f"mkdir -p {run}", timeout=60, check=True)
    with ExitStack() as stack:
        # Stable order avoids opposite-direction migrations deadlocking channel leases.
        commands = {h: stack.enter_context(transport_command(h)) for h in sorted({src, dest})}
        read = shlex.join(commands[src] + [f"tar -C {shlex.quote(run)} -cf - ."])
        write = shlex.join(commands[dest] + [f"tar -C {shlex.quote(run)} -xf -"])
        p = subprocess.run(["bash", "-o", "pipefail", "-c", f"{read} | {write}"],
                           capture_output=True, text=True, timeout=7200)
    if p.returncode:
        raise RuntimeError(f"checkpoint transfer failed: {p.stderr[-500:]}")
    ship_helpers(dest, run)
    r = ssh(dest, f"cd {run}/src && python3 {run}/cl/resume_patch.py .", timeout=120)
    if r.returncode:
        raise RuntimeError(f"resume patch failed: {(r.stdout + r.stderr)[-400:]}")
    dm = subst(j["spec"].get("verdict", {}).get("drc_metrics", ""), j)
    orfs = dm.split("/logs/")[0] if "/logs/" in dm else None
    if not orfs:
        raise RuntimeError("checkpoint transfer cannot be verified: missing ORFS checkpoint path")
    check = ssh(dest, f"bash {run}/cl/resume_check.sh {orfs} {run}/src", timeout=600)
    chk = check.stdout
    if check.returncode or not re.search(r"^RESUME_OK=1$", chk, re.M):
        raise RuntimeError(f"checkpoint transfer resume check failed rc={check.returncode}: {chk[-400:]}")
    j["resume"] = dict(from_host=src, to_host=dest, run=run, at=now_iso(),
                       transfer_s=round(time.time() - t0), check=chk.strip()[-400:],
                       checkpoint_transfer_verified=True)
    j["checkpoint_affinity"] = dict(host=dest, run=run)
    j["hosts_tried"].append(dest)
    j.update(host=dest, status="READY", attempt=j["attempt"] + 1, wait=None)
    event(j, f"checkpoint moved in {j['resume']['transfer_s']} s; make dry-run: {' '.join(chk.split())[-200:]}")
    experiment(j, f"running: route resumed on {host_cfg(dest)['label']} from checkpoint")
    save_job(j)


def migrate_overloaded(jobs, fleet):
    """LOAD REBALANCE 2: a host above its cap (or a spillover-only host short of its RAM reserve) sheds this loop's
    jobs that have not passed CTS (bench / calibrate running or waiting, route not yet launched) to a host that fits."""
    for j in jobs:
        if j["status"] in TERMINAL or not j.get("host") or checkpoint_location(j):
            continue
        cfg = host_cfg(j["host"])
        info = fleet.probe(j["host"])
        if info is None:
            continue
        over = info["load1"] > cfg["cap"] or (cfg.get("spillover_only") and info["mem_gb"] < cfg.get("reserve_ram_gb", 0))
        if not over:
            continue
        stl = stage_list(j["spec"])
        st = stl[min(j.get("stage_idx", 0), len(stl) - 1)]
        pre_cts = (j["status"] in ("RUNNING", "READY") and st["kind"] in ("bench", "calibrate")) or \
                  (j["status"] == "READY" and st["kind"] == "route") or j["status"] == "SYNC"
        if not pre_cts and j["status"] == "RUNNING" and st["kind"] == "route":
            # OWNER LOAD REBALANCE 2: a route on an overloaded host that has not reached CTS may be relaunched elsewhere
            dm = subst(j["spec"].get("verdict", {}).get("drc_metrics", ""), j)
            if dm:
                rb = dm.replace("/logs/", "/results/").rsplit("/", 1)[0]
                r = ssh(j["host"], f"ls {rb}/4_1_cts.odb {rb}/3_place.odb >/dev/null 2>&1 && echo CTS; "
                                   f"ls -d {rb.rsplit('/', 2)[0]} >/dev/null 2>&1 || echo NOBASE; "
                                   f"ls {rb}/4_1_cts.odb >/dev/null 2>&1 || echo PRECTS", timeout=60)
                pre_cts = r.returncode == 0 and "PRECTS" in r.stdout
        if not pre_cts:
            continue
        h, why = fleet.choose(j["spec"], exclude=[j["host"]])
        if not h or host_cfg(h).get("spillover_only"):
            continue
        old = cfg["label"]
        if j["status"] == "RUNNING":
            kill_own_stage(j)
        cal = next((i for i, x in enumerate(stl) if x["kind"] == "calibrate"), None)
        if st["kind"] in ("bench", "route"):
            idx = j["stage_idx"]                         # re-run the interrupted bench / pre-CTS route
            if st["kind"] == "route" and cal is not None:
                idx = cal                                # calibration is host-local (calib.env): redo it
        else:
            idx = cal if cal is not None else j["stage_idx"]
        j["hosts_tried"].append(h)
        j.update(host=h, run=f"{host_cfg(h)['base']}/{j['name']}", status="SYNC", stage_idx=idx, wait=None,
                 attempt=j["attempt"] + 1)
        j.pop("wait_since", None)
        fleet.launched(h, j["spec"].get("threads", 16), j["spec"].get("peak_ram_gb", 32), j["name"])  # 2026-10-08
        event(j, f"LOAD REBALANCE: {old} over cap (load {info['load1']:.0f}, {info['mem_gb']} GB free); pre-CTS job "
                 f"moved to {host_cfg(h)['label']} (resumes at {stl[idx]['key']})")
        experiment(j, f"running: moved {old} -> {host_cfg(h)['label']}")
        save_job(j)


TRANSIENT_RE = re.compile(r"kex_exchange|Connection (reset|refused|closed|timed out)|ssh: |Broken pipe|"
                          r"No route to host|command failed rc=255|Could not resolve hostname")
TRANSIENT_BACKOFF_S = (120, 240, 480, 900, 1800)


def is_transient(ex):
    """an ssh / network failure (timeout of an ssh call, rc 255, connection errors), not a loop or job error"""
    if isinstance(ex, subprocess.TimeoutExpired):
        return isinstance(ex.cmd, list) and bool(ex.cmd) and ex.cmd[0] in ("ssh", "rsync")
    return bool(TRANSIENT_RE.search(str(ex)))


def handle_transient(j, fleet, ex):
    """robustness (2026-10-07): transient ssh errors back off (2, 4, 8, 15, 30 min); after 3 at a stage that has
    nothing in flight on the host (QUEUED / SYNC / READY before the first launch, or READY at calibrate/bench) the job
    moves to another host; a job whose results live on the host (verdict, ECO) keeps backing off and goes NEEDS_HUMAN
    only after 12 consecutive failures (~5 h).  Returns True when handled."""
    n = j.get("transient", 0) + 1
    j["transient"] = n
    j["transient_next"] = time.time() + TRANSIENT_BACKOFF_S[min(n - 1, len(TRANSIENT_BACKOFF_S) - 1)]
    event(j, f"transient ssh/network error #{n} on {j.get('host')} ({type(ex).__name__}: {str(ex)[:160]}); backing off")
    stl = stage_list(j["spec"])
    st = stl[min(j.get("stage_idx", 0), len(stl) - 1)]
    movable = j["status"] in ("QUEUED", "SYNC") or (j["status"] == "READY" and st["kind"] in ("calibrate", "bench")
                                                     and not j.get("stage_tag"))
    if n >= 3 and movable and j.get("host") and not checkpoint_location(j):
        h, _ = fleet.choose(j["spec"], exclude=[j["host"]])
        if h:
            event(j, f"{n} transient errors on {host_cfg(j['host'])['label']}: moving to {host_cfg(h)['label']}")
            j["hosts_tried"].append(h)
            j.update(host=h, run=f"{host_cfg(h)['base']}/{j['name']}", status="SYNC", transient=0)
            j.pop("transient_next", None)
            cal = next((i for i, x in enumerate(stl) if x["kind"] == "calibrate"), None)
            if cal is not None and j.get("stage_idx", 0) > cal:
                j["stage_idx"] = cal
            return True
    if n >= 12:
        return False                     # falls through to the ordinary error accounting
    return True


def advance_job(name, fleet):
    with job_lock(name):
        j = load_job(name)
        if j["status"] in TERMINAL or j.get("admission_hold"):
            return
        nt = j.get("transient_next")
        if nt and time.time() < nt:
            return                       # backing off after a transient ssh / network error
        try:
            step(j, fleet)
            if j.get("transient"):
                j["transient"] = 0
                j.pop("transient_next", None)
        except Exception as ex:  # noqa: BLE001
            if is_transient(ex) and handle_transient(j, fleet, ex):
                save_job(j)
                return
            j.setdefault("errors", []).append(f"{now_iso()} {type(ex).__name__}: {str(ex)[:500]}")
            j["errors"] = j["errors"][-10:]
            log(f"[{j['name']}] step error:\n{traceback.format_exc()}")
            if len(j["errors"]) >= 10 and j["status"] in ("SYNC", "READY"):
                finish(j, "NEEDS_HUMAN", f"10 consecutive loop errors: {str(ex)[:200]}",
                       f"NEEDS_HUMAN: loop errors at {j['status']}: {str(ex)[:300]}")
        save_job(j)


BULK_RELEASE_PER_TICK = 4
# NEAR-MISS RETENTION (merge-eco 2026-10-09): eco-sweep found the routed databases of near-miss elements gone
# (smh_tile_w, su12_full, qfd_hub, frame_station, router: review_queue/eco-sweep.md ES-1..8), so nothing was left to
# ECO or re-STA.  A non-closed route with TT >= NEAR_MISS_PS and FF >= NEAR_MISS_PS keeps its whole route tree
# (6_final odb/spef/sdc/v, ORFS objects the re-STA reads, src snapshot) until its element (spec block) has a CLOSED job.
# Enforced in three places: release_bulk() skips it, BULK_RELEASE_SH itself refuses a run whose corner_sta*.json is a
# near miss unless the caller sets NEAR_MISS_RELEASE=1 (manual reuse of the script keeps them), and the hourly fleet
# sweeper keeps any unit holding a near-miss route (tools/fleet/sweep.py) and every run dir in near_miss_retain.json.
NEAR_MISS_PS = -100.0
NEAR_MISS_JSON = STATE / "near_miss_retain.json"
# Route bulk released on terminal jobs (fleet disk guard 2026-10-07): intermediate ODB/DEF/SPEF/guides/netlists and
# ORFS objects under the job's ORFS work trees.  Kept: 6_final.*, 5_2_route.odb, every log / report / json (metrics).
BULK_RELEASE_SH = r"""set -u
R=%(run)s
if [ "${NEAR_MISS_RELEASE:-0}" != 1 ] && python3 - "$R" <<'NMPY'
import json, os, sys
r = sys.argv[1].rstrip("/")
for dp, dn, fn in os.walk(r):
    rel = dp[len(r):]
    dn[:] = [] if rel.count("/") >= 8 else [d for d in dn if not (rel == "" and d == "src") and d not in ("objects", ".git")]
    for f in fn:
        if not (f.startswith("corner_sta") and f.endswith(".json")):
            continue
        try:
            d = json.load(open(os.path.join(dp, f)))
            su = d.get("setup_tt") or d.get("setup_ss") or {}
            tt, ff = su.get("worst_slack_ps"), (d.get("hold_ff") or {}).get("worst_slack_ps")
        except Exception:
            continue
        num = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)
        if num(tt) and num(ff) and tt >= -100 and ff >= -100 and not (tt >= 0 and ff >= 0):
            print("NEAR_MISS", os.path.join(dp, f), tt, ff)
            sys.exit(0)
sys.exit(1)
NMPY
then echo "RETAIN near-miss route (TT/FF >= -100 ps, not closed); set NEAR_MISS_RELEASE=1 once the element closes"; exit 4; fi
for p in "$R"/cl/*.pid; do [ -f "$p" ] && [ ! -f "${p%%.pid}.rc" ] && kill -0 "$(cat "$p")" 2>/dev/null && { echo LIVE "$p"; exit 3; }; done
for c in $(docker ps -q 2>/dev/null); do docker inspect --format '{{range .Mounts}}{{.Source}} {{end}}' $c | grep -q "$R/" && { echo LIVE docker; exit 3; }; done
before=$(du -sm "$R" 2>/dev/null | cut -f1)
find "$R" -path '*/orfs/*' ! -path "$R/src/*" -type d -name objects -prune -exec rm -rf {} + 2>/dev/null
find "$R" -path '*/orfs/*' ! -path "$R/src/*" -type f \( -name '*.odb' -o -name '*.def' -o -name '*.spef' -o -name '*.guide' -o -name '*.v' -o -name '*.odb.gz' -o -name '*.def.gz' \) \
     ! -name '6_final.*' ! -name '5_2_route.odb' -delete 2>/dev/null
echo FREED $before $(du -sm "$R" 2>/dev/null | cut -f1)
"""



REVOKED_JSON = Path(os.environ.get("CL_REVOKED", str(Path.home() / "claude-takeover-20261007/revoked_closures.json")))
OPTB_STATUS_GLOB = "results/closure_loop/option_b_status_*/status.json"
OPTB_DECISION = "2026-10-07T20:45"   # owner option B: setup judged at TT; SS-era closures of revoked blocks lapse


def _closed_at(j):
    ev = [e for e in j.get("events") or [] if " CLOSED" in e[:40] or "CLOSED:" in e[:40]]
    return (ev[-1] if ev else (j.get("updated") or ""))[:16]


def revoked_closures():
    """(revoked job names, option-B revoked blocks): the two sources of closures that no longer count."""
    names, blocks = set(), set()
    try:
        names |= set(json.loads(REVOKED_JSON.read_text()))
    except Exception:  # noqa: BLE001
        pass
    for p in sorted(REPO.glob(OPTB_STATUS_GLOB))[-1:]:
        try:
            d = json.loads(p.read_text()).get("revoked_previously_closed") or {}
            blocks |= {b["block"] for b in d.get("blocks", [])}
            names |= {b["job"] for b in d.get("blocks", []) if b.get("job")}
        except Exception:  # noqa: BLE001
            pass
    return names, blocks


def closure_counts(j, revoked=None):
    """A CLOSED job counts as its block's closure unless revoked (2026-10-08: dsfd_svcio_q's re-routes were bulk-released
    against a revoked closure). An option-B-revoked block's closure counts only if judged at TT (tt_ps, or closed after
    the option-B decision)."""
    if j.get("status") != "CLOSED":
        return False
    names, blocks = revoked if revoked is not None else revoked_closures()
    if j["name"] in names:
        return False
    if j["spec"].get("block") in blocks:
        return "tt_ps" in (j.get("metrics") or {}) or _closed_at(j) >= OPTB_DECISION
    return True


def closed_blocks(jobs):
    rv = revoked_closures()
    return {x["spec"].get("block") for x in jobs if closure_counts(x, rv)}


def near_miss(j, closed=None):
    """a non-CLOSED job whose route verdict is TT >= NEAR_MISS_PS and FF >= NEAR_MISS_PS (and not both >= the line),
    while its element (spec block) has no counting CLOSED job: its route tree is retained"""
    if j.get("status") == "CLOSED":
        return False
    m = j.get("metrics") or {}
    tt, ff = m.get("ss_ps"), m.get("ff_ps")
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (tt, ff)):
        return False
    if not (tt >= NEAR_MISS_PS and ff >= NEAR_MISS_PS) or (tt >= SS_MIN and ff >= FF_MIN):
        return False
    return closed is None or j["spec"].get("block") not in closed


def write_near_miss_retain(jobs, closed=None):
    """STATE/near_miss_retain.json: run dirs (+ ORFS dir) of retained near-miss routes, read by tools/fleet/fleet_sweep.py"""
    closed = closed_blocks(jobs) if closed is None else closed
    rows = []
    for x in jobs:
        if x.get("run") and x.get("host") and near_miss(x, closed):
            m = x.get("metrics") or {}
            rows.append(dict(job=x["name"], block=x["spec"].get("block"), host=x["host"], run=x["run"],
                             orfs_dir=m.get("orfs_dir"), tt_ps=m.get("ss_ps"), ff_ps=m.get("ff_ps"), drc=m.get("drc"),
                             status=x["status"]))
    body = dict(schema="opentallas.closure_loop.near_miss_retain.v1", generated=now_iso(), threshold_ps=NEAR_MISS_PS,
                rule="non-closed route with TT >= threshold and FF >= threshold keeps its route tree until its block closes",
                jobs=sorted(rows, key=lambda r: r["job"]))
    try:
        tmp = NEAR_MISS_JSON.with_suffix(".tmp")
        tmp.write_text(json.dumps(body, indent=1) + "\n")
        tmp.replace(NEAR_MISS_JSON)
    except OSError as ex:
        log(f"near_miss_retain.json not written: {ex}")
    return rows


def release_bulk(jobs):
    """CANCELLED jobs, and terminal jobs superseded by a CLOSED job of the same block, give back their route bulk --
    except a near miss (near_miss()) whose block has not closed: it keeps its route tree (NEAR-MISS RETENTION)."""
    closed = closed_blocks(jobs)
    write_near_miss_retain(jobs, closed)
    n = 0
    for x in jobs:
        if n >= BULK_RELEASE_PER_TICK:
            break
        if x.get("bulk_released") or not x.get("host") or not x.get("run") or x["status"] not in TERMINAL:
            continue
        if x["status"] == "CLOSED" or not (x["status"] == "CANCELLED" or x["spec"].get("block") in closed):
            continue
        if near_miss(x, closed) or (x.get("near_miss_retained") and x["spec"].get("block") not in closed):
            continue
        if x["host"] not in {h["name"] for h in hosts_table()}:
            continue
        with job_lock(x["name"]):
            j = load_job(x["name"])
            if j.get("bulk_released") or j["status"] not in TERMINAL or j["status"] == "CLOSED":
                continue
            # the block is closed (or the job has no near-miss verdict): a near-miss corner_sta may be released
            rel = "NEAR_MISS_RELEASE=1\n" if j["spec"].get("block") in closed else ""
            r = ssh(j["host"], rel + BULK_RELEASE_SH % dict(run=shlex.quote(j["run"])), timeout=900)
            n += 1
            if r.returncode == 4:
                if not j.get("near_miss_retained"):
                    j["near_miss_retained"] = now_iso()
                    event(j, f"bulk release refused: near-miss route retained ({r.stdout.strip()[-200:]})")
                    save_job(j)
                continue
            if r.returncode == 3:
                event(j, f"bulk release skipped: live process ({r.stdout.strip()[:120]})")
                continue
            if r.returncode != 0 and "FREED" not in r.stdout:
                continue   # host unreachable: retried next tick
            why = "cancelled" if j["status"] == "CANCELLED" else "superseded by a CLOSED job of block " + str(j["spec"].get("block"))
            j["bulk_released"] = dict(at=now_iso(), why=why, du_mb=r.stdout.strip().split("FREED", 1)[-1].strip())
            event(j, f"route bulk released ({why}; MB before/after {j['bulk_released']['du_mb']}); kept 6_final.*, 5_2_route.odb, logs/reports/json")
            save_job(j)


# DEEP RELEASE (disk-1210 2026-10-09): EPYC1 sat at 183 GB free with a 1.6 TB closure-loop tree although every terminal
# job had been bulk-released: BULK_RELEASE_SH keeps 5_2_route.odb, every eco pass's 6_final.*, the src snapshot (~1.3 GB
# per job) and bench builds (Verilator .gch/obj ~1 GB per bench), and it never touched CLOSED jobs or plain failures.
# Owner rule: CLOSED + recorded on main keeps 6_final.{odb,def,v,sdc,spef} of the accepted ORFS dir (metrics.orfs_dir)
# and of the route tree plus logs/reports; a terminal failure older than DEEP_RELEASE_AGE_H loses the ORFS 1_-5_
# intermediates, objects/, the src snapshot and bench builds, keeping 6_final.* and logs/reports; a near miss on an
# open element (near_miss()) keeps 5_2_route.odb, 6_final.*, objects/ and src (re-STA / ECO inputs) and loses only the
# 1_-4_/fill/gds intermediates and bench builds.  Every path a committed receipt on origin/main names is kept whole
# (files, source trees) or keeps its 6_final.* (generic ORFS dirs).  A src snapshot goes only when its SOURCE_COMMIT is
# the job's commit and that commit is in REPO (re-creatable by git archive).
DEEP_RELEASE_AGE_H = 6.0
DEEP_RELEASE_PER_TICK = 4
DEEP_RELEASE_FAIL = {"NEEDS_RTL", "NEEDS_HUMAN", "FLOORPLAN_MARGIN", "PREROUTE_MARGIN", "CANCELLED", "REFUSED", "INVALID",
                     *EARLY_FAIL}
DEEP_RELEASE_REFS_TTL_S = 3600
_DEEP_CACHE = {}
DEEP_RELEASE_PY = r'''
import json, os, shutil, stat, sys
a = json.loads(os.environ["OT_DR"])
R, mode = a["run"].rstrip("/"), a["mode"]
FINAL = {"6_final.odb", "6_final.def", "6_final.v", "6_final.sdc", "6_final.spef"}
BULK = (".odb", ".def", ".spef", ".v", ".gds", ".guide", ".odb.gz", ".def.gz", ".gds.gz", ".pre_eco")
GENERIC = {"orfs", "work", "base", "routes", "cl", "eco", "eco-r2", "eco-r3", "pass1", "pass2", "pass3", "route",
           "results", "logs", "reports", "asap7"}
KEEP_TEXT = (".log", ".json", ".txt", ".rpt", ".rc", ".pid", ".sdc", ".tcl", ".sh", ".env", ".csv", ".md", ".yaml",
             ".yml", ".sv", ".v", ".svh", ".vh", ".f")
if not os.path.isdir(R):
    print("DEEP_FREED 0 (no run dir)"); sys.exit(0)
for p in os.listdir("/proc"):
    if not p.isdigit():
        continue
    try:
        cwd = os.readlink("/proc/%s/cwd" % p)
        argv = open("/proc/%s/cmdline" % p, "rb").read().decode(errors="replace")
    except OSError:
        continue
    if cwd == R or cwd.startswith(R + "/") or (R + "/") in argv or argv.endswith(R) or (R + "\0") in argv:
        print("LIVE pid", p); sys.exit(3)
refs = [r.rstrip("/") for r in a.get("refs") or []]
hard = [r for r in refs if os.path.basename(r) not in GENERIC and r != R]
soft = [r for r in refs if r not in hard and r != R]
finals = [x.rstrip("/") for x in a.get("final_dirs") or []]
prot = lambda p: any(p == r or p.startswith(r + "/") for r in hard)
anc = lambda p: any(r.startswith(p + "/") for r in hard)
APPLY = not a.get("dry")
freed = 0
def blocks(p):
    try:
        st = os.lstat(p)
        return st.st_blocks * 512 if stat.S_ISREG(st.st_mode) else 0
    except OSError:
        return 0
def rm_tree(p):
    b = sum(blocks(os.path.join(dp, f)) for dp, dn, fn in os.walk(p) for f in fn)
    if APPLY:
        shutil.rmtree(p, ignore_errors=True)
    return b
def rm_file(p):
    b = blocks(p)
    if APPLY:
        try:
            os.unlink(p)
        except OSError:
            return 0
    return b
src_ok = False
try:
    src_ok = bool(a.get("src_commit")) and open(os.path.join(R, "src", "SOURCE_COMMIT")).read().strip() == a["src_commit"]
except OSError:
    pass
for top in sorted(os.listdir(R)):
    tp = os.path.join(R, top)
    if not os.path.isdir(tp) or os.path.islink(tp) or prot(tp) or anc(tp):
        continue
    if top == "src" and mode in ("closed", "fail") and src_ok:
        freed += rm_tree(tp)
    elif top.startswith("bench_src"):
        freed += rm_tree(tp)
for dp, dn, fn in os.walk(R):
    if prot(dp) or dp == R + "/src" or dp.startswith(R + "/src/"):
        dn[:] = []
        continue
    if "/orfs" in dp and mode != "nearmiss":
        for x in [x for x in dn if x == "objects"]:
            p = os.path.join(dp, x)
            if not prot(p) and not anc(p):
                freed += rm_tree(p)
                dn.remove(x)
    verilator = any(f.startswith("V") and f.endswith(".mk") for f in fn)
    for f in fn:
        p = os.path.join(dp, f)
        if prot(p) or os.path.islink(p):
            continue
        if verilator:
            if not f.endswith(KEEP_TEXT):
                freed += rm_file(p)
            continue
        if f.endswith((".gch", ".o", ".a", ".so")) and "/orfs" not in dp:
            freed += rm_file(p)
            continue
        if "/orfs" not in dp or not (f.endswith(BULK) or ".odb." in f):
            continue
        if f in FINAL and (mode != "closed" or "/routes/" in dp or any(dp.startswith(x + "/") for x in finals + soft)):
            continue
        if f == "5_2_route.odb" and mode == "nearmiss":
            continue
        freed += rm_file(p)
print("DEEP_FREED %d" % (freed // 2 ** 20))
'''


def _terminal_age_h(j, now=None):
    """hours since the job's last real event (release / retention bookkeeping does not count)"""
    t = j.get("updated") or j.get("created")
    for e in reversed(j.get("events") or []):
        if not re.search(r"bulk release|route bulk released|near-miss|deep release|disk-1210", e[:160]):
            t = e[:25]
            break
    try:
        return ((now or time.time()) - dt.datetime.fromisoformat(t).timestamp()) / 3600
    except Exception:  # noqa: BLE001
        return 0.0


def _main_evidence():
    """(origin/main sha, tree file list, merged-closure records text, receipt-referenced scratch paths), cached by sha
    (refs refreshed at most every DEEP_RELEASE_REFS_TTL_S: the git grep costs ~20 s)"""
    g = lambda *a: subprocess.run(["git", "-C", str(REPO), *a], capture_output=True, text=True, timeout=600)
    sha = g("rev-parse", "origin/main").stdout.strip()
    if not sha:
        return None
    c = _DEEP_CACHE
    if c.get("sha") != sha:
        recs = "".join(g("show", f"{sha}:{p}").stdout for p in g("ls-tree", "--name-only", sha, "results/closure_loop/").stdout.split()
                       if "merged_closures" in p)
        c.update(sha=sha, files=g("ls-tree", "-r", "--name-only", sha).stdout, recs=recs)
    if c.get("refs_sha") != sha and time.time() - c.get("refs_t", 0) > DEEP_RELEASE_REFS_TTL_S or "refs" not in c:
        out = g("grep", "-h", "-o", "-I", "-E", r"/srv/[A-Za-z0-9_./+-]+", sha).stdout
        c.update(refs=sorted({x.split(":", 1)[-1].rstrip("/.") for x in out.split()}), refs_sha=sha, refs_t=time.time())
    return c


def closure_on_main(j, ev):
    """a CLOSED job whose record reached origin/main: its record commit is an ancestor, a merged_closures record or a
    main tree path names it"""
    for e in reversed(j.get("events") or []):
        m = re.search(r"CLOSED:.*record (\S+) ([0-9a-f]{7,40})", e)
        if m:
            if subprocess.run(["git", "-C", str(REPO), "merge-base", "--is-ancestor", m.group(2), ev["sha"]],
                              capture_output=True, timeout=120).returncode == 0:
                return True
            break
    return j["name"] in ev["files"] or j["name"] in ev["recs"]


def deep_release_mode(j, closed, ev, now=None):
    """closed | fail | nearmiss | None (keep) for one job (DEEP RELEASE)"""
    if j.get("deep_released") or not j.get("host") or not j.get("run") or j["status"] not in TERMINAL:
        return None
    if _terminal_age_h(j, now) < DEEP_RELEASE_AGE_H:
        return None
    if j["status"] == "CLOSED":
        if closure_counts(j):
            return "closed" if closure_on_main(j, ev) else None
        return "fail"                                   # revoked closure: a failure on its element
    if j["status"] not in DEEP_RELEASE_FAIL:
        return None
    if near_miss(j, closed) or (j.get("near_miss_retained") and j["spec"].get("block") not in closed):
        return "nearmiss"
    return "fail"


def release_deep(jobs, now=None):
    """DEEP RELEASE of up to DEEP_RELEASE_PER_TICK terminal jobs (see DEEP_RELEASE_PY)"""
    closed = closed_blocks(jobs)
    hosts = {h["name"] for h in hosts_table()}
    shared = {}
    for x in jobs:
        if x.get("run") and x.get("host"):
            shared.setdefault((x["host"], x["run"].rstrip("/")), []).append(x)
    cand = [x for x in jobs if x.get("host") in hosts and not x.get("deep_released") and x["status"] in TERMINAL
            and _terminal_age_h(x, now) >= DEEP_RELEASE_AGE_H]
    if not cand:
        return 0
    ev = _main_evidence()
    if not ev:
        return 0
    n = 0
    for x in cand:
        if n >= DEEP_RELEASE_PER_TICK:
            break
        mode = deep_release_mode(x, closed, ev, now)
        if not mode:
            continue
        run = x["run"].rstrip("/")
        if any(y["status"] not in TERMINAL or _terminal_age_h(y, now) < DEEP_RELEASE_AGE_H
               for y in shared.get((x["host"], run), [])):
            continue                                    # a sibling job still uses the run dir
        with job_lock(x["name"]):
            j = load_job(x["name"])
            if mode != deep_release_mode(j, closed, ev, now):
                continue
            commit = j.get("commit_full") or (j["spec"].get("source") or {}).get("commit") or ""
            if commit and subprocess.run(["git", "-C", str(REPO), "cat-file", "-e", commit + "^{commit}"],
                                         capture_output=True, timeout=60).returncode != 0:
                commit = ""
            arg = dict(run=run, mode=mode, src_commit=commit, refs=[r for r in ev["refs"] if r.startswith(run + "/")],
                       final_dirs=[(j.get("metrics") or {}).get("orfs_dir")] if mode == "closed" and (j.get("metrics") or {}).get("orfs_dir") else [])
            r = ssh(j["host"], f"OT_DR={shlex.quote(json.dumps(arg))} python3 - <<'DRPY'\n{DEEP_RELEASE_PY}\nDRPY\n", timeout=1800)
            n += 1
            if r.returncode == 3:
                event(j, f"deep release skipped: live process ({r.stdout.strip()[:120]})")
                continue
            m = re.search(r"DEEP_FREED (\d+)", r.stdout)
            if r.returncode != 0 or not m:
                continue                                # host unreachable / error: retried next tick
            j["deep_released"] = dict(at=now_iso(), mode=mode, freed_mb=int(m.group(1)))
            kept = {"closed": "6_final.{odb,def,v,sdc,spef} of the accepted ORFS dir + route tree",
                    "fail": "6_final.*", "nearmiss": "5_2_route.odb, 6_final.*, objects/, src"}[mode]
            event(j, f"deep release ({mode}, {m.group(1)} MB): kept {kept}, receipt-referenced paths, logs/reports/json")
            save_job(j)
    return n


def tick(fleet):
    try:
        ingest()
    except Exception:  # noqa: BLE001
        log("ingest error:\n" + traceback.format_exc())
    own = {}
    for x in all_jobs():
        if x["status"] in ("RUNNING", "ECO", "SUMMARY", "ECO_INSTALL") and x.get("host"):
            stl = stage_list(x["spec"])
            st = stl[min(x.get("stage_idx", 0), len(stl) - 1)]
            own[x["host"]] = own.get(x["host"], 0) + (8 if x["status"] == "ECO" else st.get("threads", 4) or 4)
        for e in (x.get("btrack") or {}).values() if x["status"] not in TERMINAL else ():
            if e.get("state") == "running":
                own[e["host"]] = own.get(e["host"], 0) + 4
    fleet.own_running = own
    try:
        release_bulk(all_jobs())
    except Exception:  # noqa: BLE001
        log("release_bulk error:\n" + traceback.format_exc())
    try:
        release_deep(all_jobs())
    except Exception:  # noqa: BLE001
        log("release_deep error:\n" + traceback.format_exc())
    for req in sorted((STATE / "migrate_requests").glob("*.json")) if (STATE / "migrate_requests").exists() else []:
        try:
            rq = json.loads(req.read_text())
            with job_lock(rq["name"]):
                j = load_job(rq["name"])
                if j["status"] == "RUNNING" and j.get("stage_key") == "route":
                    migrate_checkpoint(j, rq["host"])
                else:
                    log(f"migrate request {rq['name']} ignored: status {j['status']} stage {j.get('stage_key')}")
        except Exception:  # noqa: BLE001
            log("migrate request error:\n" + traceback.format_exc())
            try:
                j = load_job(rq["name"])
                if j["status"] == "MIGRATING":
                    finish(j, "NEEDS_HUMAN", "checkpoint move failed (see daemon.log)", "NEEDS_HUMAN: checkpoint move failed")
                    save_job(j)
            except Exception:  # noqa: BLE001
                pass
        req.unlink(missing_ok=True)
    schedule_recovery()
    # persistent pool, no per-tick barrier (2026-10-07): a job still being stepped (a source sync, a 30-min verdict check)
    # is skipped this tick instead of holding every other job until the next tick
    global _POOL
    if _POOL is None:
        _POOL = ThreadPoolExecutor(max_workers=WORKERS)
    live = [x for x in all_jobs() if x["status"] not in TERMINAL]
    prio_hosts = {}
    for x in live:
        p = job_priority(x)
        if p <= 0 or x["status"] not in ("QUEUED", "READY") or not x.get("wait"):
            continue
        usable = [x["host"]] if x["status"] == "READY" and x.get("host") else \
            [h["name"] for h in hosts_table() if fleet.compatible(h["name"], x["spec"])]
        for h in usable:
            prio_hosts[h] = max(prio_hosts.get(h, 0), p)
    fleet.prio_hosts = prio_hosts
    # 21:58: a TT batch put ~150 jobs in SYNC; each source sync holds a worker and an ssh channel for minutes, so all 48
    # workers sat in sync_source and no READY stage launched for 15 min.  Syncs (QUEUED / SYNC) get at most SYNC_SLOTS
    # workers; every other state is submitted first.
    with _INFLIGHT_LOCK:
        syncing = sum(1 for x in live if x["name"] in _INFLIGHT and x["status"] in ("QUEUED", "SYNC"))
    order = sorted(live, key=lambda x: (x["status"] in ("QUEUED", "SYNC"), -job_priority(x)))
    for x in order:
        if x["status"] in ("QUEUED", "SYNC"):
            if syncing >= SYNC_SLOTS:
                continue
            with _INFLIGHT_LOCK:
                if x["name"] not in _INFLIGHT:
                    syncing += 1
        with _INFLIGHT_LOCK:
            if x["name"] in _INFLIGHT:
                continue
            _INFLIGHT.add(x["name"])
        _POOL.submit(_advance_and_release, x["name"], fleet)
    write_status()


_RECOVERY_POOL = None
_RECOVERY_FUTURE = None


def recover_jobs():
    # Historical log reads can wait on an unreachable host for minutes. They
    # must neither block live dispatch nor suppress unrelated recovery classes.
    for recover in (reevaluate_benches, requeue_toolchain, requeue_budget,
                    requeue_hold_only, requeue_ssh_verdict, auto_requeue):
        try:
            jobs = all_jobs()
            live_blocks = {j["spec"].get("block") for j in jobs
                           if j["status"] not in TERMINAL} | closed_blocks(jobs)
            # Automatic migration of historical failures must not revive a
            # superseded route alongside an active or closed replacement.
            recover([j for j in jobs if j["status"] not in TERMINAL
                     or j["spec"].get("block") not in live_blocks])
        except Exception:
            log(f"{getattr(recover, '__name__', 'recovery')} error:\n" + traceback.format_exc())


def schedule_recovery():
    global _RECOVERY_POOL, _RECOVERY_FUTURE
    if _RECOVERY_POOL is None:
        _RECOVERY_POOL = ThreadPoolExecutor(max_workers=1)
    if _RECOVERY_FUTURE is None or _RECOVERY_FUTURE.done():
        _RECOVERY_FUTURE = _RECOVERY_POOL.submit(recover_jobs)


_POOL = None
_INFLIGHT = set()
_INFLIGHT_LOCK = threading.Lock()


def _advance_and_release(name, fleet):
    try:
        advance_job(name, fleet)
    except Exception:  # noqa: BLE001
        log(f"[{name}] advance error:\n{traceback.format_exc()}")
    finally:
        with _INFLIGHT_LOCK:
            _INFLIGHT.discard(name)


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
    try:
        log(f"variant-keyed insertion backfill: {backfill_variants()} variants added")
    except Exception:  # noqa: BLE001
        log("backfill_variants error:\n" + traceback.format_exc())
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
        try:
            publish_measured()
        except Exception:  # noqa: BLE001
            log("publish_measured error:\n" + traceback.format_exc())
        schedule_deferred_record_merges()
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
    if not errs:
        res = submit_check(spec)
        print(f"submit lint {res['verdict']}: {res.get('message', '')}"
              + (f" (estimate {res.get('est')} b/um, with fix {res.get('est_fix')})" if res.get("est") else ""))
        if res["verdict"] == "REFUSE":
            errs.append(f"SUBMIT_LINT FLOORPLAN_MARGIN: the loop would REFUSE this job: {res['message']}")
        elif res["verdict"] == "FIX":
            print(f"  the loop will add {res['fix']} {res['fix_env']} to the route_master stage commands at intake")
        need = bench_missing_paths(spec)
        if need:
            print(f"bench needs repo paths outside the source sync: the loop will add {need} to source.extra_paths "
                  f"at intake (or list them in source.extra_paths)")
    print("\n".join(errs) if errs else "OK")
    sys.exit(1 if errs else 0)


def fp_margin_time(j):
    """when the job finished FLOORPLAN_MARGIN (its event), else its last update"""
    for e in reversed(j.get("events", [])):
        if " FLOORPLAN_MARGIN" in e[:60]:
            return e.split(" ", 1)[0]
    return j.get("updated", "")


def release_route_key(j):
    """drop a FLOORPLAN_MARGIN job from its block@commit route-key list: it stopped before global placement and spent
    no route, so its requeue must not be REFUSED by MAX_ROUTES_PER_KEY"""
    keys = route_keys()
    key = f"{j['spec']['block']}@{j['spec']['source']['commit'][:12]}"
    if j["name"] in keys.get(key, []):
        keys[key] = [n for n in keys[key] if n != j["name"]]
        tmp = keys_path().with_suffix(".tmp")
        tmp.write_text(json.dumps(keys, indent=1) + "\n")
        os.replace(tmp, keys_path())


def cmd_submit_recheck(a):
    """lint-at-submit back-check: every FLOORPLAN_MARGIN job since --since with no live successor (a job of the same
    block that is not terminal, or a later CLOSED one) is re-judged by the submit lint; pin-density-only failures an
    approved automatic fix passes (forced: the measured failure outranks the lower-bound estimate) are requeued
    (--requeue: the fixed spec, spec.submit_lint recorded, named <name>-ls in the drop dir; the failed job's route-key
    slot is released, it spent no route); the rest are listed with their failing checks"""
    jobs = all_jobs()
    out = []
    for j in sorted(jobs, key=fp_margin_time):
        if j["status"] != "FLOORPLAN_MARGIN" or fp_margin_time(j) < a.since:
            continue
        blk = j["spec"].get("block")
        succ = [x["name"] for x in jobs if x["name"] != j["name"] and x["spec"].get("block") == blk
                and (x["status"] not in TERMINAL or (x["status"] in ("CLOSED", "SMOKE_OK")
                                                     and x.get("created", "") > j.get("created", "")))]
        reason = j.get("reason") or ""
        checks = sorted({part.split(":", 1)[0].strip() for part in reason.split(" | ") if ":" in part})
        spec = j.get("spec_submitted", j["spec"])
        try:
            rec = submit_lint.util_record(spec, reason, submit_lint.Git(REPO), j["name"])
            if rec:
                util_db_add(*rec)
        except Exception:  # noqa: BLE001
            pass
        if succ:
            out.append(f"SUCCESSOR {j['name']}: {','.join(checks)} -> live successor {', '.join(succ[:3])}")
            continue
        pin_only = checks == ["pin_density"]
        res = submit_check(spec, force=pin_only)
        est = f" est {res.get('est')} with fix {res.get('est_fix')}" if res.get("est") else ""
        if pin_only and res["verdict"] == "FIX":
            new = (j["name"][:92] + "-ls")
            line = f"REQUEUE {j['name']} -> {new}: pin density only, fix {res['fix']} {res['fix_env']}{est}"
            if a.requeue:
                nspec = submit_lint.apply_fix(spec, res, now_iso())
                nspec["name"] = new
                nspec["submit_lint"]["requeued_from"] = j["name"]
                release_route_key(j)
                DROP.mkdir(parents=True, exist_ok=True)
                (DROP / f"{new}.json").write_text(json.dumps(nspec, indent=1) + "\n")
            out.append(line)
        else:
            what = ("pin density only; " if checks == ["pin_density"] else "") + f"submit lint {res['verdict']}"
            out.append(f"LIST {j['name']} [{blk}]: {','.join(checks) or '?'}: {reason[:220]} || {what}: "
                       f"{res.get('message', '')[:400]}{est}")
    text = "\n".join(out)
    print(text)
    if a.log:
        append_locked(Path(a.log), "".join(f"{now_iso()} [lint-at-submit recheck] {x}\n" for x in out))


@locked_job_command
def cmd_retry(a):
    j = load_job(a.name)
    if j["status"] not in ("NEEDS_HUMAN", "NEEDS_BUDGET", "PREROUTE_MARGIN", *EARLY_FAIL):
        sys.exit(f"{a.name} is {j['status']}; only NEEDS_HUMAN / NEEDS_BUDGET / PREROUTE_MARGIN / EARLY_FAIL_* jobs "
                 f"can be retried")
    if j["status"] == "NEEDS_BUDGET" and j.get("budget"):
        j["budget"]["override"] = "human retry after NEEDS_BUDGET"
        j["spec"].setdefault("budget", {})["on_deviation"] = "continue"
        j["stage_idx"] += 1           # the calibration is kept: continue after it, on the sheet SDC
    if getattr(a, "at", None):        # resume at a named stage (e.g. verdict: the evidence of the failed stage is valid)
        stl = stage_list(j["spec"])
        idx = [i for i, s in enumerate(stl) if s["key"] == a.at]
        if not idx:
            sys.exit(f"{a.name}: no stage {a.at} (stages: {' '.join(s['key'] for s in stl)})")
        j["stage_idx"], j["stage_key"] = idx[0], a.at
    synchronized = bool(j.get("commit_full")) and j.get("source_synced") is not False
    retry_status = ("READY" if synchronized else "SYNC") if j.get("host") else "QUEUED"
    j["status"], j["retries_used"], j["attempt"] = retry_status, 0, j["attempt"] + 1
    j["errors"] = []
    # 2026-10-08: a bench track pinned to an artifact run on another host (bench_location) outlives that run when a
    # purge or move deletes it -- every bench launch then failed 'No such file' until 10 loop errors.  A retry restarts
    # the unfinished benches on the job's own run.
    if j.get("bench_location") and j["bench_location"].get("run") != j.get("run"):
        j.pop("bench_location", None)
        j["btrack"] = {k: v for k, v in (j.get("btrack") or {}).items() if v.get("state") == "done"}
    event(j, "human retry: re-queued from stage " + str(j.get("stage_key")))
    save_job(j)
    ledger(j, "RETRY (human) from stage " + str(j.get("stage_key")))


@locked_job_command
def cmd_ioref_rejudge(a):
    """human (FLOW-IOREF): re-judge a NEEDS_RTL job at its ROUTED insertion (routed_ioref re-STA, no re-route).  Closes
    -> back to the verdict stage (READY; the cached re-STA is the verdict).  Hold-only at the routed reference with no
    ECO tried yet -> verdict stage too (the post-route hold ECO then runs with io_ref_routed.sdc).  Prints one line."""
    j = load_job(a.name)
    m = dict(j.get("metrics") or {})
    if j["status"] not in ("NEEDS_RTL", "NEEDS_HUMAN") or not m.get("orfs_dir"):
        print(f"SKIP {a.name}: {j['status']}, orfs_dir {m.get('orfs_dir')}")
        return
    if (j.get("eco") or {}).get("installed"):
        print(f"SKIP {a.name}: an installed ECO replaced the route")
        return
    ss0, ff0 = m.get("route_sdc_clock", {}).get("ss_ps", m.get("ss_ps")), m.get("route_sdc_clock", {}).get("ff_ps", m.get("ff_ps"))
    m["ss_ps"], m["ff_ps"] = ss0, ff0
    rr = routed_ioref(j, m)
    drc, failed = m.get("drc"), j.get("failed_checks") or []
    if not rr or not rr.get("available"):
        save_job(j)
        print(f"NOREF {a.name}: {(rr or {}).get('why')}")
        return
    closes = rr["tt"] >= SS_MIN and rr["ff"] >= FF_MIN and drc == 0 and not failed
    holdonly = rr["tt"] >= SS_MIN and rr["ff"] < FF_MIN and drc == 0 and not failed and not (j.get("eco") or {}).get("tried")
    refs = {c: ", ".join(f"{v} {d['mean']:.0f}" for v, d in rr["ioref"].get(c, {}).items()) for c in ("tt", "ff")}
    line = (f"{a.name}: route SDC TT {ss0} / FF {ff0} -> routed ref TT {rr['tt']:+.2f} / FF {rr['ff']:+.2f} DRC {drc} "
            f"(FF ref {refs['ff']}; TT ref {refs['tt']})")
    if closes or holdonly:
        stl = stage_list(j["spec"])
        vidx = next(i for i, x in enumerate(stl) if x["kind"] == "verdict")
        j.update(status="READY", stage_idx=vidx, stage_key="verdict", retries_used=0, errors=[], reason=None)
        event(j, f"FLOW-IOREF re-judge: {line} -> {'CLOSES' if closes else 'hold-only: ECO at the routed reference'}")
        ledger(j, f"RE-JUDGE at the routed insertion (no re-route): {line}")
    save_job(j)
    print(("FLIP " if closes else "HOLDONLY " if holdonly else "STILL ") + line)


@locked_job_command
def cmd_rebudget_rejudge(a):
    """human / tools/budgets/rebudget.py (REBUDGET 2026-10-08): re-judge a NEEDS_RTL job whose internal paths pass, with
    its RE-DERIVED IO budget (budget_rb<N> SDC: real die links, real block needs) appended after io_ref_routed.sdc in the
    routed re-STA -- no re-route.  Closes -> back to the verdict stage (READY; the cached re-STA is the verdict, the
    record cites budget_rb<N>); hold-only at the new budget with no ECO tried -> verdict stage too (post-route hold ECO);
    else it stays NEEDS_RTL with the result recorded under j["rebudget"].  --dry: re-STA only, the job is not changed."""
    j = load_job(a.name)
    m = dict(j.get("metrics") or {})
    if j["status"] not in ("NEEDS_RTL", "NEEDS_HUMAN") or not m.get("orfs_dir"):
        print(f"SKIP {a.name}: {j['status']}, orfs_dir {m.get('orfs_dir')}")
        return
    if (j.get("eco") or {}).get("installed"):
        print(f"SKIP {a.name}: an installed ECO replaced the route")
        return
    sdc = Path(a.sdc).resolve()
    if not sdc.is_file():
        print(f"SKIP {a.name}: no SDC {sdc}")
        return
    old_rb, old_rr = j.get("rebudget"), j.get("routed_ioref")
    j["rebudget"] = dict(rb=a.rb, sdc=str(sdc), at=now_iso())
    ss0 = m.get("route_sdc_clock", {}).get("ss_ps", m.get("ss_ps"))
    ff0 = m.get("route_sdc_clock", {}).get("ff_ps", m.get("ff_ps"))
    m["ss_ps"], m["ff_ps"] = ss0, ff0
    rr = routed_ioref(j, m)
    drc, failed = m.get("drc"), j.get("failed_checks") or []
    if not rr or not rr.get("available"):
        print(f"NOREF {a.name}: {(rr or {}).get('why')}")
        if not a.dry:
            j["rebudget"]["result"] = dict(available=False, why=(rr or {}).get("why"))
            save_job(j)
        return
    closes = rr["tt"] >= SS_MIN and rr["ff"] >= FF_MIN and drc == 0 and not failed
    holdonly = rr["tt"] >= SS_MIN and rr["ff"] < FF_MIN and drc == 0 and not failed and not (j.get("eco") or {}).get("tried")
    line = (f"{a.name}: route IO TT {ss0} / FF {ff0} -> {a.rb} TT {rr['tt']:+.2f} / FF {rr['ff']:+.2f} DRC {drc} "
            f"(TT i2r {rr.get('tt_i2r')} out {rr.get('tt_out')}; FF i2r {rr.get('ff_i2r')} out {rr.get('ff_out')} r2r {rr.get('ff_r2r')})")
    tag = "FLIP " if closes else "HOLDONLY " if holdonly else "STILL "
    if a.dry:
        print("DRY " + tag + line)
        return
    j["rebudget"]["result"] = dict(available=True, tt=rr["tt"], ff=rr["ff"], closes=closes, holdonly=holdonly)
    if closes or holdonly:
        stl = stage_list(j["spec"])
        vidx = next(i for i, x in enumerate(stl) if x["kind"] == "verdict")
        j.update(status="READY", stage_idx=vidx, stage_key="verdict", retries_used=0, errors=[], reason=None)
        event(j, f"REBUDGET re-judge under {a.rb} (re-derived die-link IO budget, no re-route): {line} -> "
                 f"{'CLOSES' if closes else 'hold-only: ECO at the new budget'}")
        ledger(j, f"RE-JUDGE under {a.rb} (re-derived die-link IO budget, no re-route): {line}")
    else:
        event(j, f"REBUDGET re-judge under {a.rb}: {line} -> still failing (stays NEEDS_RTL)")
    save_job(j)
    print(tag + line)


@locked_job_command
def cmd_reverdict(a):
    """human: re-judge a NEEDS_RTL / NEEDS_HUMAN job on its recorded evidence after an acceptance-line change, no re-route.
    Route sign-off meets the line -> back to the verdict stage (READY).  Else an earlier hold ECO whose recorded result
    meets the line but was not installed -> re-enter the ECO completion on the existing ECO output (status ECO; its
    result.json is re-read and judged by eco_passes, then installed and re-verdicted as usual)."""
    j = load_job(a.name)
    if j["status"] not in ("NEEDS_RTL", "NEEDS_HUMAN"):
        sys.exit(f"{a.name} is {j['status']}")
    m, e = j.get("metrics") or {}, j.get("eco") or {}
    if j.get("failed_checks"):
        sys.exit(f"{a.name}: verdict checks failed {j['failed_checks']}: not a line-only miss")
    stl = stage_list(j["spec"])
    vidx = next(i for i, x in enumerate(stl) if x["kind"] == "verdict")
    if eco_passes(dict(m, errors=[]), 0):
        j.update(status="READY", stage_idx=vidx, stage_key="verdict", retries_used=0, errors=[], reason=None)
        how = f"route sign-off {setup_corner_label(m)} {m.get('ss_ps')} / FF {m.get('ff_ps')} / DRC {m.get('drc')}"
    elif e.get("tried") and not e.get("installed") and eco_passes(e.get("result"), 0):
        r = ssh(j["host"], f"ls -t {j['run']}/cl/hold_eco.*.rc 2>/dev/null | head -1", timeout=60)
        rc_file = r.stdout.strip()
        if not rc_file:
            sys.exit(f"{a.name}: no hold_eco rc file under {j['run']}/cl")
        j.update(status="ECO", stage_idx=vidx, stage_key="hold_eco", stage_tag=Path(rc_file).name[:-3], retries_used=0,
                 errors=[], reason=None)
        how = f"recorded hold-ECO result {e.get('result')} ({j['stage_tag']})"
    else:
        sys.exit(f"{a.name}: recorded evidence does not meet {setup_corner_label(m)} >= {SS_MIN:g} / FF >= {FF_MIN:g} / DRC 0 "
                 f"(route {m.get('ss_ps')}/{m.get('ff_ps')}/{m.get('drc')}; eco {e.get('result')})")
    event(j, f"human re-verdict ({a.why}) at the line {setup_corner_label(m)} >= {SS_MIN:g} / FF >= {FF_MIN:g} / DRC 0 on {how}")
    save_job(j)
    ledger(j, f"RE-VERDICT (human, no re-route): {a.why}; {how}")


@locked_job_command
def cmd_retry_eco(a):
    """human: re-run the post-route hold ECO (current hold_eco rev) on a NEEDS_RTL job whose only miss was hold and whose
    earlier ECO missed; the earlier ECO is kept in eco_history and its output dir is preserved (new out: cl/eco-r<n>)."""
    j = load_job(a.name)
    e, m = j.get("eco") or {}, j.get("metrics") or {}
    if getattr(a, "stack", False):
        # DRIVE-1243: an INSTALLED ECO judged at a stale IO reference (the routed-insertion re-STA, e.g. after the
        # c4ffc4f9d vclk mapping, fails it on hold only): a second ECO on top of the installed db, at the routed reference
        if j["status"] != "NEEDS_RTL" or not e.get("installed"):
            sys.exit(f"{a.name}: --stack needs a NEEDS_RTL job with an installed ECO")
        j["eco_stack"] = dict(base=e["rb"], prior_out=e.get("out"), at=now_iso())
    elif j["status"] != "NEEDS_RTL" or not e.get("tried") or e.get("installed"):
        sys.exit(f"{a.name}: {j['status']}, eco tried={e.get('tried')} installed={e.get('installed')}: "
                 f"only a NEEDS_RTL job with an uninstalled, missed hold ECO can re-run it")
    if stage_list(j["spec"])[j["stage_idx"]]["kind"] != "verdict":
        sys.exit(f"{a.name}: not at its verdict stage")
    if not (m.get("ss_ps") is not None and m["ss_ps"] >= SS_MIN and m.get("drc") == 0 and m.get("ff_ps") is not None
            and m["ff_ps"] < FF_MIN):
        sys.exit(f"{a.name}: route verdict {setup_corner_label(m)} {m.get('ss_ps')} / FF {m.get('ff_ps')} / DRC {m.get('drc')} is not hold-only")
    j.setdefault("eco_history", []).append(e)
    j["eco"] = {}
    j.update(status="READY", stage_key="verdict", attempt=j["attempt"] + 1, retries_used=0, errors=[],
             reason=f"human retry-eco: {a.why}")
    event(j, f"human retry-eco ({a.why}): re-judged at the verdict; earlier ECO kept in eco_history")
    save_job(j)
    ledger(j, f"RETRY-ECO (human, hold_eco rev 2): {a.why}; earlier ECO {e.get('out')} -> {e.get('result')} kept")


@locked_job_command
def cmd_cancel(a):
    j = load_job(a.name)
    if j["status"] in TERMINAL:
        sys.exit(f"{a.name} already {j['status']}")
    why = getattr(a, "why", None)
    if why:
        event(j, f"cancel requested: {why}")
    j.update(status="CANCELLED", reason="cancelled by a human" + (f" ({why[:300]})" if why else ""), cancelled_at=now_iso())
    save_job(j)                 # durable even if the remote stop or experiment register fails
    if j.get("stage_tag") and j.get("host"):
        run, t = j["run"], j["stage_tag"]
        # only this loop's own stage process group, and only containers that mount this job's own run dir
        ssh(j["host"], f"""p=$(cat {run}/cl/{t}.pid 2>/dev/null); [ -n "$p" ] && kill -TERM -- -$p 2>/dev/null
for c in $(docker ps -q); do docker inspect --format '{{{{range .Mounts}}}}{{{{.Source}}}} {{{{end}}}}' $c | grep -q '{run}/' && docker stop -t 5 $c; done; true""",
            timeout=180)
    finish(j, "CANCELLED", j["reason"], "CANCELLED by a human" + (f": {why}" if why else ""))
    save_job(j)


def early_fail_finish(j, verdict, why, detail=None):
    """Stop a hopeless route (stuckscan gates): kill this job's own stage (and parallel tracks), record the diagnosis
    (STATE/early_fail/<name>.json, {CL}/early_fail.json) and end the job with the EARLY_FAIL_* verdict; failtrig/scan.py
    reports it as redesign work."""
    kill_own_stage(j)
    j["early_fail"] = dict(verdict=verdict, why=why, at=now_iso(), detail=detail or {})
    if j.get("host") and j.get("run") and detail:
        ssh(j["host"], f"cat > {j['run']}/cl/early_fail.json", input=json.dumps(detail, indent=1), timeout=60)
    paths = "\n".join(f"  {p.get('slack_ps')} ps {p.get('cls')} {p.get('dominated')}-dominated (wire {p.get('wire_ps')} / "
                      f"cell {p.get('cell_ps')} ps, fanout {p.get('max_fanout')}) {p.get('start')} -> {p.get('end')}"
                      for p in (detail or {}).get("paths", [])[:6])
    finish(j, verdict, why[:600], f"{verdict}: {why}" + (f"\nworst paths per group (post-CTS/placement report):\n{paths}"
                                                        if paths else ""))


@locked_job_command
def cmd_early_fail(a):
    j = load_job(a.name)
    if j["status"] != "RUNNING":
        sys.exit(f"{a.name} is {j['status']}, not RUNNING")
    if a.verdict not in EARLY_FAIL:
        sys.exit(f"verdict must be one of {EARLY_FAIL}")
    detail = json.loads(Path(a.detail).read_text()) if a.detail else None
    early_fail_finish(j, a.verdict, a.why, detail)
    save_job(j)

# HOLD-STOP (drive-resume 2026-10-09, coordinator APPROVED): a CTS / GRT hold repair that stalls already within a small
# margin (real FF hold WNS >= stuckscan.GATES["hold_nearmiss_ps"], -15 ps; setup gate not firing) is NOT early-failed.
# repair_timing cannot be stopped in-process, so the loop stops the stage and resumes the route from its ORFS checkpoint
# (OT_CL_RESUME=1, same host / run dir) with OT_HOLD_STOP="<stage>:<buffers>": that stage's hold repair replays up to the
# buffer count at which the stalled run reached its final WNS, then the flow continues to route; a later GRT hold repair
# is skipped (grt:0) after a CTS stop, so the flat tail cannot recur there.  The post-route hold ECO repairs the residue.
# A stage is stopped at most once per job (a second near-miss stall on the same stage early-fails as before).
HOLD_STOP_ALLOW = {"cts": "4_1_cts", "grt": "5_1_grt"}


def hold_stop_resume(j, stage, buffers, why):
    """stop the job's route stage (if running) and re-queue it as a same-host checkpoint resume with OT_HOLD_STOP"""
    if stage not in HOLD_STOP_ALLOW:
        raise ValueError(f"hold-stop stage must be one of {sorted(HOLD_STOP_ALLOW)}")
    if any(x.get("stage") == stage for x in j.get("hold_stop_log") or []):
        raise ValueError(f"{j['name']}: its {stage} hold repair was already stopped once")
    stl = stage_list(j["spec"])
    if stl[j["stage_idx"]]["kind"] != "route":
        raise ValueError(f"{j['name']}: stage {stl[j['stage_idx']]['key']} is not a route stage")
    host, run = j["host"], j["run"]
    if j["status"] == "RUNNING":
        kill_own_stage(j)
        for _ in range(30):
            r = ssh(host, f"for c in $(docker ps -q); do docker inspect --format '{{{{range .Mounts}}}}{{{{.Source}}}} {{{{end}}}}' $c "
                          f"| grep -q '{run}/' && echo BUSY; done; true", timeout=120)
            if "BUSY" not in r.stdout:
                break
            time.sleep(10)
    ship_helpers(host, run)
    r = ssh(host, f"cd {run}/src && python3 {run}/cl/resume_patch.py .", timeout=120)
    if r.returncode:
        raise RuntimeError(f"resume patch failed: {(r.stdout + r.stderr)[-400:]}")
    dm = subst(j["spec"].get("verdict", {}).get("drc_metrics", ""), j)
    orfs = dm.split("/logs/")[0] if "/logs/" in dm else None
    if not orfs:
        raise RuntimeError("hold-stop resume: no ORFS checkpoint path (verdict.drc_metrics)")
    chk = ssh(host, f"O=$(ls -d {orfs} | tail -1); bash {run}/cl/resume_check.sh $O {run}/src {HOLD_STOP_ALLOW[stage]}",
              timeout=600)
    if chk.returncode or not re.search(r"^RESUME_OK=1$", chk.stdout, re.M):
        raise RuntimeError(f"hold-stop resume check failed rc={chk.returncode}: {(chk.stdout + chk.stderr)[-400:]}")
    hs = dict(j.get("hold_stop") or {})
    hs[stage] = int(buffers)
    if stage == "cts":
        hs.setdefault("grt", 0)
    j["hold_stop"] = hs
    j.setdefault("hold_stop_log", []).append(dict(stage=stage, buffers=int(buffers), why=why[:600], at=now_iso(),
                                                  attempt=j["attempt"] + 1, prev_status=j["status"]))
    j["resume"] = dict(from_host=host, to_host=host, run=run, at=now_iso(), kind="hold_stop",
                       check=chk.stdout.strip()[-400:])
    j["checkpoint_affinity"] = dict(host=host, run=run)
    j.pop("early_fail", None)
    j.update(status="READY", attempt=j["attempt"] + 1, wait=None, errors=[], reason=None)
    stage_txt = " ".join(f"{k}:{v}" for k, v in sorted(hs.items()))
    event(j, f"HOLD-STOP {stage}: near-miss hold stall, not early-failed; route resumes from its checkpoint with "
             f"OT_HOLD_STOP='{stage_txt}' ({why[:300]})")
    ledger(j, f"HOLD-STOP {stage} ({stage_txt}): {why}")
    experiment(j, f"running: route resumed from checkpoint, hold repair stopped at {stage}")


@locked_job_command
def cmd_hold_stop(a):
    """stuckscan / human: stop a near-miss stalled CTS/GRT hold repair and resume the route (hold_stop_resume).  Accepts a
    RUNNING route or an EARLY_FAIL_HOLD job whose run dir still holds its checkpoint."""
    j = load_job(a.name)
    if j["status"] not in ("RUNNING", "EARLY_FAIL_HOLD"):
        sys.exit(f"{a.name} is {j['status']}: hold-stop needs RUNNING or EARLY_FAIL_HOLD")
    hold_stop_resume(j, a.stage, a.buffers, a.why)
    save_job(j)
    print(f"HOLD-STOP {a.name} {a.stage}:{a.buffers} -> READY (attempt {j['attempt']})")


@locked_job_command
def cmd_kill_stage(a):
    """stuckscan: kill a hung / stalled stage of a RUNNING job (its own process group, and the flow containers mounting
    --orfs, else every container of its run dir).  The loop then sees the stage LOST and retries it once (crash path)."""
    j = load_job(a.name)
    if j["status"] != "RUNNING" or not (j.get("stage_tag") and j.get("host")):
        sys.exit(f"{a.name} is {j['status']}: no running stage to kill")
    run, t = j["run"], j["stage_tag"]
    pat = shlex.quote((a.orfs.rstrip("/") + ":") if a.orfs else (run + "/"))
    ssh(j["host"], f"""p=$(cat {run}/cl/{t}.pid 2>/dev/null); [ -n "$p" ] && kill -TERM -- -$p 2>/dev/null
for c in $(docker ps -q); do docker inspect --format '{{{{range .Mounts}}}}{{{{.Source}}}}:{{{{.Destination}}}} {{{{end}}}}' $c | grep -qF {pat} && docker stop -t 5 $c; done; true""",
        timeout=300)
    j["stuck_kill"] = dict(at=now_iso(), why=a.why, tag=t)
    event(j, f"stage {t} killed by stuckscan ({a.why[:300]}); the loop retries it once")
    ledger(j, f"STUCK-KILL {t}: {a.why}")
    save_job(j)


def validate_overlay_recovery(j):
    expected_failure = dict(ss_ps=-340500.58, ff_ps=-59.43, drc=0, cells_added=0, errors=[])
    expected_pre = dict(ss_ps=190.49, ff_ps=-70.99)
    e = j.get("eco") or {}
    m = j.get("metrics") or {}
    if (j["name"] != "hbglue_cl_8ddc70024" or j.get("commit_full") != "8ddc7002479798a1e3d5ce5875a163d672973e75"
            or j["spec"]["source"]["commit"] != j["commit_full"] or j["status"] != "NEEDS_RTL"
            or j.get("attempt") != 1 or j.get("eco_overlay_recovery") or j.get("eco_history")
            or e.get("installed") or e.get("post_sdc") or not e.get("tried")
            or e.get("result") != expected_failure or e.get("pre") != expected_pre
            or {k: m.get(k) for k in expected_pre} != expected_pre or m.get("drc") != 0
            or m.get("errors") or j.get("failed_checks") or j["spec"]["verdict"].get("post_sdc")
            or m.get("post_sdc") != ["physical/s81_die_views/hbglue/margin/signoff_cl_hbglue_cl_8ddc70024.sdc"]
            or stage_list(j["spec"])[j["stage_idx"]]["kind"] != "verdict"):
        raise ValueError("not the explicitly authorized, uninstalled hbglue missing-overlay ECO failure")


@locked_job_command
def cmd_recover_eco_overlays(a):
    j = load_job(a.name)
    validate_overlay_recovery(j)
    pinned = json.loads((HERE / "evidence/reliability_20261006.json").read_text())["original_hbglue_hashes_verified"]
    request = dict(job=j, original_hashes={k: pinned[k] for k in ("odb", "spef", "sdc")},
                   post_sdc_hashes={j["metrics"]["post_sdc"][0]: pinned["post_sdc"]})
    r = ssh(j["host"], "python3 - prepare " + shlex.quote(json.dumps(request)),
            input=(HERE / "eco_recovery.py").read_text(), timeout=120, check=True)
    recovery = json.loads(r.stdout)
    recovery.update(requested=now_iso(), reason="owner-authorized one-shot correction of omitted measured overlays")
    j["eco_overlay_recovery"] = recovery
    j.setdefault("eco_history", []).append(j["eco"])
    j["eco"] = {}              # only this named job's verdict can request one new ECO
    j.update(status="READY", stage_key="verdict", attempt=2, errors=[], reason="explicit ECO overlay recovery queued")
    event(j, f"one-shot ECO overlay recovery queued: {recovery['out']}; original failure and inputs preserved")
    save_job(j)
    ledger(j, f"ECO overlay recovery requested; original failed ECO retained; admission at verdict; {recovery['out']}")


@locked_job_command
def cmd_restore_cancelled(a):
    """Recover pre-lock cancellation lost to a stale save. Never stop remote work."""
    j = load_job(a.name)
    if j["status"] == "CANCELLED":
        return
    # Require explicit historical intent; a replacement name alone is insufficient.
    cancellations = [line for line in LEDGER.read_text().splitlines()
                     if f" | {a.name} | " in line and " | CANCELLED by a human | " in line]
    if not cancellations:
        sys.exit(f"{a.name}: no human cancellation in {LEDGER}")
    if j["status"] == "CLOSED":
        sys.exit(f"{a.name}: already CLOSED; requires parent investigation")
    archive = STATE / "cancel_recovery"
    archive.mkdir(parents=True, exist_ok=True)
    backup = archive / f"{a.name}.{time.time_ns()}.json"
    with backup.open("x") as f:
        f.write(jpath(a.name).read_text())
    j["cancel_recovery"] = dict(backup=str(backup), ledger=cancellations[-1],
                               preserved_stage={k: j.get(k) for k in
                                                ("status", "host", "run", "stage_tag", "stage_started")},
                               remote_action="none; existing processes and evidence preserved")
    j.update(status="CANCELLED", reason="restored ledger cancellation; remote work preserved", cancelled_at=now_iso())
    event(j, j["reason"])
    save_job(j)
    ledger(j, f"CANCELLED restored from ledger; no remote stop; prior state {backup}; "
              f"preserved {j.get('stage_tag')} at {j.get('host')}:{j.get('run')}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("daemon"); d.add_argument("--interval", type=int, default=60)
    sub.add_parser("tick"); sub.add_parser("status")
    v = sub.add_parser("validate"); v.add_argument("file")
    sr = sub.add_parser("submit-recheck"); sr.add_argument("--since", required=True)
    sr.add_argument("--requeue", action="store_true"); sr.add_argument("--log")
    r = sub.add_parser("retry"); r.add_argument("name"); r.add_argument("--at", help="resume at this stage key")
    r = sub.add_parser("retry-eco"); r.add_argument("name"); r.add_argument("--why", default="hold_eco rev 2")
    r.add_argument("--stack", action="store_true", help="ECO on top of an installed ECO (its db in the route base)")
    r = sub.add_parser("ioref-rejudge"); r.add_argument("name")
    r = sub.add_parser("rebudget-rejudge"); r.add_argument("name"); r.add_argument("--rb", required=True)
    r.add_argument("--sdc", required=True); r.add_argument("--dry", action="store_true")
    r = sub.add_parser("reverdict"); r.add_argument("name"); r.add_argument("--why", default="owner line TTsetup>=0/FFhold>=0/DRC0; SS sensitivity")
    c = sub.add_parser("cancel"); c.add_argument("name"); c.add_argument("--why")
    ef = sub.add_parser("early-fail"); ef.add_argument("name"); ef.add_argument("--verdict", required=True)
    ef.add_argument("--why", required=True); ef.add_argument("--detail")
    hs = sub.add_parser("hold-stop"); hs.add_argument("name"); hs.add_argument("--stage", required=True, choices=("cts", "grt"))
    hs.add_argument("--buffers", type=int, required=True); hs.add_argument("--why", required=True)
    ks = sub.add_parser("kill-stage"); ks.add_argument("name"); ks.add_argument("--why", required=True)
    ks.add_argument("--orfs")
    rc = sub.add_parser("restore-cancelled"); rc.add_argument("name")
    er = sub.add_parser("recover-eco-overlays"); er.add_argument("name")
    mg = sub.add_parser("migrate"); mg.add_argument("name"); mg.add_argument("host")
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
    elif a.cmd == "submit-recheck":
        cmd_submit_recheck(a)
    elif a.cmd == "retry":
        cmd_retry(a)
    elif a.cmd == "retry-eco":
        cmd_retry_eco(a)
    elif a.cmd == "reverdict":
        cmd_reverdict(a)
    elif a.cmd == "ioref-rejudge":
        cmd_ioref_rejudge(a)
    elif a.cmd == "rebudget-rejudge":
        cmd_rebudget_rejudge(a)
    elif a.cmd == "cancel":
        cmd_cancel(a)
    elif a.cmd == "early-fail":
        cmd_early_fail(a)
    elif a.cmd == "kill-stage":
        cmd_kill_stage(a)
    elif a.cmd == "hold-stop":
        cmd_hold_stop(a)
    elif a.cmd == "recover-eco-overlays":
        cmd_recover_eco_overlays(a)
    elif a.cmd == "restore-cancelled":
        cmd_restore_cancelled(a)
    elif a.cmd == "migrate":     # executed by the daemon at its next tick (no race with the job's poller)
        (STATE / "migrate_requests").mkdir(parents=True, exist_ok=True)
        (STATE / "migrate_requests" / f"{a.name}.json").write_text(json.dumps(dict(name=a.name, host=a.host)))
        print(f"migrate request queued: {a.name} -> {a.host}")


if __name__ == "__main__":
    main()
