# CLK-TOOL-0 (2026-10-28): one die-agnostic clock tool for all 5 dies (design study, ESTIMATE ONLY)

OWNER question: "is it possible to build this die-level clock tool as a general tool so that we do not need duplicate
work on all 5 dies, and it can be a contribution to the open source community?" OWNER refinement (via COORD 21:4x):
upstream OpenROAD acceptance is NOT a goal; target = a reusable generic tool in our repo (like die_plan / landing /
bind), open source as part of OpenTallas.

**Answer: yes.** We already have most of it. `tools/die_plan/die_trial.py` is in practice the shared die clock
builder on all 5 dies. The duplication is not copied code. It comes from (a) about 244 die-specific clock scripts that
re-wrap, re-price or re-check what die_trial and its siblings do, and (b) **stage models that are optional or
hard-coded, with an unsafe default**, which is the root of the DIE-S81-17 failure. The general tool is a refactor of
the existing code behind a per-die **config file**, with a stage-model registry that **fails closed**. No clock rule
changes (rule freeze 12.14a). Every step is additive and opt-in until replay-equivalent. Estimate: 8-10 lane-days
before release and 6-8 after (UNCHECKED estimate). The first useful piece (fail-closed calibrated stage model) is
2 lane-days and directly prevents the next DIE-S81-17.

Basis: origin/main 6a56d5811 (fetched 2026-10-28 21:42 PDT). No builds, no shared-tool edits. Inventory counts come
from `inv.py` (in this directory) and are CHECKED: recomputed by script from git, filename heuristic as stated.
Effort and benefit numbers are UNCHECKED estimates.

## 1. Inventory

Method: every non-test `.py/.tcl/.sh` under `tools/` whose path matches
`clock|clk|cts|htree|mesh|regtree|dme|skew|insertion|landing|landed|_tap|tap_|spine|trunk`, minus the unrelated
`fleet_viz/landing/` recorder UI. Die is taken from the path (qwen/qc/romleaf -> QC, kv -> KV, s81_head -> HEAD,
s81/dsrom -> S81, hbm -> HBM, else shared). Category is taken from the file name. Full list: `inventory.tsv`.
Heuristic limits: a shared-named file can still hold die logic (e.g. `die_plan/qc_clk_mesh*.py` counted as QC, while
`die_plan/kv_r7/qc_clk_mesh2.py` counts as KV), and clock code inside non-clock-named files is not counted. The
content grep (`set_propagated_clock|create_clock|BUFx24|...`) touches about 1730 tool files.

| | scripts | LOC | CHECKED |
|---|---|---|---|
| clock-named scripts (non-test) | **391** | **71,921** | CHECKED |
| shared (no die in path) | 147 | 42,533 | CHECKED |
| die-specific total | **244** | 29,388 | CHECKED (brief said ~243) |
| QC / S81 / KV / HBM / HEAD | 68 / 66 / 46 / 39 / 25 | 11,725 / 5,822 / 5,234 / 4,254 / 2,353 | CHECKED |
| clock tests | 233 | 22,807 | CHECKED |

By function (scripts: shared, QC, KV, HEAD, S81, HBM; LOC). Categories come from file names only (CHECKED count, coarse):

| function | shared | QC | KV | HEAD | S81 | HBM | LOC |
|---|---|---|---|---|---|---|---|
| tree build (DME / H-tree / spine / mesh / trunk) | 39 | 14 | 17 | 10 | 12 | 6 | 28,400 |
| landing / crossing | 10 | 2 | 13 | 2 | 9 | 1 | 5,453 |
| latency targets / taps / early | 10 | 12 | 3 | 3 | 1 | 3 | 3,985 |
| stage model / calibration / OCV | 10 | 6 | 5 | 3 | 1 | 4 | 3,895 |
| STA / skew / check | 15 | 9 | 0 | 2 | 7 | 4 | 3,527 |
| plan / region / sites | 8 | 2 | 1 | 0 | 4 | 2 | 3,759 |
| other (contracts, census, bind, probes) | 48 | 23 | 7 | 5 | 30 | 19 | 22,226 |

### 1a. What is already shared, and who uses it (lane-file / review-queue citations, CHECKED as citations)

| shared tool | LOC | role | used by |
|---|---|---|---|
| `die_plan/die_trial.py` | 4,294 | die/region clock builder: H-tree, fishbone/link_htree, slice spine, region DME (+snake), early taps, inv/inv2 cells, island sites, tap pads | **all 5** (QC, S81, KV, HBM; HEAD die spine_fishbone). 52 CLI flags, 87 commits; in-code tags DIE-QC x58, DIE-S81 x10, DIE-KV x7, LAND-HEAD x4 |
| `die_plan/die_clock_mesh.py` | 4,765 | CLOCK-128 mesh/H-tree build + post + fold report (tap_arrivals) | KV, S81, HEAD, HBM (proof format for die_sta_related) |
| `die_plan/die_sta_related.py` | 2,417 | ONE shared die STA (related pairs, AOCV 0.21 %/mm, droop, spice x1.05) | all dies (OWNER rule: no forks) |
| `die_plan/count_align_plan.py`, `s81_head/landed_phase_ocv.py`, `die_plan/clock_landings.py`, `clock_landing_plan.py` | 1,215 / 209 / 1,229 / 929 | crossing (CA) plan + margin | S81, HEAD, QC, KV, HBM |
| `die_plan/clk_aocv*.py`, `clk_inv_cal.py`, (`model_corr.py` READY) | ~970 | stage/OCV calibration (BUF + inverter, MC + spice) | shared model |
| `die_plan/locality.py` | 1,559 | traffic matrix, region proposer, 12.14b estimate | all 5 |
| `die_plan/reg_spine.py/.tcl` | 270 | partition-kit register spine + local trees | HEAD (opt-in per partition type) |
| `die_plan/parent_trunk_dme.py`, `core_infra_htree.py`, `region_clock.py` | 962 / 975 / 1,144 | core-parent trunk DME, in-core H-tree, plan-level region tree | QC A0 / HBM, QC / QC-MP |
| `die_clock/*` (build.py, regtree.py, METHOD.md) | ~3,500 | 10-16 DIE-CLOCK generation (measured-trim era) | historical; partly superseded by 12.8/12.13 |

### 1b. Duplication found (CHECKED unless marked)

1. **Stage models re-implemented at least 7 times, with different numbers:** `die_trial.STAGE_1X_TT` (BUFx24 1x fit
   20.83 ps + 0.01398 ps/um), `die_plan/die_clock.STAGE_PS=15.0` ("ASSUMED"), `core_infra_plan` (24.93 ps/stage,
   0.636 ps/um), `parent_trunk_dme.EST_PS_PER_UM=0.43` (CKINVDCx16), `spine.DEFAULT_PS_PER_MM=60`,
   `kv_core_slice.TRUNK_PS_PER_UM=0.20`, `hbm_die_v15/die_clock_tree.STAGE_PS=70`. A further 71 tool files carry a
   ps/um constant. CLK-AOCV also found the plan stage model and the MC disagree by about 21 ps per 450-um stage
   (UNCHECKED).
2. **The calibrated model is opt-in, and the default is the BUFx24 model.** `die_trial --region-dme-stage-cal` was
   added by DIE-QC-21 for QC. S81 ran the same builder without it on an inv2 tree, which caused DIE-S81-17: the tree
   was balanced with wire 0.014 vs fitted 0.162 ps/um, giving 125-188 ps imbalance in svc_* and dominating 284/397
   regions (COORD-accepted, CHECKED on go15 by that lane). CLK-MODEL-SWEEP-1 (claude/clk-model-sweep-1-1028@46a74d86d9,
   UNCHECKED) finds the same class on the other dies: per-leg rms model error before -> after refit is QC 12.03 -> 7.58,
   KV 9.44 -> 7.54, HEAD 20.3 -> 13.7, HBM 34.1 -> 19.0, HBM-RISK k1 55.1 -> 24.5 ps.
3. **Copied forks.** `die_plan/clk_aocv.py` = `kv_r7/clk_aocv.py` = `kv_r8/clk_aocv.py` (shingle similarity 1.00).
   `kv_r7/qc_clk_mesh2.py` vs `qc_clk_mesh2.py` 0.97. `mesh_rec` x5 (kv_r7, kv_r8, kv_r17, kv_r18, s81_pd9; 0.88-0.98).
   `mesh_mc` x3. `die_clock_geom_dump.py` vs `s81/die_clock_geom_dump.py` 0.80. Also `kv_r7/die_sta_related_r7.py` and
   `kv_r8/die_sta_related_r8.py` (475/481 LOC, 10-26), which are per-die forks of the STA. The OWNER one-model rule
   forbids these for gate numbers; they look historical, but they still sit beside the shared one.
4. **Each die re-solves the same steps with its own scripts:** taps/early (QC `a0_clock_taps*.tcl` x3 +
   `gen_a0c{6,7,8}_taps.py`, KV `slice_core_taps`/`view_core_taps`, HEAD `head_tap_lattice`/`head_lep_pair_taps`,
   HBM `hbm_hub_clock_retarget`). Clock-pin inventory/census (HBM x4, S81 x3, QC x3). Mesh builders (`qc_clk_mesh{,2,3}`
   about 4.6k LOC, `head_mesh_r3` 864, KV mesh_rec/mc). The meshes are now the third choice (12.15d).
5. **Balancing by compensation, not structure, varies by die** (QC-A0-KITS-8 risk sweep, CHECKED counts there): mixed
   sizes per level (A0 node 51 ps FF routed vs 11.4 model), snakes (QC region DME), pads (HEAD reg_spine 1..16
   BUFx4/tap, KV `--tap-pad` 32/1920 taps). There is no single place that enforces one size per level or writes the
   v5.1 residual ledger.

## 2. One die-agnostic tool: `ot-clk` (working name)

**Scope.** The die/region clock from the die clock source (or a forwarded region root) to every partition/core clock
entry pin, plus crossing (CA) placement checks. Core-internal CTS stays with the core kits (TritonCTS or in-core
H-tree). It implements the rules as they stand: 12.13 locality, 12.16 local form + CA crossings, 12.3 v5.0 early taps,
12.8 d1/d2. It adds no new gate.

### 2a. Inputs (all files; nothing die-specific in code)

| input | format | source today |
|---|---|---|
| floorplan / placed die | DEF or ODB + tech/cell LEF | die_plan gen_phys |
| liberty (TT/FF), RC per layer + NDR | .lib, OpenROAD `set_wire_rc` / layer RC table | ASAP7 kit |
| region map (from connectivity) | JSON `{part: region}` | `locality.py propose` / die plan |
| sink list | JSON: entry pin xy, layer, load, per-core **insertion (TT/FF) from the signed/real view**, planned early offset | kit views (`view_targets`, `kit_latency`) |
| clock-forwarding graph + related-pair list | JSON: region edges (forwarded / spine), crossings, pair classes intra/seam/link | die plan ports + `count_align_plan` |
| **stage-model table** | JSON keyed by (cell, layer, NDR/width, corner, edge) -> d0, k1, k2, kf, rms, n_legs, routed-run hash | produced by `ot-clk calibrate`; **required** |
| die config | YAML/JSON, one per die (section 2c) | new; replaces flags + die scripts |

### 2b. Steps (one pipeline, each step writes a hashed artifact; the existing code is reused)

0. `estimate`: the 12.14b one-page estimate. For each region it gives span, insertion (delay/mm x span), unshared
   clock per crossing, AOCV + droop + spice-scale bound, and CA margin. The code is `locality.py` +
   `count_align_plan.py`. The build refuses a plan whose estimate fails.
1. `calibrate`: fit the stage model on **routed legs of the actual cell/layer/NDR stack** (CLK-MODEL-SWEEP form
   `n*d0 + k1 L + k2 sum Ls^2 + kf (fanout-1)` vs GRT/routed node arrivals, plus `clk_inv_cal` MC/spice factors and the
   `model_corr` golden). **Fail closed**: `build` stops if the table has no entry for the configured clock cell /
   layer / NDR / corner / edge, if the entry was fitted on another cell (the S81 case), or if the entry's rms is above
   its stated bound. The first build on a new stack runs a small calibration vehicle (a ladder of equal legs; it
   already exists as the DIE-QC-3 cal1x / trial13b pattern).
2. `top`: region root distribution. One of: forwarded neighbour chain (12.13b default), spine along the links,
   H-tree (HBM street lattice), or mesh (third choice). These are the existing die_trial / die_clock_mesh forms,
   selected by config.
3. `region`: region trees from the root to the entry pins: DME (die_trial `dme_region_tree`) or fishbone /
   link_htree / reg_spine. **One cell size per level, symmetric by geometry** (QC-A0-KITS-7 ruling). Mixed sizes per
   level are a config error. Snakes, pads and trims are allowed only as v5.1 residuals: capped at 5 % of edges, and
   each use is written to a machine-readable ledger that feeds `lanes/CLOCK-RESIDUAL.md`.
4. `land`: early taps per 12.3 v5.0, from the sink's annotated insertion (never a double compensation; the S81
   x1.78 case becomes a unit test). CA crossing placement at tree nodes (12.16b(i)), K and DEPTH from the planned
   arrival centre.
5. `legalize + write`: legal sites and islands, typed CLOCK nets, NDR/shield, and output to ODB/DEF for GRT. This
   is the existing die_trial / die_clock_mesh legalizer.
6. `signoff` hook. Its own numbers are information only; the gates stay where they are. It calls
   `die_sta_related.py` (one shared model: AOCV 0.21 %/mm, shared droop, spice x1.0485/x1.0552, inverter
   0.9324/0.9380), `landed_phase_ocv` CA margin >= 100 ps TT/FF, and the ngspice correlation (`model_corr`) on a
   sample of routed trees. It writes **predicted vs routed** per leg and per region. A region whose routed/model
   residual exceeds the calibration rms by 3 sigma triggers `calibrate` (it never triggers a trim). Skew reports
   separate designed earliness from real skew (the DIE-S81-17 label error).

### 2c. Per-die quirks become config, not code

| quirk today (flag / die script) | config key |
|---|---|
| `--clock-cell inv/inv2`, `--clock-rc 1x` (QC, S81) | `stack: {cell: CKINVDCx16, polarity: pair, layer: M8, ndr: 1x}`; the stage table entry is looked up by this key |
| `--region-dme`, `--region-dme-snake`, `--region-dme-early-mode hang` (QC) | `region.form: dme`, `residual.snake: {regions: [...], cap_frac: 0.05}`, `early.mode: hang` |
| `--tree-form fishbone/link_htree`, `--tap-pad` (KV, HBM) | `region.form: fishbone|link_htree`, `residual.pad: {...}` (ledgered) |
| `reg_spine.json` trunk/express/bin_um (HEAD) | `region.form: reg_spine` with the same JSON block inline |
| HBM street rule / no leg over a hard core (12.10c) | `keepouts: hard_cores`, `legs.max_over_block_um: 0` |
| `--island-sites`, island lattice (QC 12.2a1) | `sites.islands: {lattice_um: 8.64}` |
| S81 count-aligned crossings, HEAD forwarded taps | `crossings: {form: ca, depth_set: [8,16]}` from the forwarding graph |
| per-die early taps (QC a0_clock_taps*, KV view_core_taps, HEAD head_tap_lattice, HBM retarget) | `sinks[].insertion` from the views; one `land` step |
| per-die census / clock-pin inventory scripts | one `ot-clk inventory` reader on the kit views |

The test for "config, not code": `grep -E 'qwen|s81|hbm|kv|head'` on `tools/clk/` must return nothing. Die names
live only in `configs/<die>.yaml` and the test fixtures.

### 2d. Where it sits relative to OpenROAD (one line, per OWNER refinement)

`ot-clk` is a standalone Python driver on top of OpenROAD/OpenSTA (ODB access, legal placement, GRT, propagated-clock
STA) and ngspice (calibration). It does what TritonCTS does not do at die scale: region/forwarding-graph topology,
early taps, CA crossings, and a calibrated stage model with a residual ledger. Inside a region it can call TritonCTS
as a `region.form: tritoncts` backend if OR-CTS-PROBE-1 (running, no result yet) shows TritonCTS is equal or better
on routed arrivals.

## 3. Migration plan and estimate (no clock-rule change; closure first)

| phase | when | content | effort (lane-days, UNCHECKED) | closure risk |
|---|---|---|---|---|
| P0 replay | now | `configs/{qc,s81,kv,hbm,head}.yaml` that reproduce each die's **current** die_trial / reg_spine invocation; golden test = **byte-identical** tree JSON / ODB node list vs the current run dirs | 1.5 | none (no output change) |
| P1 stage registry | now, **highest value** | stage table + `calibrate` from routed legs (CLK-MODEL-SWEEP fit code + clk_inv_cal + model_corr); fail-closed lookup in die_trial as an **opt-in** flag, which becomes the default only after NUMBER-CHECK and canary NO-REG (12.9e) | 2 | low; this is exactly the fix DIE-S81-18 / die owners need anyway; prevents the next DIE-S81-17 |
| P2 one-size + ledger | now | one-size-per-level check + residual ledger writer (snakes/pads/trims) in die_trial; label split earliness vs skew in reports | 1.5 | low (check + report only; the die owner decides re-kits per the QC-A0-KITS-7/8 rulings) |
| P3 single entry | now / with each die's next plan event | `ot-clk estimate/calibrate/build/signoff` wrapper over existing modules; each die owner switches at its **next** plan event (never mid-run) | 3-4 | low if adopted at a plan event; a die whose replay is not identical keeps its current path |
| P4 retire + open source | **after release** | move code into `tools/clk/` with no die names, delete or retire the ~244 die scripts and the forks (kv_r7/r8 die_sta_related, clk_aocv x3, mesh_rec x5), sky130/gf180 or ASAP7-only example, docs, CI tests | 6-8 | none for release |

**Total: about 8-10 lane-days before release (P0-P3), 6-8 after (P4)** (UNCHECKED; basis: die_trial already holds
the forms; the largest unknown is P0 replay of runs whose inputs were built from frozen worktrees).

**Which die first.** P0 replay on all 5 in parallel, because it is cheap and read-only (12.14c: dies in parallel). P1
first **adopted on S81**, where the DIE-S81-17 refit is the next step in any case, so the tool lane and DIE-S81-18
are the same work, not extra. HEAD second (smallest: 25 scripts; reg_spine already config-driven). QC last, because
it already has its own calibration (DIE-QC-21) and is on the critical path; it switches at its next plan event only.

**Schedule risk.** Low, if four conditions hold: (1) one tool lane only (fits the 12.14d "open clock tools" slot), and
it never edits a die's plan or clock (12.9a: die owners own their clock); (2) everything is opt-in plus replay-identical
until NUMBER-CHECK and canary NO-REG; (3) no rule or gate threshold changes; (4) no die waits for P3/P4. The
main risk is a P1 default flip that shifts a die's numbers mid-closure. Mitigation: the flip happens per die at its
plan event, through the die owner.

**What not to do now:** P4 (rename/move/delete/open-source packaging), a second PDK example, a TritonCTS backend, and
mesh unification (meshes are third choice).

## 4. Inputs read

- METHODOLOGY §3, §12 (12.1-12.16) on coord d3e9b960a; `tools/die_clock/METHOD.md`; AGENTS.md.
- Lane evidence: DIE-S81-17 RESULT/ADDENDUM + COORD acceptance (queue 21:31-21:33), QC-A0-KITS-7/8 (21:06-21:40),
  CLK-INV-CAL-1/2, CLK-AOCV, CLK-MODEL-SWEEP-1 branch `claude/clk-model-sweep-1-1028@46a74d86d9` (README table; its
  numbers UNCHECKED here). OR-CTS-PROBE-1: started 21:35, no branch yet, so it is not used.
- `inv.py` + `inventory.tsv` (this directory) reproduce section 1: `python3 -I inv.py rows.json`, run against
  origin/main.
