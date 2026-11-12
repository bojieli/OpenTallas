import json, sys
R = "/srv/opentallas-scratch2/claude/die-s81-85/compose1111/out/"
a = json.load(open(R + "s87_ready11r/plan.json")); b = json.load(open(R + "s87_ready11p/plan.json"))
rep = json.load(open(R + "s87_ready11p/split_report.json"))
clone_of = {c["name"]: s["type"] for s in rep["splits"] for c in s["clones"]}
split = {s["type"] for s in rep["splits"]}
prob = []
A, B = a["partition_types"], b["partition_types"]
if set(B) != (set(A) - split) | set(clone_of): prob.append("type set")
for t in A:
    if t not in split and A[t] != B.get(t): prob.append(f"unsplit type changed {t}")
ALLOW = {"module", "param_base_type", "param_set", "note"}
for c, t in clone_of.items():
    Bc = json.loads(json.dumps(B[c]).replace(json.dumps(c)[1:-1], t))   # self-reference rename (clock.landing_contract.collector_tree.type) normalised
    Bc["module"], Bc["param_base_type"], Bc["param_set"], Bc["note"] = B[c]["module"], B[c]["param_base_type"], B[c]["param_set"], B[c]["note"]
    ks = [k for k in set(A[t]) | set(Bc) if A[t].get(k) != Bc.get(k)]
    bad = [k for k in ks if k not in ALLOW]
    if bad: prob.append(f"{c} differs from {t} in {bad}")
pa = {p["name"]: p for p in a["partitions"]}; pb = {p["name"]: p for p in b["partitions"]}
if list(pa) != list(pb): prob.append("partition order/set")
for n in pa:
    d = [k for k in set(pa[n]) | set(pb[n]) if pa[n].get(k) != pb[n].get(k)]
    if d != [] and d != ["type"]: prob.append(f"partition {n} keys {d}")
    if pa[n]["type"] != pb[n]["type"] and clone_of.get(pb[n]["type"]) != pa[n]["type"]: prob.append(f"partition {n} retype wrong")
top = [k for k in set(a) | set(b) if k not in ("partition_types", "partitions") and a.get(k) != b.get(k)]
sub = {}
for k in top:
    if isinstance(a.get(k), dict):
        sub[k] = {s: (len(json.dumps(a[k].get(s))), len(json.dumps(b[k].get(s)))) for s in sorted(set(a[k]) | set(b[k])) if a[k].get(s) != b[k].get(s)}
out = dict(problems=prob, top_keys_changed=top, sub=sub, split_types=len(split), clones=len(clone_of), n_types_a=len(A), n_types_b=len(B))
print(json.dumps(out, indent=1)[:3000]); json.dump(out, open(R + "s87_ready11p/eq_check.json", "w"), indent=1)
