#!/usr/bin/env python3
"""ot-orphan-reaper (ROOT-0100, 2026-10-19): kill runaway LOCAL processes left behind by dead Claude sessions.

Incident 10-19: two orphaned `git grep ... origin/main` (bash wrapper from ~/.claude/shell-snapshots, parent PID 1)
used ~25 cores + 14 GB for 2.7-4 h and an orphaned local iverilog compile ran 35 h with 12.5 GB.

A process is killed (exact PID, SIGTERM then SIGKILL, one log line each) only when ALL hold:
  (a) ORPHANED: it is a shell-snapshot wrapper's descendant (bash -c 'source ~/.claude/shell-snapshots/...') and no
      ancestor is a `claude` process (so the session that ran it is gone: ppid 1 / systemd --user, or the claude
      process exited);
  (b) it is one of
        GIT   git grep with a revision, git ls-tree, git log       elapsed > 20 min
        GREP  grep / egrep / fgrep / rg / ugrep                    elapsed > 30 min
        EDA   iverilog / ivl / vvp / verilator* / yosys* / openroad elapsed > 2 h
  (c) it, and every ancestor, is NOT protected: any `claude` process, the closure daemon (closure_loop.py), fleet-viz,
      queqiaod, ot-run, ssh/sshd, this reaper, a PID or path / job id listed in pending_results.txt.
  A GREP that reads a pipe is a filter: it is killed only when every writer of that pipe is itself a kill target or a
  leaked `tail`/`cat` in the same orphan tree (those writers are then killed too); a filter on anything else (e.g.
  `ot-run ... | grep -v x > log`) is skipped, since killing it would SIGPIPE the producer.

Usage: ot_orphan_reaper.py [--dry] [--report] [--log PATH]
  --dry     print what would be killed, kill nothing (log lines are prefixed DRY)
  --report  print local CPU (cores busy over 3 s) / RSS by category; never kills
Installed as ~/bin/ot-orphan-reaper, run by systemd --user ot-orphan-reaper.timer every 10 min.
"""
import argparse, datetime as dt, fcntl, os, re, signal, sys, time

HOME = os.path.expanduser("~")
TAKEOVER = os.path.join(HOME, "claude-takeover-20261007")
LOG = os.path.join(TAKEOVER, "ot-orphan-reaper.log")
PENDING = os.path.join(TAKEOVER, "pending_results.txt")
LOCK = os.path.join(HOME, ".cache", "ot-orphan-reaper.lock")

SNAPSHOT_MARK = "/.claude/shell-snapshots/"
SHELLS = {"bash", "sh", "zsh", "dash"}
GIT_LIMIT_S = 20 * 60
GREP_LIMIT_S = 30 * 60
EDA_LIMIT_S = 2 * 3600
GREP_NAMES = {"grep", "egrep", "fgrep", "rg", "ugrep"}
EDA_NAMES = {"iverilog", "ivl", "vvp", "verilator", "verilator_bin", "verilator_bin_dbg", "yosys", "yosys-abc",
             "openroad"}
LEAK_WRITERS = {"tail", "cat"}            # a pipe writer we may kill together with its orphaned grep filter
PROTECT_ARGV0 = {"claude", "queqiaod", "ot-run", "ssh", "sshd", "ot-orphan-reaper",
                 "ot_orphan_reaper.py", "tmux", "tmux: server"}
PROTECT_SUBSTR = ("closure_loop.py", "fleet-viz", "queqiaod", "/bin/ot-run", "ot_orphan_reaper", "ot-orphan-reaper")
CLAUDE_EXE_MARK = "/.local/share/claude/versions/"
GIT_GLOBAL_WITH_ARG = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--super-prefix",
                       "--config-env"}
REV_RE = re.compile(r"^([0-9a-f]{7,40}|HEAD([~^]\d*)*|(origin|upstream|refs)/\S+|\S+\.\.\.?\S*|\S+@\{.*\})$")


class Proc:
    __slots__ = ("pid", "ppid", "argv", "comm", "exe", "elapsed", "cpu", "rss", "start", "fd0_pipe", "pipe_w")

    def __init__(self, pid, ppid, argv, comm="", exe="", elapsed=0.0, cpu=0.0, rss=0, start=0, fd0_pipe=None,
                 pipe_w=()):
        self.pid, self.ppid, self.argv, self.comm, self.exe = pid, ppid, list(argv), comm, exe
        self.elapsed, self.cpu, self.rss, self.start = elapsed, cpu, rss, start
        self.fd0_pipe = fd0_pipe            # inode of the pipe on stdin (read side), or None
        self.pipe_w = set(pipe_w)           # inodes of pipes this process holds open for writing

    @property
    def name(self):
        return os.path.basename(self.argv[0]) if self.argv else self.comm

    @property
    def line(self):
        return " ".join(self.argv) if self.argv else "[%s]" % self.comm


# ---------------------------------------------------------------- snapshot of /proc (the only OS-dependent part)
def snapshot():
    hz = os.sysconf("SC_CLK_TCK")
    with open("/proc/uptime") as f:
        uptime = float(f.read().split()[0])
    procs = {}
    for d in os.listdir("/proc"):
        if not d.isdigit():
            continue
        pid = int(d)
        try:
            with open("/proc/%d/stat" % pid) as f:
                st = f.read()
            comm = st[st.index("(") + 1:st.rindex(")")]
            rest = st[st.rindex(")") + 2:].split()
            ppid, utime, stime, start = int(rest[1]), int(rest[11]), int(rest[12]), int(rest[19])
            rss = int(rest[21]) * os.sysconf("SC_PAGE_SIZE")
            with open("/proc/%d/cmdline" % pid, "rb") as f:
                argv = [a.decode("utf-8", "replace") for a in f.read().split(b"\0") if a]
        except (OSError, ValueError, IndexError):
            continue
        try:
            exe = os.readlink("/proc/%d/exe" % pid)
        except OSError:
            exe = ""
        fd0, wr = None, set()
        try:
            for fd in os.listdir("/proc/%d/fd" % pid):
                try:
                    tgt = os.readlink("/proc/%d/fd/%s" % (pid, fd))
                except OSError:
                    continue
                if not tgt.startswith("pipe:["):
                    continue
                ino = int(tgt[6:-1])
                mode = None
                try:
                    with open("/proc/%d/fdinfo/%s" % (pid, fd)) as f:
                        for ln in f:
                            if ln.startswith("flags:"):
                                mode = int(ln.split()[1], 8) & 3
                except OSError:
                    pass
                if fd == "0":
                    fd0 = ino
                elif mode in (1, 2):
                    wr.add(ino)
        except OSError:
            pass
        procs[pid] = Proc(pid, ppid, argv, comm, exe, max(0.0, uptime - start / hz), (utime + stime) / hz, rss,
                          start, fd0, wr)
    return procs


# ---------------------------------------------------------------- pending_results protection
def load_pending(path=PENDING):
    pids, toks = set(), set()
    try:
        text = open(path, errors="replace").read()
    except OSError:
        return pids, toks
    for raw in re.split(r"[\s|,;()\"'`]+", text):
        t = raw.strip(".:")
        if t.isdigit() and len(t) >= 3:
            pids.add(int(t))
            continue
        if ":" in t and "/" in t.split(":", 1)[1]:          # host:/path -> /path
            t = t.split(":", 1)[1]
        t = re.split(r"[*<>{}\[\]]", t)[0].rstrip("/._-")
        if t.startswith("~/"):
            t = HOME + t[1:]
        if t.startswith("/") and t.count("/") >= 4 and len(t) >= 20:
            toks.add(t)
            d = os.path.dirname(t)
            if d.count("/") >= 4:                               # a result file's run directory
                toks.add(d)
        elif re.match(r"^[A-Za-z0-9_.]+-[A-Za-z0-9_.-]{8,}$", t) and re.search(r"[0-9a-f]{7,}", t):
            toks.add(t)                                          # closure-loop job id (name-...-<sha>)
    for m in re.finditer(r"\bpid[ =:#]*(\d+)", text, re.I):
        pids.add(int(m.group(1)))
    return pids, toks


# ---------------------------------------------------------------- classification
def is_claude(p):
    if p.name in GREP_NAMES:                       # Claude's embedded ugrep runs the claude binary as argv0 'ugrep'
        return False
    return p.name == "claude" or CLAUDE_EXE_MARK in (p.exe or "") or p.comm == "claude"


def is_wrapper(p):
    return p.name in SHELLS and any(SNAPSHOT_MARK in a for a in p.argv)


def protected_reason(p, pending):
    pids, toks = pending
    if is_claude(p):
        return "claude"
    if p.name in PROTECT_ARGV0 or (len(p.argv) > 1 and os.path.basename(p.argv[1]) in PROTECT_ARGV0
                                   and p.name.startswith(("python", "perl", "bash", "sh"))):
        return "protected:" + p.name
    if not is_wrapper(p):                           # a wrapper's argv quotes the whole agent command; judge its children
        ln = p.line
        for s in PROTECT_SUBSTR:
            if s in ln:
                return "protected:" + s
    if p.pid in pids:
        return "pending_results pid"
    ln = p.line
    for t in toks:
        if t in ln:
            return "pending_results " + t[:60]
    return None


def ancestors(procs, p):
    seen, out, cur = set(), [], procs.get(p.ppid)
    while cur is not None and cur.pid not in seen:
        out.append(cur)
        seen.add(cur.pid)
        if cur.pid <= 1:
            break
        cur = procs.get(cur.ppid)
    return out


def git_class(argv):
    """'grep-rev' / 'ls-tree' / 'log' when this git argv walks a revision, else None."""
    i = 1
    while i < len(argv):
        a = argv[i]
        if a in GIT_GLOBAL_WITH_ARG:
            i += 2
            continue
        if a.startswith("-"):
            i += 1
            continue
        break
    if i >= len(argv):
        return None
    sub, rest = argv[i], argv[i + 1:]
    if sub in ("ls-tree", "log"):
        return sub
    if sub != "grep":
        return None
    args = rest[:rest.index("--")] if "--" in rest else rest
    if "--all" in args or "--cached" in args:
        return "grep-rev" if "--all" in args else None
    # skip options and their values (-e PAT, -f FILE, --max-depth N ...); the first positional is the pattern unless
    # -e/-f supplied it; every positional after it that looks like a revision makes this a revision grep
    pos, have_pat, j = [], False, 0
    takes = {"-e", "-f", "--max-depth", "-A", "-B", "-C", "--threads", "-m", "--max-count", "-O", "--open-files-in-pager"}
    while j < len(args):
        a = args[j]
        if a in ("-e", "-f"):
            have_pat = True
        if a in takes:
            j += 2
            continue
        if a.startswith("-"):
            j += 1
            continue
        pos.append(a)
        j += 1
    revs = pos if have_pat else pos[1:]
    return "grep-rev" if any(REV_RE.match(r) for r in revs) else None


def kill_class(p):
    """(class, limit_s, detail) when p's command is reapable by kind, else None."""
    n = p.name
    if n == "git":
        g = git_class(p.argv)
        return ("GIT", GIT_LIMIT_S, "git " + g) if g else None
    if n in GREP_NAMES:
        return ("GREP", GREP_LIMIT_S, n)
    if n in EDA_NAMES or n.startswith(("verilator_bin", "yosys")):
        return ("EDA", EDA_LIMIT_S, n)
    return None


def plan(procs, pending):
    """Return (kills, skips): kills = [(proc, reason)], skips = [(proc, reason)] for kind+age matches left alone."""
    kills, skips, kill_pids = [], [], set()
    cand = {}
    for p in procs.values():
        kc = kill_class(p)
        if not kc or p.elapsed <= kc[1]:
            continue
        anc = ancestors(procs, p)
        why = protected_reason(p, pending)
        if why:
            skips.append((p, why)); continue
        if any(is_claude(a) for a in anc):
            skips.append((p, "live claude session")); continue
        wrap = next((a for a in anc if is_wrapper(a)), None)
        if wrap is None:
            skips.append((p, "not under a shell-snapshot wrapper")); continue
        prot = next(((a, protected_reason(a, pending)) for a in anc if protected_reason(a, pending)), None)
        if prot:
            skips.append((p, "ancestor %d %s" % (prot[0].pid, prot[1]))); continue
        cand[p.pid] = (p, "%s %s elapsed %.1f h orphan wrapper %d" % (kc[0], kc[2], p.elapsed / 3600, wrap.pid), wrap)
    writers = {}
    for q in procs.values():
        for ino in q.pipe_w:
            writers.setdefault(ino, []).append(q)
    for pid, (p, reason, wrap) in sorted(cand.items()):
        if p.name in GREP_NAMES and p.fd0_pipe is not None:
            ws = [w for w in writers.get(p.fd0_pipe, []) if w.pid != p.pid]
            bad = [w for w in ws if w.pid not in cand and not (w.name in LEAK_WRITERS and wrap in ancestors(procs, w)
                                                               and not protected_reason(w, pending))]
            if bad:
                skips.append((p, "pipe filter fed by %d %s" % (bad[0].pid, bad[0].name))); continue
            kills.append((p, reason + " (pipe filter)")); kill_pids.add(p.pid)
            for w in ws:
                if w.pid not in cand and w.pid not in kill_pids:
                    kills.append((w, "leaked %s feeding reaped filter %d" % (w.name, p.pid))); kill_pids.add(w.pid)
            continue
        kills.append((p, reason)); kill_pids.add(p.pid)
    return kills, skips


# ---------------------------------------------------------------- act
def log(fh, msg):
    line = "%s %s" % (dt.datetime.now().astimezone().isoformat(timespec="seconds"), msg)
    print(line)
    if fh:
        fh.write(line + "\n"); fh.flush()


def same_proc(pid, start):
    try:
        with open("/proc/%d/stat" % pid) as f:
            st = f.read()
        return int(st[st.rindex(")") + 2:].split()[19]) == start
    except (OSError, ValueError, IndexError):
        return False


def do_kill(p, fh, dry):
    desc = "pid %d %s cpu %.0fs rss %.1fG | %s" % (p.pid, p.name, p.cpu, p.rss / 2**30, p.line[:300])
    if dry:
        return desc
    if not same_proc(p.pid, p.start):
        return "GONE " + desc
    try:
        os.kill(p.pid, signal.SIGTERM)
    except ProcessLookupError:
        return "GONE " + desc
    for _ in range(20):
        time.sleep(0.5)
        if not same_proc(p.pid, p.start):
            return "TERM " + desc
    if same_proc(p.pid, p.start):
        try:
            os.kill(p.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    return "KILL " + desc


# ---------------------------------------------------------------- report
def category(p, procs):
    ln, n = p.line, p.name
    if is_claude(p):
        return "claude sessions"
    if "closure_loop.py" in ln:
        return "closure daemon"
    if "fleet-viz" in ln:
        return "fleet-viz"
    if n in ("ssh", "sshd") or "ot-run" in ln:
        return "ot-run/ssh (fleet clients)"
    if n == "git":
        return "git"
    if n in GREP_NAMES:
        return "grep/rg/ugrep"
    if n in EDA_NAMES or n.startswith(("verilator", "yosys")):
        return "EDA (local!)"
    if "pre_route_gate.py" in ln or "submit_exact.py" in ln:
        return "gate/submit clients"
    if n.startswith("python"):
        return "python tools (agents)"
    return "other"


def report(procs, interval=3.0):
    a = {p.pid: p.cpu for p in procs.values()}
    time.sleep(interval)
    now = snapshot()
    cat = {}
    for p in now.values():
        c = category(p, now)
        d = cat.setdefault(c, [0.0, 0, 0, []])
        busy = max(0.0, p.cpu - a[p.pid]) / interval if p.pid in a else 0.0
        d[0] += busy; d[1] += p.rss; d[2] += 1
        d[3].append((busy, p))
    print("%-28s %7s %8s %6s  top process" % ("category", "cores", "RSS_GB", "procs"))
    for c, (busy, rss, cnt, lst) in sorted(cat.items(), key=lambda kv: -kv[1][0]):
        top = max(lst, key=lambda t: t[0])[1]
        print("%-28s %7.1f %8.1f %6d  %d %s" % (c, busy, rss / 2**30, cnt, top.pid, top.line[:90]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--log", default=LOG)
    ap.add_argument("--pending", default=PENDING)
    ap.add_argument("--show-skips", action="store_true", help="also log kind+age matches that were left alone")
    a = ap.parse_args()
    procs = snapshot()
    if a.report:
        report(procs)
        return 0
    os.makedirs(os.path.dirname(LOCK), exist_ok=True)
    lk = open(LOCK, "w")
    try:
        fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("another ot-orphan-reaper holds the lock"); return 0
    kills, skips = plan(procs, load_pending(a.pending))
    fh = open(a.log, "a") if a.log else None
    tag = "DRY " if a.dry else ""
    for p, why in kills:
        log(fh, "%sREAP %s | %s" % (tag, why, do_kill(p, fh, a.dry)))
    if a.show_skips or a.dry:
        for p, why in skips:
            log(fh, "%sSKIP %s | pid %d %s elapsed %.1f h | %s" % (tag, why, p.pid, p.name, p.elapsed / 3600,
                                                                  p.line[:200]))
    if a.dry and not kills:
        log(fh, "DRY no targets (%d processes scanned, %d kind+age matches skipped)" % (len(procs), len(skips)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
