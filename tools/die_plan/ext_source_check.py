#!/usr/bin/env python3
"""ext_source_check: a die tree's kit / bind records must not name sources outside the tree (TOOLS-CONVERGE-1116, QC-FLOWERR).

A kit built on a new tree can still read RTL from an old tree (the QC 4P manifest resolved base ../../../../.. into another lane's
tree; the KV bind named /srv/opentallas-scratch3/... paths that a roam host lacks).  This scans text records (.f .json .tcl .txt
.tsv .sh .mk .ys .log) under SCAN dirs for absolute /srv paths and fails on any that is not under an ALLOW root.

  ext_source_check.py --allow TREE [--allow BINDOUT ...] [--allow-missing-ok] SCAN [SCAN ...]    exit 1 = external path found
"""
import argparse
import json
import os
import re
import sys
from collections import Counter

EXT = (".f", ".json", ".tcl", ".txt", ".tsv", ".sh", ".mk", ".ys")
PAT = re.compile(r"/srv/[A-Za-z0-9_./+-]+")


def scan(allow, scan_dirs, exts=EXT):
    """-> (Counter {path-prefix(7 comps): n}, {prefix: (file, full path)}, missing set)"""
    allow = tuple(os.path.realpath(a).rstrip("/") + "/" for a in allow) + tuple(a.rstrip("/") + "/" for a in allow)
    cnt, ex, missing = Counter(), {}, set()
    for root in scan_dirs:
        for dp, _dn, fn in os.walk(root):
            for f in fn:
                if not f.endswith(exts):
                    continue
                p = os.path.join(dp, f)
                try:
                    txt = open(p, errors="ignore").read()
                except OSError:
                    continue
                for m in set(PAT.findall(txt)):
                    if (m + "/").startswith(allow) or m.startswith(allow):
                        continue
                    k = "/".join(m.split("/")[:7])
                    cnt[k] += 1
                    ex.setdefault(k, (p, m))
                    if not os.path.exists(m):
                        missing.add(m)
    return cnt, ex, missing


LANE_RE = re.compile(r"^/srv/[^/]+/claude/([^/]+)(?:/|$)")
# a published die tree / bind of record lives under claude/kw45 with these names; everything else under claude/<x>/ is a lane folder
OK_NAMES = (re.compile(r"^src_[a-z0-9_]+_pin_[0-9a-f]{12}$"), re.compile(r"^[a-z0-9]+bind_pin_[0-9a-f]{12}$"),
            re.compile(r"^[a-z0-9]+bind_pin_[0-9a-f]{12}\.part$"))
CONFIG_KEYS = ("src", "plan", "queue_src")
KIT_RTL_KEYS = ("bind_out", "asbuilt")


def lane_folder(path, allow=()):
    """-> the lane name when `path` points into a private lane folder /srv/*/claude/<lane>/..., else ''.  claude/kw45/<published tree or
    bind of record> and any `allow` prefix are not lane folders."""
    m = LANE_RE.match(path or "")
    if not m or any(path.startswith(a) for a in allow):
        return ""
    if m.group(1) == "kw45":
        rest = path.split("/claude/kw45/", 1)[1].split("/", 1)[0]
        if any(r.match(rest) for r in OK_NAMES):
            return ""
    return m.group(1)


def check_config(cfg, allow=()):
    """FLOW-REVIEW-0513: a die's tree, plan and bind inputs (kit_wave.json dies.<die>: src, plan, queue_src, kit_rtl.bind_out/asbuilt,
    gen_args paths) must not point into a private lane folder: a lane deletes or edits its folder and the wave builds from it.
    -> [problem]; cfg = the parsed kit_wave.json (or {"dies": {...}})"""
    out = []
    for die, d in (cfg.get("dies") or {}).items():
        if not isinstance(d, dict) or not d.get("enabled", True):
            continue
        vals = [(k, d.get(k)) for k in CONFIG_KEYS]
        kr = d.get("kit_rtl") if isinstance(d.get("kit_rtl"), dict) else {}
        vals += [("kit_rtl." + k, kr.get(k)) for k in KIT_RTL_KEYS]
        vals += [("gen_args", a) for a in (d.get("gen_args") or []) if isinstance(a, str)]
        for k, v in vals:
            if isinstance(v, str) and v.startswith("/srv/"):
                lane = lane_folder(v, allow)
                if lane:
                    out.append(f"LANE-FOLDER {die}.{k} = {v} points into lane folder claude/{lane}/ (private to that lane)")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--allow", action="append", default=[])
    ap.add_argument("--config", help="kit_wave.json: refuse tree/plan/bind inputs inside private lane folders (FLOW-REVIEW-0513)")
    ap.add_argument("scan", nargs="*")
    a = ap.parse_args(argv)
    if a.config:
        probs = check_config(json.load(open(a.config)), tuple(a.allow))
        for p in probs:
            print(p)
        print("LANE_FOLDER " + ("FAIL" if probs else "OK"))
        return 1 if probs else 0
    if not a.allow or not a.scan:
        ap.error("--allow and SCAN are required without --config")
    cnt, ex, missing = scan(a.allow, a.scan)
    for k, n in cnt.most_common(15):
        print(f"EXT_SOURCE {n} distinct path(s) under {k} (e.g. {ex[k][1]} in {ex[k][0]})")
    if cnt:
        print(f"EXT_SOURCE FAIL {sum(cnt.values())} external path(s), {len(missing)} do not exist")
        return 1
    print("EXT_SOURCE OK no path outside the allowed roots")
    return 0


if __name__ == "__main__":
    sys.exit(main())
