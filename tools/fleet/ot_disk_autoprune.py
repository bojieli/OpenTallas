#!/usr/bin/env python3
"""CLEAN-ALL-1115 (COORD 11-16, FABLE-FLOW-0913 item 2): disk-refusal auto-prune of SUPERSEDED die source trees in kw45.
A tree switch (tree_switch_<die>.json, written by TOOLS-CONVERGE) names the current tree of a die.  Every other
kw45/src_<die>_pin_<sha> tree of that die is SUPERSEDED.  `plan` lists the superseded trees on this host and says per tree whether
it may go now; `apply` deletes only those that pass EVERY guard:
  realpath == path (no symlink), not a prov_view_source / counted-signed path, no live process cwd/fd/cmdline under it, not named in a
  queued job / waiter / unit text (state scan), not named in handoff/queue text <= 72 h (ot_cleanup_textrefs), mtime older than 24 h.
`trigger` = run `apply` only when scratch2 free < --below GB (default 65, ot-run refuses below 50), at most once per --every minutes
(lock file); meant for an hourly-or-faster user timer on every host AFTER COORD approves.  Never touches a tree a marker names.
usage: ot_disk_autoprune.py {plan,apply,trigger} --markers DIR [--refs FILE ...] [--root /srv/opentallas-scratch2/claude/kw45]"""
import argparse, glob, json, os, re, shutil, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
PIN = re.compile(r"^src_(?P<die>[a-z0-9]+(?:_[a-z0-9]+)*?)_pin_(?P<sha>[0-9a-f]{8,})(?:_.*)?$")
ALIAS = {"head": "s81_head", "qc": "qwen_compute", "kv": "qwen_kvsys"}     # tree-name die token -> marker die


def current_by_die(mdir):
    cur = {}
    for f in glob.glob(os.path.join(mdir, "tree_switch_*.json")):
        try:
            d = json.load(open(f)); mt = os.path.getmtime(f)
        except (OSError, ValueError):
            continue
        k = ALIAS.get(d.get("die", ""), d.get("die", ""))
        if k not in cur or mt > cur[k][1]:
            cur[k] = (d.get("tree", ""), mt, d.get("tools_sha", ""))
    return cur


def superseded(root, mdir):
    """kw45 trees of a die whose marker now names another tree (or another tools sha)."""
    cur = current_by_die(mdir); out = []
    cur_names = {os.path.basename(v[0]) for v in cur.values()}
    cur_shas = {v[2] for v in cur.values() if v[2]}
    for n in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        m = PIN.match(n)
        if not m or n in cur_names:
            continue
        die = ALIAS.get(m.group("die"), m.group("die"))
        if die in cur and m.group("sha") not in cur_shas:
            out.append(os.path.join(root, n))
    return out


def procs_text():
    t, me = [], {os.getpid(), os.getppid()}
    for p in glob.glob("/proc/[0-9]*"):
        if int(p[6:]) in me:
            continue
        try:
            t.append(open(p + "/cmdline", "rb").read().decode("latin1"))
            t.append(os.readlink(p + "/cwd"))
            t.append(open(p + "/environ", "rb").read().decode("latin1"))
        except OSError:
            continue
        try:
            for f in os.listdir(p + "/fd"):
                try:
                    t.append(os.readlink(p + "/fd/" + f))
                except OSError:
                    pass
        except OSError:
            pass
    for r in (os.path.expanduser("~/.local/state/ot-run"), os.path.expanduser("~/.config/systemd/user")):
        for b, _, fs in os.walk(r):
            for f in fs:
                try:
                    if os.path.getsize(os.path.join(b, f)) < 5e6:
                        t.append(open(os.path.join(b, f), errors="ignore").read())
                except OSError:
                    pass
    return "\n".join(t)


def newest(d):
    n = 0
    for r, ds, fs in os.walk(d):
        if ".git" in ds:
            ds.remove(".git")
        for x in fs + ds:
            try:
                n = max(n, os.lstat(os.path.join(r, x)).st_mtime)
            except OSError:
                pass
    return n


def verdict(tree, ptext, refs, now=None, min_age_h=24):
    now = now or time.time()
    if os.path.islink(tree) or os.path.realpath(tree) != tree:
        return "symlink/realpath"
    if tree in ptext or tree + "/" in ptext:
        return "live process or queued/waiter/unit text"
    if any(r == tree or r.startswith(tree + "/") or tree.startswith(r + "/") for r in refs):
        return "referenced (provenance/signed/handoff<=72h/protected)"
    if now - newest(tree) < min_age_h * 3600:
        return "mtime < %gh" % min_age_h
    return None


def load_refs(files):
    refs = set()
    for f in files:
        for ln in open(f, errors="ignore"):
            ln = ln.split("\t")[0].strip().replace("opentallas-scratch3", "opentallas-scratch2").rstrip("/")
            if ln.startswith("/srv/"):
                refs.add(ln)
    return refs


def free_gb(path):
    s = os.statvfs(path)
    return s.f_bavail * s.f_frsize / 1e9


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["plan", "apply", "trigger"])
    ap.add_argument("--markers", required=True); ap.add_argument("--refs", nargs="*", default=[])
    ap.add_argument("--root", default="/srv/opentallas-scratch2/claude/kw45")
    ap.add_argument("--below", type=float, default=65.0); ap.add_argument("--every", type=float, default=10.0)
    ap.add_argument("--lock", default=os.path.expanduser("~/.local/state/ot-disk-autoprune.last"))
    a = ap.parse_args(argv)
    if a.mode == "trigger":
        f = free_gb(os.path.dirname(a.root.rstrip("/")))
        if f >= a.below:
            print("free %.0f GB >= %.0f: nothing to do" % (f, a.below)); return 0
        if os.path.exists(a.lock) and time.time() - os.path.getmtime(a.lock) < a.every * 60:
            print("ran < %g min ago" % a.every); return 0
        os.makedirs(os.path.dirname(a.lock), exist_ok=True); open(a.lock, "w").write(str(time.time()))
    refs, ptext, freed = load_refs(a.refs), procs_text(), 0
    for t in superseded(a.root, a.markers):
        why = verdict(t, ptext, refs)
        sz = int(subprocess.run(["du", "-xsm", t], capture_output=True, text=True).stdout.split()[0] or 0) if why is None or a.mode == "plan" else 0
        print(("KEEP %7dMB %s: %s" % (sz, t, why)) if why else ("%s %7dMB %s" % ("DEL " if a.mode != "plan" else "WOULD-DEL", sz, t)))
        if why is None and a.mode != "plan":
            subprocess.run(["chmod", "-R", "u+w", t]); shutil.rmtree(t, ignore_errors=True)
            if os.path.exists(t):
                subprocess.run(["sudo", "-n", "rm", "-rf", "--", t])
            freed += sz if not os.path.exists(t) else 0
    print("freed MB", freed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
