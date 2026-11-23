# KV-D29 handoff (Opus 5.5, started 11-23 05:50 PST). Successor of KV-PLAN-R6, FABLE-UNC-KV, OPUS-FIX-KV-HG-R8, FAM-KV-IOPC-R4,
# SINKSPREAD-R2, OPUS-FIX-KV-PV-R7, FIX-KV-PV-MESOFIFO, FAM-KV-HROOT-R1, FAM-KV-HUBC-SYSC-R2, KV-RINGMAC-R1, OPUS-KV-DIE-R2.
Also owns: 16 KV WAIT-BIND rows (hgi_*, hg_v1p5/v1p6/v3, hub_Wo) + kv3_pc_v1 pair (COORD sweep 05:5x).
Deadlines PST: tools cut 11:30 (lanes push by 11:15), package -> FABLE-RC-KVHEAD 12:30, gate 13:00, cut 14:00.
Work: epyc8 D=/srv/opentallas-scratch2/claude/kv-plan-r6/d29 (rows.json 28 rows, d29_chain8.sh, test/c25 = plan 2bb0902d3102),
tree W=/srv/opentallas-scratch2/claude/kw45/src_kv_d29_work_r6. Cut conditions D/D29_CUT_CONDITIONS.txt, rules D/CUT_RULES.txt.
## Sub-forks (spawned 06:0x): A HG, B HROOT, C hub_C+sys_c, D pc, E pv. Each delivers row+sha+gate evidence into D/rows_in/<X>/ or a REASON.
## Log
- 05:55 TAKING posted (dc5e493).
- 06:0x forks A-E spawned. rows_in/{A..E} on epyc8 d29. x10: tap_offset_fill fill+check PASS on c25 (1676 ports/19 types), cover census PASS 56/56 (kvd29/tapoff_t1). d29_chain9.sh = chain8 + all-mode TAPOFF (OT_LANE KV-D29, GATE_HOSTS env).
- 06:03 rehearsal k1 (28 rows 160c8f935f99, R8=1 RESET=1 graft r5, POSTROWS PCV1BANK) via kvd29/launch_k1.sh; log d29/k1.chain.
- 06:1x CLASS-FIX-RHI 72b268847ec4 added as row 29 (wrapper rows/ROWS_CLASS-FIX-RHI-KV.py 377b5d393209, allow_top clock); rows.json 859a3f633da1 (old 28 in kvd29/rows.json.28_*).
- 11:30 cut-over: kvd29/cutover.sh <rt sha12> (refuses if a chain runs / required commit missing); then c25 no-op recompose, then final chain (copy chain9 -> chain10 with RT = new rt).
- At APPLY: kit_wave_edit --set /dies/qwen_kvsys/die_gen_env/OT_PREGRT_HOLD_PORTS_SCOPE=ctl (KV-CTLPORT dbc5c772e0d); WAIT-BIND 16 rows release; hub_Wo/Eo hold if kit_relay_depth __rst_n fix not in wave rt.

## B-HROOT (fork B, 06:3x PST)
- Probe 1123035146 (kit intel1 KV-D28/private/FAM-KV-HROOT-R1/kv3_hroot_1123035126) DID carry the full stack R1+BAND+RING+RES+EFS (plan 56e157569c57, fork_d28c). Probe-through continues: CTS done 06:05, GRT running (adopted, not relaunched).
- Render read: the west ~45% of the 1900x838 outline is empty (all pins are on the E/S faces). Red column at x~1880 y300-650 = kvs_ctl pin-side capture. Auto-geom GRT ovfl 0; placed scan has 3 NEED-STATION groups (2 reset u_rrl_45 -> S-west 1-bit bins 764/810 um, 1 kvs_ctl dsel->bin eq 677 um).
- The 23 opposite-face pins are ALL count straps (strap_ca_k_ of E-face rings ft4/ft5/seq/kvs_ctl, sitting on the S face). Fanout 868 um = the single reset leaf rst_n_t9 (u_rrl_45).
- CTS post-hook TT: setup -57.69 (cland_fstart_in_ft4_i port -> ft4 ring s_d; seq fstart -19, ft0 -5.7). Hold -106 = arst_n/start_i (CTL class, KV-CTLPORT wave key closes it). x15 slg dch[2] y[16] = +13.20 MET.
- ROW intel1 fam-kv-hroot-r1/d29geom/ROWS_KV-D29-HROOT-GEOM.py sha12 4ca2bc6de1a3: (1) reset.leaf_clusters (11 groups, all 21 buses); (2) 4 E-ring strap groups -> E island x1896.48; (3) slg band re-centred (x15, offered to FABLE-OPEN-KV per COORD). Plan 810534ae4548 on 56e157569c57.
- Gate: chain_geom (ot-run intel1, client intel2 ~/tmp/kvd29b/chain_geom.log): fork_d29g, launch_geom rt af3f7514266b, PRE, G0, strict bind, LATCHECK, outputs d29geom/{pre.log,g0gate,bindgate*}.
