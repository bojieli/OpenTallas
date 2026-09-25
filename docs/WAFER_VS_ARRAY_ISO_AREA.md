# ROM wafer versus ROM array at equal silicon: DeepSeek-V4.1-Flash decode

Status: study, 2026-09-25. Producer: `tools/wafer_vs_array_study.py` (tests: `tests/test_wafer_vs_array_study.py`). Artifact: [`results/roofline/critical_path/wafer_vs_array_iso_area.json`](../results/roofline/critical_path/wafer_vs_array_iso_area.json). Every number below is read from that artifact; the figures that carry units are bound to it by `tools/check_prose_figures.py` annotations.

**The claim under test.** "Even tightly integrated on a wafer, V4.1 decode is not faster than the array at equal silicon, so the wafer (much harder to build) should be rejected."

## Verdict

**The claim holds for the wafer that can be built from published parts. It fails only in a narrow corner that needs an unbuilt fabric, and even there the wafer's lead is small.** At equal silicon, and with the wafer on its published stitched mesh (125 ns per 28.55 mm field crossing), the wafer's batch-1 per-user rate is 0.73 to 0.89 of the array's at every size studied (2, 3, 4 and 12 wafers). It stays below the array across the whole 75-250 ns band of the mesh. <!-- figure: 0.73 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#summary.extremes.control_ratio_b1_min" --> <!-- figure: 0.89 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#summary.extremes.control_ratio_b1_max" -->

The wafer reaches the array's batch-1 rate only when a designed express fabric brings the field crossing down to between 7.9 and 20.9 ns, depending on size and divider. That is against the array at its point link latencies. Against the array's own fast band end it needs 3.7 to 9.8 ns, which in the worst case is below the wire-plus-router limit of 5.25 ns. <!-- figure: 7.9 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#summary.extremes.crossover_ns_vs_point_min" --> <!-- figure: 20.9 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#summary.extremes.crossover_ns_vs_point_max" --> <!-- figure: 3.7 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#summary.extremes.crossover_ns_vs_low_min" --> <!-- figure: 9.8 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#summary.extremes.crossover_ns_vs_low_max" -->

Below the crossover the wafer's advantage is at most:

* **1.03** with the divider that exists (31 cycles), because both machines are then bound by the same Sinkhorn chain. <!-- figure: 1.03 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#summary.extremes.builtdiv_express_ratio_b1_max" -->
* **1.16** when the Sinkhorn chain is off the critical path. That takes a 4-cycle bit-exact divider, which is unbuilt, or removing the chain, which is hypothetical. <!-- figure: 1.16 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#summary.extremes.all_ratio_b1_max" -->

At batch 64 the wafer is slower at 3, 4 and 12 wafers in every fabric variant. The per-user ratio spans 0.48 to 1.19. <!-- figure: 0.48 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#summary.extremes.ratio_b64_min" --> <!-- figure: 1.19 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#summary.extremes.ratio_b64_max" -->

At batch 4096 the aggregate is set by stage occupancy, not by the fabric. The ratio spans 0.90 to 1.20 and does not change with the fabric. Its sign flips with size: the wafer is ahead at 2 and 12 wafers and behind at 3 and 4. <!-- figure: 0.90 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#summary.extremes.ratio_b4096_min" --> <!-- figure: 1.20 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#summary.extremes.ratio_b4096_max" -->

**The condition, stated as asked.** At batch 1 the wafer beats the array only when the field crossing is below the crossover in the table below, which is about 13-18 ns with the built divider. Even then it wins by a factor of at most 1.03. It wins by a factor of at most 1.16 only when the crossing is below the crossover AND the Sinkhorn chain is shorter than the rest of the token path. That happens at 84.2 us per token or less, with a divider of 4 cycles or fewer. <!-- figure: 84.2 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#axes.sinkhorn[id=fdiv4].chain_us_per_token_b1" --> Even then it is slower at batch 64 at three of the four sizes. Neither condition is met by any built part. The designed express fabric has no silicon: its 25/10/5 ns points are design targets, and the wire limit is a floor, not a design. A lead of this size, confined to batch 1 and resting on two unbuilt components, does not pay for what the wafer costs to build (see [manufacturing](#manufacturing-and-complexity)). The recommendation stands: **reject the wafer, build the array.**

## Method

1. **Designs at equal silicon, sized by the analytical model's own code.** For W wafers (46,225 mm2 each) the array gets W x 46,225 / 815 reticle dies, rounded DOWN to whole 4-die packages, so the array never gets more silicon than the wafer. The residual is stated below. Both sides are built by `tools/run_roofline_studies.py` `_build_rom_budget` on the `n5_vs_b200` study's `array-hw-hybrid` and `wafer-hybrid` plans:
   * ROM is sized to the stored weights at the checkpoint's 7.40 bits/parameter.
   * Overhead and interconnect take their graded fractions, with HBM PHY charged per stack.
   * Compute takes the rest.
   * HBM stacks are provisioned for the 200K-context KV of 4,096 users, capped by the die or wafer edge (`max_hbm_stacks_per_device`: 43 per wafer, 5 per die).

   Regenerated points equal the published `results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/points.json` wherever it emits the same design (`analytical_cross_check`). The 112/168/224/680-die arrays are not in that artifact, because it rounds differently and caps arrays at 400 dies, so they are built here by the same function.
2. **Decode critical path.** `tools/decode_critical_path.py` prices one token bottom-up on each design:
   * operator depths are measured RTL depths at the slowest routed ASAP7 clock, 1.0339 GHz;
   * collectives are enumerated per layer;
   * the matrix-sweep input is the analytical design's own.

   The best configuration is searched per design and per batch:
   * **Array:** tensor group 1-64, crossed with dies per package {2, 4, 8} and board topology {chain, ring, mesh, torus, fc2, fc4, fc8, one switch tier}, with the reduction algorithm best per collective.
   * **Wafer:** tensor group 2-57, crossed with field grid {square, rect}, with the same reduction rule.

   Batch-1 figures use the batch-1 optimum; batch 64 and batch 4096 each use their own optimum. The fixed-configuration ratios are also in the artifact.
3. **Layout** (`rom_packed`). A layer occupies the units its own weights need: a fraction 0.580 of the stored bytes are layer weights, and Engram tables, embedding and head fill the rest. The group may be partial in the last stage, and on a wafer a group never straddles two wafers. The `uniform` layout, in which every unit carries layer weights and Engram filler, is a sensitivity.
4. **Axes.**
   * **Wafer field crossing:** mesh at 125 ns (75-250 band), then express at 25, 10 and 5 ns and at the wire limit (28.55 mm x 150 ps/mm = 4.28 ns, plus one router cycle of 0.97 ns).
   * **Array links:** UCIe 10 ns (3-30) and board SerDes 100 ns (40-250).
   * **Sinkhorn:** the built divider (31 cycles, a 51-cycle normalisation step), a 12-cycle and a 4-cycle divider, an idealised 5-cycle step, and the chain removed.
5. **Crossover.** For each size and Sinkhorn variant, bisection finds the largest field-crossing latency at which the wafer's best batch-1 rate still reaches the array's, re-optimising the wafer's configuration at every probe.

## The designs

| wafers | wafer silicon (mm2) | array dies (packages) | array silicon (mm2) | array residual (mm2) | ROM (mm2, both) | compute wafer / array (mm2) | HBM stacks wafer / array | static power wafer / array (kW) |
|---|---|---|---|---|---|---|---|---|
| 2 | 92,450 | 112 (28) | 91,280 | 1,170 | 54,404 | 20,545 / 14,845 | 86 / 560 | 6.8 / 8.0 |
| 3 | 138,675 | 168 (42) | 136,920 | 1,755 | 54,404 | 58,019 / 49,470 | 129 / 840 | 13.6 / 15.4 |
| 4 | 184,900 | 224 (56) | 182,560 | 2,340 | 54,404 | 95,494 / 84,095 | 172 / 1120 | 20.5 / 22.8 |
| 12 | 554,700 | 680 (170) | 554,200 | 500 | 54,404 | 395,290 / 366,040 | 516 / 3400 | 75.0 / 83.0 |

**Refusals.** Every point holds the weights. The smallest wafer machine that does is 2 wafers, and the smallest array is 88 dies. One wafer is refused: its 46,225 mm2 leaves 37,475 mm2 for ROM against the 54,404 mm2 the weights need, and nothing for compute. The array's edge buys it 6.5 times the wafer's HBM stacks at every size. That is the analytical model's beachfront rule, and it is tested as a sensitivity below.

## Headline: the built divider, the control fabrics

Array on its point links, wafer on the stitched mesh at 125 ns.

| wafers | wafer b1 (tok/s) | array b1 (tok/s) | b1 wafer/array | b64 wafer/array | wafer agg b4096 (tok/s) | array agg b4096 (tok/s) | b4096 wafer/array | wafer / array tok/s per mm2 at b4096 | wafer / array tok/s per W at b4096 (derived) |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 3,487 | 4,196 | 0.82 | 1.05 | 128,443 | 107,452 | 1.20 | 1.39 / 1.18 | 16.1 / 12.0 | <!-- figure: 0.82 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#summary.cells[id=W2.fdiv31_built.mesh_125].ratio_b1" -->
| 3 | 3,814 | 4,279 | 0.89 | 0.56 | 271,109 | 294,114 | 0.92 | 1.95 / 2.15 | 16.9 / 16.2 | <!-- figure: 0.89 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#summary.cells[id=W3.fdiv31_built.mesh_125].ratio_b1" -->
| 4 | 3,705 | 4,254 | 0.87 | 0.56 | 405,539 | 449,024 | 0.90 | 2.19 / 2.46 | 16.8 / 16.5 | <!-- figure: 0.87 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#summary.cells[id=W4.fdiv31_built.mesh_125].ratio_b1" -->
| 12 | 3,083 | 4,216 | 0.73 | 0.61 | 902,042 | 873,793 | 1.03 | 1.63 / 1.58 | 10.8 / 9.5 | <!-- figure: 0.73 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#summary.cells[id=W12.fdiv31_built.mesh_125].ratio_b1" -->

Best configurations at batch 1: 2 wafers g8 square x9 against g64 8/fc8 x2; 3 wafers g4 square x25 against g8 8/ring x13; 4 wafers g8 square x17 against g8 8/ring x17; 12 wafers g12 square x34 against g64 8/fc8 x7. Here gN is the tensor group, `k/topo` is dies per package and board topology, and xS is the number of pipeline stages.

Power is derived, not measured: the design's static power plus the analytical point's dynamic energy per token, times the critical-path rate. The wafer's per-watt edge comes from its 6.5 times fewer HBM interfaces.

## Batch 1 across the fabric and Sinkhorn axes

Wafer/array batch-1 per-user ratio, with the array on its point links. Values above 1 are wafer wins.

**fdiv 31 (built)** (per-token Sinkhorn chain if serial: 167.8 us)

| wafer field crossing | 2 wafers | 3 wafers | 4 wafers | 12 wafers |
|---|---|---|---|---|
| mesh 250 ns (band high) | 0.693 | 0.762 | 0.745 | 0.538 |
| mesh 125 ns (control) | 0.831 | 0.891 | 0.871 | 0.731 |
| mesh 75 ns (band low) | 0.942 | 0.941 | 0.940 | 0.870 |
| express 25 ns | 0.992 | 0.985 | 0.988 | 0.989 |
| express 10 ns | 1.011 | 1.004 | 1.009 | 1.018 |
| express 5 ns | 1.022 | 1.015 | 1.020 | 1.030 |
| express, wire limit 5.25 ns | 1.022 | 1.015 | 1.019 | 1.029 |

**fdiv 12** (per-token Sinkhorn chain if serial: 108.9 us)

| wafer field crossing | 2 wafers | 3 wafers | 4 wafers | 12 wafers |
|---|---|---|---|---|
| mesh 250 ns (band high) | 0.572 | 0.597 | 0.590 | 0.450 |
| mesh 125 ns (control) | 0.687 | 0.718 | 0.710 | 0.612 |
| mesh 75 ns (band low) | 0.792 | 0.800 | 0.804 | 0.728 |
| express 25 ns | 0.986 | 0.947 | 0.957 | 0.951 |
| express 10 ns | 1.048 | 0.993 | 1.007 | 1.055 |
| express 5 ns | 1.071 | 1.013 | 1.029 | 1.090 |
| express, wire limit 5.25 ns | 1.069 | 1.012 | 1.027 | 1.088 |

**fdiv 4** (per-token Sinkhorn chain if serial: 84.2 us)

| wafer field crossing | 2 wafers | 3 wafers | 4 wafers | 12 wafers |
|---|---|---|---|---|
| mesh 250 ns (band high) | 0.572 | 0.584 | 0.564 | 0.448 |
| mesh 125 ns (control) | 0.686 | 0.702 | 0.679 | 0.609 |
| mesh 75 ns (band low) | 0.791 | 0.782 | 0.770 | 0.726 |
| express 25 ns | 0.986 | 0.943 | 0.940 | 0.948 |
| express 10 ns | 1.087 | 1.033 | 1.029 | 1.085 |
| express 5 ns | 1.140 | 1.064 | 1.057 | 1.159 |
| express, wire limit 5.25 ns | 1.138 | 1.063 | 1.056 | 1.155 |

**Sinkhorn removed** (per-token Sinkhorn chain if serial: 0.0 us)

| wafer field crossing | 2 wafers | 3 wafers | 4 wafers | 12 wafers |
|---|---|---|---|---|
| mesh 250 ns (band high) | 0.572 | 0.584 | 0.564 | 0.448 |
| mesh 125 ns (control) | 0.686 | 0.702 | 0.679 | 0.609 |
| mesh 75 ns (band low) | 0.791 | 0.782 | 0.770 | 0.726 |
| express 25 ns | 0.986 | 0.943 | 0.940 | 0.948 |
| express 10 ns | 1.087 | 1.033 | 1.029 | 1.085 |
| express 5 ns | 1.140 | 1.072 | 1.065 | 1.159 |
| express, wire limit 5.25 ns | 1.138 | 1.070 | 1.062 | 1.155 |

The 5-cycle idealised step and "removed" match the 4-cycle divider to within 0.01 in every cell. At a 4-cycle divider the 20-iteration Sinkhorn side branch is already shorter than the path it runs beside, so it leaves the critical path. From that point the divider stops mattering, and the fabric alone decides.

### Why: the W = 12 critical path at batch 1 (microseconds)

| case | compute chain | weight sweep | KV sweep | collective latency | collective bytes | pipeline hops | control | total |
|---|---|---|---|---|---|---|---|---|
| wafer, built divider, mesh 125 ns | 132.2 | 46.2 | 5.7 | 118.6 | 0.0 | 14.2 | 7.4 | 324.4 |
| array, built divider, mesh 125 ns | 222.0 | 0.5 | 0.0 | 5.6 | 2.8 | 3.1 | 3.2 | 237.2 |
| wafer, built divider, wire limit | 222.0 | 0.6 | 0.5 | 2.9 | 0.0 | 1.1 | 3.2 | 230.4 |
| array, built divider, wire limit | 222.0 | 0.5 | 0.0 | 5.6 | 2.8 | 3.1 | 3.2 | 237.2 |
| wafer, Sinkhorn removed, mesh 125 ns | 131.1 | 46.2 | 5.7 | 118.6 | 0.0 | 14.2 | 7.4 | 323.3 |
| array, Sinkhorn removed, mesh 125 ns | 141.2 | 3.0 | 0.0 | 32.5 | 9.9 | 3.1 | 7.4 | 197.1 |
| wafer, Sinkhorn removed, wire limit | 141.2 | 3.4 | 0.7 | 16.8 | 0.1 | 1.1 | 7.4 | 170.7 |
| array, Sinkhorn removed, wire limit | 141.2 | 3.0 | 0.0 | 32.5 | 9.9 | 3.1 | 7.4 | 197.1 |

The table shows why the wafer loses on the control mesh:

* **The mesh costs the wafer in two places.** About 119 us of the wafer's critical path is collective latency. The mesh also pushes the wafer to small tensor groups (12 fields, 34 stages), which leaves it about 46 us of weight sweep.
* **The array pays almost nothing for its collectives.** Its tensor group of 64 sits on 8-die packages with a fully connected board, so collectives cost it only a few microseconds.

A fast fabric removes both of the wafer's costs. What remains is the per-operator chain, and it is identical on both machines: the same RTL at the same clock. With the built divider that chain is the Sinkhorn iteration, about 222 us on each side, so the two machines tie to within a factor of 1.03. With the chain off the path, the remaining difference is the array's board-SerDes collectives (about 32 us) against the wafer's field crossings (about 17 us). That difference is the whole of the wafer's best-case lead.

## Crossover: the largest field crossing at which the wafer matches the array at batch 1 (ns)

| Sinkhorn variant | array links | 2 wafers | 3 wafers | 4 wafers | 12 wafers |
|---|---|---|---|---|---|
| fdiv 31 (built) | point (UCIe 10, SerDes 100 ns) | 17.9 | 12.9 | 16.2 | 18.4 |
| fdiv 31 (built) | band low (3, 40 ns) | 8.1 | 8.3 | 8.2 | 9.4 |
| fdiv 12 | point (UCIe 10, SerDes 100 ns) | 22.5 | 8.0 | 12.0 | 19.1 |
| fdiv 12 | band low (3, 40 ns) | 10.3 | 3.7 | 6.3 | 8.4 |
| fdiv 4 | point (UCIe 10, SerDes 100 ns) | 22.5 | 15.1 | 14.4 | 18.8 |
| fdiv 4 | band low (3, 40 ns) | 9.5 | 9.9 | 9.0 | 7.6 |
| Sinkhorn removed | point (UCIe 10, SerDes 100 ns) | 22.5 | 15.1 | 14.4 | 18.8 |
| Sinkhorn removed | band low (3, 40 ns) | 9.5 | 9.9 | 9.0 | 7.6 |

The crossover does not move monotonically with the divider. A faster divider also speeds up the array, which is Sinkhorn-bound on its own path. At 3 wafers with a 12-cycle divider, the array gains more than the wafer does.

## Batch 64 and batch 4096

| wafers | Sinkhorn | fabric | wafer b64 (tok/s/user) | array b64 (tok/s/user) | b64 wafer/array | b4096 wafer/array |
|---|---|---|---|---|---|---|
| 2 | fdiv31_built | mesh_125 | 1,634 | 1,553 | 1.052 | 1.195 |
| 2 | fdiv31_built | express_10 | 1,736 | 1,553 | 1.118 | 1.195 |
| 2 | fdiv31_built | express_wire_limited | 1,739 | 1,553 | 1.119 | 1.195 |
| 2 | fdiv4 | mesh_125 | 1,637 | 1,556 | 1.052 | 1.195 |
| 2 | fdiv4 | express_10 | 1,739 | 1,556 | 1.118 | 1.195 |
| 2 | fdiv4 | express_wire_limited | 1,742 | 1,556 | 1.120 | 1.195 |
| 3 | fdiv31_built | mesh_125 | 2,256 | 4,051 | 0.557 | 0.922 |
| 3 | fdiv31_built | express_10 | 2,822 | 4,051 | 0.697 | 0.922 |
| 3 | fdiv31_built | express_wire_limited | 2,844 | 4,051 | 0.702 | 0.922 |
| 3 | fdiv4 | mesh_125 | 2,262 | 4,206 | 0.538 | 0.922 |
| 3 | fdiv4 | express_10 | 2,831 | 4,206 | 0.673 | 0.922 |
| 3 | fdiv4 | express_wire_limited | 2,852 | 4,206 | 0.678 | 0.922 |
| 4 | fdiv31_built | mesh_125 | 2,320 | 4,111 | 0.564 | 0.903 |
| 4 | fdiv31_built | express_10 | 3,049 | 4,111 | 0.742 | 0.903 |
| 4 | fdiv31_built | express_wire_limited | 3,071 | 4,111 | 0.747 | 0.903 |
| 4 | fdiv4 | mesh_125 | 2,325 | 4,802 | 0.484 | 0.903 |
| 4 | fdiv4 | express_10 | 3,070 | 4,802 | 0.639 | 0.903 |
| 4 | fdiv4 | express_wire_limited | 3,105 | 4,802 | 0.647 | 0.903 |
| 12 | fdiv31_built | mesh_125 | 2,475 | 4,061 | 0.609 | 1.032 |
| 12 | fdiv31_built | express_10 | 3,713 | 4,061 | 0.914 | 1.032 |
| 12 | fdiv31_built | express_wire_limited | 3,757 | 4,061 | 0.925 | 1.032 |
| 12 | fdiv4 | mesh_125 | 2,481 | 4,061 | 0.611 | 1.032 |
| 12 | fdiv4 | express_10 | 3,836 | 4,061 | 0.945 | 1.032 |
| 12 | fdiv4 | express_wire_limited | 3,933 | 4,061 | 0.969 | 1.032 |

At batch 64, the 2-wafer point is the only size where the wafer leads. Its 112-die array is too small to stage 64 users well: it has few dies per stage and large microbatches. At batch 4096 both machines are occupancy-bound, so the ratio does not depend on the fabric.

## Sensitivities that could overturn the result

Wafer/array ratios with the built divider, for each size and wafer fabric. Each row changes one assumption on the side or sides it applies to.

| sensitivity | fabric | 2 wafers: b1 / b64 / b4096 | 3 wafers: b1 / b64 / b4096 | 4 wafers: b1 / b64 / b4096 | 12 wafers: b1 / b64 / b4096 |
|---|---|---|---|---|---|
| baseline | mesh_125 | 0.83 / 1.05 / 1.20 | 0.89 / 0.56 / 0.92 | 0.87 / 0.56 / 0.90 | 0.73 / 0.61 / 1.03 |
| baseline | express_wire_limited | 1.02 / 1.12 / 1.20 | 1.01 / 0.70 / 0.92 | 1.02 / 0.75 / 0.90 | 1.03 / 0.93 / 1.03 |
| uniform layout (every unit carries layer weights) | mesh_125 | 0.70 / 0.69 / 0.67 | 0.71 / 0.53 / 0.59 | 0.71 / 0.55 / 0.54 | 0.66 / 0.59 / 0.90 |
| uniform layout (every unit carries layer weights) | express_wire_limited | 1.02 / 0.75 / 0.67 | 1.02 / 0.78 / 0.59 | 1.02 / 0.82 / 0.54 | 1.03 / 0.97 / 0.90 |
| array limited to the wafer's HBM stack count | mesh_125 | 0.83 / 1.12 / 1.28 | 0.90 / 0.60 / 1.07 | 0.87 / 0.60 / 1.08 | 0.73 / 0.65 / 1.20 |
| array limited to the wafer's HBM stack count | express_wire_limited | 1.02 / 1.19 / 1.28 | 1.02 / 0.75 / 1.07 | 1.02 / 0.79 / 1.08 | 1.03 / 0.98 / 1.20 |
| lanes from the analytical compute roof | mesh_125 | 0.83 / 1.12 / 1.28 | 0.90 / 0.57 / 0.98 | 0.87 / 0.57 / 0.95 | 0.73 / 0.62 / 1.05 |
| lanes from the analytical compute roof | express_wire_limited | 1.02 / 1.20 / 1.28 | 1.02 / 0.72 / 0.98 | 1.02 / 0.76 / 0.95 | 1.03 / 0.93 / 1.05 |
| no producer/consumer chaining | mesh_125 | 0.82 / 0.98 / 1.20 | 0.88 / 0.53 / 0.92 | 0.86 / 0.54 / 0.90 | 0.73 / 0.60 / 1.03 |
| no producer/consumer chaining | express_wire_limited | 1.02 / 1.04 / 1.20 | 1.01 / 0.66 / 0.92 | 1.02 / 0.70 / 0.90 | 1.03 / 0.91 / 1.03 |
| HBM gather 300 ns (assumed 100) | mesh_125 | 0.83 / 1.05 / 1.20 | 0.89 / 0.56 / 0.92 | 0.87 / 0.57 / 0.90 | 0.73 / 0.61 / 1.03 |
| HBM gather 300 ns (assumed 100) | express_wire_limited | 1.02 / 1.12 / 1.20 | 1.01 / 0.70 / 0.92 | 1.02 / 0.75 / 0.90 | 1.03 / 0.92 / 1.03 |
| inter-wafer SerDes 40 ns | mesh_125 | 0.83 / 1.05 / 1.20 | 0.89 / 0.56 / 0.92 | 0.87 / 0.56 / 0.90 | 0.73 / 0.61 / 1.03 |
| inter-wafer SerDes 40 ns | express_wire_limited | 1.02 / 1.12 / 1.20 | 1.02 / 0.70 / 0.92 | 1.02 / 0.75 / 0.90 | 1.03 / 0.93 / 1.03 |
| inter-wafer SerDes 250 ns | mesh_125 | 0.83 / 1.05 / 1.20 | 0.89 / 0.56 / 0.92 | 0.87 / 0.56 / 0.90 | 0.73 / 0.61 / 1.03 |
| inter-wafer SerDes 250 ns | express_wire_limited | 1.02 / 1.12 / 1.20 | 1.01 / 0.70 / 0.92 | 1.02 / 0.75 / 0.90 | 1.02 / 0.92 / 1.03 |
| array at 113/170/227/681 dies (no package rounding) | mesh_125 | 0.83 / 1.05 / 1.19 | 0.89 / 0.56 / 0.92 | 0.87 / 0.56 / 0.90 | 0.73 / 0.62 / 1.03 |
| array at 113/170/227/681 dies (no package rounding) | express_wire_limited | 1.02 / 1.11 / 1.19 | 1.02 / 0.70 / 0.92 | 1.02 / 0.75 / 0.90 | 1.03 / 0.93 / 1.03 |

How to read the sensitivities:

* **Batch 1 moves only with the fabric.** The batch-1 ratio moves by at most a few hundredths under every non-fabric sensitivity, except the uniform layout on the mesh, which lowers it further.
* **Batch 4096 moves with the HBM beachfront rule.** If the array is held to the wafer's HBM stack count, the wafer's aggregate lead grows at 2 and 12 wafers and turns positive at 3 and 4. The array's larger edge is therefore a real advantage in the aggregate, not an artefact of the model.
* **The uniform layout hurts the wafer.** It forces more fields per layer and costs the wafer aggregate at every size.
* **Nothing reverses the batch-1 verdict except the fabric.** None of the non-fabric sensitivities moves the batch-1 ratio across 1.

## Manufacturing and complexity

The repository has no numeric yield, test, stitching or cost model for either machine. These are listed as open gaps in docs/SOURCES.md ("No public source currently establishes ... yield, repair overhead, ... wafer HBM beachfront, stitched-wafer timing, power delivery, cooling, unit cost, NRE") and in docs/PRE_NDA_TECHNOLOGY_ROADMAP.md. The comparison below is therefore qualitative, and no number is invented for it.

* **Yield and redundancy.** A wafer must tolerate every defect in place, so it needs spare fields and routing-around. Cerebras reports redundant-link repair across 84 stitched dies (docs/SOURCES.md, SRC-CEREBRAS-WSE3, used there as a feasibility anchor only). An array can discard a bad die before packaging, using known-good-die test. The ROM service RTL implements row redundancy from a BIST defect list and refuses column redundancy (docs/ROM_SERVICE_RTL.md). There is no defect density and no yield model for either machine (docs/ARCHITECTURE_ATLAS.html: "yield/redundancy handling (not started)").
* **Stitching.** The wafer needs cross-field stitched wiring. docs/CHIP_ARCHITECTURE_DESIGN.md sketches an 8-by-6 grid of 26-by-33 mm fields. The array needs none: docs/DEEPSEEK_V4_ROM_ARRAY_IMPLEMENTATION_PLAN.md lists "no reticle stitching, no distributed-HBM-around-a-wafer package" as its reason to exist. The express fabric this study would need to win is also exactly the unbuilt, unmeasured part.
* **HBM attach.** The wafer's KV bandwidth is limited by its perimeter. The beachfront rule (`max_hbm_stacks_per_device`: 12 mm stack pitch at 0.6 edge utilisation, taken from A100 and B200) gives 43 stacks per wafer, against 5 per 815 mm2 die, so equal silicon gives the array 6.5 times the stacks. results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/REPORT.md records that perimeter grows as the square root of area. The same 860 mm perimeter must also carry the inter-wafer SerDes, and whether both fit at once is not checked anywhere in the repository.
* **Cooling.** Neither machine is cooling-bound under the A100-derived `cooling_limit_w_per_mm2`. The candidate REPORT puts both the worst ROM wafer and the worst large array below half of their budget. Cooling does not separate the two.
* **Test.** No wafer-level test, burn-in or known-good-die procedure is modelled (docs/PRE_NDA_TECHNOLOGY_ROADMAP.md lists test time and repair coverage as open). An array's packages can be tested and binned one at a time. A wafer is one part.

The asymmetry is qualitative but one-directional: every item on the list is harder for the wafer. The best performance case the model finds for the wafer is a batch-1 lead of a factor of 1.16 or less, and it requires unbuilt parts.

## Assumptions and grades

| id | grade | assumption | direction |
|---|---|---|---|
| A1 | derived | Designs are sized by the analytical model's own code (run_roofline_studies._build_rom_budget, n5_vs_b200, batched, spare area to SRAM, HBM-KV provisioned for 4,096 users at 200K, stacks capped by the die/wafer edge); nothing is re-derived here. | neutral: the same rule on both sides |
| A2 | derived | Iso-area: the array gets W x 46,225 / 815 dies rounded DOWN to whole 4-die packages (a silicon shortfall of 0.0127 of the wafer area at W = 2-4 and 0.0009 at W = 12). | favours the wafer |
| A3 | measured | Operator depths are the repository's routed/campaigned RTL (decode_critical_path RTL_SOURCES) at the slowest routed clock among the token path's units (1.0339 GHz ASAP7), applied to N5 on both sides. | common-mode |
| A4 | derived | Matrix-sweep time is the analytical design's own (max(compute, weight_read)/stage balance, scaled by g_ref/g), apportioned per matvec; lanes from routed lane areas. | common-mode |
| A5 | derived | Layout rom_packed: one layer occupies units x 0.580 (its share of the stored bytes) / 40; Engram tables, embedding and head fill the other units. The 'uniform' layout (units/40) is a sensitivity. | favours neither; fewer stages for both |
| A6 | derived | Wafer control fabric: links.on_wafer_n5 125 ns per 28.55 mm field crossing (75-250 ns band); per-field-edge bandwidth on_wafer_n5.bytes_s / 57 / 4; wafers joined by rom_wafer_serdes (100 ns, 40-250). | the axis under test |
| A7 | assumed | Designed express fabric: 25/10/5 ns per field crossing are design targets with no silicon; the wire limit is 28.55 mm x 150 ps/mm (assumed, 100-250) + one router cycle (assumed). The express fabric keeps the mesh's bandwidth and is applied to every field crossing (collectives and pipeline hops). | favours the wafer |
| A8 | derived | Array links: rom_package_ucie 10 ns (3-30), rom_board_serdes 100 ns (40-250), package SerDes lanes scale with the package edge; one switch tier 250 ns assumed. | the array's axis |
| A9 | measured/assumed | Sinkhorn: 20 iterations x 2 normalisations per sublayer, each 3 sequential fadd + eps + fdiv (31 cycles, built); fdiv 12/4 and the 5-cycle step are unbuilt what-ifs; 'removed' is hypothetical and not the model. | common-mode per token |
| A10 | assumed | HBM random-row gather latency 100 ns (no constant in technology.json), charged only on index-source layers. | common-mode |
| A11 | derived | Power = the design's static power + the analytical point's dynamic energy per token x the critical-path aggregate rate (a derived estimate; no measured power). | neutral |
| A12 | derived | Uniform expert routing (the router trace is synthetic); experts striped over the tensor group (deterministic); reduction algorithm best per collective. | common-mode |

## What this study does not settle

* **Absolute rates are projections.** Every rate is a projection from ASAP7 RTL depths at 1.0339 GHz applied at N5, and no V4.1 token has been simulated across more than one node. The ratios are the robust output.
* **The fastest fabric points are targets, not measurements.** A parallel study is measuring an express link on ASAP7. If it lands above 22.5 ns per field crossing, the wafer never reaches the array at batch 1 under any divider in this model.
* **Routing is uniform.** The router trace is synthetic, so the expert-parallel alternative is not the headline, and the stripe layout used here is deterministic.
* **The committed critical-path artifact is stale.** `results/roofline/critical_path/decode_critical_path.json` predates `hdc_timing` changes in fe1e0f51, so its `test_committed_result_reproduces` fails at HEAD. This study recomputes everything from source and does not read that file.
