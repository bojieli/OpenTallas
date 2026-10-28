#!/usr/bin/env python3
"""MESO-START-2: greedy start-tree re-parent search (--tree-parent) for the CA-FAIL crossings of a plan.
usage: tp_search.py TOOLS_DIR OCV_JSON OUT_JSON [--skew-clean] [--rounds N] [--seed R=PORT,R=PORT]"""
import json, sys, time
sys.path.insert(0, sys.argv[1])
import count_align_plan as CAP
X, OUT = sys.argv[2], sys.argv[3]
SC = "--skew-clean" in sys.argv
ROUNDS = int(sys.argv[sys.argv.index("--rounds") + 1]) if "--rounds" in sys.argv else 4
SK = (55.2, 87.5)
rows0 = CAP.load_rows(X, "TT_droop-regions_corelat250,FF_droop-regions_corelat202.5")


def run(tp):
    s, out, regs = CAP.plan([dict(r) for r in rows0], 833.0, 833.0 / 8, 0.05, 26.5, 0, None, SK, SC, tree_parent=tp or None)
    return s, out, regs


def score(s, out):
    ok = [o for o in out if o.get("depth")]
    return (s["fail"], -min(min(o["margin_lo_ps"], o["margin_hi_ps"]) for o in ok), sum(o["lat_cycles"] for o in ok))


tp, log = {}, []
if "--seed" in sys.argv:
    tp = dict(kv.split("=", 1) for kv in sys.argv[sys.argv.index("--seed") + 1].split(","))
t0 = time.time()
s, out, regs = run(tp)
best = score(s, out)
log.append(dict(round=0, tp=dict(tp), score=best, sec=round(time.time() - t0, 1)))
print(log[-1], flush=True)
for rnd in range(ROUNDS):
    par = {g["region"]: g["start_from"] for g in regs}
    fails = [o for o in out if not o.get("depth")]
    if not fails:
        break
    def up(x):
        p = []
        while par[x]:
            p.append(x); x = par[x]["parent"]
        return p
    cand_regions = []
    for o in fails:
        a, b = up(o["src"]), up(o["dst"])
        for x in [y for y in a if y not in b] + [y for y in b if y not in a]:
            if par[x]["sync_values"] > 1 and x not in cand_regions:
                cand_regions.append(x)
    kids = {}
    for x, e in par.items():
        if e:
            kids.setdefault(e["parent"], []).append(x)
    def sub(x):
        q, s_ = [x], {x}
        for z in q:
            for k in kids.get(z, []):
                s_.add(k); q.append(k)
        return s_
    trials = []
    for x in cand_regions:
        sx = sub(x)
        for r in rows0:
            if r["dst"] == x and r["src"] not in sx and r["port"] != par[x]["port"]:
                trials.append((x, r["port"]))
    print(f"round {rnd + 1}: {len(fails)} FAIL, {len(cand_regions)} cand regions, {len(trials)} trials", flush=True)
    bt = None
    for x, port in trials:
        t = dict(tp); t[x] = port
        try:
            s2, o2, r2 = run(t)
        except ValueError:
            continue
        sc = score(s2, o2)
        if sc < best and (bt is None or sc < bt[0]):
            bt = (sc, t, s2, o2, r2)
    if bt is None:
        break
    best, tp, s, out, regs = bt
    log.append(dict(round=rnd + 1, tp=tp, score=best, sec=round(time.time() - t0, 1)))
    print(log[-1], flush=True)
json.dump(dict(log=log, tree_parent=tp, fail=s["fail"], fail_ports=[o["port"] for o in out if not o.get("depth")],
               summary={k: v for k, v in s.items() if k not in ("tree_edges_ambiguous",)}), open(OUT, "w"), indent=1)
