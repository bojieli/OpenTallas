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

# H0 captures bank hits beside the row/valid ingress. Count actual mapped DFFs,
# including Yosys's hit wire alias; no combinational or hold-buffer aliases.
set hcount 0
set hnames {}
foreach i [$b getInsts] {
    set n [$i getName]
    if {![string match {u.h0*} $n] && ![string match {u.hit*} $n]} { continue }
    if {![string match DFF* [[$i getMaster] getName]]} { continue }
    $i setLocation [expr {round((12.0+0.72*$hcount)*$dbu)}] [expr {round(70.2*$dbu)}]
    $i setPlacementStatus FIRM
    lappend hnames $n
    incr hcount
}
if {$hcount != 28} { error "BGL_MC_H0 expected28actualhitFFs found$hcount" }
puts "BGL_MC_H0 placed $hcount input hit flops near N row/valid pins"
set fh [open $::env(RESULTS_DIR)/ot_out_flop_at_pins.txt a]
foreach n $hnames {puts $fh $n}
close $fh

# Parallel pair-count FFs sit beside H0; both are captured from the SAME input edge.
set pcount 0; set pnames {}
foreach i [$b getInsts] {
    if {![string match {u.hpair_q*} [$i getName]]} { continue }
    if {![string match DFF* [[$i getMaster] getName]]} { continue }
    $i setLocation [expr {round((12.0+0.72*$pcount)*$dbu)}] [expr {round(68.04*$dbu)}]
    $i setPlacementStatus FIRM
    lappend pnames [$i getName]; incr pcount
}
if {$pcount != 28} {error "BGL_MC_PAIR expected28pair-countFFs found$pcount"}
set fh [open $::env(RESULTS_DIR)/ot_out_flop_at_pins.txt a]
foreach n $pnames {puts $fh $n}; close $fh
puts "BGL_MC_PAIR placed $pcount pair count flops beside H0"
