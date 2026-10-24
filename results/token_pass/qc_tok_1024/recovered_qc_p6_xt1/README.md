Rescued 2026-10-24 06:59 PDT (QC-TOK) from intel1:/mnt/old-nvme0/claude/qc-p6-xt1 minutes before the owner-ordered wipe
(07:03). Origin: lane QC-P6-XT1 (10-23 night, branch claude/qc-p6-xt1-1023 never pushed): a QC bind ("b3") of the
QC-P6 plan (QC-P6-G0C @d33d3c4e4 on main 3e05af806 + plan/tools snapshot) with recipe bind/asbuilt_xt1.json =
asbuilt_tie + asbuilt_map_xt1 (u_tap -> sl_*_ctl) + R8 table made on this bind (248,396 pad flops) + CB16 tree alignment
pads qc_tree_pads.json (STEWARD-TOKj 22:00 cause B: CB16 node n_a/n_b out of step after the 4-way cluster split).
b3 steps (b3.*.log): elab PASS, bind 0 errors / 0 tied / 0 undriven, verify PASS (2,723,870 matched / 0 mismatched),
portbind DIE_PORT_BIND PASS. xt1 was NOT run on it before the coordinator died.
plan/: the snapshot's die_plan.json (differs from main's), r8 table, recipe files. The b3 bound rtl (8 MB) is kept on
intel1:~/ot-scratch/qc-tok/recovered/qc-p6-xt1/b3/rtl (not committed here).
