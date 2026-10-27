# HBM-CORE-LAT-R3 ot_hbm_svc_sm_xcal_rel_t (B2o 207.36^2), pilot Q0 view 991af17b4632 (pins snapped), Tue Oct 27 00:20:50 PDT 2026
TRIAL kit (TRIAL-no-frozen-master-plan). Kit intel2:/srv/opentallas-scratch2/claude/hbm-core-lat-r3-xcal/kits/ot_hbm_svc_sm_xcal_rel_t_991af17b4632-_r3A (kit_hash c52ef57591fdc886), ot-run unit oth-ubuntu-3753332-1793085226, GOAL=place (stopped before CTS, no 4_* logs).
- B2o pin tables are OFF the M4/M5 0.048 lattice (all 4 tables, dev up to 0.024 um; generator refuses). pins_snap/ = nearest lattice (snap_report.json). Plan owner must re-snap (B2o tables look scaled from 250.56 without re-snap).
- planS2/clock_entries.json still says entry (125.28,125.28) (250.56 centre); die_plan tap = origin+(103.68,103.68) = 207.36 centre (used here).
- synth: face_guard rc 0, port_bind PASS, sdc_lint PASS, LEC EQUIVALENT 5593/5593 (CHECKED from logs).
- placed: 11349 cells, 3142 FFs + 4 SRAM; rows only 3826 um2 (9.7 % of core): W strip x4.3-15.2, E strip x194-203, 8 bottom rows, 6 top rows; std fill of free 42 %.
- centre entry (103.68,103.68) lies ON SRAM u_program_hi; nearest row 88.5 um. Shared planner core_infra_htree 2,2,4,4 on this geometry: PLAN MODEL TT 1331.9 / FF 1122.1, window 240 (UNCHECKED) = macro-blocked maze + equal-length detours (33 stages) -> NOT a usable structure; no slice B built.
