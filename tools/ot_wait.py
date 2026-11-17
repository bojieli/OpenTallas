#!/usr/bin/env python3 -I
"""ot_wait.py -- WAVE-FLOW-R2 11-17 (COORD, FABLE-FLOW-1300 item 1): the ONE waiter for an ot-run unit or a kit.

Lanes use this instead of private `while systemctl is-active` loops (KV's showed six dead ring masters as RUNNING for 85 minutes: a unit that is
`active` with no live process is an exited job, not a running one).  Result states:

  DONE     the job exited 0 (systemd Result=success and ExecMainStatus 0, or the client log's `exit 0`)
  FAILED   the job exited non-zero, failed, was killed, vanished without an exit status, or is `active` with no live process
  RUNNING  only while a live process of the unit / kit exists (never returned for an exited unit)
  TIMEOUT  --timeout seconds passed while still alive (exit status 2)

    ot_wait.py --unit UNIT [--host HOST] [--log FILE] [--timeout S] [--poll S] [--tail N] [--once]
    ot_wait.py --kit DIR   [--host HOST] ...          a kit: alive while a process names the kit dir; FAILED when a FAIL_* marker exists

Prints one JSON object (state, rc, status, reason, log_tail) and exits 0 DONE / 1 FAILED / 2 TIMEOUT-or-RUNNING (--once).
"""
import argparse
import json
import re
import shlex
import subprocess
import sys
import time

LIVE_ACTIVE = ("active", "activating", "reloading", "deactivating")
RAN_RE = re.compile(r"ot-run: RAN on \S+(?: \(unit \S+\))?: exit (-?\d+)")
NOTRUN_RE = re.compile(r"ot-run: NOT RUN\b[^\n]*")
PROPS = "Id,LoadState,ActiveState,SubState,Result,ExecMainStatus,ExecMainCode,MainPID,ControlGroup,Type"
LOCAL = (None, "", "localhost", "hub")


def sh(host, cmd, timeout=60):
    """run a shell command locally or over ssh -> (rc, stdout)"""
    argv = ["bash", "-c", cmd] if host in LOCAL else ["ssh", "-n", "-o", "ControlPath=none", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", host, cmd]
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return 255, f"{type(e).__name__}: {e}"
    return r.returncode, r.stdout


def parse_props(text):
    return dict(ln.split("=", 1) for ln in (text or "").splitlines() if "=" in ln)


def unit_props(host, unit, run=sh):
    rc, out = run(host, f"systemctl --user show {shlex.quote(unit)} -p {PROPS} 2>&1")
    return parse_props(out) if rc == 0 else {"LoadState": "unknown", "ActiveState": "unknown", "_err": out.strip()[:200]}


def live_pids(host, props, run=sh):
    """live processes of the unit: its MainPID, else every pid in its cgroup (a scope has no MainPID).  -> [pid]"""
    pids = []
    mp = props.get("MainPID", "0")
    if mp.isdigit() and int(mp) > 0:
        rc, out = run(host, f"test -d /proc/{int(mp)} && grep -q '^State:.*[^Z]$' /proc/{int(mp)}/status 2>/dev/null && echo {int(mp)}")
        pids += [int(x) for x in out.split() if x.isdigit()]
    cg = props.get("ControlGroup", "")
    if not pids and cg.startswith("/"):
        rc, out = run(host, f"cat /sys/fs/cgroup{shlex.quote(cg)}/cgroup.procs 2>/dev/null")
        pids += [int(x) for x in out.split() if x.isdigit()]
    return pids


def log_tail(host, unit, log, n, run=sh):
    if log:
        rc, out = run(host, f"tail -n {int(n)} {shlex.quote(log)} 2>&1")
    else:
        rc, out = run(host, f"journalctl --user -u {shlex.quote(unit)} -n {int(n)} --no-pager -o cat 2>&1")
    return [x for x in out.splitlines() if x.strip()][-n:]


def log_exit(lines):
    """exit status the ot-run client log records: ('RAN', n) | ('NOT RUN', None) | None"""
    for ln in reversed(lines):
        m = RAN_RE.search(ln)
        if m:
            return "RAN", int(m.group(1))
        if NOTRUN_RE.search(ln):
            return "NOT RUN", None
    return None


def classify_unit(props, pids, tail):
    """-> (state, rc, reason).  RUNNING only with a live process; every exited / vanished unit is DONE or FAILED."""
    load, act, sub, res = props.get("LoadState", ""), props.get("ActiveState", ""), props.get("SubState", ""), props.get("Result", "")
    st = props.get("ExecMainStatus", "")
    code = int(st) if st.lstrip("-").isdigit() else None
    if act in LIVE_ACTIVE and pids:
        return "RUNNING", None, f"{act}/{sub}, live pids {pids[:5]}"
    ex = log_exit(tail)
    if load == "not-found" or act in ("unknown", ""):
        if ex and ex[0] == "RAN":
            return ("DONE" if ex[1] == 0 else "FAILED"), ex[1], "unit collected; exit status from the client log"
        return "FAILED", None, f"unit {load or act}: exited and collected, no exit status recorded ({props.get('_err', '')})".strip()
    if act in LIVE_ACTIVE:           # active / deactivating with no live process: it exited (the 85-minute false RUNNING)
        rc = code if code is not None else (ex[1] if ex and ex[0] == "RAN" else None)
        return ("DONE" if rc == 0 and ex != ("NOT RUN", None) else "FAILED"), rc, f"{act}/{sub} but no live process"
    is_scope = props.get("Type", "") == "scope" or (props.get("Id") or "").endswith(".scope")
    if act == "failed" and res in ("", "success") and is_scope:
        # a .scope carries no ExecMainStatus (nothing is exec'd by systemd): ot-heavy runs the job in a scope and systemd marks the scope `failed` with Result=success when its processes were
        # stopped (cgroup torn down) after the job had exited; the exit status is the one the ot-run client logged (HEAD-PLAN-R4: two jobs that logged exit 0 were reported FAILED)
        if ex and ex[0] == "RAN":
            return ("DONE" if ex[1] == 0 else "FAILED"), ex[1], f"scope {act}/{sub} Result={res}: exit status {ex[1]} from the client log"
        return "FAILED", None, f"scope {act}/{sub} Result={res}: no exit status in the client log"
    if act == "failed" or res not in ("", "success"):
        return "FAILED", code, f"{act}/{sub} Result={res} exit {code}"
    if ex and ex[0] == "NOT RUN":
        return "FAILED", None, "ot-run NOT RUN (no host admitted it)"
    if code not in (None, 0):
        return "FAILED", code, f"{act}/{sub} exit {code}"
    if ex and ex[0] == "RAN" and ex[1] != 0:
        return "FAILED", ex[1], "client log exit " + str(ex[1])
    return "DONE", 0 if code is None else code, f"{act}/{sub} Result={res or 'success'}"


def kit_alive(host, kit, run=sh):
    rc, out = run(host, f"ps -eo pid=,args= | grep -F -- {shlex.quote(kit)} | grep -v -e grep -e ot_wait | awk '{{print $1}}'")
    return [int(x) for x in out.split() if x.isdigit()]


def classify_kit(host, kit, pids, run=sh):
    if pids:
        return "RUNNING", None, f"live pids {pids[:5]}", []
    rc, out = run(host, f"cd {shlex.quote(kit)} 2>/dev/null && ls -1 FAIL_* 2>/dev/null")
    marks = [x for x in out.split() if x.startswith("FAIL_")]
    if marks:
        rc2, body = run(host, f"cd {shlex.quote(kit)} && tail -n 5 {' '.join(shlex.quote(m) for m in marks[:3])} 2>&1")
        return "FAILED", None, "failure marker " + ",".join(marks[:3]), [x for x in body.splitlines() if x.strip()][-8:]
    rc3, logs = run(host, f"ls -1t {shlex.quote(kit)}/run_*.log {shlex.quote(kit)}/*.log 2>/dev/null | head -1")
    lg = logs.strip()
    tail = [x for x in run(host, f"tail -n 8 {shlex.quote(lg)} 2>&1")[1].splitlines() if x.strip()] if lg else []
    ex = log_exit(tail)
    if ex and ex[0] == "RAN" and ex[1] != 0:
        return "FAILED", ex[1], f"log exit {ex[1]}", tail
    if not rc and not out and not lg and rc3 == 0:
        return "FAILED", None, "kit has no process, no marker and no log", tail
    return "DONE", 0, "no live process and no FAIL_* marker", tail


def wait(unit=None, kit=None, host=None, log=None, timeout=0, poll=15, tail=12, run=sh, sleep=time.sleep, now=time.time, once=False):
    """poll until the unit / kit is no longer alive -> result dict (state, rc, reason, log_tail, waited_s); once = one reading"""
    t0 = now()
    while True:
        if kit:
            pids = kit_alive(host, kit, run)
            state, rc, reason, lines = classify_kit(host, kit, pids, run)
        else:
            props = unit_props(host, unit, run)
            pids = live_pids(host, props, run)
            lines = [] if props.get("ActiveState") in LIVE_ACTIVE and pids else log_tail(host, unit, log, tail, run)
            state, rc, reason = classify_unit(props, pids, lines)
        if state != "RUNNING" or once:
            break
        if timeout and now() - t0 >= timeout:
            state, reason = "TIMEOUT", f"still alive after {int(now() - t0)} s: {reason}"
            break
        sleep(poll)
    return dict(state=state, rc=rc, reason=reason, unit=unit, kit=kit, host=host or "localhost", waited_s=int(now() - t0),
                log_tail=[] if state == "RUNNING" else lines[-tail:])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--unit")
    g.add_argument("--kit")
    ap.add_argument("--host")
    ap.add_argument("--log")
    ap.add_argument("--timeout", type=int, default=0, help="seconds; 0 = wait until it exits")
    ap.add_argument("--poll", type=int, default=15)
    ap.add_argument("--tail", type=int, default=12)
    ap.add_argument("--once", action="store_true", help="one reading, no waiting")
    a = ap.parse_args(argv)
    res = wait(a.unit, a.kit, a.host, a.log, timeout=a.timeout, poll=a.poll, tail=a.tail, once=a.once)
    print(json.dumps(res))
    return {"DONE": 0, "FAILED": 1}.get(res["state"], 2)


if __name__ == "__main__":
    sys.exit(main())
