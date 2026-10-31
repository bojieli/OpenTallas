# OpenTallas release tree (pending only; refreshed 2026-10-31 16:21 PDT by CLAUDE coordinator)

_Updated 10-31 16:21 by COORD. OWNER 12.25 slack gate / 12.26 HBM tree||mesh / 12.27 pilot-first / 12.28b closure first, no new restrictive rules. Count 44 signed hard-core designs: S81 21/54, HEAD 3/4, QC 4/14, KV 14/35, HBM 2/84; 0 of ~485 types signed. main b33ff124414+ (ROOT-MERGE-AL merging 16:0x batch)._

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
- [ ] S81.CLK Die clock 12.25 · DIE-S81-44 · PASS (kits pending) · rt4: contract 0 (bk_sel margin 0.03), TT +3.85, CA PASS; FF hold BLOCKED(kits)
- [ ] S81.BIND Strict bind on cb76 (WNEG rings) · DIE-S81-44 · RUNNING · intel1 die-s81-44/bindm, VERIFY ~17:30 → KIT-WAVE-8 ring kits re-cut
- [ ] S81.SERDES PMA views + KP4 SRAMs · S81-SERDES-PHY-3 · READY (approved 16:0x) · G0C = base; pads[].macro_pin opt-in
- [ ] S81.KVLEAF kv_leaf__t2 census + ve_m GDS + bk_sel views · DIE-S81-44 · TODO
- [ ] S81.STA Die STA on real views · DIE-S81-44 · WAITS · → S81.TILES
  - [ ] S81.TILES Tile sign-offs · S81-CORES-KITS-12 / KIT-WAVE-8 · RUNNING · 21/54 (vn_b 15:13); xfin LEC false NEQ → FLOW-19 lecsib fix; ROM qxpq hold, vs s1 DRC ECO, bf_front_roots hold, cap_rt, capc5r parent tool (approved)

## DIE s81_head · HEAD · rev l48c (main) · FROZEN 12.20 (l47u exception)
- [ ] HEAD.CLK Die clock 12.25 · DIE-HEAD-51 · WAITS · GRT 0, TT +201.62, CA lo +141.5; block contracts wait signed kits
- [ ] HEAD.RINGHOLD CA ring WFALL · HEAD-RINGHOLD-2 · READY (approved 16:0x) · hd_turn_a l48f ring hold 0/2973 viol; route + sign running; then st_turn/k5/n4 (DIE-HEAD-51)
- [ ] HEAD.SERDES hd_serdes last core · HEAD-SERDES-3 · RUNNING · DRC fixed; routed TT -99 → e3 sizing ECO (est +31) in DRT, auto re-sign + LEC; e4 fallback
- [ ] HEAD.HOSTLEC HOST LEC hints · DIE-HEAD-51 · RUNNING · LEC C ~20:00 → READY 3af0682a7
- [ ] HEAD.STM hd_st_m 105 TT slew + parent hold · DIE-HEAD-51 · TODO
  - [ ] HEAD.TILES Tile sign-offs · DIE-HEAD-51 · RUNNING · 3/4 hard cores, 0/25 types

## DIE qwen_compute · QC · rev plan_qc52 gen52b · HARD FROZEN 12.22
- [ ] QC.CLK Die clock 12.25 · DIE-QC-55 · FAIL · per-type windows + region tighten; rerun on nominal single default
- [ ] QC.PROG qfd_dv_s8x_prog re-route (routed DB deleted 13-15 h) · DIE-QC-55 · TODO · top priority
  - [ ] QC.TILES Tile sign-offs · DIE-QC-55 / KIT-WAVE-8 · RUNNING · 4/14 (counter on plan_qc52; q1r/q3e/btab), 0/119 types

## DIE qwen_kvsys · KV · rev plan_c + cad8 (L430_0 depth 8, merging) · HARD FROZEN 12.20
- [ ] KV.CLK Die clock 12.25 · DIE-KV-57 · PASS (kits pending) · ptw + seam 180: contract 0 GRT + mix; cad8 fixes last -1.6 ps guard → BLOCKED(kits)
- [ ] KV.FN token_epoch · KV-FN-5 · RUNNING · cause = bench far-end placeholder witness; bench fix a30a5ce76 (no re-signs); proof run A ~16:15; rtlB = parallel variant only
- [ ] KV.ECTL ectl quarters · DIE-KV-57 · RUNNING · q0g_hA signed, LEC running → count; q0r/q2dr routing
- [ ] KV.IOFT kv3_io_ft / io_ft_v1 / hroot GEOM FAIL PLAN · DIE-KV-57 · TODO · one-block
  - [ ] KV.TILES Tile sign-offs · DIE-KV-57 / KIT-WAVE-8 · RUNNING · 14/35 (phy_pad), 0/56 types; wave re-cut on main 15:52

## DIE hbm · HBM · rev d44o (kits) / d44p (hub window 80) · HARD FROZEN 12.22
- [ ] HBM.HUBMESH Hub mesh a3e6s · HBM-HUBMESH-7 · RUNNING · GRT: TT +490/+510, needed W 65/70 ≤80 PASS; DRT iter0 58k viol → NDR/strap fix if not <1k by iter 8
- [ ] HBM.CLKLOC SM street clock C9d/C10 · HBM-CLKLOC-5 · RUNNING · TT +381.7, 626 contract viol at W160 → nominal single default (approved) + C10
- [ ] HBM.GRT Die GRT0 ≥50 it · DIE-HBM-55 · RUNNING · g50 probes
- [ ] HBM.RECIPES 9 NO_RECIPE views · DIE-HBM-55 · READY (approved) · 8/9 build (499a445db5b); lane_exp0_id → HBM-CORES-KITS-36
- [ ] HBM.OPSTORE opstore column read stage + clock entries · HBM-CORES-KITS-36 · RUNNING
  - [ ] HBM.TILES Tile sign-offs · HBM-CORES-KITS-36 / KIT-WAVE-8 · RUNNING · 2/84; QUERY MAXTREE kits PASS-COND geometry; hcol kA/kB placed

## TOKEN · Token-pass gate per design
- [ ] TOK.HBM HBM speed · TOK · PASS · ~1677 tok/s accepted (12.21)
- [ ] TOK.DS DeepSeek ROM token pass (S81 + head) · TOK · BLOCKED · → S81.TILES
- [ ] TOK.QW Qwen ROM token pass (QC + KV) · TOK · BLOCKED · → KV.FN
- [ ] TOK.E2E End-to-end token pass · TOK · NOT RUN

## FLOW · Flow release + workflow (OWNER 12.27)
- [ ] FLOW.TAGS Flow tags on main b33ff124414+ · FLOW-19 · RUNNING · h-* on 0a1b32325; re-cut after 16:0x batch
- [ ] FLOW.LEC lec.py paired-sibling closure (xfin) · FLOW-19 · RUNNING · 12bd7f93413, approved on xfin EQ
- [ ] FLOW.COUNT Honest count + re-sign · SIGNOFF-SPRINT-14 · RUNNING · hourly refresh; PROTECTED-DBS.txt

## INFRA · Merge, hosts, disks
- [ ] INFRA.MERGE Approved READY merged in order · ROOT-MERGE-AL · RUNNING · 16:0x batch: clkloc-5, head-ringhold-2, kv cad8, serdes-phy-3, capc5r, reaper, die-hbm-54, ppendif
- [ ] INFRA.DISK intel1 scratch 88% · INFRA-DISK-5 · RUNNING · intel2 77%, epyc2 77%; reaper keeps protected DBs (FLOW-19)
- [ ] INFRA.LOAD Hosts saturated · COORD · intel2 212/112, intel1 162/112, epyc2 94/128

## WAITS · who
### Waiting on the owner
- none open.
### Waiting on COORD / ROOT-MERGE
- none open (all READY/ASK through 16:0x ruled).
