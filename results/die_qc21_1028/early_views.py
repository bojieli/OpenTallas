"""DIE-QC-21: which core kits/views the 864 early core taps need. usage: early_views.py TOOLS PLAN STA_JSON"""
import json, sys, collections
sys.path.insert(0, sys.argv[1]); import schema as S
P = S.Plan(json.load(open(sys.argv[2])))
d = json.load(open(sys.argv[3]))
miss = d["corners"]["TT"]["core_insertion"].get("missing_taps") or []
print("listed missing", len(miss))
cnt = collections.Counter(); parts = collections.defaultdict(set); ex = {}
for p, pp in P.parts.items():
    for n, a, b, tp in S.core_taps(P, pp["type"]):
        key = (tp.get("name"), tp.get("kind"), tp.get("insertion_ps"), tp.get("insertion_ff_ps"), (tp.get("budget_owner") or "")[:40])
        cnt[(pp["type"], n, key)] += 1; parts[pp["type"]].add(p); ex[(pp["type"], n)] = tp
miss_parts = collections.Counter()
ms = set(miss)
for k, v in sorted(cnt.items(), key=str): print(v, k)
# which part types own the missing ports (t_<part>__<tap>)
pt = {p: pp["type"] for p, pp in P.parts.items()}
c2 = collections.Counter()
for m in miss:
    p, tap = m[2:].split("__")
    c2[(pt.get(p), tap)] += 1
print("missing by type", sorted(c2.items(), key=str))
t0 = next(iter(ex.values())); print("example contract:", json.dumps(t0)[:600] if not isinstance(t0, str) else t0)
