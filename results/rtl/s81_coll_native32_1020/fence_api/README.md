# Native cell fence API proof

Native OpenROAD26Q3-1510-g6cb3f2b704, ORFS image used by current gates, fleet ep6. This is a placement-tool fixture, not candidate RTL/timing/PG/routing qualification.

`physical/dscoll_cx/native_cell_fence.tcl` creates an EXCLUSIVE dbRegion and a VOLTAGE_DOMAIN dbGroup **parented to that region**. The native GPL and DPL consume this placement group. It creates no supply nets/rails, changes no die/core dimensions and changes no timing constraints.

- Initial40 real ASAP7DFFs in two disjoint boxes: independent post-GPL and post-DP FULL BBOX assertions PASS, check_placement0 (unit2767822). Wrapper itself repeated PASS(unit4114029).
- Runtime birth negative: two new movable DFFs born OUTSIDE boxes after GPL, assigned to the proper groups, then DP: region/overlap failure DPL-0033 (unit1839914). **Ownership alone does not recover arbitrary outside births.** Preserved fence_helper_birth_verified.log.
- Runtime birth positive: same births, explicit owner binding, NEWcells-only clamp seed inside assigned boxes before DP; all42 cells legal, full group bbox21+21 PASS, ALL non-macro cells final-band bbox PASS, check_placement0 (unit2614629). Preserved fence_helper_birth_seed_verified.log. No preexisting cell is manually moved.

Usage: create initial groups with ot_native_cell_fence name {x0 y0 x1 y1} $exact_instance_names. For future births, use ot_native_cell_fence_add with explicitly modeled owner names, then ot_native_cell_fence_seed_new for ONLY those births, then native detailed_placement and ot_native_cell_fence_check for every group. ot_native_cell_band_check audits ALL non-macro instances, including clock/reset/hold buffers, fixed/filler cells. Single-full-band owner alone may adopt all unowned cells; multiple-region HWIN requires its mapped driver/sink ownership graph. Verify hooks execute before every legalization and final stage, including CTS/GRT repair births. Fixed cells cannot be seeded; wrong ownership/overfull regions must fail. Timing, reach and native PG audits must run after placement. This helper does not fence routed metal or vias.

Run: docker run --rm -v "$PWD:/work" --entrypoint /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad openroad/orfs:latest -exit /work/fence_fixture.tcl (place helper at /work/native_cell_fence.tcl).
