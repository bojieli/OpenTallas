#!/usr/bin/env python3
"""PATH-S81 10-26: fix the 9 G0C errors left on the B2 PHY-fit plan after the explicit-tap regeneration.
usage: fix_b2_g0c_1026.py SRC_ROOT BASE_PLAN PLAN_IN PLAN_OUT RECEIPT
1. bk_sel__t2_phy1026_bk_sel: hard cores u_sel.u_c / u_sel.u_g sat on a half 8.64-um lattice step (652.32, 1058.4);
   snap to the next lattice site AWAY from u_tx (656.64, 1062.72; keeps 17.28-um gaps, both inside the outline).
2. Early core clock taps of moved hard cores (bk_sel u_sel.u_c, gunit u_l5) still carried the BASE-plan absolute
   coordinates (outside the shrunk outline). Re-derive: tap = new core origin + (base tap - base core origin), i.e. the
   core's own clock-pin offset, unchanged. Insertion/budget fields untouched.
3. SerDes io windows whose bump_exclude_um is the die-corner stress square: sites = pitch sites outside the exclusion
   (die_io.count_sites; was the full-rect 1606). lk_EN3 no longer reaches the NE die corner (window ends 31064.2 of
   31950.72), so the corner square is not part of its window/PHY domain any more: drop bump_exclude_um/esd_um there
   (the corner square itself stays C4-free at die level -> PG owner bump map).
"""
import json, sys, os
root, base, pin, pout, rec = sys.argv[1:6]
sys.path.insert(0, os.path.join(root, "tools/die_plan"))
import die_io
B = json.load(open(base)); P = json.load(open(pin)); R = {"changes": []}
T, BT = P["partition_types"], B["partition_types"]
L = 8.64
def snap(tn, inst, new):
    hc = [h for h in T[tn]["hard_cores"] if h["inst"] == inst][0]
    assert abs(new[0] / L - round(new[0] / L)) < 1e-6 and abs(new[1] / L - round(new[1] / L)) < 1e-6
    R["changes"].append(dict(type=tn, inst=inst, origin_from=hc["origin_um"], origin_to=new)); hc["origin_um"] = new
snap("bk_sel__t2_phy1026_bk_sel", "u_bk_sel.u_sel.u_c", [656.64, 665.28])
snap("bk_sel__t2_phy1026_bk_sel", "u_bk_sel.u_sel.u_g", [1062.72, 665.28])
for tn, btn in [("bk_sel__t2_phy1026_bk_sel", "bk_sel__t2"), ("gunit__t1_phy1026_gunit", "gunit__t1")]:
    for tp in T[tn]["clock"]["taps"]:
        if tp.get("kind") != "core":
            continue
        inst = tp["name"]
        bo = [h for h in BT[btn]["hard_cores"] if h["inst"] == inst][0]["origin_um"]
        bt = [p for p in BT[btn]["clock"]["taps"] if p.get("kind") == "core" and p["name"] == inst][0]["xy"]
        no = [h for h in T[tn]["hard_cores"] if h["inst"] == inst][0]["origin_um"]
        new = [round(no[0] + bt[0] - bo[0], 4), round(no[1] + bt[1] - bo[1], 4)]
        w, h = T[tn]["outline_um"]; assert 0 < new[0] < w and 0 < new[1] < h, (tn, inst, new)
        R["changes"].append(dict(type=tn, core_tap=inst, xy_from=tp["xy"], xy_to=new, pin_offset=[bt[0]-bo[0], bt[1]-bo[1]]))
        tp["xy"] = new
doms = {d["name"]: d for d in P["die"]["pg"].get("domains", [])}
for wnd in P["die"]["io"]:
    ex = wnd.get("bump_exclude_um")
    if not ex:
        continue
    r = wnd["rect_um"]
    inside = all(e[0] >= r[0] - 1e-6 and e[1] >= r[1] - 1e-6 and e[2] <= r[2] + 1e-6 and e[3] <= r[3] + 1e-6 for e in ex)
    dn = "phy_" + wnd["part"]
    if not inside:
        R["changes"].append(dict(io=wnd["name"], dropped_corner_exclusion=ex, reason="window no longer reaches the die corner"))
        del wnd["bump_exclude_um"]
        if dn in doms:
            doms[dn]["bumps"].pop("exclude_um", None); doms[dn].pop("esd_um", None)
        continue
    left = die_io.count_sites(r, wnd["pitch_um"], ex)
    R["changes"].append(dict(io=wnd["name"], sites_from=wnd.get("sites"), sites_to=left, signals=wnd.get("signals")))
    assert left >= (wnd.get("signals") or 0)
    wnd["sites"] = left
json.dump(P, open(pout, "w")); json.dump(R, open(rec, "w"), indent=1)
print(json.dumps(R, indent=1))
