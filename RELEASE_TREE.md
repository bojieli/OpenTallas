# OpenTallas release tree (pending only; refreshed 2026-10-26 02:32 PDT by CODEX coordinator)

Snapshot: 2026-10-26 01:55 PDT · main 474b749b3 (flow-tag merge: cap64 9bca574fd + cp1-driverview; full canary set submitted on e0d486853 01:19) · FROZEN: none (QC + S81-HEAD UNFROZEN 01:37 by owner, infra-first) · no die has die STA on real views · flow tag flow-20261025-b not cut yet.

## EDIT · rules
- PENDING items only, one short line each, edited in place. Remove an item when done (evidence goes in PATH-FREEZE.md / lane files).
- Line form: `- [ ] ID task · OWNER · STATUS · current fact → DEP.ID` ; "→ X" means this item waits on X (each → is a link).
- Gate ids per die are PFX.INFRA / PFX.GRT / PFX.CLK / PFX.BIND / PFX.STA.
- DIE METHOD (OWNER 10-26 01:37, D-INFRA-FIRST): (1) PG grid sized from IR → (2) clock = equal-length H-tree feeding one mesh per clock region, landed seams, driver islands in tiles → (3) reset tree → (4) 1-3 frozen as pre-routes + skew gate on them alone → (5) signal GRT >=50 iterations on leftover → (6) FREEZE on GRT0 incl. clock + related-pair skew <=80 ps TT/FF (CPPR, routed RC). Die absorbs residuals (mesh stub trim / core-latency offset), tiles rebuilt only for their own failures; every tile type gets a trial placement before freeze.
- Release gate = die STA on real views + token pass.
- Status words: RUNNING WAITS TODO NEW COORD OWNER FAIL PASS FROZEN BLOCKED NOT RUN.

## INFRA-FIRST · shared tool (all dies)
- [ ] IF.TOOL die_infra.py fixed infrastructure: preserve regional cuts + actual connected route import · INFRA-FIRST / CODEX / FLOW · RUNNING · 1d5b87430 fixes regional export; initial qc0 is capacity reservation only; actual ODB clock/PG wires+vias+terminals import tiny PASS, signal GRT50 confirmation running
- [ ] IF.MESH Regional clock + actual landed crossings · CLOCK-MESH / QC-LANDING · RUNNING · actual BUF24 width1.62 (old1.35), clock occupancy correction; real ring crossing measured +3cycles, ~1.01M storage FF / 439 crossings, QC composition pending
- [ ] IF.MASTER Master plan first (METHODOLOGY v3 12.7, OWNER 10-26 all dies): census -> corridors -> bays <=405 um any layer -> M7 entry pins -> worst-case PG + shielded clock + islands + common core latency; static plan gates before any block build · MASTER-PLAN · RUNNING · QC first, then HEAD/S81/KV/HBM
- [ ] IF.MERGE Merge mesh tool fdb5b851c7 (COORD APPROVED 01:1x) · ROOT-MERGE-16 · WAITS · after its gates

## DIE qwen_compute · Qwen compute · rev UNFROZEN 54a1aeb5 · PROTOTYPE of infra-first
- [ ] QC.INFRA One QC plan event: infra-first PG/clock/reset + batch 2 (STM ROMs, SRAM, DEAD-FAULT) + D-QC-FE-REACH stations (all FE variants) + COLLFTM-CTL + CB ID straps + SCROOT + vmr_s6kc · INFRA-FIRST + PATH-QC · RUNNING · PENDING-DELTA D-INFRA-FIRST-QC holds all 68 type routes
- [ ] QC.CLK Related-pair <=80 TT/FF · CLOCK-MESH-2 · FAIL · single mesh 146/132 (8W 139/119): pairs across root/L1/L2 split share only root → regional mesh + landed seams (COORD approved) → IF.MESH
- [ ] QC.GRT Die GRT0 incl. clock on the infra-first plan · INFRA-FIRST · WAITS · → QC.INFRA
- [ ] QC.BIND Strict bind on the QC plan event (wavefront reset/START, CB16 phase classes) · PATH-QC · WAITS · → QC.INFRA
- [ ] QC.STA Die STA on real views · DIE-PROTO · WAITS · → QC.GRT, → QC.TILES
  - [ ] QC.TILES Tile sign-offs · PATH-QC · WAITS · hard cores continue (4/9 signed; no island overlap); types wait for re-freeze; SC kits need LEC fix fffc9dd55 on flow tag

## DIE s81_head · S81 head die · rev UNFROZEN d7b8d1eb · after QC
- [ ] HEAD.INFRA Infra-first plan event (+ HEAD8 batch 187b63494b if approved) · INFRA-FIRST · WAITS · PENDING-DELTA D-INFRA-FIRST-HEAD holds all 16 type routes → IF.TOOL
- [ ] HEAD.CLK Related-pair <=80 · CLOCK-MESH-B · FAIL · old tree 268/254; channel-only mesh impossible (0 interior channel area); in-tile islands 229/193 (serdes bands undriven) → HEAD.INFRA
- [ ] HEAD.GRT Die GRT0 incl. clock on the infra-first plan · INFRA-FIRST · WAITS · old d7b8d1eb signal GRT0 no longer counts → HEAD.INFRA
- [ ] HEAD.BIND Whole-head as-built bind · CODEX / PATH-S81 · WAITS · source d0eb3d3d01; host/mesh/rank-row contract = spec item (no owner input)
- [ ] HEAD.STA Die STA on real views · DIE-PROTO · WAITS · → HEAD.CLK, → HEAD.TILES
  - [ ] HEAD.TILES Head tile sign-offs · S81-HEAD / KITS-WAVE-3 · WAITS · types held by D-INFRA-FIRST-HEAD; 1/2 hard cores signed → HEAD.INFRA

## DIE qwen_kvsys · Qwen KV · rev batch claude/path-kv-batch-0115@650841e1ef (rebase 5665cd3386 + FT reserve + D-KV-CLKMESH)
- [ ] KV.BIND Strict bind of the batch · PATH-KV · RUNNING · B31 a8c24031c strict PASS 160 parts/51 types + R8 0 unequal + full verify 2553368/2553368; final batch (8-region landings, q2 rename, B32 PV) needs one re-bind
- [ ] KV.CLK Legal mesh + routed skew · PATH-KV · RUNNING · c3t (8 regions + stub trim) claude/path-kv-r2-1026@6e753fb93: GRT0 incl clock, COMPLETE related pair 63.95 TT / 54.71 FF (0 >80); independent tool review owed
- [ ] KV.INFRA PG from IR + pre-routed PG/clock/reset via shared tool · PATH-KV · RUNNING · die_infra reset 287 nets max hop 377um PASS; signal GRT50 M4-M9 w/ clock reservation ovf0; PG needs KV power figure (0.15 W/mm2 fallback) → IF.TOOL
- [ ] KV.GRT GRT0 incl. clock on the batch · PATH-KV · PASS · batch 650841e1ef one global_route signals M4-M7 + mesh M8-M9: ovf 0 TT+FF; freeze waits KV.BIND + D-INFRA-FIRST PG/pre-route
- [ ] KV.STA Die STA on real views · DIE-PROTO · WAITS · → KV.CLK, → KV.TILES
  - [ ] KV.TILES Tile sign-offs · PATH-KV / CORES-KITS · WAITS · ASTK strict LEC EQ + S2 GRT done (remeasure); PC833 fix in main; 3 head-eighth routes held on flow canary

## DIE s81 · S81 (DeepSeek ROM layer die) · rev main · B2 batch
- [ ] S81.B2 One plan event D-S81-B2: A25 + stations v4 + PHY pins + leaf pins + eng SRAM r0c0 + FT alignment/corridors + D-S81-PHY + infra-first · PATH-S81 · RUNNING · gate: lateral jog <5M bit-um → GRT0 → skew
- [ ] S81.GRT Die GRT0 · PATH-S81 · PASS SIGNAL DIAGNOSTIC · B5(A25+C+D+E,M5tplcaps) configured50iterations overflow0, converged10; freeze still waits real PHY geometry + infra → S81.B2
- [ ] S81.PHY 14 SerDes windows at published N7 macro size · PATH-S81 · RUNNING · zero-area 14/14 fit = B2 option d (gunit/bk_sel moved), G0C PASS 210/210 (05:0x); gunit/bk_sel internals FAIL STRUCTURAL (GEOM-15) → re-plan in D-S81-B2; fallback W strip +25 mm2
- [ ] S81.CLK Clock skew · INFRA-FIRST · NOT RUN · → S81.GRT
- [ ] S81.BIND Strict bind on main · TOK-DS · PASS on 877cfdeb2 (0 tied, 10,352 straps) → re-run after S81.B2
- [ ] S81.STA Die STA on real views · DIE-PROTO · WAITS · → S81.GRT, → S81.CLK, → S81.TILES
  - [ ] S81.TILES Tile sign-offs · PATH-S81 / CORES-KITS · RUNNING · 4/171 types, 16/52 hard cores signed

## DIE hbm · HBM B2n (next release) · plan D-HBM-B1 (5fa3c6e64838)
- [ ] HBM.B1 Plan event: all hard cores M5 ceiling (COORD approved, owner M5 rule) + spu1 band + b002/b011 FT bands + 107 G0 lower-row errors + q_su11 tap + infra-first · PATH-HBM · RUNNING
- [ ] HBM.GRT Die GRT0 · PATH-HBM · FAIL as declared 1.73M; all cores at M5 → 0 @50 it → HBM.B1
- [ ] HBM.CLK Mesh clock + skew · PATH-HBM · NOT RUN · → HBM.B1
- [ ] HBM.BIND Native B2 one-clock bind · PATH-HBM / HC-NATIVE · RUNNING · recovered native generator: CUT0/clock967PASS, format literals64→0 via exact local BF16 formatter; W128 actual demands exceed oldW64plan, 98unreadoutputs under diagnosis
- [ ] HBM.STA Die STA on real views · DIE-PROTO · WAITS · → HBM.GRT

## TOKEN · Token-pass gate per design
- [ ] TOK.DS DeepSeek ROM token pass (S81 array + head) · TOK-DS · RUNNING · per-layer bound runs → S81.BIND, → HEAD.BIND
- [ ] TOK.QW Qwen ROM token pass (compute + KV) · TOK · RUNNING · QK vehicle on KV rebased bind; prices landed seams + FE stations → KV.BIND, → QC.INFRA
- [ ] TOK.HDS / TOK.HQ HBM token passes (next release) · TOK · RUNNING · SU programme-path fault (pgslice lw, side_pipe rsq) being root-caused
- [ ] TOK.FREEZE Final evidence run at freeze · COORD · WAITS · → TOK.DS, → TOK.QW
- [ ] MU.CURVE Latency-throughput curve vs A100 80GB · COORD · WAITS · → TOK.FREEZE

## FLOW · Flow release
- [ ] FLOW.TAG Cut flow-20261025-b · FLOW-TAG · RUNNING · cap64 + cp1-driverview merged (e0d486853); full canary set running since 01:19; KV canary re-baseline; add LEC fix fffc9dd55 + path-qc-2325/iohold if canaries cover them
- [ ] FLOW.HOLD Route holds lift when the canaries pass · autopilot · WAITS · sign-off flat since 10-25 16:23 → FLOW.TAG

## INFRA · Merge and probes
- [ ] INFRA.MERGE path-kv-lec 070a15290 (urgent, after full-kit LEC), S81-PHY docs bea83f9105, epyc3-retire 59bb63ed15, mesh tool fdb5b851c7 · ROOT-MERGE-16 · RUNNING
- [ ] INFRA.M89 FT-M89-PROBE: S81/HBM what-ifs (FT on M8/M9; S81 cores at M5), >=50 it · FT-M89-PROBE · RUNNING · result decides any layer-rule proposal to the owner

## WAITS · who
### Waiting on the owner
- none. Possible next: S81 SerDes shoreline shortfall (S81.PHY), if PATH-S81 cannot fit 14 N7 macros by re-lay.
### Waiting on COORD / ROOT-MERGE
- QC infra-first plan event review; HEAD8 batch approval; KV batch freeze candidate; INFRA.MERGE list; FT-M89 result → owner proposal.
