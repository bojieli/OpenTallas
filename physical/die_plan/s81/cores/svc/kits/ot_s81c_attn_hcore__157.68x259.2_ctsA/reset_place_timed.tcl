# Private timed reset wavefront: delivered synchronous input -> entry -> central relay.
# Use actual row/site lattice; no guessed cell names or silently missing anchors.
set b [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ca [$b getCoreArea]
set rows [$b getRows]
set site [[lindex $rows 0] getSite]
set sw [$site getWidth];set rh [$site getHeight]
set fh [open $::env(RESULTS_DIR)/ot_reset_timed.txt w]
foreach {netname ux uy} {rst_e_q 81.852 8.0 rst_r_q 81.852 129.6} {
 set net [$b findNet $netname]
 if {$net eq "NULL" || $net eq ""} {error "TIMED_RESET missing $netname"}
 set trail {}
 set nn $net
 for {set depth 0} {$depth<5} {incr depth} {
  set drivers {}
  foreach it [$nn getITerms] {if {[[$it getMTerm] getIoType] eq "OUTPUT"} {lappend drivers [$it getInst]}}
  if {[llength $drivers]!=1} {error "TIMED_RESET nonunique $netname driver"}
  set inst [lindex $drivers 0]
  set mn [[$inst getMaster] getName]
  if {[string match *DFF* $mn]} {break}
  if {![regexp {^(INV|BUF|HB)} $mn]} {error "TIMED_RESET unexpected $netname driver $mn"}
  lappend trail $inst
  set inputs {}
  foreach it [$inst getITerms] {
   if {[$it getSigType] eq "SIGNAL" && [[$it getMTerm] getIoType] eq "INPUT"} {lappend inputs [$it getNet]}
  }
  if {[llength $inputs]!=1} {error "TIMED_RESET ambiguous unary $mn"}
  set nn [lindex $inputs 0]
 }
 if {![string match *DFF* [[$inst getMaster] getName]]} {error "TIMED_RESET unary-depth limit"}
 set x [expr {[$ca xMin]+round(($ux*$dbu-[$ca xMin])/$sw)*$sw}]
 set y [expr {[$ca yMin]+round(($uy*$dbu-[$ca yMin])/$rh)*$rh}]
 set orient ""
 foreach row $rows {if {[lindex [$row getOrigin] 1]==$y} {set orient [$row getOrient];break}}
 if {$orient eq ""} {error "TIMED_RESET row absent y=$y"}
 $inst setOrient $orient
 $inst setLocation $x $y
 $inst setPlacementStatus FIRM
 puts $fh [$inst getName]
 # ASAP7 DFFHQN produces QN followed by a restoring INV; co-locate the actual unary tail.
 set bx [expr {$x+[[$inst getMaster] getWidth]+2*$sw}]
 foreach tail [lreverse $trail] {
  $tail setOrient $orient
  $tail setLocation $bx $y
  $tail setPlacementStatus FIRM
  puts $fh [$tail getName]
  puts "OT_TIMED_RESET unary [$tail getName] [expr {$bx/double($dbu)}] [expr {$y/double($dbu)}]"
  set bx [expr {$bx+[[$tail getMaster] getWidth]+2*$sw}]
 }
 puts "OT_TIMED_RESET $netname [$inst getName] [expr {$x/double($dbu)}] [expr {$y/double($dbu)}]"
}
close $fh
