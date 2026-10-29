#!/usr/bin/env python3
"""TOK-QC-1: count-aligned QC landing event for the ONE-QC RTL bind (METHODOLOGY 12.16a / 12.15a strap form).
= DIE-QC-4 compose_qc.py recipe (main clock_landing_plan.compose on main die_plan.json 54a1 + the 313-region map, which
gave the 98-type K2 -> K2b -> ev_a0meas event lineage) with ONE change: the region table is first annotated with the
count-aligned crossing bind (count_align_bind.annotate_table, strap_form=True: K/PAD are strap_* pins tied at the
parent, DEPTH per type), the KV DIE-KV-13/15 event recipe.  K comes from the DIE-QC die gate's bind_clock.json
(count_align_bind --from-ocv --parts ocv); K values are straps, so a newer gate (g15, ...) re-ties straps without a
type or RTL change.
usage: mk_ca_event.py REPO PLAN REGION_TABLE BIND_CLOCK OUT_DIR [forward_source]"""
import json, sys, hashlib
from pathlib import Path
R, PLAN, TAB, BC, OUT = map(Path, sys.argv[1:6]); FWD = sys.argv[6] if len(sys.argv) > 6 else "tap"
sys.path.insert(0, str(R / "tools/die_plan"))
import count_align_bind as CB, clock_landing_plan as LP, gen
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()[:12]
P = json.loads(PLAN.read_text()); T = json.loads(TAB.read_text()); B = json.loads(BC.read_text())
OUT.mkdir(parents=True, exist_ok=True)
tab = CB.annotate_table(T, B, strap_form=True)
(OUT / "regions_ca.json").write_text(json.dumps(tab, indent=1) + "\n")
plan, side = LP.compose(P, tab, plan_path=PLAN.resolve(), forward_source=FWD)
plan["note"] = plan.get("note", "") + (f" | TOK-QC-1 10-28: count-aligned strap-form landing event (main compose on die_plan {sha(PLAN)} + "
                                       f"region map {sha(TAB)} + DIE-QC gate bind_clock {sha(BC)}) for the ONE-QC RTL bind")
# hard-core pin tables are relative to the source plan dir: re-point them from the event dir (KV-15 recipe)
import os
npins = 0
for typ in plan["partition_types"].values():
    for h in typ.get("hard_cores", []):
        if h.get("pins_file") and not Path(h["pins_file"]).is_absolute():
            src = (PLAN.parent / h["pins_file"]).resolve(); assert src.exists(), src
            h["pins_file"] = os.path.relpath(src, OUT.resolve()); npins += 1
(OUT / "plan.json").write_text(json.dumps(plan, indent=1) + "\n"); (OUT / "sidecar.json").write_text(json.dumps(side, indent=1) + "\n")
gen.write_latency(plan, OUT / "latency", OUT / "plan.json")
st = CB.strap_ties(side["count_aligned"], plan); (OUT / "straps.json").write_text(json.dumps(st, indent=1) + "\n")
ca = side["count_aligned"]
print("COMPOSE", json.dumps(dict(types=len(plan["partition_types"]), parts=len(plan["partitions"]), lanes=len(plan["lanes"]),
      ports=len(side["ports"]), ca_ports=len(ca.get("ports", {})), straps=st.get("summary"),
      inputs=dict(plan=sha(PLAN), table=sha(TAB), bind_clock=sha(BC)), forward_source=FWD, pins_repointed=npins)))
