read_db $::env(ODB)
set b [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set f [open /work/placed_inst.tsv w]
set ff 0; set pg_bad 0
foreach i [$b getInsts] {
 set m [$i getMaster]; set r [$i getBBox]
 puts $f "[$i getName]\t[$m getName]\t[expr {double([$r xMin])/$dbu}]\t[expr {double([$r yMin])/$dbu}]\t[expr {double([$r xMax])/$dbu}]\t[expr {double([$r yMax])/$dbu}]"
 if {![string match DFF* [$m getName]]} continue
 incr ff
 foreach t [$i getITerms] {
  set st [[$t getMTerm] getSigType]
  if {$st ni {POWER GROUND}} continue
  set n [$t getNet]
  if {$n eq "NULL" || $n eq ""} {incr pg_bad; continue}
  set want [expr {$st eq "POWER" ? "VDD" : "VSS"}]
  if {[$n getName] ne $want} {incr pg_bad}
 }
}
close $f
set f [open /work/placed_pin.tsv w]
foreach p [$b getBTerms] {
 set r [$p getBBox]
 puts $f "[$p getName]\t[$p getIoType]\t[expr {double([$r xMin]+[$r xMax])/(2*$dbu)}]\t[expr {double([$r yMin]+[$r yMax])/(2*$dbu)}]"
}
close $f
set f [open /work/port_flops.tsv w]
set far 0; set missing 0; set got 0; set maxd 0
foreach p [$b getBTerms] {
 set pn [$p getName]
 if {$pn in {clk rst_n} || [$p getSigType] in {POWER GROUND}} continue
 set input [expr {[$p getIoType] eq "INPUT"}]
 set nets [list [$p getNet]]; set seen {}; set ffs {}
 for {set hop 0} {$hop < 10 && [llength $nets]} {incr hop} {
  set next {}
  foreach net $nets {
   if {$net eq "NULL" || [$net getName] in $seen} continue
   lappend seen [$net getName]
   foreach t [$net getITerms] {
    if {$input && ![$t isInputSignal]} continue
    if {!$input && ![$t isOutputSignal]} continue
    set i [$t getInst]; set mn [[$i getMaster] getName]
    if {[string match DFF* $mn]} {
     if {!$input || [[$t getMTerm] getName] eq "D"} {lappend ffs [$i getName]}
    } elseif {[string match BUF* $mn] || [string match INV* $mn]} {
     foreach q [$i getITerms] {
      if {($input && [$q isOutputSignal]) || (!$input && [$q isInputSignal])} {
       if {[[$q getMTerm] getSigType] ni {POWER GROUND CLOCK}} {lappend next [$q getNet]}
      }
     }
    }
   }
  }
  set nets $next
 }
 set ffs [lsort -unique $ffs]
 if {[llength $ffs] != 1} {incr missing; puts $f "$pn\tMISSING\t$ffs"; continue}
 set i [$b findInst [lindex $ffs 0]]; set rr [$i getBBox]; set pp [$p getBBox]
 set dist [expr {(abs(([$rr xMin]+[$rr xMax])-([$pp xMin]+[$pp xMax]))+abs(([$rr yMin]+[$rr yMax])-([$pp yMin]+[$pp yMax])))/(2.0*$dbu)}]
 incr got
 if {$dist > $maxd} {set maxd $dist}
 if {$dist > 20} {incr far}
 puts $f "$pn\t[$i getName]\t$dist"
}
close $f
puts "A0_PORT_GEOM got $got expected 504 missing $missing far_gt20 $far max_um $maxd"
if {$got != 504 || $missing || $far} {error "port-flop geometry audit failed"}
puts "A0_FF_PG ff $ff expected 12030 pg_bad $pg_bad"
if {$ff != 12030 || $pg_bad != 0} {error "FF/PG audit failed"}
exit
