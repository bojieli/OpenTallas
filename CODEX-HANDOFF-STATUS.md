# OpenTallas: project status for Codex (maintained by the Claude coordinator)

Last full update: 2026-10-24 08:30 PDT. A live per-lane snapshot is appended below whenever the handoff document is
generated. Lane files (~/coord/lanes/<LANE>.md) are the source of truth for each lane.

## CURRENT STATE 2026-10-26 01:55 PDT (read this first; it overrides the older sections below)

**Owner decisions 10-26 (binding):**
1. **Freeze gate:** die GRT0 incl. clock AND die-clock related-pair skew <=80 ps at TT and FF (CPPR, routed RC). Routability alone never freezes a die.
2. **INFRA-FIRST die method (01:37, "go ahead immediately"):** PG grid sized from IR → clock (equal-length H-tree feeding one mesh per clock region, landed seams, driver islands in tiles) → reset tree → freeze 1-3 as pre-routes with a skew gate → signal GRT (>=50 iterations) on the leftover → freeze on rule 1. The die absorbs residuals (mesh stub trim / core-latency offset); tiles are rebuilt only for their own failures; every tile type gets a trial placement before freeze.
3. **QC (54a1aeb5) and S81-HEAD (d7b8d1eb) are UNFROZEN.** PENDING-DELTA D-INFRA-FIRST-QC / -HEAD in lanes/PLAN-DELTA.md hold all their type routes. Hard cores continue.
4. **S81 PHY:** use published figures, recorded as assumptions (docs/ASSUMPTIONS.md 7a, branch claude/s81-phy-assume-1026).

**COORD calls in force (owner may veto):**
- HBM hard cores get an M5 route ceiling (owner 10-12 M5 rule). Measured: die GRT 1.73M → 0 at 50 iterations.
- Die GRT plan judgments need >=50 iterations; 5-iteration numbers are diagnostic only.
- QC seams across the root/L1/L2 clock split lines use landed crossings; TOK prices the cycles.
- KV clock islands in all 40 types are accepted.
- QC 40 ps two-sided IO-hold budget.
- D-QC-FE-REACH stations (all FE variants) and the CB ID straps are approved.
- ASTK face clock gets a structural sub-root (no relaxation).
- A one-cycle hop beyond 600-750 um is GEOM FAIL STRUCTURAL even with positive slack; every placement review runs a full r2r reach census.
- Feedthroughs stay <=M7 (owner 10-24) until FT-M89-PROBE measures otherwise. Then bring the owner numbers, not a rule change.

**Per die now** (details: ~/coord/RELEASE_TREE.md):
- **QC:** prototype of infra-first (lane INFRA-FIRST). Skew FAIL 146/132 with a single mesh. CLOCK-MESH-2 is building the regional mesh + landed seams. All queued QC deltas fold into ONE QC plan event.
- **S81-HEAD:** next after QC. Old tree skew 268/254. Channel-only mesh is impossible, so it uses in-tile islands.
- **KV:** batch claude/path-kv-batch-0115@650841e1ef. Open items:
  - sys_c 8 vs 5 stations: finish the SYS3 RTL;
  - mesh skew re-run on the reserved sites (main it5 mesh PASS 73 ps);
  - then PG from IR.
- **S81:** die GRT 1.80M; hot spots sit on L1/L3 hard cores walled to M7. D-S81-B2 is one plan event. SerDes shoreline is short: 43.3 mm available vs 44.9-48.2 mm needed. This may need the owner.
- **HBM:** D-HBM-B1 + M5 ceilings + 4 cut fixes + infra-first.
- **Sign-off:** flat since 10-25 16:23 because routes are held on the flow canary. FLOW-TAG submitted the full canary set at 01:19 on e0d486853 (cap64 merged). The holds lift when it passes.

**Live Claude lanes at handoff:** each lane file has its PARKED/last lines.
- Die paths: INFRA-FIRST, CLOCK-MESH-2, CLOCK-MESH-B, PATH-QC, PATH-QC-FEREACH, PATH-KV, PATH-S81 (+ B2 compose, eng SRAM), PATH-HBM.
- Kits and probes: KITS-WAVE-3, CORES-KITS, FT-M89-PROBE.
- Token, flow and merge: TOK-DS, TOK, FLOW-TAG, ROOT-MERGE-16.
- Review: GEOM-REVIEW-12, GEOM-REVIEW-13.
If they stop on the limit, restart them as fresh short agents from lanes/_FRESH_LANE_BRIEF.md + the lane file. Critical path first: INFRA-FIRST/QC, FLOW-TAG, PATH-KV, PATH-S81, PATH-HBM.

**Waiting on the owner:** none.

## What the project is
OpenTallas is mask-ROM LLM inference silicon research on ASAP7 at an 833 ps clock (1.2 GHz).

There are three design targets. Each needs the die gates and a token pass:

| Design | Dies |
|---|---|
| DeepSeek-V4.1 ROM | S81 layer die array (v4.8 plan, ~400 partitions) + a head die (LM head / argmax / MTP; 326 partitions) |
| Qwen3-8B ROM | Qwen compute die (plan P6) + KV/system die (plan v3.8v) |
| HBM accelerator | the B2 die: 4 clusters, H-tree clock, 5 SerDes, 436 hard cores; plan B2r2 on claude/hbm-arch-1024. Serves both DeepSeek and Qwen |

## Gates (top-down, plan-first flow)
- **G0** plan check: `tools/die_plan/check.py`. **G0C** is `--completeness`: types over 400k cells need hard cores.
- **G1** visual plan review (GEOM-REVIEW).
- **G2** routing probes: `g2.py`.
- **G3** partitions and hard cores. Kits are made by `gen.py phys`, run by `run_kit.sh`, and gated by `sdc_lint` +
  `face_guard`. Each run ends with `signoff.py`; only SIGNED counts.
- **G4** abutted die / seam timing: `die_sta.py` with ILM abstracts. DIE-CI runs a whole-die prototype check
  (`die_ci.py`).
- **G5** token pass: layer runs and cross-die co-sims per design (TOK-DS, TOK-QW/QC-TOK/KV-TOK, TOK-HBM).
- **Rules R2-R8** are in `tools/die_plan/README.md`:
  - R3: relay stations at most every 750 um.
  - R4: clock grid taps at 400 um, 250 ps common latency, seam skew <= 80 ps.
  - R7: no tie-offs.
  - R8: bus-coherent delay.

## Owner rulings (binding, 2026-10-24)
- **Sign-off:** setup at TT, hold at FF, 60/25 ps uncertainty, spread <= 80 ps. NEVER SS (AGENTS.md c7ce2ed69a).
- **Review before route:** render and look at every die and tile, judged by industry floorplan-review standards;
  revise before P&R / STA. Reviews are recorded in `results/geom_review`.
- **Disks:** scratch disks only (intel1/intel2/epyc2 `/srv/opentallas-scratch2`); `ot-run` places jobs there.
- **Head dies:** 4 head dies, no HBM on head dies.
- **Copy-A/B link:** the copy-A/B reserve SerDes pair is on every layer die.
- **MTP draft:** rides the copy-B dies; there are no draft fan-out SerDes. S81-HEAD confirmed the composition uses
  none.
- **Elastic seams:** experiment REJECTED (8e69517bf2). Padding is fixed plan-side.
- **The 10-21 element list is obsolete.** Open work = current plans' G0C failures, types/cores without a SIGNED view,
  GEOM-REVIEW findings, and lanes' next steps.
- **Merge recipe:**
  - `git checkout main`, then a plain `git merge` (never `-X ours`), push, and check HEAD == origin/main.
  - On conflict: abort, merge main into your branch, resolve, re-gate.

## State per design (08:30 PDT)

### DeepSeek ROM (S81 + head)
- **S81 v4.8 on main.**
  - G0 PASS, G2 PASS (31 probes).
  - G0C: 91 types lack hard cores. TYPE-DEDUP takes it to 84.
  - S81 picked "one leaf hard core + flop-only wrappers" to collapse the 74 leaf types (S81-CORES builds them).
- **S81-XDIE** (claude/s81-xdie-1024): adds the reserve SerDes pair + in-band host. xdie_io 130 -> 0.
  - GEOM-REVIEW reproduces G0C at 108 failing types, not 91. Reconcile this before merging.
  - 72 feedthrough stations sit on ROM macros; declare `regs_um`.
- **G3 runs:**
  - S81: 7 frame kits.
  - ELEM-S81: 34 slice_station + 8 head ft-station kits, plus 33 old closed hard cores re-running.
  - S81-CORES: the 84-91 G0C hard cores.
- **Head die:** G0/G0C/G1/G2 PASS.
  - hd_tile r2 failed review (slivers) and was redesigned as r3, which is routing on intel2.
- **Token pass:**
  - Entry replay FAILS: fc30/fc31 calendar fault, and layer programs carry no host boot, so u_seqhost never starts.
    TOK-DS layer verdicts are BLOCKED on this.
  - Composed rate: single-user AR 802.6 tok/s, MTP 2,564; ~30% measured-current.
  - Component benches PASS.

### Qwen ROM (compute + KV)
- **QC P6:**
  - G0 PASS, G0C 52/56: sle/slw_st_a/b ft_budget.
  - QC-A0's branch plan does not match its generator (a0v6 tap hook gives 404 clock errors). It must fix that before
    merging.
  - A0 v7 NK/NL routes are PASS-COND in review.
  - 252 ft stations sit on macros.
- **R8 padding:** 248k on P6.
- **QC-TOK, xt1 on bound_r8:** 0/64. Root causes found: x-fill lead +6, and CB16 leg skew padding of 814k. Retests
  are running. tp8/xdie/ovl4u PASS.
- **KV v3.8v on main:**
  - G0/G0C PASS.
  - The hub_Ei 2.2 mm fault leg now has stations.
  - hub_Ei vC FAILED review; the vG kit must pass review before routing.
  - 1,394 of 4,359 ft stations sit on macros.
  - Seam e5e6: TT +93.7 / FF +231 PASS.
  - kv42 boot image (PV pads) committed; hierarchical bench building.

### HBM B2
- **B2r2:** G0 PASS, G0C 49/49.
- **GEOM-REVIEW:** die PASS-COND, but q_sm*/q_hub/root are BLOCKED.
  - q_hub FAILS: 81% of core-core bits run > 1 mm.
  - bankq0 lanes0_2, gq_land and gq_issue FAIL: pins face away from partners, and s_i is tied 0 (an R7 tie-off).
  - HBM-ARCH must re-floorplan. ELEM-HBM holds hub cores and is placing 133 PASS-COND kits.
- **TRIAL-HBM:** full-die GRT + STA running on epyc2. It checks the "cut 0.55" claim; the old die was 1.70.
- **TOK-HBM:** XDIE main_rows256 10/10 PASS. Diagnostics running on epyc2.

## Toolchain lanes
| Lane | State |
|---|---|
| SIGNOFF | done: `signoff.py` merged (TT/FF). 138 old closed modules NEED RE-RUN (DBs lost); on paper 124 pass, 7 fail spread |
| DIE-STA | ILM == flat |
| DIE-CI | margins: OCV +/-5%, IR 5%, xtalk MCF 2. KV seam margined TT -20 ps |
| PART-CAP | OpenROAD scaling 1-27 copies |
| TYPE-DEDUP | done |
| FLEET-DISK | done |
| GEOM-REVIEW | independent reviews |
| TRIAL-S81 / TRIAL-QK / TRIAL-HBM | trial die runs |
| CP1-R10 | seam method on the S81 col_h10 r0/r1 pair; r10c/r10d routing on epyc3. Found and fixed (0ce45ab03c) ORFS deleting face registers after Yosys: ALL kits must be regenerated |

## Known failures nobody may drop
- S81 entry replay (fc30/fc31): this blocks the DeepSeek token pass.
- Qwen xt1 0/64: fixes found, retest pending.
- HBM q_hub floorplan and 3 cores: redesign.
- QC-A0's plan/generator mismatch.
- S81-XDIE G0C count mismatch.
- Feedthrough stations on macros (KV, QC, S81).
- 7 old closed blocks with spread > 80 ps.
- 6 S81 cores and 20 modules overall with no kit in the repo.

## Hosts
| Host | Threads | RAM | Disks |
|---|---|---|---|
| localhost | 256 | 755 GB | coordinator, central checkout ~/OpenTallas, only GitHub pusher. ot-run keeps 32 threads / 64 GB back |
| epyc2 | 128 | 1 TB | 880 GB scratch2 |
| epyc3 | 96 | 1 TB | md0 |
| intel1 | 112 | 1 TB | 3.4 TB scratch2 |
| intel2 | 112 | 1 TB | 3.4 TB scratch2 |

Servers fetch from hub = localhost. Toolchain is `~/.local/opentallas-tools/bin`, plus the docker image
`openroad/orfs:latest`.
