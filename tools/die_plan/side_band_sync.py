#!/usr/bin/env python3
# S81-LEAF-PLAN: copy each plan landing band (collector_local_sources[].band and landing_contract.bands) onto the sidecar
# collector copy (local_sources[].band only: the run_bind sync compares that copy) when the record names match and any key but rect_um differs, so the run_bind sidecar sync sees only equal
# band semantics. usage: PLAN SIDECAR OUT_SIDECAR
import copy, json, sys
p = json.load(open(sys.argv[1])); s = json.load(open(sys.argv[2])); n = 0; ts = set()
for tn, t in p["partition_types"].items():
    lc = (t.get("clock") or {}).get("landing_contract") or {}
    st = ((s.get("collector") or {}).get("types") or {}).get(tn)
    if not st: continue
    a, b = lc.get("collector_local_sources") or [], st.get("local_sources") or []
    if len(a) == len(b):
        for x, y in zip(a, b):
            nr = lambda d: {k: v for k, v in d.items() if k != "rect_um"}
            if x.get("name") == y.get("name") and isinstance(x.get("band"), dict) and isinstance(y.get("band"), dict) \
                    and nr(x["band"]) != nr(y["band"]):
                y["band"] = copy.deepcopy(x["band"]); n += 1; ts.add(tn)
json.dump(s, open(sys.argv[3], "w"), indent=1)
print("synced", n, "band copies in", len(ts), "types:", " ".join(sorted(ts)[:20]))
