#!/usr/bin/env python3
"""DIE-KV-32 10-29 fix-only plan delta: give kv3_sys_SD/_v1 their exact x6 SerDes physical identity and supplies.

Applies Codex dd4cdbbc7's sys_SD/_v1 content (physical_inst/physical_master, origin/outline, LEF/LIB of the
results/kv_serdes_pg_event27 fixed-W views) and the VDDPHY_SW/VDDPHY_SE die PG domains to a KV plan.  Fails closed
unless the target's sys_SW/sys_SE placement, type outline and logical content (inst/module) equal the source's, each
domain rect equals the content outline mapped to die coordinates, and every domain io names a die io of the target.
Nothing else in the plan changes.  Usage: apply_serdes_phys.py TOOLS_DIE_PLAN PLAN_IN DELTA_JSON PLAN_OUT"""
import copy, json, sys

tools, src, delta_p, dst = sys.argv[1:5]
sys.path.insert(0, tools)
import schema as S  # noqa: E402

plan, delta = json.load(open(src)), json.load(open(delta_p))
out = copy.deepcopy(plan)
P = S.Plan(plan)
TYPE_PART = {"kv3_sys_SD": "sys_SW", "kv3_sys_SD_v1": "sys_SE"}
want = {}
for tn, contents in delta["contents"].items():
    t = out["partition_types"][tn]
    assert t["outline_um"] == [1900.8, 1036.8], (tn, t["outline_um"])
    old = t.get("contents", [])
    assert [(c["inst"], c["module"]) for c in old] == [(c["inst"], c["module"]) for c in contents], (tn, old)
    t["contents"] = copy.deepcopy(contents)
    (c,) = contents
    x0, y0 = c["origin_um"]; w, h = c["outline_um"]
    a, b = P.to_die(TYPE_PART[tn], (x0, y0)), P.to_die(TYPE_PART[tn], (x0 + w, y0 + h))
    want[tn] = [round(min(a[0], b[0]), 4), round(min(a[1], b[1]), 4), round(max(a[0], b[0]), 4), round(max(a[1], b[1]), 4)]
ios = {x.get("name") for x in (out["die"].get("io") or [])} if isinstance(out["die"].get("io"), list) else set(out["die"].get("io") or {})
doms = out["die"].setdefault("pg", {}).setdefault("domains", [])
names = {d["name"] for d in doms}
for d in delta["domains"]:
    tn = "kv3_sys_SD" if "SW" in d["name"] else "kv3_sys_SD_v1"
    assert [round(v, 4) for v in d["rect_um"]] == want[tn], (d["name"], d["rect_um"], want[tn])
    assert d["name"] not in names, f"domain {d['name']} already in plan"
    missing = [i for i in d.get("io", []) if i not in ios]
    assert not missing or not ios, f"domain {d['name']} io not in die io: {missing}"
    doms.append(copy.deepcopy(d))
errs = [e for e in S.validate(out) if "physical_" in e or "domain" in e or "sys_SD" in e]
assert not errs, errs[:5]
json.dump(out, open(dst, "w"), indent=1)
print(json.dumps(dict(types=sorted(delta["contents"]), domains=[d["name"] for d in delta["domains"]], rects=want,
                      die_io_checked=bool(ios))))
