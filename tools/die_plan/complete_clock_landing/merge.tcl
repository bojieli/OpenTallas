source /out/component_ops.tcl
read_db $::env(IN)
set block [ord::get_db_block]; set tech [ord::get_db_tech]
set f [open /out/landing_plan.tsv r];set text [read $f];close $f
set plans {}
foreach line [split $text \n] {
 if {$line eq ""} continue
 lassign [split $line \t] name px py xe stub
 dict set plans $name [list $px $py $xe $stub]
}
if {[dict size $plans]!=$::env(OT_LANDING_COUNT) || [dict size $::component_ops]!=$::env(OT_LANDING_COUNT)} {error "declared selected count mismatch"}
set receivers {}
# Preflight actual source driver identity before changing ANY original wire.
foreach name [dict keys $::component_ops] {
 set net [$block findNet $name]
 if {$net eq "NULL" || [$net getSigType] ne "CLOCK" || [llength [$net getITerms]]!=2 || [llength [$net getBTerms]]} {error "native 2-terminal CLOCK mismatch $name"}
 lassign [dict get $::component_drivers $name] dn master xy orient mt
 set inst [$block findInst $dn]
 if {$inst eq "NULL" || [[$inst getMaster] getName] ne $master || [$inst getLocation] ne $xy || [$inst getOrient] ne $orient} {error "actual driver moved/resized: $name"}
 set driver [$inst findITerm $mt]
 if {[$driver getNet] ne $net} {error "actual driver net mismatch"}
 set receiver "NULL"
 foreach term [$net getITerms] {if {$term ne $driver} {set receiver $term}}
 if {$receiver eq "NULL" || [[[$receiver getInst] getMaster] getName] ne $::env(OT_LANDING_MASTER) || [[$receiver getMTerm] getName] ne "clk"} {error "native macro receiver mismatch"}
 lassign [dict get $plans $name] px py xe stub
 set pb [$receiver getBBox]
 if {$px<[$pb xMin] || $px>[$pb xMax] || $py<[$pb yMin] || $py>[$pb yMax]} {error "landing outside actual PORT"}
 dict set receivers $name $receiver
}
foreach name [dict keys $::component_ops] {
 set net [$block findNet $name];set nw [odb::dbWire_create $block];set enc [odb::dbWireEncoder];$enc begin $nw
 foreach op [dict get $::component_ops $name] {
  switch [lindex $op 0] {
   PATH {$enc newPath [$tech findLayer [lindex $op 1]] FIXED}
   TVIA {$enc addTechVia [$tech findVia [lindex $op 1]]}
   ITERM {$enc addITerm [[$block findInst [lindex $op 1]] findITerm [lindex $op 2]]}
   addPoint - addRect {$enc {*}$op}
   default {error "unexpected semantic native wire op"}
  }
 }
 lassign [dict get $plans $name] px py xe stub
 $enc newPath [$tech findLayer M5] FIXED
 $enc addPoint $px $py
 $enc addITerm [dict get $receivers $name]
 $enc addTechVia [$tech findVia VIA56]
 $enc addPoint $xe $py
 $enc addTechVia [$tech findVia VIA56]
 $enc addPoint $xe $stub
 $enc end;$enc -delete
 set old [$net getWire]; if {$old ne "NULL"} {odb::dbWire_destroy $old}
 $nw attach $net
 puts "COMPLETE_CLOCK $name prefix_plus_native_landing no_fixture_ports"
}
write_db /out/complete_clock_merged.odb
