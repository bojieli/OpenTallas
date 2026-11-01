# Reviewed existing-cell class correction; no new clocks/cells/stages/ports.
source /work/postcts_gate.tcl
set blk [ord::get_db_block];set u [$blk getDbUnitsPerMicron]
set oldloc {};set oldstatus {}
foreach i [$blk getInsts] {dict set oldloc [$i getName] [$i getLocation];dict set oldstatus [$i getName] [$i getPlacementStatus]}
set movers {clkbuf_6_41_0_clk_regs clkbuf_6_40_0_clk_regs clkbuf_6_37_0_clk_regs clkload30 clkbuf_6_35_0_clk_regs clkload28 clkbuf_6_34_0_clk_regs clkload27 clkbuf_6_33_0_clk_regs clkbuf_6_15_0_clk_regs clkload12 clkbuf_6_14_0_clk_regs clkload11 clkbuf_6_13_0_clk_regs clkload10 clkbuf_6_12_0_clk_regs clkload9 clkbuf_6_11_0_clk_regs clkload8 clkbuf_6_10_0_clk_regs clkbuf_6_9_0_clk_regs clkload7 clkbuf_6_8_0_clk_regs}
foreach i [$blk getInsts] {if {[$i getName] ni $movers && [$i getPlacementStatus] eq "PLACED"} {$i setPlacementStatus FIRM}}
proc cc_xy {i} {set m [$i getMaster];lassign [$i getLocation] x y;return [list [expr {($x+[$m getWidth]/2.0)/$::u}] [expr {($y+[$m getHeight]/2.0)/$::u}]]}
proc cc_place {i x y} {set m [$i getMaster];$i setPlacementStatus PLACED;$i setLocation [expr {round(($x-[$m getWidth]/2.0/$::u)*$::u)}] [expr {round(($y-[$m getHeight]/2.0/$::u)*$::u)}]}
set i [$blk findInst clkbuf_6_41_0_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_6_41_0_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 9 || [llength $ds] != 0} {error "reviewed fanout changed for clkbuf_6_41_0_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_6_41_0_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_6_41_0_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
set i [$blk findInst clkbuf_6_40_0_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_6_40_0_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 9 || [llength $ds] != 0} {error "reviewed fanout changed for clkbuf_6_40_0_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_6_40_0_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_6_40_0_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
set i [$blk findInst clkbuf_6_37_0_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_6_37_0_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 9 || [llength $ds] != 1} {error "reviewed fanout changed for clkbuf_6_37_0_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_6_37_0_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_6_37_0_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
cc_place [$blk findInst clkload30] [expr {$cx+2.160000000}] [expr {$cy+0.540000000}]
set i [$blk findInst clkbuf_6_35_0_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_6_35_0_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 8 || [llength $ds] != 1} {error "reviewed fanout changed for clkbuf_6_35_0_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_6_35_0_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_6_35_0_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
cc_place [$blk findInst clkload28] [expr {$cx+2.160000000}] [expr {$cy+0.540000000}]
set i [$blk findInst clkbuf_6_34_0_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_6_34_0_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 13 || [llength $ds] != 1} {error "reviewed fanout changed for clkbuf_6_34_0_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_6_34_0_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_6_34_0_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
cc_place [$blk findInst clkload27] [expr {$cx+2.160000000}] [expr {$cy+0.540000000}]
set i [$blk findInst clkbuf_6_33_0_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_6_33_0_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 16 || [llength $ds] != 0} {error "reviewed fanout changed for clkbuf_6_33_0_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_6_33_0_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_6_33_0_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
set i [$blk findInst clkbuf_6_15_0_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_6_15_0_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 9 || [llength $ds] != 1} {error "reviewed fanout changed for clkbuf_6_15_0_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_6_15_0_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_6_15_0_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
cc_place [$blk findInst clkload12] [expr {$cx+2.160000000}] [expr {$cy+0.540000000}]
set i [$blk findInst clkbuf_6_14_0_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_6_14_0_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 10 || [llength $ds] != 1} {error "reviewed fanout changed for clkbuf_6_14_0_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_6_14_0_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_6_14_0_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
cc_place [$blk findInst clkload11] [expr {$cx+2.160000000}] [expr {$cy+0.540000000}]
set i [$blk findInst clkbuf_6_13_0_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_6_13_0_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 9 || [llength $ds] != 1} {error "reviewed fanout changed for clkbuf_6_13_0_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_6_13_0_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_6_13_0_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
cc_place [$blk findInst clkload10] [expr {$cx+2.160000000}] [expr {$cy+0.540000000}]
set i [$blk findInst clkbuf_6_12_0_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_6_12_0_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 6 || [llength $ds] != 1} {error "reviewed fanout changed for clkbuf_6_12_0_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_6_12_0_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_6_12_0_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
cc_place [$blk findInst clkload9] [expr {$cx+2.160000000}] [expr {$cy+0.540000000}]
set i [$blk findInst clkbuf_6_11_0_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_6_11_0_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 6 || [llength $ds] != 1} {error "reviewed fanout changed for clkbuf_6_11_0_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_6_11_0_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_6_11_0_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
cc_place [$blk findInst clkload8] [expr {$cx+2.160000000}] [expr {$cy+0.540000000}]
set i [$blk findInst clkbuf_6_10_0_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_6_10_0_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 11 || [llength $ds] != 0} {error "reviewed fanout changed for clkbuf_6_10_0_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_6_10_0_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_6_10_0_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
set i [$blk findInst clkbuf_6_9_0_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_6_9_0_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 10 || [llength $ds] != 1} {error "reviewed fanout changed for clkbuf_6_9_0_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_6_9_0_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_6_9_0_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
cc_place [$blk findInst clkload7] [expr {$cx+2.160000000}] [expr {$cy+0.540000000}]
set i [$blk findInst clkbuf_6_8_0_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_6_8_0_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 11 || [llength $ds] != 0} {error "reviewed fanout changed for clkbuf_6_8_0_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_6_8_0_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_6_8_0_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
detailed_placement
check_placement -verbose
foreach i [$blk getInsts] {set n [$i getName];if {$n ni $movers && [dict get $oldloc $n] ne [$i getLocation]} {error "unapproved existing-cell move $n"}}
foreach i [$blk getInsts] {set n [$i getName];$i setPlacementStatus [dict get $oldstatus $n]}
global_connect
file mkdir $::env(OUTDIR)
write_db $::env(OUTDIR)/4_cts.odb
write_sdc $::env(OUTDIR)/4_cts.sdc
puts "OT_CLOCK_CLASS_LEGAL_DONE: actualLOOK then normalGRT+finalTTFFDRV required"
