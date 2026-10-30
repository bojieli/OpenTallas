# DIE-KV-39-PVBAL (KV-012 kv3_pv_pair 'bal' variant): balance the 4 plan quadrant-island clock trees to ONE common
# insertion after TritonCTS built their CTS-open leaf trees independently (root cause CHECKED by KV-KITS-T on
# 29f7719e90c0: isl0 tree 162 ps vs isl1 208 ps, one extra CTS level -> 46 ps inter-island skew -> GRT hold repair
# 1762 viol cut SS setup -1.9 -> -24.7).  Form = the plan tap-balance rule (tap_balance.tcl KV-P6: short trees get a
# delay chain at the tree root up to the common target) applied to the quadrant branch roots: for every quadrant k
# whose mean register-sink insertion is below the slowest quadrant's mean - tol, BUF delay cells are inserted on the
# branch input (port net -> chain -> mp_pv_ck_br<k>), so island k flops AND its planned SRAM macro chain mac<k>_* move
# together (no intra-quadrant skew change).  Measure only on placement RC at the CTS stage; fail-closed on any
# missing island; every inserted cell/net is dont_touch CLOCK.  OT_ISLBAL_REPORT_ONLY=1: measure, no change.
proc ib_env {k d} { expr {[info exists ::env($k)] && $::env($k) ne "" ? $::env($k) : $d} }
set ib_tol [ib_env OT_ISLBAL_TOL_PS 8.0]
set ib_max [ib_env OT_ISLBAL_MAX_BUFS 10]
set ib_cell [ib_env OT_ISLBAL_CELL BUFx4_ASAP7_75t_R]
set ib_fine [ib_env OT_ISLBAL_FINE_CELL BUFx2_ASAP7_75t_R]
set ib_ronly [ib_env OT_ISLBAL_REPORT_ONLY 0]
set ib_blk [ord::get_db_block]
set ib_master [[ord::get_db] findMaster $ib_cell]
if {$ib_master eq "NULL"} { error "OT_ISLBAL no master $ib_cell" }
set ib_fmaster [[ord::get_db] findMaster $ib_fine]
if {$ib_fmaster eq "NULL"} { error "OT_ISLBAL no master $ib_fine" }

proc ib_regpins {k} {
  # register clock pins below mp_pv_ck_isl<k> (BFS through buffer/inverter clock cells)
  set blk [ord::get_db_block]
  set root [$blk findInst mp_pv_ck_isl$k]
  if {$root eq "NULL"} { error "OT_ISLBAL missing mp_pv_ck_isl$k" }
  set out {}; set q [list $root]; set seen [dict create]
  while {[llength $q]} {
    set i [lindex $q 0]; set q [lrange $q 1 end]
    foreach it [$i getITerms] {
      if {![$it isOutputSignal]} continue
      set n [$it getNet]; if {$n eq "NULL"} continue
      foreach s [$n getITerms] {
        if {![$s isInputSignal]} continue
        set si [$s getInst]; set nm [$si getName]
        if {[dict exists $seen $nm]} continue
        dict set seen $nm 1
        if {[regexp {^(BUF|INV|HB|CKINV|CKBUF)} [[$si getMaster] getName]]} { lappend q $si } else { lappend out "$nm/[[$s getMTerm] getName]" }
      }
    }
  }
  return $out
}
proc ib_measure {} {
  estimate_parasitics -placement
  set res {}
  for {set k 0} {$k < 4} {incr k} {
    set s 0.0; set n 0; set mx -1e9; set mn 1e9
    foreach p $::ib_pins($k) {
      if {[catch {set a [get_property [get_pins $p] arrival_max_rise]}] || $a eq "" || [string match *INF* $a]} continue
      set s [expr {$s + $a}]; incr n
      if {$a > $mx} { set mx $a }; if {$a < $mn} { set mn $a }
    }
    if {$n == 0} { error "OT_ISLBAL island $k has no measurable register clock pin" }
    lappend res [list $k [expr {$s / $n}] $mn $mx $n]
  }
  return $res
}
set_propagated_clock [all_clocks]
for {set k 0} {$k < 4} {incr k} { set ib_pins($k) [ib_regpins $k] }
set ib_m [ib_measure]
foreach r $ib_m { puts [format "OT_ISLBAL before isl%d mean %.2f min %.2f max %.2f ps sinks %d" {*}$r] }
set ib_T -1e9; foreach r $ib_m { if {[lindex $r 1] > $ib_T} { set ib_T [lindex $r 1] } }
set ib_added 0
if {!$ib_ronly} {
  set u [[ord::get_db_tech] getDbUnitsPerMicron]
  for {set k 0} {$k < 4} {incr k} {
    # coarse cell while the gap exceeds its measured step, then the fine cell while the gap exceeds half its step
    # (nearest-to-target, no systematic overshoot); steps start at 24 / 14 ps and are re-measured per insertion
    set nb 0; set chain {}; set step(c) 24.0; set step(f) 14.0
    set cur [lindex [lsearch -index 0 -inline [ib_measure] $k] 1]
    while {$nb < $ib_max} {
      set gap [expr {$ib_T - $cur}]
      if {$gap > $step(c)} { set kind c; set m $ib_master } elseif {$gap > 0.5 * $step(f)} { set kind f; set m $ib_fmaster } else break
      set br [$ib_blk findInst mp_pv_ck_br$k]
      if {$br eq "NULL"} { error "OT_ISLBAL missing mp_pv_ck_br$k" }
      set a [$br findITerm A]
      set nin [$a getNet]
      set name "ot_islbal_b${k}_$nb"
      set bi [odb::dbInst_create $ib_blk $m $name]
      set nn [odb::dbNet_create $ib_blk "${name}_o"]
      $nn setSigType CLOCK
      lassign [$br getLocation] x y
      $bi setLocation $x $y; $bi setPlacementStatus PLACED
      $nin setDoNotTouch 0; $br setDoNotTouch 0
      $a disconnect; $a connect $nn
      [$bi findITerm A] connect $nin
      [$bi findITerm Y] connect $nn
      $nin setDoNotTouch 1; $br setDoNotTouch 1
      $bi setDoNotTouch 1; $nn setDoNotTouch 1
      incr nb; incr ib_added; lappend chain [$m getName]
      set new [lindex [lsearch -index 0 -inline [ib_measure] $k] 1]
      set step($kind) [expr {max(1.0, $new - $cur)}]; set cur $new
    }
    puts "OT_ISLBAL quadrant $k chain $nb {$chain}"
  }
  if {$ib_added} {
    if {[catch {detailed_placement} m]} { error "OT_ISLBAL detailed_placement failed: $m" }
    check_placement -verbose
  }
}
set ib_m [ib_measure]
foreach r $ib_m { puts [format "OT_ISLBAL after isl%d mean %.2f min %.2f max %.2f ps sinks %d" {*}$r] }
set ib_lo 1e9; set ib_hi -1e9
foreach r $ib_m { set v [lindex $r 1]; if {$v < $ib_lo} {set ib_lo $v}; if {$v > $ib_hi} {set ib_hi $v} }
puts [format "OT_ISLBAL spread of island means %.2f ps (target <= %.1f) added %d cells" [expr {$ib_hi - $ib_lo}] $ib_tol $ib_added]
