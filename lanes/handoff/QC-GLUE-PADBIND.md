# QC-GLUE-PADBIND handoff (COORD split lane, Opus 5.5)

Job: glue pad-binding FAIL in QC C1g GENDRY (QC-ALLFIX cF/gendry_pre2.log, FABLE-RC-QC 0c3f0f73).

State 11-24 03:2x PST:
- Only type: glue. Msg "gen phys: ERROR type glue: pad bump_bump_fwd_epoch_pad_i must bind a leaf port: None" (gen_rtl.py ~L707, plan-wrapper path).
- Root cause TOOL: plan_gate_pre GENDRY KIT-RTL classifier (gendry_kitrtl_types) needs ALL buses leafless; glue has bus.leaf on some buses, so it went to the plan wrapper. Pads are die bumps bound only via contents[].bump_ports by bind.py kit-rtl (kit RTL marks them bound-only pin). QC kit_rtl mode=bind -> wave never uses wrapper. Same plan in C4/C1g/C1h; same classifier on rt aa4d/f6d43b/25a62 -> C1h GENDRY repeats it.
- Fix commit f61b02d6da (lane clone epyc7 /srv/opentallas-scratch2/claude/QC-GLUE-PADBIND/wt): GENDRY-PADBIND-1124 gendry_plan_unbound_pads; test in test_pre_gendry_1123.py. ot-push-main running.
- Repro (real path kit-rtl + gen --kit-rtl --trial on C1g bind): unit oth-ubuntu-3821774-1795519049, epyc7 QC-GLUE-PADBIND/repro.sh, out repro_c1g/.
Next: post TOOL-FIX <main sha> + repro result to QC-ALLFIX, FABLE-RC-QC, COORD.
