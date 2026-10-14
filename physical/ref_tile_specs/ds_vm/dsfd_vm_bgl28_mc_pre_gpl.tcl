# Retain recipe2 pin hold cells and all registered data pins.
source /src/physical/dsrom_window_source/leaf_iohold.tcl
source /src/physical/qwen_die_masters/io_flop_at_pins.tcl
# RAW ret root outliers are the two W-face reset synchronizers, ~100ps late.
# Put them beside their actual S-face return consumers, under the SRAM halo.
set b [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set moved {}
set j 0
foreach i [$b getInsts] {
    if {![string match {u.rst_ret_s*} [$i getName]]} { continue }
    # Recipe2 hold buffers inherit the flop's base name; move only real DFFs.
    if {![string match DFF* [[$i getMaster] getName]]} { continue }
    $i setLocation [expr {round((288.0+1.08*$j)*$dbu)}] [expr {round(20.52*$dbu)}]
    $i setPlacementStatus FIRM
    lappend moved [$i getName]
    puts "BGL_MC_RESET_CLUSTER [$i getName] at [expr {288.0+1.08*$j}] 20.52"
    incr j
}
if {$j != 2} { error "BGL_MC_RESET_CLUSTER expected2actualresetFFs found$j" }
# The standard PRE_DETAIL_PLACE release will legalize these with the pin flops.
set fh [open $::env(RESULTS_DIR)/ot_out_flop_at_pins.txt a]
foreach n $moved { puts $fh $n }
close $fh
