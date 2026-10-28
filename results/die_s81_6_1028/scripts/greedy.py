#!/usr/bin/env python3
"""DIE-S81-6 greedy feed re-parent search (estimate only): per round, candidates from the current FAILs
(deeper side under shallower side, shallower under deeper, deeper side's subtree root just below the LCA under the
shallower side); each priced with the unchanged shared tools; keep the best (fails x1.0485 + x1.0552, then latency)."""
import json, subprocess, sys, os
O = "/srv/opentallas-scratch2/claude/die-s81-5"; H = "/srv/opentallas-scratch2/claude/die-s81-6"
base = sys.argv[1] if len(sys.argv) > 1 else "E"
feed = json.load(open(f"{O}/feed/feed_part_spine.json"))["parent"]
def run(sw, tag):
    D = f"{H}/est/g_{tag}"
    r = subprocess.run(["python3", f"{H}/est_swap.py", f"{O}/clk_{base}/tree.json", f"{O}/out_{base}_TT/arr_TT.txt",
                        f"{O}/out_{base}_FF/arr_FF.txt", D] + sw, capture_output=True, text=True)
    if r.returncode:
        return None
    subprocess.run(["bash", f"{H}/est_ca.sh", D], capture_output=True, text=True)
    try:
        s1 = json.load(open(f"{D}/ca_s1.0485.json")); s2 = json.load(open(f"{D}/ca_s1.0552.json"))
    except Exception:
        return None
    L = {x["port"]: x for x in json.load(open(f"{D}/lpo.json"))["corners"]["TT_droop-regions_corelat250"]["all"]}
    fails = [(o["src"], o["dst"], L[o["port"]]["unshared_a_ps"], L[o["port"]]["unshared_b_ps"])
             for o in s1["crossings"] + s2["crossings"] if not o.get("depth")]
    key = (s1["summary"]["fail"] + s2["summary"]["fail"], -s1["summary"]["lat_total_vs_old3"] * 0)
    return key, fails, s1["summary"], s2["summary"], D
cur = []
par = dict(feed)
best = run(cur, "r0")
print("round 0", best[0], flush=True)
for rnd in range(1, 9):
    if best[0][0] == 0:
        break
    def anc(r, p):
        o = []
        while r: o.append(r); r = p[r]
        return o
    cands = set()
    for u, v, ua, ub in best[1]:
        d, s = (u, v) if ua >= ub else (v, u)
        cands.add((d, s)); cands.add((s, d))
        a, b = anc(d, par), anc(s, par)
        l = next(x for x in a if x in b)
        i = a.index(l)
        if i >= 1: cands.add((a[i - 1], s))
        if i >= 2: cands.add((a[i // 2], s))
    res = []
    for k, (c, np_) in enumerate(sorted(cands)):
        if c == np_ or par.get(c) == np_:
            continue
        x = np_; bad = False
        while x:
            if x == c: bad = True; break
            x = par[x]
        if bad: continue
        r = run(cur + [f"{c}={np_}"], f"r{rnd}_{k}")
        if r: res.append((r[0], c, np_, r)); print(" cand", c, np_, r[0], flush=True)
    if not res:
        break
    res.sort(key=lambda z: z[0])
    if res[0][0] >= best[0]:
        print("no improvement", flush=True); break
    _, c, np_, best = res[0]
    cur.append(f"{c}={np_}"); par[c] = np_
    print("round", rnd, "take", c, "->", np_, best[0], best[2]["fail"], best[3]["fail"], best[4], flush=True)
print("FINAL", cur, best[0], json.dumps({k: best[2][k] for k in ("depth4", "depth8", "fail", "worst_margin_lo_ps", "worst_margin_hi_ps", "lat_total_vs_old3")}), json.dumps({k: best[3][k] for k in ("depth4", "depth8", "fail", "lat_total_vs_old3")}), best[4], flush=True)
