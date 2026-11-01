# OpenTallas release tree (pending only; refreshed 2026-10-31 21:2x PDT by CLAUDE coordinator)

_Updated 10-31 21:2x by COORD. OWNER 12.25 / 12.26 / 12.27 / 12.28b closure first. Count 46: S81 21/54, HEAD 3/4, QC 5/14, KV 14/35, HBM 3/84 (+tail_native); 0 of ~485 types signed. main 7997c0149+. Queue ROOT-MERGE-AL: prdlib, xrf, clkloc-6, io_cor, padclk-cdc, otstat; dh52-tile2 after kit route + canary._

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
- [ ] S81.CLK Die clock 12.25 · DIE-S81-45 · PASS (kits pending) · TT +51.86, need 132.95 vs W 180; + early taps bksel_c/gunit_l3/xrt1 approved 19:0x
- [ ] S81.BIND Strict bind on cb76 · DIE-S81-45 · PASS · bindm VERIFY_RC 0 (8.3M compared, 0 mismatch) 20:16; kit wave on f1a8dcffa6e
- [ ] S81.SERDES t12 WS3 replan (hand-built V2) + t13/t4 lots pilots · DIE-S81-45 / KIT-WAVE-8 · RUNNING · lots bccb99bde74 MERGED 17:24
- [ ] S81.KVLEAF kv_leaf__t2 2.03 M cells (>400k cap) → bank macro + hard cores (owner default B) · DIE-S81-45 · TODO
- [ ] S81.STA Die STA on real views · DIE-S81-45 · WAITS · → S81.TILES
  - [ ] S81.TILES Tile sign-offs · S81-CORES-KITS-13 / KIT-WAVE-10 · RUNNING · 21/54 (5 h flat); bf_front_roots ECO DRT; serdes rck/clk CDC settled (padclk-cdc opt-in)

## DIE s81_head · HEAD · rev l48x (approved 19:0x: l48w + 51 rst_start_raw pin moves) · FROZEN 12.20 (l47u exception)
- [ ] HEAD.CLK Die clock 12.25 · DIE-HEAD-52 · BLOCKED(kits) · l48x + START leaves h + --ca-write-fall: TT +252.75, contract 0, start-skew 0
- [ ] HEAD.RINGHOLD CA ring WFALL · HEAD-RINGHOLD-2 · RUNNING · hd_turn_a routed: ring hold 0, TT +141.85, kit hold +7.1; PRD slew then sign-off + LEC
- [ ] HEAD.SERDES hd_serdes last core · HEAD-SERDES-3 · RUNNING · DRC fixed; routed TT -99 → e3 sizing ECO (est +31) in DRT, auto re-sign + LEC; e4 fallback
- [ ] HEAD.HOSTLEC HOST LEC hints · DIE-HEAD-52 · RUNNING · LEC C ~20:00 → READY 3af0682a7
- [ ] HEAD.KITS l48x wave: st_str/turn_b/st_m PASS-COND; hd_tile wave kit lacks tile51 recipe → held until dh52-tile2 (l48y) merges · DIE-HEAD-52 / KIT-WAVE-10 · RUNNING
  - [ ] HEAD.TILES Tile sign-offs · DIE-HEAD-51 · RUNNING · 3/4 hard cores, 0/25 types

## DIE qwen_compute · QC · rev plan_qc52 gen52b · HARD FROZEN 12.22
- [ ] QC.CLK Die clock 12.25 · DIE-QC-57 · FAIL (landed class) · gen55a no trims, contracts 0 with ptw 345b2ee7941; + +1-cycle event on ~138 crossings → BLOCKED(kits)
- [ ] QC.SULANE su_lane_w x7 pilot kit l1 + QC-PLAN pin event · DIE-QC-57 · RUNNING
  - [ ] QC.TILES Tile sign-offs · DIE-QC-57 / KIT-WAVE-9 · RUNNING · 5/14, 0/119 types; A0 NK/NL structural fix 2 variants

## DIE qwen_kvsys · KV · rev plan_c + cad8 (L430_0 depth 8, merging) · HARD FROZEN 12.20
- [ ] KV.CLK Die clock 12.25 · DIE-KV-59 · BLOCKED(kits) · TT +413.66, contract 0, CA 0/3595; mix proof ~22:30
- [ ] KV.FN token_epoch FIXED (merged 7997c0149); next abort kv 41597 d2d TX not valid (emb tx2 suspect) · KV-FN-7 · RUNNING · probe P ~00:30, 2 fix variants
- [ ] KV.ECTL ectl quarters · DIE-KV-59 · RUNNING · q0 counted; q2_grtD stuck at 8 DRT → 2 variants
- [ ] KV.IOFT io_ft / io_ft_v1 / hroot re-cut on KV-58 form (form works, hroot FAIL PLAN better); io_cor 32d3e2665d2 approved · DIE-KV-59 / KIT-WAVE-10
  - [ ] KV.TILES Tile sign-offs · DIE-KV-59 / KIT-WAVE-10 · RUNNING · 14/35; token re-signs hub_Wi/hr_core_peer/hr_core_tx

## DIE hbm · HBM · rev d44o (kits) / d44p (hub window 80) · HARD FROZEN 12.22
- [ ] HBM.HUBMESH Hub mesh a3e6s · DIE-HBM-57 · RUNNING · fat-via NDR a1019de887a crop clean; full-hub DRT ~02:00
- [ ] HBM.CLKLOC Die-wide clock · HBM-CLKLOC-7 · FAIL 44 · C11m (12c8eb1f3a3 approved): contract 77,189 -> 44, TT +44.93; T010 x14200 gap 2 variants + 1 landed aggregate → target BLOCKED(kits)
- [ ] HBM.GRT Die GRT0 ≥50 it · DIE-HBM-57 · RUNNING · per-bit station siting r3_0.08: b110 50-it ~00:30, q_b011 ~07:00 11-01
- [ ] HBM.RECIPES NO_RECIPE views · DIE-HBM-57 · RUNNING
- [ ] HBM.OPSTORE opstore_a capture fix (read stage merged, not sufficient; repair_design 750k bufs) · HBM-CORES-KITS-37 · RUNNING
  - [ ] HBM.TILES Tile sign-offs · HBM-CORES-KITS-37 / KIT-WAVE-10 · RUNNING · 3/84 (+tail_native 21:13); exp0 hold (a) approved; tail1 kit queued

## TOKEN · Token-pass gate per design
- [ ] TOK.HBM HBM speed · TOK · PASS · ~1677 tok/s accepted (12.21)
- [ ] TOK.DS DeepSeek ROM token pass (S81 + head) · TOK · BLOCKED · → S81.TILES
- [ ] TOK.QW Qwen ROM token pass (QC + KV) · TOK · BLOCKED · → KV.FN
- [ ] TOK.E2E End-to-end token pass · TOK · NOT RUN

## FLOW · Flow release + workflow (OWNER 12.27)
- [ ] FLOW.PRD prd_mk keeps TC_LIB macro libs (f4c918a648c approved) → re-sign PRD'd HBM SRAM kits · FLOW-19 / SIGNOFF-SPRINT-15
- [ ] FLOW.LEC lec.py sibling + constant-trace closure (xfin) · FLOW-19 · RUNNING · d7fc5d9af79 x4b rerun ~20:00; merge only on EQ
- [ ] FLOW.COUNT Honest count + re-sign · SIGNOFF-SPRINT-15 · RUNNING · hourly refresh; PROTECTED-DBS 151 rows

## INFRA · Merge, hosts, disks
- [ ] INFRA.MERGE Approved READY merged in order · ROOT-MERGE-AL · RUNNING · see header queue
- [ ] INFRA.DISK scratch intel1 75% / intel2 79% / epyc2 84% (watch) · COORD · OK
- [ ] INFRA.LOAD Hosts saturated · COORD · intel2 270/112, intel1 116/112, epyc2 108/128

## WAITS · who
### Waiting on the owner
- none open.
### Waiting on COORD / ROOT-MERGE
- none open (all READY/ASK through 21:13 ruled).
