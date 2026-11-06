#!/usr/bin/env python3
"""DIE-KV-79 11-05: RTL flop bits that yosys removes (folded to a constant or merged) in a flattened core.
pre.json: proc; flatten; opt_clean.  post.json: opt -full; opt_dff -sat; opt_merge; opt_clean.
A register bit = Q bit of an FF cell in pre, named by its longest non-auto netname. Removed = that netname bit is no
longer an FF Q bit in post. Value: the post netname bit when it is a constant ('0'/'1'/'x'), else 'merged'.
Usage: fold_audit.py pre.json post.json [--bits]   (--bits: per register, removed index ranges + values)"""
import json, sys, re, collections
def load(path):
    d = json.load(open(path)); return next(iter(d["modules"].values()))
def ffq(m):
    q = {}
    for c in m["cells"].values():
        t = c["type"]
        if "ff" not in t.lower() and "dlatch" not in t.lower(): continue
        rst = any(p in c["connections"] for p in ("ARST", "SRST", "CLR", "SET", "R", "S"))
        for b in c["connections"].get("Q", []):
            if isinstance(b, int): q[b] = rst
    return q
def names(m):
    out = collections.defaultdict(list)
    for n, nn in m["netnames"].items():
        if n.startswith("$") or re.fullmatch(r"n\d+", n): continue
        for i, b in enumerate(nn["bits"]): out[b].append((n, i))
    return out
def observable(m):
    """bit ids in the backward cone of the output ports (through every cell, FF D/EN/reset included); bit-level after
    simplemap, so a flop whose Q only feeds its own hold mux (dead loop) is not observable"""
    drv = collections.defaultdict(list)
    for c in m["cells"].values():
        outs = [b for p, bs in c["connections"].items() if c.get("port_directions", {}).get(p) == "output" for b in bs]
        ins = [b for p, bs in c["connections"].items() if c.get("port_directions", {}).get(p) != "output" for b in bs]
        for b in outs:
            if isinstance(b, int): drv[b].extend(x for x in ins if isinstance(x, int))
    seen = set(); st = [b for p in m["ports"].values() if p["direction"] == "output" for b in p["bits"] if isinstance(b, int)]
    while st:
        b = st.pop()
        if b in seen: continue
        seen.add(b); st.extend(drv.get(b, ()))
    return seen
pre, post = load(sys.argv[1]), load(sys.argv[2])
pq, tq = ffq(pre), ffq(post)
obs = observable(pre)
dead = [b for b in pq if b not in obs]
print(f"FOLD_AUDIT unobservable (dead) RTL ff bits in pre: {len(dead)} (not counted below)")
pq = {b: r for b, r in pq.items() if b in obs}
pn = names(pre)
postnn = post["netnames"]
regs = collections.defaultdict(dict)   # name -> {i: value}
nore = collections.Counter(); tot = collections.Counter()
for b, rst in pq.items():
    cand = pn.get(b)
    if not cand: continue
    n, i = max(cand, key=lambda x: (x[0].count("."), len(x[0])))
    tot[(n, rst)] += 1
    pb = postnn.get(n, {}).get("bits")
    v = pb[i] if pb is not None and i < len(pb) else None
    if isinstance(v, int) and v in tq: continue
    regs[(n, rst)][i] = v if isinstance(v, str) else ("merged" if v is not None else "gone")
gone = sum(len(v) for v in regs.values())
print(f"FOLD_AUDIT ff_bits pre {len(pq)} post {len(tq)} removed {gone} noreset {sum(len(v) for (n, r), v in regs.items() if not r)}")
for (n, rst), v in sorted(regs.items(), key=lambda x: -len(x[1])):
    print(f"  {len(v):5d}/{tot[(n, rst)]:<5d} {'reset  ' if rst else 'NORESET'} {n}")
    if "--bits" in sys.argv:
        runs = []; ks = sorted(v)
        for k in ks:
            if runs and k == runs[-1][1] + 1 and v[k] == runs[-1][2]: runs[-1][1] = k
            else: runs.append([k, k, v[k]])
        print("        " + " ".join(f"[{a}:{b}]={c}" if a != b else f"[{a}]={c}" for b, a, c in [(r[0], r[1], r[2]) for r in runs]))
