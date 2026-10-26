# Repeater islands for feedthrough ribbons routed OVER hard cores (every core / leaf whose routing obstruction stops
# below the partition top layer: QC SU lane cores capped at M6 with M7 ribbons, su_c / cb* cores obstructed M1-M5).
# Shared by the G2 skeleton prototype (proto_sweep.py) and the partition kit flow (same procs, same order):
#
#   set ot_gap_cores {{x0 y0 x1 y1 obs} ...} ;# over-routable cores + their top obstructed layer (hard blockages too)
#   set ot_gap_top M7                     ;# partition top signal layer
#   set ot_gap_m <core margin um>         ;# row origin / partition core margin
#   source gap_repeaters.tcl
#   # placement stage (placement RC):
#   ot_gap_repair {-max_wire_length 450}  ;# repair_design -> islands -> DPL
#   ... global_route ...
#   # global-route stage (GRT RC, ORFS global_route.tcl order), repeated until no repeater lands in a core:
#   ot_gap_repair_grt {-max_wire_length 450} {<end_incremental args>}
#   ot_gap_check 4.0                      ;# fail-closed: OT_GAP_PASS / OT_GAP_FAIL + gap_repeaters.tsv (dx AND dy)
#
# Why move-after and not a blockage-only flow: the cores ARE hard placement blockages before repair_design
# (create_blockage over every core), but the OpenROAD resizer (26Q3) puts a new repeater on the Steiner point of the
# wire without looking at blockages; only DPL honours them, and DPL alone shoves the repeater sideways into the
# nearest free strip (QC slw_su_l1: 1458 repeaters into the 17-um W strip, G2 overflow 8,787).  So every new
# BUF/INV whose origin lies inside an over-routable core is moved ALONG ITS RIBBON (same x for a N-S ribbon, same y
# for an E-W ribbon) to the first legal row outside the core on the DRIVER side: the island in the gap row before
# the macro crossing, which then drives the whole crossing.  The ribbon axis is what the core leaves open: only the
# layers above its obstruction cross it (su_l1: M7 = N-S only, so every island is in a gap row at the same x; su_c:
# M6 + M7 = both, then the axis of the repeater's nets decides).  An island repeater drives the whole macro crossing,
# so it is the strong island cell (BUFx16f / INVx13: ~360 um of M7 under the 320 ps slew limit); the resizer does
# not up-size a driver on a long-wire violation, it only inserts mid-wire, i.e. back inside the core.  repair_design is then RE-RUN with the moved repeaters
# in place (cores still blocked), with global-route parasitics as ORFS does after GRT, so every island repeater is
# re-sized / re-spaced for the span it really drives.  The passes stop when a repair_design pass puts no new
# repeater in a core.  No registers, stages, OBS or layer changes.
set ot_gap_clear 2.0
set ot_gap_nudge 3.0
# single-span reach of one island repeater over a hard core: measured on QC slw_su_c GRT RC (PATH-QC-D3HOOK 10-25),
# BUFx16f driving 385 um of M7 (65 fF) -> 569 ps at the load; wire slew ~ L^2 -> 320 ps at ~290 um.  A core longer
# than this along the ribbon cannot be crossed by any repeater placed outside it: such crossings are NOT moved (the
# resizer/DPL result stands) and are counted as OT_GAP_UNREPEATABLE (a plan item: re-aspect the core or route the
# ribbon through a repeater channel), never hidden.
if {![info exists ot_gap_span_max]} { set ot_gap_span_max 290.0 }
set ot_gap_unrep 0
if {![info exists ot_gap_top]} { set ot_gap_top M7 }
set ot_gap_island_cell {BUF BUFx16f_ASAP7_75t_R INV INVx13_ASAP7_75t_R}
set ot_gap_row 0.27
set ot_gap_site 0.054
array unset ot_gap_led
set ot_gap_pass 0

proc ot_gap_snapshot {} {
  global ot_gap_old
  array unset ot_gap_old
  foreach i [[ord::get_db_block] getInsts] { set ot_gap_old([$i getName]) 1 }
}
proc ot_gap_box_in_core {bx0 by0 bx1 by1} {
  # index of the first over-routable core the box overlaps, -1 if none
  global ot_gap_cores
  set k 0
  foreach c $ot_gap_cores {
    lassign $c x0 y0 x1 y1
    if {$bx0 < $x1 - 1e-6 && $bx1 > $x0 + 1e-6 && $by0 < $y1 - 1e-6 && $by1 > $y0 + 1e-6} { return $k }
    incr k
  }
  return -1
}
proc ot_gap_open_axes {k} {
  # preferred directions of the routing layers left open above core k (obs+1 .. ot_gap_top): v, h or vh
  global ot_gap_cores ot_gap_top
  set obs [lindex [lindex $ot_gap_cores $k] 4]
  if {$obs eq ""} { return vh }
  set tech [ord::get_db_tech]; set ax ""
  for {set l [expr {[string range $obs 1 end] + 1}]} {$l <= [string range $ot_gap_top 1 end]} {incr l} {
    set L [$tech findLayer M$l]
    if {$L eq "NULL"} { continue }
    set d [$L getDirection]
    if {$d eq "VERTICAL" && [string first v $ax] < 0} { append ax v }
    if {$d eq "HORIZONTAL" && [string first h $ax] < 0} { append ax h }
  }
  return [expr {$ax eq "" ? "vh" : $ax}]
}
proc ot_gap_source {inst} {
  # the register / port that drives the repeater chain through inst (follow BUF/INV drivers upstream): the ribbon's
  # driver side.  Using the nearest driver instead made chains zigzag through an earlier strip repeater.
  for {set g 0} {$g < 64} {incr g} {
    set src ""
    foreach it [$inst getITerms] {
      if {![$it isInputSignal] || [$it getNet] eq "NULL"} { continue }
      set n [$it getNet]
      foreach o [$n getITerms] { if {[$o getInst] ne $inst && [$o isOutputSignal]} { set src [$o getInst] } }
      if {$src eq ""} { foreach bt [$n getBTerms] { return $bt } }
    }
    if {$src eq ""} { return "" }
    if {![regexp {^(BUF|INV|HB)} [[$src getMaster] getName]]} { return $src }
    set inst $src
  }
  return $src
}
proc ot_gap_xy {o dbu} {
  # um location of a dbInst (origin) or a dbBTerm (pin bbox centre)
  if {[catch {$o getLocation} loc]} {
    set b [$o getBBox]
    return [list [expr {([$b xMin] + [$b xMax])/2.0/$dbu}] [expr {([$b yMin] + [$b yMax])/2.0/$dbu}]]
  }
  lassign $loc x y
  return [list [expr {$x/double($dbu)}] [expr {$y/double($dbu)}]]
}
proc ot_gap_axis_dir {inst dbu} {
  # ribbon axis of a repeater (v = N-S, h = E-W) from the bbox of every other pin on its input and output nets,
  # and the driver-side sign along that axis (driver of the input net minus the repeater)
  set xs {}; set ys {}; set drv ""
  lassign [$inst getLocation] lx ly
  set x [expr {$lx/double($dbu)}]; set y [expr {$ly/double($dbu)}]
  foreach it [$inst getITerms] {
    set n [$it getNet]
    if {$n eq "NULL" || [$n getSigType] ne "SIGNAL"} { continue }
    set isin [$it isInputSignal]
    foreach o [$n getITerms] {
      if {[$o getInst] eq $inst} { continue }
      lassign [[$o getInst] getLocation] ox oy
      lappend xs [expr {$ox/double($dbu)}]; lappend ys [expr {$oy/double($dbu)}]
      if {$isin && [$o isOutputSignal]} { set drv [list [expr {$ox/double($dbu)}] [expr {$oy/double($dbu)}]] }
    }
    foreach bt [$n getBTerms] {
      set b [$bt getBBox]
      set px [expr {([$b xMin] + [$b xMax])/2.0/$dbu}]; set py [expr {([$b yMin] + [$b yMax])/2.0/$dbu}]
      lappend xs $px; lappend ys $py
      if {$isin} { set drv [list $px $py] }
    }
  }
  if {![llength $xs]} { return [list v 0] }
  set w [expr {[tcl::mathfunc::max {*}$xs] - [tcl::mathfunc::min {*}$xs]}]
  set h [expr {[tcl::mathfunc::max {*}$ys] - [tcl::mathfunc::min {*}$ys]}]
  set ax [expr {$h >= $w ? "v" : "h"}]
  set s 0
  set src [ot_gap_source $inst]
  if {$src ne ""} { set drv [ot_gap_xy $src $dbu] }
  if {$drv ne ""} {
    lassign $drv dx dy
    set d [expr {$ax eq "v" ? $dy - $y : $dx - $x}]
    set s [expr {$d > 0 ? 1 : ($d < 0 ? -1 : 0)}]
  }
  return [list $ax $s]
}
proc ot_gap_axis_dir_along {inst dbu ax} {
  # driver-side sign of a repeater along a given axis (source register of its chain)
  set src [ot_gap_source $inst]
  if {$src eq ""} { return 0 }
  lassign [ot_gap_xy $src $dbu] sx sy
  lassign [$inst getLocation] lx ly
  set d [expr {$ax eq "v" ? $sy - $ly/double($dbu) : $sx - $lx/double($dbu)}]
  return [expr {$d > 0 ? 1 : ($d < 0 ? -1 : 0)}]
}
proc ot_gap_island_size {inst} {
  # the island repeater drives the whole macro crossing: strong island cell of the same function
  global ot_gap_island_cell
  array set c $ot_gap_island_cell
  set m [[$inst getMaster] getName]
  foreach f {BUF INV} {
    if {[string match ${f}* $m] && $m ne $c($f)} {
      set nm [[ord::get_db] findMaster $c($f)]
      if {$nm ne "NULL"} { $inst swapMaster $nm }
    }
  }
}
proc ot_gap_edge_nudge {k ax x y w h W H} {
  global ot_gap_cores ot_gap_nudge ot_gap_m
  lassign [lindex $ot_gap_cores $k] x0 y0 x1 y1
  set best ""; set bd 1e30
  if {$ax eq "v"} {
    foreach nx [list [expr {$x0 - $w - 0.1}] [expr {$x1 + 0.1}]] {
      set d [expr {abs($nx - $x)}]
      if {$d <= $ot_gap_nudge && $d < $bd && $nx >= $ot_gap_m && $nx + $w <= $W - $ot_gap_m
          && [ot_gap_box_in_core $nx $y [expr {$nx + $w}] [expr {$y + $h}]] < 0} { set best [list $nx $y]; set bd $d }
    }
  } else {
    foreach ny [list [expr {$y0 - $h - 0.1}] [expr {$y1 + 0.1}]] {
      set d [expr {abs($ny - $y)}]
      if {$d <= $ot_gap_nudge && $d < $bd && $ny >= $ot_gap_m && $ny + $h <= $H - $ot_gap_m
          && [ot_gap_box_in_core $x $ny [expr {$x + $w}] [expr {$ny + $h}]] < 0} { set best [list $x $ny]; set bd $d }
    }
  }
  return $best
}
proc ot_gap_slide {ax s x y w h W H} {
  # slide the w x h box at (x, y) along axis ax in direction s (+1/-1) until it clears every core (plus clearance),
  # snapped to rows (v) / sites (h); "" if it leaves the partition core area
  global ot_gap_cores ot_gap_clear ot_gap_m ot_gap_row ot_gap_site
  for {set guard 0} {$guard < 64} {incr guard} {
    set k [ot_gap_box_in_core $x $y [expr {$x + $w}] [expr {$y + $h}]]
    if {$k < 0} { return [list $x $y] }
    lassign [lindex $ot_gap_cores $k] x0 y0 x1 y1
    if {$ax eq "v"} {
      if {$s > 0} {
        set y [expr {$ot_gap_m + ceil(($y1 + $ot_gap_clear - $ot_gap_m)/$ot_gap_row - 1e-6)*$ot_gap_row}]
      } else {
        set y [expr {$ot_gap_m + floor(($y0 - $ot_gap_clear - $h - $ot_gap_m)/$ot_gap_row + 1e-6)*$ot_gap_row}]
      }
      if {$y < $ot_gap_m - 1e-6 || $y + $h > $H - $ot_gap_m + 1e-6} { return "" }
    } else {
      if {$s > 0} {
        set x [expr {$ot_gap_m + ceil(($x1 + $ot_gap_clear - $ot_gap_m)/$ot_gap_site - 1e-6)*$ot_gap_site}]
      } else {
        set x [expr {$ot_gap_m + floor(($x0 - $ot_gap_clear - $w - $ot_gap_m)/$ot_gap_site + 1e-6)*$ot_gap_site}]
      }
      if {$x < $ot_gap_m - 1e-6 || $x + $w > $W - $ot_gap_m + 1e-6} { return "" }
    }
  }
  return ""
}
proc ot_gap_move {stage} {
  # move every repeater created since the last ot_gap_snapshot whose box overlaps an over-routable core to its
  # island (driver side along its ribbon; the other side, then the other axis, only if that side leaves the area)
  global ot_gap_old ot_gap_led ot_gap_pass
  incr ot_gap_pass
  set blk [ord::get_db_block]; set dbu [$blk getDbUnitsPerMicron]
  set da [$blk getDieArea]
  set W [expr {[$da xMax]/double($dbu)}]; set H [expr {[$da yMax]/double($dbu)}]
  set n 0; set fresh 0; set nu 0
  global ot_gap_span_max ot_gap_unrep ot_gap_cores
  foreach i [$blk getInsts] {
    set nm [$i getName]
    if {[info exists ot_gap_old($nm)]} { continue }
    if {![regexp {^(BUF|INV|HB)} [[$i getMaster] getName]]} { continue }
    incr fresh
    set b [$i getBBox]
    set x [expr {[$b xMin]/double($dbu)}]; set y [expr {[$b yMin]/double($dbu)}]
    set w [expr {([$b xMax] - [$b xMin])/double($dbu)}]; set h [expr {([$b yMax] - [$b yMin])/double($dbu)}]
    if {[ot_gap_box_in_core $x $y [expr {$x + $w}] [expr {$y + $h}]] < 0} { continue }
    set k [ot_gap_box_in_core $x $y [expr {$x + $w}] [expr {$y + $h}]]
    lassign [ot_gap_axis_dir $i $dbu] ax s
    set open [ot_gap_open_axes $k]
    if {[string length $open] == 1 && $ax ne $open} {
      # the net's long side cannot cross this core on the open layers: the ribbon runs along the open axis
      set ax $open
      lassign [ot_gap_axis_dir_along $i $dbu $ax] s
    }
    if {$s == 0} { set s -1 }
    # island cell first, so the site is computed for the cell that will sit there
    set m0 [$i getMaster]
    ot_gap_island_size $i
    set b [$i getBBox]
    set w [expr {([$b xMax] - [$b xMin])/double($dbu)}]; set h [expr {([$b yMax] - [$b yMin])/double($dbu)}]
    # a ribbon that runs along a core edge (the repeater only overlaps the core by its own width): step off the
    # edge across the ribbon (<= ot_gap_nudge um, stays on the ribbon line) instead of sliding along it
    set to [ot_gap_edge_nudge $k $ax $x $y $w $h $W $H]
    lassign [lindex $ot_gap_cores $k] cx0 cy0 cx1 cy1
    set span [expr {$ax eq "v" ? $cy1 - $cy0 : $cx1 - $cx0}]
    if {$to eq "" && $span > $ot_gap_span_max} {
      $i swapMaster $m0
      incr ot_gap_unrep; incr nu
      continue
    }
    if {$to eq ""} { set to [ot_gap_slide $ax $s $x $y $w $h $W $H] }
    if {$to eq ""} { set to [ot_gap_slide $ax [expr {-$s}] $x $y $w $h $W $H] }
    if {$to eq ""} {
      set ax2 [expr {$ax eq "v" ? "h" : "v"}]
      set to [ot_gap_slide $ax2 1 $x $y $w $h $W $H]
      if {$to eq ""} { set to [ot_gap_slide $ax2 -1 $x $y $w $h $W $H] }
    }
    if {$to eq ""} { error "OT_GAP no legal island site for $nm at ($x, $y)" }
    lassign $to nx ny
    $i setLocation [expr {round($nx*$dbu)}] [expr {round($ny*$dbu)}]
    $i setPlacementStatus PLACED
    set ot_gap_led($nm) [list $x $y $ax $s $stage $ot_gap_pass]
    incr n
  }
  puts "OT_GAP pass $ot_gap_pass ($stage) moved $n of $fresh new repeaters from over-routable cores to islands"
  if {$nu} { puts "OT_GAP_UNREPEATABLE pass $ot_gap_pass $nu repeaters on crossings longer than $ot_gap_span_max um (left to DPL)" }
  return $n
}
proc ot_gap_repair {rargs} {
  # placement stage: one repair_design pass on placement RC, islands, DPL
  ot_gap_snapshot
  repair_design {*}$rargs
  ot_gap_move place
  detailed_placement -max_displacement {400 400}
}
proc ot_gap_repair_grt {rargs eargs {max_pass 8}} {
  # global-route stage (ORFS global_route.tcl order: GRT parasitics -> repair_design -> incremental GRT of the
  # changed nets), repeated while a pass still puts new repeaters into a core
  for {set p 1} {$p <= $max_pass} {incr p} {
    estimate_parasitics -global_routing
    ot_gap_snapshot
    repair_design {*}$rargs
    global_route -start_incremental
    set n [ot_gap_move grt]
    detailed_placement -max_displacement {400 400}
    global_route -end_incremental {*}$eargs
    if {$n == 0} { break }
  }
  estimate_parasitics -global_routing
  puts "OT_GAP_GRT_PASSES $p"
}
proc ot_gap_check {{max_dev 4.0} {ledger /work/gap_repeaters.tsv}} {
  # PASS = every island repeater ends outside every over-routable core and within max_dev um of its ribbon line
  # (|dx| for a N-S ribbon, |dy| for an E-W ribbon).  Ledger: dx AND dy from the resizer's site, axis, stage, pass.
  global ot_gap_led
  set blk [ord::get_db_block]; set dbu [$blk getDbUnitsPerMicron]
  set bad {}; set mdx 0.0; set mdy 0.0; set mdev 0.0; set fh [open $ledger w]
  puts $fh "inst\tmaster\taxis\tdrv_side\tstage\tpass\tx0\ty0\tx\ty\tdx\tdy\tribbon_dev\tin_core\tok"
  foreach nm [lsort [array names ot_gap_led]] {
    lassign $ot_gap_led($nm) x0 y0 ax s st ps
    set i [$blk findInst $nm]
    if {$i eq "NULL"} { lappend bad "$nm:missing"; continue }
    set b [$i getBBox]
    set x [expr {[$b xMin]/double($dbu)}]; set y [expr {[$b yMin]/double($dbu)}]
    set dx [expr {$x - $x0}]; set dy [expr {$y - $y0}]
    set dev [expr {$ax eq "v" ? abs($dx) : abs($dy)}]
    if {abs($dx) > $mdx} { set mdx [expr {abs($dx)}] }
    if {abs($dy) > $mdy} { set mdy [expr {abs($dy)}] }
    if {$dev > $mdev} { set mdev $dev }
    set inc [expr {[ot_gap_box_in_core $x $y [expr {[$b xMax]/double($dbu)}] [expr {[$b yMax]/double($dbu)}]] >= 0}]
    set ok [expr {!$inc && $dev <= $max_dev}]
    puts $fh [format "%s\t%s\t%s\t%d\t%s\t%d\t%.3f\t%.3f\t%.3f\t%.3f\t%.3f\t%.3f\t%.3f\t%d\t%d" $nm \
      [[$i getMaster] getName] $ax $s $st $ps $x0 $y0 $x $y $dx $dy $dev $inc $ok]
    if {!$ok} { lappend bad [format "%s:x=%.3f,y=%.3f,dev=%.3f,in_core=%d" $nm $x $y $dev $inc] }
  }
  close $fh
  # repeaters in cores that were never moved (would mean a resizer call outside these procs)
  set stray 0
  foreach i [$blk getInsts] {
    if {![regexp {^(BUF|INV|HB)} [[$i getMaster] getName]]} { continue }
    set b [$i getBBox]
    if {[ot_gap_box_in_core [expr {[$b xMin]/double($dbu)}] [expr {[$b yMin]/double($dbu)}] \
          [expr {[$b xMax]/double($dbu)}] [expr {[$b yMax]/double($dbu)}]] >= 0} { incr stray }
  }
  if {$stray} { lappend bad "stray_in_core:$stray" }
  if {[llength $bad]} {
    puts "OT_GAP_FAIL [llength $bad] of [array size ot_gap_led] island repeaters inside a core or off the ribbon: [lrange $bad 0 9]"
  } else {
    puts [format "OT_GAP_PASS %d repeaters in gap rows, max |dx| %.3f um, max |dy| %.3f um, max ribbon dev %.3f um" \
      [array size ot_gap_led] $mdx $mdy $mdev]
  }
}
proc ot_drv_classify {rpt out} {
  # split a report_check_types -violators file into port pins, port legs (pin on a net with a top-level port: the
  # die-level hop to the neighbour's first station) and INTERNAL pins (everything else)
  set blk [ord::get_db_block]
  set fi [open $rpt r]; set fo [open $out w]
  puts $fo "check\tpin\tlimit\tvalue\tslack\tclass"
  set chk ""
  while {[gets $fi ln] >= 0} {
    if {[regexp {^max slew} $ln]} { set chk slew; continue }
    if {[regexp {^max capacitance} $ln]} { set chk cap; continue }
    if {[regexp {^max fanout} $ln]} { set chk fanout; continue }
    if {![regexp {^(\S+)\s+([-0-9.]+)\s+([-0-9.]+)\s+([-0-9.]+)\s+\(VIOLATED\)} $ln -> pin lim val slk]} { continue }
    set cls port_pin
    if {[string first / $pin] >= 0} {
      set cls internal
      set it [$blk findITerm $pin]
      if {$it ne "NULL" && [$it getNet] ne "NULL" && [llength [[$it getNet] getBTerms]]} { set cls port_leg }
    }
    puts $fo "$chk\t$pin\t$lim\t$val\t$slk\t$cls"
  }
  close $fi; close $fo
}
