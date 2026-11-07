# Private CH_STAGE1 form: place only the seven new state bits that split the
# four measured failing D nets. Existing pin placement runs unchanged first.
# These anchors accompany new RTL; this is not a region-only P&R retry.
source /work/face_flops.tcl
uplevel #0 {
set txb [ord::get_db_block]
set txu [[ord::get_db_tech] getDbUnitsPerMicron]
set txcore [$txb getCoreArea]
set txrows [$txb getRows]
set txsite [[lindex $txrows 0] getSite]
set txsw [$txsite getWidth]
set txn 0
set txout [open $::env(RESULTS_DIR)/ot_face_flops.txt a]
foreach inst [$txb getInsts] {
  set nm [string map [list "\\" ""] [$inst getName]]
  set xy {}
  if {[regexp {^u_enc\.g_ch_stage\.mid\[(98|113|128)\]} $nm -> bit]} {
    switch $bit { 98 {set xy {80 45}} 113 {set xy {80 52}} 128 {set xy {80 59}} }
  } elseif {[regexp {^u_enc\.g_la2\.g_ch_flags\.f0_mid\[([0-3])\]} $nm -> bit]} {
    set xy [list 282 [expr {40 + 2*$bit}]]
  }
  if {![llength $xy]} continue
  if {![string match "*DFF*" [[$inst getMaster] getName]]} continue
  set xx [expr {int(round(([lindex $xy 0]*$txu-[$txcore xMin])/double($txsw)))*$txsw+[$txcore xMin]}]
  set ty [expr {[lindex $xy 1]*$txu}]
  set best "";set delta 1e30
  foreach row $txrows {
    set yy [lindex [$row getOrigin] 1]
    set d [expr {abs($yy-$ty)}]
    if {$d<$delta} {set best $row;set delta $d}
  }
  set yy [lindex [$best getOrigin] 1]
  if {[$inst getPlacementStatus] eq "FIRM"} {$inst setPlacementStatus PLACED}
  $inst setOrient [$best getOrient]
  $inst setLocation $xx $yy
  $inst setPlacementStatus FIRM
  # Existing PRE_DETAIL_PLACE hook releases these with all pin/relay anchors.
  puts $txout "[$inst getName]\tCH_STAGE\t[expr {$xx/double($txu)}]\t[expr {$yy/double($txu)}]\tnew_midstage"
  puts "TX_CH_STAGE_ANCHOR [$inst getName] [expr {$xx/double($txu)}] [expr {$yy/double($txu)}]"
  incr txn
}
close $txout
if {$txn != 7} {error "TX_CH_STAGE expected7 new mapped state anchors, found$txn"}
}
