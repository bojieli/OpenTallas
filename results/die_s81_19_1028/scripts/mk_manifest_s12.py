#!/usr/bin/env python3
"""DIE-S81-19: asbuilt_b178_coll_s12.json = asbuilt_b178_coll_s11.json (TOK-S81-1) +
 (1) clock_landing_table = the plan_s12 composed sidecar (collector rooted at seqhost, actual S81 observer);
 (2) the PD7d observer opt-in, copied verbatim from asbuilt_b178_coll_pd7d.json: define S81_HOSTB_LAND_OBS, dissolve
     dsdv_hostb_seqhost_mux, file dsdv_mu_hwin.sv, straps one level down (u_seqhost.u_seqhost.*, u_seqhost.u_source.select_hbe);
 (3) substitute_inst: every as-built ot_v41_rom_elem_q_qxpq_w10 ROM element (72 frames x 12 = 864) -> the plan master
     ot_v41_rom_elem_q_qxpq_w10_gb (S81-QX-GB; ports = master minus input xs_sv, recorded variant_removed, never tied).
     Paths are exact per frame variant (col_h10 / col_h9 rows hold dsfd_bf_front_roots at other u_e indices).
usage: mk_manifest_s12.py BIND_DIR FRAMES_TXT SIDECAR_REL OUT"""
import json, sys, re
B, frames_txt, side_rel, out = sys.argv[1:5]
a = json.load(open(f"{B}/asbuilt_b178_coll_s11.json"))
pd = json.load(open(f"{B}/asbuilt_b178_coll_pd7d.json"))
# (3) element indices per row module (rtl/dsrom_sys/s81_dv/frame_lp/plan/col_h{10,9}_l4_lp_plan_kit.sv, the files the bind elaborates)
IDX = {"col_h10": {0: [0, 2, 3, 4], 1: [6, 7, 8, 9], 2: [11, 12, 13, 14]},
       "col_h9": {0: [0, 1, 2, 3], 1: [5, 6, 7, 9], 2: [10, 11, 12, 14]}}
fr = {"col_h10": [], "col_h9": []}
for line in open(frames_txt):
    m, inst = line.split()
    fr[m.split("_l4_")[0]].append(inst)
assert len(fr["col_h10"]) == 12 and len(fr["col_h9"]) == 60, {k: len(v) for k, v in fr.items()}
subs = []
for v in ("col_h10", "col_h9"):
    rows = "|".join(f"{r}\\.u_e({'|'.join(str(i) for i in ix)})" for r, ix in IDX[v].items())
    subs.append(dict(inst=f"({'|'.join(sorted(fr[v]))})\\.u_r({rows})", module="ot_v41_rom_elem_q_qxpq_w10_gb",
                     reason=f"DIE-S81-19 plan_s12: plan binds every qxpq_w10 ROM hard core as the adopted _gb master (S81-QX-GB 10-26, "
                            f"LEC EQ CGR0/CGR8 vs the legacy master with go/tag delayed 1 edge); {v} frames x 12 elements; "
                            f"_gb ports = master minus input xs_sv (variant_removed, not tied)"))
a["substitute_inst"] = a.get("substitute_inst", []) + subs
a["clock_landing_table"] = side_rel
for k in ("defines", "dissolve", "files", "straps"):
    for x in pd[k]:
        if x not in a[k] and (k != "files" or "dsdv_mu_hwin" in x) and (k != "straps" or "seqhost" in x):
            a[k].append(x)
for f in ("rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10_gb.sv",):
    if f not in a["files"]:
        a["files"].append(f)
a["note"] += (" | DIE-S81-19 10-28 plan_s12 variant: identical to asbuilt_b178_coll_s11.json except clock_landing_table = "
              "the plan_s12 composed sidecar (r98 98-region table, collector rooted at seqhost with the ACTUAL S81 observer "
              "dsdv_hostb_dstat u_u_dst, fault vid_ri / ready alive_i), the PD7d observer opt-in (define S81_HOSTB_LAND_OBS, "
              "dissolve dsdv_hostb_seqhost_mux + its straps one level down, dsdv_mu_hwin.sv), and substitute_inst of the 864 "
              "qxpq_w10 ROM elements -> ot_v41_rom_elem_q_qxpq_w10_gb (the plan master since plan_s11).")
json.dump(a, open(out, "w"), indent=1)
print(json.dumps(dict(subs=[s["inst"][:120] + "..." for s in subs], defines=a["defines"], dissolve=a["dissolve"],
                      straps_seqhost=[s for s in a["straps"] if "seqhost" in s], files_added=[f for f in a["files"] if "hwin" in f or "_gb" in f])))
