# GENERATED-COPY of tools/die_plan/rck_star.tcl (PRE_CTS, opt-in plan clock.pad_clock pins[].star; FABLE-FIX-S81-SERDES 11-18).
# Matched-leg star trunk of a pad clock, planned on the PLACED sinks by rck_star.py: the sinks are cut into compact regions;
# every region gets an entry driver on its own leg from one hub, each leg with the same stage count and the same length (a
# detour makes up a shorter distance), so the trunk is equal by construction and TritonCTS only builds a 2-4 level tree per
# entry.  A pad that is far from the sinks reaches the hub through one common feeder chain.  Same ports, flops, logic,
# constraints and cycles; the cells are ordinary PLACED clock buffers (pce_<entry>_s<k> / pce_<entry>_drv, rks_feed_<k>).
# Env: OT_RCK_STAR_PORT (io_pma_rck), OT_RCK_STAR_MAX_SINKS (200), OT_RCK_STAR_MAX_EXTENT_UM (100), OT_RCK_STAR_HOP_UM (92),
#      OT_RCK_STAR_CELL (BUFx24_ASAP7_75t_R).
proc rks_env {k d} { if {[info exists ::env($k)] && $::env($k) ne ""} { return $::env($k) }; return $d }
set rks_dir [file dirname [file normalize [info script]]]
set rks_blk [ord::get_db_block]
if {[$rks_blk findInst pce_rck_r0_drv] eq "NULL"} {
  set rks_port [rks_env OT_RCK_STAR_PORT io_pma_rck]
  set rks_bt [$rks_blk findBTerm "${rks_port}\[0\]"]
  if {$rks_bt eq "NULL"} { set rks_bt [$rks_blk findBTerm $rks_port] }
  if {$rks_bt eq "NULL"} { error "OT_RCK_STAR: pad clock port $rks_port not in the block" }
  set rks_net [$rks_bt getNet]
  set rks_u [expr {double([$rks_blk getDbUnitsPerMicron])}]
  set rks_geom [file join $rks_dir rck_star_geom.tsv]
  set rks_f [open $rks_geom w]
  set rks_bb [$rks_bt getBBox]
  puts $rks_f "PORT\t$rks_port\t[expr {([$rks_bb xMin] + [$rks_bb xMax]) / 2.0 / $rks_u}]\t[expr {([$rks_bb yMin] + [$rks_bb yMax]) / 2.0 / $rks_u}]"
  # rows by yMin for the site lookup (one pass; 6.7k rows on serdes__t13)
  array unset rks_rows
  foreach rks_r [$rks_blk getRows] {
    set rks_b [$rks_r getBBox]
    puts $rks_f "ROW\t[expr {[$rks_b xMin] / $rks_u}]\t[expr {[$rks_b yMin] / $rks_u}]\t[expr {[$rks_b xMax] / $rks_u}]\t[expr {[$rks_b yMax] / $rks_u}]"
    lappend rks_rows([$rks_b yMin]) [list [$rks_b xMin] [$rks_b xMax] [$rks_r getOrient] [[$rks_r getSite] getWidth]]
  }
  set rks_ys [lsort -integer [array names rks_rows]]
  set rks_sinks {}
  foreach rks_it [$rks_net getITerms] {
    if {!([$rks_it isInputSignal] || [[$rks_it getMTerm] getSigType] eq "CLOCK")} continue
    set rks_i [$rks_it getInst]; set rks_b [$rks_it getBBox]
    puts $rks_f "SINK\t[$rks_i getName]\t[[$rks_it getMTerm] getName]\t[[$rks_i getMaster] getName]\t[expr {[[$rks_i getMaster] isBlock] ? 1 : 0}]\t[expr {([$rks_b xMin] + [$rks_b xMax]) / 2.0 / $rks_u}]\t[expr {([$rks_b yMin] + [$rks_b yMax]) / 2.0 / $rks_u}]"
    lappend rks_sinks $rks_it
  }
  close $rks_f
  set rks_out [file join $rks_dir rck_star_plan.tcl]
  file delete -force $rks_out
  puts [exec python3 -I [file join $rks_dir rck_star.py] $rks_geom $rks_out --max-sinks [rks_env OT_RCK_STAR_MAX_SINKS 200] \
          --max-extent [rks_env OT_RCK_STAR_MAX_EXTENT_UM 100] --hop [rks_env OT_RCK_STAR_HOP_UM 92] \
          --cell [rks_env OT_RCK_STAR_CELL BUFx24_ASAP7_75t_R] --report [file join $rks_dir rck_star_report.json]]
  uplevel #0 [list source $rks_out]
  if {[llength $::rks_assign] != [llength $rks_sinks]} { error "OT_RCK_STAR: plan covers [llength $::rks_assign] of [llength $rks_sinks] sinks" }
  set rks_m [[ord::get_db] findMaster $::rks_cell]
  if {$rks_m eq "NULL"} { error "OT_RCK_STAR: no master $::rks_cell" }
  set rks_mw [$rks_m getWidth]
  proc rks_place {inst x y} {
    # the row band at or below y that spans the cell at x (rck_star.py only emits points inside a row), x on the site grid
    global rks_rows rks_ys rks_u rks_mw
    set X [expr {round($x * $rks_u)}]; set Y [expr {round($y * $rks_u)}]
    set i [lsearch -integer -sorted -bisect $rks_ys $Y]
    foreach j [list $i [expr {$i + 1}] [expr {$i - 1}] [expr {$i + 2}] [expr {$i - 2}]] {
      if {$j < 0 || $j >= [llength $rks_ys]} continue
      set yy [lindex $rks_ys $j]
      foreach r $rks_rows($yy) {
        lassign $r x0 x1 orient sw
        if {$X < $x0 || $X + $rks_mw > $x1} continue
        $inst setOrient $orient
        $inst setLocation [expr {$x0 + round(($X - $x0) / double($sw)) * $sw}] $yy
        $inst setPlacementStatus PLACED
        return
      }
    }
    error "OT_RCK_STAR: no row at ($x, $y) for [$inst getName]"
  }
  proc rks_stage {name src x y {outname ""}} {
    # one trunk buffer at (x, y) fed by net src; returns its output net
    global rks_blk rks_m
    set i [odb::dbInst_create $rks_blk $rks_m $name]
    if {$i eq "NULL"} { error "OT_RCK_STAR: cannot create $name" }
    rks_place $i $x $y
    set in ""; set out ""
    foreach it [$i getITerms] {
      set mt [$it getMTerm]
      if {[$mt getSigType] ne "SIGNAL"} continue
      if {[$mt getIoType] eq "INPUT"} { set in $it } elseif {[$mt getIoType] eq "OUTPUT"} { set out $it }
    }
    if {$in eq "" || $out eq ""} { error "OT_RCK_STAR: $::rks_cell is not a one-input buffer" }
    $in connect $src
    set net [odb::dbNet_create $rks_blk [expr {$outname ne "" ? $outname : "${name}_n"}]]
    if {$net eq "NULL"} { error "OT_RCK_STAR: net of $name exists" }
    $net setSigType CLOCK
    $out connect $net
    return $net
  }
  # common feeder pad -> hub (empty when the hub is at the pad)
  set rks_hub $rks_net; set rks_k 0
  foreach rks_pt $::rks_feeder { set rks_hub [rks_stage rks_feed_$rks_k $rks_hub {*}$rks_pt]; incr rks_k }
  # one leg per entry; the entry net carries the entry name
  set rks_enets {}; set rks_nst 0
  foreach rks_leg $::rks_legs {
    lassign $rks_leg rks_name rks_st rks_xy
    set rks_src $rks_hub; set rks_j 0
    foreach rks_pt $rks_st { set rks_src [rks_stage pce_${rks_name}_s$rks_j $rks_src {*}$rks_pt]; incr rks_j; incr rks_nst }
    lappend rks_enets [rks_stage pce_${rks_name}_drv $rks_src {*}$rks_xy $rks_name]
  }
  foreach rks_it $rks_sinks rks_e $::rks_assign { $rks_it disconnect; $rks_it connect [lindex $rks_enets $rks_e] }
  puts "OT_RCK_STAR $rks_port: [llength $rks_sinks] sinks behind [llength $rks_enets] matched entries ($rks_nst leg stations + $rks_k feeder stations of $::rks_cell), 0 left on the pad net"
}
