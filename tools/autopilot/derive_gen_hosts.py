#!/usr/bin/env python3
"""derive_gen_hosts (FLEET-OPS-R, COORD FABLE-FLOW-1100 (2)): a die's gen_hosts = the hosts that HOLD its current source tree (the tree's manifest hash file equals the die's
src_manifest_hash, no .part / .building beside it) AND have room (scratch free >= floor + 20 GB, floor = max(gen_disk_min_gb 50..)).  Never an empty list: when no host qualifies the
current list is kept and an ALERT line is printed.  Dry by default; --apply rewrites kit_wave.json under .coord.lock (old list in prev_gen_hosts_derive) and commits through coord-commit.sh.
usage: derive_gen_hosts.py [--coord ~/coord] [--hosts h1,h2,..] [--apply]"""
import argparse, fcntl, json, os, shlex, shutil, subprocess, sys

HOSTS = ("epyc10", "epyc7", "epyc8", "epyc9", "epyc2", "intel1")
HASHFILE = ".src-manifest.sha256"
HARD_FLOOR, MARGIN = 50, 20
# COORD 11-17: ~/.local/opentallas-pdk-asap7 (the legacy PDK root ref_tile.py gen routes use) existed on intel1 and epyc2 only, so svc core routes failed on epyc8.  A host that lacks a required
# tool path is not a gen host.  Per die: kit_wave.json dies.<die>.host_requires (list, [] = none); default for every die = REQUIRES_DEFAULT.
def flow_images(kind="require"):
    """names in tools/fleet/flow_images.txt with the given keyword"""
    try:
        txt = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fleet", "flow_images.txt")).read()
    except OSError:
        return ()
    return tuple(l.split(None, 1)[1].strip() for l in txt.splitlines() if l.split(None, 1)[:1] == [kind] and len(l.split(None, 1)) == 2)


def pinned_images():
    """[(name, id)] of the `pin NAME ID` lines"""
    return tuple((p[0], p[1]) for p in (x.split() for x in flow_images("pin")) if len(p) == 2)


# a `docker-image:NAME` entry means the docker image must exist on the host (COORD 11-17: epyc7 lacked opentallas/orfs:asap7lock-grtoff -> FAIL_PREFLOOR)
REQUIRES_DEFAULT = ("~/.local/opentallas-pdk-asap7/lib",) + tuple("docker-image:" + i for i in flow_images("require")) \
    + tuple("docker-id:%s=%s" % p for p in pinned_images())


def probe(host, tree, run=subprocess.run):
    """-> (hash text or '', partial present, scratch free GB or None)"""
    d = os.path.dirname(tree)
    cmd = (f"cat {shlex.quote(tree)}/{HASHFILE} 2>/dev/null | head -c 64; echo; "
           f"ls -d {shlex.quote(tree)}.part {shlex.quote(tree)}.building 2>/dev/null | head -n1; echo; "
           f"df -BM --output=avail {shlex.quote(d)} 2>/dev/null | tail -n1 | tr -dc 0-9; echo")
    try:
        r = run(["ssh", "-n", "-o", "BatchMode=yes", "-o", "ControlPath=none", "-o", "ConnectTimeout=15", host, cmd], capture_output=True, text=True, timeout=60)
    except Exception:
        return "", False, None
    ls = (r.stdout.split("\n") + ["", "", ""])[:3]
    try:
        free = int(ls[2]) / 1024
    except ValueError:
        free = None
    return ls[0].strip(), bool(ls[1].strip()), free


def host_requires(host, paths, run=subprocess.run):
    """-> [paths missing on host] (ssh test -e per path; a host that does not answer is reported missing for all)"""
    def one(p):
        if p.startswith("docker-id:"):       # a pinned NAME must resolve to exactly this id on the host (an unpinned/foreign :latest drops the host)
            n, i = p[len("docker-id:"):].split("=", 1)
            return "[ \"$(docker image inspect --format '{{.Id}}' %s 2>/dev/null || sudo -n docker image inspect --format '{{.Id}}' %s 2>/dev/null)\" = %s ] || echo MISSING %s" % (shlex.quote(n), shlex.quote(n), shlex.quote(i), shlex.quote(p))
        if p.startswith("docker-image:"):
            n = shlex.quote(p[len("docker-image:"):])
            return "(docker image inspect %s || sudo -n docker image inspect %s) >/dev/null 2>&1 || echo MISSING %s" % (n, n, shlex.quote(p))
        return "[ -e %s ] || echo MISSING %s" % (p.replace("~", "$HOME", 1), shlex.quote(p))
    cmd = "; ".join(one(p) for p in paths)
    try:
        r = run(["ssh", "-n", "-o", "BatchMode=yes", "-o", "ControlPath=none", "-o", "ConnectTimeout=15", host, cmd], capture_output=True, text=True, timeout=60)
    except Exception:
        return list(paths)
    if getattr(r, "returncode", 0) not in (0, None):
        return list(paths)
    return [l.split(None, 1)[1].strip("'") for l in r.stdout.splitlines() if l.startswith("MISSING ")]


def derive(cfg, hosts=HOSTS, prober=probe, floor=None, checker=host_requires):
    """-> {die: (new list, [reasons])}"""
    out = {}
    _req = {}
    base = max(HARD_FLOOR, int(floor if floor is not None else HARD_FLOOR))
    for die, d in (cfg.get("dies") or {}).items():
        tree, want = d.get("src"), d.get("src_manifest_hash")
        if not tree or not want or not d.get("gen_hosts"):
            continue
        keep, why = [], []
        need = tuple(d["host_requires"]) if isinstance(d.get("host_requires"), list) else REQUIRES_DEFAULT
        for h in hosts:
            if need:
                miss = _req.get((h, need))
                if miss is None:
                    miss = _req[(h, need)] = checker(h, need)
                if miss:
                    if h in d["gen_hosts"]: why.append(f"{h}: lacks {', '.join(miss)}")
                    continue
            got, partial, free = prober(h, tree)
            if got != want:
                if h in d["gen_hosts"]: why.append(f"{h}: tree missing or other hash")
                continue
            if partial:
                if h in d["gen_hosts"]: why.append(f"{h}: partial copy beside it")
                continue
            need_free = max(base + MARGIN, int((d.get("gen_host_min_free_gb") or {}).get(h) or 0))     # COORD 11-18: per-host floor above the common one (intel1 150 GB for S81 col)
            if free is None or free < need_free:
                if h in d["gen_hosts"]: why.append(f"{h}: {free if free is None else round(free)} GB free < {need_free}")
                continue
            keep.append(h)
        if not keep:
            out[die] = (list(d["gen_hosts"]), ["ALERT no host holds the tree with room: list kept"])
        else:
            new = [h for h in d["gen_hosts"] if h in keep] + [h for h in keep if h not in d["gen_hosts"]]
            out[die] = (new, why)
    return out


def apply(coord, result, run=subprocess.run):
    p = os.path.join(coord, "autopilot/kit_wave.json"); changed = []
    with open(os.path.join(coord, ".coord.lock"), "a") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        c = json.load(open(p))
        for die, (new, why) in result.items():
            d = c["dies"][die]
            if new and new != d["gen_hosts"]:
                d["prev_gen_hosts_derive"] = list(d["gen_hosts"]); d["gen_hosts"] = new; changed.append(f"{die}={','.join(new)}")
        if changed:
            shutil.copy(p, p + ".bak-derive-gen-hosts")
            tmp = p + ".tmp.derive"; open(tmp, "w").write(json.dumps(c, indent=1)); os.replace(tmp, p)
    if changed:
        run(["bash", os.path.join(coord, "bin/coord-commit.sh"), "derive_gen_hosts: " + " ".join(changed), "autopilot/kit_wave.json"], cwd=coord, capture_output=True, text=True)
    return changed


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--coord", default=os.path.expanduser("~/coord")); ap.add_argument("--hosts", default=",".join(HOSTS)); ap.add_argument("--apply", action="store_true")
    ap.add_argument("--log", default="", help="append one line per die and run (time, old -> new, reasons, applied) to this file: every change is logged")
    a = ap.parse_args(argv)
    cfg = json.load(open(os.path.join(a.coord, "autopilot/kit_wave.json")))
    res = derive(cfg, tuple(a.hosts.split(",")))
    for die, (new, why) in sorted(res.items()):
        cur = cfg["dies"][die]["gen_hosts"]
        print(f"{die}: {','.join(cur)} -> {','.join(new)}" + (" | " + "; ".join(why) if why else ""))
    changed = apply(a.coord, res) if a.apply else []
    if a.apply:
        print("applied:", changed or "nothing")
    if a.log:
        import time
        os.makedirs(os.path.dirname(os.path.abspath(a.log)), exist_ok=True)
        with open(a.log, "a") as f:
            for die, (new, why) in sorted(res.items()):
                cur = cfg["dies"][die]["gen_hosts"]
                f.write("%s %s %s -> %s%s%s\n" % (time.strftime("%F %T"), die, ",".join(cur), ",".join(new), " APPLIED" if any(c.startswith(die + "=") for c in changed) else (" (dry)" if not a.apply else ""), (" | " + "; ".join(why)) if why else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
