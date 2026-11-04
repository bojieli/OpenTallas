#!/usr/bin/env python3
"""DIE-HBM-65 d44v part 9 (COORD 07:34 (2), 08:40 (4)). mk_p9.py PLAN_DIR TABLES_DIR XCAL_LANE1_MACROS.json

One-block plan event on PLAN_DIR (unpacked d44v):
  * oneclk tables (mk_oneclk.py outputs, kept in TABLES_DIR) for lane1, lane_exp canon and split3 ctl: pins_file repointed;
  * q2_hard_v8g__reduce table without u_reduce_in_flit[544:512]: bits unread by the RTL and dropped by the face shell, so the
    signed record has 1110 pins and the old table 1143 (design_unmatched);
  * core_macros.json rows of the file argument replace those of the plan (xcal central form, lane1 names under one clock).
No other row changes. Writes part9_event.json."""
import json, re, shutil, sys
from pathlib import Path
pd, td, macros = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
D = json.loads((pd / "die_plan.json").read_text()); ev = dict(schema="opentallas.hbm_plan_event.part9", moved={})
for t in sorted(td.glob("*__oneclk.json")):
    shutil.copyfile(t, pd / "cores" / t.name)
    old = "cores/" + t.name[: -len("__oneclk.json")] + ".json"; new = "cores/" + t.name; k = 0
    for ty in D["partition_types"].values():
        for c in ty.get("hard_cores") or []:
            if c.get("pins_file") == old: c["pins_file"] = new; k += 1
    if not k: raise SystemExit(f"no row uses {old}")
    ev["moved"][new] = k
Q = "cores/ot_hfd_coll_q2_hard_v8g__reduce__233.28x233.28__q_hub_u_hb_coll_Q_reduce__oneclk__codex_g21__centry"
T = json.loads((pd / (Q + ".json")).read_text())
keep = [p for p in T if not ((m := re.fullmatch(r"u_reduce_in_flit\[(\d+)\]", p["name"])) and int(m[1]) >= 512)]
if len(T) - len(keep) != 33: raise SystemExit(f"q2r drop {len(T) - len(keep)} != 33")
(pd / (Q + "__in512.json")).write_text(json.dumps(keep)); k = 0
for ty in D["partition_types"].values():
    for c in ty.get("hard_cores") or []:
        if c.get("pins_file") == Q + ".json": c["pins_file"] = Q + "__in512.json"; k += 1
if k != 2: raise SystemExit(f"q2r rows {k} != 2")
ev["moved"][Q + "__in512.json"] = k; ev["q2r_dropped"] = 33
(pd / "die_plan.json").write_text(json.dumps(D, indent=1) + "\n")
cm = json.loads((pd / "core_macros.json").read_text()); new = json.loads(macros.read_text())["cores"]; cm["cores"].update(new)
(pd / "core_macros.json").write_text(json.dumps(cm, indent=1) + "\n"); ev["core_macros"] = sorted(new)
(pd / "part9_event.json").write_text(json.dumps(ev, indent=1) + "\n"); print(json.dumps(ev)[:400])
