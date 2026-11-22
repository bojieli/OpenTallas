"""ot_deathclass: failure class + one-line cause for a DIED post (FLOW-DEATHCLASS-R1, FABLE-FLOW-0000 class F10).

classify(rc, cmd, log_tail, secs) -> (CLASS, cause).  Classes, first match wins:
  SSH-DROP     ssh/host unreachable (rc 78 NOT-RUN no host, 255, 141, "Could not resolve", "Connection reset/closed")
  OOM          rc 137 / "Killed" / out of memory
  GEOM-FAIL    the kit placed and AUTO-GEOM judged it FAIL (a design verdict; checked first: geom logs also carry advisory GRT kills / tracebacks)
  ADMIT        ot-run memory admission refused it (no host admits the request now: request > admissible, memory admission) -- not a crash
  RAIL-KILL    stopped or refused by a host rail or guard (DRAIN, no host qualifies on disk, disk floor, reaper, "stopped by <tool>")
  CANCEL       rc 143/130/129 or an explicit cancel (SIGTERM; by ot-run --cancel, a watchdog, or the unit stopped)
  SETUP        the command never got going: rc 64/127/126/14/10, no such file, command not found, kit preflight, not a kit-wave attempt
  TEST-FAIL    pytest / ot-push-main gate failed
  PUSH-CONFLICT ot-push-main merge or conflict
  TOOL-TRACEBACK a Python/Tcl traceback or a tool Error line
  DESIGN-FAIL  a flow check reported a design failure (timing, route, bind, LEC, DRC, hold, structural)
  CHECKER-RC   the job ran to its end marker/verdict and exited nonzero (findings, not a crash)
  UNCLASSIFIED nothing matched; the cause is the last log line
stdlib only; pure function (tests need no host)."""
import os
import re

TAIL_BYTES = 6000


def read_tails(path, n=TAIL_BYTES):
    """the log tail; a kit_wave stage log X.live.log holds stderr only (ot-run / ot-heavy lines): its stdout X.log (the verdict) comes after it"""
    t = read_tail(path, n)
    if path and str(path).endswith(".live.log"):
        so = read_tail(str(path)[:-len(".live.log")] + ".log", n)
        if so:
            t = (t + "\n" + so) if t else so
    return t


def read_tail(path, n=TAIL_BYTES):
    if not path or path == "none":
        return ""
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - n))
            return f.read().decode("utf-8", "replace")
    except OSError:
        return ""


# FLOW-FLEET-R1 11-22: ot-run's per-host admission status line ("ot-run: epyc7   admits 231 GB (avail ..., headroom 0, ...)") is printed for every
# ADMITTED job; it was the "cause" of 9 UNCLASSIFIED geom DIED posts (00:10-01:25) whose real cause was AUTO-GEOM FAIL in the stdout log
BOILER = re.compile(r"^(ot-run: (RAN on|->|admitted|\S+\s+admits\s+\d+ GB)|ot-heavy:|rc=\d+ wall|\+ |\W*$)")


def _last_line(tail, pat=None):
    for ln in reversed([x.strip() for x in tail.splitlines() if x.strip() and not BOILER.match(x.strip())]):
        if pat is None or re.search(pat, ln, re.I):
            return re.sub(r"\s+", " ", ln)[:110]
    return ""


def _c(cls, cause):
    return cls, (cause or "no cause line").replace("\n", " ")[:120]


def classify(rc, cmd="", log_tail="", secs=0):
    t = log_tail or ""
    cmd = cmd or ""
    if rc != 0 and re.search(r"AUTO-GEOM FAIL\b", t):
        return _c("GEOM-FAIL", _last_line(t, r"AUTO-GEOM FAIL"))
    if re.search(r"NOT-RUN no host qualifies \((?!.*resolve)[^)]*\b(mem|admi)|exceeds physical RAM|memory admission (refus|wait)", t):
        return _c("ADMIT", _last_line(t, r"NOT-RUN|exceeds physical RAM|memory admission") or "memory admission refused the request")
    if re.search(r"DRAIN(ING)?:|NOT-RUN no host qualifies \((?!.*resolve)[^)]*(scratch|disk|free)|scratch disk", t):
        return _c("RAIL-KILL", _last_line(t, r"DRAIN|NOT-RUN|scratch disk") or "host rail refused the job")
    if rc in (78, 255, 141) or re.search(r"Could not resolve hostname|Connection (reset|closed|timed out|refused)|Broken pipe|SSH probe exit|client gone", t):
        return _c("SSH-DROP", _last_line(t, r"resolve hostname|Connection|Broken pipe|SSH probe|NOT-RUN|client gone") or "ssh/host unreachable (rc %s)" % rc)
    if rc == 137 or re.search(r"\bKilled\b|Out of memory|oom-kill|MemoryError|Cannot allocate memory", t):
        return _c("OOM", _last_line(t, r"Killed|memory|oom") or "SIGKILL (rc 137), memory limit")
    if re.search(r"stopped by [\w./-]+:|disk floor|DISK-RAIL|memory admission|guard kill|reaper|ot-guard|rail kill", t, re.I):
        return _c("RAIL-KILL", _last_line(t, r"stopped by|floor|admission|guard|reaper|rail"))
    if rc in (143, 130, 129) or re.search(r"\bcancel(l)?ed\b|--cancel|SIGTERM|Terminated\b", t):
        return _c("CANCEL", _last_line(t, r"cancel|SIGTERM|Terminated") or "SIGTERM (rc %s): cancelled or unit stopped" % rc)
    if re.search(r"TESTS FAILED|\bFAILED\b.*::|\d+ failed\b|AssertionError|pytest", t) and (rc in (1, 2, 4) or "pytest" in cmd or "ot-push-main" in cmd):
        return _c("TEST-FAIL", _last_line(t, r"TESTS FAILED|FAILED|\d+ failed|AssertionError"))
    if "ot-push-main" in cmd and re.search(r"merge conflict|CONFLICT|dropped from.*train", t, re.I):
        return _c("PUSH-CONFLICT", _last_line(t, r"conflict|train"))
    if rc in (64, 126, 127, 14, 10) or re.search(r"No such file or directory|command not found|not a kit-wave attempt|FAIL_PREFLOOR|kit_preflight|Permission denied|usage:", t):
        return _c("SETUP", _last_line(t, r"No such file|not found|not a kit-wave|PREFLOOR|preflight|Permission|usage:|refus") or "command could not start (rc %s)" % rc)
    if re.search(r"Traceback \(most recent call last\)|\[ERROR [A-Z]+-\d+\]|^Error:|\b\w+Error: ", t, re.M):
        return _c("TOOL-TRACEBACK", _last_line(t, r"\w+Error:|\[ERROR|^Error:|Exception"))
    if re.search(r"FAIL_\w+|G0 errors|BIND_RC=[1-9]|setup .*-\d|WNS|hold|overflow|DRC|LEC.*(fail|differ|not equivalent)|violat|hop_um|STRUCT|\bFAIL\b", t, re.I):
        return _c("DESIGN-FAIL", _last_line(t, r"FAIL_\w+|errors|BIND_RC|WNS|hold|overflow|DRC|LEC|violat|hop_um|STRUCT"))
    if re.search(r"\b[A-Z0-9_]+_DONE\b|VERDICT|\bPASS\b", t):
        return _c("CHECKER-RC", _last_line(t, r"_DONE|VERDICT|PASS") + " (finished, exit rc %s: findings or verdict)" % rc)
    if not t.strip() and rc in (1, 2) and secs <= 10:
        return _c("SETUP", "died after %s s with no log: the command failed at start (rc %s)" % (secs, rc))
    return _c("UNCLASSIFIED", _last_line(t) or ("rc %s after %s s, no log" % (rc, secs)))


def label(rc, cmd="", log=None, secs=0):
    """' | class=X cause=...' suffix for a DIED post; never raises"""
    try:
        cls, cause = classify(rc, cmd, read_tails(log), secs)
        return " | class=%s cause=%s" % (cls, cause)
    except Exception as e:      # a classifier bug must not lose the DIED post
        return " | class=UNCLASSIFIED cause=classifier error %s" % type(e).__name__
