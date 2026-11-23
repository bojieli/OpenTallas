# KV-D29 handoff (Opus 5.5, started 11-23 05:50 PST). Successor of KV-PLAN-R6, FABLE-UNC-KV, OPUS-FIX-KV-HG-R8, FAM-KV-IOPC-R4,
# SINKSPREAD-R2, OPUS-FIX-KV-PV-R7, FIX-KV-PV-MESOFIFO, FAM-KV-HROOT-R1, FAM-KV-HUBC-SYSC-R2, KV-RINGMAC-R1, OPUS-KV-DIE-R2.
Also owns: 16 KV WAIT-BIND rows (hgi_*, hg_v1p5/v1p6/v3, hub_Wo) + kv3_pc_v1 pair (COORD sweep 05:5x).
Deadlines PST: tools cut 11:30 (lanes push by 11:15), package -> FABLE-RC-KVHEAD 12:30, gate 13:00, cut 14:00.
Work: epyc8 D=/srv/opentallas-scratch2/claude/kv-plan-r6/d29 (rows.json 28 rows, d29_chain8.sh, test/c25 = plan 2bb0902d3102),
tree W=/srv/opentallas-scratch2/claude/kw45/src_kv_d29_work_r6. Cut conditions D/D29_CUT_CONDITIONS.txt, rules D/CUT_RULES.txt.
## Sub-forks (spawned 06:0x): A HG, B HROOT, C hub_C+sys_c, D pc, E pv. Each delivers row+sha+gate evidence into D/rows_in/<X>/ or a REASON.
## Log
- 05:55 TAKING posted (dc5e493).
