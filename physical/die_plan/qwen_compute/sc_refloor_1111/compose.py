"""SC-REFLOOR-1: compose a plan = BASE + per-type partition_types records taken from variant plans.
usage: compose.py BASE.json OUT.json DELTA.json TYPE=VARIANT.json ...  (DELTA lists type, source plan sha, changed keys)"""
import hashlib, json, sys
base, out, dout = sys.argv[1:4]
raw = open(base, "rb").read()
P = json.loads(raw)
rows = []
cache = {}
for spec in sys.argv[4:]:
    tn, _, vp = spec.partition("=")
    if vp not in cache:
        r = open(vp, "rb").read()
        cache[vp] = (json.loads(r), hashlib.sha256(r).hexdigest())
    V, vsha = cache[vp]
    old, new = P["partition_types"][tn], V["partition_types"][tn]
    keys = sorted(k for k in set(old) | set(new) if old.get(k) != new.get(k))
    sub = []
    if old.get("clock") != new.get("clock"):
        sub = sorted(k for k in set(old["clock"]) | set(new["clock"]) if old["clock"].get(k) != new["clock"].get(k))
    assert set(keys) <= {"ft_slots", "clock", "hard_cores", "count_straps"}, keys
    P["partition_types"][tn] = new
    rows.append(dict(type=tn, source=vp, source_sha256=vsha, changed=keys, clock_changed=sub))
s = json.dumps(P, indent=1)
open(out, "w").write(s)
sha = hashlib.sha256(s.encode()).hexdigest()
json.dump(dict(tool="SC-REFLOOR-1 compose.py", base_sha256=hashlib.sha256(raw).hexdigest(), plan_sha256=sha, types=rows),
          open(dout, "w"), indent=1)
for r in rows:
    print(r["type"], r["changed"], r["clock_changed"])
print("sha256", sha[:12])
