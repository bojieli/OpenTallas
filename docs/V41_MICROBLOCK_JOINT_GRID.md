# V4.1 one-macro physical qualification

These experiments test only one VM macro and one MP1 macro with nearby registered interfaces. They do not establish complete VM/ME composition or operating frequency. Primary test ports are false-pathed; every internal path remains timed. Target period is 0.92 ns, clock uncertainty60ps, original fanout32 and transition320ps limits preserved.

## Corrected placement grids

The historical placement at Y59.940um offsets all437VM and819MP1 signal M4 pin centers12nm from horizontal track centers. An initial track-only origin(60,60)um caused27tapcells and2ordinarycells to fail placement legality. Failed ODB confirms macro and tap X positions6nm off54nm site grid; the ordinarycells were1nm off, consistent with float serialization.

The joint-grid hook selects(60.048,60.480)um, legal on row/site and signal-track grids, and formats placement coordinates to1nm. It preserves RTL/latency and legality checks. `physical/abi3/v41_macro_local_place_tracks.tcl` is the exact hook used for the recorded joint-grid attempt.

## Both results: route completed, power connectivity failed

Both VM and ME detailed routing completed with ODBs, zero DRC and zero antenna violations. Final report failed PSM-0069 VDD connectivity, so there is no final accepted extracted timing or closure result. Inspection of6_1_fill.odb found fixed wr_data_q[0] and other FFs with orientationR0 on MX rows. The old hook failed to orient fixed FFs with their power rows. Both sides of the SRAM report disconnected cell power shapes.

Candidate `v41_macro_local_place_tracks_pg.tcl` adds only explicit per-row orientation to fixed FF placement. It fails if no row exists; it does not waive PG checks or change timing constraints. Three static Tcl regression tests and behavioral one-word/registered-latency SRAM cut test pass. This candidate has no physical verdict until rerun.

The remote image is pinned to sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29. Historical negative records did not preserve image ID; differences against them are not a controlled single-variable comparison. The source-pinned driver is from the original isolated branch, not current main. Input hashes and original failure record are preserved under results/physical_abi3/asap7/chip/v41_macro_local_joint_grid.

Before composition: both microblocks require routed setup/hold, zero DRC/antenna, power connectivity, clock/data fanout/slew/cap checks, and actual local wire-delay evidence. A positive placement slack does not satisfy these gates.

The approved PG-orientation rerun adds POST_DETAIL_PLACE check_power_grid on VDD/VSS. This early check reproduces PSM-0069 on the failed prior placement ODB, so broken power connectivity fails before another detailed route. The check is additional validation; no original constraint is relaxed.

## VM PG-corrected final result

The follow-up completes with physical VDD/VSS connectivity, zero DRC/antenna/slew/cap violations. Extracted setup is +259.405ps, but hold is -6.831ps across18 violating endpoints, and7 clock outputs retain fanout33 against limit32. Verdict remains **NOT_MET**; no achieved operating frequency is claimed. All checks retain0.92ns period and60ps uncertainty. Remaining fixes must repair actual hold and clock-tree fanout, rather than weakening constraints. Its full die outline remains44,800um2 with5,170.65um2 macro and505.43um2 standard-cell area; those figures are this microblock only.

## MP1 PG-corrected final result and next bounded repair

The MP1 cut completes routing and physical VDD/VSS connectivity. Extracted setup is +402.886ps, hold is -3.357ps across7 endpoints. DRC, antenna, max slew, capacitance and fanout violations are all zero. It remains **NOT_MET** solely on hold. Together the cuts show that pin escape and row/rail orientation have workable implementations, but neither is timing-qualified yet.

The next proposed implementation repair is a positive20ps hold-repair target, preserving the actual60ps uncertainty and0.92ns period. VM additionally needs clock leaf clustering below the existing32-fanout rule (candidate16 sinks per cluster). Those changes require architecture approval and measured clock-buffer/area/hold impact; no frequency claim or larger neighborhood follows from the present tests. The VM worst short path is rd_row_q[2] to SRAM address:257.06ps arrival versus263.89ps requirement, including the unchanged60ps clock reserve. No extra architectural cycle is justified by this small minimum-delay miss alone.
