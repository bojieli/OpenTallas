#!/usr/bin/env python3
"""ext_source_check: a die tree's kit / bind records must not name sources outside the tree (TOOLS-CONVERGE-1116, QC-FLOWERR).

A kit built on a new tree can still read RTL from an old tree (the QC 4P manifest resolved base ../../../../.. into another lane's
tree; the KV bind named /srv/opentallas-scratch3/... paths that a roam host lacks).  This scans text records (.f .json .tcl .txt
.tsv .sh .mk .ys .log) under SCAN dirs for absolute /srv paths and fails on any that is not under an ALLOW root.

  ext_source_check.py --allow TREE [--allow BINDOUT ...] [--allow-missing-ok] SCAN [SCAN ...]    exit 1 = external path found
"""
import argparse
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


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--allow", action="append", required=True)
    ap.add_argument("scan", nargs="+")
    a = ap.parse_args(argv)
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
