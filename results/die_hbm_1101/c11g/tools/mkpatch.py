#!/usr/bin/env python3
"""DIE-HBM-57 c11G: patch = every ft_slot of plan G that differs from the S11 base (Codex 871748099 stations compose) +
changed latency rows; apply_patch(base) reproduces G (verified by sha of canonical json)."""
import json, sys, hashlib, gzip
base_p, new_p, out = sys.argv[1:4]
b = json.load(open(base_p)); n = json.load(open(new_p))
slots, lat = {}, {}
for t, tn in n["partition_types"].items():
    tb = b["partition_types"][t]
    sb = {s["name"]: s for s in tb.get("ft_slots", [])}
    for s in tn.get("ft_slots", []):
        if sb.get(s["name"]) != s: slots.setdefault(t, {})[s["name"]] = s
    other = {k for k in set(tn) | set(tb) if k != "ft_slots" and tn.get(k) != tb.get(k)}
    assert not other, (t, other)
for k in set(n) | set(b):
    if k not in ("partition_types", "latency"): assert n.get(k) == b.get(k), k
for l, r in n["latency"]["lanes"].items():
    if b["latency"]["lanes"].get(l) != r: lat[l] = {"old": b["latency"]["lanes"].get(l), "new": r}
canon = lambda d: hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()
def apply(base, p):
    d = json.loads(json.dumps(base))
    for t, ss in p["replace_slots"].items():
        for i, s in enumerate(d["partition_types"][t]["ft_slots"]):
            if s["name"] in ss: d["partition_types"][t]["ft_slots"][i] = ss[s["name"]]
    for l, r in p["replace_latency_lanes"].items(): d["latency"]["lanes"][l] = r["new"]
    return d
p = {"schema": "opentallas.hbm_c11g_patch.v1", "base_sha256_file": hashlib.sha256(open(base_p, "rb").read()).hexdigest(),
     "base_canon_sha256": canon(b), "new_canon_sha256": canon(n),
     "replace_slots": slots, "replace_latency_lanes": lat}
assert canon(apply(b, p)) == canon(n)
with gzip.open(out, "wt") as f: json.dump(p, f)
print("slots", {t: sorted(v) for t, v in slots.items()}); print("latency", {l: (r["old"]["cycles"], r["new"]["cycles"]) for l, r in lat.items()})
