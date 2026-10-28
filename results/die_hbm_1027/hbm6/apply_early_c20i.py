#!/usr/bin/env python3
"""DIE-HBM-6: apply the CHECKED rows of HBM-CORE-LAT-2 early_taps.json (claude/hbm-core-lat-2-1028@2ec75de09e) to the
plan core taps (COORD 03:33: CHECKED view/probe rows only; model/proxy/old-kit rows keep 250/202.5).
Join: tap name -> the type's hard_cores[inst].module (the core master); fallback tap budget_owner.  MULTI-CLOCK rows take
the table's reg-weighted mean on the one plan entry tap (tap_rule) and are listed: per-pin taps need a per-pin plan
entry, which is owned by HBM-CORES-REBAL-1 (c).
    usage: apply_early_c20i.py PLAN_IN EARLY_TAPS_JSON PLAN_OUT REPORT_JSON"""
import collections, hashlib, json, pathlib, sys
P = json.loads(pathlib.Path(sys.argv[1]).read_text()); T = json.loads(pathlib.Path(sys.argv[2]).read_text())
rows = {r["module"]: r for r in T["rows"] if r["label"].startswith("CHECKED")}
hit, miss, multi = collections.Counter(), collections.Counter(), set()
for tn, t in P["partition_types"].items():
    hmod = {h["inst"]: h["module"] for h in t.get("hard_cores", [])}
    for tp in t.get("clock", {}).get("taps", []):
        if tp.get("kind") != "core":
            continue
        m = hmod.get(tp["name"], tp.get("budget_owner")); r = rows.get(m)
        if r is None:
            miss[m] += 1; continue
        tp["insertion_ps"], tp["insertion_ff_ps"] = float(r["insertion_ps"]), float(r["insertion_ff_ps"])
        tp["note"] = tp.get("note", "") + f" | DIE-HBM-6 early tap = core insertion (HBM-CORE-LAT-2 {r['label'][:40]})"
        hit[m] += 1
        if any("MULTI-CLOCK" in f for f in r.get("flags", [])):
            multi.add(m)
txt = json.dumps(P, indent=1); out = pathlib.Path(sys.argv[3]); out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(txt); (out.parent / "die_plan.sha256").write_text(hashlib.sha256(txt.encode()).hexdigest() + "  die_plan.json\n")
rep = dict(source="claude/hbm-core-lat-2-1028@2ec75de09e results/hbm_core_lat_2_1028/early_taps.json",
           checked_rows=len(rows), taps_set=sum(hit.values()), modules_set=len(hit), taps_kept=sum(miss.values()),
           modules_kept=len(miss), unused_checked_rows=sorted(set(rows) - set(hit)), multi_clock_mean_only=sorted(multi),
           set={m: [n, rows[m]["insertion_ps"], rows[m]["insertion_ff_ps"]] for m, n in sorted(hit.items())},
           plan_sha256=hashlib.sha256(txt.encode()).hexdigest())
pathlib.Path(sys.argv[4]).write_text(json.dumps(rep, indent=1) + "\n")
print(json.dumps({k: v for k, v in rep.items() if k != "set"}))
