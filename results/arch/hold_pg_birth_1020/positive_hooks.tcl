foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT*TT*.lib*] {read_liberty $f}
foreach f [glob /src/physical/asap7_memory_macros/ot_sram_1rw_128x64_m2_r2c2_p192_mir/*_tt.lib] {read_liberty $f}
read_db /old/routes/gate/work/orfs/results/asap7/opentallas_ot_hgi_coll_fj_n2s1_r128_asap7_ref_gate/base/3_2_place_iop.odb
file mkdir $::env(RESULTS_DIR)
set ::env(OT_FJ_BAND) {2.16,2.16,101.52,41.04}
set ::env(OT_HOLD_MM) {1}
set ::env(OT_INHOLD_DRV) {BUFx4f_ASAP7_75t_R}
set ::env(OT_INHOLD_MASTER) {HB2xp67_ASAP7_75t_R}
set ::env(OT_IOHOLD_IN) {1}
set ::env(OT_IO_HOLD_SKEW) {50}
set ::env(OT_IO_INTER) {none_*}
set ::env(OT_IO_SKEW) {90}
set ::env(OT_IO_SKEW_INTER) {150}
set ::env(OT_KEEP_PIN_REGS) {1}
set ::env(OT_MM_FF_SDC) {/src/physical/ref_tile/hcoll_fj3_r128u/signoff.sdc}
set ::env(OT_OFLOP_ALLOW_NONE) {1}
set ::env(OT_OFLOP_COLS) {4}
set ::env(OT_OFLOP_HOPS) {8}
set ::env(OT_PIN_REGS_CLOCK) {clk}
set ::env(OT_PIN_REGS_RESET_PORTS) {rst_n}
set ::env(OT_PK_ABOVE_ONLY) {1}
set ::env(OT_PK_FRAC) {0.5}
set ::env(OT_REF_GLOB) {*}
set ::env(OT_RST_COPIES_MAX) {32}
set ::env(OT_RST_LAND) {1}
set ::env(OT_RST_LAND_STAGES) {2}
source /src/physical/ref_tile/hcoll_fj3_r128u/pre_gpl.tcl
set b [ord::get_db_block]
set f [open $::env(STATE_FILE) w]
set missing 0;set protected 0
foreach i [$b getInsts] {set pins {};foreach t [$i getITerms] {set n [$t getNet];set nn [expr {$n eq "NULL" || $n eq "" ? "" : [$n getName]}];if {[$t getSigType] in {POWER GROUND}} {if {$nn eq "" && [$i isDoNotTouch]} {incr missing};continue};lappend pins [list [[$t getMTerm] getName] $nn]};if {[$i isDoNotTouch]} {incr protected};puts $f [list [$i getName] [[$i getMaster] getName] [$i getLocation] [$i getOrient] [$i getPlacementStatus] [$i isDoNotTouch] [$i getSourceType] [lsort $pins]]}
close $f
puts "ACTUAL_HOLD_PG_HOOK protected=$protected unbound_protected_pg_iterms=$missing"
