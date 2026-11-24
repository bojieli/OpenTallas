"""ot_copy_class.py: the ot-run COPY CLASS (COORD 11-24): one cross-host tree copy as an ordinary admitted, slotted, leased ot-run job.

  ot-run --mem 8 --threads 4 --disk GB --hosts DSTHOST --dir LANEDIR --stage SRCHOST:SRC -- python3 -I RT/tools/fleet/ot-tree-fork SRC DST --src-host SRCHOST
  ot-run --mem 8 --threads 4 --disk GB --hosts SRCHOST --dir LANEDIR --stage SRCHOST:TREE -- python3 -I RT/tools/autopilot/src_manifest.py replicate TREE --hosts DSTHOST [--tar]

RT = /srv/opentallas-scratch[23]/claude/rt/{current,<sha12>}.  A --stage HOST:PATH is accepted for this class only: one tool, one source, one host
each end.  SRC is checked on SRCHOST, the destination (inside --dir by realpath, --dir inside the caller's own lane dir, never kw45 / an event tree,
not existing yet) on its host; a host that does not answer is a refusal.  The leases on SRC, the destination and --dir must be live before the job
queues.  The job is a hard pin: never spilled, widened, prioritised or run --direct.  The copy slot is taken by the tool itself.
Every other job: nothing here applies, the ISOLATION step 3 guard and the --stage rules are unchanged."""
import os, re, shlex, socket, subprocess

HOST_STAGE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9.-]*):(/.*)$")
RT_TOOL = re.compile(r"/srv/opentallas-scratch[23]?/claude/rt/(?:current|[0-9a-f]{12})/tools/(fleet/ot-tree-fork|autopilot/src_manifest\.py)")
LANE = re.compile(r"/srv/opentallas-scratch[0-9]*/claude/([^/]+)(?:/.+)?")
SHARED = {"kw45", "rt", "ot-jobs", "autopilot", "auto-resign"}      # shared containers: never a copy destination
HEAD_VALUE = {"--mem", "--dir", "--disk", "--hosts", "--threads", "--stage", "--max-wait"}
HEAD_FLAG = {"--strict-host", "--no-spill"}
STREAMS = re.compile(r"OT_TREE_FORK_STREAMS=([1-9][0-9]?)")
NO_ENV = ("OT_RUN_NO_LEASE", "OT_RUN_DIRECT", "OT_RUN_CRIT", "OT_RUN_PRIO_ENV", "OT_RUN_PLAN_JOB", "OT_RUN_INCLUDE_HELD")


class Refused(Exception):
    pass


def head_of(argv):
    return argv[:argv.index("--")] if "--" in argv else list(argv)


def wanted(argv):
    """True when the request names a --stage HOST:PATH: it is a copy-class job or it is refused"""
    h = head_of(argv)
    vals = [h[i + 1] for i, x in enumerate(h[:-1]) if x == "--stage"] + [x[8:] for x in h if x.startswith("--stage=")]
    return any(HOST_STAGE.match(p) for v in vals for p in v.split(","))


def plain(p, what):
    if not re.fullmatch(r"/[A-Za-z0-9_.+@%=,:/-]+", p) or os.path.normpath(p) != p:
        raise Refused(f"{what} {p!r}: an absolute normalised path, no ~ .. glob or variable")
    return p


def inside(p, root):
    return p == root or p.startswith(root.rstrip("/") + "/")


def lane_dir_ok(d, lane):
    m = LANE.fullmatch(d)
    if not m or m.group(1) in SHARED:
        return False
    a, b = m.group(1).lower(), lane.lower()
    return a == b or a.startswith((b + "-", b + "_"))


def parse(argv, env=None):
    """-> the job {tool, rt_tool, src, src_host, dst, dst_host, run_host, dir}; Refused otherwise (pure: no host is asked)"""
    env = os.environ if env is None else env
    if "--" not in argv:
        raise Refused("no command")
    head, cmd, o = head_of(argv), list(argv[argv.index("--") + 1:]), {}
    i = 0
    while i < len(head):
        k = head[i]
        if k in HEAD_FLAG:
            i += 1
            continue
        if k not in HEAD_VALUE or i + 1 >= len(head):
            raise Refused(f"option {k}: a copy job takes only {' '.join(sorted(HEAD_VALUE | HEAD_FLAG))}")
        if k in o:
            raise Refused(f"{k} given twice")
        o[k] = head[i + 1]
        i += 2
    for k in ("--mem", "--dir", "--hosts", "--stage"):
        if not o.get(k):
            raise Refused(f"{k} is required")
    bad = [k for k in NO_ENV if env.get(k)]
    if bad:
        raise Refused(f"{', '.join(bad)} set: a copy job is admitted, queued and leased like any other")
    lane = env.get("OT_LANE") or ""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", lane):
        raise Refused("OT_LANE is not set (the lease owner, and the lane whose --dir this is)")
    m = HOST_STAGE.match(o["--stage"])
    if not m or "," in o["--stage"]:
        raise Refused("exactly one --stage SRCHOST:SRC")
    sh, sp = m.group(1), plain(m.group(2), "--stage")
    if not LANE.fullmatch(sp):
        raise Refused(f"--stage {sp}: the source is a tree inside /srv/opentallas-scratch*/claude/<lane>/")
    run_host = o["--hosts"]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]*", run_host):
        raise Refused("--hosts names exactly one host")
    d = plain(o["--dir"], "--dir")
    if not lane_dir_ok(d, lane):
        raise Refused(f"--dir {d}: not inside the lane dir of {lane} (kw45, rt and the other shared trees are never a destination)")
    if cmd[:1] == ["env"]:
        if len(cmd) < 2 or not STREAMS.fullmatch(cmd[1]):
            raise Refused("env sets only OT_TREE_FORK_STREAMS=1..99")
        cmd = cmd[2:]
    if len(cmd) < 4 or cmd[0] not in ("python3", "/usr/bin/python3") or cmd[1] != "-I":
        raise Refused("the command is python3 -I <rt tool> ..., no shell")
    t = RT_TOOL.fullmatch(cmd[2])
    if not t:
        raise Refused(f"{cmd[2]}: only ot-tree-fork or src_manifest.py from rt/current or rt/<sha12>")
    pos, opt, rest = [], {}, cmd[3:]
    fork = t.group(1).startswith("fleet")
    if not fork:
        if rest[0] != "replicate":
            raise Refused("src_manifest.py: only replicate")
        rest = rest[1:]
    val, flag = ({"--src-host", "--jobs"}, {"--no-manifest", "--dry"}) if fork else ({"--hosts"}, {"--tar"})
    i = 0
    while i < len(rest):
        x = rest[i]
        if x in flag:
            opt[x] = True
            i += 1
        elif x in val and i + 1 < len(rest) and x not in opt:
            opt[x] = rest[i + 1]
            i += 2
        elif x.startswith("-"):
            raise Refused(f"{x}: not allowed in a copy job (takes {' '.join(sorted(val | flag))})")
        else:
            pos.append(plain(x, "path"))
            i += 1
    if len(pos) != (2 if fork else 1):
        raise Refused("SRC DST" if fork else "replicate takes one TREE")
    if pos[0] != sp:
        raise Refused(f"source {pos[0]} is not the declared --stage {sh}:{sp}")
    if fork:
        dst, dst_host = pos[1], run_host
        if opt.get("--src-host") != sh:
            raise Refused(f"--src-host must be the declared {sh}")
        if not re.fullmatch(r"[0-9]+", opt.get("--jobs", "1")):
            raise Refused("--jobs takes a number")
    else:
        dst, dst_host = sp, opt.get("--hosts", "")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]*", dst_host):
            raise Refused("replicate --hosts names exactly one host")
        if sh != run_host:
            raise Refused(f"replicate runs where the tree is: --hosts must be the declared {sh}")
    if sh == dst_host:
        raise Refused(f"source and destination are both on {sh}: a local fork declares its source with a plain --stage PATH")
    if dst == d or not inside(dst, d):
        raise Refused(f"destination {dst} is not inside --dir {d}")
    return {"tool": "fork" if fork else "replicate", "rt_tool": cmd[2], "src": sp, "src_host": sh, "dst": dst, "dst_host": dst_host,
            "run_host": run_host, "dir": d, "lane": lane}


SRC_PY = r"""
import os, sys
p = sys.argv[1]
print("OK " + os.path.realpath(p) if os.path.isdir(p) else "NO " + p + " is not a directory here")
"""

# the destination rules of the rt ot-tree-fork itself (check_dst / event_root), run on the destination host; no bytecode into rt
DST_PY = r"""
import os, sys
sys.dont_write_bytecode = True
from importlib.machinery import SourceFileLoader
tool, d, dst = sys.argv[1:4]
M = SourceFileLoader("otf_copy_class", tool).load_module()
def why():
    if not os.path.isdir(d):
        return "--dir " + d + " is not a directory here"
    ev = M.event_root(d)
    if ev:
        return "--dir " + d + " resolves into event tree " + ev
    w = M.check_dst("/nonexistent/copy-class-src", dst)
    if w:
        return w
    full = os.path.join(os.path.realpath(os.path.dirname(dst)), os.path.basename(dst))
    root = os.path.realpath(d)
    if not full.startswith(root + "/"):
        return "destination resolves to " + full + ", outside --dir (" + root + ")"
    return ""
w = why()
print("NO " + w if w else "OK " + os.path.realpath(d))
"""


def is_self(host):
    return host in ("localhost", socket.gethostname().split(".")[0])


def ask(host, code, args):
    """last OK / NO line of a probe on host ('' = no answer)"""
    ev = os.environ.get("OT_EVENT_TREE_ROOTS", "")
    cmd = ["env", "OT_EVENT_TREE_ROOTS=" + ev, "python3", "-I", "-c", code] + list(args)
    if not is_self(host):
        cmd = ["ssh", "-n", "-o", "ControlPath=none", "-o", "ConnectTimeout=20", "-o", "BatchMode=yes", host, " ".join(shlex.quote(x) for x in cmd)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return ""
    return next((ln for ln in reversed(r.stdout.splitlines()) if ln[:3] in ("OK ", "NO ")), "")


def check_hosts(job, ask=ask):
    """the source on its host, the destination on its host; Refused when either is wrong or does not answer"""
    a = ask(job["src_host"], SRC_PY, [job["src"]])
    if not a.startswith("OK "):
        raise Refused(f"source {job['src_host']}:{job['src']}: {a[3:] or 'the host did not answer'}")
    if not LANE.fullmatch(a[3:].strip()):
        raise Refused(f"source {job['src_host']}:{job['src']} resolves to {a[3:].strip()}, outside /srv/opentallas-scratch*/claude/<lane>/")
    tool = RT_TOOL.fullmatch(job["rt_tool"])
    otf = job["rt_tool"][:tool.start(1)] + "fleet/ot-tree-fork"
    b = ask(job["dst_host"], DST_PY, [otf, job["dir"], job["dst"]])
    if not b.startswith("OK "):
        raise Refused(f"destination {job['dst_host']}:{job['dst']}: {b[3:] or 'the host did not answer'}")
    if not lane_dir_ok(b[3:].strip(), job["lane"]):
        raise Refused(f"--dir {job['dir']} resolves to {b[3:].strip()} on {job['dst_host']}, outside the lane dir of {job['lane']}")


def lease_list(job):
    return [job["dir"], job["src"], job["dst"]]


def check_leases(job, owner, leases):
    """Refused unless a live lease of this client names the source, the destination and --dir"""
    have = {r["path"] for r in leases if r.get("owner") == owner}
    miss = [p for p in lease_list(job) if p not in have]
    if miss:
        raise Refused("no live lease on " + ", ".join(miss))
