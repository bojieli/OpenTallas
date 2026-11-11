#!/usr/bin/env python3
"""CPL-S81-SLICE: run the composer gate on a delta per type.  usage: ctest.py PLAN DELTA.json [TYPE...]"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cpl  # noqa: E402
import common  # noqa: E402
import cgate  # noqa: E402

P, conns = cpl.load(sys.argv[1])
D = json.load(open(sys.argv[2]))
for tn in (sys.argv[3:] or sorted(D)):
    t0 = time.time()
    M = common.model(P, conns, tn)
    G = cgate.Gate(sys.argv[1], tn, M.t)
    pl = list(M.current())
    for inst, v in D.get(tn, {}).items():
        pl[M.ix[inst]] = (v[0], v[1], v[2])
    t = M.plan_with(pl)
    new = G.new(t)
    tp = G.taps(t)
    print(tn, "moved", len(D.get(tn, {})), "new", len(new), new[:6], "tap0", G.tap0, "tap", tp, "%.1fs" % (time.time() - t0), flush=True)
