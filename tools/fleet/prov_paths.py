#!/usr/bin/env python3
"""prov_paths (FLEET-OPS-R, COORD r550/r551 class defect 11-17): every path a view's provenance.json names is a LIVE reference of its tree.
74 S81 col launches failed kit_snap because a view in the current d5e tree named .../count-archive-2/s81views_v20261110/x/ot_s81_cfg7_seq_bfp/xbase/6_final.odb and the cleaner had deleted that archive.
scan_tree(tree)  -> {abs path: [provenance.json files naming it]} (stdlib only, runs on the host that holds the tree)
audit(cfg, hosts)  for each die: current src + rollback_tree on each gen host (or the hosts that hold them): paths + whether each exists there -> cache JSON (read by build_protected_live) + a missing list
usage: prov_paths.py audit [--coord ~/coord] [--cache ~/.local/state/prov_paths.json] [--post]       prov_paths.py scan TREE   (JSON on stdout)"""
import json, os, re, shlex, subprocess, sys, time

RX = re.compile(r"/srv/opentallas-scratch[0-9]*/claude/[A-Za-z0-9._+/@=~-]+")
CACHE = os.path.expanduser("~/.local/state/prov_paths.json")


def scan_tree(tree):
    out = {}
    for dp, dn, fn in os.walk(tree):
        dn[:] = [d for d in dn if d not in (".git", "__pycache__")]
        if "provenance.json" not in fn:
            continue
        f = os.path.join(dp, "provenance.json")
        try:
            txt = open(f, errors="replace").read()
        except OSError:
            continue
        for m in RX.finditer(txt):
            p = m.group().rstrip("/.-")
            if p.count("/") >= 5 and not p.startswith(tree):
                out.setdefault(p, []).append(os.path.relpath(f, tree))
    return out


def scan_and_check(tree):
    """-> {path: {"by": [files], "exists": bool}} on THIS host"""
    return {p: {"by": by[:3], "exists": os.path.lexists(p)} for p, by in scan_tree(tree).items()}


REMOTE = "import json,sys; sys.path.insert(0,'/tmp'); exec(open('/tmp/_prov_paths_remote.py').read()); print(json.dumps(scan_and_check(sys.argv[1])))"


def remote_scan(host, tree, script_text, run=subprocess.run):
    """ship this file to /tmp on host and scan there"""
    cmd = f"cat > /tmp/_prov_paths_remote.py && python3 -I -c {shlex.quote(REMOTE)} {shlex.quote(tree)}"
    r = run(["ssh", "-o", "BatchMode=yes", "-o", "ControlPath=none", "-o", "ConnectTimeout=20", host, cmd], input=script_text, capture_output=True, text=True, timeout=900)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return None


def targets(cfg, holds=None):
    """-> [(die, host, tree)] current src and rollback of each die on each of its gen_hosts"""
    out = []
    for die, d in (cfg.get("dies") or {}).items():
        for key in ("src", "rollback_tree"):
            t = d.get(key)
            if isinstance(t, str) and t.startswith("/srv/"):
                for h in d.get("gen_hosts") or []:
                    out.append((die, h, t))
    return out


def audit(cfg, scanner, now=None):
    """-> {"time": t, "paths": {path: {"dies": [...], "exists_on": [hosts], "missing_on": [hosts]}}}"""
    res = {}
    for die, host, tree in targets(cfg):
        got = scanner(host, tree)
        if got is None:
            continue
        for p, v in got.items():
            e = res.setdefault(p, {"dies": [], "exists_on": [], "missing_on": []})
            if die not in e["dies"]: e["dies"].append(die)
            (e["exists_on"] if v["exists"] else e["missing_on"]).append(host)
    return {"time": now or time.time(), "paths": res}


def missing(a):
    """paths that exist on NO host that was scanned"""
    return sorted(p for p, v in a["paths"].items() if not v["exists_on"])


def main(argv=None):
    argv = argv or sys.argv[1:]
    if argv and argv[0] == "scan":
        print(json.dumps(scan_and_check(argv[1]))); return 0
    coord = os.path.expanduser("~/coord"); cache = CACHE
    for i, x in enumerate(argv):
        if x == "--coord": coord = argv[i + 1]
        if x == "--cache": cache = argv[i + 1]
    cfg = json.load(open(os.path.join(coord, "autopilot/kit_wave.json")))
    text = open(os.path.abspath(__file__)).read()
    a = audit(cfg, lambda h, t: remote_scan(h, t, text))
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    tmp = cache + ".tmp"; json.dump(a, open(tmp, "w")); os.replace(tmp, cache)
    miss = missing(a)
    print("provenance paths %d, missing everywhere %d" % (len(a["paths"]), len(miss)))
    for p in miss: print("MISSING", p, "dies", ",".join(a["paths"][p]["dies"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
