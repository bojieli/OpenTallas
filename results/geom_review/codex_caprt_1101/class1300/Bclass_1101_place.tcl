# Reviewed existing-cell class correction; no new clocks/cells/stages/ports.
source /work/postcts_gate.tcl
set blk [ord::get_db_block];set u [$blk getDbUnitsPerMicron]
set oldloc {};set oldstatus {}
foreach i [$blk getInsts] {dict set oldloc [$i getName] [$i getLocation];dict set oldstatus [$i getName] [$i getPlacementStatus]}
set movers {clkbuf_7_81__f_clk_regs clkload56 clkbuf_7_80__f_clk_regs clkbuf_7_76__f_clk_regs clkload53 clkbuf_7_75__f_clk_regs clkload52 clkbuf_7_74__f_clk_regs clkload51 clkbuf_7_73__f_clk_regs clkload50 clkbuf_7_69__f_clk_regs clkbuf_7_68__f_clk_regs clkload47 clkbuf_7_66__f_clk_regs clkbuf_7_65__f_clk_regs clkload45 clkbuf_7_31__f_clk_regs clkbuf_7_30__f_clk_regs clkload20 clkbuf_7_29__f_clk_regs clkload19 clkbuf_7_28__f_clk_regs clkbuf_7_27__f_clk_regs clkload18 clkbuf_7_26__f_clk_regs clkbuf_7_25__f_clk_regs clkload17 clkbuf_7_24__f_clk_regs clkload16 clkbuf_7_23__f_clk_regs clkload15 clkbuf_7_22__f_clk_regs clkload14 clkbuf_7_21__f_clk_regs clkload13 clkbuf_7_20__f_clk_regs clkbuf_7_19__f_clk_regs clkload12 clkbuf_7_18__f_clk_regs clkbuf_7_17__f_clk_regs clkload11 clkbuf_7_16__f_clk_regs clkload10}
foreach i [$blk getInsts] {if {[$i getName] ni $movers && [$i getPlacementStatus] eq "PLACED"} {$i setPlacementStatus FIRM}}
proc cc_xy {i} {set m [$i getMaster];lassign [$i getLocation] x y;return [list [expr {($x+[$m getWidth]/2.0)/$::u}] [expr {($y+[$m getHeight]/2.0)/$::u}]]}
proc cc_place {i x y} {set m [$i getMaster];$i setPlacementStatus PLACED;$i setLocation [expr {round(($x-[$m getWidth]/2.0/$::u)*$::u)}] [expr {round(($y-[$m getHeight]/2.0/$::u)*$::u)}]}
set i [$blk findInst clkbuf_7_81__f_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_7_81__f_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 9 || [llength $ds] != 1} {error "reviewed fanout changed for clkbuf_7_81__f_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_7_81__f_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_7_81__f_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
cc_place [$blk findInst clkload56] [expr {$cx+2.160000000}] [expr {$cy+0.540000000}]
set i [$blk findInst clkbuf_7_80__f_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_7_80__f_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 12 || [llength $ds] != 0} {error "reviewed fanout changed for clkbuf_7_80__f_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_7_80__f_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_7_80__f_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
set i [$blk findInst clkbuf_7_76__f_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_7_76__f_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 7 || [llength $ds] != 1} {error "reviewed fanout changed for clkbuf_7_76__f_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_7_76__f_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_7_76__f_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
cc_place [$blk findInst clkload53] [expr {$cx+2.160000000}] [expr {$cy+0.540000000}]
set i [$blk findInst clkbuf_7_75__f_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_7_75__f_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 8 || [llength $ds] != 1} {error "reviewed fanout changed for clkbuf_7_75__f_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_7_75__f_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_7_75__f_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
cc_place [$blk findInst clkload52] [expr {$cx+2.160000000}] [expr {$cy+0.540000000}]
set i [$blk findInst clkbuf_7_74__f_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_7_74__f_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 10 || [llength $ds] != 1} {error "reviewed fanout changed for clkbuf_7_74__f_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_7_74__f_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_7_74__f_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
cc_place [$blk findInst clkload51] [expr {$cx+2.160000000}] [expr {$cy+0.540000000}]
set i [$blk findInst clkbuf_7_73__f_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_7_73__f_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 10 || [llength $ds] != 1} {error "reviewed fanout changed for clkbuf_7_73__f_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_7_73__f_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_7_73__f_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
cc_place [$blk findInst clkload50] [expr {$cx+2.160000000}] [expr {$cy+0.540000000}]
set i [$blk findInst clkbuf_7_69__f_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_7_69__f_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 13 || [llength $ds] != 0} {error "reviewed fanout changed for clkbuf_7_69__f_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_7_69__f_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_7_69__f_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
set i [$blk findInst clkbuf_7_68__f_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_7_68__f_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 12 || [llength $ds] != 1} {error "reviewed fanout changed for clkbuf_7_68__f_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_7_68__f_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_7_68__f_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
cc_place [$blk findInst clkload47] [expr {$cx+2.160000000}] [expr {$cy+0.540000000}]
set i [$blk findInst clkbuf_7_66__f_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_7_66__f_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 17 || [llength $ds] != 0} {error "reviewed fanout changed for clkbuf_7_66__f_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_7_66__f_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_7_66__f_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
set i [$blk findInst clkbuf_7_65__f_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_7_65__f_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 14 || [llength $ds] != 1} {error "reviewed fanout changed for clkbuf_7_65__f_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_7_65__f_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_7_65__f_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
cc_place [$blk findInst clkload45] [expr {$cx+2.160000000}] [expr {$cy+0.540000000}]
set i [$blk findInst clkbuf_7_31__f_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_7_31__f_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 10 || [llength $ds] != 0} {error "reviewed fanout changed for clkbuf_7_31__f_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_7_31__f_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_7_31__f_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
set i [$blk findInst clkbuf_7_30__f_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_7_30__f_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 9 || [llength $ds] != 1} {error "reviewed fanout changed for clkbuf_7_30__f_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_7_30__f_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_7_30__f_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
cc_place [$blk findInst clkload20] [expr {$cx+2.160000000}] [expr {$cy+0.540000000}]
set i [$blk findInst clkbuf_7_29__f_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_7_29__f_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 8 || [llength $ds] != 1} {error "reviewed fanout changed for clkbuf_7_29__f_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_7_29__f_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_7_29__f_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
cc_place [$blk findInst clkload19] [expr {$cx+2.160000000}] [expr {$cy+0.540000000}]
set i [$blk findInst clkbuf_7_28__f_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_7_28__f_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 10 || [llength $ds] != 0} {error "reviewed fanout changed for clkbuf_7_28__f_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_7_28__f_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_7_28__f_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
set i [$blk findInst clkbuf_7_27__f_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_7_27__f_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 6 || [llength $ds] != 1} {error "reviewed fanout changed for clkbuf_7_27__f_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_7_27__f_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_7_27__f_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
cc_place [$blk findInst clkload18] [expr {$cx+2.160000000}] [expr {$cy+0.540000000}]
set i [$blk findInst clkbuf_7_26__f_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_7_26__f_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 8 || [llength $ds] != 0} {error "reviewed fanout changed for clkbuf_7_26__f_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_7_26__f_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_7_26__f_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
set i [$blk findInst clkbuf_7_25__f_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_7_25__f_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 6 || [llength $ds] != 1} {error "reviewed fanout changed for clkbuf_7_25__f_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_7_25__f_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_7_25__f_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
cc_place [$blk findInst clkload17] [expr {$cx+2.160000000}] [expr {$cy+0.540000000}]
set i [$blk findInst clkbuf_7_24__f_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_7_24__f_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 6 || [llength $ds] != 1} {error "reviewed fanout changed for clkbuf_7_24__f_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_7_24__f_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_7_24__f_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
cc_place [$blk findInst clkload16] [expr {$cx+2.160000000}] [expr {$cy+0.540000000}]
set i [$blk findInst clkbuf_7_23__f_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_7_23__f_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 9 || [llength $ds] != 1} {error "reviewed fanout changed for clkbuf_7_23__f_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_7_23__f_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_7_23__f_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
cc_place [$blk findInst clkload15] [expr {$cx+2.160000000}] [expr {$cy+0.540000000}]
set i [$blk findInst clkbuf_7_22__f_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_7_22__f_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 8 || [llength $ds] != 1} {error "reviewed fanout changed for clkbuf_7_22__f_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_7_22__f_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_7_22__f_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
cc_place [$blk findInst clkload14] [expr {$cx+2.160000000}] [expr {$cy+0.540000000}]
set i [$blk findInst clkbuf_7_21__f_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_7_21__f_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 9 || [llength $ds] != 1} {error "reviewed fanout changed for clkbuf_7_21__f_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_7_21__f_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_7_21__f_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
cc_place [$blk findInst clkload13] [expr {$cx+2.160000000}] [expr {$cy+0.540000000}]
set i [$blk findInst clkbuf_7_20__f_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_7_20__f_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 12 || [llength $ds] != 0} {error "reviewed fanout changed for clkbuf_7_20__f_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_7_20__f_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_7_20__f_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
set i [$blk findInst clkbuf_7_19__f_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_7_19__f_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 10 || [llength $ds] != 1} {error "reviewed fanout changed for clkbuf_7_19__f_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_7_19__f_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_7_19__f_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
cc_place [$blk findInst clkload12] [expr {$cx+2.160000000}] [expr {$cy+0.540000000}]
set i [$blk findInst clkbuf_7_18__f_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_7_18__f_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 11 || [llength $ds] != 0} {error "reviewed fanout changed for clkbuf_7_18__f_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_7_18__f_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_7_18__f_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
set i [$blk findInst clkbuf_7_17__f_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_7_17__f_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 9 || [llength $ds] != 1} {error "reviewed fanout changed for clkbuf_7_17__f_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_7_17__f_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_7_17__f_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
cc_place [$blk findInst clkload11] [expr {$cx+2.160000000}] [expr {$cy+0.540000000}]
set i [$blk findInst clkbuf_7_16__f_clk_regs]
if {$i eq "NULL"} {error "missing reviewed parent clkbuf_7_16__f_clk_regs"}
set net [[$i findITerm Y] getNet]
set ls {};set ds {}
foreach t [$net getITerms] {
 if {[[$t getMTerm] getIoType] ne "INPUT"} continue
 set c [$t getInst]
 if {[string match clkload* [$c getName]]} {lappend ds $c} else {lappend ls $c}
}
if {[llength $ls] != 9 || [llength $ds] != 1} {error "reviewed fanout changed for clkbuf_7_16__f_clk_regs"}
set cx 0;set cy 0
foreach c $ls {lassign [cc_xy $c] x y;if {$y >= 38.88} {error "non-south real load for clkbuf_7_16__f_clk_regs"};set cx [expr {$cx+$x}];set cy [expr {$cy+$y}]}
set cx [expr {$cx/[llength $ls]}];set cy [expr {$cy/[llength $ls]}]
puts "OT_CLOCK_CLASS clkbuf_7_16__f_clk_regs old=[cc_xy $i] real_loads=[llength $ls] target=$cx,$cy"
cc_place $i $cx $cy
cc_place [$blk findInst clkload10] [expr {$cx+2.160000000}] [expr {$cy+0.540000000}]
detailed_placement
check_placement -verbose
foreach i [$blk getInsts] {set n [$i getName];if {$n ni $movers && [dict get $oldloc $n] ne [$i getLocation]} {error "unapproved existing-cell move $n"}}
foreach i [$blk getInsts] {set n [$i getName];$i setPlacementStatus [dict get $oldstatus $n]}
global_connect
file mkdir $::env(OUTDIR)
write_db $::env(OUTDIR)/4_cts.odb
write_sdc $::env(OUTDIR)/4_cts.sdc
puts "OT_CLOCK_CLASS_LEGAL_DONE: actualLOOK then normalGRT+finalTTFFDRV required"
