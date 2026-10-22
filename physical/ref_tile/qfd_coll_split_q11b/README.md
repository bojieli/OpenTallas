# qfd_coll_split_q11b -- FALLBACK of q11a (SQC-CTL, 10-21)

q11a (Codex, 0626dcd6b) = q10a geometry + same-edge SRAM/control/read-capture and stage-local reset clock
neighbourhoods (tools/qwen_cluster/q11_pair/clock_pair.tcl, OT_SPINE_TOL_PS=10). q11b = the same hook on the
q10b FALLBACK geometry (239.76x285.12, central 30-um W-E band, macro halo 8.64, W/E pins 1.87/um).

Failure classes addressed (q9b NEEDS_RTL TT -30.07/FF -54.88; q10a route TT -15.55/FF -47.2; q10b TT -28.07/FF -51.65;
CODEX-Q11-CAUSE-2000.md): TT SRAM->out_data setup (SRAM rclk 82 ps later than output capture), FF shared counter ->
SRAM r_addr hold (SRAM clock 85 ps late), reset-release removal to edl (68 ps).

SAFE 8-point: 1 pins PASS (q10b full-face W/E 1.87/um, RTL pin flops) 2 reach PASS (q10b worst pin-flop hop 382 um)
3 fanout PASS (RTL unchanged, native32 max32) 4 depth PASS 288 ps 5 storage PASS (12 SRAM, 3 free columns, >=20 um
channels) 6 floorplan WARN fill 35% (outline kept, enlarge-not-squeeze) 7 clock: local SRAM/control/capture + reset
neighbourhood leaves (the fix), measured at gate 8 reset PASS (control/valid only; stage-local release kept with its sinks).
Benches: lint + coll_gold_unit + coll_gold_prod + 6 mutants (from q10b). Zero cycles, RTL unchanged.
