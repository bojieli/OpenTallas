# OpenTallas release tree (pending only; refreshed 2026-10-26 06:21 PDT by CLAUDE coordinator)

Snapshot: 2026-10-26 06:21 PDT · main 3ab63782a7 · FROZEN: none · no die has die STA on real views · sign-off flat since 10-25 16:23 · flow tag per die (12.9e) being cut · PRIORITY: QC critical path, then S81 / HEAD / KV / HBM on the same template.

## EDIT · rules
- PENDING items only, one short line each, edited in place. Remove an item when done (evidence goes in PATH-FREEZE.md / lane files).
- Line form: `- [ ] ID task · OWNER · STATUS · current fact → DEP.ID` ; "→ X" means this item waits on X (each → is a link).
- Gate ids per die are PFX.INFRA / PFX.GRT / PFX.CLK / PFX.BIND / PFX.STA.
- DIE METHOD = METHODOLOGY s12 v5.1 (v5.0: early taps = macro insertion balancing, AOCV 0.21%/mm gates; v5.1: trims/useful skew/pads sparse <=~5% + CLOCK-RESIDUAL ledger after structural fix; 5%/15% cost = targets) (OWNER 10-26, frozen; change only on measured failure + owner decision): 12.7 MASTER PLAN FIRST per die (census -> corridors <=0.6 -> bays <=405 um every path/layer -> M7 entry pins -> worst-case PG, PG-shielded clock, islands clock/reset only, one core latency) + static plan gates incl. analytic predictor BEFORE any block build; kits carry a plan slice. 12.8 clock by construction: plan-defined centre clock entry per core, 250 ps TT, structured core trees; NO early taps / post-measurement trims / clock ECOs / mesh-node CPPR (plan-computed per-tap sizing OK). Freeze = GRT0 incl clock (>=50 it) + DIE STA with the real clock on related pairs (TT setup, FF hold; CPPR to last tree node); 80 ps skew = design target only. v4.6-4.9: MSCTS H-tree->ONE continuous mesh (signed mesh = CPPR point)->short local trees; clock OCV = depth/distance table (draft, owner review); droop shared (clock charged differential only); data hold buffers allowed. 12.9: one owner per die plan/clock (lanes/OWNERS-DIE.md); gate numbers via NUMBER-CHECK.
- Release gate = die STA on real views + token pass.
- Status words: RUNNING WAITS TODO NEW COORD OWNER FAIL PASS FROZEN BLOCKED NOT RUN.

## INFRA-FIRST · shared tool (all dies)
- [ ] IF.TOOL die_infra.py fixed infrastructure: preserve regional cuts + actual connected route import · INFRA-FIRST / CODEX / FLOW · RUNNING · 1d5b87430 fixes regional export; initial qc0 is capacity reservation only; actual ODB clock/PG wires+vias+terminals import tiny PASS, signal GRT50 confirmation running
- [ ] IF.CLK128 die clock tool 12.8 (last-node CPPR, early tap = FAIL, plan sizing, shielded legs) · CLOCK-128-R2 · READY clock128-main 2779c3a553 + default b5fb5d77a8 (after kv-clktools-r3); TODO shield VSS vias; HBM r8 461/384 diag (tree 830-846 ps/region, trunk 3 ns) -> by-construction rebuild
- [ ] IF.MASTER Master plan first (METHODOLOGY v3 12.7, OWNER 10-26 all dies): census -> corridors -> bays <=405 um any layer -> M7 entry pins -> worst-case PG + shielded clock + islands + common core latency; static plan gates before any block build · MASTER-PLAN · RUNNING · QC first, then HEAD/S81/KV/HBM
- [ ] IF.GEN Shared slice-driven core-kit generator (pushdown islands, in-core H-tree, bays, M7 pins), all dies · MASTER-PLAN-R2 · RUNNING · master-plan 979fc60bf0 READY; kits only stamp slice today
- [ ] IF.FALLBACK Bottom-up landed fallback · FALLBACK-LAND · DONE-ANALYSIS (UNCHECKED): area <1%/die; QC -8.6/-12.5% at K=2/3, Qwen pair breaks 15% cap at K=3, S81 -2..-3%, HEAD ~0; viable S81/HEAD/KV, last resort QC/HBM
- [ ] IF.MERGE Merge mesh tool fdb5b851c7 (COORD APPROVED 01:1x) · ROOT-MERGE-16 · WAITS · after its gates

## DIE qwen_compute · Qwen compute · rev UNFROZEN 54a1aeb5 · PROTOTYPE of infra-first
- [ ] QC.PATH CRITICAL PATH end to end (12.9b): 12.7b plan gates -> core rebuilds (12.8) -> die clock (12.8) -> GRT0 -> skew gate -> die STA · INFRA-FIRST · RUNNING · dated ETA checklist in lanes/INFRA-FIRST.md
- [ ] QC.INFRA One QC plan event: infra-first PG/clock/reset + batch 2 (STM ROMs, SRAM, DEAD-FAULT) + D-QC-FE-REACH stations (all FE variants) + COLLFTM-CTL + CB ID straps + SCROOT + vmr_s6kc · INFRA-FIRST + PATH-QC · RUNNING · PENDING-DELTA D-INFRA-FIRST-QC holds all 68 type routes
- [ ] QC.CLK Clock 12.8 (gate = related-pair STA) · INFRA-FIRST-QC-R14 · RUNNING · R13 74/74 types identical, nominal 48.5/39.6, STA TT +537 / kit hold +6.2 (UNCHECKED); dry build 3147 err (M7 risers) -> trunks on M8 tracks + slot rows; centre channel APPROVED, centre row split · ETA freeze est 10-28..29
- [ ] QC.SU 4 SU core types · QC-SU-F4G · DONE-RP1 · F4G RP1 ADOPTED (TT +236.87/FF +5.92/LEC 3703, window 23.2/20.3 CHECKED); F4F = fallback; F4G VMR live (epyc2 unit 714733)
- [ ] QC.GRT Die GRT0 incl. clock on the infra-first plan · INFRA-FIRST · WAITS · → QC.INFRA
- [ ] QC.BIND Strict bind on the QC plan event (wavefront reset/START, CB16 phase classes) · PATH-QC · WAITS · → QC.INFRA
- [ ] QC.STA Die STA on real views · DIE-PROTO · WAITS · → QC.GRT, → QC.TILES
  - [ ] QC.TILES Tile sign-offs · PATH-QC · WAITS · hard cores continue (4/9 signed; no island overlap); types wait for re-freeze; SC kits need LEC fix fffc9dd55 on flow tag

## DIE s81_head · S81 head die · rev UNFROZEN d7b8d1eb · after QC
- [ ] HEAD.INFRA Infra-first plan event (+ HEAD8 batch 187b63494b if approved) · INFRA-FIRST · WAITS · PENDING-DELTA D-INFRA-FIRST-HEAD holds all 16 type routes → IF.TOOL
- [ ] HEAD.CLK elemA/elemB · HEAD-CORE-R12 · RUNNING · hold2 GRT A/B TT +118.5/+120.6, FF hold +10.6/+10.7 (0 viol); neither signed off yet (A 'SIGNED' log was stale 10-25); repaired-export LEC -> route+signoff chains live intel1/epyc2 (10-27 00:27) · ETA freeze est 10-29..30
- [ ] HEAD.GRT Die GRT0 incl. clock on the infra-first plan · INFRA-FIRST · WAITS · old d7b8d1eb signal GRT0 no longer counts → HEAD.INFRA
- [ ] HEAD.BIND Whole-head as-built bind · CODEX / PATH-S81 · WAITS · source d0eb3d3d01; host/mesh/rank-row contract = spec item (no owner input)
- [ ] HEAD.STA Die STA on real views · DIE-PROTO · WAITS · → HEAD.CLK, → HEAD.TILES
  - [ ] HEAD.TILES Head tile sign-offs · S81-HEAD / KITS-WAVE-3 · WAITS · types held by D-INFRA-FIRST-HEAD; 1/2 hard cores signed → HEAD.INFRA

## DIE qwen_kvsys · Qwen KV · rev batch claude/path-kv-batch-0115@650841e1ef (rebase 5665cd3386 + FT reserve + D-KV-CLKMESH)
- [ ] KV.BIND Strict bind of the batch · PATH-KV · RUNNING · B31 a8c24031c strict PASS 160 parts/51 types + R8 0 unequal + full verify 2553368/2553368; final batch (8-region landings, q2 rename, B32 PV) needs one re-bind
- [ ] KV.CLK Clock under 12.8 (gate = related-pair STA) · CLOCK-KV-R17 · RUNNING · mesh variation sign-off (12.8e) + droop-region tool fix + clock_entry on slice 1814a2d8 · ETA freeze est 10-28..29
- [ ] KV.INFRA PG from IR + pre-routed PG/clock/reset via shared tool · PATH-KV · RUNNING · die_infra reset 287 nets max hop 377um PASS; signal GRT50 M4-M9 w/ clock reservation ovf0; PG needs KV power figure (0.15 W/mm2 fallback) → IF.TOOL
- [ ] KV.GRT GRT0 incl. clock on the batch · PATH-KV · PASS · batch 650841e1ef one global_route signals M4-M7 + mesh M8-M9: ovf 0 TT+FF; freeze waits KV.BIND + D-INFRA-FIRST PG/pre-route
- [ ] KV.STA Die STA on real views · CLOCK-KV-R17 · FAIL · first real-view run R16: TT -110.8 / FF -400.5 (31% inst real, UNCHECKED) = unsigned mesh + droop tool bug; w/o AOCV TT +399 / FF -6..-12
  - [ ] KV.TILES Tile sign-offs · PATH-KV / KV-CORES · BLOCKED · KV-CORES-R1 gate 0/24 core types buildable: no 12.8a centre entry + R1-R7 islands in plan hm_r12 96e6d1cb; signed only head e1/e5 → KV.CORE-SLICE
  - [ ] KV.CORE-SLICE One KV core slice (centre entries, in-core islands, M7 entry pins; hr recut, q2 rename, phy_pad outline) · KV-CORE-SLICE-1 · RUNNING → KV-CORES-R2 → KV.CLK

## DIE s81 · S81 (DeepSeek ROM layer die) · rev main · B2 batch
- [ ] S81.B2 One plan event D-S81-B2: A25 + stations v4 + PHY pins + leaf pins + eng SRAM r0c0 + FT alignment/corridors + D-S81-PHY + infra-first · PATH-S81 · RUNNING · gate: lateral jog <5M bit-um → GRT0 → skew
- [ ] S81.GRT Die GRT0 incl clock · PATH-S81-PD6 · GRT0 DONE on PD5 6d6e8b34f9 (TT+FF overflow 0, CHECKED); 13 B5 cut errors -> measured-usage waiver; 17 storage bands fixing · ETA freeze est 10-28..29
- [ ] S81.PHY 14 SerDes windows · PATH-S81 · RUNNING · zero-area fit 14/14; gunit R180 re-plan PASS-COND (GEOM-17); bk_sel option B re-cut 864x483.84 APPROVED (rebuild quarter tile) → S81.B2
- [ ] S81.CLK Clock under 12.8 · PATH-S81 · NOT RUN · replace early taps (gunit u_l5 520, bk_sel u_c 430) with centre entries; cores → S81-CORE-LAT → IF.CLK128
- [ ] S81.BIND Strict bind on main · TOK-DS · PASS on 877cfdeb2 (0 tied, 10,352 straps) → re-run after S81.B2
- [ ] S81.STA Die STA on real views · PATH-S81-PD6 · RUNNING · related-pair STA on PD5 kit (real where signed + budget)
  - [ ] S81.TILES Tile sign-offs · PATH-S81 / CORES-KITS · RUNNING · 4/171 types, 16/52 hard cores signed

## DIE hbm · HBM UNIFIED SU/MTP/MU one design (OWNER 10-26 23:1x; SU latency qualified first) · plan D-HBM-B1 (5fa3c6e64838)
- [ ] HBM.B1 Unified plan of record = planU2 (55ea5ec620f5, 526.571 mm2 CHECKED) hubs H4320 + quad v2 · HBM-MU-QUAD · FAIL G0/G0C · claude/hbm-mu-quad-2-1026@03d5f0266f: NW 0.594/NE 0.586 k3 PASS (CHECKED), n4 order model PASS; G0C: +794.88 shift leaves 4 straddling cols unabutted (8 abutment, L28/L125/L9/L63 hops), MU cores no pins_file → compose fix (move straddlers/fill relays) + pin tables
- [ ] HBM.GRT Die GRT0 incl clock on the UNIFIED plan · PATH-HBM · WAITS · R15 S2/F2 = SU plan (H3525, 16 banks), flow canary only, collect; unified GRT after HBM.B1 + views
- [ ] HBM.CLK Mesh clock 12.8 on unified plan · CLOCK-128 · FAIL/INVALID · r7/r8 on old plan; rebuild after HBM.B1, 4 new types need islands (bank/fused/tnode/keybuf); core-lat R3: 11/28 types gate-PASS, 0 built past place, xcal/ep need structure ruling
- [ ] HBM.BIND Native B2 one-clock bind · PATH-HBM / HC-NATIVE · RUNNING · 98 unread outputs classified (svg redundant views, sm.request/expected check w/o comparator, xl y, ordinals); no open inputs
- [ ] HBM.STA Die related-pair STA real routed clock (TT setup/FF hold) · DIE-PROTO · WAITS · → HBM.GRT; SU latency qualified first (HBM.SU)
- [ ] HBM.SU SU latency qual: ds_ar cycles/token on unified plan (target hub Δ<=5%, design <=15%, owner-accepted ~1973 tok/s) · HBM-MU-QUAD · PARTIAL · planU2 R13 price lower/mid/upper 2.39/2.67/7.88 % = 2031/2025/1917 tok/s (CHECKED arith): lower+mid PASS, upper FAIL 5% + 1973

## TOKEN · Token-pass gate per design
- [ ] TOK.DS DeepSeek ROM token pass (S81 array + head) · TOK-DS-6 · RUNNING · L14 27/57/8; idx scan 3-die shard; S81 all-rows MTP 3,655 tok/s > 3,000 floor (AR 1,260), 17.0% ledger ACCEPTED (owner 10-26) → S81.BIND, → HEAD.BIND
- [ ] TOK.QW Qwen ROM token pass (compute + KV) · TOK · RUNNING · QK vehicle on KV rebased bind; prices landed seams + FE stations → KV.BIND, → QC.INFRA
- [ ] TOK.HDS / TOK.HQ HBM token passes (unified SU/MTP/MU, SU latency first) · TOK · RUNNING · SU programme-path fault (pgslice lw, side_pipe rsq) being root-caused
- [ ] TOK.E2E End-to-end token pass: NOT PASSED on any of 5 dies (components only; QC whole-die waits QC.INFRA, KV B48 boot verdict ~01:00-03:00, S81 L14 10 GAP ops, HEAD full G5, HBM no RTL token replay) · TOK lanes · RUNNING
- [ ] TOK.FREEZE Final evidence run at freeze · COORD · WAITS · → TOK.DS, → TOK.QW
- [ ] MU.CURVE Latency-throughput curve vs A100 80GB · COORD · WAITS · → TOK.FREEZE

## FLOW · Flow release
- [ ] FLOW.TAG Cut flow-20261025-b PER DIE (12.9e, owner 10-26) · ROOT-MERGE-17 · RUNNING · cap64 + cp1-driverview merged (e0d486853); full canary set running since 01:19; KV canary re-baseline; add LEC fix fffc9dd55 + path-qc-2325/iohold if canaries cover them
- [ ] FLOW.HOLD Route holds lift PER DIE on that die's tag (12.9e) · autopilot · WAITS · claude/ap-perdie-tag-1026@a326eea7a4 in review → FLOW.TAG

## INFRA · Merge and probes
- [ ] INFRA.MERGE path-kv-lec 070a15290 (urgent, after full-kit LEC), S81-PHY docs bea83f9105, epyc3-retire 59bb63ed15, mesh tool fdb5b851c7 · ROOT-MERGE-16 · RUNNING
- [ ] INFRA.M89 FT-M89-PROBE: S81/HBM what-ifs (FT on M8/M9; S81 cores at M5), >=50 it · FT-M89-PROBE · RUNNING · result decides any layer-rule proposal to the owner

## REVIEW · independent checks
- [ ] NUM.CHECK Recompute every owner-reported gate number (12.9f) · NUMBER-CHECK · RUNNING · backlog: QC 154/143, KV c3t, HBM r7, QC/S81 GRT, sign-off counts

## WAITS · who
### Waiting on the owner
- none.
### Waiting on COORD / ROOT-MERGE
- COORD-REVIEW-20: 7 READY lines (hbm-core-lat, infra-m89-default, qc-clock-r2 [12.8 check], kv-infra-r2, path-s81-b2d1, path-kv-clktools [12.8 check], ap-perdie-tag).
