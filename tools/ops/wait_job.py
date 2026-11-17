#!/usr/bin/env python3
"""wait_job.py: wait for ONE job to end, named by pid, systemd unit or ot-run unit id; never by a command-line pattern (WAVE-CONFIG 11-16).

  python3 -I tools/ops/wait_job.py --pid 12345 [--timeout S] [--poll S]
  python3 -I tools/ops/wait_job.py --unit NAME [--user] [--host H]          systemd service/scope (--user = the user manager)
  python3 -I tools/ops/wait_job.py --ot-run-unit oth-ubuntu-123-1699999999 [--host H]     an ot-heavy unit (a --user scope; ".scope" optional)

Why: a waiter that looked for its job with `pgrep -f <pattern>` matched its own command line (the pattern is in it) and waited forever.  This
helper never reads a command line.  A pid is checked by number and start time (a reused pid counts as ended; a zombie counts as ended); a unit is
checked with `systemctl show` (LoadState / ActiveState).  A pid that is this process or one of its ancestors is refused (it can never end first).
--host H asks a fleet host over ssh (BatchMode, no ControlPath); an ssh failure is never read as "ended": 5 in a row exit 3.
A unit that does not exist when the wait starts is an error (exit 2: a typo would otherwise return at once); --missing-ok says it may already be gone.
Exit: 0 the job ended, 124 --timeout, 2 bad request / job not found at start, 3 cannot look (ssh or systemctl failed repeatedly).
Library: wait_pid(pid, ...), wait_unit(unit, ...) return the same codes.  No output unless --verbose; the verdict line goes to stderr."""
import argparse
import os
import shlex
import subprocess
import sys
import time

EXIT_ENDED, EXIT_BAD, EXIT_BLIND, EXIT_TIMEOUT = 0, 2, 3, 124
BLIND_LIMIT = 5


def pid_start(pid):
    """(start time in clock ticks, state letter) of a pid from /proc/<pid>/stat, or None when it does not exist.  The comm field may hold spaces
    and parentheses: split after the LAST ')'."""
    try:
        with open(f"/proc/{pid}/stat") as f:
            raw = f.read()
    except OSError:
        return None
    rest = raw[raw.rindex(")") + 2:].split()
    return int(rest[19]), rest[0]


def _ppid(p):
    with open(f"/proc/{p}/stat") as f:
        raw = f.read()
    return int(raw[raw.rindex(")") + 2:].split()[1])


def ancestors(pid=None):
    """this process and its parents (pids)"""
    out, p = set(), pid or os.getpid()
    while p > 1 and p not in out:
        out.add(p)
        try:
            p = _ppid(p)
        except (OSError, ValueError, IndexError):
            break
    return out


def wait_pid(pid, timeout=None, poll=2.0, sleep=time.sleep, clock=time.monotonic):
    if pid in ancestors():
        print(f"wait_job: pid {pid} is this waiter or one of its parents; it cannot end before the wait does", file=sys.stderr)
        return EXIT_BAD
    first = pid_start(pid)
    if first is None:
        print(f"wait_job: pid {pid} does not exist", file=sys.stderr)
        return EXIT_BAD
    t0 = clock()
    while True:
        now = pid_start(pid)
        if now is None or now[0] != first[0] or now[1] in ("Z", "X"):
            return EXIT_ENDED
        if timeout is not None and clock() - t0 >= timeout:
            return EXIT_TIMEOUT
        sleep(poll)


def unit_state(unit, user=False, host=None, run=subprocess.run):
    """(LoadState, ActiveState) of a unit, or None when systemctl / ssh could not be asked"""
    cmd = ["systemctl"] + (["--user"] if user else []) + ["show", "-p", "LoadState", "-p", "ActiveState", "--", unit]
    if host:
        cmd = ["ssh", "-n", "-o", "BatchMode=yes", "-o", "ControlPath=none", "-o", "ConnectTimeout=15", host] + \
              [shlex.join(cmd)]
    try:
        p = run(cmd, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if p.returncode:
        return None
    kv = dict(l.split("=", 1) for l in p.stdout.splitlines() if "=" in l)
    if "LoadState" not in kv or "ActiveState" not in kv:
        return None
    return kv["LoadState"], kv["ActiveState"]


def wait_unit(unit, user=False, host=None, timeout=None, poll=5.0, missing_ok=False, sleep=time.sleep, clock=time.monotonic, state=unit_state):
    t0, blind, seen = clock(), 0, False
    while True:
        st = state(unit, user, host)
        if st is None:
            blind += 1
            if blind >= BLIND_LIMIT:
                print(f"wait_job: cannot read the state of {unit}{' on ' + host if host else ''} ({BLIND_LIMIT} tries); not treating that as ended", file=sys.stderr)
                return EXIT_BLIND
        else:
            blind = 0
            load, active = st
            gone = load == "not-found" or active in ("inactive", "failed", "dead")
            if load == "not-found" and not seen and not missing_ok:
                print(f"wait_job: unit {unit} not found (use --missing-ok if it may have ended already)", file=sys.stderr)
                return EXIT_BAD
            if gone:
                return EXIT_ENDED
            seen = True
        if timeout is not None and clock() - t0 >= timeout:
            return EXIT_TIMEOUT
        sleep(poll)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--pid", type=int)
    g.add_argument("--unit")
    g.add_argument("--ot-run-unit", dest="otunit", help="ot-heavy unit id, e.g. oth-ubuntu-123-1699999999 (a --user scope)")
    ap.add_argument("--user", action="store_true", help="--unit lives in the user manager")
    ap.add_argument("--host", help="ask this fleet host over ssh (units only)")
    ap.add_argument("--timeout", type=float, help="seconds; exit 124 when the job is still running")
    ap.add_argument("--poll", type=float, default=None, help="seconds between looks (pid 2, unit 5)")
    ap.add_argument("--missing-ok", action="store_true")
    ap.add_argument("--verbose", "-v", action="store_true")
    a = ap.parse_args(argv)
    if a.pid is not None:
        if a.host:
            ap.error("--host applies to units; a pid on another host is not addressable")
        if a.pid <= 1:
            ap.error("bad pid")
        rc = wait_pid(a.pid, a.timeout, a.poll or 2.0)
        what = f"pid {a.pid}"
    else:
        unit, user = a.unit, a.user
        if a.otunit:
            unit, user = (a.otunit if a.otunit.endswith(".scope") else a.otunit + ".scope"), True
        if not unit or unit.startswith("-") or any(c.isspace() or c in ";|&$`'\"\\" for c in unit):
            ap.error("bad unit name")
        rc = wait_unit(unit, user, a.host, a.timeout, a.poll or 5.0, a.missing_ok)
        what = f"unit {unit}"
    if a.verbose or rc:
        print(f"wait_job: {what}: " + {0: "ended", 2: "refused", 3: "unreadable", 124: "timeout"}.get(rc, str(rc)), file=sys.stderr)
    return rc


if __name__ == "__main__":
    sys.exit(main())
