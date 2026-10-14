# Existing forwarding lead BUF moves beside its actual used FF and polarity
# converter. Existing tail BUF stays at the output pin. Counts/epochs/ABI stay.
set fd_block [ord::get_db_block]
set fd_firm [expr {![info exists ::env(S81_FORWARD_DRIVE_MOVABLE)] || !$::env(S81_FORWARD_DRIVE_MOVABLE)}]
set fd_keep [open $::env(RESULTS_DIR)/s81_forward_drive_firm.txt w]
set fd_report [open $::env(RESULTS_DIR)/s81_forward_drive.tsv w]
puts $fd_report "output\tused_FF\tlead_BUF\tupstream_cells\tphase\tlead_x_um\tlead_y_um"
set fd_count 0;set fd_upstream_count 0
foreach fd_key $mp_order {
 set fd_ff [dict get $mp_map $fd_key]
 set fd_net [[$fd_block findBTerm $fd_key] getNet]
 set fd_lead ""
 # Resizer may have added pin-side buffers; find the preserved leading BUF.
 for {set hop 0} {$hop<20} {incr hop} {
  set driver ""
  foreach it [$fd_net getITerms] {if {[$it isOutputSignal]} {set driver $it;break}}
  if {$driver eq ""} {error "S81_FORWARD_DRIVE undriven output $fd_key"}
  set inst [$driver getInst];set master [[$inst getMaster] getName]
  if {[regexp {^ot_ohdrv_[0-9]+_0$} [$inst getName]]} {set fd_lead $inst;break}
  if {![regexp {^(BUF|INV|HB)} $master]} {error "S81_FORWARD_DRIVE no original lead BUF $fd_key ($master)"}
  set fd_net [[$inst findITerm A] getNet]
 }
 if {$fd_lead eq ""} {error "S81_FORWARD_DRIVE lead search exhausted $fd_key"}
 set fd_chain {};set fd_net [[$fd_lead findITerm A] getNet]
 for {set hop 0} {$hop<20} {incr hop} {
  set driver "";set loads 0
  foreach it [$fd_net getITerms] {if {[$it isOutputSignal]} {set driver $it} else {incr loads}}
  if {$driver eq ""} {error "S81_FORWARD_DRIVE undriven lead input $fd_key"}
  set inst [$driver getInst]
  if {$inst eq $fd_ff} break
  set master [[$inst getMaster] getName]
  if {$loads!=1 || [llength [$fd_net getBTerms]]!=0 || ![regexp {^(BUF|INV|HB)} $master]} {
   error "S81_FORWARD_DRIVE shared/non-buffer path before lead $fd_key ($master loads$loads)"
  }
  lappend fd_chain $inst
  set fd_net [[$inst findITerm A] getNet]
 }
 if {$inst ne $fd_ff} {error "S81_FORWARD_DRIVE does not reach original used FF $fd_key"}
 set fd_chain [lreverse $fd_chain]
 set bb [$fd_ff getBBox];set x [$bb xMax];set y [$bb yMin]
 set face [[$fd_block findBTerm $fd_key] getBBox]
 set west [expr {[$face xMin]==0}]
 if {$west} {set x [$bb xMin]}
 if {[string match {co*} $fd_key]} {set x [$bb xMin];set y [expr {$y-round(.54*$mp_dbu)}]}
 set names {}
 foreach inst [concat $fd_chain [list $fd_lead]] {
  set master [$inst getMaster]
  if {[$master getHeight]!=[$bb yMax]-[$bb yMin]} {error "S81_FORWARD_DRIVE non-single-row stage $fd_key"}
  if {$west} {set x [expr {$x-[$master getWidth]-round(.108*$mp_dbu)}]} else {set x [expr {$x+round(.108*$mp_dbu)}]}
  $inst setOrient [$fd_ff getOrient];$inst setLocation $x $y
  if {$fd_firm} {$inst setPlacementStatus FIRM;puts $fd_keep [$inst getName]} else {$inst setPlacementStatus PLACED}
  lappend names [$inst getName]
  if {!$west} {set x [expr {$x+[$master getWidth]}]}
 }
 lassign [$fd_lead getLocation] lx ly
 incr fd_upstream_count [llength $fd_chain]
 puts $fd_report "$fd_key\t[$fd_ff getName]\t[$fd_lead getName]\t[join $names ,]\t[expr {$fd_firm ? {GPL_FIRM} : {DPL_MOVABLE}}]\t[expr {$lx/double($mp_dbu)}]\t[expr {$ly/double($mp_dbu)}]"
 incr fd_count
}
close $fd_report;close $fd_keep
if {$fd_count!=1464} {error "S81_FORWARD_DRIVE expected1464 genuine forwarding roles, got$fd_count"}
puts "S81_FORWARD_DRIVE $fd_count existing leading BUFs +$fd_upstream_count existing polarity/buffer cells beside original used FFs; tail BUFs stay at pins; no new cell/state/epoch."
