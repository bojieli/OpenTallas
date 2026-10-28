"""DIE-S81-13: S81's own early-hang ratio. For every early core tap hung by --region-dme-early: delivered early (built) =
median late of the plain taps of the same partition - late of the core tap; ratio = delivered / early_model_ps (what
1.48 TT / 1.28 FF should be if QC's applies); residual = delivered - declared core insertion (plan).
usage: early_ratio.py TREE PLAN ARR_TT ARR_FF OUT"""
import json, sys, statistics, collections
tree, plan, aTT, aFF, OUT = sys.argv[1:6]
t = json.load(open(tree)); P = json.load(open(plan))
rows = []
def walk(o):
    if isinstance(o, dict):
        if "early_taps" in o and isinstance(o["early_taps"], list): rows.extend(o["early_taps"])
        for v in o.values(): walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)
walk(t)
ins = {}
pt = {q["name"]: q["type"] for q in P["partitions"]}
for q, ty in pt.items():
    for i, tp in enumerate(P["partition_types"][ty]["clock"].get("taps", [])):
        if tp.get("kind") == "core": ins[(q, "clk_c%d" % i)] = (tp.get("insertion_ps"), tp.get("insertion_ff_ps"))
res = {}
for C, f in (("TT", aTT), ("FF", aFF)):
    A = json.load(open(f)); by = collections.defaultdict(dict)
    for r in A["taps"]: by[r["part"]][r["port"].split("__")[-1]] = r["late_ps"]
    out = []
    for r in rows:
        port = r["port"].split("__")[-1]; d = by.get(r["part"], {})
        if port not in d: continue
        plain = [v for k, v in d.items() if k.startswith("clk_t") or k == "clk"]
        if not plain: continue
        dl = statistics.median(plain) - d[port]
        iv = ins.get((r["part"], port), (None, None))[0 if C == "TT" else 1]
        out.append(dict(part=r["part"], port=port, model=r["early_model_ps"], delivered=round(dl, 1),
                        ratio=round(dl / r["early_model_ps"], 3) if r["early_model_ps"] else None,
                        residual=round(dl - iv, 1) if iv is not None else None))
    rr = [o["ratio"] for o in out if o["ratio"]]; rs = [o["residual"] for o in out if o["residual"] is not None]
    q = lambda v, p: sorted(v)[int(p * (len(v) - 1))] if v else None
    res[C] = dict(n=len(out), ratio_p10=q(rr, .1), ratio_p50=q(rr, .5), ratio_p90=q(rr, .9),
                  residual_p10=q(rs, .1), residual_p50=q(rs, .5), residual_p90=q(rs, .9), rows=out)
    print(C, {k: v for k, v in res[C].items() if k != "rows"})
print("early rows in tree", len(rows))
json.dump(res, open(OUT, "w"), indent=0)
