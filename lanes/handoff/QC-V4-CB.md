# QC-V4-CB (Opus 5.5, sub-lane of QC-V4) - STOOD DOWN 11-23 11:4x PST (QC-V4 order: verdict, handoff, stop)
Deliverable (adopted from Codex carry, not redone): epyc8 /srv/opentallas-scratch2/claude/qc-v4-cb/clk_c4_1123/carry_0924.row.json
sha256 e28b3b71a97b, base C4 81fd3e6370c0 (measured from 6341fe2a8a38). Wholesale partition_types for cbf_q11,
cbx_q10__cl89936551, cbx_q10__cl89936551_h, cbx_q10__cl94a12200_h, glue + tap_offset rows. QC-V4 stages it as a REASONED row
for the 13:00 gate (C4 already in strict bind; no second bind fits).
Census at cap 900 on placed sinks (real 3_place.odb .reg in qc-v4-cb/regs): glue 87->115 taps max 900; cl899 94->139 max 896;
cl899_h 135->153 max 896; cl94_h 141->147 max 873; cbf_q11 127->149 max 872; over-cap 0, radius <=200 everywhere.
Kit-table placed census before the split (over 1000): cl899 12 (max 4078), cl899_h 13 (3989), cl94_h 13 (5426), cbf_q11 10 (5435).
The plan has no cbx_q10__cl94a12200 type (cen5_c census 46496 sinks, max 2998, over 9 is for an older plan only).
Checks: on the carried remapped.json ADDTAP illegal 0, TAPNAME fails 0; Codex: TAPOFF census PASS (119 ports), landing_remap 0 rewrites.
On c3n: tap_split r2 REMAP anchor 4/4 clean + LANDREMAP recheck clean; glue g1 remap clean, ADDTAP 0, TAPNAME 0.
OPEN: reset_anchor + LANDREMAP recheck of the carried plan, unit oth-ubuntu-3299626-1795459874 (chk_c4.sh, log intel2 ~/qc-v4-cb.chkc4.log,
output epyc8 qc-v4-cb/chk_c4). Slow (check_landremap ~2 h). Unit posts DONE itself; QC-V4 reads the verdict.
Cancelled my own superseded c3n glue recheck oth-ubuntu-608565-1795443890.
Glue rows402+clock21 were not in c3n (its glue == p7c5rt base glue); they are now in the carry row.
