read_db /data/topology.odb
source /data/assigned_pin_exact.tcl
set b [ord::get_db_block];set u [$b getDbUnitsPerMicron]
set die [$b getDieArea]
odb::Rect ot_test_die [$die xMin] [$die yMin] [$die xMax] [expr {int(round(432.0*$u))}]
$b setDieArea ot_test_die
foreach layer [[ord::get_db_tech] getLayers] {
 set grid [$b findTrackGrid $layer]
 if {$grid ne "NULL" && $grid ne ""} {odb::dbTrackGrid_destroy $grid}
}
source /OpenROAD-flow-scripts/flow/platforms/asap7/openRoad/make_tracks.tcl
foreach layer {M2 M3 M4} {
 set grid [$b findTrackGrid [[ord::get_db_tech] findLayer $layer]]
 puts "ACTUAL_GRID layer=$layer unit=$u X=[lrange [$grid getGridX] 0 2] Y=[lrange [$grid getGridY] 0 2]"
}
set f [open /data/safe1_assigned_pins.tcl r];set contents [read $f];close $f
set existing 0;set future 0;set extended 0;set coords [dict create N {} S {} E {} W {}]
foreach line [split $contents "\n"] {
 if {![regexp {^ot_assigned_pin_exact \{([^\}]+)\} (M[1-6]) ([NSEW]) ([0-9.]+)$} $line -> name layer face value]} continue
 set bt [$b findBTerm $name]
 if {$bt eq "NULL" || $bt eq ""} {
  if {[string first {ctx_x[} $name]!=0 && $name ne "mu_fault" && $name ne "init_u0"} {error "unexpected absentport$name"}
  set grid [$b findTrackGrid [[ord::get_db_tech] findLayer $layer]]
  set tracks [expr {$face in {N S}?[$grid getGridX]:[$grid getGridY]}]
  if {[lsearch -exact $tracks [expr {int(round($value*$u))}]]<0} {error "futureport$name offactualgrid"}
  incr future
 } else {
  set grid [$b findTrackGrid [[ord::get_db_tech] findLayer $layer]]
  set tracks [expr {$face in {N S}?[$grid getGridX]:[$grid getGridY]}]
  set target [expr {int(round($value*$u))}]
  if {[lsearch -exact $tracks $target]<0} {
   error "actualfreshgridgrantinvalid$name layer=$layer target=$target"
  } else {foreach bp [$bt getBPins] {odb::dbBPin_destroy $bp};eval $line;incr existing}
 }
 dict lappend coords $face $value
}
foreach {face values} $coords {
 set values [lsort -real $values];set min Inf
 foreach x [lrange $values 0 end-1] y [lrange $values 1 end] {set d [expr {$y-$x}];if {$d<$min} {set min $d}}
 if {[llength $values]>1 && $min<0.192-1e-6} {error "pitchbelow0.192on$face:$min"}
 puts "SAFE1_PIN_GRANTS face=$face count=[llength $values] minimum_pitch_um=$min"
}
if {$existing!=2861 || $future!=131 || $extended!=0} {error "portcoverageunexpected$existing/$future"}
puts "SAFE1_PIN_GRANTS PASS actual_existing_ports=$existing new_ABI_grid_only=$future unverified_extended_grants=$extended no_functional_netlist_claim=1"
