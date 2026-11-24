#!/usr/bin/env python3
"""counted_view_canary.py (FLOW-OPS-R2 VIEW-CANARY-1123, COORD ruling 11-23 after the qct13 btab/prog loss):
every counted child view in kit_wave.json dies.<die>.prov_view_sources (job COUNTED / counted true) must exist at a
staged path: <dir>/<module>{_tt.lib,_ff.lib,.lef} non-empty on at least one live host.  Hourly from cron; posts the
modules with no live copy to the hub (FLOW-OPS-R2) when the missing set changes, and again every --repost-h hours.

  counted_view_canary.py [--kit-wave FILE] [--hosts h1,h2] [--dies all|d1,d2] [--post] [--state DIR]
HBM is parked: skipped unless --dies names it.  Read-only on every host."""
import argparse
import json
import os
import subprocess
import sys
import time

HOSTS = ["epyc7", "epyc8", "epyc9", "epyc10", "epyc11", "intel1", "epyc2", "intel2"]
HUB = "intel2"
KW = "/home/ubuntu/coord/autopilot/kit_wave.json"
SUFFIXES = ("_tt.lib", "_ff.lib", ".lef")
CHECK = ('while read m d; do ok=1; for s in _tt.lib _ff.lib .lef; do [ -s "$d/$m$s" ] || ok=0; done; '
         'echo "$ok $m $d"; done')


def counted_sources(cfg, dies=None):
    """-> {(die, module): [dir, ...]} of the counted prov_view_sources"""
    out = {}
    for die, d in sorted((cfg.get("dies") or {}).items()):
        if not isinstance(d, dict) or (dies and die not in dies):
            continue
        for m, srcs in sorted((d.get("prov_view_sources") or {}).items()):
            for e in srcs if isinstance(srcs, list) else []:
                if isinstance(e, dict) and e.get("dir") and ("COUNTED" in str(e.get("job", "")) or e.get("counted")):
                    out.setdefault((die, m), [])
                    if e["dir"] not in out[(die, m)]:
                        out[(die, m)].append(e["dir"])
    return out


def missing(sources, present):
    """sources {(die, m): [dir]}, present {(m, dir): set(hosts)} -> sorted [(die, m)] with no live copy"""
    return sorted(k for k, dirs in sources.items() if not any(present.get((k[1], d)) for d in dirs))


def probe(host, pairs, timeout=600):
    """-> {(m, dir)} present on host, or None when the host did not answer"""
    inp = "".join(f"{m} {d}\n" for m, d in pairs)
    try:
        r = subprocess.run(["ssh", "-o", "ControlPath=none", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", host, CHECK],
                           input=inp, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None
    if r.returncode != 0:
        return None
    got = set()
    for line in r.stdout.splitlines():
        p = line.split(" ", 2)
        if len(p) == 3 and p[0] == "1":
            got.add((p[1], p[2]))
    return got


def load_cfg(path):
    if os.path.exists(path):
        return json.load(open(path))
    r = subprocess.run(["ssh", "-o", "ControlPath=none", "-o", "BatchMode=yes", HUB, f"cat {KW}"],
                       capture_output=True, text=True, timeout=120, check=True)
    return json.loads(r.stdout)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kit-wave", default=KW)
    ap.add_argument("--hosts", default=",".join(HOSTS))
    ap.add_argument("--dies", default="qwen_compute,qwen_kvsys,s81,s81_head")
    ap.add_argument("--post", action="store_true")
    ap.add_argument("--repost-h", type=float, default=6.0)
    ap.add_argument("--state", default=os.path.expanduser("~/.local/state/counted-view-canary"))
    a = ap.parse_args(argv)
    cfg = load_cfg(a.kit_wave)
    dies = None if a.dies == "all" else set(a.dies.split(","))
    src = counted_sources(cfg, dies)
    pairs = sorted({(m, d) for (_, m), ds in src.items() for d in ds})
    present, down = {}, []
    for h in a.hosts.split(","):
        got = probe(h, pairs)
        if got is None:
            down.append(h)
            continue
        for k in got:
            present.setdefault(k, set()).add(h)
    miss = missing(src, present)
    stamp = time.strftime("%F %T")
    line = (f"VIEW-CANARY {stamp}: {len(src)} counted views, {len(miss)} with no live copy"
            + (f" (hosts down: {','.join(down)})" if down else ""))
    print(line)
    for die, m in miss:
        print(f"  MISSING {die} {m}: {' | '.join(src[(die, m)])}")
    os.makedirs(a.state, exist_ok=True)
    sf = os.path.join(a.state, "last.json")
    last = json.load(open(sf)) if os.path.exists(sf) else {}
    key = [f"{d}/{m}" for d, m in miss]
    due = key and (key != last.get("missing") or time.time() - last.get("posted", 0) > a.repost_h * 3600)
    rec = {"t": stamp, "missing": key, "down": down, "posted": last.get("posted", 0)}
    if a.post and due:
        txt = (f"ALERT [VIEW-CANARY -> COORD, FLOW-OPS-R2] {len(miss)} counted child view(s) have no live copy at any "
               f"staged path (kits that bind them fail INFRA-VIEW-MISSING): " + ", ".join(key))
        r = subprocess.run(["ssh", "-o", "ControlPath=none", "-o", "BatchMode=yes", HUB,
                            "cd ~/coord && bin/post.sh FLOW-OPS-R2 \"$(cat)\""], input=txt, capture_output=True,
                           text=True, timeout=120)
        if r.returncode == 0:
            rec["posted"] = time.time()
    json.dump(rec, open(sf + ".tmp", "w"), indent=1)
    os.replace(sf + ".tmp", sf)
    return 1 if miss else 0


if __name__ == "__main__":
    sys.exit(main())
