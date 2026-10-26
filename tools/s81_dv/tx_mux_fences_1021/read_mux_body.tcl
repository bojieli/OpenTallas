# Actual score-memory read mux and its registered receiver stay in the open central channel.
# Stops at SRAM pins and sequential roots. Release exclusive fence before DPL / CTS.
proc txmux_seq {m} {
 foreach mt [$m getMTerms] {if {[$mt getSigType] eq "CLOCK"} {return 1}}
 return 0
}
set ::txm_b [ord::get_db_block]
set ::txm_dbu [$::txm_b getDbUnitsPerMicron]
set ::txm_region [odb::dbRegion_create $::txm_b lp_fence_tx_score_mux]
lassign $::txm_box x0 y0 x1 y1
odb::dbBox_create $::txm_region [expr {round($x0*$::txm_dbu)}] [expr {round($y0*$::txm_dbu)}] [expr {round($x1*$::txm_dbu)}] [expr {round($y1*$::txm_dbu)}]
set ::txm_group [odb::dbGroup_create $::txm_region lp_fence_grp_tx_score_mux]
set ::txm_front {};set ::txm_seeds 0;set ::txm_comb 0
foreach i [$::txm_b getInsts] {
 regsub -all {\\} [$i getName] {} n
 if {![regexp {(?:^|[./])u_sm[./]rd\[[0-9]+\]} $n]} continue
 if {[[$i getMaster] isBlock] || ![txmux_seq [$i getMaster]]} continue
 if {[$i getGroup] ne "NULL"} {error "TX_MUX_FENCE seed already grouped: $n"}
 $::txm_group addInst $i
 lappend ::txm_front $i;incr ::txm_seeds
}
if {$::txm_seeds != 256} {error "TX_MUX_FENCE expected 256 actual score receiver registers, found $::txm_seeds"}
for {set depth 0} {$depth < 24 && [llength $::txm_front]} {incr depth} {
 set next {}
 foreach i $::txm_front {
  foreach it [$i getITerms] {
   if {![$it isInputSignal] || [[$it getMTerm] getSigType] eq "CLOCK"} continue
   if {[txmux_seq [$i getMaster]] && [[$it getMTerm] getName] ne "D"} continue
   set n [$it getNet];if {$n eq "NULL" || [$n getSigType] ne "SIGNAL"} continue
   foreach dt [$n getITerms] {
    if {![$dt isOutputSignal]} continue
    set di [$dt getInst];set dm [$di getMaster]
    if {[$dm isBlock] || [$dm getType] ne "CORE" || [txmux_seq $dm] || [$di getGroup] ne "NULL"} continue
    $::txm_group addInst $di;incr ::txm_comb;lappend next $di
   }
  }
 }
 set ::txm_front $next
}
if {$::txm_comb < 256} {error "TX_MUX_FENCE score read cone unexpectedly small: $::txm_comb"}
puts "TX_MUX_FENCE seeds=$::txm_seeds comb=$::txm_comb box=$::txm_box (release before DPL and CTS)"
