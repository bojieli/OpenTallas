# BW safe3 single-band diagnostic kit

Source base: `8389e864f`. No RTL changes. Generate with:

```
python3 tools/ref_tile/ref_tile.py gen tools/ref_tile/specs_hbm_bw_safe_1019/hdie_pc_ctrl_bw_safe3.json
python3 tools/ref_tile/pre_route_gate.py physical/ref_tile/hdie_pc_ctrl_bw_safe3
```

This is a synthesis/floorplan diagnostic with `no_bench_reason`, not a submission or production qualification. The portable transaction gate currently fails its random-workload rate check; preserve that evidence. No heavy synthesis, placement, routing, or submission was launched to prepare this kit.

Geometry: 432 × 475.2 µm, thirteen stock SRAMs at the safe2 origins on the 43.2 µm lattice. One connected full-width core FENCE is x=2.16..429.84, y=270..291.06 µm, area 9007 µm². Its edges align to the 0.27 µm cell rows. The top of the adjacent macro row is 257.064 µm and the next macro row begins at 302.4 µm, so no macro intersects the band. The inherited 3679.539 µm² standard area is stale: measure the current synthesis area and adjust band height if needed before physical review. At 40–60% density this band admits 3603–5404 µm² of core cells, less boundary exceptions.

Custom hooks replace the generated duplicate boundary wrappers, preserving the stock order: pin_reg_split, leaf_iohold, io_flop_at_pins, then the core-band assignment. Hold and pin flops stay FIRM through global placement and are excluded from the band. PRE_DETAIL_PLACE uses the stock release hooks and reloads both boundary-name lists, then assigns newly inserted soft cells to the same band. POST_IO_PLACEMENT moves only clk to W/M4 at y=278.208 µm and saves the updated IO database/pin plan. Other pins retain their balanced full-face plan.

OpenDB API feasibility was measured on the fleet's OpenROAD 26Q3-1510 with an existing safe2 floorplan ODB: the final hook creates one region/box and associates 34,081 soft cells. Initial API mistakes were corrected: the OpenDB enum is EXCLUSIVE (DEF TYPE FENCE), and association is region.addGroup(group). This smoke checks API execution, not placement fit or timing. See `api_smoke.log`; repeat `api_smoke.tcl` on the fleet with INPUT_ODB. The primary API definitions are [OpenDB db.h](https://github.com/The-OpenROAD-Project/OpenROAD/blob/master/src/odb/include/odb/db.h); the [DEF writer](https://github.com/The-OpenROAD-Project/OpenROAD/blob/master/src/odb/src/defout/defout_impl.cpp) maps EXCLUSIVE to FENCE.

Timing blocker: route clock is the actual HBM 1024 ps. Existing spine-mode generator signoff remains 833.333 ps. `route.signoff_period_ps=1024` is rejected unless native_leaf mode is multiple_cts_roots/hybrid_entries. No fake mode or manual signoff override is introduced. A real clock-domain receipt/flow extension is required before 1024 ps signoff can be claimed. No clock uncertainty or hold margin changed (60/25 ps; 0.03 ns repair margins).

Safe-design checklist for this diagnostic:

1. Pins — fixed: native pin captures plus unchanged stock split/hold/flop hooks; balanced face plan, clock beside the band. Actual pin-flop audit remains required.
2. Reach — waived-with-reason: no new RTL; actual <=405 µm stage reach must be measured after placement.
3. Fanout — fixed in source base: kept selectors and 72 same-edge reset regions; synthesis must verify they survive.
4. Depth — fixed in source base: SRAM head capture separates macro read from column decision; timing remains unmeasured for this kit.
5. Storage — PASS design inventory: thirteen SRAMs; unchanged payload/identity storage.
6. Floorplan — fixed: one full-width FENCE, lattice origins, existing channels/halo and boundary exceptions. Updated area and actual placement still required; global low-fill waiver inherited from coordinator.
7. Clock — waived-with-reason: 1024 ps route, 833.333 ps generated signoff blocker; spread TT/FF unmeasured, no insertion/spread claim.
8. Schedule — PASS scope: no RTL, protocol or latency changes in this kit. Production qualification remains blocked.
