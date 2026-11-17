#!/usr/bin/env python3
"""gen_hosts_check: every gen host of a die must hold the die's CURRENT source tree (FLEET-OPS-R, COORD 11-16 'a tree apply must replicate to every gen host first,
or drop the hosts that lack it').  S81 D5 was applied while intel1 held only D4; the apply silently reset gen_hosts to the verified hosts.
  gaps(cfg, present)        -> {die: [host without <src>/.src-manifest.json]}   (present(host, path) -> bool)
  usage: gen_hosts_check.py [--kit-wave kit_wave.json] [--dies s81 ...]     exit 1 = a gap (printed)"""
import argparse, json, os, subprocess, sys


def gaps(cfg, present, dies=None):
    out = {}
    for die, d in (cfg.get("dies") or {}).items():
        if dies and die not in dies:
            continue
        src = str(d.get("src") or "").rstrip("/")
        if not src.startswith("/") or d.get("src_manifest") is False:
            continue
        miss = [h for h in (d.get("gen_hosts") or []) if not present(h, src + "/.src-manifest.json")]
        if miss:
            out[die] = miss
    return out


def ssh_present(host, path):
    argv = ["test", "-f", path] if host in ("intel2", "localhost") else ["ssh", "-n", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "-o", "ControlPath=none", host, "test -f " + path]
    return subprocess.run(argv, capture_output=True).returncode == 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kit-wave", default=os.path.expanduser("~/coord/autopilot/kit_wave.json")); ap.add_argument("--dies", nargs="*")
    a = ap.parse_args(argv)
    g = gaps(json.load(open(a.kit_wave)), ssh_present, a.dies)
    for die, hs in sorted(g.items()):
        print("GEN-HOST GAP %s: no source on %s (replicate the tree there, or drop the host from gen_hosts)" % (die, ", ".join(hs)))
    print("gen_hosts_check: %s" % ("GAPS" if g else "OK"))
    return 1 if g else 0


if __name__ == "__main__":
    sys.exit(main())
