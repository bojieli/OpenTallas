#!/usr/bin/env python3
"""DIE-HBM-66 d44v part 10 (COORD 09:16 (2)): fused host program conservative outline. mk_p10.py PLAN_DIR
Width 207.36 -> 276.48 um, height kept: 35832 um2, fill 0.43 (1273 std + 14194 macro) against 0.65. All growth is on E (69.12 um):
W holds L9x1 stage 10 bit sites (x up to 747.36), E is free, so origin stays. Every pin, both SRAMs and the clock island keep core and
die position and no parent wire moves. Slot room, including actual bit sites, read in part10_event.json. No other row changes."""
import json, sys
from pathlib import Path
pd = Path(sys.argv[1]); DX = 0.0; M = "ot_hnx_fused_host_program"; I = "u_mu_fused_program"
OLD = "cores/ot_hnx_fused_host_program__207.36x129.6__c25b__centry"; NEW = "cores/ot_hnx_fused_host_program__276.48x129.6__c25b__centry__p10"
D = json.loads((pd / "die_plan.json").read_text()); R = D["partition_types"]["root"]
n = 0
for key in ("hard_cores", "contents"):
    for c in R[key]:
        if c.get("inst") == I:
            assert c["origin_um"] == [734.4, 5339.52] and c["outline_um"] == [207.36, 129.6], c
            c["outline_um"] = [276.48, 129.6]; n += 1
            if key == "hard_cores": assert c["pins_file"] == OLD + ".json"; c["pins_file"] = NEW + ".json"
assert n == 2
ox0, ox1, oy0, oy1 = 734.4, 1010.88, 5339.52, 5469.12
hits = []
for key in ("hard_cores", "contents"):
    for c in R[key]:
        if c.get("inst") == I: continue
        x, y = c["origin_um"]; w, h = c["outline_um"]
        if x < ox1 and x + w > ox0 and y < oy1 and y + h > oy0: hits.append([key, c.get("inst")])
for s in R["ft_slots"]:
    for x, y in s.get("regs_um") or []:
        if ox0 <= x <= ox1 and oy0 <= y <= oy1: hits.append(["ft_slots", s["name"], x, y])
    cw, ch = s.get("bit_site_cell_um") or [0, 0]
    for g, st in enumerate(s.get("bit_sites_um") or []):
        k = sum(1 for x, y in st if x < ox1 and x + cw > ox0 and y < oy1 and y + ch > oy0)
        if k: hits.append(["bit_sites", s["name"], g, k])
for c in R["channels"]:
    r = c["rect_um"]
    if r[0] < ox1 and r[2] > ox0 and r[1] < oy1 and r[3] > oy0: hits.append(["channels", r])
for s in R["internal_stations"]:
    xy = s.get("origin_um") or s.get("xy_um") or s.get("at_um")
    if xy and ox0 <= xy[0] <= ox1 and oy0 <= xy[1] <= oy1: hits.append(["internal_stations", s.get("name") or s.get("inst")])
P = json.loads((pd / (OLD + ".json")).read_text())
for p in P: p["x"] = round(p["x"] + DX, 3)
(pd / (NEW + ".json")).write_text(json.dumps(P))
cm = json.loads((pd / "core_macros.json").read_text()); r = cm["cores"][M]
r["outline_um"] = [276.48, 129.6]
for m in r["macros"]:
    a = m["rect_um"]; m["rect_um"] = [round(a[0] + DX, 3), a[1], round(a[2] + DX, 3), a[3]]
r["basis"] = "DIE-HBM-66 part 10 conservative outline (COORD 09:16 (2)): +69.12 um on E, same SRAMs and pins at the same die position; " + r["basis"]
for k, v in list(r.items()):
    if "island" in k and isinstance(v, list) and len(v) == 4: r[k] = [round(v[0] + DX, 3), v[1], round(v[2] + DX, 3), v[3]]
ce = json.loads((pd / "clock_entries.json").read_text()); e = ce["root"][I]
e["xy_um"] = [round(e["xy_um"][0] + DX, 3), e["xy_um"][1]]; a = e["island_um"]; e["island_um"] = [round(a[0] + DX, 3), a[1], round(a[2] + DX, 3), a[3]]
(pd / "clock_entries.json").write_text(json.dumps(ce, indent=1) + "\n")
(pd / "die_plan.json").write_text(json.dumps(D, indent=1) + "\n"); (pd / "core_macros.json").write_text(json.dumps(cm, indent=1) + "\n")
ev = dict(schema="opentallas.hbm_plan_event.part10", core=M, inst=I, outline_um=[[207.36, 129.6], [276.48, 129.6]], origin_um=[734.4, 5339.52],
          fill=[0.65, 0.43], pins=len(P), slot_hits=hits, note="Pins keep their die position: parent wires unchanged")
(pd / "part10_event.json").write_text(json.dumps(ev, indent=1) + "\n"); print(json.dumps(ev))
