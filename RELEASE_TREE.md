# OpenTallas release tree (pending only; coordinator update 2026-11-01 08:22 PST)

_COORD 2026-11-01 08:22 PST: back after limit; Codex 05:44-08:13 merged gl1-lvn/int/qfill/leccc/G5/mchan2/childlib/hb4/suw-lec/kv macro+g0c (main e1aa524c9). Count 48 (S81 22/54, HEAD 3/4, QC 5/15, KV 14/35, HBM 4/84) -> 49 at refresh (gunit_l1). Merge train: kv phytap, s81 t48tap, kv-viewclosure, hbm stations 8717480994c, hbm shared clock 584a15b09+tools, ORFS power, TOK-DS, KV ahub (GRT50 ov0 viewed PASS). Types 0/485: classes -> S81 parent_budget (DIE-S81-47), fill/empty exception (KIT-TRIAGE-1), LEC NEQ @place (FLOW-21). 19 lanes resumed._

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
- [ ] S81.CLK Die clock 12.25 · DIE-S81-45 · PASS (kits pending) · plan dd2cd280def6 (16 early taps + t4/t13 collector fix) APPROVED 21:4x: GRT 0, TT +49.70, CA 0
- [ ] S81.BIND Strict bind on cb76 · DIE-S81-45 · PASS · bindm VERIFY_RC 0 (8.3M compared, 0 mismatch) 20:16; kit wave on f1a8dcffa6e
- [ ] S81.SERDES t12 WS3 V2 537b916454f APPROVED (after etap); 8 serdes pilots in LEC on epyc2 · DIE-S81-46 / KIT-WAVE-10 · RUNNING
- [ ] S81.KVLEAF kv_leaf__t2 a3 three-slot TAG 407b175146b APPROVED (G0C 0 new, die clock same, bind 0) -> 30 types + 11 serdes re-cut · DIE-S81-47 / KIT-WAVE-12
- [ ] S81.STA Die STA on real views · DIE-S81-45 · WAITS · → S81.TILES
    - [ ] S81.TILES Tile sign-offs · S81-CORES-KITS-13 / KIT-WAVE-13 · RUNNING · 22/54 (+gunit_l1 at refresh); xrt1 P3M70/P3M110, crs4, bf_front_roots, xfin; QBS20/CFG7 Codex receipts

## DIE s81_head · HEAD · rev l48x (approved 19:0x: l48w + 51 rst_start_raw pin moves) · FROZEN 12.20 (l47u exception)
- [ ] HEAD.CLK Die clock 12.25 · DIE-HEAD-53 · BLOCKED(kits) · l48x + START leaves h + --ca-write-fall: TT +252.75, contract 0
- [ ] HEAD.RINGHOLD hd_turn_a SIGNED l48x (TT +142.43 / FF +9.46, LEC EQ) -> count by SIGNOFF-SPRINT-15 · DONE pending count
- [ ] HEAD.SERDES hd_serdes e3 DRT ~it 55/64, 17-22 viol, ~2 h/it -> parallel incremental reroute / 2nd variant · HEAD-SERDES-3 · RUNNING
- [ ] HEAD.HOSTLEC HOST LEC hints · DIE-HEAD-52 · RUNNING · LEC C ~20:00 → READY 3af0682a7
- [ ] HEAD.KITS hold limit -100+min(0,in_min+40,-W_t) approved 22:0x: hd_spn_end l49x routes; hd_tile l48y 3 variants (tap assign / port offsets / hold repair); hd_st_m local PASS needs parent hold · DIE-HEAD-53 / KIT-WAVE-10 · RUNNING
  - [ ] HEAD.TILES Tile sign-offs · DIE-HEAD-53 · RUNNING · 3/4 hard cores, 0/25 types

## DIE qwen_compute · QC · rev plan_qc52 gen52b · HARD FROZEN 12.22
- [ ] QC.CLK Die clock 12.25 · DIE-QC-58 · BLOCKED(kits) · A2 + collector fix 00452027cbe approved (strict bind 0); QC enters wave at merge
- [ ] QC.SULANE su_lane LEC NEQ = reset window -> QC rst_n >=64 clk contract approved; then pin event READY · DIE-QC-58 · RUNNING
  - [ ] QC.TILES Tile sign-offs · DIE-QC-58 / KIT-WAVE-12 · RUNNING · 5/14; A0 NK/NL single root gate PASS-COND (GRT>=50 it, NL LEC 2 UNPROVEN)

## DIE qwen_kvsys · KV · rev plan_c + cad8 (L430_0 depth 8, merging) · HARD FROZEN 12.20
- [ ] KV.CLK Die clock 12.25 · DIE-KV-60 · BLOCKED(kits) · mix proof 01:3x: TT +595.71, contract 0, CA 0/3595, kit hold PASS; 37674 pairs UNMEASURED (no real views)
- [ ] KV.FN token_epoch FIXED; 41597 d2d fix 00aa31544 APPROVED (es145 passes); next abort kv 42327 far KVN port-3 · KV-FN-7 · RUNNING
- [ ] KV.ECTL q2 v3c/v3d DRC 0, hold -3.32 + slew ECO -> sign at k-kv · DIE-KV-60 · RUNNING
- [ ] KV.IOFT kv3_phy2 1d2d0b3fc36 + io_ft 57cc33983e2 approved; hroot relay_sites + (A) stations; pc_v1 class (13 items, core tap means) plan fix · DIE-KV-60 / KIT-WAVE-12 · RUNNING
  - [ ] KV.TILES Tile sign-offs · DIE-KV-60 / KIT-WAVE-11 · RUNNING · 14/35; token re-signs core_tx (re-kit) / core_peer / hub_Wi

## DIE hbm · HBM · rev d44o (kits) / d44p (hub window 80) · HARD FROZEN 12.22
- [ ] HBM.HUBMESH Hub mesh a3e6s · DIE-HBM-57 · RUNNING · fat-via NDR a1019de887a crop clean; full-hub DRT ~02:00
- [ ] HBM.CLKLOC Die-wide clock · CODEX HBM clock · BLOCKED(clock-feed/kits) current G4: actual roots NW (9437.08,7534.08), NE (18807.16,6696); source distances from T028/T029 are4776.88/1487.74um. Paired actual-source local bridges now DRC0 and matched-mesh CA773/773 TT+FF PASS, TTsetup+93.69ps; B selected candidate costs+164 aggregate table cycles/32START retimes. Production clock/island/joint-route integration,396182 hold-pair views, and full-hub DRC125/139 remain open. Historical C12e abstract contract0 retained; neither historical nor piecewise probe receipts qualify freeze.
- [ ] HBM.GRT Die GRT0 >=50 it · DIE-HBM-57 · RUNNING · station compose 8717480994c (38 bits <=403 um) merging; VMS GRT50 live epyc2; watchdog killed 4 GRT50 as idle -> CPU-active exemption class; p3 + 41-type sweep
- [ ] HBM.RECIPES NO_RECIPE views · DIE-HBM-57 · RUNNING
- [ ] HBM.OPSTORE opstore_a: GPL never converged (751k bufs) -> plain place 18.6k bufs, oap/oar route · HBM-CORES-KITS-39 · RUNNING
  - [ ] HBM.TILES Tile sign-offs · HBM-CORES-KITS-39 / KIT-WAVE-12 · RUNNING · 4/84; HCOL kA DRT 0 -> sign; QUERY 2 variants; exp0 3 variants

## TOKEN · Token-pass gate per design
- [ ] TOK.HBM HBM speed · TOK · PASS · ~1677 tok/s accepted (12.21)
- [ ] TOK.DS DeepSeek whole-die token sim (S81) on current bind · TOK-DS-2 · RUNNING · started 03:2x PST (never run before)
- [ ] TOK.QW QC whole-die token + QC+KV pair · TOK-QK-2 / KV-FN-7 · RUNNING · pair calendar ruled MU single-seq both dies -> QC u_cseq change DIE-QC-59Q · KV past 41597 (fix 00aa31544), next abort kv 42327
- [ ] TOK.E2E End-to-end token pass · TOK · NOT RUN

## FLOW · Flow release + workflow (OWNER 12.27)
- [ ] FLOW.PRD prd_mk keeps TC_LIB macro libs (f4c918a648c approved) → re-sign PRD'd HBM SRAM kits · FLOW-21 / SIGNOFF-SPRINT-17
- [ ] FLOW.LEC lec.py sibling + constant-trace closure (xfin) · FLOW-19 · RUNNING · d7fc5d9af79 x4b rerun ~20:00; merge only on EQ
- [ ] FLOW.KITS Type-kit classes (OWNER batch) · KIT-TRIAGE-1 / KIT-WAVE-13 · RUNNING · latest 261 FAIL/115 RUN: gen PLAN 118, geom 46 (fill/empty exception), place 23+14 LEC, kit_rtl 19
- [ ] FLOW.COUNT Honest count + re-sign · SIGNOFF-SPRINT-17 · RUNNING · hourly refresh; PROTECTED-DBS 151 rows

## INFRA · Merge, hosts, disks
- [ ] INFRA.MERGE Approved READY merged in order · ROOT-MERGE-AL · RUNNING · see header queue
- [ ] INFRA.DISK scratch 87-91% -> PRUNE-1101B · COORD · RUNNING
- [ ] INFRA.LOAD intel1 290/112, intel2 303/112, epyc2 110/128; waiters 26/30/37 (queue full) · COORD

## WAITS · who
### Waiting on the owner
- none open.
### Waiting on COORD / ROOT-MERGE
- none open (all READY/ASK through 01:20 ruled).
