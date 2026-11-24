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
  NOT-RUN      ot-run refused before running for a named reason that is not ssh (disk-ETA hold, isolation, ...) -- FABLE-FLOW-0230 D1: was SSH-DROP by rc 78
  BIND-FAIL    a die/core bind stopped on an EMIT / compare error (EMIT ..., compare FAIL)
  ROUTE-FAIL   the kit's own make flow stopped at a stage (FAIL_route / make: *** [...] Error N)
  VERDICT-FAIL a checker wrote "verdict": "FAIL" (json) and exited nonzero
  NO-PATTERN   nothing matched; the cause is the last non-ot-run log line (was UNCLASSIFIED; every DIED post carries class=)
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


# ot-run prints these when choosing hosts. Neither line says the job was refused
# or stopped: an existing job may run, and a new job may choose another host.
_DRAIN_ADVISORY = re.compile(
    r"^ot-run: DRAIN:[^\n]*(?:the job may run there|not used for this job \(new job dir\))\s*$",
    re.MULTILINE,
)


# EVENT-ENV-PREFLIGHT 11-24: ot-run's informational lines.  "ot-run: rt pinned for this unit: OT_TOOLSTALE_RT=... (current; TOOLSTALE reference ...)"
# was the cause of 9 DIED posts 02:00-04:52 read as TOOLSTALE pin refusals (class NO-PATTERN).  It is printed for every started unit, and
# those units wrote their real output to their own files.  The preflight WARN and EVENT lines are report-only too.
_INFO_LINES = re.compile(r"^ot-run: (rt pinned for this unit: |PREFLIGHT WARN: |EVENT \S+ env )[^\n]*$", re.MULTILINE)


def _last_line(tail, pat=None):
    for ln in reversed([x.strip() for x in tail.splitlines() if x.strip() and not BOILER.match(x.strip())]):
        if pat is None or re.search(pat, ln, re.I):
            return re.sub(r"\s+", " ", ln)[:110]
    return ""


def _c(cls, cause):
    return cls, (cause or "no cause line").replace("\n", " ")[:120]


def classify(rc, cmd="", log_tail="", secs=0):
    t = _INFO_LINES.sub("", _DRAIN_ADVISORY.sub("", log_tail or ""))
    cmd = cmd or ""
    preflight = _last_line(t, r"^NOT-RUN PREFLIGHT\b")
    if rc and preflight:
        return _c("NOT-RUN", preflight)
    if rc != 0 and re.search(r"AUTO-GEOM FAIL\b", t):
        return _c("GEOM-FAIL", _last_line(t, r"AUTO-GEOM FAIL"))
    if re.search(r"NOT-RUN no host qualifies \((?!.*resolve)[^)]*\b(mem|admi)|exceeds physical RAM|memory admission (refus|wait)", t):
        return _c("ADMIT", _last_line(t, r"NOT-RUN|exceeds physical RAM|memory admission") or "memory admission refused the request")
    if re.search(r"DRAIN(ING)?:|NOT-RUN no host qualifies \((?!.*resolve)[^)]*(scratch|disk|free)|scratch disk", t):
        return _c("RAIL-KILL", _last_line(t, r"DRAIN|NOT-RUN|scratch disk") or "host rail refused the job")
    # FABLE-FLOW-0230 D1: an ot-run NOT-RUN / REFUSED with a reason that is not ssh is that reason, not SSH-DROP (3 disk-ETA holds were labelled SSH-DROP)
    m = re.search(r"^(?:ot-run: )?(?:NOT[- ]RUN|REFUSED)\b[^\n]*", t.lstrip(), re.M)
    if m and not re.search(r"resolve hostname|Connection (reset|closed|timed out|refused)|SSH probe|ssh|unreachable", m.group(0), re.I):
        return _c("NOT-RUN", re.sub(r"\s+", " ", m.group(0))[:110])
    if re.search(r"^\s*(EMIT\b|EMIT_ERROR|BIND_RC=[1-9])|compare FAIL|mismatched\b", t, re.M):
        return _c("BIND-FAIL", _last_line(t, r"EMIT|compare FAIL|mismatch|BIND_RC"))
    if rc in (78, 255, 141) or re.search(r"Could not resolve hostname|Connection (reset|closed|timed out|refused)|Broken pipe|SSH probe exit|client gone", t):
        return _c("SSH-DROP", _last_line(t, r"resolve hostname|Connection|Broken pipe|SSH probe|NOT-RUN|client gone") or "ssh/host unreachable (rc %s)" % rc)
    # The DRT watchdog logs its decision before killing the OpenROAD process.
    # A shell "Killed" after this exact terminal marker is the stop mechanism.
    drt_stop = _last_line(t, r"^OT_DRT_NO_PROGRESS stage=\S+ class=DRT_NO_PROGRESS: .*stopping the stage \(FAILFAST-1\)")
    if rc and drt_stop:
        return _c("ROUTE-FAIL", drt_stop)
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
    if re.search(r"(^|/)FAIL_route\b|make(\[\d+\])?: \*\*\* \[[^\]]*(route|grt|5_)[^\]]*\] Error \d+", t, re.M):
        return _c("ROUTE-FAIL", _last_line(t, r"FAIL_route|\*\*\*|DPL-|GRT-|DRT-|ERROR"))
    if re.search(r'"verdict"\s*:\s*"FAIL', t):
        return _c("VERDICT-FAIL", _last_line(t, r"verdict|FAIL|reason"))
    if re.search(r"Traceback \(most recent call last\)|\[ERROR [A-Z]+-\d+\]|^Error:|\b\w+Error: ", t, re.M):
        return _c("TOOL-TRACEBACK", _last_line(t, r"\w+Error:|\[ERROR|^Error:|Exception"))
    if re.search(r"FAIL_\w+|G0 errors|BIND_RC=[1-9]|setup .*-\d|WNS|hold|overflow|DRC|LEC.*(fail|differ|not equivalent)|violat|hop_um|STRUCT|\bFAIL\b", t, re.I):
        return _c("DESIGN-FAIL", _last_line(t, r"FAIL_\w+|errors|BIND_RC|WNS|hold|overflow|DRC|LEC|violat|hop_um|STRUCT"))
    if re.search(r"\b[A-Z0-9_]+_DONE\b|VERDICT|\bPASS\b", t):
        return _c("CHECKER-RC", _last_line(t, r"_DONE|VERDICT|PASS") + " (finished, exit rc %s: findings or verdict)" % rc)
    if not t.strip() and rc in (1, 2) and secs <= 10:
        return _c("SETUP", "died after %s s with no log: the command failed at start (rc %s)" % (secs, rc))
    if not _last_line(t) and t.strip():
        return _c("NO-PATTERN", "rc %s after %s s; the log holds only ot-run lines (the command wrote its output to its own files)" % (rc, secs))
    return _c("NO-PATTERN", _last_line(t) or ("rc %s after %s s, no log" % (rc, secs)))


def label(rc, cmd="", log=None, secs=0, refusal=None):
    """' | class=X cause=...' suffix for a DIED post; never raises"""
    try:
        tail = f"NOT-RUN {refusal}" if refusal else read_tails(log)
        cls, cause = classify(rc, cmd, tail, secs)
        return " | class=%s cause=%s" % (cls, cause)
    except Exception as e:      # a classifier bug must not lose the DIED post
        return " | class=NO-PATTERN cause=classifier error %s" % type(e).__name__
