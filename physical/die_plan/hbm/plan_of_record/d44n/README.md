d44n = d44m (die_plan.json 243ff7d018ba UNCHANGED, core_conns.json e689ac2475d8) + core_macros.json 0aec701442c6
(DIE-HBM-49/51 10-31, OWNER 07:1x one-block NO_RECIPE plan event; base core_macros ea6bd3fa92e0).
Static SRAM sites (core_macros_fix static section, see core_macros_fix_report.json) for 11 cores whose macro positions
were UNKNOWN: ot_hnx_fused_host_program, ot_hnx_fused_hub_n4ext, ot_hnx_fused_tnode, ot_hfd_coll_q2n2_body_core,
ot_hbm_su_programme_pslice_c5 (100 macros, 8 cols), ot_hgi_sm_xload_cl2_bfqg, ot_hnx_idxn_keybuf_slice,
ot_hbm_su_static_pgslice_lg__lane_exp__canon_7cd691, __lanes__canon_cf1e77, hnx_vms_bank_q0_faces__vec6293 / __vecd4ae.
Sites: x on 0.048 grid, y on M4 track (0.012 mod 0.048), macro channels >= 10.8 um; outlines/pins unchanged.
G0 974 -> 968, G0C 1327 -> 1321: exact new 0, gone 6 (clock_entry_macro "macro positions UNKNOWN" WARNs) -- g0/g0_delta.json.
Kits regenerated with these sites: KIT_PREFLIGHT PASS (issues 0) for the 6 gen2 cores and 9 rs/ variants (intel1
/srv/opentallas-scratch2/claude/die-hbm-49/macros). Generator + inputs + renders: results/die_hbm_1031/dhbm51_cm.
Still open: lane_exp canon, lanes canon, keybuf, vms_bank x2 need a full gen with macros/views_cm.json.
