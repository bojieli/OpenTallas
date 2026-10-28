# START-TREE-1 (2026-10-28): the start / reset-release tree follows the clock tree (`--start-tree clock`)

Shared opt-in for `tools/die_plan/count_align_plan.py`, `count_align_bind.py`, and the die STA re-check in
`die_sta_related.py`. It implements METHODOLOGY 12.16b(i)/(iv)/(d) and 12.16e: crossings are safe by design, and reset
is a crossing. It is built to the CLK-LOCAL-EST-1 proposal: one dedicated start port per clock fork, so each crossing
takes its count from its own tree node. This is an estimate only: no builds, and it runs on each die's existing plan
inputs.

Labels: CHECKED means my own tool run on the named files. ESTIMATE/UNCHECKED means a model claim.

## 1. Root cause (CHECKED on QC t6 and S81 s10; `scripts/rootcause_paths.py`)

The default planner (`directed_tree` + `plan`) creates the ambiguity in three steps.

- **Start edges are data crossings.**
  - The start tree is a min-ambiguity spanning tree over the DATA crossings, chosen over all roots.
  - It knows nothing about the clock tree.
  - A start edge's interval is the region-pair UNION of every tap pair of that data crossing, plus the full unshared
    clock OCV (the CA-OCV-1 hull).
  - An edge is CLEAN iff `[lo - T/8, hi + T/8]` holds no rise or fall boundary. This is guaranteed only for widths
    <= `T/2 - 2ap` = 208 ps. With OCV most union widths are 350-550 ps.
  - Result: QC has 141 of 312 start edges ambiguous, S81 82 of 397, KV 73 of 127.
- **Ambiguity adds up along the path.**
  - A crossing u -> v that is not a tree edge gets `rel = d + path_amb`.
  - `path_amb` is the sum of the J-deviation ranges of every ambiguous edge on the start-tree path u -> LCA -> v
    (conservative, uncorrelated).
  - Regions that are clock or physical neighbours can be 10-40 start hops apart.
- **Measured on the failing crossings:**

| die (plan) | FAIL | start hops med / max | ambiguous edges on path med / max | path-ambiguous cycles med / max |
|---|---|---|---|---|
| QC t6 | 94 | 10 / 11 | 5 / 8 | 6 / 9 |
| S81 s10 | 44 | 39 / 42 | 5 / 6 | 6 / 7 |

  The ~5 ns interval widths that DIE-QC-9 reported are these 6 cycles, not clock OCV.

**Why the DIE-S81-11 `est_cstree` trial created new FAILs (44 -> 34, 4 new pairs).**

- What it did: it ran Prim's minimum-bottleneck tree on the unshared clock of the DATA crossings.
- The start edges were still data crossings with region-pair-union intervals. So the edges did not get narrower:
  85 ambiguous (82 before).
- A bottleneck tree is not a shortest-path tree, and it is not the clock tree. It grew to depth 49 (34 before). The
  remaining FAILs sit 35 hops apart (max 43).
- Pairs that had a short clean start path in the min-ambiguity tree (s_6S_L3/x06, s_7N_L2/s_7S_L4,
  phy_hbm/svc_12, ...) now crossed 5-6 ambiguous edges.
- In short, it changed which paths were long. It did not remove the accumulation.

## 2. Structural rule (`--start-tree clock`)

**Nodes.**
- Every data region sits at its clock root: the longest common `tree_path` prefix of its proof taps.
- Every branch node of the clock subtree that spans those roots is a virtual node `st:<path>`, a start stage on that
  tree node.
- Each node's start parent is its nearest clock-tree ancestor node. So the start path between two regions IS their
  clock-tree path.

**One dedicated start port per edge.** It is not a data crossing and not a region-pair union.
- Launch: the parent region's FORK tap (the deepest common tree node with the child's sync tap), or the parent node's
  virtual tap.
- Capture: the child region's tap with the shortest leg below its root (its origin / sync flop), or the child node's
  virtual tap.
- Interval: `die_sta_related.count_align_d_intervals` on that ONE tap pair. It uses the same CPPR-at-LCA and the same
  `ca_ocv` callable (table + shared droop, spice cal), unioned over TT/FF. This is the shared model, not a fork of it.
- Virtual tap: node arrival plus the proof's median tap leg (`die_sta_related.tap_leg` / `virtual_tap`, ~40-60 ps).

**Retiming, bounded.**
- An unclean port is split by retime stages on intermediate tree nodes, down to the sync tap's driving node inside the
  child region.
- The split is greedy: take the deepest clean segment first. At most `--start-retime-max` (8) stages per edge.
- A branch node is CONTRACTED (no stage of its own) when every child takes a clean port straight from its parent.

**Reset is a crossing.**
- Every start port must be CLEAN under the CA rule: its derated interval (same `--sta-clock-ocv table` model: OCV +
  droop + spice) keeps >= T/8 = 104 ps from every sampling boundary of the chosen edge. This is `--start-clean phase`,
  the default.
- `--start-clean width` is stricter: the interval width (+ skew range) must be <= T/2 - 2ap = 208 ps, so the port is
  clean wherever d lands. On today's deep trees it costs many more retime stages (see section 3).
- An unclean port FAILs the plan (`start_fail`, rc 1).
- `--start-tree clock` refuses to run without `--sta-proof` / `--sta-plan` and `--sta-clock-ocv table`.

**Why it cannot accumulate.** With every start port clean, each `J` is chip-invariant. `a_v - a_u` is then exact for
every pair, so `path_amb` = 0 whatever the hop count. A data crossing's width is its own interval only.

**What is not done.** There are no per-pair tree-parent overrides (`--tree-parent` is refused with `--start-tree clock`),
and no PAD/K tweaks. Under 12.16c, a tree choice derived from the clock tree is part of (b).

**Built-arrival re-check (12.16d).**
- `count_align_bind` carries `start_ports`, with their tap ends, interval and origin step. `verify()` samples them, the
  loop identity treats them as K+1 = 0 edges, and parts mode homes them in the fork / sync tap partitions.
- `die_sta_related --count-align` re-times every start port on the proof's arrivals (`count_align_start_ports`) and
  fails closed on a missing tap.

## 3. Estimate on all dies (existing plan inputs, no builds; tool runs CHECKED, physical feasibility UNCHECKED)

Both columns use the same flags: CA-OCV-1 hull, spice, cppr-lca, clock_ocv table, shared droop, core latency 250 / 202.5,
and the die's start-skew. "data" is the default tree, "clock" is `--start-tree clock`. MC is 300 chips. Width is
L_width = the crossing's lag interval.

| die (inputs) | xings | FAIL data -> clock | D4/D8 clock | worst lo / hi clock (ps) | max path amb cyc | width p50/p90/p99/max ps data -> clock | start ports (clean) / virtual / retime | MC viol |
|---|---|---|---|---|---|---|---|---|
| S81 (s8 sp_xing, packed-G proof_body, plan_s10, skew-clean 46.9/79.4) | 2306 | **44 -> 0** | 2264 / 42 | 105.4 / 207.5 | 7 -> 0 | 430/1379/6393/6572 -> 418/706/2793/4073 | 630 (630) / 233 / 28 | 0 |
| QC (DIE-QC-9 t6) | 2537 | **94 -> 0** | 2474 / 63 | 106.2 / 104.4 | 9 -> 0 | 596/2191/6049/8128 -> 558/802/2420/2718 | 463 (463) / 151 / 4 | 0 |
| KV (pad2 xing, proofpad2, hm_r26q9c, skew-clean 57.6/89.8, no ECTL/edge-pad) | 3595 | **305 -> 0** | 3480 / 115 | 104.1 / 115.1 | 18 -> 0 | 1411/3907/13422/17592 -> 578/933/3387/3673 | 165 (165) / 38 / 38 | 0 |
| HEAD (die-head-5 ocv_spice, sta_ival proof, sp5, skew 57.5/89.7) | 427 | 0 -> 0 (D8 7 -> 0) | 427 / 0 | 132.2 / 801.1 | 1 -> 0 | 222/306/1619/1619 -> 222/306/786/786 | 367 (367) / 42 / 1 | 0 |
| HBM | - | not runnable | | | | | | |

- **Baselines reproduce the die runs (CHECKED).** S81 base crossings are byte-identical to die-s81-10/gate/plan.json,
  and QC to t6/plan.json. The default CLI output is unchanged.
- **QC end to end (CHECKED).**
  - `count_align_bind --from-ocv --parts ocv --start-tree clock`: 0 identity/loop errors over 2537 loops, 0 of 500 sim
    violations, sim margins 106.7 / 104.5.
  - Reset release reaches the deepest node at origin 42 cycles.
  - Die STA on the same proof (`die_sta_related --count-align`, table, shared droop, spice, cppr-lca, key region):
    TT and FF both PASS. Crossings: 2537 timed, 0 FAIL, 0 below 100 ps, worst lo/hi 109.4/105.6 TT and 106.1/110.3 FF.
    Slot-read 0, guard 0, unbound 0.
  - All 463 start ports are re-timed as crossings and all PASS (min STA sync distance after the clk->Q skew:
    69.9 TT / 43.8 FF, against the 26.5 ps sync aperture).
  - The baseline DIE-QC-9 t6 gate on the default tree had 94 plan FAILs.
- **HBM.** The R2/R4 k1 placement-RC proof has no node arrivals or stages (`node_late_ps` / `node_stages`), so
  `clock_ocv_fn` and the start tree cannot run (fail closed). The CLK-LOCAL-EST-1 HBM estimate stands: 61/62 fork ports
  clean, and the one 8.8 mm child needs the sync on the spine tap. That remedy is exactly what the retime-into-child
  step here does (UNCHECKED on HBM until a proof with node arrivals exists).
- **Strict `--start-clean width` (same inputs, CHECKED).**
  - S81: 0 FAIL, but 6 ports cannot be made width-clean in 8 stages (start_fail 6). It needs 417 retime stages.
  - QC: 0 FAIL, with 506 retimes.
  - HEAD: 0 FAIL, with 16 retimes.
  - KV: 26 FAIL and 27 start_fail (retime_max 8 is hit inside the deep 1-1.7 ns region legs).
  - So on today's trees the width form is not affordable. It becomes cheap once the local form (CLK-LOCAL: ports
    <= 184 ps) is in. Data in `width_rule/`.
- **Combined with CLK-LOCAL-EST-1.**
  - These numbers are on the CURRENT clock trees.
  - The start-tree fix alone removes every FAIL on S81/QC/KV/HEAD at D8. What is left is each crossing's own loop
    width, up to 2.7-4.1 ns at p99/max. That width is the unshared-clock part, which the local form (12.16e) shrinks.
  - CLK-LOCAL's fork-port model gives start widths <= 184 ps. Here the clean ports are up to 386-527 ps wide, and
    51-92% of them are clean by PHASE, not by width (S81 54%, HEAD 51%, QC 92%, KV 77%), because the current trees are
    deeper.
  - So the two fixes combine. Local form plus `--start-tree clock` gives narrower ports (clean by width) and narrower
    loops.

## 4. Costs and open items (UNCHECKED, for die owners)

- **Start stages on tree nodes.** S81 233, QC 151, HEAD 42, KV 38 virtual nodes. Each is one `ot_dp_landing_origin`
  (3 sync flops + PAD, no new RTL form) clocked from that tree node, plus a 1-bit start wire beside the clock route.
  - They need a physical home: the partition under the node, or a cell beside the clock buffer.
  - This is the "dedicated start port at the fork" cost CLK-LOCAL also names.
- **Clean by phase.** Ports clean by phase rely on the computed interval, as every data crossing's K does. The
  built-arrival re-check (`die_sta_related`, 12.16d) is therefore mandatory before freeze. It is wired in. Once the
  local form is in, switch the die default to `--start-clean width`.
- **Retime stages per edge.** At most 8 (worst die KV: 38 retimes over 165 edges). They add only origin latency, which
  the root settle absorbs.

## 5. Files

- **Code:**
  - `count_align_plan.py`: `clock_contexts`, `clock_start_edges`, plan(start_edges=, start_root=), and the CLI
    `--start-tree` / `--start-retime-max`.
  - `count_align_bind.py`: start_ports, verify, parts, and the CLI.
  - `die_sta_related.py`: `tap_leg`, `virtual_tap`, `count_align_start_ports`, and the start-port rows in
    `count_align_landed`.
- **Tests:** `test_count_align_starttree.py`, 7 tests.
  - Default unchanged.
  - Accumulation demonstrated in data mode and gone in clock mode.
  - MC mutant (PAD +3) caught.
  - Retime split, and `retime_max=0` -> start FAIL.
  - Bind region + parts, with an origin mutant -> BindError.
  - Gate re-check, with a moved sync clock -> FAIL and a missing tap -> FAIL.
  - CLI refusals.
  - Related suites: 190 pass (183 on main + 7).
- **Data:**
  - intel2:/srv/opentallas-scratch2/claude/start-tree-1/{s81,head,qc} and intel1:.../start-tree-1/kv hold base/clock
    plan JSON + logs.
  - `plan_summary_<die>.json` and `summary.txt` here.
