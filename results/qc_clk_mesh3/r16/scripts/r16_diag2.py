import json, sys
sys.path.insert(0, "/w/die_plan")
import qc_clk_mesh3 as M3
ap = __import__("argparse").ArgumentParser(); M3.add_common(ap)
a = ap.parse_args()
a.no_spine, a.top_w, a.top_m, a.top_reach, a.islands, a.feed, a.lanes = True, "16w", 2, 450.0, "type", "periodic", "vss"
B = M3.build(a, M3.Stage(a.stage))
by = {n["tag"]: n for n in B["top_nodes"]}
bad = sorted((n for n in B["top_nodes"] if abs(n.get("imbalance_TT", 0.0)) > 5), key=lambda n: -abs(n["imbalance_TT"]))
for n in bad[:12]:
    print(n["tag"], [round(v,1) for v in n["xy"]], "imbTT", n["imbalance_TT"], "kids", [(k, [round(v,1) for v in by[k]["xy"]] if k in by else None, round(by[k]["T"]["TT"],1) if k in by else None) for k in n["kids"]])
print(len(bad))
for ct in B["ctrees"][:3]: print({k: (v if k!="nodes" else len(v)) for k,v in ct.items()})
