# The registered data pins use leaf_inhold. Valid/ready enter small control
# cones and need the same receiver hold obligation even without a direct D pin.
set ihb [ord::get_db_block]
set ihd [$ihb getDbUnitsPerMicron]
set ihm [[ord::get_db] findMaster HB4xp67_ASAP7_75t_R]
set ihbuf [[ord::get_db] findMaster BUFx4f_ASAP7_75t_R]
if {$ihm eq "NULL" || $ihbuf eq "NULL"} { error "IDX_CONTROL_HOLD: missing delay/driver master" }
set ihfh [open $::env(RESULTS_DIR)/ot_inhold_firm.txt a]
foreach pn {cmd_valid in_valid out_ready} {
  set bt [$ihb findBTerm $pn]
  if {$bt eq "NULL"} { error "IDX_CONTROL_HOLD: missing input $pn" }
  set net [$bt getNet]; set sinks {}
  foreach it [$net getITerms] { if {[$it isInputSignal]} { lappend sinks $it } }
  if {![llength $sinks]} { error "IDX_CONTROL_HOLD: input $pn has no sinks" }
  set n1 [odb::dbNet_create $ihb ot_idxctl_${pn}_hold]
  set n2 [odb::dbNet_create $ihb ot_idxctl_${pn}_drive]
  set hb [odb::dbInst_create $ihb $ihm ot_idxctl_${pn}_hb]
  set bf [odb::dbInst_create $ihb $ihbuf ot_idxctl_${pn}_buf]
  foreach it $sinks { $it disconnect; $it connect $n2 }
  [$hb findITerm A] connect $net; [$hb findITerm Y] connect $n1
  [$bf findITerm A] connect $n1; [$bf findITerm Y] connect $n2
  set r [$bt getBBox]; set ca [$ihb getCoreArea]
  set x [expr {max([$ca xMin], min(([$r xMin]+[$r xMax])/2, [$ca xMax]-[$ihm getWidth]-[$ihbuf getWidth]))}]
  set y [expr {max([$ca yMin], min(([$r yMin]+[$r yMax])/2, [$ca yMax]-[$ihm getHeight]))}]
  $hb setOrient R0; $hb setLocation $x $y; $hb setPlacementStatus FIRM
  $bf setOrient R0; $bf setLocation [expr {$x+[$ihm getWidth]}] $y; $bf setPlacementStatus FIRM
  $net setDoNotTouch 1; $n1 setDoNotTouch 1; $hb setDoNotTouch 1
  puts $ihfh [$hb getName]; puts $ihfh [$bf getName]
  puts "IDX_CONTROL_HOLD $pn: [llength $sinks] sinks behind local HB4+BUF"
}
close $ihfh
