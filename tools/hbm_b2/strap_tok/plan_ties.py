#!/usr/bin/env python3
"""TOK-HBM 10-25 strap token test, step 1: every strap_* tie the HBM die plan makes -> the old constant variant it replaces.

    python3 tools/hbm_b2/strap_tok/plan_ties.py PLAN.json VARIANTS.json OUT.json

PLAN.json     = the die plan (repo-relative, e.g. physical/die_plan/hbm_arch/B2n/die_plan.json): every hard core with a
                non-empty "straps" list is one parent tie (TIEHI/TIELO of a strap_* ID pin, owner option B 10-25).
VARIANTS.json = results/type_reduce3_1025/hbm/variants.json: strap master -> the old constant variants (old_view) and the
                strap values that reproduce each.
Fail-closed: every plan tie must equal exactly one variant's straps (same ports, same value, width = plan width), every
variant must be tied by >= 1 plan instance, and every master must be tied with >= 2 distinct values (TYPE-REDUCE-3).
OUT.json lists one bench per distinct (master, tie value) with the plan instances it covers."""
import collections, json, re, sys
plan_f, var_f, out_f = sys.argv[1:4]
plan, variants = json.load(open(plan_f)), json.load(open(var_f))
ties = []
for pt, t in sorted(plan.get("partition_types", {}).items()):
    for i, hc in enumerate(t.get("hard_cores", [])):
        if hc.get("straps"):
            ties.append(dict(partition_type=pt, index=i, inst=hc.get("inst"), master=hc["module"], straps=hc["straps"]))
err = []
bench = collections.OrderedDict()
for t in ties:
    vs = variants.get(t["master"])
    if vs is None:
        err.append(f"{t['partition_type']}/{t['inst']}: master {t['master']} has no variant list"); continue
    s = {}
    for x in t["straps"]:
        m = re.fullmatch(r"(\d+)'b([01]+)", str(x["value"]))
        if not x["port"].startswith("strap_") or not m or int(m.group(1)) != x["width"] or len(m.group(2)) != x["width"]:
            err.append(f"{t['partition_type']}/{t['inst']}: bad strap {x}"); continue
        s[x["port"]] = x["value"]
    hit = [v for v in vs if v["straps"] == s]
    if len(hit) != 1:
        err.append(f"{t['partition_type']}/{t['inst']}: tie {s} matches {len(hit)} variants of {t['master']}"); continue
    key = (t["master"], hit[0]["old_module"])
    b = bench.setdefault(key, dict(master=t["master"], old_module=hit[0]["old_module"], old_view=hit[0]["old_view"],
                                   straps=s, plan_instances=[]))
    b["plan_instances"].append(f"{t['partition_type']}/{t['inst']}")
per = collections.defaultdict(list)
for (m, o), b in bench.items():
    per[m].append(o)
for m, vs in variants.items():
    unused = sorted(set(v["old_module"] for v in vs) - set(per[m]))
    if unused:
        err.append(f"{m}: variants not tied by any plan instance: {unused}")
    if len(per[m]) < 2:
        err.append(f"{m}: only {len(per[m])} distinct plan tie values (need >= 2)")
res = dict(plan=plan_f, variants=var_f, plan_ties=len(ties), benches=list(bench.values()),
           per_master={m: dict(plan_instances=sum(len(bench[(m, o)]["plan_instances"]) for o in per[m]),
                               distinct_values=len(per[m])) for m in sorted(per)},
           errors=err, verdict="PASS" if not err and ties else "FAIL")
json.dump(res, open(out_f, "w"), indent=1)
print(json.dumps(dict(verdict=res["verdict"], plan_ties=len(ties), benches=len(bench), per_master=res["per_master"], errors=err[:8])))
sys.exit(0 if res["verdict"] == "PASS" else 1)
