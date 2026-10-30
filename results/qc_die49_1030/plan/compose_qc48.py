"""DIE-QC-49 plan_qc48 = plan_qc47 + one-block landing fix for slw_stm_v1__cle34a73c3 (COORD 12:2x ruling (3)).

Why: PLACE 3_3 failed 'OT_CLAND no legal nonoverlapping row/site in reserved band for
u_bound.u_cland_collect_rst_rl_1/_7_' (QC-KITS-Y 12:04). Four collector groups + reset copy + u_srl_2 share the
4.32x4.32 near() box around relays u_rrl_0..3 (460.08,837.0) and the x_sc_fw_i ring band [421.2,836.136,503.28,845.048]
covers its top 3.0 um. Fix: landing_contract.group_rects_um moves u_cland_collect_rst_rl_1 and _rst_rl_2 to one shared
9.72 um square directly below the relay point, clear of the ring band (1.656 um gap) and of the near() box rows
(0.36 um gap). Native 3_2_place_iop.odb probe: only LOCKED tapcells at x 453.384..453.492 (outside), no obstruction,
no placement blockage in the box. No outline/pin/relay/tap/RTL/cycle change; no neighbour change.
"""
import hashlib, json, sys
src, dst = sys.argv[1], sys.argv[2]
P = json.load(open(src))
t = P["partition_types"]["slw_stm_v1__cle34a73c3"]
lc = t["clock"]["landing_contract"]
assert "group_rects_um" not in lc
X, Y1 = 460.08, 834.48
box = [round(X - 4.86, 3), round(Y1 - 9.72, 3), round(X + 4.86, 3), Y1]
ring = lc["bands"]["x_sc_fw_i"]["rect_um"]
assert box[3] < ring[1] and box[3] < 837.0 - 2.16
lc["group_rects_um"] = {"u_cland_collect_rst_rl_1": box, "u_cland_collect_rst_rl_2": box}
P["note"] = P.get("note", "") + " | plan_qc48 (DIE-QC-49): plan_qc47 + slw_stm_v1__cle34a73c3 collector group_rects_um (rst_rl_1/rst_rl_2)"
open(dst, "w").write(json.dumps(P, indent=1) + "\n")
print(json.dumps(dict(src_sha256=hashlib.sha256(open(src, "rb").read()).hexdigest(),
                      dst_sha256=hashlib.sha256(open(dst, "rb").read()).hexdigest(),
                      type="slw_stm_v1__cle34a73c3", group_rects_um=lc["group_rects_um"], ring=ring), indent=1))
