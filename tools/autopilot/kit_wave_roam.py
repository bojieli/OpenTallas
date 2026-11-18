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

RAN_RE = re.compile(r"(?m)^ot-run: RAN on ([^\s:]+)")
MAX_MB = 3000


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


    def ensure_snap(self, src, dst, sd, verify_cmd):
        """KIT-OPS-5 11-15 (COORD r241): the verified kit snapshot directory sd is present on dst, replicated from src first when it is
        not.  A roam stage reads kit inputs through snapshot paths; a host that never received the snapshot raised FileNotFoundError.
        Present = sd/.verified exists on dst (written only by a passing verify).  -> (rc, text); rc 0 = present and verified."""
        rc, _ = self.sh(dst, f"test -f {sd}/.verified")
        if rc == 0:
            return 0, ""
        rc, txt = self.sh(src, f"ssh -o BatchMode=yes -o ControlPath=none {dst} mkdir -p {sd} && "
                               f"rsync -a --exclude .verified --exclude .used -e 'ssh -o BatchMode=yes -o ControlPath=none' {sd}/ {dst}:{sd}/")
        if rc:
            return rc, txt
        return self.sh(dst, verify_cmd(sd))


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
