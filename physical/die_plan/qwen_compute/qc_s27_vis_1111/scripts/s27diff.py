"""s26 -> s27 diff: which top-level / per-type keys changed; reset-tree depth and collector cycles per changed type."""
import json, sys
a, b = (json.load(open(p)) for p in sys.argv[1:3])
sa, sb = (json.load(open(p)) for p in sys.argv[3:5])
top = [k for k in set(a) | set(b) if a.get(k) != b.get(k) and k != "partition_types"]
print("top-level keys changed:", top)
PA, PB = a["partition_types"], b["partition_types"]
changed = [t for t in PA if PA[t] != PB.get(t)]
print("types changed:", len(changed), "added/removed:", set(PA) ^ set(PB))


def paths(x, y, p=""):
    if isinstance(x, dict) and isinstance(y, dict):
        for k in set(x) | set(y):
            if x.get(k) != y.get(k):
                yield from paths(x.get(k), y.get(k), p + "." + k)
    elif isinstance(x, list) and isinstance(y, list) and len(x) == len(y) and p.endswith(("hard_cores", "ft_slots")):
        for i, (u, v) in enumerate(zip(x, y)):
            if u != v:
                yield from paths(u, v, p + "[]")
    else:
        yield p


for t in sorted(changed):
    ks = sorted(set(paths(PA[t], PB[t])))
    lc0, lc1 = PA[t]["clock"]["landing_contract"], PB[t]["clock"]["landing_contract"]
    d0, d1 = lc0["collector_tree"]["depth"], lc1["collector_tree"]["depth"]
    print(f"{t}: tree depth {d0}->{d1} root {lc0.get('collector_root_node')}->{lc1.get('collector_root_node')} keys {ks}")
ca, cb = sa["collector"]["types"], sb["collector"]["types"]
sc = [t for t in set(ca) | set(cb) if ca.get(t) != cb.get(t)]
print("sidecar collector types changed:", sorted(sc), "== plan types changed:", sorted(sc) == sorted(changed))
other = [k for k in set(sa) | set(sb) if k != "collector" and sa.get(k) != sb.get(k)]
okeys = [k for k in set(sa["collector"]) | set(sb["collector"]) if k != "types" and sa["collector"].get(k) != sb["collector"].get(k)]
print("sidecar other keys changed:", other, okeys)
for t in sorted(sc):
    print(" sidecar", t, sorted(k for k in set(ca[t]) | set(cb[t]) if ca[t].get(k) != cb[t].get(k)))
