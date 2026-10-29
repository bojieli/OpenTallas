# DIE-KV-23: structural diff of the new event plan vs the DIE-KV-19 event plan of record (pins_file compared by resolved content sha).
import json, sys, hashlib
from pathlib import Path
from collections import Counter
A, B = Path(sys.argv[1]), Path(sys.argv[2])
a, b = json.load(open(A)), json.load(open(B))
def sha(base, pf): return hashlib.sha256((base.parent / pf).read_bytes()).hexdigest()[:16]
def norm(p, base):
    p = json.loads(json.dumps(p))
    for t in p["partition_types"].values():
        for h in t.get("hard_cores", []):
            if h.get("pins_file"): h["pins_file"] = sha(base, h["pins_file"])
    p.pop("note", None); return p
a, b = norm(a, A), norm(b, B)
print("top keys diff", sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k)))
ta, tb = a["partition_types"], b["partition_types"]
print("types", len(ta), len(tb), "only old", sorted(set(ta) - set(tb))[:10], "only new", sorted(set(tb) - set(ta))[:10])
pa = {x["name"]: x for x in a["partitions"]}; pb = {x["name"]: x for x in b["partitions"]}
ch = Counter()
for n in pa:
    for k in set(pa[n]) | set(pb[n]):
        if pa[n].get(k) != pb[n].get(k): ch[k] += 1
print("partition field changes", dict(ch))
tc = Counter()
for t in set(ta) & set(tb):
    for k in set(ta[t]) | set(tb[t]):
        if ta[t].get(k) != tb[t].get(k): tc[k] += 1
print("common type field changes", dict(tc))
