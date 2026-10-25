# Lane PATH-HBM -- one complete HBM path (owner priority 10-25 08:10)

Path: hb_coll_NW TKM static II8 -> native NW L74 two-beat -> shared root tkm_SW (TP192/KMAX2048) canonical root + 32 common
tiles -> return L12 (CTL) / L13 (DATA) -> hb_coll_NW tkx_w*.  "Complete" = every partition/core on the path GEOM PASS +
routed + signed off (TT setup / FF hold) + bound in the die + token test exercising exactly this path.

## Items (2026-10-25 08:09 PDT)  state legend: OPEN / WIP / PASS(gate) / SIGNED
| # | item | state |
|---|------|-------|
| P1 | NW_hub (q_hub) TKM ingress source cores (u_hb_coll_Q_body/reduce/ring_ag etc. driving tkx_*) | BLOCKED: plan_direct3 NW_hub uses q2 ot_hfd_coll_q2_hard_v8g (SOLO=0: tkx_* driven 0, tkx_w*/busy/done/fault tied 0; split cores have NO tkx pins). Needs NW-only q3 type ot_hfd_coll_q3_hard_v8x (make_wiring.py W-EP, 'plan change owed'), its split (q2 already 465k) + kits. UNOWNED |
| P2 | L74 NW_hub->root direct 2341 b, 2 cycles (plan_direct3 ecfb97d718) | PASS(cut 0.5968) analytic only; no G0/G0C on full plan, not on main |
| P3 | L12 CTL / L13 DATA root->NW_hub direct 2 cycles each | PASS(cut) analytic only, same plan |
| P4 | TKM root core u_tkm_SW_root (319.68x345.6, 3575 pins) | kit d944a428 synth+bench PASS; pins must change (P6); no P&R |
| P5 | common TKM tile core (x32, tile_tid ID pin, owner decision B) | gen PASS 3387725, synth DONE, LEC UNPROVEN 689 pts (ovf_b/up_out); pins must change (P6); no P&R |
| P6 | root<->tile0 + tile<->tile chain seam geometry | FAIL: up_out max 511 um, 75 b >405; and the 32 tiles are scattered (tile0 y518 -> tile1 y4735) |
| P7 | tile_clk / clr / conv distribution (32 tiles, die-spine taps, static equal-latency broadcast) | OPEN |
| P8 | root partition (soft glue + stations) and NW_hub partition route/sign-off for path nets | OPEN |
| P9 | die bind of the path (plan on main, raw bind, port-bind 0 errors) | OPEN |
| P11 | SM/matvec leg: one SM half hnx_rp3lp3h_n (+ its _s pair) of the NW quadrant whose output feeds hb_coll_NW (SM -> coll -> TKM) | OPEN: NEEDS-KIT (OWNERS: NO_RECIPE in coregen; 10-24 WC runs were PATHFINDING only) |
| D1 | die GRT with the path's real signed-off views (stand-ins elsewhere) | OPEN |
| D2 | die STA TT setup / FF hold over the path | OPEN |
| D3 | clock die root -> path flops (regional taps, related-pair skew + CPPR) incl. 32 tile_clk taps | OPEN (plan4 tile_clk data-station bug fixed in 7ff73a8320, not yet regenerated) |
| D4 | reset + START broadcast (decision 13c) to path cores | OPEN (HBM plans still reset.release counted) |
| D5 | long-reach L74 seam crossing NW_hub->root (and inside root to the TKM root core del_flit face) | OPEN (partition cut PASS only) |
| P10 | token: TKM path test with face_shell wrappers instantiated, >=2 tile IDs, L74/L12/L13 final cycles | WIP: r3 baseline (no shells) live intel1 unit 2167534 |

Signed off: 0 of 16.

2026-10-25 08:13 PDT PATH-HBM: coordinator scope add (owner 10-25): die-level items D1-D5 (token on exactly the bound views = P10, >=2 tile IDs).
Representative coverage: OWNERS.tsv most-replicated HBM masters = hnx_rp3lp3h_n / _s (SM halves, 128 replicas each; SM/matvec class)
then idx_score_quarter (36). The TKM path does NOT pass through an SM core, so P11 adds one NW SM half pair (the matvec that
produces the scores feeding hb_coll_NW): it covers the most replicated master on the die, and it is the natural upstream of the TKM
stream (SM matvec -> coll -> TKM -> return). Common TKM tile (x32, strap ID) covers the next replication class inside root.
2026-10-25 08:11 PDT FLOW-INFRA/DIE-PROTO -> PATH-HBM: HBM B2n die-top GRT (plan f710e18c = main) still LIVE epyc1 dtrial-grt-3616206 (iter 2/50 at 07:42) -> no overflow yet; hops 0 over 405; clk_run30 pair skew 135.6/135.4 FAIL (seam 43.9 ok, insertion 18.8ns) (CLOCK/HBM); die STA ideal TT+FF live intel2 die-proto-hbm/sta. claude/die-proto-1025@bd51e6310 results/die_proto_1025/SUMMARY.md

2026-10-25 08:14 PDT PATH-HBM: endpoint audit: (a) P1 BLOCKED (above): L74 2341 b = exactly tkx_* (2180 flit + 161 cfg/start/slot/valid); return = 569 w_* + busy/done/fault (572 b) inside L12/L13 3143 b, L12-vs-L13 bit split not yet specified. (b) Inside both partitions the plan relay chains for L74/L12/L13 end at the wrong cores (q_hub: u_pgp_Q/u_hcollgi_Q/u_hc_Q; root: u_col_idx/u_hb_idx__*/u_hb_argmax/u_hc_eng_*); none reaches u_hb_coll_Q_* or u_tkm_SW_root. (c) root partition: 0 internal stations on the TKM tile chain buses (only 907 tile_clk 'data' stations from the 7ff bug).
OWNER?/COORD: who owns the NW-only q3 hub type + split (HBM-PLAN/B2o delta + HBM-CORES)? Without it the path cannot be complete.
2026-10-25 08:15 PDT FLOW-INFRA -> PATH-HBM: flow canary (main 202a50a59) hfd_hgi_vm_calendar_f20 FAIL: face_guard (553 checked) = 3 true shared data nets tgt_fault/active/fault (Codex clock-cover correction: clk_cap/clk_tgt/missing-port were false) + rc_file (config.mk sets no LAYER_PARASITICS_FILE: that canary kit predates HBM-KITS F2 on main - regenerate). epyc1:/srv/opentallas-scratch2/claude/flow-canary/runs/hbm_202a50a59_1025_0648/ + epyc1:/srv/opentallas-scratch2/claude/codex-infra-0719/hbm_cover_diagnostic_0719.json
2026-10-25 08:18 PDT PATH-HBM: P6 structural fix DESIGNED (0 cycles): straight-through common tile template + 4-column snake + root re-pin; audit PASS (worst hop 345.6 um, 0 b >405, 0 obstacles). GEOM REQ [PATH-HBM-TKMCHAIN] posted; files epyc1:/srv/opentallas-scratch2/claude/path-hbm/geom_chain1/. clr/conv broadcast needs ~14 equal registered stages (to token). P6 -> WAIT-GEOM.
