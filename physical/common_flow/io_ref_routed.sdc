# FLOW-IOREF 2026-10-08: sign-off IO reference from the ROUTE'S OWN clock tree (rule H1 "mean FF insertion").
# Read LAST (after 6_final.sdc, SPEF, set_propagated_clock and every post-SDC) in a single-corner sign-off / hold-ECO
# session.  Every VIRTUAL clock (vclk, vclki, ot_lb_v_<clk>, nbr_clk, ...) is moved to the mean propagated clock
# arrival, IN THIS SESSION'S CORNER, at the boundary registers of its real clock (registers fed by a data input or
# feeding a data output -- ck_insertion.py's definition); IO delays and the H1 uncertainties (+50 sender / 25
# receiver) are untouched.  Why: the die clock plan aligns every block's nominal insertion, so the routed tree is the
# truth; the calibrate run's CTS (or an assumed) insertion is not (hbm_pkt_ii1r: vclk FF 363 from calibrate vs the
# routed FF mean ~307 -> output-port-only hold -43).  Only the insertion-reference virtual clocks (vclk*, ot_lb_v_*,
# nbr_clk) move; window clocks with explicit min/max source latency (io_clk, io_ci/io_co) are kept.  Virtual clock -> real clock: ot_lb_v_<name> / a name match, else
# the only real clock with register sinks, else core_clk for vclk*, else the dominant one (>= 4x the register sinks of any other); otherwise left unchanged (OT_IOREF skip).  Prints one OT_IOREF line per clock.
# MMFF-INSERTION 2026-10-08: in a MULTI-SCENE session (orfs_hold_mm.tcl: WC = TT/SS libs + BC = FF libs in one STA)
# `get_property <pin> arrival_max_rise` is the max over ALL scenes = the TT/SS arrival, not this mode's corner: the
# route-time FF scene set vclk 1.2x too late (hbm_vm8_nws_s2_hm25 4_1_cts: mm 455.7 = TT-only 455.7, FF-only 380.2 =
# calibrate 380) -> FF output hold over-repaired / input hold under-repaired by ~75 ps on every mm route.  The caller
# names its scene in ::ot_ioref_scene (ot_mm_sync: BC); arrivals are then read with report_arrival -scene (the max of
# the rise arrivals, = arrival_max_rise of a single-corner session).  A single-scene session is unchanged.
proc ot_ir_multi {} { expr {![catch {sta::multi_scene} m] && $m} }
# FLOW-FIX-0410 2026-10-09 (struct-close SC-4/SC-14): the insertion of a sink is the arrival of its ACTIVE transition,
# measured from the source edge that produces it.  Behind an odd number of clock inversions (ot_fwd_link_stage on
# fck = ~ck with negedge flops: every common-clock station) the pin RISE comes from the source FALL edge, so
# arrival_max_rise = T/2 + tree: dsfd_hstnh_515 read "vclk core_clk mean 603.1" for a ~190 ps tree and CTS hold repair
# chased FF -384.7 on all 515 outputs (RSZ-0060).  The active transition is the from-transition of the cell's
# clock->output arc ("Reg Clk to Q" / latch "En to Q"; cached per cell and pin); an arrival produced by the source
# fall edge has the half period (fall - rise of the waveform) removed, so the result stays on the rise-edge time base
# of every earlier reading.  A non-inverted posedge sink is unchanged; a negedge sink reads its fall tree (not its
# rise tree); a cell without a recognisable arc reads the transition produced by the source RISE edge.
set ::ot_ir_act [dict create]
proc ot_ir_active {p} {
  set c [get_cells -quiet -of_objects $p]
  if {![llength $c]} { return "" }
  set k "[get_property $c ref_name]/[get_property $p lib_pin_name]"
  if {[dict exists $::ot_ir_act $k]} { return [dict get $::ot_ir_act $k] }
  sta::redirect_string_begin
  catch {report_edges -from $p}
  set r [sta::redirect_string_end]
  set on 0; set fr {}
  foreach l [split $r "\n"] {
    if {[regexp {^\S} $l]} { set on [regexp {(Clk|En) to Q} $l]; continue }
    if {$on && [regexp {^\s+([\^v])\s+->} $l -> e]} { if {[lsearch -exact $fr $e] < 0} { lappend fr $e } }
  }
  set a [expr {[llength $fr] == 1 ? ([lindex $fr 0] eq "^" ? "r" : "f") : ""}]
  dict set ::ot_ir_act $k $a
  return $a
}
# {edge transition value} triples (edge ^ / v of the source clock, transition r / f at the pin, max arrival)
proc ot_ir_arrs {p cn} {
  if {![ot_ir_multi]} {
    set ar [get_property $p arrival_max_rise]; set af [get_property $p arrival_max_fall]
    set ok [expr {[string is double -strict $ar] && [string is double -strict $af]}]
    if {!$ok} {
      # one transition only: it is taken as produced by the source rise edge (pre-0410 reading)
      if {[string is double -strict $ar]} { return [list [list ^ r $ar]] }
      if {[string is double -strict $af]} { return [list [list ^ f $af]] }
      return {}
    }
    # single-scene property = latest arrival of each transition: the earlier of the two comes from the rise edge
    if {$ar <= $af} { return [list [list ^ r $ar] [list v f $af]] }
    return [list [list ^ f $af] [list v r $ar]]
  }
  set sc [expr {[info exists ::ot_ioref_scene] ? [list -scene $::ot_ioref_scene] : {}}]
  sta::redirect_string_begin
  catch {report_arrival {*}$sc -digits 4 $p}
  set r [sta::redirect_string_end]
  set out {}; set mine {}
  foreach {- ck e rv fv} [regexp -all -inline {\((\S+) ([\^v])\)\s+r\s+(\S+)\s+f\s+(\S+)} $r] {
    foreach {tr v} [list r $rv f $fv] {
      set x [lindex [split $v :] end]
      if {![string is double -strict $x]} continue
      lappend out [list $e $tr $x]
      if {$ck eq $cn} { lappend mine [list $e $tr $x] }
    }
  }
  return [expr {[llength $mine] ? $mine : $out}]
}
proc ot_ir_arr {p {cn ""}} {
  if {$cn eq ""} { set cn [get_full_name [lindex [get_clocks -quiet -of_objects $p] 0]] }
  set half 0.0
  # Clock_waveform / Clock_period are in seconds; get_property period is in user units (ps)
  if {$cn ne "" && ![catch {set c [get_clocks $cn]; list [$c waveform] [$c period] [get_property $c period]} w]} {
    lassign $w wf ps pu
    if {[llength $wf] >= 2 && $ps > 0} { set half [expr {([lindex $wf 1] - [lindex $wf 0]) * $pu / $ps}] } }
  set t [ot_ir_active $p]
  set v ""; set shifted 0
  foreach a [ot_ir_arrs $p $cn] {
    lassign $a e tr x
    if {$t eq "" ? ($e ne "^") : ($tr ne $t)} continue
    set y [expr {$e eq "v" ? $x - $half : $x}]
    if {$v eq "" || $y > $v} { set v $y; set shifted [expr {$e eq "v"}] }
  }
  # for the caller's census: {active transition (r / f / "" = no clock->output arc), half period removed}
  set ::ot_ir_last [list $t $shifted]
  return $v
}
if {[ot_ir_multi] && ![info exists ::ot_ioref_scene]} {
  # a run whose own orfs_hold_mm.tcl predates ::ot_ioref_scene: its hold scene is named BC (orfs_hold_mm) or ff (hold_eco)
  foreach ot_ir_n {BC ff} { if {![catch {sta::find_scene $ot_ir_n} ot_ir_o] && $ot_ir_o ne "" && $ot_ir_o ne "NULL"} { set ::ot_ioref_scene $ot_ir_n; break } }
}
if {[ot_ir_multi]} {
  if {[info exists ::ot_ioref_scene]} { puts "OT_IOREF multi-scene session: arrivals of scene $::ot_ioref_scene" } else {
    puts "OT_IOREF WARNING: multi-scene session without ::ot_ioref_scene: arrivals of the command scene" }
}
set ot_ir_real {}
foreach c [all_clocks] { if {[llength [get_property $c sources]]} { lappend ot_ir_real [get_full_name $c] } }
# S81-TAIL 2026-10-08: a data input delay on a REAL clock's source port (route SDCs that budget every non-core input,
# e.g. s81ph dsfd_ctrl_pc: set_input_delay 316.7 -clock vclk on ckh[0] = hbm_clk) makes the register clock pins of
# that clock carry a DATA arrival (vclk latency + input delay + tree), and arrival_max_rise below returns it instead
# of the clock arrival: hbm_clk measured 796 TT / 752 FF vs the real tree 226 / 188 -> fake i2r TT -556 / out FF -487.
# A clock source port times no data, so its input delays are dropped before the measurement.
foreach cn $ot_ir_real {
  foreach s [get_property [get_clocks $cn] sources] {
    set sn [get_full_name $s]
    if {![llength [get_ports -quiet $sn]]} continue
    # unset_input_delay without -clock only drops clock-less delays: one call per reference clock and edge
    foreach ot_ir_c [all_clocks] {
      unset_input_delay -clock $ot_ir_c [get_ports $sn]; unset_input_delay -clock $ot_ir_c -clock_fall [get_ports $sn]
    }
    unset_input_delay [get_ports $sn]
    puts "OT_IOREF clock-port $sn ($cn): data input delays dropped"
  }
}
set ot_ir_bnd [dict create]
set ot_ir_din [all_inputs -no_clocks]
if {[llength $ot_ir_din]} {
  foreach pe [find_timing_paths -path_delay max -from $ot_ir_din -to [all_registers -data_pins] -group_path_count 200000 -endpoint_path_count 1] {
    dict set ot_ir_bnd [regsub {/[^/]+$} [get_full_name [get_property $pe endpoint]] {}] 1 }
}
if {[llength [all_outputs]]} {
  foreach pe [find_timing_paths -path_delay max -from [all_registers -clock_pins] -to [all_outputs] -group_path_count 200000 -endpoint_path_count 100000] {
    dict set ot_ir_bnd [regsub {/[^/]+$} [get_full_name [get_property $pe startpoint]] {}] 1 }
}
set ot_ir_ins [dict create]
set ::ot_ir_moved [dict create]
set ot_ir_nreg [dict create]
foreach cn $ot_ir_real {
  set b {}; set a {}
  array unset ot_ir_e; array set ot_ir_e {neg 0 noarc 0 half 0}
  foreach p [all_registers -clock_pins -clock [get_clocks $cn]] {
    set v [ot_ir_arr $p $cn]
    if {$v eq "" || $v eq "INF" || $v eq "-INF"} continue
    lappend a $v
    if {[dict exists $ot_ir_bnd [regsub {/[^/]+$} [get_full_name $p] {}]]} {
      lappend b $v
      lassign $::ot_ir_last t sh
      if {$t eq "f"} { incr ot_ir_e(neg) }
      if {$t eq ""} { incr ot_ir_e(noarc) }
      if {$sh} { incr ot_ir_e(half) }
    }
  }
  set use [expr {[llength $b] ? $b : $a}]
  if {![llength $use]} continue
  set s 0.0; foreach v $use { set s [expr {$s + $v}] }
  set u [lsort -real $use]
  dict set ot_ir_ins $cn [list [expr {$s / [llength $use]}] [lindex $u 0] [lindex $u end] [llength $use] [expr {[llength $b] ? "boundary" : "all"}]]
  dict set ot_ir_nreg $cn [llength $a]
  # census of the boundary sinks: negedge-active, no clock->output arc, read through an odd clock inversion (the half
  # period was removed; a pre-0410 reading of these sinks was T/2 late)
  puts [format "OT_IOREF_EDGE %s boundary %d negedge %d noarc %d inverted %d" $cn [llength $b] $ot_ir_e(neg) $ot_ir_e(noarc) $ot_ir_e(half)]
}
foreach c [all_clocks] {
  if {[llength [get_property $c sources]]} continue
  set vn [get_full_name $c]; set rc ""
  if {![regexp {^(vclk[A-Za-z0-9_]*|ot_lb_v_.*|nbr_clk)$} $vn]} { puts "OT_IOREF keep $vn (not an insertion-reference clock)"; continue }
  foreach cn [dict keys $ot_ir_ins] { if {$vn eq "ot_lb_v_$cn"} { set rc $cn } }
  if {$rc eq ""} { foreach cn [dict keys $ot_ir_ins] { if {[string first $cn $vn] >= 0} { set rc $cn } } }
  if {$rc eq "" && [dict size $ot_ir_ins] == 1} { set rc [lindex [dict keys $ot_ir_ins] 0] }
  # DRIVE-1113 2026-10-08: several real clocks (e.g. hfd_svc_SW_s3: core_clk + forwarded input clocks fq4 / fe that only
  # write two-clock FIFOs) -> the insertion reference is the DOMINANT real clock: the one with >= 4x the register sinks
  # of every other (the forwarded clocks clock a few hundred FIFO flops).  Before this every such block skipped vclk.
  # FWDCLK-SWEEP 2026-10-08: the budget SDC convention makes vclk / vclki the IO reference of core_clk (forwarded input
  # clocks are declared asynchronous to {core_clk vclk}); hfd_index_q_b0 (core_clk + fk0 / fk1 key-capture clocks) is
  # below the 4x dominance ratio and was skipped.  A vclk* clock resolves to core_clk when that real clock exists.
  # DRIVE-1243 2026-10-08: a vclk_<x> whose PERIOD equals exactly one real clock's is that clock's reference (s81ph
  # dsfd_capt_grp: vclk_s = ser_clk period 4/3 core, IO of the ser domain; the core_clk fallback below moved it to the
  # core_clk FF mean 244 instead of the ser_clk 229).  Checked before the vclk* -> core_clk fallback.
  if {$rc eq "" && [string match vclk* $vn]} {
    set ot_ir_pm {}
    foreach cn [dict keys $ot_ir_ins] { if {abs([get_property [get_clocks $cn] period] - [get_property $c period]) < 0.001} { lappend ot_ir_pm $cn } }
    if {[llength $ot_ir_pm] == 1} { set rc [lindex $ot_ir_pm 0] }
  }
  if {$rc eq "" && [string match vclk* $vn] && [dict exists $ot_ir_ins core_clk]} { set rc core_clk }
  if {$rc eq "" && [dict size $ot_ir_nreg] > 1} {
    set ot_ir_srt [lsort -stride 2 -index 1 -integer -decreasing $ot_ir_nreg]
    if {[lindex $ot_ir_srt 1] >= 4 * [lindex $ot_ir_srt 3]} { set rc [lindex $ot_ir_srt 0] }
  }
  if {$rc eq ""} { puts "OT_IOREF skip $vn (no unique real clock)"; continue }
  lassign [dict get $ot_ir_ins $rc] L lo hi n kind
  set_clock_latency -source 0 [get_clocks $vn]
  set_clock_latency $L [get_clocks $vn]
  puts [format "OT_IOREF %s %s mean %.1f min %.1f max %.1f n %d %s" $vn $rc $L $lo $hi $n $kind]
  dict set ::ot_ir_moved $vn [list $L $rc]
}
# PINFLOP-INPUT (drive-0849 2026-10-10, coordinator class-1 extension): ROUTE-TIME ONLY (env OT_IOREF_INPUT_PF=1, exported
# by the closure loop for calibrate / route stages; never set for the verdict re-STA or the post-route ECOs).  The input
# side of every moved insertion-reference clock is re-referenced from the boundary-register mean L to the mean arrival
# Lpf (this scene) of the INPUT PIN FLOPS (input port -> D directly or through <= 2 buffers): each input delay on that
# clock is re-issued at value + (Lpf - L).  Outputs keep L.  Why: the FF-scene hold repair of the route_mtp /
# hbm_accel_smh / dsrom qs / markov-driver recipes saw inputs referenced to the mean of ALL boundary registers, hundreds of
# ps before the capture pin flops' clock, and flooded (39 EARLY_FAIL_HOLD; ehash / core18 closed only after naming the
# pin flops by hand).  The verdict still re-times at the routed boundary mean.  No pin flops / any error -> unchanged.
if {[info exists ::env(OT_IOREF_INPUT_PF)] && $::env(OT_IOREF_INPUT_PF) eq "1" && [info exists ::ot_ir_moved] && [dict size $::ot_ir_moved]} {
  if {[catch {
    set ot_pf_seen [dict create]; set ot_pf_pins {}
    foreach port [all_inputs -no_clocks] {
      set nets [get_nets -quiet [get_full_name $port]]
      for {set hop 0} {$hop < 3 && [llength $nets]} {incr hop} {
        set next {}
        foreach nn $nets {
          foreach pin [get_pins -quiet -of_objects $nn] {
            if {[string first / [get_full_name $pin]] < 0} continue
            if {[get_property $pin direction] ne "input"} continue
            set c [get_cells -quiet -of_objects $pin]
            if {![llength $c]} continue
            set fn [get_full_name $c]
            set ck [get_pins -quiet "$fn/CLK"]
            if {[llength $ck]} {
              if {[get_property $pin lib_pin_name] ne "CLK" && ![dict exists $ot_pf_seen $fn]} { dict set ot_pf_seen $fn 1; lappend ot_pf_pins $ck }
            } elseif {[regexp {^(BUF|HB)} [get_property $c ref_name]]} {
              foreach op [get_pins -quiet -of_objects $c] { if {[get_property $op direction] eq "output"} { lappend next [get_nets -quiet -of_objects $op] } }
            }
          }
        }
        set nets $next
      }
    }
    set ot_pf_v {}
    set ot_pf_rc [lindex [lindex [dict values $::ot_ir_moved] 0] 1]
    foreach p $ot_pf_pins { set v [ot_ir_arr $p $ot_pf_rc]; if {$v ne "" && $v ne "INF" && $v ne "-INF" && [string is double -strict $v]} { lappend ot_pf_v $v } }
    if {[llength $ot_pf_v]} {
      set s 0.0; foreach v $ot_pf_v { set s [expr {$s + $v}] }
      set Lpf [expr {$s / [llength $ot_pf_v]}]
      set ot_pf_tmp [file join [expr {[info exists ::env(TMPDIR)] ? $::env(TMPDIR) : "/tmp"}] "ot_pf_[pid]_[clock clicks].sdc"]
      write_sdc $ot_pf_tmp
      set fh [open $ot_pf_tmp r]; set txt [read $fh]; close $fh; file delete $ot_pf_tmp
      set redo {}; set ports [dict create]
      foreach ln [split $txt "\n"] {
        if {![regexp {^set_input_delay\s+(\S+)\s+(.*-clock \[get_clocks \{([^\}]+)\}\].*?)(\[get_ports .*\])\s*$} $ln -> val mid ck tgt]} continue
        if {![dict exists $::ot_ir_moved $ck]} continue
        set d [expr {$Lpf - [lindex [dict get $::ot_ir_moved $ck] 0]}]
        lappend redo [list [expr {$val + $d}] $mid $tgt]
        dict set ports "$ck|$tgt" [list $ck $tgt]
      }
      dict for {k v} $ports { lassign $v ck tgt; unset_input_delay -clock $ck [subst $tgt]; unset_input_delay -clock $ck -clock_fall [subst $tgt] }
      foreach r $redo { lassign $r val mid tgt; eval "set_input_delay $val $mid $tgt" }
      puts [format "OT_IOREF_PF input pin flops %d mean %.1f: %d input delays re-referenced (ports %d)" [llength $ot_pf_v] $Lpf [llength $redo] [dict size $ports]]
    } else { puts "OT_IOREF_PF no input pin flops: input reference unchanged" }
  } ot_pf_err]} { puts "OT_IOREF_PF WARNING: $ot_pf_err -- input reference unchanged"; if {[info exists ::env(OT_IOREF_PF_DEBUG)]} { puts $::errorInfo } }
}
