#!/usr/bin/env python3
"""derive_gen_hosts (FLEET-OPS-R, COORD FABLE-FLOW-1100 (2)): a die's gen_hosts = the hosts that HOLD its current source tree (the tree's manifest hash file equals the die's
src_manifest_hash, no .part / .building beside it) AND have room (scratch free >= floor + 20 GB, floor = max(gen_disk_min_gb 50..)).  Never an empty list: when no host qualifies the
current list is kept and an ALERT line is printed.  Dry by default; --apply rewrites kit_wave.json under .coord.lock (old list in prev_gen_hosts_derive) and commits through coord-commit.sh.
usage: derive_gen_hosts.py [--coord ~/coord] [--hosts h1,h2,..] [--apply]"""
import argparse, fcntl, json, os, shlex, shutil, subprocess, sys

HOSTS = ("epyc10", "epyc7", "epyc8", "epyc9", "epyc2", "intel1")
HASHFILE = ".src-manifest.sha256"
HARD_FLOOR, MARGIN = 50, 20


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


def derive(cfg, hosts=HOSTS, prober=probe, floor=None):
    """-> {die: (new list, [reasons])}"""
    out = {}
    base = max(HARD_FLOOR, int(floor if floor is not None else HARD_FLOOR))
    for die, d in (cfg.get("dies") or {}).items():
        tree, want = d.get("src"), d.get("src_manifest_hash")
        if not tree or not want or not d.get("gen_hosts"):
            continue
        keep, why = [], []
        for h in hosts:
            got, partial, free = prober(h, tree)
            if got != want:
                if h in d["gen_hosts"]: why.append(f"{h}: tree missing or other hash")
                continue
            if partial:
                if h in d["gen_hosts"]: why.append(f"{h}: partial copy beside it")
                continue
            if free is None or free < base + MARGIN:
                if h in d["gen_hosts"]: why.append(f"{h}: {free if free is None else round(free)} GB free < {base + MARGIN}")
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
    a = ap.parse_args(argv)
    cfg = json.load(open(os.path.join(a.coord, "autopilot/kit_wave.json")))
    res = derive(cfg, tuple(a.hosts.split(",")))
    for die, (new, why) in sorted(res.items()):
        cur = cfg["dies"][die]["gen_hosts"]
        print(f"{die}: {','.join(cur)} -> {','.join(new)}" + (" | " + "; ".join(why) if why else ""))
    if a.apply:
        print("applied:", apply(a.coord, res) or "nothing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
