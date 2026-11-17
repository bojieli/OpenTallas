#!/usr/bin/env python3
"""entry_symlinks: make the installed fleet entry points symlinks into rt/current so they cannot drift from main again (FLEET-OPS-R,
FABLE-FLOW-2000: noprog_stage.py differed on 7/7 hosts; ot-heavy / ot-run / ot-merge-queue copies drifted from rt/current).

  entry_symlinks.py check  [--rt DIR] [--home DIR]       report per entry: LINK-OK | LINK-WRONG | FILE-SAME | FILE-DIFF | MISSING (changes nothing; exit 1 on drift)
  entry_symlinks.py apply  [--rt DIR] [--home DIR] [--only NAME ...]
        replace each FILE with a symlink to <rt>/current/<repo path> atomically (ln -s to a temp name + rename; the previous file is kept as
        <path>.bak-symlink-<stamp>).  An entry whose rt target is missing is skipped.  Entries under /usr/local need write access (sudo -n when not root).

The ENTRIES table is the whole list; add a line to bring another installed copy under main.  Running processes keep their open file; the next
exec follows the link, so `apply` is a deploy of whatever rt/current holds: run it only after the rt/current sync of an approved main."""
import argparse, os, subprocess, sys, time

RT_DEFAULT = "/srv/opentallas-scratch2/claude/rt"
# installed path (~ = home)  ->  path under rt/current
ENTRIES = {
    "/usr/local/bin/ot-heavy": "tools/fleet/ot-heavy",
    "/usr/local/bin/ot-heavy-reconcile": "tools/fleet/ot-heavy-reconcile",
    "/usr/local/bin/ot-heavy-stop": "tools/fleet/ot-heavy-stop",
    "/usr/local/bin/ot-direct-pending": "tools/fleet/ot-direct-pending",
    "/usr/local/bin/ot-mem-grow": "tools/fleet/ot-mem-grow",
    "/usr/local/bin/ot-mem-grow-outcome": "tools/fleet/ot-mem-grow-outcome",
    "/usr/local/bin/ot-oom-age": "tools/fleet/ot-oom-age",
    "/usr/local/bin/ot-protect-die": "tools/fleet/ot-protect-die",
    "/usr/local/bin/ot-stage-peaks": "tools/fleet/ot-stage-peaks",
    "/usr/local/bin/ot-tmpfs-clean": "tools/fleet/ot-tmpfs-clean",
    "/usr/local/bin/ot-vl-jcap": "tools/fleet/ot-vl-jcap",
    "/usr/local/lib/ot-heavy/ot-heavy-exit": "tools/fleet/ot-heavy-exit",
    "~/.local/bin/ot-run": "tools/fleet/ot-run",
    "~/.local/bin/ot-job": "tools/fleet/ot-job",
    "~/.local/bin/ot-job-docker": "tools/fleet/ot-job-docker",
    "~/.local/bin/ot-git-mirror": "tools/fleet/ot-git-mirror",
    "~/.local/bin/ot-lane-clone": "tools/fleet/ot-lane-clone",
    "~/.local/bin/ot-merge-queue": "tools/fleet/ot-merge-queue",
    "~/.local/bin/ot-reserve": "tools/fleet/ot-reserve",
    "~/.local/bin/ot-sizes-sync": "tools/fleet/ot-sizes-sync",
    "~/.local/bin/ot-src-refresh": "tools/fleet/ot-src-refresh",
    "~/.local/bin/ot_store.py": "tools/fleet/ot_store.py",
    "~/.local/bin/signed_store.py": "tools/fleet/signed_store.py",
    "~/.local/lib/noprog/noprog_stage.py": "tools/autopilot/noprog_stage.py",
}


def resolve(entries, rt, home):
    for inst, rel in entries.items():
        yield inst.replace("~", home, 1) if inst.startswith("~") else inst, os.path.join(rt, "current", rel)


def state(inst, target):
    if not os.path.lexists(inst):
        return "MISSING"
    if os.path.islink(inst):
        return "LINK-OK" if os.path.realpath(inst) == os.path.realpath(target) or os.readlink(inst) == target else "LINK-WRONG"
    try:
        same = open(inst, "rb").read() == open(target, "rb").read()
    except OSError:
        return "FILE-DIFF"
    return "FILE-SAME" if same else "FILE-DIFF"


def check(entries, rt, home):
    rows = [(state(i, t), i, t) for i, t in resolve(entries, rt, home)]
    return rows


def apply(entries, rt, home, only=(), stamp=None, run=subprocess.run):
    stamp = stamp or time.strftime("%Y%m%d-%H%M%S")
    done = []
    for inst, target in resolve(entries, rt, home):
        if only and os.path.basename(inst) not in only:
            continue
        st = state(inst, target)
        if st == "LINK-OK" or not os.path.exists(target):
            continue
        tmp = inst + ".new-symlink"
        sudo = [] if os.access(os.path.dirname(inst), os.W_OK) else ["sudo", "-n"]
        cmds = [["ln", "-sfn", target, tmp]]
        if os.path.lexists(inst) and not os.path.islink(inst):
            cmds.append(["cp", "-p", inst, inst + ".bak-symlink-" + stamp])
        cmds.append(["mv", "-T", tmp, inst])
        ok = all(run(sudo + c, capture_output=True).returncode == 0 for c in cmds)
        done.append((inst, st, "OK" if ok else "FAILED"))
    return done


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["check", "apply"]); ap.add_argument("--rt", default=RT_DEFAULT)
    ap.add_argument("--home", default=os.path.expanduser("~")); ap.add_argument("--only", nargs="*", default=[])
    a = ap.parse_args(argv)
    if a.mode == "check":
        rows = check(ENTRIES, a.rt, a.home)
        for st, i, t in rows:
            print("%-10s %s" % (st, i))
        return 1 if any(s not in ("LINK-OK",) for s, _, _ in rows) else 0
    for inst, st, res in apply(ENTRIES, a.rt, a.home, a.only):
        print("%s %s (was %s)" % (res, inst, st))
    return 0


if __name__ == "__main__":
    sys.exit(main())
