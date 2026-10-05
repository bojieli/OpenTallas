# ROM wafer versus ROM array at equal silicon: DeepSeek-V4.1-Flash decode

Status: study, 2026-09-26: rerun on the realistic interconnect. The array is now built from shipping two-die packages whose dies link only to edge-adjacent dies, joined by a 209 ns board SerDes, and the wafer-to-wafer link is priced as the same link class. The 2026-09-25 version of this study used the earlier, optimistic links, and its verdict is superseded below. Producer: `tools/wafer_vs_array_study.py` (tests: `tests/test_wafer_vs_array_study.py`). Artifact: [`results/roofline/critical_path/wafer_vs_array_iso_area.json`](../results/roofline/critical_path/wafer_vs_array_iso_area.json). Every number below is read from that artifact unless another source is named. The figures that carry units are bound to it by `tools/check_prose_figures.py` annotations.

**The claim under test.** "Even tightly integrated on a wafer, V4.1 decode is not faster than the array at equal silicon, so the wafer (much harder to build) should be rejected."

## Verdict

**On the realistic links the first half of the claim is false. A tightly integrated wafer, meaning one with an express field-crossing fabric, is faster than the array at batch 1 at every size studied. It is still slower on the published stitched mesh, and it is slower in aggregate at 3, 4 and 12 wafers. Any case for rejecting the wafer must now rest on throughput and manufacturing, not on single-user speed.**

On the published stitched mesh (125 ns per 28.55 mm field crossing), the wafer's batch-1 per-user rate is 0.81 to 0.94 of the array's at every size studied (2, 3, 4 and 12 wafers). It stays below the array across the whole 75-250 ns band of the mesh, and at the fast end of that band it is nearly level, at 0.977 to 0.997. <!-- figure: 0.81 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#summary.extremes.control_ratio_b1_min" --> <!-- figure: 0.94 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#summary.extremes.control_ratio_b1_max" -->

The wafer reaches the array's batch-1 rate once the field crossing falls below a crossover of 56.5 to 70.6 ns. The crossover depends on size and divider, and is taken against the array at its point link latencies. Against the array's fast band end, the crossover is 39.0 to 51.3 ns. The earlier links put this crossover at 4 to 21 ns. The target is now about half the mesh's 125 ns, just under the 75 ns end of the mesh band. <!-- figure: 56.5 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#summary.extremes.crossover_ns_vs_point_min" --> <!-- figure: 70.6 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#summary.extremes.crossover_ns_vs_point_max" --> <!-- figure: 39.0 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#summary.extremes.crossover_ns_vs_low_min" --> <!-- figure: 51.3 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#summary.extremes.crossover_ns_vs_low_max" -->

The wafer wins at batch 1 in 80 of the 140 cells studied (4 sizes x 5 Sinkhorn variants x 7 wafer fabrics). The wins are exactly the express-fabric cells, from 25 ns down to the wire limit; none of the mesh cells is a win. <!-- figure: 80 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#summary.wafer_wins_b1_cells" --> <!-- figure: 140 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#summary.cells_b1" -->

The express fabric is no longer only a target. A routed ASAP7 implementation of the express link (`rtl/rom/ot_rom_express_link.sv`, `results/architecture/wafer_express_link_measurement.json`) extrapolates to 30 ns per field crossing. That is below every crossover in the table below. It is post-route evidence, not fabricated silicon, and this study sweeps 25/10/5 ns and the wire limit rather than that value. <!-- figure: 30 src="configs/hardware/technology.json#links.rom_wafer_express.hop_latency_s.value" scale="1e9" -->

Below the crossover the wafer's lead is at most:

* **1.15** with the divider that exists (31 cycles). At 25 ns it is 1.03 to 1.11, and it reaches 1.15 at 12 wafers at the wire limit. <!-- figure: 1.15 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#summary.extremes.builtdiv_express_ratio_b1_max" -->
* **1.50** when the Sinkhorn chain is off the critical path. That takes a 4-cycle bit-exact divider, which is unbuilt, or removing the chain, which is hypothetical. <!-- figure: 1.50 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#summary.extremes.all_ratio_b1_max" -->

**What moved the result is the array's links, not the wafer.** The artifact also prices the array on the earlier links, where every die of a package of 4 or fewer links to every other and the board SerDes runs at 100 ns at the raw 1.8 TB/s. There, with 2-, 4- and 8-die packages allowed, the built-divider wire-limit ratio is 1.00 to 1.03, which is the old verdict. <!-- figure: 1.03 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#comparisons[wafers=12,sinkhorn=fdiv31_built,wafer_fabric=express_wire_limited,array_links=links_optimistic].ratio_b1" name="optimistic-links wire-limit ratio at W=12" -->

With the realistic links but 4- and 8-die packages allowed, which are roadmap interposers, the ratio is 1.00 to 1.07. <!-- figure: 1.07 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#comparisons[wafers=12,sinkhorn=fdiv31_built,wafer_fabric=express_wire_limited,array_links=links_point_future_packaging].ratio_b1" name="future-packaging wire-limit ratio at W=12" -->

On shipping two-die packages the array's best batch-1 configuration at every size is a tensor group of 16 spread over 8 packages. Its collectives and pipeline hops therefore cross the 209 ns board link. At the array's slow band end (409 ns SerDes) even the plain-mesh wafer draws level or leads at 3 and 4 wafers (1.04 and 1.01). <!-- figure: 1.04 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#comparisons[wafers=3,sinkhorn=fdiv31_built,wafer_fabric=mesh_125,array_links=links_high].ratio_b1" name="mesh wafer vs array at band high, W=3" -->

At batch 64 the per-user ratio spans 0.56 to 1.34, and the sign depends on size and fabric: <!-- figure: 0.56 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#summary.extremes.ratio_b64_min" --> <!-- figure: 1.34 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#summary.extremes.ratio_b64_max" -->

* at 2 wafers the wafer leads in every variant (1.19);
* at 3 wafers the wafer trails in every variant;
* at 4 and 12 wafers the wafer leads with an express fabric and trails on the 125 and 250 ns mesh.

At batch 4096 the aggregate is set by stage occupancy, not by the fabric. The ratio spans 0.61 to 1.15 and does not change with the fabric. The wafer leads only at 2 wafers (1.15). At 3, 4 and 12 wafers the array's aggregate is 1.37, 1.33 and 1.65 times the wafer's, and on the derived power the array also delivers more tokens per watt at those sizes. <!-- figure: 0.61 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#summary.extremes.ratio_b4096_min" --> <!-- figure: 1.15 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#summary.extremes.ratio_b4096_max" -->

**The condition, stated as asked.** At batch 1 the wafer beats the array whenever its field crossing is below the crossover in the table below, which is 61-71 ns with the built divider. Its lead with the built divider is then at most a factor of 1.15. The lead reaches 1.50 only when the Sinkhorn chain is shorter than the rest of the token path, which happens at 84.2 us per token or less, with a divider of 4 cycles or fewer. <!-- figure: 84.2 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#axes.sinkhorn[id=fdiv4].chain_us_per_token_b1" -->

No fabricated part meets the fabric condition. The published mesh is 125 ns, but the routed 30 ns express link meets it with margin, so this is no longer a narrow corner that needs a fabric nobody has drawn.

**What the numbers now support.** The wafer and the array trade against each other:

* **Single-user speed favours the wafer.** It is faster by 3-15% with the built divider, and by up to 50% with an unbuilt 4-cycle divider.
* **Aggregate throughput at 3 or more wafers favours the array,** by 33-65%.
* **Manufacturing favours the array on every item** (see [manufacturing](#manufacturing-and-complexity)).

The claim "the wafer is not faster" should no longer be cited. Whether to reject the wafer depends on how single-user latency is weighed against aggregate throughput and build risk:

* **If aggregate throughput and build risk decide,** as the deployment target so far has, the array remains the choice. The wafer's advantage is at most 15% at batch 1 on the built divider, and it costs the wafer a quarter to two fifths of its aggregate at 3-12 wafers, plus the manufacturing items below.
* **If per-user latency decides,** the wafer with an express fabric is now the faster machine.

## Method

1. **Designs at equal silicon, sized by the analytical model's own code.** For W wafers (46,225 mm2 each), the array gets W x 46,225 / 815 reticle dies. That count is rounded DOWN to whole two-die packages, so the array never gets more silicon than the wafer. Two dies is the shipping, B200-class package. The residual is stated below. Both sides are built by `tools/run_roofline_studies.py` `_build_rom_budget` on the `n5_vs_b200` study's `array-hw-hybrid` and `wafer-hybrid` plans:
   * ROM is sized to the stored weights at the checkpoint's 7.40 bits/parameter.
   * Overhead and interconnect take their graded fractions, with HBM PHY charged per stack.
   * Compute takes the rest.
   * HBM stacks are provisioned for the 200K-context KV of 4,096 users, capped by the die or wafer edge (`max_hbm_stacks_per_device`: 43 per wafer, 5 per die).

   The artifact compares its regenerated batch-1 analytical points with the published `results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/points.json` (`analytical_cross_check`). At this rerun none of them is equal. The published file was last regenerated on 2026-09-25, before the realistic links landed in `configs/hardware/technology.json`. The wafer points are within 1% of it, and the array points are 21-24% below it. The 112/170/226/680-die arrays are not in that artifact, because it rounds differently and caps arrays at 400 dies, so they are built here by the same function.
2. **Decode critical path.** `tools/decode_critical_path.py` prices one token bottom-up on each design:
   * operator depths are measured RTL depths at the slowest routed ASAP7 clock, 1.0339 GHz;
   * collectives are enumerated per layer;
   * the matrix-sweep input is the analytical design's own.

   The best configuration is searched per design and per batch:
   * **Array:** tensor group 1-64 on two-die packages, crossed with board topology {chain, ring, mesh, torus, fc2, fc4, fc8, one switch tier}, with the reduction algorithm best per collective. The layers' bytes are packed onto the dies in order, and a token hops at every tensor-group boundary it crosses. Packages of 4 and 8 dies are searched only in the labelled future-packaging and optimistic variants.
   * **Wafer:** tensor group 2-57, crossed with field grid {square, rect}, with the same reduction rule.

   Batch-1 figures use the batch-1 optimum; batch 64 and batch 4096 each use their own optimum. The fixed-configuration ratios are also in the artifact.
3. **Layout** (`rom_packed`). A layer occupies the units its own weights need: a fraction 0.580 of the stored bytes are layer weights, and Engram tables, embedding and head fill the rest. The group may be partial in the last stage, and on a wafer a group never straddles two wafers. The `uniform` layout, in which every unit carries layer weights and Engram filler, is a sensitivity.
4. **Axes.**
   * **Wafer field crossing:** mesh at 125 ns (75-250 band), then express at 25, 10 and 5 ns and at the wire limit (28.55 mm x 150 ps/mm = 4.28 ns, plus one router cycle of 0.97 ns).
   * **Wafer-to-wafer link:** `rom_wafer_serdes`, the same link class as the array's board link: 209 ns (129-409) at 5.67 TB/s net of FEC per wafer. The earlier 100 ns at the raw 6 TB/s is a sensitivity.
   * **Array links:** UCIe 10 ns (3-30) per edge-adjacent die-to-die link at 4.2 TB/s. Board SerDes is 209 ns (129-409), made up of a 200 ns channel of 112G PAM4 with RS(544,514) FEC and flight, 4 clock-domain-crossing cycles, and a 5-cycle digital endpoint. It carries 1.687 TB/s net per four-die-class package, scaled by sqrt(dies/4) for the package edge. There are two labelled variants: 4- and 8-die future packaging on the same links, and the earlier optimistic links.
   * **Sinkhorn:** the built divider (31 cycles, a 51-cycle normalisation step), a 12-cycle and a 4-cycle divider, an idealised 5-cycle step, and the chain removed.
5. **Crossover.** For each size and Sinkhorn variant, bisection finds the largest field-crossing latency at which the wafer's best batch-1 rate still reaches the array's. The wafer's configuration is re-optimised at every probe.

## The designs

| wafers | wafer silicon (mm2) | array dies (packages) | array silicon (mm2) | array residual (mm2) | ROM (mm2, both) | compute wafer / array (mm2) | HBM stacks wafer / array | static power wafer / array (kW) |
|---|---|---|---|---|---|---|---|---|
| 2 | 92,450 | 112 (56) | 91,280 | 1,170 | 54,404 | 20,545 / 14,845 | 86 / 560 | 6.8 / 8.0 |
| 3 | 138,675 | 170 (85) | 138,550 | 125 | 54,404 | 58,019 / 50,707 | 129 / 850 | 13.6 / 15.6 |
| 4 | 184,900 | 226 (113) | 184,190 | 710 | 54,404 | 95,494 / 85,331 | 172 / 1130 | 20.5 / 23.0 |
| 12 | 554,700 | 680 (340) | 554,200 | 500 | 54,404 | 395,290 / 366,040 | 516 / 3400 | 75.0 / 83.0 |

**Refusals.** Every point holds the weights. The smallest wafer machine that does is 2 wafers, and the smallest array is 88 dies. One wafer is refused: its 46,225 mm2 leaves 37,475 mm2 for ROM against the 54,404 mm2 the weights need, and nothing for compute.

The array's edge buys it 6.5 to 6.6 times the wafer's HBM stacks at every size. That is the analytical model's beachfront rule, and it is tested as a sensitivity below.

## Headline: the built divider, the control fabrics

Array on its point links (two-die packages, UCIe 10 ns, board SerDes 209 ns), wafer on the stitched mesh at 125 ns.

| wafers | wafer b1 (tok/s) | array b1 (tok/s) | b1 wafer/array | b64 wafer/array | wafer agg b4096 (tok/s) | array agg b4096 (tok/s) | b4096 wafer/array | wafer / array tok/s per mm2 at b4096 | wafer / array tok/s per W at b4096 (derived) |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 3,678 | 4,346 | 0.85 | 1.19 | 129,626 | 113,150 | 1.15 | 1.40 / 1.24 | 16.1 / 12.5 | <!-- figure: 0.85 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#summary.cells[id=W2.fdiv31_built.mesh_125].ratio_b1" -->
| 3 | 4,133 | 4,389 | 0.94 | 0.90 | 272,909 | 375,227 | 0.73 | 1.97 / 2.71 | 16.7 / 19.4 | <!-- figure: 0.94 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#summary.cells[id=W3.fdiv31_built.mesh_125].ratio_b1" -->
| 4 | 3,991 | 4,349 | 0.92 | 0.95 | 409,478 | 545,092 | 0.75 | 2.21 / 2.96 | 16.7 / 19.1 | <!-- figure: 0.92 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#summary.cells[id=W4.fdiv31_built.mesh_125].ratio_b1" -->
| 12 | 3,264 | 4,021 | 0.81 | 0.79 | 819,267 | 1,351,517 | 0.61 | 1.48 / 2.44 | 9.8 / 13.9 | <!-- figure: 0.81 src="results/roofline/critical_path/wafer_vs_array_iso_area.json#summary.cells[id=W12.fdiv31_built.mesh_125].ratio_b1" -->

Best configurations at batch 1:

| wafers | wafer | array |
|---|---|---|
| 2 | g8 square x9 | g16 2/fc8 x5 |
| 3 | g4 square x25 | g16 2/fc8 x7 |
| 4 | g8 square x17 | g16 2/fc8 x9 |
| 12 | g12 square x34 | g16 2/fc8 x25 |

Here gN is the tensor group, `k/topo` is dies per package and board topology, and xS is the number of pipeline stages. At batch 4096 the array's optimum is a tensor group of 1 or 2 on a board chain, which keeps its 6.5-6.6 times larger HBM attach busy.

Power is derived, not measured: the design's static power plus the analytical point's dynamic energy per token, times the critical-path rate. Per watt at batch 4096, the wafer leads only at 2 wafers (1.29 times the array). At 3, 4 and 12 wafers the array's larger aggregate outweighs its extra HBM interfaces, and the wafer delivers 0.86, 0.87 and 0.71 of the array's tokens per watt.

## Batch 1 across the fabric and Sinkhorn axes

Wafer/array batch-1 per-user ratio, with the array on its point links. Values above 1 are wafer wins.

**fdiv 31 (built)** (per-token Sinkhorn chain if serial: 167.8 us)

| wafer field crossing | 2 wafers | 3 wafers | 4 wafers | 12 wafers |
|---|---|---|---|---|
| mesh 250 ns (band high) | 0.691 | 0.793 | 0.777 | 0.590 |
| mesh 125 ns (control) | 0.846 | 0.942 | 0.918 | 0.812 |
| mesh 75 ns (band low) | 0.978 | 0.996 | 0.997 | 0.977 |
| express 25 ns | 1.033 | 1.040 | 1.045 | 1.110 |
| express 10 ns | 1.050 | 1.055 | 1.063 | 1.139 |
| express 5 ns | 1.056 | 1.061 | 1.069 | 1.150 |
| express, wire limit 5.25 ns | 1.056 | 1.061 | 1.069 | 1.149 |

**fdiv 12** (per-token Sinkhorn chain if serial: 108.9 us)

| wafer field crossing | 2 wafers | 3 wafers | 4 wafers | 12 wafers |
|---|---|---|---|---|
| mesh 250 ns (band high) | 0.651 | 0.708 | 0.689 | 0.563 |
| mesh 125 ns (control) | 0.798 | 0.863 | 0.841 | 0.775 |
| mesh 75 ns (band low) | 0.929 | 0.971 | 0.962 | 0.933 |
| express 25 ns | 1.181 | 1.172 | 1.162 | 1.230 |
| express 10 ns | 1.274 | 1.223 | 1.221 | 1.377 |
| express 5 ns | 1.298 | 1.246 | 1.244 | 1.420 |
| express, wire limit 5.25 ns | 1.297 | 1.245 | 1.243 | 1.417 |

**fdiv 4** (per-token Sinkhorn chain if serial: 84.2 us)

| wafer field crossing | 2 wafers | 3 wafers | 4 wafers | 12 wafers |
|---|---|---|---|---|
| mesh 250 ns (band high) | 0.650 | 0.708 | 0.689 | 0.563 |
| mesh 125 ns (control) | 0.797 | 0.863 | 0.841 | 0.775 |
| mesh 75 ns (band low) | 0.928 | 0.971 | 0.962 | 0.933 |
| express 25 ns | 1.181 | 1.188 | 1.194 | 1.230 |
| express 10 ns | 1.308 | 1.308 | 1.313 | 1.424 |
| express 5 ns | 1.379 | 1.349 | 1.347 | 1.503 |
| express, wire limit 5.25 ns | 1.375 | 1.348 | 1.346 | 1.499 |

**Sinkhorn removed** (per-token Sinkhorn chain if serial: 0.0 us)

| wafer field crossing | 2 wafers | 3 wafers | 4 wafers | 12 wafers |
|---|---|---|---|---|
| mesh 250 ns (band high) | 0.650 | 0.708 | 0.689 | 0.563 |
| mesh 125 ns (control) | 0.797 | 0.863 | 0.841 | 0.775 |
| mesh 75 ns (band low) | 0.928 | 0.971 | 0.962 | 0.933 |
| express 25 ns | 1.181 | 1.188 | 1.194 | 1.230 |
| express 10 ns | 1.308 | 1.308 | 1.313 | 1.424 |
| express 5 ns | 1.379 | 1.357 | 1.362 | 1.503 |
| express, wire limit 5.25 ns | 1.375 | 1.354 | 1.360 | 1.499 |

The 5-cycle idealised step and "removed" match the 4-cycle divider to within 0.02 in every cell. At a 4-cycle divider, the 20-iteration Sinkhorn side branch is already shorter than the path it runs beside, so it leaves the critical path. From that point the divider stops mattering, and the fabric alone decides.

On the mesh, a faster divider lowers the wafer's ratio. The array is Sinkhorn-bound on its own path and gains more than the wafer does. With an express fabric the order reverses.

### Why: the W = 12 critical path at batch 1 (microseconds)

| case | compute chain | weight sweep | KV sweep | collective latency | collective bytes | pipeline hops | control | total |
|---|---|---|---|---|---|---|---|---|
| wafer, built divider, mesh 125 ns | 112.9 | 46.5 | 5.7 | 118.6 | 0.0 | 15.2 | 7.4 | 306.4 |
| array, built divider, point links | 170.2 | 17.7 | 0.4 | 23.0 | 9.2 | 22.5 | 5.7 | 248.7 |
| wafer, built divider, wire limit | 204.2 | 3.1 | 2.1 | 1.9 | 0.0 | 1.9 | 3.2 | 216.5 |
| array, built divider, point links | 170.2 | 17.7 | 0.4 | 23.0 | 9.2 | 22.5 | 5.7 | 248.7 |
| wafer, Sinkhorn removed, mesh 125 ns | 111.9 | 46.5 | 5.7 | 118.6 | 0.0 | 15.2 | 7.4 | 305.4 |
| array, Sinkhorn removed, point links | 114.6 | 34.2 | 0.4 | 41.7 | 15.9 | 22.5 | 7.4 | 236.7 |
| wafer, Sinkhorn removed, wire limit | 115.1 | 19.9 | 2.5 | 11.1 | 0.1 | 1.9 | 7.3 | 157.9 |
| array, Sinkhorn removed, point links | 114.6 | 34.2 | 0.4 | 41.7 | 15.9 | 22.5 | 7.4 | 236.7 |

The array rows do not depend on the wafer's fabric, and are repeated beside each wafer row for comparison. The wafer's configuration is g12 square x34 on the mesh and g28 square x15 at the wire limit. The array's is g16 2/fc8 x25 throughout.

Why the wafer loses on the control mesh:

* **The mesh costs the wafer in two places.** About 119 us of the wafer's critical path is collective latency. The mesh also pushes the wafer to small tensor groups (12 fields, 34 stages), which leaves it about 47 us of weight sweep.

Why it wins with a fast fabric:

* **A fast fabric removes both of those costs.** At the wire limit the wafer pays about 4 us for collectives and pipeline hops.
* **The array's interconnect is no longer nearly free.** On two-die packages its tensor group of 16 spans eight packages, so every collective and each of its 25 pipeline hops crosses the 209 ns board SerDes. That costs it about 55 us of collective latency, collective bytes and pipeline hops.

With the built divider, the wafer's longer compute chain in its wider configuration (204 against 170 us) gives most of that back, which leaves a lead of 1.15. With the chain off the path, the compute chains match (115 against 115 us). What is left is the whole of the wafer's lead:

* the array's interconnect (about 80 us) against the wafer's (about 13 us);
* the array's weight sweep (34 us) against the wafer's (20 us).

## Crossover: the largest field crossing at which the wafer matches the array at batch 1 (ns)

| Sinkhorn variant | array links | 2 wafers | 3 wafers | 4 wafers | 12 wafers |
|---|---|---|---|---|---|
| fdiv 31 (built) | point (UCIe 10, SerDes 209 ns) | 61.2 | 70.1 | 70.6 | 66.3 |
| fdiv 31 (built) | band low (3, 129 ns) | 41.6 | 45.2 | 48.4 | 51.3 |
| fdiv 12 | point (UCIe 10, SerDes 209 ns) | 56.5 | 66.8 | 64.1 | 60.1 |
| fdiv 12 | band low (3, 129 ns) | 39.0 | 42.9 | 40.7 | 42.0 |
| fdiv 4 | point (UCIe 10, SerDes 209 ns) | 56.5 | 66.8 | 64.1 | 60.0 |
| fdiv 4 | band low (3, 129 ns) | 39.0 | 42.9 | 40.6 | 42.0 |
| Sinkhorn removed | point (UCIe 10, SerDes 209 ns) | 56.5 | 66.8 | 64.1 | 60.0 |
| Sinkhorn removed | band low (3, 129 ns) | 39.0 | 42.9 | 40.6 | 42.0 |

The crossover is highest with the built divider. The Sinkhorn chain, common to both machines, hides part of the wafer's fabric latency, and a faster divider exposes it. From the 12-cycle divider on, the chain is off the critical path and the crossover is the same to within 0.1 ns. The idealised 5-cycle step (not shown) equals the 4-cycle row. Every crossover lies between the routed express link's 30 ns and the mesh band's 75 ns end.

## Batch 64 and batch 4096

| wafers | Sinkhorn | fabric | wafer b64 (tok/s/user) | array b64 (tok/s/user) | b64 wafer/array | b4096 wafer/array |
|---|---|---|---|---|---|---|
| 2 | fdiv31_built | mesh_125 | 1,963 | 1,649 | 1.191 | 1.146 |
| 2 | fdiv31_built | express_10 | 1,963 | 1,649 | 1.191 | 1.146 |
| 2 | fdiv31_built | express_wire_limited | 1,963 | 1,649 | 1.191 | 1.146 |
| 2 | fdiv4 | mesh_125 | 1,963 | 1,649 | 1.191 | 1.146 |
| 2 | fdiv4 | express_10 | 1,963 | 1,649 | 1.191 | 1.146 |
| 2 | fdiv4 | express_wire_limited | 1,963 | 1,649 | 1.191 | 1.146 |
| 3 | fdiv31_built | mesh_125 | 3,680 | 4,085 | 0.901 | 0.727 |
| 3 | fdiv31_built | express_10 | 4,034 | 4,085 | 0.988 | 0.727 |
| 3 | fdiv31_built | express_wire_limited | 4,034 | 4,085 | 0.988 | 0.727 |
| 3 | fdiv4 | mesh_125 | 3,694 | 4,102 | 0.900 | 0.727 |
| 3 | fdiv4 | express_10 | 4,034 | 4,102 | 0.983 | 0.727 |
| 3 | fdiv4 | express_wire_limited | 4,034 | 4,102 | 0.983 | 0.727 |
| 4 | fdiv31_built | mesh_125 | 3,874 | 4,084 | 0.949 | 0.751 |
| 4 | fdiv31_built | express_10 | 4,255 | 4,084 | 1.042 | 0.751 |
| 4 | fdiv31_built | express_wire_limited | 4,261 | 4,084 | 1.043 | 0.751 |
| 4 | fdiv4 | mesh_125 | 3,992 | 4,231 | 0.944 | 0.751 |
| 4 | fdiv4 | express_10 | 4,944 | 4,231 | 1.169 | 0.751 |
| 4 | fdiv4 | express_wire_limited | 4,987 | 4,231 | 1.179 | 0.751 |
| 12 | fdiv31_built | mesh_125 | 3,074 | 3,906 | 0.787 | 0.606 |
| 12 | fdiv31_built | express_10 | 4,448 | 3,906 | 1.139 | 0.606 |
| 12 | fdiv31_built | express_wire_limited | 4,475 | 3,906 | 1.146 | 0.606 |
| 12 | fdiv4 | mesh_125 | 3,083 | 4,034 | 0.764 | 0.606 |
| 12 | fdiv4 | express_10 | 5,257 | 4,034 | 1.303 | 0.606 |
| 12 | fdiv4 | express_wire_limited | 5,415 | 4,034 | 1.342 | 0.606 |

At batch 64 the 2-wafer point is the one size where the wafer leads in every variant, and there the ratio does not depend on the fabric. Its 112-die array is too small to stage 64 users well: it has few dies per stage and large microbatches.

At 3 wafers the wafer trails even with an express fabric (0.98-0.99). At 4 and 12 wafers an express fabric puts it ahead, by 1.04-1.18 and 1.12-1.34.

At batch 4096 both machines are occupancy-bound, so the ratio does not depend on the fabric. The array's larger HBM attach wins at every size but 2 wafers.

## Sensitivities that could overturn the result

Wafer/array ratios with the built divider, for each size and wafer fabric. Each row changes one assumption on the side or sides it applies to.

| sensitivity | fabric | 2 wafers: b1 / b64 / b4096 | 3 wafers: b1 / b64 / b4096 | 4 wafers: b1 / b64 / b4096 | 12 wafers: b1 / b64 / b4096 |
|---|---|---|---|---|---|
| baseline | mesh_125 | 0.85 / 1.19 / 1.15 | 0.94 / 0.90 / 0.73 | 0.92 / 0.95 / 0.75 | 0.81 / 0.79 / 0.61 |
| baseline | express_wire_limited | 1.06 / 1.19 / 1.15 | 1.06 / 0.99 / 0.73 | 1.07 / 1.04 / 0.75 | 1.15 / 1.15 / 0.61 |
| uniform layout (every unit carries layer weights) | mesh_125 | 0.72 / 0.66 / 0.67 | 0.73 / 0.54 / 0.55 | 0.74 / 0.65 / 0.51 | 0.81 / 0.78 / 0.94 |
| uniform layout (every unit carries layer weights) | express_wire_limited | 1.06 / 0.66 / 0.67 | 1.07 / 0.82 / 0.55 | 1.08 / 1.01 / 0.51 | 1.27 / 1.25 / 0.94 |
| array limited to the wafer's HBM stack count | mesh_125 | 0.85 / 1.27 / 1.23 | 0.95 / 1.01 / 0.88 | 0.93 / 1.01 / 0.93 | 0.82 / 0.80 / 0.73 |
| array limited to the wafer's HBM stack count | express_wire_limited | 1.06 / 1.27 / 1.23 | 1.07 / 1.11 / 0.88 | 1.08 / 1.11 / 0.93 | 1.16 / 1.16 / 0.73 |
| lanes from the analytical compute roof | mesh_125 | 0.85 / 1.27 / 1.23 | 0.94 / 0.93 / 0.78 | 0.92 / 0.96 / 0.80 | 0.81 / 0.79 / 0.62 |
| lanes from the analytical compute roof | express_wire_limited | 1.06 / 1.27 / 1.23 | 1.06 / 1.01 / 0.78 | 1.07 / 1.06 / 0.80 | 1.15 / 1.15 / 0.62 |
| no producer/consumer chaining | mesh_125 | 0.83 / 1.19 / 1.15 | 0.93 / 0.90 / 0.73 | 0.91 / 0.95 / 0.75 | 0.81 / 0.78 / 0.61 |
| no producer/consumer chaining | express_wire_limited | 1.06 / 1.19 / 1.15 | 1.06 / 1.03 / 0.73 | 1.07 / 1.06 / 0.75 | 1.16 / 1.15 / 0.61 |
| HBM gather 300 ns (assumed 100) | mesh_125 | 0.85 / 1.19 / 1.15 | 0.94 / 0.90 / 0.73 | 0.92 / 0.95 / 0.75 | 0.81 / 0.79 / 0.61 |
| HBM gather 300 ns (assumed 100) | express_wire_limited | 1.06 / 1.19 / 1.15 | 1.06 / 0.99 / 0.73 | 1.07 / 1.04 / 0.75 | 1.15 / 1.14 / 0.61 |
| inter-wafer SerDes 129 ns (band low) | mesh_125 | 0.85 / 1.19 / 1.15 | 0.94 / 0.90 / 0.73 | 0.92 / 0.95 / 0.75 | 0.81 / 0.79 / 0.61 |
| inter-wafer SerDes 129 ns (band low) | express_wire_limited | 1.06 / 1.19 / 1.15 | 1.06 / 0.99 / 0.73 | 1.07 / 1.04 / 0.75 | 1.15 / 1.15 / 0.61 |
| inter-wafer SerDes 409 ns (band high) | mesh_125 | 0.85 / 1.19 / 1.15 | 0.94 / 0.90 / 0.73 | 0.92 / 0.95 / 0.75 | 0.81 / 0.78 / 0.61 |
| inter-wafer SerDes 409 ns (band high) | express_wire_limited | 1.05 / 1.19 / 1.15 | 1.06 / 0.99 / 0.73 | 1.07 / 1.04 / 0.75 | 1.14 / 1.14 / 0.61 |
| inter-wafer SerDes 100 ns at 6 TB/s (the earlier, optimistic link) | mesh_125 | 0.85 / 1.19 / 1.15 | 0.94 / 0.90 / 0.73 | 0.92 / 0.95 / 0.75 | 0.81 / 0.79 / 0.61 |
| inter-wafer SerDes 100 ns at 6 TB/s (the earlier, optimistic link) | express_wire_limited | 1.06 / 1.19 / 1.15 | 1.06 / 0.99 / 0.73 | 1.07 / 1.04 / 0.75 | 1.15 / 1.15 / 0.61 |
| array at 113/227/681 dies (no package rounding; 170 is already whole) | mesh_125 | 0.85 / 1.17 / 1.10 | - | 0.92 / 0.95 / 0.75 | 0.81 / 0.79 / 0.61 |
| array at 113/227/681 dies (no package rounding; 170 is already whole) | express_wire_limited | 1.06 / 1.17 / 1.10 | - | 1.07 / 1.04 / 0.75 | 1.15 / 1.14 / 0.61 |

How to read the sensitivities:

* **Only the fabric moves the batch-1 result.** None of the non-fabric sensitivities moves the batch-1 ratio across 1: on the mesh the wafer stays at or below 0.95, and at the wire limit at or above 1.05. The uniform layout is the largest mover. On the mesh it lowers the wafer's ratio at 2-4 wafers, and at the wire limit it raises the 12-wafer lead to 1.27.
* **The wafer-to-wafer link does not matter.** Pricing it like the board link, anywhere in its 129-409 ns band, or at the earlier optimistic 100 ns, moves no ratio by more than 0.01. The rerun's shift comes from the array's links (see the verdict), not from the wafer's.
* **Batch 4096 moves with the HBM beachfront rule, but does not flip.** Holding the array to the wafer's HBM stack count raises the wafer's aggregate ratio from 0.73/0.75/0.61 to 0.88/0.93/0.73 at 3/4/12 wafers, and from 1.15 to 1.23 at 2. The array's larger edge is part of its aggregate lead, not all of it.
* **The uniform layout cuts the wafer's aggregate at 2-4 wafers** (0.51-0.67), because it forces more fields per layer. At 12 wafers it raises the aggregate ratio to 0.94.

## Manufacturing and complexity

The repository has no numeric yield, test, stitching or cost model for either machine. These are listed as open gaps in docs/SOURCES.md ("No public source currently establishes ... yield, repair overhead, ... wafer HBM beachfront, stitched-wafer timing, power delivery, cooling, unit cost, NRE") and in docs/PRE_NDA_TECHNOLOGY_ROADMAP.md. The comparison below is therefore qualitative, and no number is invented for it.

* **Yield and redundancy.** A wafer must tolerate every defect in place, so it needs spare fields and routing-around. Cerebras reports redundant-link repair across 84 stitched dies (docs/SOURCES.md, SRC-CEREBRAS-WSE3, used there as a feasibility anchor only). An array can discard a bad die before packaging, using known-good-die test. The ROM service RTL implements row redundancy from a BIST defect list and refuses column redundancy (docs/ROM_SERVICE_RTL.md). There is no defect density and no yield model for either machine (docs/ARCHITECTURE_ATLAS.html: "yield/redundancy handling (not started)").
* **Stitching.** The wafer needs cross-field stitched wiring. docs/CHIP_ARCHITECTURE_DESIGN.md sketches an 8-by-6 grid of 26-by-33 mm fields. The array needs none: docs/DEEPSEEK_V4_ROM_ARRAY_IMPLEMENTATION_PLAN.md lists "no reticle stitching, no distributed-HBM-around-a-wafer package" as its reason to exist. The express fabric the wafer needs in order to win is routed on ASAP7 but not fabricated, and it runs across exactly these stitched boundaries.
* **HBM attach.** The wafer's KV bandwidth is limited by its perimeter. The beachfront rule (`max_hbm_stacks_per_device`: 12 mm stack pitch at 0.6 edge utilisation, taken from A100 and B200) gives 43 stacks per wafer, against 5 per 815 mm2 die, so equal silicon gives the array 6.5 to 6.6 times the stacks. results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/REPORT.md records that perimeter grows as the square root of area. The same 860 mm perimeter must also carry the inter-wafer SerDes, and whether both fit at once is not checked anywhere in the repository.
* **Cooling.** Neither machine is cooling-bound under the A100-derived `cooling_limit_w_per_mm2`. The candidate REPORT puts both the worst ROM wafer and the worst large array below half of their budget. Cooling does not separate the two.
* **Test.** No wafer-level test, burn-in or known-good-die procedure is modelled (docs/PRE_NDA_TECHNOLOGY_ROADMAP.md lists test time and repair coverage as open). An array's packages can be tested and binned one at a time. A wafer is one part.

The asymmetry is qualitative but one-directional: every item on the list is harder for the wafer. Against it, the model now finds a real performance case for the wafer:

* a batch-1 lead of up to 1.15 with the built divider;
* a batch-1 lead of up to 1.50 with an unbuilt 4-cycle divider.

Both need an express fabric that is routed but not fabricated. The same wafer trails the array's aggregate at 3, 4 and 12 wafers (0.61-0.75 at batch 4096).

## Assumptions and grades

| id | grade | assumption | direction |
|---|---|---|---|
| A1 | derived | Designs are sized by the analytical model's own code (run_roofline_studies._build_rom_budget, n5_vs_b200, batched, spare area to SRAM, HBM-KV provisioned for 4,096 users at 200K, stacks capped by the die/wafer edge); nothing is re-derived here. | neutral: the same rule on both sides |
| A2 | derived | Iso-area: the array gets W x 46,225 / 815 dies rounded DOWN to whole 2-die packages, the shipping (B200-class, ~3.3-reticle interposer) package (the silicon shortfall per pair is pairs[].array_residual_fraction, at most 2 dies: 0.0127 of the wafer area at W = 2, 0.0038 at W = 4 and 0.0009 at W = 3 and 12). | favours the wafer |
| A3 | measured | Operator depths are the repository's routed/campaigned RTL (decode_critical_path RTL_SOURCES) at the slowest routed clock among the token path's units (1.0339 GHz ASAP7), applied to N5 on both sides. | common-mode |
| A4 | derived | Matrix-sweep time is the analytical design's own (max(compute, weight_read)/stage balance, scaled by g_ref/g), apportioned per matvec; lanes from routed lane areas. | common-mode |
| A5 | derived | Layout rom_packed: one layer occupies units x 0.580 (its share of the stored bytes) / 40; Engram tables, embedding and head fill the other units. On the array the layers' bytes are packed onto the dies in order (decode_critical_path.packed_placement) and a token hops at every tensor-group boundary it crosses. The 'uniform' layout (units/40) is a sensitivity. | favours neither; fewer stages for both |
| A6 | derived | Wafer control fabric: links.on_wafer_n5 125 ns per 28.55 mm field crossing (75-250 ns band); per-field-edge bandwidth on_wafer_n5.bytes_s / 57 / 4; wafers joined by rom_wafer_serdes, the same 112G PAM4 + RS(544,514) FEC link class as the array's board link (209 ns, 129-409, 5.67 TB/s net per wafer); the earlier 100 ns at the raw 6 TB/s is the wafer_serdes_optimistic_100ns sensitivity. | the axis under test |
| A7 | assumed | Designed express fabric: 25/10/5 ns per field crossing are design targets with no silicon; the wire limit is 28.55 mm x 150 ps/mm (assumed, 100-250) + one router cycle (assumed). The express fabric keeps the mesh's bandwidth and is applied to every field crossing (collectives and pipeline hops). | favours the wafer |
| A8 | derived/assumed | Array links: two-die packages (shipping); rom_package_ucie 10 ns (3-30) per edge-adjacent link, a 2 x 2 package's diagonal relayed (+4 ns) or on a standard-package link; rom_board_serdes 209 ns (129-409: 112G PAM4, RS(544,514) FEC, 4 CDC cycles, 5 endpoint cycles) at 1.69 TB/s net per four-die-class package, lanes scaling with the package edge; one switch tier 250 ns assumed. 4- and 8-die packages and the earlier optimistic links are labelled array_links variants. | the array's axis |
| A9 | measured/assumed | Sinkhorn: 20 iterations x 2 normalisations per sublayer, each 3 sequential fadd + eps + fdiv (31 cycles, built); fdiv 12/4 and the 5-cycle step are unbuilt what-ifs; 'removed' is hypothetical and not the model. | common-mode per token |
| A10 | assumed | HBM random-row gather latency 100 ns (no constant in technology.json), charged only on index-source layers. | common-mode |
| A11 | derived | Power = the design's static power + the analytical point's dynamic energy per token x the critical-path aggregate rate (a derived estimate; no measured power). | neutral |
| A12 | derived | Uniform expert routing (the router trace is synthetic); experts striped over the tensor group (deterministic); reduction algorithm best per collective. | common-mode |

## What this study does not settle

* **Absolute rates are projections.** Every rate is a projection from ASAP7 RTL depths at 1.0339 GHz applied at N5, and no V4.1 token has been simulated across more than one node. The ratios are the robust output.
* **The express fabric is routed, not built, and not swept at its measured point.** The routed ASAP7 express link extrapolates to 30 ns per field crossing, below every crossover here (56.5-70.6 ns against the array's point links, 39.0-51.3 ns against its fast band). The study's express axis is 25/10/5 ns and the wire limit, so the lead at 30 ns is bracketed but not computed. Before the wafer is argued for, the study should add that point, and at the link's measured 12.5 TB/s per field edge rather than the mesh's bandwidth (A7).
* **The array's side rests on a packaging choice.** The array is limited to shipping two-die packages and a 209 ns board SerDes. With 4- and 8-die packages, which are roadmap interposers, the built-divider wire-limit lead shrinks to 1.00-1.07. On the earlier optimistic links it is 1.00-1.03. A four-die package would largely close the batch-1 gap.
* **Routing is uniform.** The router trace is synthetic, so the expert-parallel alternative is not the headline, and the stripe layout used here is deterministic.
* **The published analytical points are older than these links.** `results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/points.json` predates the realistic-link change, so `analytical_cross_check` reports no equal point: the arrays are 21-24% below it. This study recomputes everything from source and does not read that file's rates. `results/roofline/critical_path/decode_critical_path.json` was regenerated in the same change as this artifact.
