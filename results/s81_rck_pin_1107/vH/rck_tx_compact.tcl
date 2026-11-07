# Private t16 TX data-flow form. Native pins, tap positions and source window stay unchanged.
set ::env(OT_TAP_MAX_SINKS) 6500
# S81-RCK-6 11-07 vH.  Raw ODB names carry backslashes (pin_q\[0\]\[7\]$_DFF_P_): the vG regex had none, so no pin row grouped.
# pin_v / pin_rst_n are one merged FF per stage with D = rs_t[1]: no timing path to data in stages 0 and 1, so only pin_v[2] joins a group, the encoder's.
# Each pin_q stage is its own whole-row group on its centroid's tap; the encoder tree keeps its 200 um span.
set ::env(OT_TAP_GROUP_RE) {(u_core\.u_tx_pin\.u_enc|u_bin_coll_i0|u_cland_coll_i0|u_core\.u_tx_pin\.pin_q\\?\[[0-2]\\?\]|u_core\.u_tx_pin\.pin_v\\?\[2\\?\])}
set ::env(OT_TAP_GROUP_ALIAS) [list u_core.u_tx_pin.u_enc=encoder u_core.u_tx_pin.pin_v*=encoder u_bin_coll_i0=coll_capture u_cland_coll_i0=coll_capture]
proc rck_clean {s} {return [string map {\\ {}} $s]}
proc rck_ff {i} {return [string match *DFF* [[$i getMaster] getName]]}
proc rck_tx_group {name box members} {
  set b [ord::get_db_block]; set u [$b getDbUnitsPerMicron]
  set r ""; foreach x [$b getRegions] {if {[$x getName] eq $name} {set r $x; break}}
  if {$r eq ""} {
    set r [odb::dbRegion_create $b $name]; $r setRegionType EXCLUSIVE
    lassign $box x0 y0 x1 y1
    odb::dbBox_create $r [expr {round($x0*$u)}] [expr {round($y0*$u)}] [expr {round($x1*$u)}] [expr {round($y1*$u)}]
    set g [odb::dbGroup_create $r $name]; $g setType VOLTAGE_DOMAIN
  } else {set g [lindex [$r getGroups] 0]}
  set area 0.0; set n 0; set conflict 0
  dict for {key i} $members {
    set old [$i getGroup]
    if {$old ne "NULL" && $old ne "" && [$old getName] ne [$g getName]} {incr conflict; continue}
    $g addInst $i; incr n
    set m [$i getMaster]; set area [expr {$area+double([$m getWidth])*[$m getHeight]/$u/$u}]
  }
  lassign $box x0 y0 x1 y1
  puts "RCK_TX_COMPACT region=$name cells=$n area_um2=$area fill=[expr {$area/(($x1-$x0)*($y1-$y0))}] other_group_conflicts=$conflict box=$box"
}
proc rck_tx_compact_regions {} {
  set b [ord::get_db_block]; set enc [dict create]; set bin [dict create]; set stack {}
  foreach i [$b getInsts] {
    set n [rck_clean [$i getName]]
    if {[rck_ff $i] && [regexp {u_core[./]u_tx_pin[./]u_enc[./]} $n]} {
      dict set enc [$i getName] $i
      foreach t [$i getITerms] {if {[[$t getMTerm] getName] eq "D" && [$t getNet] ne "NULL"} {lappend stack [$t getNet]}}
    }
    if {[rck_ff $i] && [regexp {u_bin_coll_i0[./]} $n]} {dict set bin [$i getName] $i}
  }
  # Yosys ABC cell names may be anonymous. Own the registered encoder's actual
  # combinational fan-in, stopping at all other registers and hard macros.
  set seen [dict create]
  while {[llength $stack]} {
    set net [lindex $stack end]; set stack [lrange $stack 0 end-1]
    if {[dict exists $seen [$net getName]]} continue
    dict set seen [$net getName] 1
    foreach t [$net getITerms] {
      if {![$t isOutputSignal]} continue
      set i [$t getInst]; set m [$i getMaster]
      if {[$m isBlock] || [rck_ff $i] || [string match TIE* [$m getName]] || [dict exists $enc [$i getName]]} continue
      dict set enc [$i getName] $i
      foreach p [$i getITerms] {if {[$p isInputSignal] && [$p getNet] ne "NULL"} {lappend stack [$p getNet]}}
    }
  }
  if {![dict size $enc] || ![dict size $bin]} {error "RCK_TX_COMPACT: stale encoder/BIN selector"}
  rck_tx_group rck_tx_encoder {2065 466 2265 666} $enc
  rck_tx_group rck_tx_bin {2770 105 2874 265} $bin
}
proc rck_tx_pin_positions {} {
  set b [ord::get_db_block]; set u [$b getDbUnitsPerMicron]; set nq 0; set np 0
  set pd {}
  foreach i [$b getInsts] {
    if {![rck_ff $i]} continue
    set n [rck_clean [$i getName]]
    if {[regexp {u_bin_coll_i0[./]q\[([0-9]+)\]} $n -> bit]} {
      $i setLocation [expr {round((2772+($bit%32)*3.0)*$u)}] [expr {round((115+int($bit/32)*6.5)*$u)}]
      $i setPlacementStatus PLACED; incr nq
    } elseif {[regexp {u_bin_coll_i0[./]eq} $n]} {
      $i setLocation [expr {round(2832*$u)}] [expr {round(240*$u)}]; $i setPlacementStatus PLACED
    }
    if {[regexp {u_core[./]u_tx_pin[./]u_enc[./]p_d\[([0-9]+)\]} $n -> bit]} {lappend pd [list $bit $i]}
    if {[regexp {u_core[./]u_tx_pin[./]u_enc[./]p_v} $n]} {$i setLocation [expr {round(2255*$u)}] [expr {round(660*$u)}]; $i setPlacementStatus PLACED}
  }
  set x 2065.0; set y 650.0
  foreach item [lsort -integer -index 0 $pd] {
    set i [lindex $item 1]; set w [expr {double([[$i getMaster] getWidth])/$u}]
    if {$x+$w > 2264} {set x 2065.0; set y [expr {$y+0.54}]}
    $i setLocation [expr {round($x*$u)}] [expr {round($y*$u)}]; $i setPlacementStatus PLACED
    set x [expr {$x+$w+0.216}]; incr np
  }
  puts "RCK_TX_COMPACT placed_BIN=$nq placed_encoder_pd=$np pd_last_y=$y (DPL must legalize; measure actual hops at PLACE)"
}
# S81-RCK-5 11-07: the fences shape global placement only.  Legalizing inside them left 2011 cells stuck on the fence edges (DPL-0033, t16 PLACE pilot);
# released on a copy of that DB the legalizer finished in one pass, 2.3 um max displacement, checks clean.  Other regions (PHY PG keep-out) stay.
proc rck_tx_release_regions {} {
  set b [ord::get_db_block]
  foreach g [$b getGroups] {
    set n [$g getName]; if {![string match rck_tx_* $n]} continue
    set c 0; foreach i [$g getInsts] {$g removeInst $i; incr c}
    set r [$g getRegion]; odb::dbGroup_destroy $g; if {$r ne "NULL"} {odb::dbRegion_destroy $r}
    puts "RCK_TX_COMPACT released fence $n cells=$c"
  }
}

# S81-RCK-6 11-07 vH: the reset/valid chain follows its own source: evenly from rs_t[1] to the encoder box north wall.  vG hops 447/50/441 um, v2 outside the fence.
proc rck_tx_pose_controls {} {
  set b [ord::get_db_block]; set u [$b getDbUnitsPerMicron]; set src ""; set v [dict create]
  foreach i [$b getInsts] {
    if {![rck_ff $i]} continue
    set n [rck_clean [$i getName]]
    if {[regexp {u_core[./]rs_t\[1\]} $n]} {set src $i}
    if {[regexp {u_core[./]u_tx_pin[./]pin_v\[([0-2])\]} $n -> j]} {dict set v $j $i}
  }
  if {$src eq "" || [dict size $v] != 3} {error "RCK_TX_CONTROL: selector found src='$src' stages=[dict size $v]"}
  lassign [$src getLocation] px py
  set tx [expr {round(2165*$u)}]; set ty [expr {round(462*$u)}]
  foreach j {0 1 2} {
    set f [expr {($j+1)/3.0}]; set x [expr {round($px+($tx-$px)*$f)}]; set y [expr {round($py+($ty-$py)*$f)}]
    set i [dict get $v $j]; $i setLocation $x $y; $i setPlacementStatus PLACED
    # the QN inverter goes with its flop; deeper encoder reset buffers stay where they serve
    set moved 0
    foreach o [$i getITerms] {
      if {![$o isOutputSignal] || [$o getNet] eq "NULL"} continue
      foreach l [[$o getNet] getITerms] {
        if {![$l isInputSignal]} continue
        set li [$l getInst]
        if {[regexp {^(BUF|INV)} [[$li getMaster] getName]]} {$li setLocation [expr {$x+round(2*$u)}] $y; $li setPlacementStatus PLACED; incr moved}
      }
    }
    puts "RCK_TX_CONTROL pin_v$j at [expr {double($x)/$u}] [expr {double($y)/$u}] moved_inverters $moved"
  }
}
# Fail closed: a silent alias miss cost one whole vG place.
proc rck_tx_assert_cohort {} {
  set b [ord::get_db_block]; set u [$b getDbUnitsPerMicron]; set nets [dict create]
  foreach i [$b getInsts] {
    if {![rck_ff $i]} continue
    set n [rck_clean [$i getName]]; set k ""
    if {[regexp {u_core[./]u_tx_pin[./]pin_q\[([0-2])\]} $n -> j]} {set k pin$j
    } elseif {[regexp {u_core[./]u_tx_pin[./]pin_v\[2\]} $n] || [regexp {u_core[./]u_tx_pin[./]u_enc[./]} $n]} {set k encoder
    } elseif {[regexp {u_bin_coll_i0[./]} $n]} {set k bin}
    if {$k eq ""} continue
    foreach t [$i getITerms] {if {[[$t getMTerm] getName] eq "CLK"} {dict incr nets "$k [[$t getNet] getName]"}}
  }
  puts "RCK_TX_COHORT $nets"
  set seen [dict create]; dict for {kn c} $nets {dict incr seen [lindex $kn 0]}
  foreach k {pin0 pin1 pin2 encoder bin} {if {![dict exists $seen $k] || [dict get $seen $k] != 1} {error "RCK_TX_COHORT $k not on one tap: $nets"}}
}
