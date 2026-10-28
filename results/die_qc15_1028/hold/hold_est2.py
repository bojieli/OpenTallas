"""DIE-QC-15 FF hold ESTIMATE: per partition intra tap damage = max over taps (late + core FF insertion) - min(...),
declared model (202.5 everywhere, as the gate) vs the plan per-tap insertion_ff_ps (early taps = signed core views).
Port t_<part>__clk_c<k> = k-th core tap of the partition type clock.taps; other ports = glue/density taps (202.5)."""
import json, sys, re, collections, statistics as st
P = json.load(open(sys.argv[1])); taps = {t["port"]: t for t in json.load(open(sys.argv[2]))["taps"]}
parts = P["partitions"] if isinstance(P["partitions"], dict) else {p["name"]: p for p in P["partitions"]}
pt = P["partition_types"]
def ins_ff(port, part):
    m = re.search(r"__clk_c(\d+)$", port)
    if not m: return 202.5
    ty = parts[part]["type"]; cores = [t for t in pt[ty]["clock"].get("taps", []) if t.get("kind") == "core"]
    k = int(m.group(1))
    if k >= len(cores): return None
    t = cores[k]; return float(t.get("insertion_ff_ps", 0.81 * float(t.get("insertion_ps", 250))))
by = collections.defaultdict(list)
for p, t in taps.items(): by[t["part"]].append(p)
res = {}; skipped = 0
for part, ps in by.items():
    if len(ps) < 2 or part not in parts: continue
    a = [(taps[p]["late_ps"], ins_ff(p, part)) for p in ps]
    if any(x[1] is None for x in a): skipped += 1; continue
    d = [x[0] + 202.5 for x in a]; r = [x[0] + x[1] for x in a]
    res[part] = (max(d) - min(d), max(r) - min(r))
fam = collections.defaultdict(list)
for part, v in res.items(): fam[re.sub(r"^(sl|c)_[EW]\d_", r"\1_", part)].append(v)
print("parts", len(res), "skipped (core index beyond plan taps)", skipped)
for f, vs in sorted(fam.items(), key=lambda x: -max(v[0] for v in x[1]))[:12]:
    print("%-16s n=%3d declared max %6.1f med %6.1f | plan insertion max %6.1f med %6.1f" % (f, len(vs), max(v[0] for v in vs), st.median(v[0] for v in vs), max(v[1] for v in vs), st.median(v[1] for v in vs)))
w = max(res.items(), key=lambda x: x[1][1]); print("worst with plan insertion:", w[0], round(w[1][1], 1), "| est FF intra hold ~ %.0f (gate scale 250.43/218.8 + remainder 31.4)" % (-(w[1][1] * 250.43 / 218.8) - 31.4))
