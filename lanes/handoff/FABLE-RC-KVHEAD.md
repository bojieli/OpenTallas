# FABLE-RC-KVHEAD (Fable, started 11-23 00:45 PST) independent root-cause review, dies KV + HEAD
Brief: scratchpad fable_review_brief.txt (+rules.txt, visual_brief.txt, visual_brief2.txt). Output: lanes/FABLE-RC-REVIEW.tsv.
Local work dir (rtx-pro): scratchpad/fablerc/{kv,head}. VIS-KV renders reused from scratchpad/viskv/all.
Split: parent does KV (hgi/hg, pc, hroot, sys_c, pv); a fork does HEAD (hd_lep0N w/e, hd_ctl, hd_serdes) and returns TSV lines.
Deadlines: KV families without a full-cause row -> tell KV-PLAN-R6 + VIS-KV by 05:00 (not released at D29 apply ~06:00); new rows -> D30.
## log
- 00:45 started; own view first, VIS-COVERAGE not opened yet.
- 00:58 HEAD fork done (13 TSV lines returned to parent; 1 post 7e850385f82 to VIS-HEAD + OPUS-FIX-HEAD-LEP0N-R9: tap-window die row MISSED, E-half macro rows PARTIAL, twist COVERED).
- 00:58 KV probes via ot-run from intel2 ~/fable-rc-kvhead (logs g_*.otrun.log = 5-it GRT congestion, t_*.otrun.log = timing classes); outputs epyc8/9/10 /srv/opentallas-scratch2/claude/fable-rc-kvhead/{g_*,t_*}; tools there (vis_probe.*, tprobe.*, cong_census.py, pgrp.py). Load cap makes them trickle.
- KV own view so far: hroot = E-strip landing cland_i_kvs_ctl_o_hroot_Q x1850-1900 y450-650 (1523 GRT ov, 20425/20426 DRC); sys_c = GRT clean, setup -342..-387 TNS -21k..-71k, pinreg max 431; pc_v3 = setup -531..-807 TNS -218k..-290k, 86 unstationed reach classes, 74k hold cells, port_in hold -269; hgi_v2 = ectl pd -> hst3 path 1.8 mm -285..-361, W strips x25-300 y600-850 / y950-1250 ov 6155; pc_v1 x3 + pv_v3 = exact bank/site flow errors.
- 01:3x resumed after 5-h limit (Codex handoff 01:19 read: D29 cut = 16 rows, sys_c dropped; composed D29 must pass ADV-MERGE-RESET-DEPTH). Posts: KV 1/3 04bcd7b9 (hroot, sys_c), 2/3 74d728f4 (pc). 30 lines appended to lanes/FABLE-RC-REVIEW.tsv (17 KV + 13 HEAD).
- Probes done: g_hgi_v1, g_hgi_v4, g_pc_v3 (epyc9), t_hroot, t_sys_c, t_pc_v3. g_pv_v8 died GRT-0228. Still queued/running on epyc8 (do NOT relaunch; ot-run clients alive on intel2): g_pv_v6n, g_hg, t_hg, t_hgi_v2cle, t_pv_v6n.
- NEXT: post 3/3 (hgi/hg/pv + D29 hold list) ; read replies; census epyc8 probes; update TSV verdicts; final COORD report (2) when every gap has a row or reason.
