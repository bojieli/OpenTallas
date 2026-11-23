#!/usr/bin/env python3
"""ot_lease.py: leases on trees, rt snapshots and kit dirs (CLEAN-AGGR-R3, COORD 11-21 after FABLE-FLOW-2200: four guard cases in one night --
copied record markers, a specA / specA7 prefix match, s81_head_r4_s0 deleted under a live plan, pruned rt snapshots -- each fixed one at a time).

A lane or job that uses a path takes a lease (path, owner, expiry); its waiter / ot-run renews it.  ot_delete_guard keeps any path that holds, lies
inside or contains a LIVE lease; an expired lease protects nothing, so everything else falls to the aggressive rules.

  ot_lease.py take PATH --owner LANE [--ttl-h 6] [--host epyc7]   (take or renew; idempotent per path+owner)
  ot_lease.py release PATH --owner LANE
  ot_lease.py list [--all]
  ot_lease.py renew-while PID PATH --owner LANE [--ttl-h 2]       (renew every ttl/3 while PID lives, then release: for waiters / ot-run)

Lease files: OT_LEASE_DIR (default ~/.local/state/ot-leases), one json per path+owner.  The hub copy of a lease reaches the other hosts through the
protected list (build_protected_live: live hub leases written host-scoped when --host is given)."""
import argparse, hashlib, json, os, re, sys, time

DEFAULT_DIR = os.path.expanduser("~/.local/state/ot-leases")
MAX_TTL_H = 72.0


def lease_dir(d=None):
    return d or os.environ.get("OT_LEASE_DIR") or DEFAULT_DIR


def _norm(p):
    return os.path.normpath(os.path.abspath(p))


def _file(d, path, owner):
    return os.path.join(d, hashlib.sha1(("%s\0%s" % (path, owner)).encode()).hexdigest()[:20] + ".json")


def take(path, owner, ttl_h=6.0, host=None, d=None, now=None):
    if not owner:
        raise ValueError("owner required")
    ttl_h = min(float(ttl_h), MAX_TTL_H)
    d = lease_dir(d); os.makedirs(d, exist_ok=True)
    now = time.time() if now is None else now
    rec = {"path": _norm(path), "owner": owner, "expires": now + ttl_h * 3600, "taken": now, "host": host or None}
    f = _file(d, rec["path"], owner); tmp = f + ".tmp%d" % os.getpid()
    with open(tmp, "w") as fh:
        json.dump(rec, fh)
    os.replace(tmp, f)
    return rec


def release(path, owner, d=None):
    try:
        os.unlink(_file(lease_dir(d), _norm(path), owner)); return True
    except FileNotFoundError:
        return False


def leases(d=None, now=None, live_only=True):
    d = lease_dir(d); now = time.time() if now is None else now
    out = []
    try:
        names = os.listdir(d)
    except OSError:
        return out
    for n in names:
        if not n.endswith(".json"):
            continue
        try:
            r = json.load(open(os.path.join(d, n)))
            if not isinstance(r, dict) or not str(r.get("path", "")).startswith("/"):
                continue
            if live_only and float(r.get("expires") or 0) <= now:
                continue
            out.append(r)
        except (OSError, ValueError, TypeError):
            continue
    return out


# CLEAN-AGGR-R3 11-22: ot-run auto-leases named whole containers (claude/kw45, claude/ot-jobs: 59 live leases), which kept every tree inside them.
# A lease on a shared container protects the container itself (and what contains it), not the trees below it.
CONTAINER = re.compile(r"/srv/opentallas-scratch[0-9]*/claude(/(kw45(/snap_[^/]+)?|ot-jobs|rt|autopilot(/closed(/[^/]+)?)?|[^/]+/runs(/[^/]+(/kit-wave)?)?))?")


# CLEAN-AGGR-R3 11-22 (COORD: 5 fable-fix-qc-v4 *_bound dirs, ~300 GB, unreachable): ot-run's automatic lease on a job's --dir that is a whole
# LANE ROOT (claude/<lane>) protects the lane dir itself, not every sibling subtree; the job's real inputs carry their own auto-leases (in/, l1r/,
# W/launch ...).  A lane's own explicit lease (owner without "/ot-run-") on its root still protects everything below it.
LANE_ROOT = re.compile(r"/srv/opentallas-scratch[0-9]*/claude/[^/]+")


def _container(r):
    p = r["path"]
    return bool(CONTAINER.fullmatch(p) or (LANE_ROOT.fullmatch(p) and "/ot-run-" in str(r.get("owner") or "")))


def covering(target, lease_list):
    """the first live lease that protects target: target is the leased path, inside it, or contains it"""
    t = _norm(target)
    for r in lease_list:
        p = r["path"]
        if p == t or p.startswith(t + "/") or (t.startswith(p + "/") and not _container(r)):
            return r
    return None


def renew_while(pid, path, owner, ttl_h=2.0, host=None, d=None, sleep=time.sleep):
    take(path, owner, ttl_h, host, d)
    while True:
        try:
            os.kill(int(pid), 0)
        except OSError:
            break
        sleep(max(60.0, ttl_h * 3600 / 3))
        take(path, owner, ttl_h, host, d)
    release(path, owner, d)


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    for c in ("take", "release"):
        x = sp.add_parser(c); x.add_argument("path"); x.add_argument("--owner", default=os.environ.get("OT_LANE"))
        if c == "take":
            x.add_argument("--ttl-h", type=float, default=6.0); x.add_argument("--host")
    x = sp.add_parser("list"); x.add_argument("--all", action="store_true")
    x = sp.add_parser("renew-while"); x.add_argument("pid"); x.add_argument("path"); x.add_argument("--owner", default=os.environ.get("OT_LANE"))
    x.add_argument("--ttl-h", type=float, default=2.0); x.add_argument("--host")
    a = ap.parse_args(argv)
    if a.cmd == "take":
        print(json.dumps(take(a.path, a.owner, a.ttl_h, a.host)))
    elif a.cmd == "release":
        print("released" if release(a.path, a.owner) else "no such lease")
    elif a.cmd == "list":
        for r in leases(live_only=not a.all):
            print("%s\t%s\t%s\t%s" % (r["path"], r["owner"], time.strftime("%F %T", time.localtime(r["expires"])), r.get("host") or "-"))
    else:
        renew_while(a.pid, a.path, a.owner, a.ttl_h, a.host)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
