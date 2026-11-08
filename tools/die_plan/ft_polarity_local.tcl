# Optional PRE_GLOBAL_PLACE placement structure for FT QN -> INV pairs.
# Keep the polarity inverter beside the planned launch station; subsequent
# repair_design buffers the long wire after the inverter, rather than the weak QN.
# Placement only: no cells, connections, clocks, or cycles change. The ordinary
# face_flops_release hook releases these cells for legalisation before DPL.
if {![info exists ::env(OT_FT_POLARITY_LOCAL)] || $::env(OT_FT_POLARITY_LOCAL) ne "1"} {return}
set fpl_blk [ord::get_db_block]
set fpl_core [$fpl_blk getCoreArea]
set fpl_n 0
set fpl_seen {}
# The planned FT grid reserves room for FFs at its target local density.
# Put the new fixed inverter cohort in a neighbouring band instead of filling
# the free fraction of those same FF rows (which makes GPL unable to spread).
set fpl_groups {}
foreach fpl_ff [$fpl_blk getInsts] {
  set fpl_name [string map {\\ {}} [$fpl_ff getName]]
  if {![regexp {^(u_ft_.+_s[0-9]+)/q\[} $fpl_name -> fpl_group]} {continue}
  if {![string match DFF* [[$fpl_ff getMaster] getName]]} {continue}
  set fpl_bb [$fpl_ff getBBox]
  set fpl_box [list [$fpl_bb xMin] [$fpl_bb yMin] [$fpl_bb xMax] [$fpl_bb yMax]]
  if {[dict exists $fpl_groups $fpl_group]} {
    lassign [dict get $fpl_groups $fpl_group] ax ay bx by
    lassign $fpl_box cx cy dx dy
    set fpl_box [list [expr {min($ax,$cx)}] [expr {min($ay,$cy)}] [expr {max($bx,$dx)}] [expr {max($by,$dy)}]]
  }
  dict set fpl_groups $fpl_group $fpl_box
}
set fpl_out [open $::env(RESULTS_DIR)/ot_face_flops.txt a]
foreach fpl_ff [$fpl_blk getInsts] {
  set fpl_name [string map {\\ {}} [$fpl_ff getName]]
  if {![regexp {^(u_ft_.+_s[0-9]+)/q\[} $fpl_name -> fpl_group]} {continue}
  if {![string match DFF* [[$fpl_ff getMaster] getName]]} {continue}
  if {[$fpl_ff getPlacementStatus] ni {FIRM PLACED}} {continue}
  foreach fpl_q [$fpl_ff getITerms] {
    if {![$fpl_q isOutputSignal] || [[$fpl_q getMTerm] getName] ne "QN"} {continue}
    set fpl_net [$fpl_q getNet]
    if {$fpl_net eq "NULL" || $fpl_net eq "" || [llength [$fpl_net getBTerms]]} {continue}
    set fpl_inv ""
    # Earlier placement can already have inserted a unary buffer before INV.
    # Follow only an exclusive short unary chain. Moving its inverter beside
    # the FF also makes HPWL place those freely movable buffers beside it.
    for {set fpl_hop 0} {$fpl_hop < 4} {incr fpl_hop} {
      if {[llength [$fpl_net getBTerms]]} {break}
      set fpl_loads {}
      foreach fpl_it [$fpl_net getITerms] {
        if {[$fpl_it isInputSignal]} {lappend fpl_loads $fpl_it}
      }
      if {[llength $fpl_loads] != 1} {break}
      set fpl_it [lindex $fpl_loads 0]
      set fpl_cell [$fpl_it getInst]
      set fpl_master [[$fpl_cell getMaster] getName]
      if {[[$fpl_it getMTerm] getName] ne "A"} {break}
      if {[string match INV* $fpl_master]} {set fpl_inv $fpl_cell;break}
      if {![string match BUF* $fpl_master]} {break}
      set fpl_y [$fpl_cell findITerm Y]
      if {$fpl_y eq "NULL" || $fpl_y eq ""} {break}
      set fpl_net [$fpl_y getNet]
      if {$fpl_net eq "NULL" || $fpl_net eq ""} {break}
    }
    if {$fpl_inv eq ""} {continue}
    if {[$fpl_inv getPlacementStatus] in {FIRM LOCKED COVER} || [dict exists $fpl_seen [$fpl_inv getName]]} {continue}
    set fpl_bb [$fpl_ff getBBox]
    set fpl_w [[$fpl_inv getMaster] getWidth]
    set fpl_x [$fpl_bb xMax]
    set fpl_y [$fpl_bb yMin]
    lassign [dict get $fpl_groups $fpl_group] ax ay bx by
    if {$bx-$ax >= $by-$ay} {
      # An even number of rows preserves the source row orientation.
      set fpl_rh [[$fpl_ff getMaster] getHeight]
      set fpl_shift [expr {int(ceil(double($by-$ay)/(2*$fpl_rh)))*2*$fpl_rh}]
      if {$by+$fpl_shift > [$fpl_core yMax]} {set fpl_shift [expr {-$fpl_shift}]}
      set fpl_y [expr {$fpl_y+$fpl_shift}]
    } else {
      set fpl_x [expr {$fpl_x+$bx-$ax}]
      if {$fpl_x+$fpl_w > [$fpl_core xMax]} {set fpl_x [expr {[$fpl_bb xMin]-($bx-$ax)-$fpl_w}]}
    }
    if {$fpl_x + $fpl_w > [$fpl_core xMax]} {set fpl_x [expr {[$fpl_bb xMin]-$fpl_w}]}
    if {$fpl_x < [$fpl_core xMin] || $fpl_y < [$fpl_core yMin] || $fpl_y+[[$fpl_inv getMaster] getHeight] > [$fpl_core yMax]} {continue}
    $fpl_inv setOrient [$fpl_ff getOrient]
    $fpl_inv setLocation $fpl_x $fpl_y
    $fpl_inv setPlacementStatus FIRM
    dict set fpl_seen [$fpl_inv getName] 1
    puts $fpl_out "[$fpl_inv getName]\tPOLARITY\t$fpl_x\t$fpl_y\t[$fpl_ff getName]"
    incr fpl_n
  }
}
close $fpl_out
puts "OT_FT_POLARITY_LOCAL launch pairs $fpl_n (placement only, PIN CYCLES 0)"
