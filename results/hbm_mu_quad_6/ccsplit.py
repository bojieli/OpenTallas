#!/usr/bin/env python3
"""HBM-MU-QUAD-6: make core_conns.json resolve quadrant-split partners per quadrant.
A core_conns entry  <type>.<leaf>.<port> -> core:<X>  where X is a soft content realised ONLY by split hard cores
X__q<k> (no core named X) and <leaf> is itself split into <leaf>__q<k>: the true partner of <leaf>__q<k> is X__q<k>
(the plan's own internal_stations launch/capture pairs are per quadrant).  Rewrites the generic entry into per-split
entries; leaves everything else untouched.  usage: ccsplit.py PLAN.json CORE_CONNS_IN CORE_CONNS_OUT REPORT"""
import json, sys, re
plan, cin, cout, rp = sys.argv[1:5]
P = json.load(open(plan)); C = json.load(open(cin)); rep = []
for tn, leaves in C.items():
    t = P["partition_types"].get(tn)
    if not t:
        continue
    cores = {h["inst"] for h in t.get("hard_cores", [])}
    def splits(x):
        return sorted(c for c in cores if re.fullmatch(re.escape(x) + r"__q\d+", c))
    for leaf in list(leaves):
        lsp = splits(leaf)
        if leaf in cores or not lsp:
            continue
        ports = leaves[leaf]; moved = {}
        for port, lst in ports.items():
            keep, per = [], {}
            for v in lst:
                k, _, nm = v.partition(":")
                psp = splits(nm) if k == "core" and nm not in cores else []
                if psp and {s[len(nm):] for s in psp} >= {s[len(leaf):] for s in lsp}:
                    for s in lsp:
                        per.setdefault(s, []).append("core:" + nm + s[len(leaf):])
                else:
                    keep.append(v)
            if per:
                moved[port] = (keep, per)
        for port, (keep, per) in moved.items():
            if keep:
                ports[port] = keep
            else:
                del ports[port]
            for s, lst in per.items():
                leaves.setdefault(s, {}).setdefault(port, []).extend(lst)
            rep.append(dict(type=tn, leaf=leaf, port=port, per_split={s: l for s, l in per.items()}, kept=keep))
        if not ports:
            del leaves[leaf]
json.dump(C, open(cout, "w"), indent=1, sort_keys=True)
json.dump(dict(rewritten=len(rep), entries=rep), open(rp, "w"), indent=1)
print(len(rep), "port entries rewritten per split")
