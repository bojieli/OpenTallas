#!/usr/bin/env python3
"""DIE-HBM-31: plan event d31s = BASE + OWNER 10-30 (B) SU lane ID strap alias.

u_su_Q0_lane_exp0 / u_su_Q1_lane_exp0 (types q_su00, q_su10 and their __physical_v1 copies) move from the literal-ID-0
master ot_hbm_su_static_pgslice_lg__lane_exp0 to the free-ID master ot_hbm_su_static_pgslice_lg__lane_exp0_id
(= the same sw2.py wrapper, lane_lane_id driven from the physical pin strap_lane_lane_id[10:0]). The plan declares
the physical strap (straps: strap_lane_lane_id, 11 b, value = bound source ID 0 / 16); the binder ties the native
lane_lane_id (tools/die_plan/parent_id_straps.py NATIVE_ALIAS). Pin table = old exp0 table + 11 strap pins on the
N face M5 at the lane_exp canon positions (x 415.848..431.208, same track grid; >= 0.336 um from every exp0 pin).
Every other module-keyed sidecar gets the new master next to the old one. Files written here are NEW files (rm then
write): no write through a hardlinked sidecar of BASE (Codex 10-29 metadata incident).
usage: mk_d31s.py BASE OUT"""
import json, os, shutil, subprocess, sys, hashlib
from pathlib import Path
base, out = Path(sys.argv[1]), Path(sys.argv[2])
OLD, NEW = "ot_hbm_su_static_pgslice_lg__lane_exp0", "ot_hbm_su_static_pgslice_lg__lane_exp0_id"
IDS = {"u_su_Q0_lane_exp0": 0, "u_su_Q1_lane_exp0": 16}
CANON = "cores/ot_hbm_su_static_pgslice_lg__lane_exp__canon_7cd691__440.64x207.36__canon__codex_g21.json"
if out.exists():
    sys.exit(f"{out} exists (refuse to overwrite)")
subprocess.check_call(["cp", "-al", str(base), str(out)])
def wnew(rel, obj):                      # break any hardlink before writing
    p = out / rel
    if p.exists() or p.is_symlink():
        p.unlink()
    p.write_text(json.dumps(obj, indent=1) + "\n")
rep = dict(lane="DIE-HBM-31", base=str(base), changes=[])
P = json.load(open(base / "die_plan.json"))
old_pf = None
for tn, t in P["partition_types"].items():
    for hc in t.get("hard_cores", []):
        if hc.get("module") == OLD:
            assert hc["inst"] in IDS, (tn, hc["inst"])
            assert not hc.get("straps") and not hc.get("parent_id_straps")
            old_pf = old_pf or hc["pins_file"]
            assert hc["pins_file"] == old_pf
            hc["module"] = NEW
            hc["straps"] = [dict(port="strap_lane_lane_id", width=11, value=IDS[hc["inst"]],
                                 note="OWNER 10-30 (B): physical strap_* alias of native lane_lane_id; parent-tied")]
            rep["changes"].append(dict(type=tn, inst=hc["inst"], module=NEW, strap_value=IDS[hc["inst"]]))
assert len(rep["changes"]) == 4, rep["changes"]
# pin table
pins = json.load(open(base / old_pf))
canon = [p for p in json.load(open(base / CANON)) if p["name"].startswith("lane_lane_id[")]
assert len(canon) == 11
nface = [p["x"] for p in pins if p["layer"] == "M5" and p["y"] > 207.0]
add = []
for p in canon:
    q = dict(p, name="strap_" + p["name"])
    d = min(abs(q["x"] - x) for x in nface)
    assert d >= 0.3, (q, d)
    assert abs((q["x"] / 0.048) % 1 - 0.5) < 1e-6
    add.append(q)
assert not any(p["name"].startswith("strap_") or p["name"].startswith("lane_lane_id") for p in pins)
new_pf = f"cores/{NEW}__440.64x207.36__d31s.json"
for tn, t in P["partition_types"].items():
    for hc in t.get("hard_cores", []):
        if hc.get("module") == NEW:
            hc["pins_file"] = new_pf
(out / "cores").is_dir() and not (out / "cores").is_symlink() or sys.exit("cores/ must be a real dir")
# cores/ is a cp -al directory: adding a NEW file is safe
wnew(new_pf, pins + add)
rep["pin_table"] = dict(old=old_pf, new=new_pf, pins_old=len(pins), pins_new=len(pins) + len(add),
                        strap_pins=[(p["name"], p["layer"], p["x"], p["y"]) for p in add])
# budget_owner labels
n_bo = 0
for L in P.get("lanes", []) + P.get("buses", []) if isinstance(P.get("lanes", []), list) else []:
    pass
def relabel(o):
    global n_bo
    if isinstance(o, dict):
        for k, v in o.items():
            if k == "budget_owner" and v == OLD:
                o[k] = NEW; n_bo += 1
            else:
                relabel(v)
    elif isinstance(o, list):
        for v in o:
            relabel(v)
relabel(P)
rep["budget_owner_relabelled"] = n_bo
wnew("die_plan.json", P)
# module-keyed sidecars
cm = json.load(open(base / "core_macros.json")); cm["cores"][NEW] = cm["cores"][OLD]; wnew("core_macros.json", cm)
en = json.load(open(base / "entries.json")); en[NEW] = en[OLD]; wnew("entries.json", en)
ce = json.load(open(base / "clock_entries.json")); n = 0
for tn, d in ce.items():
    if isinstance(d, dict):
        for inst, e in d.items():
            if isinstance(e, dict) and e.get("module") == OLD:
                e["module"] = NEW; n += 1
assert n == 4, n
wnew("clock_entries.json", ce)
pw = json.load(open(base / "pin_windows.json"))
extra = [dict(r, type=NEW) for r in pw["records"] if r.get("type") == OLD]
pw["records"] += extra; wnew("pin_windows.json", pw)
rep["sidecars"] = dict(core_macros="+NEW", entries="+NEW", clock_entries=n, pin_windows=len(extra))
for f in ("g0_report.json",):
    if (out / f).exists():
        (out / f).unlink()
rep["die_plan_sha256"] = hashlib.sha256((out / "die_plan.json").read_bytes()).hexdigest()
wnew("d31s_report.json", rep)
print(json.dumps({k: v for k, v in rep.items() if k != "changes"}, indent=1))
