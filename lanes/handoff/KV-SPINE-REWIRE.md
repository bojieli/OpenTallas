# QC-GLUE-PADBIND handoff (COORD split lane, Opus 5.5)

Job: glue pad-binding FAIL in QC C1g GENDRY (QC-ALLFIX cF/gendry_pre2.log, FABLE-RC-QC 0c3f0f73).

State 11-24 03:2x PST:
- Only type: glue. Msg "gen phys: ERROR type glue: pad bump_bump_fwd_epoch_pad_i must bind a leaf port: None" (gen_rtl.py ~L707, plan-wrapper path).
- Root cause TOOL: plan_gate_pre GENDRY KIT-RTL classifier (gendry_kitrtl_types) needs ALL buses leafless; glue has bus.leaf on some buses, so it went to the plan wrapper. Pads are die bumps bound only via contents[].bump_ports by bind.py kit-rtl (kit RTL marks them bound-only pin). QC kit_rtl mode=bind -> wave never uses wrapper. Same plan in C4/C1g/C1h; same classifier on rt aa4d/f6d43b/25a62 -> C1h GENDRY repeats it.
- Fix commit f61b02d6da (lane clone epyc7 /srv/opentallas-scratch2/claude/QC-GLUE-PADBIND/wt): GENDRY-PADBIND-1124 gendry_plan_unbound_pads; test in test_pre_gendry_1123.py. ot-push-main running.
- Repro (real path kit-rtl + gen --kit-rtl --trial on C1g bind): unit oth-ubuntu-3821774-1795519049, epyc7 QC-GLUE-PADBIND/repro.sh, out repro_c1g/.
Next: post TOOL-FIX <main sha> + repro result to QC-ALLFIX, FABLE-RC-QC, COORD.
- 03:12 intel2 fork OK (tree). R1 (schema note key) / R2 (landing_network edges) / R3 (sidecar count_aligned L657_0) each stopped on a row gap; row now 3 halves.
- 04:03 R4 full gate: plan f068c2e47f9a, asbuilt_spine_A5t3.json 4bb7f5e8871f (sink_stages + clock_landing_table -> eW_sidecar_spine_A5t3.json 9b86464db7a2). Unit oth-ubuntu-3699367-1795521786, log intel2 kv-spine-rewire/logs/gate_R4.otrun.log.
- base_A5t3/ = copy of KV-ALLFIX gate_A5t3/bind outputs (rtl, bind_reset, bus_groups, latency, param_regen); base_A5t3_regen.json (19 OK / pc833 ERROR source path only).
- Next: pins_from_bind.py on gate_R4/bind/rtl -> PINS.json -> row --pins; flush3 on gate_R4/bind (rtl + bind_reset.json); regen diff; ROW-REBASED post.
