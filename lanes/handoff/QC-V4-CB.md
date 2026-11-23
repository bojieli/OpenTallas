# QC-V4-CB (Opus 5.5, sub-lane of QC-V4), 11-23 06:1x PST
Item: placed-tap census + tap_split --require-placed rows (cap 900) for cbx_q10 x3 + cbf_q11 on c3n base
(epyc8 fable-fix-qc-v4/plans/c3n/plan.json sha256 3b5d2af7f2b0; LATGEN/bound eecec2f6206b). Due 07:45 PST to QC-V4.
- Plan has only 3 cbx_q10 types (cl89936551, cl89936551_h, cl94a12200_h); cbx_q10__cl94a12200 is NOT in c3n (KeyError).
- Placed .reg inventories: epyc8 /srv/opentallas-scratch2/claude/qc-v4-cb/regs/<type>.reg (from FAM-QC-CB-R4 cen5 a/b/c/h
  + my cbf_q11 census epyc10 qc-v4-cb/census_q11, V3 private geom 3_place.odb: 50788 sinks, kit max 5435, over 10).
- Work: epyc8 /srv/opentallas-scratch2/claude/qc-v4-cb/run1.sh (W2/launch = bind rt 0d6ca tools; rt/current tap_split
  fails on missing tap_offset_fill in W2 tools). r2 = 4 types.
