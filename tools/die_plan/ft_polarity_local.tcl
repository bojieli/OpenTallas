# Optional PRE_GLOBAL_PLACE placement structure for FT QN -> INV pairs.
# Keep the polarity inverter beside the planned launch station; subsequent
# repair_design buffers the long wire after the inverter, rather than the weak QN.
# Both canonical _sN and bound port-derived _i_N/_o_N stations belong to the same
# physical structure; bound names under u_bound are emitted by prepare-stations.
# Placement only: no cells, connections, clocks, or cycles change. The ordinary
# face_flops_release hook releases these cells for legalisation before DPL.
if {![info exists ::env(OT_FT_POLARITY_LOCAL)] || $::env(OT_FT_POLARITY_LOCAL) ne "1"} {return}
set fpl_only_group ""
if {[info exists ::env(OT_FT_POLARITY_LOCAL_GROUP)]} {
  set fpl_only_group $::env(OT_FT_POLARITY_LOCAL_GROUP)
}
# An authored table is complete for one exact native payload group. Build the
# placement transaction first so a stale bit or occupied site moves no inverter.
proc fpl_load_exact_sites {path} {
  set sites {}
  set input [open $path r]
  try {
    while {[gets $input line] >= 0} {
      set fields [split $line "\t"]
      lassign $fields bit x y
      if {[llength $fields] != 3 || ![regexp {^(0|[1-9][0-9]*)$} $bit] ||
          ![string is double -strict $x] || ![string is double -strict $y] ||
          [dict exists $sites $bit]} {
        error "invalid or duplicate authored FT polarity site: $line"
      }
      dict set sites $bit [list $x $y]
    }
  } finally {
    close $input
  }
  if {![dict size $sites]} {error "authored FT polarity site table is empty"}
  return $sites
}

proc fpl_box {inst} {
  set b [$inst getBBox]
  return [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]
}

proc fpl_row_indexes {y h} {
  global ff_y0 ff_rh
  set rows {}
  for {set r [expr {int(floor(double($y-$ff_y0)/$ff_rh))}]} {$ff_y0+$r*$ff_rh < $y+$h} {incr r} {
    lappend rows $r
  }
  return $rows
}

proc fpl_check_site {name x y w h launch rows_name blocks} {
  global ff_x0 ff_y0 ff_x1 ff_y1 ff_sw ff_dbu ff_orient
  upvar 1 $rows_name occupied
  if {$x < $ff_x0 || $y < $ff_y0 || $x+$w > $ff_x1 || $y+$h > $ff_y1 ||
      ![dict exists $ff_orient $y] || ($x-$ff_x0)%$ff_sw != 0} {
    error "authored FT polarity site is off the legal row grid: $name"
  }
  lassign $launch ax ay bx by
  if {abs($x-$bx)+abs($y-$ay) > 25*$ff_dbu} {
    error "authored FT polarity site is >25um from its current launch flop: $name"
  }
  if {[ff_core_hit $blocks $x $y $w $h] || [ff_hits_explicit $x $y $w $h]} {
    error "authored FT polarity site overlaps a macro or explicit reservation: $name"
  }
  set box [list $x $y [expr {$x+$w}] [expr {$y+$h}]]
  foreach row [fpl_row_indexes $y $h] {
    if {[ff_pair_row_blocked $row] || ([dict exists $occupied $row] &&
        [ff_core_hit [dict get $occupied $row] $x $y $w $h])} {
      error "authored FT polarity site overlaps a blocked row or fixed cell: $name"
    }
    dict lappend occupied $row $box
  }
}

set fpl_sites {}
set fpl_bits {}
set fpl_moves {}
set fpl_blocks {}
set fpl_occupied {}
if {[info exists ::env(OT_FT_POLARITY_LOCAL_SITES)]} {
  if {$fpl_only_group eq ""} {error "authored FT polarity sites require one exact native group"}
  set fpl_sites [fpl_load_exact_sites $::env(OT_FT_POLARITY_LOCAL_SITES)]
  # face_flops.tcl initializes this state globally, but ORFS sources this
  # hook from its placement procedure's local frame.
  set fpl_dbu $::ff_dbu
}
set fpl_blk [ord::get_db_block]
set fpl_core [$fpl_blk getCoreArea]
set fpl_n 0
set fpl_seen {}
# The planned FT grid reserves room for FFs at its target local density.
# Put the new fixed inverter cohort in a neighbouring band instead of filling
# the free fraction of those same FF rows (which makes GPL unable to spread).
set fpl_groups {}
foreach fpl_ff [$fpl_blk getInsts] {
  if {[dict size $fpl_sites]} {
    if {[[$fpl_ff getMaster] isBlock]} {
      lappend fpl_blocks [fpl_box $fpl_ff]
    } elseif {[$fpl_ff getPlacementStatus] in {FIRM LOCKED COVER}} {
      set fpl_box [fpl_box $fpl_ff]
      lassign $fpl_box x y u v
      foreach fpl_r [fpl_row_indexes $y [expr {$v-$y}]] {
        dict lappend fpl_occupied $fpl_r $fpl_box
      }
    }
    continue
  }
  set fpl_name [string map {\\ {}} [$fpl_ff getName]]
  if {![regexp {^((?:.*[./])?u_ft_.+_(?:s[0-9]+|[io]_[0-9]+))/q\[} $fpl_name -> fpl_group]} {continue}
  if {$fpl_only_group ne "" && $fpl_group ne $fpl_only_group} {continue}
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
  if {![regexp {^((?:.*[./])?u_ft_.+_(?:s[0-9]+|[io]_[0-9]+))/q\[} $fpl_name -> fpl_group]} {continue}
  if {$fpl_only_group ne "" && $fpl_group ne $fpl_only_group} {continue}
  if {![string match DFF* [[$fpl_ff getMaster] getName]]} {continue}
  if {[dict size $fpl_sites]} {
    if {![regexp {/q\[((?:0|[1-9][0-9]*))\]\$_} $fpl_name -> fpl_bit] ||
        ![dict exists $fpl_sites $fpl_bit] || [dict exists $fpl_bits $fpl_bit]} {
      error "unexpected or duplicate authored FT polarity launch bit: $fpl_name"
    }
    dict set fpl_bits $fpl_bit 1
  }
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
    if {[dict size $fpl_sites]} {
      lassign [dict get $fpl_sites $fpl_bit] fpl_x_um fpl_y_um
      set fpl_x [expr {round($fpl_x_um*$fpl_dbu)}]
      set fpl_y [expr {round($fpl_y_um*$fpl_dbu)}]
      if {abs($fpl_x_um*$fpl_dbu-$fpl_x)>1e-6 || abs($fpl_y_um*$fpl_dbu-$fpl_y)>1e-6} {
        error "authored FT polarity site is not on the database grid: $fpl_name"
      }
      fpl_check_site $fpl_name $fpl_x $fpl_y $fpl_w [[$fpl_inv getMaster] getHeight] \
          [fpl_box $fpl_ff] fpl_occupied $fpl_blocks
      dict set fpl_moves $fpl_bit [list $fpl_inv $fpl_x $fpl_y [$fpl_ff getName]]
      dict set fpl_seen [$fpl_inv getName] 1
      continue
    }
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
if {[dict size $fpl_sites]} {
  if {[dict size $fpl_moves] != [dict size $fpl_sites]} {
    close $fpl_out
    error "authored FT polarity group matched [dict size $fpl_moves]/[dict size $fpl_sites] movable QN/INV pairs"
  }
  dict for {bit move} $fpl_moves {
    lassign $move inv x y launch
    $inv setOrient [dict get $::ff_orient $y]
    $inv setLocation $x $y
    $inv setPlacementStatus FIRM
    puts $fpl_out "[$inv getName]\tPOLARITY\t$x\t$y\t$launch"
    incr fpl_n
  }
}
close $fpl_out
if {$fpl_only_group ne "" && $fpl_n == 0} {
  error "OT_FT_POLARITY_LOCAL no movable launch pairs for $fpl_only_group"
}
puts "OT_FT_POLARITY_LOCAL launch pairs $fpl_n (placement only, PIN CYCLES 0)"
