# OpenTallas release tree (pending only; refreshed 2026-10-31 05:41 PDT by CLAUDE coordinator)

_Updated 10-31 07:06 by COORD. OWNER 12.25 slack gate / 12.26 HBM tree||mesh / 12.27 pilot-first, default-on fixes, class canary + tag scope, gen lint. Count 40 signed hard-core designs: S81 19/54, HEAD 3/4, QC 4/14, KV 12/35, HBM 2/84; 0 of ~460 types signed._

## EDIT · rules
- PENDING items only, one short line each, edited in place. Remove an item when done (evidence goes in PATH-FREEZE.md / lane files).
- Line form: `- [ ] ID task · OWNER · STATUS · current fact → DEP.ID` ; "→ X" means this item waits on X (each → is a link).
- Gate ids per die are PFX.INFRA / PFX.GRT / PFX.CLK / PFX.BIND / PFX.STA.
- OWNER 12.18 (2026-10-29 05:44 PDT): full-gate census per die -> lanes/CLOSURE-LIST.tsv (fixed list); rule freeze (new checks only by owner); hourly burn-down open/closed/added; all 5 dies in parallel.
- OWNER 12.17 (2026-10-29 05:31 PDT): freeze plan on die GRT0+clock pass (fix-only after); one clock tool ot_clk.py for all dies; 2 parallel fix variants per failing gate; strict bind clean before GRT counts.
- DIE METHOD = METHODOLOGY s12 v5.1 (v5.0: early taps = macro insertion balancing, AOCV 0.21%/mm gates; v5.1: trims/useful skew/pads sparse <=~5% + CLOCK-RESIDUAL ledger after structural fix; 5%/15% cost = targets) (OWNER 10-26, frozen; change only on measured failure + owner decision): 12.7 MASTER PLAN FIRST per die (census -> corridors <=0.6 -> bays <=405 um every path/layer -> M7 entry pins -> worst-case PG, PG-shielded clock, islands clock/reset only, one core latency) + static plan gates incl. analytic predictor BEFORE any block build; kits carry a plan slice. 12.8 clock by construction: plan-defined centre clock entry per core, 250 ps TT, structured core trees; NO early taps / post-measurement trims / clock ECOs / mesh-node CPPR (plan-computed per-tap sizing OK). Freeze = GRT0 incl clock (>=50 it) + DIE STA with the real clock on related pairs (TT setup, FF hold; CPPR to last tree node); 80 ps skew = design target only. v4.6-4.9: MSCTS H-tree->ONE continuous mesh (signed mesh = CPPR point)->short local trees; clock OCV = depth/distance table (draft, owner review); droop shared (clock charged differential only); data hold buffers allowed. 12.9: one owner per die plan/clock (lanes/OWNERS-DIE.md); gate numbers via NUMBER-CHECK.
- Release gate = die STA on real views + token pass.
- Status words: RUNNING WAITS TODO NEW COORD OWNER FAIL PASS FROZEN BLOCKED NOT RUN.

## DIE s81 · S81 (DeepSeek ROM layer die) · rev plan_h2_2249 7515f32564e8 (grid+explicit taps, main) → aa596d4b8224 (band B, merging) · HARD FROZEN 12.20
- [ ] S81.BIND Strict bind on 7515f32564e8 · DIE-S81-41 · FAIL · 1 error 'rst_rl_87 raw reset parent rst_rl_86 absent' (also on base; likely taps merge relay numbering) → tool fix
- [ ] S81.GRT Die GRT0 incl clock · DIE-S81-41 · PASS · ckclk3 on grid+explicit taps: overflow 0
- [ ] S81.CLK Die clock 12.25 · DIE-S81-41 · FAIL · CA PASS; kit-contract hold +26.35 / 0 viol; TT setup -27.23 / 7 neg pairs in bk_sel__t2 (bk_sel core views missing → UNMEASURED) → S81.BKSEL
- [ ] S81.TAPW Per-type clock.tap_window (station hold gate fails by construction at die-wide 180) · DIE-S81-41 · RUNNING · approved 05:2x: W_t = measured need + 10 (t20 110, t7 90, t23 110, t30 100/130, t24 150); 6 types >140 need region tree tightening → b2-s81
- [ ] S81.RINGHOLD Landing-ring write hold (~180 ps short per bit; 147/150 recent kits) · S81-RINGHOLD-3 · RUNNING · OWNER approved: measure sender min, (b) bounded ring clock main path, (a) opposite-edge RTL in parallel
- [ ] S81.BKSEL bk_sel__t2 setup + core views · DIE-S81-41 · TODO · one-block fix, 2 variants
- [ ] S81.STA Die STA on real views · DIE-S81-41 · FAIL · → S81.CLK, → S81.TILES
- [ ] S81.XFIN xfin 552.7k > 400k cap: harden children · S81-CORES-KITS-10 · RUNNING · eng_finish x4 (61% N-face tracks) || eng2 x2 (34%), first to pass pins+route wins
- [ ] S81.KVLEAF kv_leaf__t2 census (10 h yosys stall killed) · DIE-S81-41 · TODO · rerun without FA extraction, 1 h cap
  - [ ] S81.TILES Tile sign-offs · S81-CORES-KITS-10 / KIT-WAVE-5 / SIGNOFF-SPRINT-11 · RUNNING · 19/54 hard cores (ve_m 04:3x), 0/204 types; vn_a LEC EQ 06:44, b-s81 re-sign running (SPRINT-11); station kits wait S81.TAPW; serdes/iqf/seqhost pilots launched

## DIE s81_head · S81 head die · rev l47k (main 98d42235330) → l47t (hd_st_turn local reset, merging) · FROZEN 12.20
- [ ] HEAD.PLAN Plan pointer + packaging · ROOT-MERGE-AJ / DIE-HEAD-48 · RUNNING · l47 + l47t packaging merged (fd132, ba509); OWNER 07:0x: l47u reset-tree regeneration GO (exception, RTL+sidecar+re-kit); G0C shows None: plan names native_domains/*_contract.json relative to its own dir → packaging fix
- [ ] HEAD.BIND Strict bind on l47k · DIE-HEAD-48 · PASS · TIE_AUDIT 1669/0, nested 6111; strap LEC wshim_rx 5/5 + lep0N EQ
- [ ] HEAD.GRT Die GRT0 incl clock · DIE-HEAD-48 · PASS · overflow 0
- [ ] HEAD.CLK Die clock 12.25 · DIE-HEAD-48 · WAITS · setup PASS; routed regions 86-105 ps, detour 1.00; TT setup +145.8 intra / +537.3 seam, 0 neg; CA 0/427 (l47k); FF hold BLOCKED (0/23 types signed); START skew UNMEASURED
- [ ] HEAD.STTURN hd_st_turn clock tap near (1160,990) + hd_st_m status-stage sites · DIE-HEAD-48 · TODO · one-block events
- [ ] HEAD.HOLDCLS l47 landing class canary: hold repair hit 7651-buffer limit in GRT · FLOW-16 · RUNNING · probe whether die-wide tap_window (same class as S81.TAPW)
- [ ] HEAD.STA Die STA on real views · DIE-HEAD-48 · WAITS · → HEAD.TILES
  - [ ] HEAD.TILES Tile sign-offs · DIE-HEAD-48 / KIT-WAVE-5 · RUNNING · 3/4 hard cores (lep_pair ECO7 LEC EQ), 0/25 types; HEAD wave kits re-GEN on main (E-face landing fix); HOST LEC B + SerDes _0920_ open

## DIE qwen_compute · Qwen compute · rev plan_qc52 gen52b (0735589d) · HARD FROZEN 12.22
- [ ] QC.BIND Strict bind on plan_qc52 · DIE-QC-52 · PASS · bind clean on the frozen plan
- [ ] QC.GRT Die GRT0 incl clock · DIE-QC-52 · PASS · gen52b 50-it GRT, 51,365 clock nets NDR M8/M9 + 492,777 signal: overflow 0
- [ ] QC.CLK Die clock 12.25 · DIE-QC-52 · FAIL · TT setup +100.60 / 0 neg, seam +224.32; FF hold BLOCKED (kits); 679 block-contract viol (W 180) in ~20 c_*_11/_01 regions: stage model 5 ps vs GRT 160 ps spread → routed C-box DRT (NDR w0.04) + stage-model refit; routed number due 06:00
- [ ] QC.STA Die STA on real views · DIE-QC-52 · WAITS · → QC.CLK, → QC.TILES
  - [ ] QC.TILES Tile sign-offs · DIE-QC-52 / KIT-WAVE-5 / SIGNOFF-SPRINT-11 · RUNNING · 4/14 hard cores (rp1 FT counted), 0/119 types; b-qc tag cut @9cf9419c0

## DIE qwen_kvsys · Qwen KV · rev plan_c 0684843dda9f (event28w_c + PHY pc4 views + band resize) · HARD FROZEN 12.20
- [ ] KV.BIND Strict bind on plan_c · DIE-KV-51 · PASS · plan of record bind clean; PHY/band delta 0 new
- [ ] KV.GRT Die GRT0 incl clock · DIE-KV-51 · PASS · replay with PHY+band delta IDENTICAL
- [ ] KV.CLK Die routed clock 12.25 · DIE-KV-51 · RUNNING · intel1 die-kv-49/clkdrt boxes 1/2 + GRT box0; post due 12:00
- [ ] KV.ECTL ectl 18/34 quarters · DIE-KV-51 · RUNNING · q1 FF -4.49 + slew, q2 FF -6.49 + slew/skew + stale LVT libs → repair + re-sign b-kv; q3/q3b GRT-0183 both → rebuild with core_infra_plan regenerated for 18/34
- [ ] KV.FN token_epoch functional bug blocks KV count · KV-FN-2 · RUNNING · OWNER: must be fixed; RTL change + re-signs accepted
- [ ] KV.TAPW Per-type windows (W 80: 4913 contract viol) · DIE-KV-51 · WAITS · → daaa48cc29b merge (ROOT-MERGE-AJ); PHY abutment to core edge approved (PG openings for M6→M7)
- [ ] KV.PHYK PHY wrapper kits not generatable (reset_tree hard partitions; M7 clock-pin form) · AUTOBUILD-PIPE-5 · TODO · class fix default-on
- [ ] KV.STA Die STA on real views · DIE-KV-51 · WAITS · → KV.CLK, → KV.TILES
  - [ ] KV.TILES Tile sign-offs · DIE-KV-51 / KIT-WAVE-5 · RUNNING · 12/35 hard cores (ectl q2 retired), 0/56 types; core_tx SIGNED b-kv (+62.61/+8.39), counts on LEC EQ; kvs_pc/pv_join_t/astk not started

## DIE hbm · HBM unified SU/MTP/MU · rev d44f → d44g (tap_window 160 + seam_hold, metadata, merging) · HARD FROZEN 12.22
- [ ] HBM.BIND Strict bind d44f · DIE-HBM-49 · RUNNING · residual pairs from d41f; d44g metadata adds 0
- [ ] HBM.GRT Die GRT0 incl clock at >=50 it · DIE-HBM-49 · RUNNING · 22 g50 probes (q_b010 it 12/50); window wB_d38a 165,661 ov mid-window (real vs artifact: render check); V3 A/B fallback probes ~08:00
- [ ] HBM.CLKLOC Hub/regional clock, tree form · HBM-CLKLOC-3 · RUNNING · C4 DME fail fixed (be8142a717e); C5 kit ETA 06:30-08:30 → routed 12.25 + needed-W
- [ ] HBM.HUBMESH Hub mesh form T028/T029 · HBM-HUBMESH-3 · RUNNING · a3 TT +666 / 0 neg; needed W 59-62 on mesh, ~200-210 with 35 early core taps; GRT-0183 cause open
- [ ] HBM.CLK Die clock 12.25 · DIE-HBM-49 · WAITS · → HBM.CLKLOC or HBM.HUBMESH (first to pass, 12.26)
- [ ] HBM.STA Die STA on real views · DIE-HBM-49 · WAITS · → HBM.GRT, → HBM.TILES
  - [ ] HBM.TILES Tile sign-offs · HBM-CORES-KITS-34 / DIE-HBM-49 / KIT-WAVE-5 · OWNER: one-block plan events for the 20 NO_RECIPE items · RUNNING · 2/84 hard cores, 0/81 types; generator fixes (clock pin at entry, NO_RECIPE, IO-HOLD A) merged/merging; hnx_fused_lane cast RTL fix + LEC; no HBM pilot signed → b-hbm waits

## TOKEN · Token-pass gate per design
- [ ] TOK.HBM HBM speed · TOK · PASS · ~1677 tok/s accepted (OWNER 12.21)
- [ ] TOK.DS DeepSeek ROM token pass (S81 + head) · TOK lanes · BLOCKED · → S81.BIND
- [ ] TOK.QW Qwen ROM token pass (QC + KV) · TOK lanes · BLOCKED · QC 36/36 PASS (10-28); KV FN L0 probe: epoch never latches, fault 0x80 (DIE-KV-51)
- [ ] TOK.E2E End-to-end token pass · TOK lanes · NOT RUN
- [ ] TOK.FREEZE Final evidence run at freeze · SIGNOFF-SPRINT-11 · WAITS · → TOK.DS, → TOK.QW
- [ ] MU.CURVE Latency-throughput curve vs A100 80GB · SIGNOFF-SPRINT-11 · WAITS · → TOK.FREEZE

## FLOW · Flow release + workflow (OWNER 12.27)
- [ ] FLOW.TAGS Tags per covered class (12.27c tag scope) · FLOW-16 · RUNNING · b-qc/b-kv @9cf9419c0; b-s81/b-head @01ed95d1c (core/legacy re-sign + hd_turn_a only); b2-s81 → S81.TAPW; KV re-tag → KV core canary; b-hbm → first signed HBM pilot
- [ ] FLOW.PILOT Pilot per die x kit class before volume (12.27a) · KIT-WAVE-5 · RUNNING · pilot_gate live on hub; class table in lanes/KIT-WAVE-5.md; 0 classes signed
- [ ] FLOW.DEFON Class fixes default-on (12.27b) + gen-time lint (12.27d) · AUTOBUILD-PIPE-5 · RUNNING · gen_lint live; pinslot landing default-on; diamond legalizer + --gpl-plain flip after class canary
- [ ] FLOW.COUNT Honest count + re-sign · SIGNOFF-SPRINT-11 · RUNNING · hourly forced refresh; counter clk-pin convention fixed (HEAD 3/4)

## INFRA · Merge, hosts, disks
- [ ] INFRA.MERGE Approved READY lines merged in order · ROOT-MERGE-AI · RUNNING · ~35 merges 00:30-05:30 (main da25e3ac0ea+)
- [ ] INFRA.DISK Disks · INFRA-DISK-3 · PASS · 07:04 localhost root 90%; scratch intel1 82%, intel2 79%, epyc2 79%
- [ ] INFRA.WATCHDOG 2-h hung-job watchdog (12.22) · autopilot · RUNNING · STOP 4 this morning (incl 10 h yosys stall)

## WAITS · who
### Waiting on the owner
- none open. Defaults in force: S81 global START registered recompose, real PMA view/period/source, QC UCIe lclk, HBM stack3/Engram mapping, KV T6.
### Waiting on COORD / ROOT-MERGE
- none open (all READY/ASK lines through 05:2x ruled).
