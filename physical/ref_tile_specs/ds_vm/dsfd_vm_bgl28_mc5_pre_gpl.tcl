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
    if {![string match {u_leaf.u.rst_ret_s*} [$i getName]]} { continue }
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
    if {![string match {u_leaf.u.h0*} $n] && ![string match {u_leaf.u.hit*} $n]} { continue }
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
    if {![string match {u_leaf.u.hpair_q*} [$i getName]]} { continue }
    if {![string match DFF* [[$i getMaster] getName]]} { continue }
    $i setLocation [expr {round((12.0+0.72*$pcount)*$dbu)}] [expr {round(68.04*$dbu)}]
    $i setPlacementStatus FIRM
    lappend pnames [$i getName]; incr pcount
}
if {$pcount != 28} {error "BGL_MC_PAIR expected28pair-countFFs found$pcount"}
set fh [open $::env(RESULTS_DIR)/ot_out_flop_at_pins.txt a]
foreach n $pnames {puts $fh $n}; close $fh
puts "BGL_MC_PAIR placed $pcount pair count flops beside H0"

# Output-only 14-port domains: compact reset conditioners beside their S consumers.
set out_rst_n 0
foreach i [$b getInsts] {
 if {![string match {u_leaf.g_output_reset*rst_out_b*} [$i getName]]} {continue}
 if {![string match DFF* [[$i getMaster] getName]]} {continue}
 # Exact reset clocks are subsequently validated from the actual mapped root census.
 $i setLocation [expr {round((100.0+100.0*($out_rst_n/2)+0.72*($out_rst_n%2))*$dbu)}] [expr {round(18.36*$dbu)}]
 $i setPlacementStatus FIRM
 set fh [open $::env(RESULTS_DIR)/ot_out_flop_at_pins.txt a];puts $fh [$i getName];close $fh
 incr out_rst_n
}
if {$out_rst_n != 4} {error "MC5 expected4actual output reset FFs found$out_rst_n"}
# Actual output hold chains retain the original lead4f and one final24.
set final24 [[ord::get_db] findMaster BUFx24_ASAP7_75t_R]
set nfinal 0;set nhb2 0;set nhb3 0
foreach i [$b getInsts] {
 if {![string match ot_ohdrv_*_2 [$i getName]]} {continue}
 set net [[$i findITerm Y] getNet]
 if {[llength [$net getBTerms]] != 1} {error "MC5 final not directly on one port"}
 set port [[lindex [$net getBTerms] 0] getName]
 set hnet [[$i findITerm A] getNet];set hi ""
 foreach t [$hnet getITerms] {if {[$t isOutputSignal]} {set hi [$t getInst]}}
 if {$hi eq "" || ![string match HB* [[$hi getMaster] getName]]} {error "MC5 missing real hold stage"}
 set hmaster HB2xp67_ASAP7_75t_R
 if {[string match o_* $port]} {set hmaster HB3xp67_ASAP7_75t_R;incr nhb3} else {incr nhb2}
 $hi setDoNotTouch 0
 if {![$hi swapMaster [[ord::get_db] findMaster $hmaster]]} {error "MC5 hold master swap failed"}
 $hi setDoNotTouch 1
 if {![$i swapMaster $final24]} {error "MC5 final24 swap failed"}
 $net setDoNotTouch 1
 incr nfinal
}
set_dont_touch [get_cells ot_ohdrv_*_2]
if {$nfinal != 5441 || $nhb2 != 4144 || $nhb3 != 1297} {error "MC5 actual hold census final$nfinal f$nhb2 o$nhb3"}
puts "MC5_OUTPUT_DOMAINS final24=$nfinal forwardHB2=$nhb2 returnHB3=$nhb3 resetFF=$out_rst_n"
