set b [ord::get_db_block]
proc need {ok msg} {if {!$ok} {error $msg}}
source /work/pg_connect.tcl
ot_pg_require_bound l7_lvt_import_before
set original {};set wires {}
foreach i [$b getInsts] {
 dict set original [$i getName] [list [[$i getMaster] getName] [$i getLocation] [$i getOrient] [$i getPlacementStatus] [$i isDoNotTouch]]
 foreach t [$i getITerms] {set n [$t getNet]; lappend wires [list [$i getName] [[$t getMTerm] getName] [expr {$n eq "NULL" ? "NULL" : [$n getName]}]]}
}
set swaps [dict create _249548_ [list AND5x1_ASAP7_75t_R AND5x1_ASAP7_75t_L] _292848_ [list AND4x1_ASAP7_75t_R AND4x1_ASAP7_75t_L] _284962_ [list AND5x1_ASAP7_75t_R AND5x1_ASAP7_75t_L] _259631_ [list AND5x1_ASAP7_75t_R AND5x1_ASAP7_75t_L]]
need [expr {[llength [$b getInsts]] == 272550}] {wrong L7 instance-count baseline}
dict for {nm pair} $swaps {
 set i [$b findInst $nm];need [expr {$i ne "NULL" && [[$i getMaster] getName] eq [lindex $pair 0]}] "wrong source $nm"
 foreach t [$i getITerms] {set n [$t getNet];need [expr {$n eq "NULL" || [$n getSigType] ne "CLOCK"}] "CLOCK target $nm"}
 set m [[ord::get_db] findMaster [lindex $pair 1]];need [expr {$m ne "NULL"}] "missing LVT master $nm"
 need [expr {[$m getWidth] == [[$i getMaster] getWidth] && [$m getHeight] == [[$i getMaster] getHeight]}] "bbox mismatch $nm"
 need [$i swapMaster $m] "swap failed $nm"
}
set after {};set actual {};set changed {}
foreach i [$b getInsts] {
 set nm [$i getName];need [dict exists $original $nm] "new instance $nm"
 set r [dict get $original $nm];set expected [lindex $r 0]
 if {[dict exists $swaps $nm]} {set expected [lindex [dict get $swaps $nm] 1];lappend changed $nm}
 need [expr {[list [[$i getMaster] getName] [$i getLocation] [$i getOrient] [$i getPlacementStatus] [$i isDoNotTouch]] eq [lreplace $r 0 0 $expected]}] "unexpected master/pose/status/DNT delta $nm"
 foreach t [$i getITerms] {set n [$t getNet];lappend after [list $nm [[$t getMTerm] getName] [expr {$n eq "NULL" ? "NULL" : [$n getName]}]]}
 dict set actual $nm 1
}
need [expr {[dict size $original]==[dict size $actual] && [llength $changed]==4 && [lsort $wires] eq [lsort $after]}] {topology/count delta}
source /work/pg_connect.tcl
ot_pg_connect_all l7_lvt
ot_pg_require_bound l7_lvt
check_placement -verbose
set pf [open /work/lvt_placement.tsv w];foreach i [$b getInsts] {puts $pf [list [$i getName] [[$i getMaster] getName] [$i getLocation] [$i getOrient]]};close $pf
write_db /work/LVT_DATA_GEOMETRY_CHECKPOINT.odb

puts L7_LVT_DATA_GEOMETRY_COMPLETE_EXACT_FOUR_MASTERS
