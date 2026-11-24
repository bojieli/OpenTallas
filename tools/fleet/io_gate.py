#!/usr/bin/env python3
"""io_gate (E11-IO-STALL-1124, COORD hub 48a3b0f1): one per-host IO-pressure rule for bulk-read jobs.

epyc11's single consumer NVMe sat at 100 % util, 220 ms read latency and 20-30 MB/s under a random small-file read storm: 12 parallel tar fork
pipelines, a 4-job ot-tree-fork, src_manifest builds and whole-scratch find/grep/du/lane_quota scans.  It stalled copies, sshd and rt sync.
A host is IO-GATED while /proc/pressure/io "some avg60" > IO_GATE_SOME (default 20; 0 disables).  While it is gated:
  * ot-heavy holds (queues, never fails) a NEW fork / copy / seal job (is_bulk below, or OT_HEAVY_IO=bulk) for at most IO_GATE_MAX_WAIT_S
    (default 3600 s, then it is admitted anyway, so a job never starves); running jobs and children of an admitted unit are never held;
  * lane_quota.py scan does not scan that host (it reports nothing for it this pass).
CLI:  io_gate.py --gated            prints 'GATED <avg60> <threshold>' / 'OK <avg60> <threshold>'; exit 0 when gated, 1 otherwise
      io_gate.py --is-bulk -- ARGV  exit 0 when ARGV is a bulk fork / copy / seal command, else 1.  Stdlib only."""
import os
import re
import shlex
import sys

PSI = os.environ.get("OT_IO_PSI", "/proc/pressure/io")
WRAPPERS = {"env", "nice", "ionice", "timeout", "exec", "sudo", "python3", "python", "bash", "sh", "nohup", "time", "stdbuf", "command"}
BULK_PROGS = {"ot-tree-fork", "rsync", "tar", "fork_bound.sh", "ot-tree-copy"}
SRC_MANIFEST_BULK = {"replicate", "materialize", "seal", "build", "publish"}
SEG = re.compile(r"[\n;|&()]+")


def threshold():
    try:
        return float(os.environ.get("IO_GATE_SOME", "20"))
    except ValueError:
        return 20.0


def some_avg60(path=None):
    """-> float or None (no PSI on this kernel)"""
    try:
        for ln in open(path or PSI):
            if ln.startswith("some"):
                for kv in ln.split()[1:]:
                    k, _, v = kv.partition("=")
                    if k == "avg60":
                        return float(v)
    except (OSError, ValueError):
        return None
    return None


def gated(path=None, limit=None):
    """-> (gated, avg60, threshold).  threshold 0 or no PSI -> never gated"""
    limit = threshold() if limit is None else limit
    v = some_avg60(path)
    return (bool(limit) and v is not None and v > limit), v, limit


def _words(seg):
    try:
        return shlex.split(seg, comments=False)
    except ValueError:
        return seg.split()


def _prog(words):
    """-> (program basename, the words after it) skipping assignments, wrappers, their options and numbers"""
    for i, w in enumerate(words):
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", w) or w.startswith("-") or re.fullmatch(r"[0-9.]+[smhd]?", w):
            continue
        b = os.path.basename(w)
        if b in WRAPPERS or re.fullmatch(r"python3(\.\d+)?", b):
            continue
        return b, words[i + 1:]
    return "", []


def is_bulk(argv):
    """a fork / copy / seal command: ot-tree-fork, rsync, tar, cp -a/-r, fork_bound.sh, seal_tree*, src_manifest.py replicate|materialize|seal|build|publish.
    Each simple command of the argv (and of any script text inside it) is checked by its program name, so text that only mentions a name
    (a heredoc, a comment, a Python string) does not count."""
    text = []
    for a in argv:
        text.append(("\n" + a + "\n") if re.search(r"\s", a) else a)
    for seg in SEG.split(" ".join(text)):
        prog, rest = _prog(_words(seg.strip()))
        if not prog:
            continue
        if prog in BULK_PROGS or prog.startswith("seal_tree"):
            return True
        if prog == "cp" and any(re.fullmatch(r"-[a-zA-Z]*[arR][a-zA-Z]*", w) for w in rest):
            return True
        if prog == "src_manifest.py" and rest[:1] and rest[0] in SRC_MANIFEST_BULK:
            return True
    return False


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["--gated"]:
        g, v, lim = gated()
        print(f"{'GATED' if g else 'OK'} {'-' if v is None else v} {lim:g}")
        return 0 if g else 1
    if argv[:1] == ["--is-bulk"]:
        rest = argv[2:] if argv[1:2] == ["--"] else argv[1:]
        return 0 if is_bulk(rest) else 1
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
