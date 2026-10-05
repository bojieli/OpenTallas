# --step-tcl POST_PDN hook for the ot_fwd_link_hop2 fixture (die 490 x 320 um): stage A at the west edge, stage B at the
# east edge, fence centroids 440 um apart (>= the 430.56 um link span).  Each stage's fence holds its flops and the
# logic local to them (A: its flops' D-side cone, i.e. the reset/enable gating; B: its flops' Q-side loads), so the
# only long wires are the hop's data bus and its forwarded clock.  Geometry only; no timing constraint.
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set XA0 5;   set XA1 45      ;# stage A fence (centroid x 25)
set XB0 445; set XB1 485     ;# stage B fence (centroid x 465)
# both fences span the band the ordered port groups occupy (the placer packs the 515 ports of each edge into ~50 um
# around the die's mid height), so each bit runs straight across: port -> A flop -> span -> B flop -> port
set Y0 110;  set Y1 210
proc fence {block dbu name x0 x1 y0 y1} {
  set r [odb::dbRegion_create $block $name]
  odb::dbBox_create $r [expr {int($x0 * $dbu)}] [expr {int($y0 * $dbu)}] [expr {int($x1 * $dbu)}] [expr {int($y1 * $dbu)}]
  return $r
}
proc free_comb {inst} { expr {![[$inst getMaster] isSequential] && [$inst getRegion] eq "NULL"} }
# driver cone of an input pin, `depth` combinational levels
proc add_driver_cone {region iterm depth} {
  set net [$iterm getNet]
  if {$net eq "NULL" || $depth <= 0} { return 0 }
  set n 0
  foreach it [$net getITerms] {
    if {![$it isOutputSignal]} { continue }
    set inst [$it getInst]
    if {![free_comb $inst]} { continue }
    $region addInst $inst; incr n
    foreach in [$inst getITerms] { if {[$in isInputSignal]} { incr n [add_driver_cone $region $in [expr {$depth - 1}]] } }
  }
  return $n
}
set west [fence $block $dbu tx_west $XA0 $XA1 $Y0 $Y1]
set east [fence $block $dbu rx_east $XB0 $XB1 $Y0 $Y1]
set nw 0; set ne 0; set cw 0; set ce 0
foreach inst [$block getInsts] {
  if {![[$inst getMaster] isSequential]} { continue }
  set n [$inst getName]
  if {[string match "u_a.*" $n]} {
    $west addInst $inst; incr nw
    foreach it [$inst getITerms] { if {[$it isInputSignal] && [[$it getMTerm] getName] ne "CLK"} { incr cw [add_driver_cone $west $it 2] } }
  } elseif {[string match "u_b.*" $n]} {
    $east addInst $inst; incr ne
    foreach it [$inst getITerms] {
      if {![$it isOutputSignal] || [$it getNet] eq "NULL"} { continue }
      foreach ld [[$it getNet] getITerms] {
        set li [$ld getInst]
        if {[$ld isInputSignal] && [free_comb $li]} { $east addInst $li; incr ce }
      }
    }
  }
}
# stage A's forwarding inverter (u_a.active.u_fwd_inv, kept hierarchy) at the launching end
set ni 0
foreach inst [$block getInsts] {
  if {[string match "u_a.*u_fwd_inv*" [$inst getName]] && [$inst getRegion] eq "NULL"} { $west addInst $inst; incr ni }
}
# forwarded-clock span repeaters u_rep<k> (k = 0..5): a 4 x 4 um fence each, at even pitch from the forwarding inverter
# (x 25) to stage B's subtree root (x 465) along the die's mid line (y 160), as a hand-placed clock spine
set nr 0
foreach inst [$block getInsts] {
  if {[regexp {^u_rep([0-9])/} [$inst getName] -> k]} {
    set x [expr {25.0 + 440.0 * ($k + 1) / 7.0}]
    set r [fence $block $dbu "fwd_rep_$k" [expr {$x - 2}] [expr {$x + 2}] 158 162]
    $r addInst $inst; incr nr
  }
}
puts "OT_FENCE tx_west sequential $nw cone $cw inverter $ni; rx_east sequential $ne cone $ce; span repeaters $nr"
if {$nw == 0 || $ne == 0 || $ni != 1 || $nr != 6} { error "ot_fwd_link_hop2 fence: unexpected instance names" }
