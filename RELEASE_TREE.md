# OpenTallas release tree (pending only; refreshed 2026-10-26 06:21 PDT by CLAUDE coordinator)

Snapshot: 2026-10-28 17:20 PDT · main bfc232967f · FROZEN: none · gate numbers only on shared die STA with clock_variation=table (CA >=100 ps) · sign-off flat 12 h (KV e2/e6 signed off, ledger pending) · 12.16e local clock form on all 5 dies · KV plan delta (DIE-KV-14), HEAD GRT0 flow (HEAD-14), QC hold glue (QC-20), S81 go15 ~20:30, HBM SU lanes WCOPY re-place (REBAL-10).

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
- [ ] QC.LAND Per-slice clocks + landed slice crossings (12.10b/12.11, main path) · QC-SLICECLK-1 · RUNNING · price -> plan delta -> GEN -> GRT incl clock -> STA
- [ ] QC.CLK Clock 12.16 local inverter tree · DIE-QC-24 · RUNNING · model OK (sweep); worst ~123 ps c_*_tf_00 not model-limited -> A0-quad mesh pilot (GRT pair U 45-54 ps <= 61) DRT proof QC-MESH-PILOT-2; A0 node lattice re-kit a0k8 (QC-A0-KITS-9)
- [ ] QC.SU 4 SU core types · QC-SU-F4G · DONE-RP1 · F4G RP1 ADOPTED (TT +236.87/FF +5.92/LEC 3703, window 23.2/20.3 CHECKED); F4F = fallback; F4G VMR live (epyc2 unit 714733)
- [ ] QC.GRT Die GRT0 incl. clock on the infra-first plan · INFRA-FIRST · WAITS · → QC.INFRA
- [ ] QC.BIND Strict bind on the QC plan event (wavefront reset/START, CB16 phase classes) · PATH-QC · WAITS · → QC.INFRA
- [ ] QC.STA Die STA on real views · DIE-PROTO · WAITS · → QC.GRT, → QC.TILES
  - [ ] QC.TILES Tile sign-offs · PATH-QC · WAITS · hard cores continue (4/9 signed; no island overlap); types wait for re-freeze; SC kits need LEC fix fffc9dd55 on flow tag

## DIE s81_head · S81 head die · rev UNFROZEN d7b8d1eb · after QC
- [ ] HEAD.INFRA Infra-first plan event (+ HEAD8 batch 187b63494b if approved) · INFRA-FIRST-HEAD-1 · RUNNING (started 01:5x, parallel to QC) · PENDING-DELTA D-INFRA-FIRST-HEAD holds all 16 type routes → IF.TOOL
- [ ] HEAD.LAND Landed regions (12.11, main path) · LAND-HEAD-1 · RUNNING · token window check (9,282 vs 10,357 + landed cycles) -> equal-length region trees -> GRT -> STA
- [ ] HEAD.CLK Clock 12.16 local tree + real hd_tile ring clocks (--ca-ring, on main 21:1x) · DIE-HEAD-20 · RUNNING · hd_tile gate CA min 136 TT/163.8 FF PASS on 240 measured crossings; 187 crossings still on ASSUMED clocks (14 types unkitted) -> no freeze claim; hd_tile diagnostic run in GRT
- [ ] HEAD.GRT Die GRT0 incl. clock on the infra-first plan · INFRA-FIRST · WAITS · old d7b8d1eb signal GRT0 no longer counts → HEAD.INFRA
- [ ] HEAD.BIND Whole-head as-built bind · CODEX / PATH-S81 · WAITS · contract DRAFT ASKed (host N3@276, mesh64 2-beat, head_row_map; head-core-r13@148ff6a840); gaps: ROW0/TEN straps, hd_serdes u_phy open pins → next HEAD PLAN-DELTA
- [ ] HEAD.STA Die STA on real views · DIE-PROTO · WAITS · → HEAD.CLK, → HEAD.TILES
  - [ ] HEAD.TILES Head tile sign-offs · HEAD-KITS-1 (new 21:1x) · RUNNING · 0/16 types, 2/3 hard cores; 14 types no routed kit (5 NEEDS-KIT, 9 FIX) - kit with fwd_buffer + tap_passthrough, hd_spn/hd_spn_end/hd_turn_b first

## DIE qwen_kvsys · Qwen KV · rev batch claude/path-kv-batch-0115@650841e1ef (rebase 5665cd3386 + FT reserve + D-KV-CLKMESH)
- [ ] KV.BIND Strict bind of the batch · PATH-KV · RUNNING · B31 a8c24031c strict PASS 160 parts/51 types + R8 0 unequal + full verify 2553368/2553368; final batch (8-region landings, q2 rename, B32 PV) needs one re-bind
- [ ] KV.LAND Landed 128 groups (12.10a/12.11, main path) · LAND-KV-1 · RUNNING · 30 band FAILs + 20 G0C -> GEN -> GRT incl regional clocks -> STA -> token price
- [ ] KV.CLK Clock 12.16 neighbour-forwarded inverter tree · DIE-KV-13 · RUNNING · inverter clock accepted (VPORT_RT 95); write-group rule KV-13b approved; step-5 bind (compose start pins) building = B48 vehicle source
- [ ] KV.INFRA PG from IR + pre-routed PG/clock/reset via shared tool · PATH-KV · RUNNING · die_infra reset 287 nets max hop 377um PASS; signal GRT50 M4-M9 w/ clock reservation ovf0; PG needs KV power figure (0.15 W/mm2 fallback) → IF.TOOL
- [ ] KV.GRT GRT0 incl. clock at >=50 it · KV-PLAN-DELTA-5 · RUNNING · stall fixed (crit 0, merged RM79), q5c TT/FF overflow 0 CHECKED; FT hub_Wi seam windows in KV event
- [ ] KV.STA Die STA on real views · DIE-KV-21 · RUNNING · tree of record proofF_p20 (phy pads 136->89, seam contract +18.31); spice_edge: BOTH-REAL FF +46.08, real-view -57.92 = declared-budget ends (no view e0/e1/e3/e4/e7, KV-KITS-16 priority); est +32..37 when views land (UNCHECKED); pv_S_6 kit contract -6.80 -> fitted-model rebuild
  - [ ] KV.TILES Tile sign-offs · KV-KITS-16 · RUNNING · 5/31 hard cores (e2 e5 e6 + 2); e1 -1.6 ps re-run, phy_pad + core_tx GEOM PASS-COND queued, pv_pair re-run; two-mode GRT repair root cause
- [ ] KV.TOK Whole-die token pass on bind5 · TOK-KV-2 · RUNNING · B48 nominal + bind5m builds on intel1 (ETA ~01:10 10-29), then boot ~1.3 h + 1 token; composer 4089.4 COMPOSER-ONLY
  - [ ] KV.CORE-SLICE One KV core slice (centre entries, in-core islands, M7 entry pins; hr recut, q2 rename, phy_pad outline) · KV-CORE-SLICE-1 · RUNNING → KV-CORES-R2 → KV.CLK

## DIE s81 · S81 (DeepSeek ROM layer die) · rev main · B2 batch
- [ ] S81.B2 One plan event D-S81-B2: A25 + stations v4 + PHY pins + leaf pins + eng SRAM r0c0 + FT alignment/corridors + D-S81-PHY + infra-first · PATH-S81 · RUNNING · gate: lateral jog <5M bit-um → GRT0 → skew
- [ ] S81.GRT Die GRT0 incl clock · PATH-S81-PD6 · GRT0 DONE on PD5 6d6e8b34f9 (TT+FF overflow 0, CHECKED); 13 B5 cut errors -> measured-usage waiver; 17 storage bands fixing · ETA freeze est 10-28..29
- [ ] S81.PHY 14 SerDes windows · PATH-S81 · RUNNING · zero-area fit 14/14; gunit R180 re-plan PASS-COND (GEOM-17); bk_sel option B re-cut 864x483.84 APPROVED (rebuild quarter tile) → S81.B2
- [ ] S81.LAND Landed regions (12.11, main path) · LAND-S81-1 · RUNNING · rebase on gunit re-layout -> G0C fix -> GEN -> GRT -> STA -> token price
- [ ] S81.CLK Clock 12.16 local inverter tree · DIE-S81-19 · RUNNING · root cause CHECKED (label + stale BUF stage model + x1.78 double comp); go16 on epyc2 (fitted stage cal, spice_edge gate, corrected early cores) results ~01:30-02:30; plan_s12 (S81 landing observer) for strict bind; bk_sel est 140-160 > 80 needs structural form
- [ ] S81.BIND Strict bind on main · TOK-DS · PASS on 877cfdeb2 (0 tied, 10,352 straps) → re-run after S81.B2
- [ ] S81.STA Die STA on real views · PATH-S81-PD6 · RUNNING · related-pair STA on PD5 kit (real where signed + budget)
  - [ ] S81.TILES Tile sign-offs · PATH-S81 / CORES-KITS · RUNNING · 4/171 types, 16/52 hard cores signed

## DIE hbm · HBM UNIFIED SU/MTP/MU one design (OWNER 10-26 23:1x; SU latency qualified first) · plan D-HBM-B1 (5fa3c6e64838)
- [ ] HBM.LAND Landed regions + street grid (12.10c/12.11, main path) · LAND-HBM-1 + HBM-STREETS-1 · RUNNING · region price vs 1906 tok/s -> street-rule plan event -> region trees -> GRT -> STA
- [ ] HBM.B1 Unified plan C16 (Q3 re-lot, EP crossing capacity, clock entries fix) · HBM-R15 · RUNNING · G0/G0C gates pending; 31 core faces over pin capacity; FF clock late (245.77) -> latency fix
- [ ] HBM.GRT Die GRT0 incl clock on the UNIFIED plan · DIE-HBM-10 · WAITS · clock-only trial2b GRT ov 0 but FF duty FAIL; full-signal GRT after C25b (bind 476 errors, S-role q0 halves, 5 reset + 3 provider legs, SRAM outlines) + 461 unbalanced legs / 38 undeliverable early taps (CLK-MODEL-SWEEP-1)
- [ ] HBM.CLK Clock 12.16 local inverter tree on unified plan · DIE-HBM-10 · RUNNING · C22b gates + trial2 (inv2); PHY_N rc_slice C23 (3 clock groups; PHY 4-ch clock ASSUMED, ledgered); reset >=64-edge sequencer + reset_contract.json per kit
- [ ] HBM.BIND Native B2 one-clock bind · PATH-HBM / HC-NATIVE · RUNNING · 98 unread outputs classified (svg redundant views, sm.request/expected check w/o comparator, xl y, ordinals); no open inputs
- [ ] HBM.STA Die related-pair STA real routed clock (TT setup/FF hold) · DIE-PROTO · WAITS · → HBM.GRT; SU latency qualified first (HBM.SU)
- [ ] HBM.PHYCLK ASSUMED licensed-PHY abstract: HBM3E PHY clocked per 4-channel group (one clk/rst_n per slice W PC0-7 / C PC8-23 / E PC24-31; stack-global functions in C) · COORD ruling f6eced6f9 (10-28) · ASSUMED · basis for PHY_N C23 split + hbm_phy_gen rc_slice (claude/die-hbm-10-physlice-1028@c99b18e969); remove when IP datasheet confirms or the split is dropped
- [ ] HBM.SU SU latency qual: ds_ar on planU2; OWNER 10-27 accepts 1917 tok/s (upper) -> priced PASS; measured SU bench PR0/PR1 rerun on main LIVE intel1 · TOK-HBM · RUNNING

## TOKEN · Token-pass gate per design
- [ ] TOK.DS DeepSeek ROM token pass (S81 47 users + head) · TOK-ALL · BLOCKED · 0/6 layer types on current die; main die_b178.v strict bind FAIL (TOK-ALL-13r 10-28: 5/1/656 now 0; left: 81 tied strap inputs, 31 open outputs, ~10.2k landing bits, vehicle regen from current S81 plan -> DIE-S81); priced MTP 3,655 / AR 1,260 tok/s (UNCHECKED); was: L14 27/57/8; idx scan 3-die shard; S81 all-rows MTP 3,655 tok/s > 3,000 floor (AR 1,260), 17.0% ledger ACCEPTED (owner 10-26) → S81.BIND, → HEAD.BIND
- [ ] TOK.QW Qwen ROM token pass (QC + KV, 4 users) · TOK-ALL · BLOCKED · QC 36/36 PASS (CHECKED); KV 0/36: B48 boot now PASS on main (r4 failure was a stale harness, TOK-ALL-13r); next blocker dcal en lane 1 edge early -> KV R8 regen; composer 4,051 tok/s (UNCHECKED); was: QK vehicle on KV rebased bind; prices landed seams + FE stations → KV.BIND, → QC.INFRA
- [ ] TOK.HDS / TOK.HQ HBM token passes (unified SU/MTP/MU, SU latency first) · TOK-ALL · RUNNING · planU3f 1,906 tok/s OWNER-accepted; SU PR0/PR1 PASS on main, 0/41 segments (no unified die top); was: SU programme-path fault (pgslice lw, side_pipe rsq) being root-caused
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
