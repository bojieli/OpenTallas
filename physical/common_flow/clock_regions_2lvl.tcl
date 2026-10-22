# Regional clock roots + per-region leaf clusters (SQ-C2-N59 2026-10-21; owner PD-AUDIT 10-21 must-do for Q.STA.N59:
# "2 regional clock roots (W/E halves) + landed seam, pin-flop spread <= 80 ps at TT and FF in each region, no waiver").
# Generalises clock_split_km.tcl (one level of k-means leaf roots under the port) to TWO levels with FIXED regions:
#   level 1 (regional roots): the core is cut at fixed seams into OT_CKRG_MODE regions --
#       we   : W / E halves (seam x = core centre)                       -> 2 regional roots
#       quad : NW / NE / SW / SE quadrants (seams x, y = core centre)    -> 4 regional roots
#     every clock sink is assigned to the region holding its placed cell; one BUFx24 regional root sits at the region's
#     sink centroid, driven by the clock port net (the port pin sits on / near a seam: equal-length region trunks).
#   level 2 (leaf roots): inside each region, OT_CKRG_LEAVES (default 6) k-means clusters (Lloyd, angle-ordered seeds,
#     as clock_split_km), one BUFx24 leaf root per cluster driven by its regional root net.  No leaf cluster and no
#     CTS subtree crosses a seam: every tree is local to its region; CTS latency balancing equalises the leaf roots under
#     each regional root and the two (four) regional roots under the port.
# Seam: every data path whose launch and capture flops sit in different regions is a flop -> flop crossing between two
# regional trees of the same synchronous clock (fixed latency: one edge, no elastic stage); after CTS the hook records
# each region's insertion range and the inter-region root delta (CLOCK_REGIONS lines + $LOG_DIR/clock_regions.json).
# Same port, clock, flops, constraints and cycles; one external clock root.  Source it via spec pre_cts_extra.
# Knobs (env): OT_CKRG_MODE (we), OT_CKRG_LEAVES (6), OT_CKRG_PORT (ck), OT_CKRG_ITERS (25).
set ot_ckrg_blk [ord::get_db_block]
if {[$ot_ckrg_blk findInst ot_ckrg_r0] eq "NULL"} {
  set mode [expr {[info exists ::env(OT_CKRG_MODE)] && $::env(OT_CKRG_MODE) ne "" ? $::env(OT_CKRG_MODE) : "we"}]
  set KL [expr {[info exists ::env(OT_CKRG_LEAVES)] && $::env(OT_CKRG_LEAVES) ne "" ? $::env(OT_CKRG_LEAVES) : 6}]
  set port [expr {[info exists ::env(OT_CKRG_PORT)] && $::env(OT_CKRG_PORT) ne "" ? $::env(OT_CKRG_PORT) : "ck"}]
  set iters [expr {[info exists ::env(OT_CKRG_ITERS)] && $::env(OT_CKRG_ITERS) ne "" ? $::env(OT_CKRG_ITERS) : 25}]
  if {$mode ni {we quad}} { error "CLOCK_REGIONS: OT_CKRG_MODE must be we or quad" }
  set u [[ord::get_db_tech] getDbUnitsPerMicron]
  set core [$ot_ckrg_blk getCoreArea]
  set sx_um [expr {([$core xMin] + [$core xMax]) / 2.0 / $u}]
  set sy_um [expr {([$core yMin] + [$core yMax]) / 2.0 / $u}]
  set bt [$ot_ckrg_blk findBTerm $port]
  if {$bt eq "NULL"} { error "CLOCK_REGIONS: no $port port" }
  set pnet [$bt getNet]
  set nreg [expr {$mode eq "we" ? 2 : 4}]
  set rname [expr {$mode eq "we" ? {W E} : {SW SE NW NE}}]
  for {set r 0} {$r < $nreg} {incr r} { set R($r,xs) {}; set R($r,ys) {}; set R($r,its) {} }
  foreach it [$pnet getITerms] {
    if {![$it isInputSignal]} continue
    set inst [$it getInst]
    set bb [$inst getBBox]
    set x [expr {([$bb xMin] + [$bb xMax]) / 2.0 / $u}]; set y [expr {([$bb yMin] + [$bb yMax]) / 2.0 / $u}]
    set r [expr {$x < $sx_um ? 0 : 1}]
    if {$mode eq "quad" && $y >= $sy_um} { incr r 2 }
    lappend R($r,xs) $x; lappend R($r,ys) $y; lappend R($r,its) $it
  }
  set m [[ord::get_db] findMaster BUFx24_ASAP7_75t_R]
  set ::ot_ckrg_regions {}
  for {set r 0} {$r < $nreg} {incr r} {
    set xs $R($r,xs); set ys $R($r,ys); set its $R($r,its)
    set N [llength $its]
    if {$N < 2 * $KL} { error "CLOCK_REGIONS: region [lindex $rname $r] has only $N sinks for $KL leaves" }
    set mx 0.0; set my 0.0
    foreach x $xs y $ys { set mx [expr {$mx + $x}]; set my [expr {$my + $y}] }
    set mx [expr {$mx / $N}]; set my [expr {$my / $N}]
    # level 1: the regional root at the region's sink centroid, on the port net
    set rb [odb::dbInst_create $ot_ckrg_blk $m ot_ckrg_r$r]
    $rb setLocation [expr {int($mx * $u)}] [expr {int($my * $u)}]; $rb setPlacementStatus PLACED
    set rnet [odb::dbNet_create $ot_ckrg_blk ot_ckrg_r${r}_clk]; $rnet setSigType CLOCK
    [$rb findITerm A] connect $pnet; [$rb findITerm Y] connect $rnet
    # level 2: k-means leaf clusters inside the region (angle-ordered equal-count seeds, Lloyd)
    set ang {}
    for {set i 0} {$i < $N} {incr i} { lappend ang [list [expr {atan2([lindex $ys $i] - $my, [lindex $xs $i] - $mx)}] $i] }
    set ang [lsort -real -index 0 $ang]
    set cx {}; set cy {}
    for {set k 0} {$k < $KL} {incr k} {
      set lo [expr {($N * $k) / $KL}]; set hi [expr {($N * ($k + 1)) / $KL - 1}]
      set ax 0.0; set ay 0.0
      foreach e [lrange $ang $lo $hi] { set i [lindex $e 1]; set ax [expr {$ax + [lindex $xs $i]}]; set ay [expr {$ay + [lindex $ys $i]}] }
      set n [expr {$hi - $lo + 1}]
      lappend cx [expr {$ax / $n}]; lappend cy [expr {$ay / $n}]
    }
    set asg [lrepeat $N 0]
    for {set it_ 0} {$it_ < $iters} {incr it_} {
      set moved 0
      for {set i 0} {$i < $N} {incr i} {
        set x [lindex $xs $i]; set y [lindex $ys $i]; set best 0; set bd 1e30
        for {set k 0} {$k < $KL} {incr k} {
          set d [expr {abs($x - [lindex $cx $k]) + abs($y - [lindex $cy $k])}]
          if {$d < $bd} { set bd $d; set best $k }
        }
        if {[lindex $asg $i] != $best} { lset asg $i $best; incr moved }
      }
      set ax [lrepeat $KL 0.0]; set ay [lrepeat $KL 0.0]; set an [lrepeat $KL 0]
      for {set i 0} {$i < $N} {incr i} {
        set k [lindex $asg $i]
        lset ax $k [expr {[lindex $ax $k] + [lindex $xs $i]}]; lset ay $k [expr {[lindex $ay $k] + [lindex $ys $i]}]
        lset an $k [expr {[lindex $an $k] + 1}]
      }
      for {set k 0} {$k < $KL} {incr k} {
        if {[lindex $an $k] > 0} { lset cx $k [expr {[lindex $ax $k] / [lindex $an $k]}]; lset cy $k [expr {[lindex $ay $k] / [lindex $an $k]}] }
      }
      if {$it_ > 0 && $moved == 0} break
    }
    set nets {}
    for {set k 0} {$k < $KL} {incr k} {
      if {[lindex $an $k] == 0} { lappend nets ""; continue }
      set b [odb::dbInst_create $ot_ckrg_blk $m ot_ckrg_r${r}_l$k]
      $b setLocation [expr {int([lindex $cx $k] * $u)}] [expr {int([lindex $cy $k] * $u)}]; $b setPlacementStatus PLACED
      set net [odb::dbNet_create $ot_ckrg_blk ot_ckrg_r${r}_l${k}_clk]; $net setSigType CLOCK
      [$b findITerm A] connect $rnet; [$b findITerm Y] connect $net
      lappend nets $net
    }
    set names {}
    for {set i 0} {$i < $N} {incr i} {
      set it [lindex $its $i]
      lappend names "[[$it getInst] getName]/[[$it getMTerm] getName]"
      $it disconnect; $it connect [lindex $nets [lindex $asg $i]]
    }
    lappend ::ot_ckrg_regions [list [lindex $rname $r] $names]
    set xl [lsort -real $xs]; set yl [lsort -real $ys]
    puts [format "CLOCK_REGIONS: region %s %d sinks x %.1f..%.1f y %.1f..%.1f root at (%.1f, %.1f), %d leaves (sizes %s)" \
      [lindex $rname $r] $N [lindex $xl 0] [lindex $xl end] [lindex $yl 0] [lindex $yl end] $mx $my $KL $an]
  }
  puts [format "CLOCK_REGIONS: mode %s seams x %.2f%s um" $mode $sx_um [expr {$mode eq "quad" ? [format " y %.2f" $sy_um] : ""}]]
  detailed_placement
  # after CTS: per-region insertion record (informational; the gate's ck.json judges the pin-flop spread at TT + FF)
  rename clock_tree_synthesis ::ot_ckrg_cts_orig
  proc clock_tree_synthesis {args} {
    ::ot_ckrg_cts_orig {*}$args
    if {[catch {
      catch {set_propagated_clock [all_clocks]}
      set recs {}
      foreach reg $::ot_ckrg_regions {
        lassign $reg nm names
        set lo 1e30; set hi -1e30; set n 0
        foreach pn $names {
          if {[catch {set p [get_pins -quiet [string map {[ {\[} ] {\]}} $pn]]}] || ![llength $p]} continue
          if {[catch {set a [get_property $p arrival_max_rise]}]} continue
          if {![string is double -strict $a]} continue
          if {$a < $lo} { set lo $a }; if {$a > $hi} { set hi $a }; incr n
        }
        if {$n} {
          puts [format "CLOCK_REGIONS: post-CTS region %s %d sinks insertion %.1f..%.1f (spread %.1f, all registers, route corner)" $nm $n $lo $hi [expr {$hi - $lo}]]
          lappend recs "\"$nm\": {\"sinks\": $n, \"min\": [format %.1f $lo], \"max\": [format %.1f $hi], \"spread\": [format %.1f [expr {$hi - $lo}]]}"
        }
      }
      set rr {}
      foreach b [lsort [get_cells -quiet ot_ckrg_r*]] {
        set nm [get_full_name $b]
        if {[string match *_l* $nm]} continue
        set p [get_pins -quiet $nm/Y]
        if {[llength $p]} { lappend rr "\"$nm\": [format %.1f [get_property $p arrival_max_rise]]" }
      }
      puts "CLOCK_REGIONS: regional root output arrivals {[join $rr {, }]}"
      if {[info exists ::env(LOG_DIR)]} {
        set f [open $::env(LOG_DIR)/clock_regions.json w]
        puts $f "{\"regions\": {[join $recs {, }]}, \"roots\": {[join $rr {, }]}}"
        close $f
      }
    } err]} { puts "CLOCK_REGIONS: post-CTS record skipped: $err" }
  }
}
