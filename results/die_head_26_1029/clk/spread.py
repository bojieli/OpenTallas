# DIE-HEAD-25: DIE-KV-26 spread.py recipe on HEAD hk4 regions (spine_regions.json part_region); raw OpenSTA arrivals and
# spice-scaled (x1.0485 TT / x1.0552 FF, 12.15b) per region.  usage: spread.py TAG REGIONS_JSON
import json, collections, sys
k, regf = sys.argv[1:3]
t = json.load(open(f"kit_{k}/kit/clock/tree.json")); taps = {x["port"]: x["part"] for x in t["taps"]}
reg = json.load(open(regf))["part_region"]
SC = {"TT": 1.0485, "FF": 1.0552}
out = {}
for c in ["TT", "FF"]:
    R = collections.defaultdict(list); slew = 0.0; allarr = []
    for l in open(f"out_{k}_{c}/arr_{c}.txt"):
        f = l.split()
        if f[0] == "T" and f[1] in taps:
            R[reg[taps[f[1]]]].append(float(f[2])); slew = max(slew, float(f[4])); allarr.append(float(f[2]))
    rs = sorted(((max(v) - min(v)), r2, len(v)) for r2, v in R.items())
    out[c] = dict(regions=len(rs), taps=sum(len(v) for v in R.values()), worst_raw=round(rs[-1][0], 2),
                  worst_scaled=round(rs[-1][0] * SC[c], 2), n_over_150_scaled=sum(a * SC[c] > 150 for a, _, _ in rs),
                  worst5=[(round(a, 1), r2, n) for a, r2, n in rs[-5:]], max_tap_slew=round(slew, 1),
                  insertion_min_max=[round(min(allarr), 1), round(max(allarr), 1)])
    print(k, c, json.dumps(out[c]))
json.dump(out, open(f"spread_{k}.json", "w"), indent=1)
