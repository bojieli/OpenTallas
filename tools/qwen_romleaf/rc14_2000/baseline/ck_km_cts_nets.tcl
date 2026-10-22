# QW-CB16R 10-20 (A0 rc12): CTS + measured top balancing for the k-means local roots of ck_km_split.tcl.
# (1) The hybrid clock-entry wrapper (physical/common_flow/clock_entries.tcl) calls ot_ce_cts_orig with -clk_nets = the
#     declared glue roots only, so the K cluster nets (ot_ckkm_<port>_<k>_clk) would stay one BUFx24 each (measured: NK
#     ck_de 302 ps).  Every ot_ckkm_*_clk net is appended to -clk_nets: one short TritonCTS tree per compact cluster.
# (2) TritonCTS does not balance user-listed nets against each other: with (1) alone every cluster tree is tight (5..20 ps)
#     but the top tree from the port to the K cluster roots left NK ck_de clusters 482..679 ps (spread 211 ps).  After CTS
#     the latest sink arrival of every cluster is MEASURED (STA, placement parasitics, propagated clocks, the calibrated
#     clock RC when tools/orfs_hold_mm provides it) and early clusters get pad cells in front of their cluster root
#     (coarse HB4xp67, then fine BUFx2; per-pad delay learned from the previous round), as physical/common_flow/
#     clock_spine.tcl does for its leaves.  Buffers only: ports, clocks, flops, constraints and cycles unchanged.
# Knobs (env): OT_CKKM_ITERS_BAL (8), OT_CKKM_TOL_PS (20), OT_CKKM_STAGE_PS (45), OT_CKKM_FINE_PS (12).
proc ot_ckkm_env {n d} { if {[info exists ::env($n)] && $::env($n) ne ""} { return $::env($n) }; return $d }
proc ot_ckkm_leafnets {net} {
  # BFS from a cluster net through clock buffers/inverters; return the nets that drive sequential clock pins
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
      foreach o [[$it getInst] getITerms] {
        if {[$o isOutputSignal] && [$o getNet] ne "NULL"} { lappend todo [$o getNet] }
      }
    }
    if {$leaf} { lappend out [$n getName] }
  }
  return $out
}
proc ot_ckkm_arrivals {} {
  estimate_parasitics -placement
  sta::find_timing_paths -path_delay max -group_path_count 1
  set a [dict create]
  dict for {b leaves} $::ot_ckkm_leaves {
    set v 0.0
    foreach ln $leaves {
      foreach pin [get_pins -quiet -of_objects [get_nets -quiet $ln] -filter "direction==input"] {
        set x [get_property $pin arrival_max_rise]
        if {$x ne "" && $x ne "INF" && $x ne "-INF" && $x > $v} { set v $x }
      }
    }
    dict set a $b $v
  }
  return $a
}
proc ot_ckkm_pad {b count master} {
  set blk [ord::get_db_block]
  set inst [$blk findInst $b]
  set ait [$inst findITerm A]
  set net [$ait getNet]
  lassign [$inst getLocation] lx ly
  $ait disconnect
  for {set i 0} {$i < $count} {incr i} {
    set p [incr ::ot_ckkm_npad]
    set c [odb::dbInst_create $blk $master ot_ckkm_pad_$p]
    $c setLocation $lx $ly; $c setPlacementStatus PLACED
    set nn [odb::dbNet_create $blk ot_ckkm_pad_${p}_clk]; $nn setSigType CLOCK
    foreach it [$c getITerms] {
      if {[$it isInputSignal]} { $it connect $net } elseif {[$it isOutputSignal]} { $it connect $nn }
    }
    set net $nn
  }
  $ait connect $net
}
proc ot_ckkm_balance {} {
  set blk [ord::get_db_block]
  set ::ot_ckkm_leaves [dict create]; set ::ot_ckkm_npad 0
  foreach inst [$blk getInsts] {
    set n [$inst getName]
    if {![regexp {^ot_ckkm_(.+)_([0-9]+)$} $n -> port k]} continue
    set o [[$inst findITerm Y] getNet]
    dict set ::ot_ckkm_leaves $n [ot_ckkm_leafnets $o]
    dict lappend ::ot_ckkm_byport $port $n
  }
  if {![dict size $::ot_ckkm_leaves]} return
  set_propagated_clock [all_clocks]
  set rcc 0
  if {[llength [info commands ot_rc_cal_apply]]} { set rcc [ot_rc_cal_apply ckkm] }
  set iters [ot_ckkm_env OT_CKKM_ITERS_BAL 8]; set tol [ot_ckkm_env OT_CKKM_TOL_PS 20]
  set stage [ot_ckkm_env OT_CKKM_STAGE_PS 45]; set fstage [ot_ckkm_env OT_CKKM_FINE_PS 12]
  set mc [[ord::get_db] findMaster HB4xp67_ASAP7_75t_R]; set mf [[ord::get_db] findMaster BUFx2_ASAP7_75t_R]
  dict for {port bufs} $::ot_ckkm_byport {
    set mode coarse; set prev ""; set padded [dict create]
    for {set it 0} {$it <= $iters} {incr it} {
      set all [ot_ckkm_arrivals]; set a [dict create]
      foreach b $bufs { dict set a $b [dict get $all $b] }
      set vals [dict values $a]; set mx [tcl::mathfunc::max {*}$vals]; set mn [tcl::mathfunc::min {*}$vals]
      if {$prev ne "" && [dict size $padded]} {
        set g {}
        dict for {b c} $padded { lappend g [expr {([dict get $a $b] - [dict get $prev $b]) / double($c)}] }
        set g [lsort -real $g]; set m [lindex $g [expr {[llength $g] / 2}]]
        if {$m < 3.0} { set m 3.0 }
        if {$mode eq "coarse"} { set stage $m } else { set fstage $m }
      }
      puts [format "OT_CKKM balance %s iter %d (%s) clusters %d latest %.1f..%.1f ps (spread %.1f) pad %.1f / %.1f ps pads %d" $port $it $mode [llength $bufs] $mn $mx [expr {$mx - $mn}] $stage $fstage $::ot_ckkm_npad]
      if {$it == $iters || $mx - $mn <= $tol} break
      if {$mode eq "coarse" && $mx - $mn < 1.6 * $stage} { set mode fine }
      set st [expr {$mode eq "coarse" ? $stage : $fstage}]
      set prev $a; set padded [dict create]
      dict for {b v} $a {
        set c [expr {int(floor(($mx - $v - 0.5 * $tol) / $st))}]
        if {$c > 0} { ot_ckkm_pad $b $c [expr {$mode eq "coarse" ? $mc : $mf}]; dict set padded $b $c }
      }
      if {![dict size $padded]} break
    }
  }
  if {$rcc} { ot_rc_cal_restore; estimate_parasitics -placement }
}
if {[info procs ot_ce_cts_orig] ne "" && [info procs ot_ckkm_cts_inner] eq ""} {
  rename ot_ce_cts_orig ot_ckkm_cts_inner
  proc ot_ce_cts_orig {args} {
    set extra {}
    foreach net [[ord::get_db_block] getNets] {
      if {[string match {ot_ckkm_*_clk} [$net getName]] && ![string match {ot_ckkm_pad_*} [$net getName]]} { lappend extra [$net getName] }
    }
    set i [lsearch -exact $args -clk_nets]
    if {$i >= 0 && [llength $extra]} {
      lset args [expr {$i + 1}] [concat [lindex $args [expr {$i + 1}]] $extra]
      puts "OT_CKKM CTS -clk_nets += [llength $extra] cluster nets"
    }
    set r [ot_ckkm_cts_inner {*}$args]
    ot_ckkm_balance
    return $r
  }
}
