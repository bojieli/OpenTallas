#!/usr/bin/env python3
"""HBM-REFORM-B5 d44v part 33: split_p33.json for ot_hfd_coll_q2n2_body_core = ot_q2nf_rest (lower band, all 19 macros at their old rects) + ot_q2nf_qout (top band under the old dst_d pins).
    mk_spec.py PLAN_DIR OUT.json TILEBUS.json"""
import json, sys
d, out = sys.argv[1], sys.argv[2]
C = "ot_hfd_coll_q2n2_body_core"; W, H = 786.24, 743.04; TH, ST = 112.32, 8.64; RH = 622.08
assert abs(RH + ST + TH - H) < 1e-6
cm = json.load(open(d + "/core_macros.json"))["cores"][C]
mac = cm if isinstance(cm, list) else cm["macros"]
rest = [dict(name="u_fcore." + m["name"].removeprefix("u_fcore."), master=m["master"], orient=m.get("orient", "R0"), rect_um=m["rect_um"]) for m in mac]
assert len(rest) == 19 and all(m["rect_um"][3] <= RH - 8 for m in rest), [m["rect_um"] for m in rest if m["rect_um"][3] > RH - 8]
# clock entry of rest: the widest free x gap at mid height
ys = RH / 2; xs = sorted((m["rect_um"][0], m["rect_um"][2]) for m in rest if m["rect_um"][1] <= ys <= m["rect_um"][3])
gaps = [(b - a, (a + b) / 2) for a, b in zip([0] + [x[1] for x in xs], [x[0] for x in xs] + [W])]
rx = round(max(gaps)[1] / 4.32) * 4.32
sp = dict(core=C, sha="p33", part="p33", glue=C + "__p33glue.sv", conn=C + ".conn.json",
 subs=[dict(module="ot_q2nf_rest", cells=125000), dict(module="ot_q2nf_qout", cells=100000)],
 added_cycles="0 data cycles: the kit face flops are the flat qslots registers; select_fault / unavailable_fault +2 edges (sticky fault only). cycles/q2n2_split.tsv",
 keep_face=True,
 sub_face=dict(ot_q2nf_qout=dict(pin_d="N", captured="S", cap_slot="S", sink_slot="S", sink_select="S", lk_d="S", select_fault="S", unavailable_fault="S")),
 boundary_sub="u_fcore.u_core.u_r", hub_sub="u_fcore.u_core.u_r",
 layout={"u_fcore.u_core.u_r": dict(xy=[0.0, 0.0], wh=[W, RH]), "u_fcore.u_core.u_q": dict(xy=[0.0, RH + ST], wh=[W, TH])},
 clock_entry=dict(ot_q2nf_rest=[round(rx, 3), round(round(ys / 4.32) * 4.32, 3)], ot_q2nf_qout=[393.12, 56.16]),
 macros=dict(ot_q2nf_rest=rest))
json.dump([sp], open(out, "w"), indent=1); open(out, "a").write("\n")
print(sp["clock_entry"], len(rest))
