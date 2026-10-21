# QW-CB16REG 10-20 (fallback b): cluster-root regional clock distribution for the 16 region clocks of the flat CB16 parent
# (generalises tools/qwen_romleaf/rc12/ck_km_split.tcl + ck_km_cts_nets.tcl, claude/qw-a0-rc12-1020 ca5efcb2e).
# Why (measured, fulln/fullnb/fullm gates 10-20, scratch/qw-cb16r/ev_*): one TritonCTS tree per region root over its
# 6.7k-20.9k register sinks left WITHIN-region TT spread 410-813 ps (insertion 1.3-2.7 ns, avg sink wire 1.3-2.7 mm) and
# post-CTS setup WNS -1.4..-1.7 ns at the landing readers (bank on the source root -> read register on the destination root).
# Change (buffers only; same RTL, ports, clocks, flops, SDC, fences, cycles):
#  (1) every region port's REGISTER sinks are split into K compact 2-D k-means clusters (K = clamp(ceil(N / OT_CB16KM_PER),
#      OT_CB16KM_KMIN, OT_CB16KM_KMAX)), one BUFx24 local root at each centroid; hard-child clock pins stay on the port net;
#  (2) clock_tree_synthesis gets -clk_nets = the 16 port nets + every cluster net (one short tree per cluster);
#  (3) after CTS, the latest arrival of every cluster (STA, placement parasitics, propagated clocks, calibrated clock RC when
#      available) and of every hard-child clock pin (+ its recorded TT child insertion) is MEASURED in ONE pass for all
#      ports, and early groups get pad cells in front of their root (coarse HB4xp67, then fine BUFx2; per-pad delay learned
#      from the previous round).  Target per port = its latest group; with OT_CB16KM_GLOBAL=1 (default) every port is padded
#      to the latest group of ALL ports, so the single-cycle landing-ring read paths between regions see aligned roots.
# Knobs: OT_CB16KM_PORTS (regex, ^ck_c[0-3]r[0-3]$), OT_CB16KM_PER (500), OT_CB16KM_KMIN (12), OT_CB16KM_KMAX (40),
#        OT_CB16KM_ITERS (25), OT_CB16KM_ITERS_BAL (10), OT_CB16KM_TOL_PS (20), OT_CB16KM_GLOBAL (1), OT_CB16KM_DMAX (250 um).
proc ot_cbk_env {n d} { if {[info exists ::env($n)] && $::env($n) ne ""} { return $::env($n) }; return $d }
# recorded TT child insertion (views/*/insertion.json tt.all.mean; A0 stand-in per pin) -- added to a hard-child pin arrival
set ::ot_cbk_ins [dict create qfd_c_stn514 96.6 qfd_c_stn516 95.7 qfd_c_xstn_safe 141.9 qfd_c_xstnw_safe 137.8 \
  qfd_tile_nk_rp2_romleaf_rr 174.5 qfd_tile_nl_rp2_romleaf_rr 174.5]
set ::ot_cbk_ins_pin [dict create ck_node 243.1 ck 190.5 ck_tx3 202.0 ck_tx4 219.4 ck_tx5 214.1 \
  ck_lsl0 165.3 ck_lsl1 165.3 ck_lsl2 165.3 ck_lsl3 165.3 ck_lsl4 165.3 ck_lsl5 165.3 ck_lsl6 165.3 ck_lsl7 165.3 \
  ck_rp0 201.5 ck_rp1 201.5 ck_rp2 201.5 ck_rp3 201.5 ck_rp4 201.5 ck_rp5 201.5 ck_rp6 201.5 ck_rp7 201.5 ck_rp8 201.5 ck_rp9 201.5]
proc ot_cbk_child_ins {it} {
  set m [[$it getInst] getMaster]; set mn [$m getName]; set pn [[$it getMTerm] getName]
  if {[string match qfd_tile_n?_rp2_romleaf_rr $mn]} {
    if {[dict exists $::ot_cbk_ins_pin $pn]} { return [dict get $::ot_cbk_ins_pin $pn] }
    return 150.0
  }
  if {[dict exists $::ot_cbk_ins $mn]} { return [dict get $::ot_cbk_ins $mn] }
  return 0.0
}
proc ot_cbk_split {port} {
  set blk [ord::get_db_block]
  if {[$blk findInst ot_cbk_${port}_0] ne "NULL"} { return }
  set u [[ord::get_db_tech] getDbUnitsPerMicron]
  set bt [$blk findBTerm $port]
  if {$bt eq "NULL"} { error "CB16KM: no $port port" }
  set pnet [$bt getNet]
  set xs {}; set ys {}; set its {}; set nmac 0
  foreach it [$pnet getITerms] {
    if {![$it isInputSignal]} continue
    if {[[[$it getInst] getMaster] isBlock]} { incr nmac; continue }
    set l [[$it getInst] getLocation]
    lappend xs [expr {[lindex $l 0] / double($u)}]; lappend ys [expr {[lindex $l 1] / double($u)}]; lappend its $it
  }
  set N [llength $its]
  set K [expr {int(ceil($N / double([ot_cbk_env OT_CB16KM_PER 500])))}]
  set K [expr {max([ot_cbk_env OT_CB16KM_KMIN 12], min([ot_cbk_env OT_CB16KM_KMAX 40], $K))}]
  if {$N < 2 * $K} { puts "CB16KM: $port only $N register sinks, not split"; return }
  set iters [ot_cbk_env OT_CB16KM_ITERS 25]
  set mx 0.0; set my 0.0
  foreach x $xs y $ys { set mx [expr {$mx + $x}]; set my [expr {$my + $y}] }
  set mx [expr {$mx / $N}]; set my [expr {$my / $N}]
  set ang {}
  for {set i 0} {$i < $N} {incr i} { lappend ang [list [expr {atan2([lindex $ys $i] - $my, [lindex $xs $i] - $mx)}] $i] }
  set ang [lsort -real -index 0 $ang]
  set cx {}; set cy {}
  for {set k 0} {$k < $K} {incr k} {
    set lo [expr {($N * $k) / $K}]; set hi [expr {($N * ($k + 1)) / $K - 1}]
    set sx 0.0; set sy 0.0
    foreach e [lrange $ang $lo $hi] { set i [lindex $e 1]; set sx [expr {$sx + [lindex $xs $i]}]; set sy [expr {$sy + [lindex $ys $i]}] }
    set n [expr {$hi - $lo + 1}]
    lappend cx [expr {$sx / $n}]; lappend cy [expr {$sy / $n}]
  }
  set asg [lrepeat $N 0]; set sn [lrepeat $K 0]
  for {set r 0} {$r < $iters} {incr r} {
    set moved 0
    for {set i 0} {$i < $N} {incr i} {
      set x [lindex $xs $i]; set y [lindex $ys $i]; set best 0; set bd 1e30
      for {set k 0} {$k < $K} {incr k} {
        set d [expr {abs($x - [lindex $cx $k]) + abs($y - [lindex $cy $k])}]
        if {$d < $bd} { set bd $d; set best $k }
      }
      if {[lindex $asg $i] != $best} { lset asg $i $best; incr moved }
    }
    set sx [lrepeat $K 0.0]; set sy [lrepeat $K 0.0]; set sn [lrepeat $K 0]
    for {set i 0} {$i < $N} {incr i} {
      set k [lindex $asg $i]
      lset sx $k [expr {[lindex $sx $k] + [lindex $xs $i]}]; lset sy $k [expr {[lindex $sy $k] + [lindex $ys $i]}]
      lset sn $k [expr {[lindex $sn $k] + 1}]
    }
    for {set k 0} {$k < $K} {incr k} {
      if {[lindex $sn $k] > 0} { lset cx $k [expr {[lindex $sx $k] / [lindex $sn $k]}]; lset cy $k [expr {[lindex $sy $k] / [lindex $sn $k]}] }
    }
    if {$r > 0 && $moved == 0} break
  }
  # groups = k-means clusters, then any group wider than OT_CB16KM_DMAX (half-perimeter, um) is bisected along its longer
  # axis until it fits (sparse scalar control / reset runs spread along a column; smoke on fulln 3_place: 25 of 402
  # k-means clusters spanned 500-1488 um with 3-24 sinks)
  set dmaxlim [ot_cbk_env OT_CB16KM_DMAX 250]
  set todo {}
  for {set k 0} {$k < $K} {incr k} { set mem($k) {} }
  for {set i 0} {$i < $N} {incr i} { lappend mem([lindex $asg $i]) $i }
  for {set k 0} {$k < $K} {incr k} { if {[llength $mem($k)]} { lappend todo $mem($k) } }
  set groups {}
  while {[llength $todo]} {
    set g [lindex $todo 0]; set todo [lrange $todo 1 end]
    set gx [lsort -real [lmap i $g {lindex $xs $i}]]; set gy [lsort -real [lmap i $g {lindex $ys $i}]]
    set wx [expr {[lindex $gx end] - [lindex $gx 0]}]; set wy [expr {[lindex $gy end] - [lindex $gy 0]}]
    if {$wx + $wy <= $dmaxlim || [llength $g] < 2} { lappend groups $g; continue }
    set ax [expr {$wx >= $wy ? $xs : $ys}]
    set srt [lsort -real -index 0 [lmap i $g {list [lindex $ax $i] $i}]]
    set h [expr {[llength $srt] / 2}]
    lappend todo [lmap e [lrange $srt 0 [expr {$h - 1}]] {lindex $e 1}] [lmap e [lrange $srt $h end] {lindex $e 1}]
  }
  set m [[ord::get_db] findMaster BUFx24_ASAP7_75t_R]
  set dmax 0.0; set k 0
  foreach g $groups {
    set gx [lsort -real [lmap i $g {lindex $xs $i}]]; set gy [lsort -real [lmap i $g {lindex $ys $i}]]
    set cxk [expr {([tcl::mathop::+ {*}$gx]) / [llength $g]}]; set cyk [expr {([tcl::mathop::+ {*}$gy]) / [llength $g]}]
    set b [odb::dbInst_create $blk $m ot_cbk_${port}_$k]
    $b setLocation [expr {int($cxk * $u)}] [expr {int($cyk * $u)}]; $b setPlacementStatus PLACED
    set net [odb::dbNet_create $blk ot_cbk_${port}_${k}_clk]; $net setSigType CLOCK
    [$b findITerm A] connect $pnet; [$b findITerm Y] connect $net
    foreach i $g { set it [lindex $its $i]; $it disconnect; $it connect $net }
    set d [expr {[lindex $gx end] - [lindex $gx 0] + [lindex $gy end] - [lindex $gy 0]}]
    if {$d > $dmax} { set dmax $d }
    puts [format "CB16KM: %s cluster %d %d sinks x %.1f..%.1f y %.1f..%.1f root (%.1f, %.1f)" $port $k [llength $g] \
      [lindex $gx 0] [lindex $gx end] [lindex $gy 0] [lindex $gy end] $cxk $cyk]
    incr k
  }
  set K $k
  puts [format "CB16KM: %s %d register sinks -> %d clusters (max half-perimeter %.1f um), %d hard-child clock pins stay on the port net" $port $N $K $dmax $nmac]
}
proc ot_cbk_ports {} {
  set re [ot_cbk_env OT_CB16KM_PORTS {^ck_c[0-3]r[0-3]$}]
  set out {}
  foreach bt [[ord::get_db_block] getBTerms] { if {[regexp $re [$bt getName]]} { lappend out [$bt getName] } }
  return [lsort $out]
}
proc ot_cbk_leafnets {net} {
  set out {}; set todo [list $net]; set seen [dict create]
  while {[llength $todo]} {
    set n [lindex $todo 0]; set todo [lrange $todo 1 end]
    if {[dict exists $seen [$n getName]]} continue
    dict set seen [$n getName] 1
    set leaf 0
    foreach it [$n getITerms] {
      if {![$it isInputSignal]} continue
      set m [[$it getInst] getMaster]
      if {[$m isSequential] || [$m isBlock]} { set leaf 1; continue }
      foreach o [[$it getInst] getITerms] { if {[$o isOutputSignal] && [$o getNet] ne "NULL"} { lappend todo [$o getNet] } }
    }
    if {$leaf} { lappend out [$n getName] }
  }
  return $out
}
# groups: cluster root inst name -> {port leafnets}; hard-child clock pin "inst/pin" -> {port ins}
proc ot_cbk_groups {} {
  set blk [ord::get_db_block]
  set ::ot_cbk_cl [dict create]; set ::ot_cbk_hc [dict create]
  foreach inst [$blk getInsts] {
    if {![regexp {^ot_cbk_(ck_c[0-9]+r[0-9]+)_([0-9]+)$} [$inst getName] -> port k]} continue
    dict set ::ot_cbk_cl [$inst getName] [list $port [ot_cbk_leafnets [[$inst findITerm Y] getNet]]]
  }
  foreach port [ot_cbk_ports] {
    foreach ln [ot_cbk_leafnets [[$blk findBTerm $port] getNet]] {
      foreach it [[$blk findNet $ln] getITerms] {
        if {![$it isInputSignal] || ![[[$it getInst] getMaster] isBlock]} continue
        dict set ::ot_cbk_hc "[[$it getInst] getName]/[[$it getMTerm] getName]" [list $port [ot_cbk_child_ins $it]]
      }
    }
  }
}
proc ot_cbk_arrivals {} {
  estimate_parasitics -placement
  sta::find_timing_paths -path_delay max -group_path_count 1
  set a [dict create]
  dict for {b pl} $::ot_cbk_cl {
    set v 0.0
    foreach ln [lindex $pl 1] {
      foreach pin [get_pins -quiet -of_objects [get_nets -quiet $ln] -filter "direction==input"] {
        set x [get_property $pin arrival_max_rise]
        if {$x ne "" && $x ne "INF" && $x ne "-INF" && $x > $v} { set v $x }
      }
    }
    dict set a $b $v
  }
  dict for {p pl} $::ot_cbk_hc {
    set pin [get_pins -quiet $p]; set v 0.0
    if {[llength $pin]} { set x [get_property $pin arrival_max_rise]; if {$x ne "" && $x ne "INF" && $x ne "-INF"} { set v $x } }
    dict set a $p [expr {$v + [lindex $pl 1]}]
  }
  return $a
}
# insert count pads (master) in front of a group: a cluster root's A pin or a hard-child clock pin
proc ot_cbk_pad {g count master} {
  set blk [ord::get_db_block]
  if {[dict exists $::ot_cbk_cl $g]} { set inst [$blk findInst $g]; set ait [$inst findITerm A] } else {
    lassign [split $g /] iname pname; set inst [$blk findInst $iname]; set ait [$inst findITerm $pname]
  }
  set net [$ait getNet]
  lassign [$inst getLocation] lx ly
  if {![dict exists $::ot_cbk_cl $g]} {
    # hard child: put the pads at the clock pin, not at the macro origin
    set bb [$ait getBBox]; set lx [expr {([$bb xMin] + [$bb xMax]) / 2}]; set ly [expr {([$bb yMin] + [$bb yMax]) / 2}]
  }
  $ait disconnect
  for {set i 0} {$i < $count} {incr i} {
    set p [incr ::ot_cbk_npad]
    set c [odb::dbInst_create $blk $master ot_cbk_pad_$p]
    $c setLocation $lx $ly; $c setPlacementStatus PLACED
    set nn [odb::dbNet_create $blk ot_cbk_pad_${p}_clk]; $nn setSigType CLOCK
    foreach it [$c getITerms] { if {[$it isInputSignal]} { $it connect $net } elseif {[$it isOutputSignal]} { $it connect $nn } }
    set net $nn
  }
  $ait connect $net
}
proc ot_cbk_balance {} {
  ot_cbk_groups
  set ::ot_cbk_npad 0
  if {![dict size $::ot_cbk_cl]} return
  set_propagated_clock [all_clocks]
  set rcc 0
  if {[llength [info commands ot_rc_cal_apply]]} { set rcc [ot_rc_cal_apply cb16km] }
  set iters [ot_cbk_env OT_CB16KM_ITERS_BAL 10]; set tol [ot_cbk_env OT_CB16KM_TOL_PS 20]
  set glob [ot_cbk_env OT_CB16KM_GLOBAL 1]
  set stage 45.0; set fstage 12.0; set mode coarse; set prev ""; set padded [dict create]
  set port_of [dict create]
  dict for {g pl} $::ot_cbk_cl { dict set port_of $g [lindex $pl 0] }
  dict for {g pl} $::ot_cbk_hc { dict set port_of $g [lindex $pl 0] }
  set mc [[ord::get_db] findMaster HB4xp67_ASAP7_75t_R]; set mf [[ord::get_db] findMaster BUFx2_ASAP7_75t_R]
  for {set it 0} {$it <= $iters} {incr it} {
    set a [ot_cbk_arrivals]
    # per-port spread report + target
    set pmax [dict create]; set pmin [dict create]
    dict for {g v} $a {
      set p [dict get $port_of $g]
      if {![dict exists $pmax $p] || $v > [dict get $pmax $p]} { dict set pmax $p $v }
      if {![dict exists $pmin $p] || $v < [dict get $pmin $p]} { dict set pmin $p $v }
    }
    set gmax [tcl::mathfunc::max {*}[dict values $pmax]]; set gmin [tcl::mathfunc::min {*}[dict values $pmin]]
    set worst 0.0
    dict for {p mx} $pmax {
      set sp [expr {$mx - [dict get $pmin $p]}]; if {$sp > $worst} { set worst $sp }
      puts [format "OT_CB16KM balance iter %d %s latest %.1f..%.1f ps (spread %.1f)" $it $p [dict get $pmin $p] $mx $sp]
    }
    if {$prev ne "" && [dict size $padded]} {
      set gl {}
      dict for {g c} $padded { lappend gl [expr {([dict get $a $g] - [dict get $prev $g]) / double($c)}] }
      set gl [lsort -real $gl]; set m [lindex $gl [expr {[llength $gl] / 2}]]
      if {$m < 3.0} { set m 3.0 }
      if {$mode eq "coarse"} { set stage $m } else { set fstage $m }
    }
    set allsp [expr {$gmax - $gmin}]
    puts [format "OT_CB16KM balance iter %d (%s) groups %d all-port %.1f..%.1f (spread %.1f) worst in-port %.1f pad %.1f / %.1f ps pads %d" \
      $it $mode [dict size $a] $gmin $gmax $allsp $worst $stage $fstage $::ot_cbk_npad]
    set crit [expr {$glob ? $allsp : $worst}]
    if {$it == $iters || $crit <= $tol} break
    if {$mode eq "coarse" && $crit < 1.6 * $stage} { set mode fine }
    set st [expr {$mode eq "coarse" ? $stage : $fstage}]
    set prev $a; set padded [dict create]
    dict for {g v} $a {
      set tgt [expr {$glob ? $gmax : [dict get $pmax [dict get $port_of $g]]}]
      set c [expr {int(floor(($tgt - $v - 0.5 * $tol) / $st))}]
      if {$c > 0} { ot_cbk_pad $g $c [expr {$mode eq "coarse" ? $mc : $mf}]; dict set padded $g $c }
    }
    if {![dict size $padded]} break
  }
  if {$rcc} { ot_rc_cal_restore; estimate_parasitics -placement }
  detailed_placement
}
if {[info procs clock_tree_synthesis] ne "" && [info procs ot_cbk_cts_orig] eq ""} {
  rename clock_tree_synthesis ot_cbk_cts_orig
  proc clock_tree_synthesis {args} {
    set ports [ot_cbk_ports]
    foreach p $ports { ot_cbk_split $p }
    detailed_placement
    set nets {}
    foreach p $ports { lappend nets [[[ord::get_db_block] findBTerm $p] getNet] }
    foreach net [[ord::get_db_block] getNets] {
      if {[string match {ot_cbk_ck_*_clk} [$net getName]]} { lappend nets $net }
    }
    set names [lmap n $nets {$n getName}]
    set i [lsearch -exact $args -clk_nets]
    if {$i >= 0} { lset args [expr {$i + 1}] [concat [lindex $args [expr {$i + 1}]] $names] } else { lappend args -clk_nets $names }
    puts "OT_CB16KM CTS -clk_nets [llength $names] nets ([llength $ports] region ports + cluster nets)"
    set r [ot_cbk_cts_orig {*}$args]
    ot_cbk_balance
    return $r
  }
}
