"""ot_status: one exit-status file per ot-run unit / ot-push-main push, and a DONE/DIED post (WAITER-STD-1600, 2026-11-20).

Why: proofs died unseen (lepe proof7 exit 2 sat 16 h) because lanes waited with `pgrep -f`, whose waiter matched itself.  The tool
that ran the work now records how it ended, and `ot-wait` reads that record.

Record: $OT_STATUS_DIR (default ~/.local/state/ot-status) / <name>.json, written atomically (tmp + rename) at start and at end:
  {schema, kind (run|push), name, unit, host, pid, pid_start, lane, cmd, log, t_start, state (running|done), rc, t_end}
  name: run  -> otrun-<host>-<client pid>   (the ot-run client; its pid is what a lane has in $!)
        push -> otpush-<host>-<pid>
  unit is the oth-... scope name once ot-heavy admitted the job (ot-wait accepts it too).
Post: bash ~/coord/bin/post.sh <LANE> "DONE|DIED [<LANE>] ..." (on the hub directly, elsewhere through ssh intel2), detached so the exit
is never delayed.  LANE = $OT_LANE (explicit), for a push also the lane clone's directory name; no lane -> no post (the file is still written).
DIED = rc != 0 (or no exit status at all).  DONE of an ot-run unit is posted only when it ran >= OT_STATUS_DONE_MIN_S (default 120 s).
OT_STATUS=0 turns the whole thing off; OT_STATUS_POST=0 turns off only the post."""
import json
import os
import re
import socket
import subprocess
import sys
import time

SCHEMA = "opentallas.ot_status.v1"
NOT_LANES = {"rt", "warm", "git-mirror", "flowhold", "ttbatch", "ttviews", "mq-gate", "claude"}
LANE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
DIR_LANE = re.compile(r"/srv/opentallas-scratch[^/]*/claude/([A-Za-z0-9][A-Za-z0-9._-]*)(?:/|$)")


def status_dir():
    return os.environ.get("OT_STATUS_DIR") or os.path.join(os.path.expanduser("~"), ".local", "state", "ot-status")


def enabled():
    if os.environ.get("PYTEST_CURRENT_TEST") and not os.environ.get("OT_STATUS_DIR"):
        return False                         # other tests that run ot-run / ot-push-main must not write records or post
    return os.environ.get("OT_STATUS", "1") != "0"


def host():
    return socket.gethostname().split(".")[0]


def pid_start(pid):
    """field 22 of /proc/<pid>/stat (clock ticks since boot): tells a reused pid from the original"""
    try:
        s = open(f"/proc/{pid}/stat").read()
        return int(s[s.rindex(")") + 2:].split()[19])
    except (OSError, ValueError, IndexError):
        return None


def cmdline(pid):
    try:
        return open(f"/proc/{pid}/cmdline", "rb").read().replace(b"\0", b" ").decode(errors="replace").strip()
    except OSError:
        return ""


def lane_name(path=None, explicit_only=False):
    v = os.environ.get("OT_LANE", "").strip()
    if v and LANE_RE.match(v):
        return v
    if explicit_only:
        return ""
    m = DIR_LANE.match(os.path.realpath(path or os.getcwd()))
    return m.group(1) if m and m.group(1) not in NOT_LANES else ""


def _log_path():
    for fd in (1, 2):
        try:
            p = os.readlink(f"/proc/self/fd/{fd}")
        except OSError:
            continue
        if p.startswith("/") and not p.startswith(("/dev/", "/proc/")) and os.path.isfile(p):
            return p
    return ""


def path_of(name):
    return os.path.join(status_dir(), name + ".json")


def write(rec):
    d = status_dir()
    os.makedirs(d, exist_ok=True)
    tmp = os.path.join(d, f".{rec['name']}.{os.getpid()}.tmp")
    with open(tmp, "w") as f:
        json.dump(rec, f, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path_of(rec["name"]))


def read(name):
    try:
        return json.load(open(path_of(name)))
    except (OSError, ValueError):
        return None


def begin(kind, cmd="", lane=None, log=None):
    """-> record (also on disk, state running); None when disabled or the directory is not writable"""
    if not enabled():
        return None
    pid = os.getpid()
    rec = dict(schema=SCHEMA, kind=kind, name=f"ot{kind}-{host()}-{pid}", unit="", host=host(), pid=pid, pid_start=pid_start(pid),
               lane=lane if lane is not None else lane_name(), cmd=str(cmd)[:400], log=log if log is not None else _log_path(),
               t_start=int(time.time()), state="running", rc=None, t_end=None)
    try:
        write(rec)
    except OSError:
        return None
    return rec


def update(rec, **kw):
    if rec is None:
        return
    rec.update(kw)
    try:
        write(rec)
    except OSError:
        pass


def env_tag(cmd):
    """DONE/DIED env=wave+N: a kit named in the command (an absolute path, or one with a kit_env_provenance.json up to 3 parents above)
    -> " env=wave+N" (N = env keys differing from the wave env that are not plan-derived); "" when no kit record is readable here"""
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "autopilot"))
        import env_provenance as _EP
        for tok in re.findall(r"/[^\s\"';|&<>]+", str(cmd)):
            d = tok
            for _ in range(4):
                if os.path.isfile(os.path.join(d, _EP.RECORD)):
                    n = _EP.wave_delta(d)
                    return "" if n is None else f" env=wave+{n}"
                d = os.path.dirname(d)
                if len(d) < 2:
                    break
    except Exception:
        pass
    return ""


def post_text(rec):
    died = rec.get("rc") != 0
    secs = (rec.get("t_end") or 0) - rec.get("t_start", 0)
    what = "ot-push-main" if rec["kind"] == "push" else "ot-run"
    head = f"{'DIED' if died else 'DONE'} [{rec['lane']}]"
    tail = ""
    if died:
        try:
            import ot_deathclass      # FLOW-DEATHCLASS-R1: class + one-line cause on every DIED post
            tail = ot_deathclass.label(rec.get("rc"), rec.get("cmd", ""), rec.get("log"), secs, refusal=rec.get("refusal"))
        except Exception:
            tail = " | class=NO-PATTERN cause=classifier unavailable"
    return (f"{head} {what} {rec['unit'] or rec['name']} on {rec['host']}: rc={rec['rc']} after {secs} s, ended "
            f"{time.strftime('%H:%M:%S', time.localtime(rec['t_end']))}{env_tag(rec.get('cmd', ''))}, log {rec.get('log') or 'none'}, cmd: {rec['cmd'][:140]}{tail}")


def should_post(rec):
    if os.environ.get("OT_STATUS_POST", "1") == "0" or not rec.get("lane") or not enabled():
        return False
    if rec["kind"] == "run":
        if not os.environ.get("OT_LANE"):
            return False                      # run jobs post only for a lane that named itself; the autopilot's launches never do
        if rec.get("rc") == 0 and (rec["t_end"] - rec["t_start"]) < float(os.environ.get("OT_STATUS_DONE_MIN_S", "120")):
            return False
    return True


STDOUT_WAIT_S = 45.0


def stdout_log_of(log):
    """a kit_wave stage log X.live.log holds stderr only; the stage's stdout X.log (the verdict) is written by the CALLER after ot-run exits"""
    log = str(log or "")
    return log[:-len(".live.log")] + ".log" if log.endswith(".live.log") else ""


def wait_stdout_log(rec, wait_s=None, sleep=time.sleep, now=time.time):
    """D1 (FABLE-FLOW-0800: NO-PATTERN 43 % of DIED): 42 of 70 NO-PATTERN DIED posts on 11-22 were AUTO-GEOM FAIL in geom.log, written by
    kit_wave run() only after this ot-run exited, so the classifier read an empty stdout log ('rc 1 after N s, no log').
    -> True once X.log is non-empty and not older than the job end, False after wait_s (OT_STATUS_STDOUT_WAIT_S, default 45 s)"""
    so = stdout_log_of(rec.get("log"))
    if not so:
        return False
    if wait_s is None:
        try:
            wait_s = float(os.environ.get("OT_STATUS_STDOUT_WAIT_S", STDOUT_WAIT_S))
        except ValueError:
            wait_s = STDOUT_WAIT_S
    t_end = float(rec.get("t_end") or 0)
    deadline = now() + wait_s
    while True:
        try:
            st = os.stat(so)
            if st.st_size > 0 and st.st_mtime >= t_end - 1:
                return True
        except OSError:
            pass
        if now() >= deadline:
            return False
        sleep(1.0)


def deferred_post_argv(rec):
    """the detached argv that waits for the stdout log, then posts (a DIED with an X.live.log), else None"""
    if rec.get("rc") == 0 or not stdout_log_of(rec.get("log")) or os.environ.get("OT_STATUS_DEFER", "1") == "0":
        return None
    return [sys.executable, "-I", os.path.abspath(__file__), "deferred-post", json.dumps(rec)]


def post(rec):
    """detached post.sh call; returns the argv used (tests) or None.  A DIED whose verdict lands in X.log after this process exits is
    posted by a detached deferred-post child that waits for that log first (D1)."""
    if not should_post(rec):
        return None
    dargv = deferred_post_argv(rec)
    if dargv:
        try:
            subprocess.Popen(dargv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            return dargv
        except OSError:
            pass                                   # post now, unclassified rather than never
    post_sh = os.environ.get("OT_POST_SH") or os.path.expanduser("~/coord/bin/post.sh")
    text = post_text(rec)
    if os.path.exists(post_sh):
        argv = ["bash", post_sh, rec["lane"], text]
    else:
        hub = os.environ.get("OT_STATUS_HUB", "intel2")
        import shlex
        argv = ["timeout", "120", "ssh", "-o", "ControlPath=none", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", hub,
                "bash ~/coord/bin/post.sh " + shlex.quote(rec["lane"]) + " " + shlex.quote(text)]
    try:
        subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError:
        return None
    return argv


def finish(rec, rc):
    if rec is None:
        return
    if rc is None:
        rc = 0
    elif not isinstance(rc, int):
        rc = 1                                  # sys.exit("message") is status 1
    update(rec, state="done", rc=rc, t_end=int(time.time()))
    post(rec)


def run_recorded(kind, fn, cmd="", lane=None):
    """fn() with a status record around it; fn's SystemExit / return value is the status, passed on unchanged"""
    rec = begin(kind, cmd, lane)
    global CURRENT
    CURRENT = rec
    try:
        r = fn()
    except SystemExit as e:
        finish(rec, e.code)
        raise
    except BaseException:
        finish(rec, 1)
        raise
    finish(rec, r if isinstance(r, int) else 0)
    return r


CURRENT = None


def set_refusal(reason):
    """Retain a queue-time refusal even when stdout and stderr have no logfile."""
    if CURRENT is not None:
        CURRENT["refusal"] = str(reason)


def set_unit(unit):
    """ot-run calls this when ot-heavy admitted the job (the oth-... scope)"""
    update(CURRENT, unit=unit)


def _deferred_post(rec_json):
    rec = json.loads(rec_json)
    wait_stdout_log(rec)
    os.environ["OT_STATUS_DEFER"] = "0"
    post(rec)
    return 0


if __name__ == "__main__" and sys.argv[1:2] == ["deferred-post"] and len(sys.argv) == 3:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.exit(_deferred_post(sys.argv[2]))
