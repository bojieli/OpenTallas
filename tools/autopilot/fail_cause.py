"""ROUTEFAIL-CAUSE 11-23: the cause part of a FAILED post: class, first error line, log path.

Text only. It never changes a verdict, a kind, a retry or a cancel. Of 745 crash posts 11-17..23, 239 read
'make exit 2 (see run_route.log)' and 82 broke the one-line post with a raw log tail, and the class they carried was often wrong
(51 of 51 infra-orphan posts were the autopilot's own cancels, 19 of 22 infra-oom posts were PLACE-SETUP-STOP).
"""
import os
import re

# first match wins, on one line of text
CLASSES = (
    ("disk-full", r"No space left on device|ENOSPC|disk quota exceeded"),
    ("not-run", r"^NOT-RUN |^ot-(?:job|run): NOT RUN\b"),
    ("place-setup", r"PLACE-SETUP-STOP"),
    ("no-progress", r"NO_PROGRESS|NOCONVERGE"),
    ("grt-congestion", r"GRT-0116|GRT-0118|GRT-0183|GRT-0228|GRT-0273|OT_GRT_CONGESTED_FAIL"),
    ("pin-access", r"DRT-0073|No access point"),
    ("drt", r"\[ERROR DRT-\d+|\bDRT-0255\b"),
    ("legalize", r"\[ERROR DPL-\d+|\bDPL-00\d\d\b"),
    ("buffer-cap", r"RSZ-0060"),
    ("mem-kill", r"\] Error 247\b|\brc[ =]+137\b|make exit 137|signal 9\b|SIGKILL|\bKilled\b|bad_alloc|[Oo]ut of memory|OOMKilled|EARLYOOM|earlyoom"),
    ("stopped", r"\] Error 241\b|stopped by signal 15|signal 15:|SystemExit: 143|make exit 143"),
    ("gate", r"^FAIL_(?:POSTCTS|PREFLOOR)\b|^[A-Z][A-Z0-9_]+ FAIL\b|: FAIL\b"),
    ("flow-script", r"\.tcl, \d+|can't read \"|invalid command name \"|\w+Error: |bwrap: |No such file or directory|not in the store"),
    ("tool-crash", r"Segmentation fault|Signal 11|SIGSEGV|core dumped|\[ERROR [A-Z]+-\d+\]"),
)
ERR_LINE = re.compile(r"\[ERROR [A-Z]+-\d+\]|^Error: |can't read \"|invalid command name \"|Segmentation fault|Signal 11 received|"
                      r"No space left on device|^NOT-RUN |\] Error (?:137|241|247)\b|EARLYOOM|yosys signal 9|PLACE-SETUP-STOP|OT_\w*(?:NO_PROGRESS|NOCONVERGE)|"
                      r"^(?:\w+\.)*\w+Error: |^bwrap: |^ot-job: (?:signal 15|NOT RUN|PUBLISH FAILED)|SystemExit: 143|^FAIL_(?:POSTCTS|PREFLOOR|POSTPLACE) |: FAIL\b")
NOISE = re.compile(r"LEC_|SIGNOFF_TOOL|KIT_FLOW_REFRESH|print\(|KIT_PREFLIGHT (?:PASS|ADVISORY)")
CAUSELESS = re.compile(r"\(see run_\w+\.log\)|^exit \d+$|^\s*$|stopped from outside|^client lost")
HUB_ACT = re.compile(r"AUTOPILOT: (KIT-WAVE GRT-ARM CANCEL|KIT-WAVE REAP(?!-)|WITHDRAW-REQUESTED|NOPROG-REJUDGE|CANCEL\S*) ")


def one_line(s, n=300):
    """a post is one line of the hub file: newlines and runs of blanks become one space"""
    return re.sub(r"\s+", " ", str(s or "")).strip()[:n]


def classify_line(s):
    for name, rx in CLASSES:
        if re.search(rx, s or "", re.M):
            return name
    return "unclassified"


def client_error(text):
    """first error line of this attempt in the client log; '' when the log names none"""
    i = text.rfind("AP_START ")
    tail = text[i:] if i >= 0 else text
    hits = [l.strip() for l in tail.splitlines() if ERR_LINE.search(l[:500]) and not NOISE.search(l[:200])]
    if "ot-run: RAN on " in tail:                          # a refused host before the one that ran the job is no cause
        hits = [l for l in hits if not l.startswith("NOT-RUN ")]
    if not hits:
        mk = re.findall(r"(?m)^make\[1\]: \*\*\* [^\n]*", tail)
        return mk[-1] if mk else ""
    # ENOSPC, a refused start, a kill or a signal explains the Python / tool errors around it
    for pri in ("disk-full", "not-run", "place-setup", "stopped"):
        for l in hits:
            if classify_line(l) == pri:
                return l
    return hits[0]


def tail_of(path, n):
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - n))
            return f.read().decode(errors="replace")
    except OSError:
        return ""


def stop_sender(j, hub_log, signals):
    """the hub line that stopped this job: an autopilot action on its id / unit, else the ot-run --cancel sender; '' when none is logged"""
    keys = [k for k in (j.get("id"), j.get("unit")) if k]
    for l in reversed(hub_log.splitlines()):
        if HUB_ACT.search(l) and any(k in l for k in keys):
            return l
    path, rununit = j.get("path"), j.get("run_unit")
    for l in reversed(signals.splitlines()):
        if (path and re.search(re.escape(path) + r"(?=[\s;:)]|$)", l)) or (rununit and rununit in l):
            return l
    return ""


def cause(j, client_text="", hub_log="", signals=""):
    """-> (class, line, log path) of the failed job; line '' when nothing names a cause"""
    kind = j.get("kind", "")
    log = j.get("client_log") or ""
    m = re.findall(r"logs/ and reports/ of the failed stage kept in (\S+)", client_text)
    kept = f"{j.get('ran_on') or j.get('host')}:{m[-1]}" if m else ""
    if kind in ("infra-orphan", "infra-stopped"):
        s = stop_sender(j, hub_log, signals)
        if s:
            return ("no-progress" if "NOPROG-REJUDGE" in s else "cancelled"), one_line(s, 260), kept or log
    fe = one_line(j.get("first_error"), 260)
    ce = one_line(client_error(client_text), 260)
    if kind == "infra-oom":                                # the kind is a memory verdict; a place stop in the client log overrides nothing but is named
        line = ce or fe or one_line(j.get("reasons"), 260)
    elif ce and classify_line(ce) in ("disk-full", "not-run", "stopped", "mem-kill", "place-setup"):
        line = ce                                          # the host or a sender ended the run: an earlier (caught) tool error is not the cause
    else:
        line = fe or ce
    path = log
    if line == fe and fe:
        path = j.get("first_error_log") or kept or log
    elif kept:
        path = kept
    if not line and not CAUSELESS.search(one_line(j.get("reasons"))):
        line = one_line(j.get("reasons"), 260)
    cls = classify_line(line) if line else "unclassified"
    if cls == "unclassified" and kind == "infra-stopped":
        cls = "stopped"
    return cls, line, path


def suffix(j, coord):
    """' | cause <class>: <first error> | log <path>' for failed_notice; never raises"""
    try:
        text = tail_of(j.get("client_log") or "", 400_000)
        hub = sig = ""
        if j.get("kind") in ("infra-orphan", "infra-stopped"):
            hub = tail_of(os.path.join(str(coord), "autopilot", "log.txt"), 12_000_000)
            sig = tail_of(os.path.expanduser("~/.local/state/ot-run/signals.log"), 4_000_000)
        cls, line, path = cause(j, text, hub, sig)
        return f" | cause {cls}: {line or 'no error line found'}" + (f" | log {path}" if path else "")
    except Exception as e:                                 # a post must never be lost to its own decoration
        return f" | cause unclassified: cause scan failed ({one_line(e, 80)})"
