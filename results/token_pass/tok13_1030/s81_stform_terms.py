"""TOK-13: S81 station-form (DIE-S81-36 claude/die-s81-36-stform-1030@90ba64737ef, plan 42b082ebcc8c) vs its base
event3 plan bcfcb4e1737e (merge-base 3928a54d881) and main a2c105604e3c: composer lane terms
(tools/s81_dv/tokfunc/compose_tok_ds.py _lane_terms, unchanged; TOK-9 method) + per-lane deltas by class."""
import json, sys, re, collections
sys.path[:0] = ["tools/s81_dv/tokfunc", "tools/s81_dv", "tools"]
import compose_tok_ds as C
plans = {"base_bcfcb4e1": "/tmp/tok13_s81_base.json", "main_a2c10560": "/tmp/tok13_s81_main.json",
         "stform_42b082eb": "/tmp/tok13_s81_stform.json"}
out = {"terms": {}, "delta": {}}
L = {}
for k, p in plans.items():
    L[k] = json.load(open(p))["latency"]["lanes"]
    lat = {"lanes": L[k]}
    C.lane_table = lambda lat=lat: (lat, "x")
    t = C._lane_terms(lambda pat: C.lanes(pat))
    out["terms"][k] = {n: dict(cycles=v["cycles"], lanes=v["lanes"]) for n, v in t.items()}
    print(k, {n: v["cycles"] for n, v in t.items()})
b, s = L["base_bcfcb4e1"], L["stform_42b082eb"]
ch = {n: (b[n]["cycles"], s[n]["cycles"]) for n in s if n in b and b[n]["cycles"] != s[n]["cycles"]}
cls = collections.Counter(n.split("__")[0] for n in ch)
print("changed", len(ch), dict(cls), "sum", sum(v[1]-v[0] for v in ch.values()), "max", max(v[1]-v[0] for v in ch.values()))
for c in sorted(cls):
    m = {n: v for n, v in ch.items() if n.split("__")[0] == c}
    top = sorted(m.items(), key=lambda kv: -kv[1][1])[:5]
    allc = [v["cycles"] for n, v in s.items() if n.split("__")[0] == c]
    print(" ", c, len(m), "max new", max(v[1] for v in m.values()), "class max base", max(v["cycles"] for n, v in b.items() if n.split("__")[0] == c), "stform", max(allc), top)
out["delta"] = {n: dict(old=v[0], new=v[1]) for n, v in ch.items()}
json.dump(out, open(sys.argv[1], "w"), indent=1)
