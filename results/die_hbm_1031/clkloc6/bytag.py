#!/usr/bin/env python3
"""HBM-CLKLOC-6 diagnostic wrapper (no gate change): runs main die_sta_related with the given argv and also writes, for
every class with a kit-contract hold window, the per-tag (part / 'src->dst') contract violations and needed W with the
SAME formula as time_class (lc - ea - cr + ko > W).  usage: bytag.py OUT.json -- <die_sta_related argv>"""
import json, sys, atexit
from collections import defaultdict
out = sys.argv[1]; argv = sys.argv[sys.argv.index("--") + 1:]
sys.path.insert(0, "/srv/opentallas-scratch2/claude/wt/hbm-clkloc-6/tools/die_plan")
import die_sta_related as D
REC = []
orig = D.time_class
def tc(pairs, taps, rng, reg, *a, **kw):
    r = orig(pairs, taps, rng, reg, *a, **kw)
    hw, ko_ = kw.get("hold_window"), kw.get("kit_offset")
    if hw is not None and pairs:
        w = float(hw["ps"]); st = defaultdict(lambda: [0, 0, 0.0])
        for a_, b_, tag in pairs:
            A, B = taps[a_], taps[b_]
            node = D.pair_node(A, B); la, ea, lc, ec = D.arr4(A, B, node); cr = D.credit(rng, node, la, ea, lc, ec)
            ko = (ko_.get(b_, 0.0) - ko_.get(a_, 0.0)) if ko_ else 0.0
            v = lc - ea - cr + ko; s = st[tag]; s[0] += 1; s[1] += v > w; s[2] = max(s[2], v)
        REC.append(dict(window=w, basis=hw.get("basis"), tags={k: dict(pairs=v[0], viol=v[1], need=round(v[2], 2))
                                                               for k, v in sorted(st.items(), key=lambda kv: -kv[1][2])}))
    return r
D.time_class = tc
atexit.register(lambda: json.dump(REC, open(out, "w"), indent=1))
sys.exit(D.main(argv))
