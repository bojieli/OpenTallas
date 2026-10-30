import json, sys
sys.path.insert(0, "tools/die_plan")
import schema as S, reset_tree as RT
side = json.load(open(sys.argv[1]))
Pb = S.Plan(json.load(open(sys.argv[2])), sys.argv[2]); Pw = S.Plan(json.load(open(sys.argv[3])), sys.argv[3])
n = lambda T: {r["q"]: (r["d"], tuple(round(v, 3) for v in r["xy"])) for r in T["relays"]}
for tn in sys.argv[4:]:
    s = n(side["collector"]["types"][tn]["tree"]) if tn in side["collector"]["types"] else None
    b = n(RT.for_type(Pb, tn)); w = n(RT.for_type(Pw, tn))
    print(tn, "sidecar==base", s == b if s else "no-collector", "base==w", b == w, len(b), len(w))
    if b != w:
        tb = {q: v[1] for q, v in b.items() if q.startswith("rst_n_t")}; tw = {q: v[1] for q, v in w.items() if q.startswith("rst_n_t")}
        print("  taps equal", tb == tw, [(q, tb.get(q), tw.get(q)) for q in sorted(set(tb) | set(tw)) if tb.get(q) != tw.get(q)][:8])
        sb = sorted(set(v[1] for v in b.values())); sw = sorted(set(v[1] for v in w.values()))
        print("  sites only base", [p for p in sb if p not in sw][:12]); print("  sites only w", [p for p in sw if p not in sb][:12])
