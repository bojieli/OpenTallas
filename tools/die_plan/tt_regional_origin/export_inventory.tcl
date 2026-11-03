# Read-only TT mapped/preCTS inventory. Caller reads the exact actual ODB first.
# No link/design/placement/clock mutation is performed here.
if {![info exists ::env(OT_TT_NATIVE_OUT)]} {error "OT_TT_NATIVE_OUT is required"}
set tni_b [ord::get_db_block]
set tni_u [expr {double([$tni_b getDbUnitsPerMicron])}]
set tni_o [open $::env(OT_TT_NATIVE_OUT) w]
puts $tni_o "META\t[$tni_b getName]\t$tni_u"
foreach tni_i [$tni_b getInsts] {
 set tni_m [$tni_i getMaster]
 set tni_sig 0
 foreach tni_it [$tni_i getITerms] {
  set tni_mt [$tni_it getMTerm]
  if {[$tni_mt getSigType] in {POWER GROUND}} continue
  incr tni_sig
  set tni_n [$tni_it getNet]
  set tni_net "-"
  if {$tni_n ne "NULL"} {set tni_net [$tni_n getName]}
  puts $tni_o "PIN\t[$tni_i getName]\t[$tni_mt getName]\t[$tni_mt getIoType]\t[$tni_mt getSigType]\t$tni_net"
  # SYNTH-only ODBs have no authorized macro poses. Export no invented geometry.
  if {[$tni_m isBlock] && [$tni_mt getSigType] eq "CLOCK" && ![info exists ::env(OT_TT_SYNTH_ONLY)]} {
   if {[$tni_i getOrient] ne "R0"} {error "TT selected macro clock orientation changed"}
   set tni_ib [$tni_i getBBox];set tni_x0 1e30;set tni_y0 1e30;set tni_x1 -1e30;set tni_y1 -1e30
   foreach tni_mp [$tni_mt getMPins] {foreach tni_g [$tni_mp getGeometry] {
    set tni_x0 [expr {min($tni_x0,[$tni_g xMin])}];set tni_y0 [expr {min($tni_y0,[$tni_g yMin])}]
    set tni_x1 [expr {max($tni_x1,[$tni_g xMax])}];set tni_y1 [expr {max($tni_y1,[$tni_g yMax])}]
   }}
   if {$tni_x0 > $tni_x1} {error "Actual macro clock pin has no physical shape"}
   puts $tni_o [format "MPIN\t%s\t%s\t%.9f\t%.9f" [$tni_i getName] [$tni_mt getName] [expr {($tni_x0+$tni_x1+2*[$tni_ib xMin])/(2*$tni_u)}] [expr {($tni_y0+$tni_y1+2*[$tni_ib yMin])/(2*$tni_u)}]]
  }
 }
 puts $tni_o [format "CELL\t%s\t%s\t%.9f\t%.9f\t%d\t%d" [$tni_i getName] [$tni_m getName] [expr {[$tni_m getWidth]/$tni_u}] [expr {[$tni_m getHeight]/$tni_u}] [$tni_m isBlock] $tni_sig]
}
foreach tni_bt [$tni_b getBTerms] {
 set tni_n [$tni_bt getNet]
 set tni_net "-"
 if {$tni_n ne "NULL"} {set tni_net [$tni_n getName]}
 set tni_x "-";set tni_y "-";set tni_layer "-"
 set tni_bp [lindex [$tni_bt getBPins] 0]
 if {$tni_bp ne ""} {
  set tni_box [lindex [$tni_bp getBoxes] 0]
  if {$tni_box ne ""} {
   set tni_x [format %.9f [expr {([$tni_box xMin]+[$tni_box xMax])/(2*$tni_u)}]]
   set tni_y [format %.9f [expr {([$tni_box yMin]+[$tni_box yMax])/(2*$tni_u)}]]
   set tni_tl [$tni_box getTechLayer]
   if {$tni_tl ne "NULL"} {set tni_layer [$tni_tl getName]}
  }
 }
 puts $tni_o "PORT\t[$tni_bt getName]\t[$tni_bt getIoType]\t[$tni_bt getSigType]\t$tni_layer\t$tni_x\t$tni_y\t$tni_net"
}
close $tni_o
puts "TT_READ_ONLY_NATIVE_INVENTORY_DONE $::env(OT_TT_NATIVE_OUT)"
