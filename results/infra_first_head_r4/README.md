# INFRA-FIRST-HEAD-4: s81_head plan delta, measured PG and VSS-lane clock straps

Lane INFRA-FIRST-HEAD-4 is the single owner of the s81_head plan, clock and infra (12.9a). It continues R3 (claude/infra-head3-1027@77ae153cac).
Plan in this commit: `physical/die_plan/s81_head/die_plan.json` sha256 5dbd7bdc… (was 674a8ac9). G0/G0C **PASS, 0 errors / 6 warnings** (g0_report.json).

## 1. Plan delta (task 1)

* **hd_tile clock tap moved to the channel cross (354.24, 354.24).** It replaces (354.24, 518.4).
* **Declared clock slots.** `partition_types.*.clock.die_islands_um` holds one 8.64-um square per R3 tree site (tools/s81_head/head_slot_census.py, head_infra_delta_r4.py).
  * Slots are 1387 sites over 13 types: hd_tile 69 on the channel row, spine 47+18, stations 16/13/10/10/5/3, mesh 17, ctl 7, host 7, lep0N 5.
  * No slot overlaps a hard core.
  * Slots are centred on the site and not clipped at the outline, so island_lattice displacement is 0.
* **master_plan --declared-slots (opt-in, default unchanged).**
  * The declared slots become islands (kind=partition_slot, role=clock_slot).
  * island_ft_inputs lists a slot that a replica does not use, with no die-level load in it, as a **declared tie** (TIELO). Result: 177 ties, listed per instance in gates.json `declared_ties`.
  * Test: tools/die_plan/test_master_plan_h4.py (3 PASS). The existing master_plan tests r1/r3/r5/r6 also PASS (53).
* **Die PG grid → M8 0.48@4.32 / M9 6.48@34.56** (the "C3" grid). This is the best lane-feasible grid at 150 um and also the 75-um fallback grid, so the strap plan does not depend on the bump decision (section 2).
* **Straps on the VSS lanes** (head_mesh_r3.py --pg-lanes). Every M8 row and M9 column is snapped to the nearest legal 16W lane in a VSS-adjacent half-gap of the plan grid:
  * strap ends follow the end strap they sit on, so the mesh is still **one component** (147 straps: 52 M8 + 95 M9);
  * riser/jog is at most 8.64 um, mean 2.37 um;
  * all 300 drivers are on a strap;
  * footless_stubs PASS.
* **Spine (GEOM-REVIEW-18 on HEAD-3): we ADD STRAPS** (head_mesh_r3.py --spine-columns). We do not declare a region boundary.
  * The 1740.96-um column gap over the spine (x 7890→9631) now carries 9 M9 spine columns at the tile column pitch, running from the serdes rows to the serdes rows.
  * The die stays one continuous mesh (12.8e1): one droop / CPPR region.
  * Viewed in mesh/r3_mesh_tree.png and r3_zoom_spine.png. GEOM should check one point: column x 8752.32 runs 8.64 um from the spine trunk at x 8760.96.

## 2. PG on MEASURED activity (task 2, OWNER decision via COORD)

**Activity source.** tb_s81hd_mini scenario A, run on current RTL with Verilator 5.050 --trace:
* config: CUT 511, SPLIT9, skew-11 images, 2 positions;
* result: TB_PASS (row 21946, 4173a558, 8430 cycles/position);
* VCD: 18212 cycles over the full elemA (g_a[0]) and elemB.

Per-bit toggle rates in transitions per cycle:

| | bits | mean | median | p90 | max | zero |
|---|---|---|---|---|---|---|
| elemA | 233173 | 0.203 | 0.116 | 0.457 | 0.908 | 25% |
| elemB | 224203 | 0.216 | 0.193 | 0.458 | 0.908 | 27% |

**Annotation.** OpenSTA report_power on the hold2 GRT views (tools/s81_head/head_pg_power_meas.tcl):
* register outputs and input ports come from the VCD (set_power_activity -pins); combinational activity is propagated;
* registers matched by name: A 7029 of 28723, B 6416 of 25983. Unmatched registers get the matched mean (A 0.263, B 0.286). The matched maximum is 0.908.

| number | value | flat 0.5 (R3) | label |
|---|---|---|---|
| elemA power | **0.1244 W** | 0.1487 | UNCHECKED |
| elemB power | **0.1189 W** | 0.1370 | UNCHECKED |
| hd_tile upper (glue at core density) | 0.924 W, 1.258 W/mm2 | 1.097, 1.493 | UNCHECKED |
| die tiles upper | 243.9 W | 289.6 | UNCHECKED |
| analytic IR @150, best grid (M8 1.92@8.64/M9 3.84@8.64, 91/99% tracks, no clock lane) | 58.4 mV | | UNCHECKED |
| analytic IR @150, best lane-feasible (C3) | 94.4 mV | | UNCHECKED |
| **PDNSim IR @150, C3, tile window [3801.6,6704.64,5287.68,8190.72]** | **worst 92.4 / avg 54.9 mV → FAIL (35 mV)** | | UNCHECKED |
| analytic IR @75, C3 | 17.2 mV | 24.5 (R3) | UNCHECKED |
| **PDNSim IR @75, C3, same window** | **worst 20.6 / avg 10.0 mV → PASS** | | UNCHECKED |

Measured activity lowers power by only 13-16%. About 72% of the power is internal power: flop clock pins, clock tree and ROM macros, all of which switch every cycle. **150 um therefore fails at measured activity, so we raise an ASK.**
* Option (a): adopt 75-um bumps for the core region (C3 at 75 passes with 41% margin).
* Option (b): keep 150 um and accept no grid. The best grid without clock lanes still reaches 58 mV at about 99% M9 tracks.
* The plan keeps the 150-um bumps until the ruling. Only the PG grid changed, to C3, which serves both pitches.

## 3. Master-plan gates on plan r4c + mesh m4c (`master_plan --mesh m4c --declared-slots`)

**Newly PASS** (R3 → R4):
* clock_sites (599 nodes + 300 drivers off island → 0);
* island_lattice (displacement max 0.007 um);
* footless_stubs (2978 no_stub → 0);
* clock_shield pg_overlaps (118 → 0).

**Still FAIL, with causes:**
* **clock_shield: 0 of 147 shielded.** master_plan counts a strap as shielded only when the plan PG grid comes within 0.16 um on both sides. Any legal lane in a PG half-gap is 1.68 um or more wide. The real shields are the VSS wires that die_clock_mesh --rule-12-8 (CLOCK-128) draws next to every strap. This is a gap in the master_plan model, reported to MASTER-PLAN.
* clock_entry / core_reach / core_insertion_model (5 / 2 cores): edge pins on the head cores. This waits on HEAD-CORE-R13: elemA/elemB re-pin plus measured insertions.
* tree_balance: 175 of 300 families have unequal length. The R3 tree is a length-family form, not a delay-balanced tree. This needs either the CTS build (task 3) or a ruling.
* tree_commensurate (1 PHY entry), die_pair_skew_model (diagnostic only).
* tree_on_islands (master_plan form): 177 leg-repeater gaps, the worst 4588 um. Legs cross station and spine areas that have no declared repeater slot. head_mesh_r3's own check is PASS.
* island_ft_inputs: 5280 open. All of them are **in-core** tree_leaf islands, i.e. core pushdown ft ports. They are not proven dead, so they are **not tied** (only the 177 unused partition slots are).

infra_sites, clock_rep_sites and tap_region_containment did not run (no place.json and no part_region in this mesh form).

## 4. Not done in this round
* Tasks 3-5: die_clock_mesh combo build + render + GEOM REQ, die GRT ≥50 iterations, mesh MC and related-pair STA with the R13 insertions. These come next, after the 150/75 ruling, and are not started.
* Head bind gaps from COORD on R13 ASK4 (per-instance ID straps, hd_serdes binding, nested port-bind walk + test + LEC). These are in sub-lane HEAD-BIND-4, branch claude/head-bind4-1027 (still running at this commit).

Scratch: intel2:/srv/opentallas-scratch2/claude/infra-head4-1027 (activity_vcd.json 26 MB, psm_b150/psm_b75 kits). The 24-GB VCD was deleted after parsing.
