"""per-type gen_phys export lines that s26 changes (tap affinity / post merge / strip rows)"""
import json, sys, os, collections
repo, a, b = sys.argv[1:4]
sys.path.insert(0, os.path.join(repo, "tools/die_plan"))
import gen_phys as GP
A, B = json.load(open(a)), json.load(open(b))
out = collections.OrderedDict()
for tn in sorted(B["partition_types"]):
    ta, tb = A["partition_types"][tn], B["partition_types"][tn]
    ea = GP.tap_pair_affinity_exports(ta) + GP.tap_post_merge_exports(ta) + [f"STRIP_ROWS={GP._cland_strip_rows(A['budgets'], tn)}"]
    eb = GP.tap_pair_affinity_exports(tb) + GP.tap_post_merge_exports(tb) + [f"STRIP_ROWS={GP._cland_strip_rows(B['budgets'], tn)}"]
    if ea != eb:
        out[tn] = sorted(set(eb) - set(ea))
c = collections.Counter(tuple(v) for v in out.values())
print(len(out), "types with changed exports")
for k, v in c.most_common(): print(v, list(k))
