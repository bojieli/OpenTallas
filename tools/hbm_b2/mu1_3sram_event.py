#!/usr/bin/env python3
"""TOK-HBM-1/TOK-HBM-2 plan event mu1-3sram (HBM d44q -> d44s) (OWNER 11-02 19:19 "agree with 3-SRAM layout", option A).
Retypes the 16 u_vmb_Q*_mu1 hard cores of q_hub_nw/q_hub_ne from hnx_vms_bank_q0_faces__vec6293 (4-SRAM r2048
grown bank, rq 18 b, clk_macro0..3) to hnx_vms_bank_q0_faces__vecd4ae (3-SRAM native bank = the module the
selected source already instantiates for every u_u_vmb_Q*_mu1).  Geometry is unchanged: same origin, orient and
270x403.92 outline; each mu1 instance keeps its own pin faces (its pins file minus the 14 pins that exist only on
the 4-SRAM bank: clk_macro3, rq0..4[17], dq/kq/wq0/wq1[281], pq[285], eg/xq/xq2[276]).  core_conns has no
connection on any of those pins (checked below), so no parent net changes.
usage: mu1_3sram_event.py BASE_PLAN_DIR OUT_DIR"""
import json, os, sys, hashlib, copy, collections
BASE, OUT = sys.argv[1:3]
OLD, NEW = "hnx_vms_bank_q0_faces__vec6293", "hnx_vms_bank_q0_faces__vecd4ae"
REWRITE = {"die_plan.json", "core_macros.json", "clock_entries.json", "pin_windows.json"}
os.makedirs(OUT + "/cores", exist_ok=True)
for f in os.listdir(BASE):
    if f in REWRITE or f == "cores": continue
    dst = os.path.join(OUT, f)
    if not os.path.lexists(dst): os.symlink(os.path.realpath(os.path.join(BASE, f)), dst)
for f in os.listdir(BASE + "/cores"):
    dst = os.path.join(OUT, "cores", f)
    if not os.path.lexists(dst): os.symlink(os.path.realpath(os.path.join(BASE, "cores", f)), dst)
J = lambda p: json.load(open(p))
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
plan = J(BASE + "/die_plan.json"); cm = J(BASE + "/core_macros.json"); ce = J(BASE + "/clock_entries.json")
pw = J(BASE + "/pin_windows.json"); cc = J(BASE + "/core_conns.json")
rep = {"event": "mu1-3sram", "owner_decision": "OWNER 2026-11-02 19:19 PST 'agree with 3-SRAM layout' (mu1 option A)",
       "base": BASE, "base_sha256": {f: sha(BASE + "/" + f) for f in sorted(REWRITE | {"core_conns.json"})},
       "old_module": OLD, "new_module": NEW, "changed_instances": [], "pins_files": {}}
# reference pin-name set of the 3-SRAM module = every NEW pins file in use
ref = None
for pt, v in plan["partition_types"].items():
    for hc in v.get("hard_cores", []):
        if hc.get("module") == NEW:
            s = {p["name"] for p in J(BASE + "/" + hc["pins_file"])}
            assert ref is None or s == ref, ("NEW pin sets differ", hc["pins_file"]); ref = s
assert ref, "no NEW instance in base"
rep["new_module_pins"] = len(ref)
pmap = {}
def strip(old_pf):
    if old_pf in pmap: return pmap[old_pf]
    pins = J(BASE + "/" + old_pf); names = {p["name"] for p in pins}
    drop = sorted(names - ref); assert ref <= names, ("old file lacks NEW pins", sorted(ref - names)[:5])
    keep = [p for p in pins if p["name"] in ref]
    stem = os.path.basename(old_pf)[len(OLD + "__"):]          # e.g. 270x403.92__canon__codex_g21.json
    new_pf = "cores/" + NEW + "__mu1s3__" + stem
    json.dump(keep, open(OUT + "/" + new_pf, "w"), indent=0)
    pmap[old_pf] = new_pf
    rep["pins_files"][old_pf] = {"new": new_pf, "sha256": sha(OUT + "/" + new_pf), "old_pins": len(pins),
                                 "new_pins": len(keep), "dropped": drop}
    return new_pf
# core_conns must not use any dropped pin on an OLD instance
mu1 = {}
for pt, v in plan["partition_types"].items():
    for hc in v.get("hard_cores", []):
        if hc.get("module") == OLD: mu1.setdefault(pt, set()).add(hc["inst"])
# The base plan carries NO core_conns entry for the 16 _mu1 banks (their clients are the open S-role ports of the
# 8SM->4-role fold); recorded so the event cannot silently drop a connection.
rep["core_conns_entries_on_old_instances"] = sum(1 for pt, insts in mu1.items() for inst in insts if cc.get(pt, {}).get(inst))
dropped_all = set()
for pt, v in plan["partition_types"].items():
    for hc in v.get("hard_cores", []):
        if hc.get("module") != OLD: continue
        old = copy.deepcopy(hc); new_pf = strip(hc["pins_file"])
        dropped_all |= set(rep["pins_files"][hc["pins_file"]]["dropped"])
        hc["module"] = NEW; hc["pins_file"] = new_pf
        hc["note"] = (hc.get("note", "") + " | TOK-HBM-2 mu1-3sram (event by TOK-HBM-1): 4-SRAM vec6293 -> 3-SRAM vecd4ae (OWNER 11-02 19:19 option A); same origin/orient/outline/faces, 14 4-SRAM-only pins dropped").strip(" |")
        rep["changed_instances"].append({"type": pt, "inst": hc["inst"], "orient": hc.get("orient", "R0"),
            "origin_um": hc["origin_um"], "outline_um": hc["outline_um"], "old_pins_file": old["pins_file"], "new_pins_file": new_pf})
    for t in v.get("clock", {}).get("taps", []):
        if t.get("budget_owner") == OLD:
            t["budget_owner"] = NEW; t["note"] = t.get("note", "") + " | mu1-3sram: budget owner vecd4ae"
# core_conns pin-level check against dropped names
hits = []
def scan(o, path):
    if isinstance(o, dict):
        for k, x in o.items(): scan(x, path + [k])
    elif isinstance(o, list):
        for i, x in enumerate(o): scan(x, path + [i])
    elif isinstance(o, str) and o in dropped_all: hits.append(path)
for pt, insts in mu1.items():
    for inst in insts: scan(cc.get(pt, {}).get(inst), [pt, inst])
assert not hits, ("core_conns uses dropped pins", hits[:5])
rep["core_conns_dropped_pin_hits"] = 0
isl = plan.get("clock", {}).get("mesh", {}).get("core_islands", {})
if OLD in isl:
    assert isl[OLD]["rects_um"] == isl[NEW]["rects_um"], "core island rects differ"
    isl[NEW]["instances"] = isl[NEW].get("instances", 0) + isl[OLD].get("instances", 0); del isl[OLD]
    rep["core_islands"] = "merged into NEW (identical rects)"
n = 0
for pt, ents in ce.items():
    for inst, e in ents.items():
        if isinstance(e, dict) and e.get("module") == OLD:
            e["module"] = NEW
            e["merged_clock_ports"] = [p for p in e.get("merged_clock_ports", []) if p not in dropped_all]
            e["source"] = e.get("source", "") + " | mu1-3sram: vecd4ae, clk_macro3 removed"; n += 1
rep["clock_entries_changed"] = n
for r in pw.get("records", []):
    if r.get("type") == OLD:
        old_pf = r["pins_file"]
        r["type"] = NEW; r["note"] = "mu1-3sram: counts recomputed after dropping the 4-SRAM-only pins; peaks stale (from " + old_pf + ")"
        pins = [p for p in J(BASE + "/" + old_pf) if p["name"] in ref]
        r["pins"] = r["pin_entries"] = len(pins)
        rep["pin_windows_record"] = {"old_pins_file": old_pf, "pins_now": len(pins)}
old_cm = cm["cores"].pop(OLD)
rep["core_macros_removed"] = {"macros": old_cm.get("macros"), "outline_um": old_cm.get("outline_um")}
rep["core_macros_new"] = [m["name"] for m in cm["cores"][NEW]["macros"]]
json.dump(plan, open(OUT + "/die_plan.json", "w"))
json.dump(cm, open(OUT + "/core_macros.json", "w"), indent=1)
json.dump(ce, open(OUT + "/clock_entries.json", "w"), indent=1)
json.dump(pw, open(OUT + "/pin_windows.json", "w"), indent=1)
rep["new_sha256"] = {f: sha(OUT + "/" + f) for f in sorted(REWRITE)}
rep["n_instances"] = len(rep["changed_instances"]); rep["dropped_pins"] = sorted(dropped_all)
mods = collections.Counter(hc.get("module") for v in plan["partition_types"].values() for hc in v.get("hard_cores", []))
rep["vms_modules_after"] = {k: c for k, c in mods.items() if "vms_bank" in str(k)}
json.dump(rep, open(OUT + "/mu1_3sram_event_report.json", "w"), indent=1)
print("instances", rep["n_instances"], "pins files", len(pmap), "die_plan", rep["new_sha256"]["die_plan.json"][:12])
