DIE-KV-34 (2026-10-29 14:05-15:20 PDT) KV die owner, receipts. Runs: intel1 /srv/opentallas-scratch2/claude/die-kv-34-1029
(+ Codex leaf A chain intel1 codex-kv-1355/A, epyc2 die-kv-34-1029/{ioft,sd}).

1. KV-019 leaf-driver variants (generic tool: claude/die-kv-34-leaf-1029@384f6ff4fd, ot_clk leaf-drivers).
   A (fixed x5p33->x16 pair per FF cluster, 2956 cells) on its own die GRT0 incl clock: overflow 0; spread TT 95.9 / FF 86.0,
   0/128 >150; duty 0 outside 45-55; clock DRV 0; legs max 304.43 (0 >405); probe3 0 long FF-loaded nets off M8/M9.  PASS.
   SM (stage-model sized): TT pv_S_5 150.2 >150 and FF duty 309 taps outside -> FAIL.  A wins (12.17(3)).
   Files: A.json SM.json base.json (base reproduces the 490.7/447.8 FAIL), legs_A.out, probe3_A.out, ana34.py, resume_leaf.sh.
2. Tap arrival shift A vs tree-c combo (delta_A.json): TT median +254.2 / max +555.2; +11.6 ps/stage on provider-loaded trunk nets.
3. CA on A (DIE-KV-27 proofE recipe; read.tcl/run.sh OT_EDGES readout on A's in-session GRT, main trial_tap_arrivals,
   gate.sh = main die_sta_related): TT lo 46.3 (82 <100) / FF 98.0 (4 <100), spice_edge; spice_cell TT -2.5 / FF 89.1.
   Recipe check sta_E_edge_chk = record 104.8/109.6 exactly.  86 failing ports = 8 tags (6 pc->pc, hg_WS_7->hub_Wo,
   hg_WN_4->pc_WN_4), all fixed by K+1 on that port (arithmetic on rows, both corners, both cals).  NEXT: count_align
   replan on proofA (native6 plan_native.py takes d from inputs/ca_mixed_replan.json -> regenerate that from proofA).
4. sys_c resize-bands (plan_band + cland_fit_reserve): 23 bands re-sized in kv3_sys_c (sysc_resize_bands.log).
