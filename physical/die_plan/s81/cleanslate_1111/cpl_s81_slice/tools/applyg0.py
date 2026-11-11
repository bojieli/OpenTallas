#!/usr/bin/env python3
"""CPL-S81-SLICE: apply family deltas (positions/orients, internal-station regs + core clock taps re-sited with
unchanged counts) to plan 99f40d35 -> plan_after.json; EQ check: only hard_cores origin/orient, internal_stations
from/to/regs and clock.taps xy differ, and station/tap counts are unchanged.  usage: applyg0.py PLAN OUT DELTA..."""
import copy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cpl  # noqa: E402
import common  # noqa: E402

P, conns = cpl.load(sys.argv[1])
Q = copy.deepcopy(P)
n_types = 0
for dp in sys.argv[3:]:
    D = json.load(open(dp))
    for tn, d in D.items():
        M = common.model(P, conns, tn)
        pl = list(M.current())
        for inst, v in d.items():
            pl[M.ix[inst]] = (v[0], v[1], v[2])
        Q["partition_types"][tn] = M.plan_with(pl, resite=True)
        n_types += 1


def diff(a, b, path=""):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in set(a) | set(b):
            if k not in a or k not in b:
                out.append(path + "/" + str(k) + " (added/removed)")
            else:
                out += diff(a[k], b[k], path + "/" + str(k))
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(path + " (len %d->%d)" % (len(a), len(b)))
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                out += diff(x, y, path + "[%d]" % i)
    elif a != b:
        out.append(path)
    return out


import re  # noqa: E402
ALLOWED = re.compile(r"^/partition_types/[^/]+/(hard_cores\[\d+\]/(origin_um|orient)(\[\d\])?|"
                     r"internal_stations\[\d+\]/(from_um|to_um|regs_um)(\[\d+\])*|clock/taps\[\d+\]/(xy|tap_um|xy_um)(\[\d\])?)$")
bad = [p for p in diff(P, Q) if not ALLOWED.match(p)]
json.dump(Q, open(sys.argv[2], "w"), indent=1)
print("types changed", n_types, "EQ non-position diffs", len(bad), bad[:20])
