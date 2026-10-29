#!/usr/bin/env python3
"""TOK-QC-2 (from TOK-QC-1 mk_ca_event.py): count-aligned QC landing event for the ONE-QC RTL bind (METHODOLOGY 12.16a / 12.15a strap form).
= DIE-QC-4 compose_qc.py recipe (main clock_landing_plan.compose on main die_plan.json 54a1 + the 313-region map, which
gave the 98-type K2 -> K2b -> ev_a0meas event lineage) with ONE change: the region table is first annotated with the
count-aligned crossing bind (count_align_bind.annotate_table, strap_form=True: K/PAD are strap_* pins tied at the
parent, DEPTH per type), the KV DIE-KV-13/15 event recipe.  K comes from the DIE-QC die gate's bind_clock.json
(count_align_bind --from-ocv --parts ocv); K values are straps, so a newer gate (g15, ...) re-ties straps without a
type or RTL change.
TOK-QC-2 change: the gate bind_clock first takes the PAIRED-DIRECTION rule (physical/die_plan/qwen_compute/bind/
ca_pair_rule.py: both directions of each collective relay pair RS_j get the same count) and is re-verified
(count_align_bind.verify: identity, loops, ring guards >= 100 ps) before annotate_table.
usage: mk_ca_event.py REPO PLAN REGION_TABLE BIND_CLOCK OUT_DIR [forward_source]"""
import json, sys, hashlib
from pathlib import Path
R, PLAN, TAB, BC, OUT = map(Path, sys.argv[1:6]); FWD = sys.argv[6] if len(sys.argv) > 6 else "tap"
sys.path.insert(0, str(R / "tools/die_plan"))
import count_align_bind as CB, clock_landing_plan as LP, gen
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()[:12]
P = json.loads(PLAN.read_text()); T = json.loads(TAB.read_text()); B = json.loads(BC.read_text())
# TOK-QC-2 recorded plan delta (ASK 21:14 DEFAULT, DIE-QC-24 to adopt): the 12 plan fault hops sl_*_st_a.flt_o ->
# sl_*_fw.flt_st_a_i have no RTL counterpart (the bound st_a fault u_r0.fault feeds u_ctl.stn_fault inside the slice;
# the bound fw leaf u_fdn has no fault pin) -> dropped with their lanes and the two plan-generated u_pstn buses.
import os, re
DROP = []
if os.environ.get("TOKQC2_DROP_FLT_ST_A"):
    DROP = [x["id"] for x in P["ports"] if re.fullmatch(r"sl_[EW]\d_st_a__flt__0", x["id"])
            and x["dst"]["bus"] == "flt_st_a_i" and x["src"]["bus"] == "flt_o"]
    assert len(DROP) == 12, DROP
    P["ports"] = [x for x in P["ports"] if x["id"] not in DROP]
    P["lanes"] = [l for l in P["lanes"] if not set(l["ports"]) & set(DROP)]
    tp = {x["name"]: x["type"] for x in P["partitions"]}
    for part, bus in [(r, "flt_st_a_i") for r in {re.sub("st_a__flt__0", "fw", d) for d in DROP}] + \
                     [(r, "flt_o") for r in {re.sub("__flt__0", "", d) for d in DROP}]:
        t = P["partition_types"][tp[part]]
        t["buses"] = [b for b in t["buses"] if b["name"] != bus]
    T["ports"] = [r for r in T["ports"] if r["port"] not in DROP]
    dl = {re.sub(r"__0$", "", d) for d in DROP}
    for k in dl:
        P["latency"]["lanes"].pop(k, None)
    def _prune(o):
        if isinstance(o, list):
            o[:] = [x for x in o if not (isinstance(x, dict) and any(str(x.get("id", "")).endswith(d) for d in DROP))]
            for x in o:
                _prune(x)
        elif isinstance(o, dict):
            for x in o.values():
                _prune(x)
    _prune(P["clock"])
    assert not any(d in json.dumps(P) for d in DROP), "dropped port still referenced"
    print("PLAN_DELTA dropped", len(DROP), "ports:", DROP[:3], "...")
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(R / "physical/die_plan/qwen_compute/bind"))
import ca_pair_rule as PR
pair_rec = PR.apply(B, T)
v = CB.verify(B, samples=500)
if v["identity_and_loop_errors"] or v["sim_window_violations"] or v["sim_below_need"]:
    sys.exit(f"pair rule broke the CA bind: {v}")
B.setdefault("report", {})["pair_rule"] = dict(pairs=pair_rec, verify=v)
(OUT / "bind_clock_paired.json").parent.mkdir(parents=True, exist_ok=True)
(OUT / "bind_clock_paired.json").write_text(json.dumps(B, indent=1) + "\n")
print("PAIR", json.dumps(dict(pairs=[dict(pair=r["pair"], chains=r["chains"], target=r["target"], steps=len(r["steps"])) for r in pair_rec],
      verify={k: v[k] for k in ("identity_and_loop_errors", "sim_window_violations", "sim_min_margin_low_ps", "sim_min_margin_high_ps")})))
tab = CB.annotate_table(T, B, strap_form=True)
(OUT / "regions_ca.json").write_text(json.dumps(tab, indent=1) + "\n")
plan, side = LP.compose(P, tab, plan_path=PLAN.resolve(), forward_source=FWD)
plan["note"] = plan.get("note", "") + (f" | TOK-QC-2 10-28: count-aligned strap-form landing event + CA pair rule (main compose on die_plan {sha(PLAN)} + "
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
