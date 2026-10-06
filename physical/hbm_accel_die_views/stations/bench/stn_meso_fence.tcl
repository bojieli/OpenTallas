# POST_FLOORPLAN hook for the CLAUDE HBM-ABSTRACTS station views that hold a mesochronous crossing (stn_route.sh
# FENCE=1).  The closed ot_meso_fifo contract (results/uarch/meso_fifo_20261004 meso_d4_v6/v7) times its
# wclk -> rclk crossing (ring slot -> one-hot read select -> receive register, 356.667 ps ignoring latency) on a compact
# ~30 % utilisation square.  A station outline is the r16g die slot: long and sparse (meso_r32 39 x 285 um, 24 %), the
# FIFO's I/O ends sit on opposite faces, and global placement spreads the ring and the receive buffer along the whole
# length, so the crossing alone carries a 100+ um wire (routed SS -5 .. -83 ps, r4/r5).  This hook gives each FIFO
# u_meso<k> an INCLUSIVE region at OT_FENCE_DENSITY (default 0.45) of its own cell area, spanning the outline's
# short side, centred between the terminals that feed it and the terminals it drives (OT_FENCE_POS; block centre
# when either set is empty), so the crossing stays as compact as in the contract and the I/O legs carry the distance.
# Membership: the FIFO's named cells (flops, kept select cells: u_meso<k>.*).  Synthesis renames the combinational
# cells (ABC) and a receive register that drives a block terminal ("b[158]$_DFF_P_"), so a sequential cell that
# drives a terminal joins the group whose named cells reach its inputs through at most OT_DEPTH (4) unnamed cells.
# Terminals: inputs that reach a group forwards within OT_DEPTH cells; outputs of the group's terminal registers.
# ORFS sources step hooks inside a proc: the tables the helper procs read must be true globals
global ot_pin ot_grp
set ot_dens [expr {[info exists ::env(OT_FENCE_DENSITY)] ? $::env(OT_FENCE_DENSITY) : 0.45}]
set ot_depth [expr {[info exists ::env(OT_DEPTH)] ? $::env(OT_DEPTH) : 4}]
# OT_FENCE_POS: region centre as a fraction of the way from the feeding terminals' centroid to the driven ones' (the
# input leg is a half-period arc: forwarded data captured on the falling edge; the output leg has a full period)
set ot_pos [expr {[info exists ::env(OT_FENCE_POS)] ? $::env(OT_FENCE_POS) : 0.5}]
set ot_blk [ord::get_db_block]
set ot_dbu [$ot_blk getDbUnitsPerMicron]
set ot_core [$ot_blk getCoreArea]
set cx0 [$ot_core xMin]; set cy0 [$ot_core yMin]; set cx1 [$ot_core xMax]; set cy1 [$ot_core yMax]
array set ot_pin {}
# (ORFS erases IO_CONSTRAINTS in the floorplan stage, so stn_route.sh passes the same file as OT_IO_FILE)
set ot_iof [expr {[info exists ::env(OT_IO_FILE)] ? $::env(OT_IO_FILE) : ([info exists ::env(IO_CONSTRAINTS)] ? $::env(IO_CONSTRAINTS) : "")}]
if {$ot_iof ne "" && [file exists $ot_iof]} {
  set fh [open $ot_iof]; set txt [read $fh]; close $fh
  foreach {m nm x y} [regexp -all -inline {place_pin -pin_name \{([^\}]+)\} -layer \S+ -location \{(\S+) (\S+)\}} $txt] {
    set ot_pin($nm) [list [expr {round($x*$ot_dbu)}] [expr {round($y*$ot_dbu)}]]
  }
}
array set ot_mem {}; array set ot_grp {}
foreach i [$ot_blk getInsts] {
  if {[regexp {^(u_meso[0-9]+)\.} [$i getName] -> g]} { lappend ot_mem($g) $i; set ot_grp([$i getName]) $g }
}
proc ot_isseq {i} { return [[$i getMaster] isSequential] }
proc ot_skip {n} { return [expr {$n eq "NULL" || [$n getSigType] in {POWER GROUND CLOCK RESET}}] }
proc ot_back {i depth} {
  global ot_grp
  if {$depth < 0} { return "" }
  foreach it [$i getITerms] {
    if {[$it isOutputSignal]} continue
    set n [$it getNet]; if {[ot_skip $n]} continue
    foreach d [$n getITerms] {
      if {![$d isOutputSignal]} continue
      set di [$d getInst]
      if {[info exists ot_grp([$di getName])]} { return $ot_grp([$di getName]) }
      if {![ot_isseq $di]} { set g [ot_back $di [expr {$depth-1}]]; if {$g ne ""} { return $g } }
    }
  }
  return ""
}
proc ot_fwd {n depth} {
  global ot_grp
  if {$depth < 0} { return "" }
  foreach it [$n getITerms] {
    if {[$it isOutputSignal]} continue
    set di [$it getInst]
    if {[info exists ot_grp([$di getName])]} { return $ot_grp([$di getName]) }
    if {![ot_isseq $di]} {
      foreach o [$di getITerms] {
        if {![$o isOutputSignal]} continue
        set on [$o getNet]; if {[ot_skip $on]} continue
        set g [ot_fwd $on [expr {$depth-1}]]; if {$g ne ""} { return $g }
      }
    }
  }
  return ""
}
proc ot_toport {n depth} {
  # terminal positions a net reaches directly or through at most depth combinational cells (QN flop -> inverter)
  global ot_pin
  set pins {}
  foreach bt [$n getBTerms] { if {[info exists ot_pin([$bt getName])]} { lappend pins $ot_pin([$bt getName]) } }
  if {$depth > 0} {
    foreach it [$n getITerms] {
      if {[$it isOutputSignal]} continue
      set di [$it getInst]; if {[ot_isseq $di]} continue
      foreach o [$di getITerms] {
        if {![$o isOutputSignal]} continue
        set on [$o getNet]; if {[ot_skip $on]} continue
        set pins [concat $pins [ot_toport $on [expr {$depth-1}]]]
      }
    }
  }
  return $pins
}
array set ot_outs {}; array set ot_ins {}
foreach i [$ot_blk getInsts] {
  if {![ot_isseq $i]} continue
  set pins {}
  foreach it [$i getITerms] {
    if {![$it isOutputSignal]} continue
    set n [$it getNet]; if {[ot_skip $n]} continue
    set pins [concat $pins [ot_toport $n 2]]
  }
  if {![llength $pins]} continue
  if {[info exists ot_grp([$i getName])]} {
    foreach p $pins { lappend ot_outs($ot_grp([$i getName])) $p }
    continue
  }
  set g [ot_back $i $ot_depth]
  if {$g ne ""} { lappend ot_mem($g) $i; foreach p $pins { lappend ot_outs($g) $p } }
}
foreach bt [$ot_blk getBTerms] {
  if {[$bt getIoType] ne "INPUT" || ![info exists ot_pin([$bt getName])]} continue
  set n [$bt getNet]; if {[ot_skip $n]} continue
  set g [ot_fwd $n $ot_depth]
  if {$g ne ""} { lappend ot_ins($g) $ot_pin([$bt getName]) }
}
proc ot_cent {l} {
  set sx 0; set sy 0
  foreach p $l { set sx [expr {$sx+[lindex $p 0]}]; set sy [expr {$sy+[lindex $p 1]}] }
  return [list [expr {$sx/[llength $l]}] [expr {$sy/[llength $l]}]]
}
if {![array size ot_pin]} { error "OT_STN fence: no terminal positions (OT_IO_FILE '$ot_iof')" }
# One fence holds every FIFO of the view: a view's FIFOs are parallel lanes between the same faces (meso_r1: three
# lanes E -> W), and separate regions would overlap.  Its centre is the area-weighted mean of the per-FIFO centres.
set area 0.0; set wx 0.0; set wy 0.0; set nin 0; set nout 0; set all {}
foreach g [lsort [array names ot_mem]] {
  set ins [expr {[info exists ot_ins($g)] ? $ot_ins($g) : {}}]
  set outs [expr {[info exists ot_outs($g)] ? $ot_outs($g) : {}}]
  set ga 0.0
  foreach i $ot_mem($g) { set ga [expr {$ga + double([[$i getMaster] getWidth])*[[$i getMaster] getHeight]}] }
  set mid [list [expr {($cx0+$cx1)/2}] [expr {($cy0+$cy1)/2}]]
  if {[llength $ins] && [llength $outs]} {
    set a [ot_cent $ins]; set b [ot_cent $outs]
    set mid [list [expr {[lindex $a 0]+$ot_pos*([lindex $b 0]-[lindex $a 0])}] [expr {[lindex $a 1]+$ot_pos*([lindex $b 1]-[lindex $a 1])}]]
  }
  puts [format "OT_STN: fifo %s %d cells %.1f um2, %d in / %d out terminals, centre (%.2f %.2f) um" $g [llength $ot_mem($g)] \
        [expr {$ga/$ot_dbu/$ot_dbu}] [llength $ins] [llength $outs] [expr {[lindex $mid 0]/double($ot_dbu)}] [expr {[lindex $mid 1]/double($ot_dbu)}]]
  set area [expr {$area+$ga}]; set wx [expr {$wx+$ga*[lindex $mid 0]}]; set wy [expr {$wy+$ga*[lindex $mid 1]}]
  set nin [expr {$nin+[llength $ins]}]; set nout [expr {$nout+[llength $outs]}]; set all [concat $all $ot_mem($g)]
}
if {[llength $all]} {
  set mid [list [expr {$wx/$area}] [expr {$wy/$area}]]
  set need [expr {$area / $ot_dens}]
  set W [expr {$cx1-$cx0}]; set H [expr {$cy1-$cy0}]
  if {$H >= $W} {
    set rw $W; set rh [expr {min($H, $need / $W)}]
    set rx0 $cx0; set ry0 [expr {max($cy0, min($cy1-$rh, [lindex $mid 1]-$rh/2))}]
  } else {
    set rh $H; set rw [expr {min($W, $need / $H)}]
    set ry0 $cy0; set rx0 [expr {max($cx0, min($cx1-$rw, [lindex $mid 0]-$rw/2))}]
  }
  set rx0 [expr {round($rx0)}]; set ry0 [expr {round($ry0)}]
  set rx1 [expr {round($rx0+$rw)}]; set ry1 [expr {round($ry0+$rh)}]
  set r [odb::dbRegion_create $ot_blk "ot_fence_meso"]
  odb::dbBox_create $r $rx0 $ry0 $rx1 $ry1
  $r setRegionType INCLUSIVE
  # global placement places a region's cells through a group bound to it (a region alone only constrains the
  # legaliser, which then drags the cells there after an unconstrained global placement: r8, 3x wirelength)
  set grp [odb::dbGroup_create $r "ot_fence_grp_meso"]
  foreach i $all { $grp addInst $i }
  puts [format "OT_STN: fence %d FIFO(s) %d cells %.1f um2 at %.2f -> (%.2f %.2f %.2f %.2f) um, %d in / %d out terminals" \
        [array size ot_mem] [llength $all] [expr {$area/$ot_dbu/$ot_dbu}] $ot_dens [expr {$rx0/double($ot_dbu)}] \
        [expr {$ry0/double($ot_dbu)}] [expr {$rx1/double($ot_dbu)}] [expr {$ry1/double($ot_dbu)}] $nin $nout]
}
