# GENERATED-COPY of tools/die_plan/grt_clock_first.tcl (FLOW-CLKGRT-1121, opt-in OT_GRT_CLOCK_FIRST=1; sourced last in grt_pre.tcl).
# Clock-first global routing.  The 30-iteration congestion negotiation rips up and re-routes every net that crosses an
# overflowed gcell edge, clock leaf branches included, so near-tap clock branches came out 217..432 um where the same CTS
# database routes them <= 215 um on an empty grid (KV hroot D25d a5: clk_t9 spread 39 -> 510 ps after GRT; leaf repeaters on
# S81 76 / QC 27 GRT logs).  Industry practice: route the clock first and keep it while signals route.  OpenROAD has no fixed-net
# mode, so the first full global_route of the stage runs as two routes of the same grid and capacity setup:
#   phase 1  the clock nets only (grt::add_net_to_route): short, near-CTS routes; their guides go to the database;
#   phase 2  every other net, with the clock routes' gcell-edge usage reserved as capacity (region adjustments, one track per
#            clock wire per edge), so signals negotiate around the clock instead of displacing it; only phase-2 nets get guides;
#   merge    grt::read_segments of both segment sets, so the in-memory routing the rest of the stage reads (estimate_parasitics
#            -global_routing, repair_design / repair_timing incremental routes, the GRT leaf-repeat pass) holds every net.
# Later global_route calls (-start_incremental / -end_incremental) pass through unchanged.  OT_GRT_CLOCK_FIRST_RESERVE=0 skips
# the phase-2 capacity reservation (A/B only).  Opt-out: OT_GRT_CLOCK_FIRST unset / 0 (the hook is then a no-op).
namespace eval ot_gcf {
  variable done 0
  # clock network = the nets from every register clock pin up through the buffer / inverter tree (single-input cells, or the CLK
  # pin of a clock gate) to its port, plus every net the database already types CLOCK
  proc nets {} {
    set blk [ord::get_db_block]
    array set seen {}
    set todo {}
    foreach n [$blk getNets] { if {[$n getSigType] eq "CLOCK"} { lappend todo $n } }
    foreach p [all_registers -clock_pins] {
      set it [sta::sta_to_db_pin $p]
      if {$it eq "" || $it eq "NULL"} continue
      set n [$it getNet]; if {$n ne "NULL"} { lappend todo $n }
    }
    while {[llength $todo]} {
      set n [lindex $todo end]; set todo [lrange $todo 0 end-1]
      set nm [$n getName]
      if {[info exists seen($nm)]} continue
      set seen($nm) $n
      if {[$n isSpecial] || [$n getSigType] in {POWER GROUND}} { unset seen($nm); continue }
      foreach it [$n getITerms] {
        if {![$it isOutputSignal]} continue
        set ins {}
        foreach ii [[$it getInst] getITerms] { if {[$ii isInputSignal] && [$ii getNet] ne "NULL"} { lappend ins $ii } }
        foreach ii $ins {
          if {[llength $ins] == 1 || [string toupper [[$ii getMTerm] getName]] eq "CLK"} { lappend todo [$ii getNet] }
        }
      }
    }
    set out {}
    foreach {k v} [array get seen] { lappend out $v }
    return $out
  }
  proc dbu_um {v} { return [expr {double($v) / [[ord::get_db_tech] getDbUnitsPerMicron]}] }
  # phase-2 capacity reservation: one track per clock wire on each gcell edge it uses.  computeRegionAdjustments takes, on a region
  # that sits inside one gcell row (column) of a horizontal (vertical) layer, ceil(thickness / pitch) tracks off every edge of the
  # run, so the region is the run (tile centre to one dbu short of the far tile) with a thickness of one pitch less one dbu: -1 track.
  proc reserve {seg} {
    set tech [ord::get_db_tech]
    set gc [[ord::get_db_block] getGCellGrid]
    set tile 0
    if {$gc ne "NULL" && $gc ne ""} { catch { set gx [$gc getGridX]; if {[llength $gx] > 1} { set tile [expr {[lindex $gx 1] - [lindex $gx 0]}] } } }
    if {$tile <= 0} { puts "OT_GRT_CLOCK_FIRST reserve skipped: no gcell grid"; return 0 }
    set n 0; set bad 0
    array set pitch {}
    set f [open $seg]
    while {[gets $f line] >= 0} {
      set t [regexp -all -inline {\S+} $line]
      if {[llength $t] != 6} continue
      lassign $t x1 y1 l1 x2 y2 l2
      if {$l1 ne $l2 || ($x1 == $x2 && $y1 == $y2)} continue
      if {![info exists pitch($l1)]} {
        set L [$tech findLayer $l1]
        set pitch($l1) [expr {$L eq "NULL" ? 0 : [$L getPitch]}]
      }
      set p $pitch($l1)
      if {$p <= 1} continue
      set h [expr {($p - 1) / 2}]
      if {$y1 == $y2} {
        set a [expr {min($x1, $x2)}]; set b [expr {max($x1, $x2) - $tile / 2 - 1}]
        set box [list $a [expr {$y1 - $h}] $b [expr {$y1 - $h + $p - 1}]]
      } else {
        set a [expr {min($y1, $y2)}]; set b [expr {max($y1, $y2) - $tile / 2 - 1}]
        set box [list [expr {$x1 - $h}] $a [expr {$x1 - $h + $p - 1}] $b]
      }
      set um {}; foreach v $box { lappend um [dbu_um $v] }
      if {[catch {set_global_routing_region_adjustment $um -layer $l1 -adjustment 0.001}]} { incr bad; continue }
      incr n
    }
    close $f
    if {$bad} { puts "OT_GRT_CLOCK_FIRST reserve: $bad runs refused by set_global_routing_region_adjustment" }
    return $n
  }
  proc route {args} {
    variable done
    set dir [expr {[info exists ::env(RESULTS_DIR)] ? $::env(RESULTS_DIR) : "."}]
    set blk [ord::get_db_block]
    set t0 [clock seconds]
    set clk [nets]
    foreach n $clk { grt::add_net_to_route $n }
    set a1 $args
    set i [lsearch -exact $a1 -congestion_report_file]
    if {$i >= 0} { set a1 [lreplace $a1 [expr {$i + 1}] [expr {$i + 1}] "[file rootname [lindex $a1 [expr {$i + 1}]]]_clock_first.rpt"] }
    uplevel 1 [list ::ot_gcf_gr_orig {*}$a1]
    grt::write_segments $dir/5_1_grt.clock_first.seg
    grt::read_segments $dir/5_1_grt.clock_first.seg      ;# router reset (clears the nets-to-route list); clock guides stay in the db
    set t1 [clock seconds]
    set nres 0
    if {![info exists ::env(OT_GRT_CLOCK_FIRST_RESERVE)] || $::env(OT_GRT_CLOCK_FIRST_RESERVE) ne "0"} { set nres [reserve $dir/5_1_grt.clock_first.seg] }
    array set isclk {}; foreach n $clk { set isclk([$n getName]) 1 }
    set ns 0
    foreach n [$blk getNets] {
      if {[info exists isclk([$n getName])] || [$n isSpecial] || [$n getSigType] in {POWER GROUND}} continue
      grt::add_net_to_route $n; incr ns
    }
    puts [format "OT_GRT_CLOCK_FIRST phase 1: %d clock nets routed in %d s; phase 2: %d other nets, %d clock runs reserved" [llength $clk] [expr {$t1 - $t0}] $ns $nres]
    set rc [catch {uplevel 1 [list ::ot_gcf_gr_orig {*}$args]} res opts]
    if {$rc} { return -options $opts $res }
    grt::write_segments $dir/5_1_grt.clock_first_sig.seg
    set fo [open $dir/5_1_grt.clock_first_all.seg w]
    foreach p [list $dir/5_1_grt.clock_first.seg $dir/5_1_grt.clock_first_sig.seg] { set fi [open $p]; fcopy $fi $fo; close $fi }
    close $fo
    grt::read_segments $dir/5_1_grt.clock_first_all.seg
    # read_segments resets the router state: re-arm allow-congestion (else the next incremental route raises GRT-0116)
    if {[lsearch -exact $args -allow_congestion] >= 0} { ::grt::set_allow_congestion 1 }
    set done 1
    puts [format "OT_GRT_CLOCK_FIRST done in %d s: clock + signal routes merged (%s)" [expr {[clock seconds] - $t0}] $dir/5_1_grt.clock_first_all.seg]
    return $res
  }
}
if {[info exists ::env(OT_GRT_CLOCK_FIRST)] && $::env(OT_GRT_CLOCK_FIRST) eq "1" && [llength [info commands ::global_route]]
    && [llength [info commands ::grt::add_net_to_route]] && [llength [info commands ::grt::read_segments]] && ![llength [info commands ::ot_gcf_gr_orig]]} {
  rename ::global_route ::ot_gcf_gr_orig
  proc ::global_route {args} {
    if {$::ot_gcf::done || [lsearch -exact $args -start_incremental] >= 0 || [lsearch -exact $args -end_incremental] >= 0} {
      return [uplevel 1 [list ::ot_gcf_gr_orig {*}$args]]
    }
    return [uplevel 1 [list ::ot_gcf::route {*}$args]]
  }
  puts "OT_GRT_CLOCK_FIRST installed: the first full global_route routes the clock nets first and keeps them"
}
