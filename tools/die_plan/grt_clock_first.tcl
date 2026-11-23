# GENERATED-COPY of tools/die_plan/grt_clock_first.tcl (FLOW-CLKGRT-1121, gen default OT_GRT_CLOCK_FIRST=1 (FLOW-CLKGRT-R2), opt-out =0; sourced last in grt_pre.tcl).
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
# Later global_route calls (-start_incremental / -end_incremental) pass through unchanged.  OT_GRT_CLOCK_FIRST_RES_AWARE=1 adds
# -resistance_aware -res_aware_nets_percentage 0 to both phases (recommended form).  OT_GRT_CLOCK_FIRST_RESERVE=0 skips
# the phase-2 capacity reservation (A/B only).  Opt-out: gen env OT_GRT_CLOCK_FIRST=0 (config.mk without the key: the hook is a no-op).
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
  # Clock NDR loss in the clock-only phase (GRT-0273 "Disabled NDR (to reduce congestion)") means the clock lost its wide/spaced
  # rule where no signal net competes: the capacity at its pins (PG / obstruction / pin-access edges) is short, so neither
  # clock-first nor CTS-NDR scoping can fix it; it needs a legal pin / root-buffer escape (HEAD r18 t7/t32/t37: M7 pin-centre
  # offsets).  One row per dropped net -> 5_1_grt.clock_ndr_loss.tsv (header only when none); no stop.  class root = net driven by
  # a port or a clock-root buffer (clknet_0_*), tap = a deeper tree net.
  proc ndr_loss {log out} {
    set blk [ord::get_db_block]
    set gc [$blk getGCellGrid]
    set gx {}; set gy {}
    if {$gc ne "NULL" && $gc ne ""} { catch { set gx [$gc getGridX]; set gy [$gc getGridY] } }
    set names {}
    foreach line [split $log "\n"] {
      if {[regexp {GRT-0273\].*for net:\s*(\S+)} $line -> nm] && [lsearch -exact $names $nm] < 0} { lappend names $nm }
    }
    set f [open $out w]
    puts $f [join {net class ndr driver driver_master pin_layer x_um y_um gcell_x gcell_y fanout bbox_w_um bbox_h_um} "\t"]
    foreach nm $names {
      set n [$blk findNet $nm]
      if {$n eq "NULL" || $n eq ""} { puts $f [join [list $nm unknown - - - - - - - - - - -] "\t"]; continue }
      set ndr [$n getNonDefaultRule]; set ndr [expr {$ndr eq "NULL" ? "-" : [$ndr getName]}]
      set drv "-"; set mst "-"; set lay "-"; set x ""; set y ""; set cls tap
      foreach bt [$n getBTerms] { if {[$bt getIoType] eq "INPUT"} { set drv [$bt getName]; set mst PORT; set cls root
          catch { set lay [[[lindex [[lindex [$bt getBPins] 0] getBoxes] 0] getTechLayer] getName] }
          catch { set bb [$bt getBBox]; set x [expr {([$bb xMin] + [$bb xMax]) / 2}]; set y [expr {([$bb yMin] + [$bb yMax]) / 2}] } } }
      foreach it [$n getITerms] {
        if {![$it isOutputSignal]} continue
        set drv "[[$it getInst] getName]/[[$it getMTerm] getName]"; set mst [[[$it getInst] getMaster] getName]
        lassign [$it getAvgXY] ok x y
        if {!$ok} { lassign [[$it getInst] getLocation] x y }
      }
      if {[string match "clknet_0_*" $nm]} { set cls root }
      set ix -; set iy -
      if {$x ne "" && [llength $gx] > 1} { set ix 0; foreach g $gx { if {$g <= $x} { set ix [lsearch -exact $gx $g] } } }
      if {$y ne "" && [llength $gy] > 1} { set iy 0; foreach g $gy { if {$g <= $y} { set iy [lsearch -exact $gy $g] } } }
      set fo 0; set x0 {}; set y0 {}; set x1 {}; set y1 {}
      set pts {}
      if {$x ne "" && $y ne ""} { lappend pts [list $x $y] }
      foreach it [$n getITerms] { if {[$it isInputSignal]} { incr fo }; lassign [$it getAvgXY] ok px py; if {$ok} { lappend pts [list $px $py] } }
      foreach pt $pts { lassign $pt px py
        if {1} { if {$x0 eq "" || $px < $x0} { set x0 $px }; if {$x1 eq "" || $px > $x1} { set x1 $px }
                   if {$y0 eq "" || $py < $y0} { set y0 $py }; if {$y1 eq "" || $py > $y1} { set y1 $py } } }
      set bw [expr {$x0 eq "" ? "-" : [format %.1f [dbu_um [expr {$x1 - $x0}]]]}]
      set bh [expr {$y0 eq "" ? "-" : [format %.1f [dbu_um [expr {$y1 - $y0}]]]}]
      set xu [expr {$x eq "" ? "-" : [format %.3f [dbu_um $x]]}]; set yu [expr {$y eq "" ? "-" : [format %.3f [dbu_um $y]]}]
      puts $f [join [list $nm $cls $ndr $drv $mst $lay $xu $yu $ix $iy $fo $bw $bh] "\t"]
    }
    close $f
    puts [format "OT_GRT_CLOCK_FIRST clock NDR loss in clock-only phase: %d nets%s (%s)" [llength $names] \
          [expr {[llength $names] ? " -> pin/root escape capacity, not signal congestion" : ""}] $out]
    return [llength $names]
  }
  proc route {args} {
    variable done
    set dir [expr {[info exists ::env(RESULTS_DIR)] ? $::env(RESULTS_DIR) : "."}]
    set blk [ord::get_db_block]
    set t0 [clock seconds]
    # OT_GRT_CLOCK_FIRST_RES_AWARE=1: both phases route resistance-aware (FastRoute orders the clock nets first and lifts them to low-R
    # layers); KV hroot a5 A/B: t9 spread 170 -> 92 ps, FF internal hold -86 -> -60 ps, overflow 385 -> 382
    if {[info exists ::env(OT_GRT_CLOCK_FIRST_RES_AWARE)] && $::env(OT_GRT_CLOCK_FIRST_RES_AWARE) eq "1" && [lsearch -exact $args -resistance_aware] < 0} {
      lappend args -resistance_aware -res_aware_nets_percentage 0
    }
    set clk [nets]
    foreach n $clk { grt::add_net_to_route $n }
    set a1 $args
    set i [lsearch -exact $a1 -congestion_report_file]
    if {$i >= 0} { set a1 [lreplace $a1 [expr {$i + 1}] [expr {$i + 1}] "[file rootname [lindex $a1 [expr {$i + 1}]]]_clock_first.rpt"] }
    set cap [expr {[llength [info commands ::utl::teeStringBegin]] && [llength [info commands ::utl::teeStringEnd]]}]
    if {$cap} { ::utl::teeStringBegin }
    set rc1 [catch {uplevel 1 [list ::ot_gcf_gr_orig {*}$a1]} res1 opts1]
    set log1 [expr {$cap ? [::utl::teeStringEnd] : ""}]
    if {$rc1} { return -options $opts1 $res1 }
    ndr_loss $log1 $dir/5_1_grt.clock_ndr_loss.tsv
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
