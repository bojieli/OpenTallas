# OpenTallas release tree (pending only; refreshed 2026-10-31 18:2x PDT by CLAUDE coordinator)

_Updated 10-31 18:2x by COORD. OWNER 12.25 slack gate / 12.26 HBM tree||mesh / 12.27 pilot-first / 12.28b closure first, no new restrictive rules. Count 45 signed hard-core designs: S81 21/54, HEAD 3/4, QC 5/14, KV 14/35 (q0g_hA replaced old q0), HBM 2/84; 0 of ~485 types signed. main bfdc480ffc7+ (ROOT-MERGE-AL: clkloc-5, KV-58 geom, dh51-st h queued)._

## EDIT · rules
- PENDING items only, one short line each, edited in place. Remove an item when done (evidence goes in PATH-FREEZE.md / lane files).
- Line form: `- [ ] ID task · OWNER · STATUS · current fact → DEP.ID` ; "→ X" means this item waits on X (each → is a link).
- Gate ids per die are PFX.INFRA / PFX.GRT / PFX.CLK / PFX.BIND / PFX.STA.
- OWNER 12.18 (2026-10-29 05:44 PDT): full-gate census per die -> lanes/CLOSURE-LIST.tsv (fixed list); rule freeze (new checks only by owner); hourly burn-down open/closed/added; all 5 dies in parallel.
- OWNER 12.17 (2026-10-29 05:31 PDT): freeze plan on die GRT0+clock pass (fix-only after); one clock tool ot_clk.py for all dies; 2 parallel fix variants per failing gate; strict bind clean before GRT counts.
- DIE METHOD = METHODOLOGY s12 v5.1 (v5.0: early taps = macro insertion balancing, AOCV 0.21%/mm gates; v5.1: trims/useful skew/pads sparse <=~5% + CLOCK-RESIDUAL ledger after structural fix; 5%/15% cost = targets) (OWNER 10-26, frozen; change only on measured failure + owner decision): 12.7 MASTER PLAN FIRST per die (census -> corridors <=0.6 -> bays <=405 um every path/layer -> M7 entry pins -> worst-case PG, PG-shielded clock, islands clock/reset only, one core latency) + static plan gates incl. analytic predictor BEFORE any block build; kits carry a plan slice. 12.8 clock by construction: plan-defined centre clock entry per core, 250 ps TT, structured core trees; NO early taps / post-measurement trims / clock ECOs / mesh-node CPPR (plan-computed per-tap sizing OK). Freeze = GRT0 incl clock (>=50 it) + DIE STA with the real clock on related pairs (TT setup, FF hold; CPPR to last tree node); 80 ps skew = design target only. v4.6-4.9: MSCTS H-tree->ONE continuous mesh (signed mesh = CPPR point)->short local trees; clock OCV = depth/distance table (draft, owner review); droop shared (clock charged differential only); data hold buffers allowed. 12.9: one owner per die plan/clock (lanes/OWNERS-DIE.md); gate numbers via NUMBER-CHECK.
- Release gate = die STA on real views + token pass.
- Status words: RUNNING WAITS TODO NEW COORD OWNER FAIL PASS FROZEN BLOCKED NOT RUN.

## DIE s81 · S81 · rev plan cb76a9754330 (main: rt4 + ringfall + t30/t46b) → bfe27b2c00be (SerDes PMA/KP4 replay, merging) · HARD FROZEN 12.20
- [ ] S81.CLK Die clock 12.25 · DIE-S81-45 · PASS (kits pending) · single default on BFE/LOTS: TT +51.86, contract need 132.95 vs W 180, CA PASS; FF hold BLOCKED(kits)
- [ ] S81.BIND Strict bind on cb76 · DIE-S81-45 · RUNNING · BIND_RC 0; verify rerun after OOM (ot-run oth-ubuntu-3631073, 300 GB, intel1) → KIT-WAVE-8 ring kits
- [ ] S81.SERDES t12 WS3 replan (hand-built V2) + t13/t4 lots pilots · DIE-S81-45 / KIT-WAVE-8 · RUNNING · lots bccb99bde74 MERGED 17:24
- [ ] S81.KVLEAF kv_leaf__t2 2.03 M cells (>400k cap) → bank macro + hard cores (owner default B) · DIE-S81-45 · TODO
- [ ] S81.STA Die STA on real views · DIE-S81-45 · WAITS · → S81.TILES
  - [ ] S81.TILES Tile sign-offs · S81-CORES-KITS-12 / KIT-WAVE-8 · RUNNING · 21/54; xfin LEC NEQ 30 pts → FLOW-19 lecsib d7fc5d9af79 rerun ~20:00

## DIE s81_head · HEAD · rev l48w (main) · FROZEN 12.20 (l47u exception)
- [ ] HEAD.CLK Die clock 12.25 · DIE-HEAD-52 · BLOCKED(kits) · START leaves real (dh51-st h e12b72e5132 approved): start-skew 0, contract 0, TT +252.75; rerun with fstart at fclk fall + rst_start_raw_2 pin fix
- [ ] HEAD.RINGHOLD CA ring WFALL · HEAD-RINGHOLD-2 · RUNNING · hd_turn_a routed: ring hold 0, TT +141.85, kit hold +7.1; PRD slew then sign-off + LEC
- [ ] HEAD.SERDES hd_serdes last core · HEAD-SERDES-3 · RUNNING · DRC fixed; routed TT -99 → e3 sizing ECO (est +31) in DRT, auto re-sign + LEC; e4 fallback
- [ ] HEAD.HOSTLEC HOST LEC hints · DIE-HEAD-52 · RUNNING · LEC C ~20:00 → READY 3af0682a7
- [ ] HEAD.KITS l48w kits st_turn/k5/n4 (contract-relative hold limit, 18:0x) + hd_st_m PRD B + hd_tile C9b GEOM FAIL (grt 1916) · DIE-HEAD-52 · RUNNING
  - [ ] HEAD.TILES Tile sign-offs · DIE-HEAD-51 · RUNNING · 3/4 hard cores, 0/25 types

## DIE qwen_compute · QC · rev plan_qc52 gen52b · HARD FROZEN 12.22
- [ ] QC.CLK Die clock 12.25 · DIE-QC-56 · FAIL → one value event approved 18:0x (+1 cycle ~138 crossings + per-type windows + seam) on winning gen55 tree (~19:00)
- [ ] QC.SULANE su_lane_w x7 pilot kit l1 + QC-PLAN pin event (approved 18:0x, parallel) · DIE-QC-56 · RUNNING
  - [ ] QC.TILES Tile sign-offs · DIE-QC-56 / KIT-WAVE-8 · RUNNING · 5/14 (prog V2 counted), 0/119 types

## DIE qwen_kvsys · KV · rev plan_c + cad8 (L430_0 depth 8, merging) · HARD FROZEN 12.20
- [ ] KV.CLK Die clock 12.25 · DIE-KV-58 · BLOCKED(kits) · GEOM-93 taps rerun: TT +413.66, contract 0, CA 0/3595; mix DRT proof rebuild pending
- [ ] KV.FN token_epoch · KV-FN-6 · RUNNING · bench fix alone fails (START race); rtlB 992dcf00d proof kvfn5-HC ~19:00 → READY
- [ ] KV.ECTL ectl quarters · DIE-KV-58 · RUNNING · q0g_hA counted (replaces old q0); q0r/q2dr routing
- [ ] KV.IOFT kv3_io_ft / io_ft_v1 / hroot plan geom 4a6ed13b45e approved 18:0x · DIE-KV-58 → KIT-WAVE-8 re-cut
  - [ ] KV.TILES Tile sign-offs · DIE-KV-57 / KIT-WAVE-8 · RUNNING · 14/35 (phy_pad), 0/56 types; wave re-cut on main 15:52

## DIE hbm · HBM · rev d44o (kits) / d44p (hub window 80) · HARD FROZEN 12.22
- [ ] HBM.HUBMESH Hub mesh a3e6s · DIE-HBM-57 · RUNNING · fat-via NDR a1019de887a crop clean; full-hub DRT ~02:00
- [ ] HBM.CLKLOC Die-wide clock (SM C10i + hub mesh + T010 own form) · HBM-CLKLOC-6 · RUNNING · SM contract 0/8844; clkloc-5 7a45300f6c3 approved
- [ ] HBM.GRT Die GRT0 ≥50 it · DIE-HBM-57 · RUNNING · per-bit station siting r3_0.08: b110 50-it ~00:30, q_b011 ~07:00 11-01
- [ ] HBM.RECIPES NO_RECIPE views · DIE-HBM-57 · RUNNING
- [ ] HBM.OPSTORE opstore_a capture fix (read stage merged, not sufficient; repair_design 750k bufs) · HBM-CORES-KITS-37 · RUNNING
  - [ ] HBM.TILES Tile sign-offs · HBM-CORES-KITS-37 / KIT-WAVE-8 · RUNNING · 2/84

## TOKEN · Token-pass gate per design
- [ ] TOK.HBM HBM speed · TOK · PASS · ~1677 tok/s accepted (12.21)
- [ ] TOK.DS DeepSeek ROM token pass (S81 + head) · TOK · BLOCKED · → S81.TILES
- [ ] TOK.QW Qwen ROM token pass (QC + KV) · TOK · BLOCKED · → KV.FN
- [ ] TOK.E2E End-to-end token pass · TOK · NOT RUN

## FLOW · Flow release + workflow (OWNER 12.27)
- [ ] FLOW.TAGS Flow tags + contract-relative hold_gate default (18:0x) · FLOW-19 · RUNNING
- [ ] FLOW.LEC lec.py sibling + constant-trace closure (xfin) · FLOW-19 · RUNNING · d7fc5d9af79 x4b rerun ~20:00; merge only on EQ
- [ ] FLOW.COUNT Honest count + re-sign · SIGNOFF-SPRINT-14 · RUNNING · hourly refresh; PROTECTED-DBS.txt

## INFRA · Merge, hosts, disks
- [ ] INFRA.MERGE Approved READY merged in order · ROOT-MERGE-AL · RUNNING · queued: clkloc-5 7a45300f6c3, KV-58 geom 4a6ed13b45e, dh51-st e12b72e5132
- [ ] INFRA.DISK scratch intel1 80% / intel2 81% / epyc2 80% · COORD · OK (<85%); reaper fix deployed (FLOW-19)
- [ ] INFRA.LOAD Hosts saturated · COORD · intel2 133/112, intel1 127/112, epyc2 92/128

## WAITS · who
### Waiting on the owner
- none open.
### Waiting on COORD / ROOT-MERGE
- none open (all READY/ASK through 18:02 ruled).
