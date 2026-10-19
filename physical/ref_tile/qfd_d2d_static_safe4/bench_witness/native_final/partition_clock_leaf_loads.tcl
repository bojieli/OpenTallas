# Equal-level real clock-branch replication. New drivers retain the exact source
# master, parent input net and polarity. Each copy drives actual clock loads.
# No delay cells, dummy loads, clock exceptions or extra FF/clock-buffer levels.
namespace eval ot_clock_part {variable serial 0;variable records {};variable limit 20}
proc ot_clock_part::connect {term net} {
 set i [$term getInst];set it [$i isDoNotTouch];set old [$term getNet]
 set ot 0;if {$old ne "NULL" && $old ne ""} {set ot [$old isDoNotTouch]}
 set nt [$net isDoNotTouch]
 if {$it} {$i setDoNotTouch false};if {$ot} {$old setDoNotTouch false};if {$nt} {$net setDoNotTouch false}
 try {if {$old ne "NULL" && $old ne ""} {$term disconnect};$term connect $net} finally {
  if {$it} {$i setDoNotTouch true};if {$ot} {$old setDoNotTouch true};if {$nt} {$net setDoNotTouch true}
 }
}
set block [ord::get_db_block];set units [$block getDbUnitsPerMicron]
# Build actual clock ancestry from every sequential clock pin, including hard macros.
set clock_nets {};set queue {}
foreach p [all_registers -clock_pins] {
 set i [sta::sta_to_db_inst [lindex [get_cells -of_objects $p] 0]]
 set t [$i findITerm [file tail [get_full_name $p]]]
 if {$t eq "NULL"} {error "CLOCK_PART missingactualclockpin[get_full_name $p]"}
 lappend queue [$t getNet]
}
while {[llength $queue]} {
 set net [lindex $queue end];set queue [lrange $queue 0 end-1]
 if {$net eq "NULL" || [dict exists $clock_nets $net]} continue
 dict set clock_nets $net 1
 foreach d [$net getITerms] {
  if {![$d isOutputSignal]} continue
  set i [$d getInst];set mn [[$i getMaster] getName]
  if {![string match BUF* $mn] && ![string match *INV* $mn]} {error "CLOCK_PART unsupported clock source[$i getName]:$mn"}
  foreach t [$i getITerms] {if {[$t isInputSignal]} {lappend queue [$t getNet]}}
 }
}
set changed 1
while {$changed} {
 set changed 0
 foreach net [dict keys $clock_nets] {
  set loads {};set driver {}
  foreach t [$net getITerms] {if {[$t isInputSignal]} {lappend loads $t};if {[$t isOutputSignal]} {lappend driver $t}}
  if {[llength $loads]<=$ot_clock_part::limit} continue
  if {[llength $driver]!=1} {error "CLOCK_PART primary/multidriver overloaded[$net getName]"}
  set driver [lindex $driver 0];set original [$driver getInst];set master [$original getMaster]
  set input {};foreach t [$original getITerms] {if {[$t isInputSignal]} {lappend input $t}}
  if {[llength $input]!=1} {error "CLOCK_PART unsupported buffer ABI"}
  set parent [[lindex $input 0] getNet]
  # Deterministic physical ownership grouping, independent of any CTS instance name.
  set ordered {};foreach t $loads {set bb [[$t getInst] getBBox];lappend ordered [list [expr {[$bb xMin]+1000*[$bb yMin]}] $t]}
  set loads {};foreach pair [lsort -integer -index 0 $ordered] {lappend loads [lindex $pair 1]}
  for {set offset $ot_clock_part::limit} {$offset<[llength $loads]} {incr offset $ot_clock_part::limit} {
   incr ot_clock_part::serial
   if {$ot_clock_part::serial>2000} {error "CLOCK_PART bound2000 exceeded"}
   set name [format ot_owned_clock_leaf_%05d $ot_clock_part::serial]
   set copy [odb::dbInst_create $block $master $name]
   set next [odb::dbNet_create $block ${name}_q];$next setSigType CLOCK
   foreach t [$original getITerms] {
    set c [$copy findITerm [[$t getMTerm] getName]]
    if {[$t isInputSignal]} {ot_clock_part::connect $c $parent}
    if {[$t isOutputSignal]} {ot_clock_part::connect $c $next}
    if {[$t getSigType] in {POWER GROUND} && [$t getNet] ne "NULL"} {ot_clock_part::connect $c [$t getNet]}
   }
   set chunk [lrange $loads $offset [expr {$offset+$ot_clock_part::limit-1}]]
   set x 0;set y 0
   foreach t $chunk {set bb [[$t getInst] getBBox];set x [expr {$x+([$bb xMin]+[$bb xMax])/2.0}];set y [expr {$y+([$bb yMin]+[$bb yMax])/2.0}];ot_clock_part::connect $t $next}
   $copy setOrient [$original getOrient]
   $copy setLocation [expr {int(round($x/[llength $chunk]))}] [expr {int(round($y/[llength $chunk]))}]
   $copy setPlacementStatus PLACED
   dict set clock_nets $next 1
   lappend ot_clock_part::records [list $name [$original getName] [$master getName] [$parent getName] [llength $chunk]]
  }
  set changed 1
 }
}
puts "CLOCK_PART PASS copied_real_drivers=$ot_clock_part::serial maximum_direct_clock_load=$ot_clock_part::limit same_parent_master_polarity_level=1"
if {[info exists ::ot_clock_part_manifest]} {set f [open $::ot_clock_part_manifest w];puts $f [list set ::ot_clock_part_records $ot_clock_part::records];close $f}
