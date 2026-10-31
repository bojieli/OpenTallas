#!/usr/bin/env python3
"""Transplant the DIE-KV-49-HG kv3_hg_v1 delta (plan_of_record/plan_c.json) into a plan COPY (e.g. the kit-wave
plan copy with absolute pins paths).  Copies core_pg_connect and the kind=core tap insertion_ps / insertion_ff_ps /
budget_owner / note of kv3_hg_v1, and binds hard_cores[].lef/lib to VIEWS_ROOT/<module>/ (absolute; a host copy of
hgclk_1030/views).  Fail-closed: the copy's kv3_hg_v1 cores (inst/module/site/outline/orient) and taps (name/kind/xy) must equal the
repo plan's (other differences are reported, not copied), and nothing outside kv3_hg_v1 changes.
Usage (repo root): python3 physical/die_plan/qwen_kvsys/hgclk_1030/apply_hgclk.py COPY.json VIEWS_ROOT OUT.json
"""
import copy, json, os, sys

TN = "kv3_hg_v1"
POR = "physical/die_plan/qwen_kvsys/plan_of_record/plan_c.json"
KEYS = ("insertion_ps", "insertion_ff_ps", "budget_owner", "note")


def strip(t):
    t = copy.deepcopy(t)
    t.pop("core_pg_connect", None)
    for h in t["hard_cores"]:
        for k in ("lef", "lib", "pins_file"):
            h.pop(k, None)
    for tp in t["clock"]["taps"]:
        for k in KEYS:
            tp.pop(k, None)
    return t


def main(src, views, out):
    new = json.load(open(POR))["partition_types"][TN]
    raw = open(src).read()
    plan = json.loads(raw)
    ref = copy.deepcopy(plan)
    t = plan["partition_types"][TN]
    geo = lambda x: ([(h["inst"], h["module"], h["origin_um"], h["outline_um"], h["orient"]) for h in x["hard_cores"]],
                     [(tp["name"], tp["kind"], tp["xy"]) for tp in x["clock"]["taps"]], x["clock"]["core_taps"])
    assert geo(t) == geo(new), "plan copy kv3_hg_v1 cores/taps differ from the repo plan"
    a, b = strip(t), strip(new)
    other = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
    other += sorted("clock." + k for k in set(a["clock"]) | set(b["clock"]) if a["clock"].get(k) != b["clock"].get(k))
    if other:   # reported, not copied: the copy keeps its own content outside the delta keys
        print("WARN plan copy kv3_hg_v1 differs from the repo plan outside the delta in:", ", ".join(other))
    t["core_pg_connect"] = new["core_pg_connect"]
    for h, n in zip(t["hard_cores"], new["hard_cores"]):
        assert h["inst"] == n["inst"] and h["module"] == n["module"]
        m = h["module"]
        h["lef"], h["lib"] = f"{views}/{m}/{m}.lef", f"{views}/{m}/{m}_tt.lib"
        assert os.path.isfile(h["lef"]) and os.path.isfile(h["lib"]) and os.path.isfile(f"{views}/{m}/signoff.json"), m
    for tp, n in zip(t["clock"]["taps"], new["clock"]["taps"]):
        assert tp["name"] == n["name"]
        for k in KEYS:
            if k in n:
                tp[k] = n[k]
    a, b = copy.deepcopy(ref), copy.deepcopy(plan)
    a["partition_types"].pop(TN); b["partition_types"].pop(TN)
    assert a == b
    open(out, "w").write(json.dumps(plan, indent=1) + "\n")


if __name__ == "__main__":
    main(*sys.argv[1:])
