# Leaf-owned exact pin placement repair/audit. Uses actual ODB routing tracks and
# actual VDD/VSS port shapes; no invented pin capacity or technology pitch.
set nb [ord::get_db_block]
set nt [ord::get_db_tech]
set nu [$nb getDbUnitsPerMicron]
set nd [$nb getDieArea]
set nx0 [$nd xMin];set nx1 [$nd xMax];set ny0 [$nd yMin];set ny1 [$nd yMax]
set npg {}
foreach bt [$nb getBTerms] {
 if {[$bt getSigType] ni {POWER GROUND}} continue
 foreach bp [$bt getBPins] {foreach box [$bp getBoxes] {
  lappend npg [list [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]]
 }}
}
if {[llength $npg]==0} {error "NATIVE_BANK_PIN_AUDIT: no actual VDD/VSS port geometry"}
set nports {}
foreach bt [$nb getBTerms] {
 if {[$bt getSigType] in {POWER GROUND}} continue
 set bp [lindex [$bt getBPins] 0]
 if {$bp eq ""} {error "NATIVE_BANK_PIN_AUDIT: unplaced [$bt getName]"}
 set box [lindex [$bp getBoxes] 0]
 set x [expr {([$box xMin]+[$box xMax])/2.0}]
 set y [expr {([$box yMin]+[$box yMax])/2.0}]
 set choices [list [list [expr {abs($x-$nx0)}] W] [list [expr {abs($x-$nx1)}] E] [list [expr {abs($y-$ny0)}] S] [list [expr {abs($y-$ny1)}] N]]
 set face [lindex [lindex [lsort -real -index 0 $choices] 0] 1]
 set along [expr {$face in {N S}?$x:$y}]
 lappend nports [list $face $along [$bt getName]]
}
# Remove the old uniform signal pin plan as a complete set. Keeping pins
# awaiting relocation lets place_pin move an otherwise legal requested track
# around an old neighbour; a second pass can appear correct by accident.
# Power/ground port geometry remains intact and is the exclusion source.
foreach bt [$nb getBTerms] {
 if {[$bt getSigType] in {POWER GROUND}} continue
 foreach bp [$bt getBPins] {odb::dbBPin_destroy $bp}
}
array set nused {};array set ncount {N 0 S 0 E 0 W 0}
set nmanifest [open [file join $::env(RESULTS_DIR) native_bank_pin_coordinates.tsv] w]
puts $nmanifest "port\tface\tlayer\tcenter_um\tactual_track_dbu\tPG_projection_clear"
foreach item [lsort -real -index 1 $nports] {
 lassign $item face preferred name
 set layer [expr {$face in {N S}?"M5":"M4"}]
 set tl [$nt findLayer $layer]
 set grid [$nb findTrackGrid $tl]
 set tracks [expr {$face in {N S}?[$grid getGridX]:[$grid getGridY]}]
 set extent [expr {$face in {N S}?$nx1:$ny1}]
 set half [expr {[$tl getWidth]/2.0}]
 set margin [expr {round(5.4*$nu)}]
 set space [expr {round(0.072*$nu)}]
 set best -1;set distance 1e30
 # Routing grids are sorted. Binary locate the preferred actual track, then
 # visit nearby real tracks in distance order instead of scanning the die.
 set left 0;set right [expr {[llength $tracks]-1}]
 while {$left<$right} {
  set middle [expr {($left+$right)/2}]
  if {[lindex $tracks $middle]<$preferred} {set left [expr {$middle+1}]} else {set right $middle}
 }
 set candidates {}
 for {set offset -128} {$offset<=128} {incr offset} {
  set index [expr {$left+$offset}]
  if {$index<0||$index>=[llength $tracks]} continue
  set pos [lindex $tracks $index]
  lappend candidates [list [expr {abs($pos-$preferred)}] $pos]
 }
 foreach candidate [lsort -real -index 0 $candidates] {
  set pos [lindex $candidate 1]
  if {$pos<$margin||$pos>$extent-$margin} continue
  set delta [expr {abs($pos-$preferred)}]
  if {$delta>=$distance} continue
  set legal 1
  foreach rect $npg {
   lassign $rect pl ax ay bx by
   if {$pl ne $layer} continue
   # Exclude projected actual PG contact columns, including both power nets,
   # even when the PG metal itself stops just short of the signal edge pin.
   set low [expr {$face in {N S}?$ax:$ay}]
   set high [expr {$face in {N S}?$bx:$by}]
   if {$pos+$half+$space>$low && $pos-$half-$space<$high} {set legal 0;break}
  }
  if {!$legal} continue
  if {[info exists nused($face)]} {foreach occupied $nused($face) {
   if {abs($occupied-$pos)<2*$half+$space} {set legal 0;break}
  }}
  if {$legal} {set best $pos;set distance $delta;break}
 }
 if {$best<0} {error "NATIVE_BANK_PIN_AUDIT: no on-track PG-clear position for $name"}
 lappend nused($face) $best;incr ncount($face)
 set along [expr {double($best)/$nu}]
 set x [expr {$face eq "W"?double($nx0)/$nu:($face eq "E"?double($nx1)/$nu:$along)}]
 set y [expr {$face eq "S"?double($ny0)/$nu:($face eq "N"?double($ny1)/$nu:$along)}]
 # PPL uses the first routing track strictly above its requested edge
 # coordinate. Request one DBU below the chosen actual center, then verify
 # the resulting BTerm rectangle independently; never trust request positions.
 set request_x $x;set request_y $y
 if {$face in {N S}} {set request_x [expr {$x-1.0/$nu}]} else {set request_y [expr {$y-1.0/$nu}]}
 place_pin -pin_name $name -layer $layer -location [list $request_x $request_y] -force_to_die_boundary
 # Read back the placed rectangle, so a future PPL snapping change fails
 # immediately instead of silently accepting requested coordinates.
 set placed_bt [$nb findBTerm $name]
 set placed_box [lindex [[lindex [$placed_bt getBPins] 0] getBoxes] 0]
 set actual_center [expr {$face in {N S}?([$placed_box xMin]+[$placed_box xMax])/2.0:([$placed_box yMin]+[$placed_box yMax])/2.0}]
 if {abs($actual_center-$best)>0.1} {error "NATIVE_BANK_PIN_AUDIT: requested track $best actual $actual_center on $name"}
 puts $nmanifest "$name\t$face\t$layer\t$along\t$best\t1"
}
close $nmanifest
source /src/tools/fp_margin_lint.tcl
ot_fp_lint_dump [file join $::env(RESULTS_DIR) native_bank_actual_pin_pg.json]
orfs_write_db $::env(RESULTS_DIR)/3_2_place_iop.odb
puts "NATIVE_BANK_PIN_AUDIT: actual-track PG-clear placement N=$ncount(N) S=$ncount(S) E=$ncount(E) W=$ncount(W); PG_shapes=[llength $npg]"
