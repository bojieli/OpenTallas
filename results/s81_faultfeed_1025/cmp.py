import json,sys,collections
A=json.load(open(sys.argv[1])); B=json.load(open(sys.argv[2]))
print("top keys diff", set(A)^set(B))
def idx(L,k="id"): return {x[k]:x for x in L}
for key in ("lanes",):
    a=idx(A[key]); b=idx(B[key])
    print(key, len(a), len(b), "added", sorted(set(b)-set(a)), "removed", sorted(set(a)-set(b)))
    ch=[k for k in a if k in b and a[k]!=b[k]]
    print("changed lanes", len(ch))
    fields=collections.Counter()
    for k in ch:
        for f in set(a[k])|set(b[k]):
            if a[k].get(f)!=b[k].get(f): fields[f]+=1
    print(" fields", fields)
    roles=collections.Counter(a[k].get("role") for k in ch); print(" roles", roles)
    nonfault=[k for k in ch if a[k].get("role") not in ("sid","vid")]
    print(" non-ring changed", len(nonfault), nonfault[:20])
pa=idx(A["partitions"],"name"); pb=idx(B["partitions"],"name")
print("parts", len(pa), len(pb), "removed", sorted(set(pa)-set(pb)), "added", sorted(set(pb)-set(pa)))
pc=[k for k in pa if k in pb and pa[k]!=pb[k]]; print("parts changed", len(pc))
fc=collections.Counter(f for k in pc for f in set(pa[k])|set(pb[k]) if pa[k].get(f)!=pb[k].get(f)); print(" fields",fc)
ta=A["partition_types"]; tb=B["partition_types"]
print("types", len(ta), len(tb), "removed", sorted(set(ta)-set(tb)), "added", sorted(set(tb)-set(ta)))
tc=[k for k in ta if k in tb and ta[k]!=tb[k]]; print("types changed", len(tc))
fc=collections.Counter(f for k in tc for f in set(ta[k])|set(tb[k]) if ta[k].get(f)!=tb[k].get(f)); print(" fields",fc)
print(" ft_slots changed", sorted(k for k in tc if ta[k].get("ft_slots")!=tb[k].get("ft_slots")))
print(" non-ft changed", sorted(k for k in tc if {f:v for f,v in ta[k].items() if f!="ft_slots"}!={f:v for f,v in tb[k].items() if f!="ft_slots"}))
