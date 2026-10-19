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
# Use the same actual generated-clock ancestry and physical tags as CE/native R.
# BEGIN shared clock_family.tcl (checked byte-for-byte by tests)
# Actual OpenSTA clock ancestry and physical propagated-clock measurements.
# OpenSTA's Clock wrapper has no master accessor. Its canonical SDC exporter
# resolves inferred masters; evaluate only its generated-clock declarations in
# an isolated safe interpreter, never replay constraints in the live session.
proc ot_cf_record {args} {
  set ni [lsearch -exact $args -name]; set mi [lsearch -exact $args -master_clock]
  set si [lsearch -exact $args -source]
  if {$ni < 0 || $mi < 0 || $si < 0} {error "OT_CLOCK_FAMILY: canonical generated clock lacks resolved name/master/source"}
  set name [lindex $args [expr {$ni+1}]]
  set master [lindex $args [expr {$mi+1}]]; set source [lindex $args [expr {$si+1}]]
  if {[llength $master] != 1 || [llength $source] != 1 || [dict exists $::ot_cf_master $name]} {
    error "OT_CLOCK_FAMILY: ambiguous generated clock $name"
  }
  set parent [get_full_name $master]
  if {[sta::object_type $source] eq "Port"} {set source [sta::get_port_pin $source]}
  set owners {}; foreach c [get_property $source clocks] {lappend owners [get_full_name $c]}
  if {[lsort -unique $owners] ne [list $parent]} {
    error "OT_CLOCK_FAMILY: generated source of $name has owners $owners, expected $parent"
  }
  dict set ::ot_cf_master $name $parent
}
proc ot_cf_refresh {} {
  set ::ot_cf_master {}; set ::ot_cf_active_cache {}; set generated {}
  foreach c [all_clocks] {if {[$c is_generated]} {lappend generated [get_full_name $c]}}
  if {![llength $generated]} {return}
  sta::update_generated_clks
  # Iterating paths alone does not initialize generated source insertion.
  # A native timing search fills the complete root-to-bank physical arrivals.
  find_timing_paths -group_path_count 1
  set fd [file tempfile path ot-clock-family-]; close $fd
  set ip [interp create -safe]
  try {
    write_sdc $path
    foreach cmd {get_ports get_pins get_clocks} {interp alias $ip $cmd {} $cmd}
    interp alias $ip create_generated_clock {} ot_cf_record
    set fd [open $path r]; set text [read $fd]; close $fd
    set command {}
    foreach line [split $text \n] {
      append command $line \n
      if {![info complete $command]} continue
      if {[regexp {^\s*create_generated_clock\s} $command]} {interp eval $ip $command}
      set command {}
    }
    if {[string trim $command] ne ""} {error "OT_CLOCK_FAMILY: incomplete canonical SDC"}
    if {[lsort [dict keys $::ot_cf_master]] ne [lsort $generated]} {error "OT_CLOCK_FAMILY: incomplete generated-clock ancestry"}
    foreach c $generated {ot_cf_root $c}
  } finally {interp delete $ip; file delete -force $path}
}
proc ot_cf_root {name} {
  set seen {}
  while {[dict exists $::ot_cf_master $name]} {
    if {$name in $seen} {error "OT_CLOCK_FAMILY: ancestry cycle $name"}
    lappend seen $name; set name [dict get $::ot_cf_master $name]
  }
  set c [get_clocks -quiet $name]
  if {[llength $c] != 1 || [$c is_generated]} {error "OT_CLOCK_FAMILY: unresolved root $name"}
  return $name
}
proc ot_cf_pins {root} {
  set name [get_full_name $root]
  if {[ot_cf_root $name] ne $name} {error "OT_CLOCK_FAMILY: requested root $name is generated"}
  set pins {}; set owners {}
  foreach c [all_clocks] {
    if {[ot_cf_root [get_full_name $c]] ne $name} continue
    foreach p [all_registers -clock_pins -clock $c] {
      set pn [get_full_name $p]
      set actual {}; foreach owner [get_property $p clocks] {lappend actual [get_full_name $owner]}
      if {[llength [lsort -unique $actual]] != 1} {
        error "OT_CLOCK_FAMILY: ambiguous clock sink $pn ($actual)"
      }
      if {[ot_cf_root [lindex $actual 0]] ne $name} {error "OT_CLOCK_FAMILY: foreign sink $pn"}
      if {[lindex $actual 0] ne [get_full_name $c]} continue
      if {[dict exists $owners $pn]} {error "OT_CLOCK_FAMILY: duplicate sink $pn"}
      dict set owners $pn $c; lappend pins $p
    }
  }
  return [list $pins $owners]
}
proc ot_cf_active {p} {
  set cell [get_cells -of_objects $p]
  set key [list [get_property $cell ref_name] [get_property $p lib_pin_name]]
  if {[dict exists $::ot_cf_active_cache $key]} {return [dict get $::ot_cf_active_cache $key]}
  sta::redirect_string_begin
  set failed [catch {report_edges -from $p} message]
  set report [sta::redirect_string_end]; set on 0; set edges {}
  if {$failed} {error "OT_CLOCK_FAMILY: active-edge query failed [get_full_name $p]: $message"}
  foreach line [split $report \n] {
    if {[regexp {^\S} $line]} {set on [regexp {(Clk|En) to Q} $line]; continue}
    if {$on && [regexp {^\s+([\^v])\s+->} $line -> edge] && $edge ni $edges} {lappend edges $edge}
  }
  if {![llength $edges] && [llength [info commands ord::get_db]]} {
    # Check-only hard entries (notably SRAM write clocks) have no clock-to-Q
    # arc. Only an actual physical BLOCK with unique loaded Liberty clock
    # timing-check edges is supported; missing soft-register arcs still fail.
    set master [[ord::get_db] findMaster [get_property $cell ref_name]]
    if {$master ne "NULL" && [$master isBlock]} {
      set on 0
      foreach line [split $report \n] {
        if {[regexp {^\S} $line]} {set on [regexp { (setup|hold|recovery|removal)$} $line]; continue}
        if {$on && [regexp {^\s+([\^v])\s+->} $line -> edge] && $edge ni $edges} {lappend edges $edge}
      }
    }
  }
  if {[llength $edges] != 1} {error "OT_CLOCK_FAMILY: missing unique active clock edge [get_full_name $p] ($edges)"}
  set active [expr {[lindex $edges 0] eq "^" ? "rise" : "fall"}]
  dict set ::ot_cf_active_cache $key $active
  return $active
}
proc ot_cf_wire {pin clock {scene {}}} {
  if {$scene eq ""} {set scene [get_property [sta::cmd_scene] name]}
  set cn [get_full_name $clock]; set waveform {}
  foreach time [$clock waveform] {lappend waveform [sta::time_sta_ui $time]}
  if {[llength $waveform] != 2} {error "OT_CLOCK_FAMILY: invalid waveform $cn"}
  foreach time $waveform {if {![string is double -strict $time] || [regexp -nocase {inf|nan} $time]} {error "OT_CLOCK_FAMILY: nonfinite waveform $cn"}}
  set transition [ot_cf_active $pin]; set marker [expr {$transition eq "rise" ? "^max" : "vmax"}]
  set values {}
  foreach vertex [$pin vertices] {
    if {$vertex eq "NULL"} continue
    set paths [$vertex path_iterator $transition max]
    while {[$paths has_next]} {
      set path [$paths next]; set tag [$path tag]; set edge [lindex $tag 4]
      if {[lindex $tag 1] ne $scene || [lindex $tag 2] ne $marker || [lindex $tag 3] ne $cn || $edge ni {^ v} || [string first "(clock prop)" $tag] < 0} continue
      set arrival [sta::time_sta_ui [$path arrival]]
      if {![string is double -strict $arrival] || [regexp -nocase {inf|nan} $arrival]} {$paths finish; error "OT_CLOCK_FAMILY: nonfinite clock arrival [get_full_name $pin]"}
      lappend values [expr {$arrival-[lindex $waveform [expr {$edge eq "^" ? 0 : 1}]]}]
    }
    $paths finish
  }
  if {[llength $values] != 1} {error "OT_CLOCK_FAMILY: missing unique physical clock arrival [get_full_name $pin] clock=$cn scene=$scene"}
  return [lindex $values 0]
}
# END shared clock_family.tcl
ot_cf_refresh
proc ot_ir_arr {p {cn ""}} {
  set owners [get_property $p clocks]
  if {[llength $owners] != 1 || ($cn ne "" && [ot_cf_root [get_full_name $owners]] ne $cn)} {
    error "OT_IOREF: wrong/ambiguous clock ownership [get_full_name $p]"
  }
  set scene {}; if {[info exists ::ot_ioref_scene]} {set scene $::ot_ioref_scene}
  set ::ot_ir_last [list [expr {[ot_cf_active $p] eq "fall" ? "f" : "r"}] 0]
  return [ot_cf_wire $p $owners $scene]
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
foreach c [all_clocks] { if {![$c is_generated] && [llength [get_property $c sources]]} { lappend ot_ir_real [get_full_name $c] } }
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
set ot_ir_real_src {}
foreach cn $ot_ir_real { foreach s [get_property [get_clocks $cn] sources] { lappend ot_ir_real_src [get_full_name $s] } }
# Structural boundary membership survives false/disabled data paths; async controls are excluded.
proc ot_ir_boundary_cells {} {
  set regs {}
  foreach p [all_registers -clock_pins] {
    set n [get_full_name $p]
    dict set regs [regsub {/[^/]+$} $n {}] $n
  }

set bnd {}
set ot_ck_data {}
set ot_ck_async {}
foreach p [all_registers -async_pins] { dict set ot_ck_async [get_full_name $p] 1 }
foreach p [all_registers -data_pins] {
  set n [get_full_name $p]
  if {![dict exists $ot_ck_async $n]} { dict set ot_ck_data $n 1 }
}
set din [all_inputs -no_clocks]
if {[llength $din]} {
  foreach p [get_fanout -from $din -flat -endpoints_only -trace_arcs all] {
    set n [get_full_name $p]
    if {![dict exists $ot_ck_data $n]} continue
    set i [regsub {/[^/]+$} $n {}]
    if {[dict exists $regs $i]} { dict set bnd $i 1 }
  }
}
set dout [all_outputs]
if {[llength $dout]} {
  foreach p [get_fanin -to $dout -flat -startpoints_only -trace_arcs all] {
    set i [regsub {/[^/]+$} [get_full_name $p] {}]
    if {[dict exists $regs $i]} { dict set bnd $i 1 }
  }
}

  return $bnd
}
set ot_ir_bnd [ot_ir_boundary_cells]
# CLOCK-CLASS 2026-10-13 (export-sdc; smh_tile_eg r10 diagnosis codex/hbm-sm-cluster 4a8f09870): ONE boundary number per
# clock is wrong for a block whose boundary registers sit on two clock classes of the same port clock -- smh_tile_eg:
# 9 flops + the ICG on the raw clk net (0.5 ps) beside 967 flops behind the ICG and the spine (TT 1871..1902): the
# reference (boundary mean 1425.5; link-budget midrange 950.6) matched no flop and the raw-launched cgo output read a
# false -1381.5 ps hold, raw-captured cgi a false -1533 setup.  The die delivers each LINK's two ends on matching
# classes (cgo -> next tile's cgi: raw to raw), so each port is referenced to the class of the registers that launch /
# capture it:
#   * the standard-cell boundary registers of a real clock are split into classes wherever two neighbouring arrivals
#     are more than OT_IOREF_CLASS_GAP apart (default the larger of 0.25 T and 150 ps: far beyond any tree skew);
#   * the virtual clocks move to the DOMINANT class's mean (most boundary registers; one class = the old behaviour,
#     bit for bit);
#   * a port whose registers are all in another class k keeps its clock and has every IO delay on a moved virtual clock
#     or on the real clock itself (references baked into the value) re-issued at  input: value + (Lk - L0)   output: value - (Lk - L0)  (-min and -max alike) = referenced to Lk;
#   * a port reaching registers of SEVERAL classes cannot have one reference: it stays on the dominant class and is
#     reported (OT_IOREF_CLASS mixed ...): that is a real structural finding (smh rst_n -> ICG ENA + gated flops).
# The applied adjustment is kept in ::ot_cls_adj ("in|out,clock,port"), so a second read of this file (the verdict reads
# it twice) or physical/common_flow/link_budget_consistent.sdc's own class split before it is not applied twice.
# OT_IOREF_CLASS=0 (env) disables the split.  Hard-macro clock pins never form a class (their internal insertion is
# in the view).
proc ot_ir_env {n d} { expr {[info exists ::env($n)] && $::env($n) ne "" ? $::env($n) : $d} }
# sorted arrivals -> list of {lo hi} class intervals
proc ot_ir_split {vals gap} {
  set out {}; set lo ""; set hi ""
  foreach v [lsort -real $vals] {
    if {$lo eq ""} { set lo $v; set hi $v; continue }
    if {$v - $hi > $gap} { lappend out [list $lo $hi]; set lo $v }
    set hi $v
  }
  if {$lo ne ""} { lappend out [list $lo $hi] }
  return $out
}
proc ot_ir_class_of {v cls} {
  # nearest class interval
  set best 0; set bd ""
  set i 0
  foreach c $cls {
    lassign $c lo hi
    set d [expr {$v < $lo ? $lo - $v : ($v > $hi ? $v - $hi : 0.0)}]
    if {$bd eq "" || $d < $bd} { set bd $d; set best $i }
    incr i
  }
  return $best
}
proc ot_ir_is_std_reg {p} {
  set c [get_cells -quiet -of_objects $p]
  if {![llength $c]} { return 0 }
  regexp {^(DFF|DHL|DLL|SDF|ASYNC|ICG)} [get_property $c ref_name]
}
set ot_ir_ins [dict create]
set ::ot_ir_moved [dict create]
set ot_ir_nreg [dict create]
set ot_ir_cls [dict create]    ;# real clock -> {classes dominant {class -> mean lo hi n}}  (only with >= 2 classes)
set ot_ir_arrof [dict create]  ;# real clock -> {register cell -> clock arrival}
foreach cn $ot_ir_real {
  set b {}; set a {}; set ot_ir_bs {}; set ot_ir_bo {}; set ot_ir_ao [dict create]
  array unset ot_ir_e; array set ot_ir_e {neg 0 noarc 0 half 0}
  lassign [ot_cf_pins [get_clocks $cn]] ot_ir_family_pins ot_ir_family_owners
  foreach p $ot_ir_family_pins {
    set v [ot_ir_arr $p $cn]
    if {$v eq "" || $v eq "INF" || $v eq "-INF"} continue
    lappend a $v
    dict set ot_ir_ao [regsub {/[^/]+$} [get_full_name $p] {}] $v
    if {[dict exists $ot_ir_bnd [regsub {/[^/]+$} [get_full_name $p] {}]]} {
      lappend b $v
      if {[ot_ir_is_std_reg $p]} { lappend ot_ir_bs $v } else { lappend ot_ir_bo $v }
      lassign $::ot_ir_last t sh
      if {$t eq "f"} { incr ot_ir_e(neg) }
      if {$t eq ""} { incr ot_ir_e(noarc) }
      if {$sh} { incr ot_ir_e(half) }
    }
  }
  set use [expr {[llength $b] ? $b : $a}]
  if {![llength $use]} continue
  dict set ot_ir_arrof $cn $ot_ir_ao
  if {[ot_ir_env OT_IOREF_CLASS 1] ne "0" && [llength $ot_ir_bs] > 1} {
    set ot_ir_T [get_property [get_clocks $cn] period]
    set ot_ir_gap [ot_ir_env OT_IOREF_CLASS_GAP [expr {max(0.25 * $ot_ir_T, 150.0)}]]
    set ot_ir_cl [ot_ir_split $ot_ir_bs $ot_ir_gap]
    if {[llength $ot_ir_cl] > 1} {
      # per class: the standard-cell boundary registers in it; the dominant class also keeps every other boundary sink
      set ot_ir_m [dict create]
      foreach v $ot_ir_bs { dict lappend ot_ir_m [ot_ir_class_of $v $ot_ir_cl] $v }
      set ot_ir_dom 0
      dict for {k vs} $ot_ir_m { if {[llength $vs] > [llength [dict get $ot_ir_m $ot_ir_dom]]} { set ot_ir_dom $k } }
      foreach v $ot_ir_bo { dict lappend ot_ir_m $ot_ir_dom $v }
      set ot_ir_st [dict create]
      dict for {k vs} $ot_ir_m {
        set s 0.0; foreach v $vs { set s [expr {$s + $v}] }
        set u [lsort -real $vs]
        dict set ot_ir_st $k [list [expr {$s / [llength $vs]}] [lindex $u 0] [lindex $u end] [llength $vs]]
      }
      dict set ot_ir_cls $cn [list $ot_ir_cl $ot_ir_dom $ot_ir_st]
      set use [dict get $ot_ir_m $ot_ir_dom]
    }
  }
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
# CLOCK-CLASS: re-reference the ports of the non-dominant classes (see above)
if {![info exists ::ot_cls_adj]} { set ::ot_cls_adj [dict create] }
set ot_ir_want [dict create]   ;# "in|out,virtual clock,port" -> adjustment wanted now
proc ot_ir_port_classes {port dir cn cls arrof} {
  # classes of the registers of real clock CN that PORT reaches (in) / is launched from (out)
  set ks [dict create]
  if {$dir eq "in"} { set pins [get_fanout -from $port -flat -endpoints_only] } else { set pins [get_fanin -to $port -flat -startpoints_only] }
  foreach q $pins {
    set n [get_full_name $q]
    if {[string first / $n] < 0} continue
    set c [regsub {/[^/]+$} $n {}]
    if {[dict exists $arrof $c]} { dict set ks [ot_ir_class_of [dict get $arrof $c] $cls] 1 }
  }
  return [lsort -integer [dict keys $ks]]
}
dict for {ot_ir_rc ot_ir_c} $ot_ir_cls {
  lassign $ot_ir_c ot_ir_cl ot_ir_dom ot_ir_st
  set ot_ir_ao [dict get $ot_ir_arrof $ot_ir_rc]
  set ot_ir_L0 [lindex [dict get $ot_ir_st $ot_ir_dom] 0]
  set ot_ir_vcs {}
  # the real clock itself too: a sign-off SDC that bakes the reference into delays on the real clock (ref_tile /
  # qwen_die_masters io_ref_skew.sdc: input max = 0.2 T + L(median pin flop) + skew on core_clk; smh cgi 2139.4 = the
  # gated pin-flop median, captured by raw flops) is moved by the same class distance
  set ot_ir_vcs [list $ot_ir_rc]
  dict for {vn v} $::ot_ir_moved { if {[lindex $v 1] eq $ot_ir_rc} { lappend ot_ir_vcs $vn } }
  # candidate ports: those touching a non-dominant boundary register (one fan-in / fan-out sweep per class)
  set ot_ir_ci [dict create]; set ot_ir_co [dict create]
  dict for {c v} $ot_ir_ao {
    if {![dict exists $ot_ir_bnd $c]} continue
    set k [ot_ir_class_of $v $ot_ir_cl]
    if {$k == $ot_ir_dom} continue
    set cell [get_cells -quiet $c]
    if {![llength $cell] || ![regexp {^(DFF|DHL|DLL|SDF|ASYNC|ICG)} [get_property $cell ref_name]]} continue
    foreach q [get_pins -quiet -of_objects $cell] {
      set dq [get_property $q direction]
      if {$dq eq "input"} {
        foreach s [get_fanin -to $q -flat -startpoints_only] { set sn [get_full_name $s]; if {[string first / $sn] < 0 && [llength [get_ports -quiet $sn]]} { dict set ot_ir_ci $sn 1 } }
      } elseif {$dq eq "output"} {
        foreach s [get_fanout -from $q -flat -endpoints_only] { set sn [get_full_name $s]; if {[string first / $sn] < 0 && [llength [get_ports -quiet $sn]]} { dict set ot_ir_co $sn 1 } }
      }
    }
  }
  set ot_ir_cnt [dict create]; set ot_ir_mixed {}
  foreach {dir cand} [list in $ot_ir_ci out $ot_ir_co] {
    foreach pn [dict keys $cand] {
      set port [get_ports $pn]
      if {[get_property $port direction] ne [expr {$dir eq "in" ? "input" : "output"}]} continue
      if {[lsearch -exact $ot_ir_real_src $pn] >= 0} continue
      set ks [ot_ir_port_classes $port $dir $ot_ir_rc $ot_ir_cl $ot_ir_ao]
      if {[llength $ks] != 1} { lappend ot_ir_mixed "$pn\($dir: [join $ks +]\)"; continue }
      set k [lindex $ks 0]
      if {$k == $ot_ir_dom} continue
      set d [expr {[lindex [dict get $ot_ir_st $k] 0] - $ot_ir_L0}]
      foreach vn $ot_ir_vcs { dict set ot_ir_want "$dir,$vn,$pn" [expr {$dir eq "in" ? $d : -$d}] }
      dict incr ot_ir_cnt "$k,$dir"
    }
  }
  foreach k [lsort -integer [dict keys $ot_ir_st]] {
    lassign [dict get $ot_ir_st $k] L lo hi n
    puts [format "OT_IOREF_CLASS %s class %d%s mean %.1f min %.1f max %.1f n %d ports_in %d ports_out %d" $ot_ir_rc $k \
      [expr {$k == $ot_ir_dom ? " dominant" : ""}] $L $lo $hi $n \
      [expr {[dict exists $ot_ir_cnt "$k,in"] ? [dict get $ot_ir_cnt "$k,in"] : 0}] [expr {[dict exists $ot_ir_cnt "$k,out"] ? [dict get $ot_ir_cnt "$k,out"] : 0}]]
  }
  if {[llength $ot_ir_mixed]} { puts "OT_IOREF_CLASS $ot_ir_rc mixed [llength $ot_ir_mixed] ports on several classes (kept on the dominant class): [lrange $ot_ir_mixed 0 7]" }
}
# apply: every (port, virtual clock) whose wanted adjustment differs from the one already in its delays
set ot_ir_todo [dict create]
dict for {k d} $ot_ir_want { if {![dict exists $::ot_cls_adj $k] || abs([dict get $::ot_cls_adj $k] - $d) > 1e-6} { dict set ot_ir_todo $k $d } }
dict for {k d} $::ot_cls_adj { if {![dict exists $ot_ir_want $k] && abs($d) > 1e-6} { dict set ot_ir_todo $k 0.0 } }
if {[dict size $ot_ir_todo]} {
  set ot_ir_tmp [file join [expr {[info exists ::env(TMPDIR)] ? $::env(TMPDIR) : "/tmp"}] "ot_cls_[pid]_[clock clicks].sdc"]
  write_sdc $ot_ir_tmp
  set fh [open $ot_ir_tmp r]; set ot_ir_txt [read $fh]; close $fh; file delete $ot_ir_tmp
  set ot_ir_redo {}; set ot_ir_un [dict create]
  foreach ln [split $ot_ir_txt "\n"] {
    if {![regexp {^set_(input|output)_delay\s+(\S+)\s+(.*-clock \[get_clocks \{([^\}]+)\}\].*?)(\[get_ports \{(.+)\}\])\s*$} $ln -> io val mid ck tgt pn]} continue
    set k "[expr {$io eq "input" ? "in" : "out"}],$ck,$pn"
    if {![dict exists $ot_ir_todo $k]} continue
    set prev [expr {[dict exists $::ot_cls_adj $k] ? [dict get $::ot_cls_adj $k] : 0.0}]
    lappend ot_ir_redo [list $io [expr {$val - $prev + [dict get $ot_ir_todo $k]}] $mid $tgt]
    dict set ot_ir_un $k [list $io $ck $pn]
  }
  dict for {k v} $ot_ir_un {
    lassign $v io ck pn
    unset_${io}_delay -clock $ck [get_ports $pn]; unset_${io}_delay -clock $ck -clock_fall [get_ports $pn]
  }
  foreach r $ot_ir_redo { lassign $r io val mid tgt; eval "set_${io}_delay $val $mid $tgt" }
  dict for {k d} $ot_ir_todo { dict set ::ot_cls_adj $k $d }
  puts [format "OT_IOREF_CLASS %d IO delays re-referenced (%d port/clock pairs)" [llength $ot_ir_redo] [dict size $ot_ir_un]]
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
    # PF-HOLDPAD (NATIVE-REF 2026-10-18): the pin-flop search of physical/qwen_die_masters/pinflop_ref.tcl (single-load
    # hold-pad chains past hop 3, hard-child clock pins at + internal insertion) when that file is reachable (the
    # shipped {CL} copy beside this one, the repo / job source tree); else the original 3-hop search below
    if {[info procs ot_pf_lib_ins] eq ""} {
      set ot_pf_here [expr {[catch {file dirname [file normalize [info script]]} d] ? "." : $d}]
      foreach ot_pf_f [list $ot_pf_here/pinflop_ref.tcl $ot_pf_here/../qwen_die_masters/pinflop_ref.tcl \
                         $ot_pf_here/../physical/qwen_die_masters/pinflop_ref.tcl /src/physical/qwen_die_masters/pinflop_ref.tcl] {
        if {[file readable $ot_pf_f]} { source $ot_pf_f; break }
      }
    }
    set ot_pf_new [expr {[info procs ot_pf_lib_ins] ne ""}]
    if {$ot_pf_new} { set ot_pf_pins [ot_pf_clks [all_inputs -no_clocks]]; puts "OT_IOREF_PF search: pinflop_ref.tcl (hold-pad chains, hard children)" }
    foreach port [expr {$ot_pf_new ? {} : [all_inputs -no_clocks]}] {
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
    # mtp-wfc 2026-10-11 (dsfd_wfc_crp, two port clocks ck / ckv): the mean is PER REAL CLOCK.  It was taken over the pin
    # flops of the FIRST moved clock only (core_clk, 288.8) and applied to every moved clock's inputs: the ser-domain
    # inputs (vclk_s, boundary mean 215.1) were shifted +73.7 ps late, the FF hold scene saw +10 on f_swa / f_ksrd /
    # credits and never repaired them, the verdict (no PF) read -33.  Each moved virtual clock now shifts by the pin-flop
    # mean of ITS real clock (only pin flops on that tree: svc-fix 2026-10-10, forwarded-clock capture flops excluded); a
    # clock with no pin flops keeps its boundary reference.
    set ot_pf_rcs [lsort -unique [lmap v [dict values $::ot_ir_moved] {lindex $v 1}]]
    set ot_pf_m [dict create]
    foreach rc $ot_pf_rcs {
      set vs {}
      foreach p $ot_pf_pins {
        if {[lsearch -exact [lmap c [get_property $p clocks] {get_full_name $c}] $rc] < 0} continue
        set v [ot_ir_arr $p $rc]; if {$v ne "" && $v ne "INF" && $v ne "-INF" && [string is double -strict $v]} { lappend vs [expr {$ot_pf_new ? $v + [ot_pf_ins $p max] : $v}] }
      }
      if {[llength $vs]} { set s 0.0; foreach v $vs { set s [expr {$s + $v}] }; dict set ot_pf_m $rc [list [expr {$s / [llength $vs]}] [llength $vs]] }
    }
    if {[dict size $ot_pf_m]} {
      set ot_pf_tmp [file join [expr {[info exists ::env(TMPDIR)] ? $::env(TMPDIR) : "/tmp"}] "ot_pf_[pid]_[clock clicks].sdc"]
      write_sdc $ot_pf_tmp
      set fh [open $ot_pf_tmp r]; set txt [read $fh]; close $fh; file delete $ot_pf_tmp
      set redo {}; set ports [dict create]
      foreach ln [split $txt "\n"] {
        if {![regexp {^set_input_delay\s+(\S+)\s+(.*-clock \[get_clocks \{([^\}]+)\}\].*?)(\[get_ports .*\])\s*$} $ln -> val mid ck tgt]} continue
        if {![dict exists $::ot_ir_moved $ck]} continue
        lassign [dict get $::ot_ir_moved $ck] L rc
        if {![dict exists $ot_pf_m $rc]} continue
        # CLOCK-CLASS: a port referenced to its own (non-dominant) class keeps that reference
        if {[regexp {\[get_ports \{(.+)\}\]} $tgt -> ot_pf_pn] && [dict exists $::ot_cls_adj "in,$ck,$ot_pf_pn"] && abs([dict get $::ot_cls_adj "in,$ck,$ot_pf_pn"]) > 1e-6} continue
        set d [expr {[lindex [dict get $ot_pf_m $rc] 0] - $L}]
        lappend redo [list [expr {$val + $d}] $mid $tgt]
        dict set ports "$ck|$tgt" [list $ck $tgt]
      }
      dict for {k v} $ports { lassign $v ck tgt; unset_input_delay -clock $ck [subst $tgt]; unset_input_delay -clock $ck -clock_fall [subst $tgt] }
      foreach r $redo { lassign $r val mid tgt; eval "set_input_delay $val $mid $tgt" }
      dict for {rc v} $ot_pf_m {
        puts [format "OT_IOREF_PF %s input pin flops %d mean %.1f" $rc [lindex $v 1] [lindex $v 0]]
      }
      puts [format "OT_IOREF_PF %d input delays re-referenced (ports %d)" [llength $redo] [dict size $ports]]
    } else { puts "OT_IOREF_PF no input pin flops: input reference unchanged" }
  } ot_pf_err]} { puts "OT_IOREF_PF WARNING: $ot_pf_err -- input reference unchanged"; if {[info exists ::env(OT_IOREF_PF_DEBUG)]} { puts $::errorInfo } }
}
