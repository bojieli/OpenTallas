#!/usr/bin/env python3 -I
"""kit_wave_roam.py -- WAVE-BALANCE-1 (COORD 11-14): a kit-wave stage may run on ANY of the die's gen hosts.

Why.  run-item created the attempt dir W on the gen host G and pinned every heavy stage `--dir W --hosts G`: a pinned
ot-run waiter can never be re-placed, rebalanced or spilled, so 100+ waiters sat on epyc9 while epyc2 admitted 400 GB.
How.  The attempt dir is small before place (about 1 MB; checked against max_mb).  Before a stage the Roamer copies W from
the home host G to every other candidate host (rsync --delete, so each copy mirrors the home copy exactly); ot-run gets
`--hosts G,H1,H2..`, so every listed host holds --dir with the previous stage's outputs and ot-run's own admission and
REBALANCE (300 s) pick or move the waiter; after the stage the host that RAN it copies W back to G (G stays home: every
later reader, result.json and the place stage still look at G:W).  Any copy failure drops that host for the stage; with no
other host the stage is pinned to G exactly as before.  Only stages whose --dir is W roam (never the shared lane root).
"""
import re
import shlex
import subprocess
import time

RAN_RE = re.compile(r"(?m)^ot-run: RAN on ([^\s:]+)")
MAX_MB = 3000
COPY_TIMEOUT_S = 2400


class Ops:
    """host access: size_mb(host, path), copy(src_host, dst_host, path) -> rc, text (path/ -> path/ with --delete)"""
    def __init__(self, ssh_run):
        self.sh = ssh_run                              # sh(host, cmd) -> (rc, text)

    def size_mb(self, host, path):
        rc, txt = self.sh(host, f"du -sm {path} | cut -f1")
        try:
            return int(txt.split()[-1]) if rc == 0 else None
        except (ValueError, IndexError):
            return None

    def copy(self, src, dst, path, delete=True):
        flag = "--delete " if delete else ""
        return self.sh(src, f"ssh -o BatchMode=yes -o ControlPath=none {dst} mkdir -p {path} && "
                            f"rsync -a {flag}-e 'ssh -o BatchMode=yes -o ControlPath=none' {path}/ {dst}:{path}/")


    SSH = "ssh -o BatchMode=yes -o ControlPath=none"

    def ensure_snap(self, src, dst, sd, verify_cmd):
        """KIT-OPS-5 11-15 (COORD r241): the verified kit snapshot directory sd is present on dst, replicated from src first when it is
        not.  A roam stage reads kit inputs through snapshot paths; a host that never received the snapshot raised FileNotFoundError.
        Present = sd/.verified exists on dst (written only by a passing verify).  -> (rc, text); rc 0 = present and verified.
        COPY-DEDUPE-1119 (COORD: 74 identical rsyncs of ONE snapshot, 213 in all, from 5 hosts into epyc7 for 65 min, epyc7 at load 700): every roaming kit ran its own copy because the
        snapshot stays unverified until the first copy ends.  Now ONE copy per (snapshot, destination) runs at a time: the check + rsync + verify run under an flock on the SOURCE host
        (<sd>.push-<dst>.lock); a kit that waited finds .verified on dst afterwards and returns at once (no second copy, no second verify)."""
        rc, _ = self.sh(dst, f"test -f {sd}/.verified")
        if rc == 0:
            return 0, ""
        lock = f"{sd}.push-{dst}.lock"
        body = (f"{self.SSH} {dst} test -f {sd}/.verified && exit 0; "
                f"{self.SSH} {dst} mkdir -p {sd} && "
                f"rsync -a --exclude .verified --exclude .used -e '{self.SSH}' {sd}/ {dst}:{sd}/ && "
                f"{self.SSH} {dst} {shlex.quote(verify_cmd(sd))}")
        # COPY-TIMEOUT-1119: the copy runs under `timeout -k 30 COPY_TIMEOUT_S` (own process group: on expiry the bash, its rsync and its ssh are all killed), so a timed-out copy cannot keep running after its row gave up
        return self.sh(src, f"flock -w 7200 {shlex.quote(lock)} timeout -k 30 {COPY_TIMEOUT_S} bash -c {shlex.quote(body)}")


class RoamArgv(list):
    """an ot-run argv whose --hosts value the Roamer rewrites (list subclass: run() / logging treat it as a list)"""
    roamer = None

    def set_hosts(self, hosts):
        i = self.index("--hosts")
        self[i + 1] = ",".join(hosts)


class Roamer:
    def __init__(self, ops, W, G, candidates, hub_names=("localhost",), max_mb=MAX_MB, enabled=True):
        self.ops, self.W, self.G, self.max_mb = ops, W, G, max_mb
        self.others = [] if not enabled else [h for h in dict.fromkeys(candidates or [])
                                              if h != G and h not in hub_names and h]
        self.log = []
        self.snaps = []                    # verified kit snapshot dirs this kit reads (set once kit_snap_stage returned)
        self.snap_verify = None            # sd -> shell command that verifies sd on the host it runs on

    def before(self, stage):
        """copy W to every other candidate -> the host list for this stage (G first)"""
        if not self.others:
            return [self.G]
        mb = self.ops.size_mb(self.G, self.W)
        if mb is None or mb > self.max_mb:
            self.log.append(f"KW_ROAM {stage}: pinned to {self.G} (attempt dir {mb} MB)")
            return [self.G]
        ok = [self.G]
        for h in self.others:
            rc, txt = self.ops.copy(self.G, h, self.W)
            if rc == 0:                    # the stage may only be offered to a host that holds the kit's snapshots (no pinning)
                for sd in self.snaps:
                    rc, txt = self.ops.ensure_snap(self.G, h, sd, self.snap_verify)
                    if rc:
                        txt = f"snapshot {sd[-40:]}: {txt}"
                        break
            if rc == 0:
                ok.append(h)
            else:
                self.log.append(f"KW_ROAM {stage}: {h} dropped (sync rc {rc}: {txt[-120:]})")
        return ok

    def after(self, stage, txt):
        """the host that ran the stage copies W home -> (ok, note); a stage that ran on G needs nothing"""
        ran = RAN_RE.findall(txt or "")
        h = ran[-1] if ran else self.G
        if h == self.G or h == "localhost" or h not in self.others:
            return True, ""
        rc, t = self.ops.copy(h, self.G, self.W, delete=False)
        if rc:
            return False, f"KW_ROAM_PULLBACK_FAIL {stage} {h}->{self.G} rc {rc}: {t[-200:]}"
        return True, f"KW_ROAM {stage}: ran on {h}, outputs copied back to {self.G}"


# REPIN-1121 (COORD: s81 kv_leaf t1 a3 geometry check queued from 19:26 on epyc2 with --hosts epyc2, 24 GB asked, epyc2 admitting 0 GB; 14 s81 waiters pinned the same way):
# a stage whose attempt dir is over MAX_MB (after place it is 4+ GB) never roams, and geom runs where the placed checkpoint is.  A single-host-pinned stage that has
# not been admitted within REPIN_S is re-submitted on a host that admits it now: the attempt dir (kit, geom tools) is copied there, the stage runs there, the outputs are
# copied back to the home host.  The client stopped is this process's own child (SIGTERM makes ot-run cancel its queued waiter).
REPIN_S = 1800
ADMITTED_RE = re.compile(r"ot-heavy: admitted on|ot-run: RAN on")
ADMITS_RE = re.compile(r"(?:ot-run status:|\|)\s*(\S+) admits (\d+) GB")


def single_pin(argv):
    """host of a single-host --hosts pin, else ''"""
    v = arg_after(argv, "--hosts")
    return v if v and "," not in v else ""


def arg_after(argv, flag):
    try:
        return argv[list(argv).index(flag) + 1]
    except (ValueError, IndexError):
        return ""


def parse_admits(status_text):
    """`ot-run --status` text -> {host: GB it admits now}"""
    return {h: int(g) for h, g in ADMITS_RE.findall(status_text or "")}


def pick_alt(admits, mem, exclude, candidates):
    """the candidate host (not excluded) that admits >= mem GB now with the most room, else ''"""
    best = sorted(((admits.get(h, 0), h) for h in candidates if h not in exclude and admits.get(h, 0) >= mem), reverse=True)
    return best[0][1] if best else ""


def is_movable(argv, others, home_dir, repin_s=REPIN_S):
    d = arg_after(argv, "--dir")
    return bool(single_pin(argv) and others and repin_s and d and (d == home_dir or d.startswith(home_dir.rstrip("/") + "/")))


class Done:
    def __init__(self, returncode, stdout):
        self.returncode, self.stdout = returncode, stdout


def run_watch(argv, ef, live, others, home_dir, ops, status_fn, log, repin_s=REPIN_S, poll_s=30, clock=time.time, popen=subprocess.Popen, timeout=None):
    """run the ot-run argv; a stage pinned to ONE host and not admitted within repin_s moves to a host that admits it (see above) -> Done(rc, stdout)"""
    pin, d = single_pin(argv), arg_after(argv, "--dir")
    mem = int(arg_after(argv, "--mem") or 0)
    movable = is_movable(argv, others, home_dir, repin_s)
    p = popen(list(argv), stdout=subprocess.PIPE, stderr=ef, text=True)
    t0 = clock()
    while movable:
        try:
            out, _ = p.communicate(timeout=poll_s)
            return Done(p.returncode, out)
        except subprocess.TimeoutExpired:
            pass
        if clock() - t0 < repin_s:
            continue
        try:
            if ADMITTED_RE.search(open(live, errors="replace").read()):
                break                                      # admitted: it runs, never touched
        except OSError:
            pass
        alt = pick_alt(parse_admits(status_fn()), mem, {pin}, others)
        if not alt:
            t0 = clock()                                   # nothing admits it now: look again in repin_s
            continue
        log(f"KW_REPIN {d[-60:]}: not admitted on {pin} after {int(clock() - t0)} s; copying the attempt dir to {alt}")
        rc, txt = ops.copy(pin, alt, d)
        if rc:
            log(f"KW_REPIN: copy to {alt} failed (rc {rc}: {txt[-120:]}); stays pinned to {pin}")
            t0 = clock()
            continue
        p.terminate()                                      # our own child: its queued waiter is cancelled
        try:
            p.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            p.kill()
            p.communicate()
        argv2 = list(argv)
        argv2[argv2.index("--hosts") + 1] = alt
        p2 = popen(argv2, stdout=subprocess.PIPE, stderr=ef, text=True)
        out, _ = p2.communicate(timeout=timeout)
        b, note = ops.copy(alt, pin, d, delete=False)
        log(f"KW_REPIN: ran on {alt}" + (f"; outputs copied back to {pin}" if not b else f"; COPY-BACK FAILED rc {b}: {note[-120:]}"))
        return Done(p2.returncode if not b else (p2.returncode or 1), out)
    out, _ = p.communicate(timeout=timeout)
    return Done(p.returncode, out)
