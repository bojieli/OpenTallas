# CLAUDE setup-triage 2026-10-07: CONSISTENT die-link IO budget (owner-delegated decision, coordinator 2026-10-07).
#
# A registered die link is  sender flop -> sender pin -> die wire / pin station -> receiver pin -> receiver flop.  Its
# setup equation, with the two blocks' clock arrivals differing by up to SKEW, is
#     S (sender clk->Q + reg->pin) + LINK (measured wire + station) + R (receiver pin->flop + setup) + SKEW <= T - 60
# so the two SDCs of one link must split ONE budget:  S + R = T - 60 - SKEW - LINK.  The per-block generators in use
# (0.2T-outside, W2 make_sdc.py, budget sheets) give each side the remainder after assuming the OTHER side small, so the
# two windows overlap (W2: 338 + 263 = 601 ps vs 423 available at WIRE 200).  This SDC re-applies every data port's
# max delay from the consistent split, referenced to a virtual clock at the block's MEASURED mid insertion:
#     input  max = T - 60 - R      output max = T - 60 - S      (uncertainty 60 is applied by STA itself)
# Knobs (Tcl vars before sourcing, else env, else default): ot_lb_skew (150, inter-region; 90 intra), ot_lb_link
# (114 = 100 um pin-station segment x 1.135 ps/um SS), ot_lb_sfrac (0.5).  SETUP ONLY: read it in the SS session;
# hold keeps flow-hold's rule-H1 SDC (this file sets no -min and removes nothing).  Exceptions (false/multicycle paths from/to ports) stay.
proc ot_lb_get {n d} { if {[info exists ::$n]} { return [set ::$n] }; if {[info exists ::env($n)]} { return $::env($n) }; return $d }
set ot_lb_skew [ot_lb_get ot_lb_skew 150]
set ot_lb_link [ot_lb_get ot_lb_link 114]
set ot_lb_sfrac [ot_lb_get ot_lb_sfrac 0.5]
set ot_lb_clks {}
foreach c [all_clocks] {
  set src [get_property $c sources]
  if {[llength $src] == 1 && [get_property $c is_generated] == 0 && [llength [get_ports -quiet [get_full_name [lindex $src 0]]]]} {
    # forwarded (source-synchronous) clocks arrive on data-side ports (fi*, fk*, a[N], ...): their ports are timed by the
    # per-link source-synchronous model (tools/setup_triage/srcsync), not by this common-clock split
    if {[regexp {^f} [get_full_name $c]] || [regexp {^(fi|fk|fclk)} [get_full_name [lindex $src 0]]]} { lappend ot_lb_fwd [get_full_name $c] } else { lappend ot_lb_clks $c }
  }
}
if {[info exists ot_lb_fwd]} { puts "OT_LINK_BUDGET forwarded clocks (own SDC kept, srcsync model): $ot_lb_fwd" }
if {[llength $ot_lb_clks] < 1} { puts "OT_LINK_BUDGET: no common port clock (all forwarded): nothing to apply" } else {
# one virtual clock per port-sourced clock, at that clock's measured mid insertion
# q-kvd 2026-10-12 (qkd_d2d_ref-q8-aeca40e24): with hard macros (block masters: SRAMs, hardened sub-tiles) the clock's
# sinks include the macros' clock pins, which arrive EARLY by design (their internal insertion is folded into the
# view's arcs / max_clock_tree_path; the parent spine targets pin + internal = flop arrival).  report_clock_latency's
# min..max then spans macro pin .. register (qkd_d2d: 1,139 .. 1,706 -> L 1,422.5, ~280 ps below the face registers at
# ~1,700), so every face output failed falsely (-122 ps on ot_lb_v) and every input gained the same.  The reference is
# the boundary registers' clock: when the block has a block-master instance, L is the mid of the standard-cell
# REGISTER clock-pin arrivals of that clock (min of the rise/fall arrival = the tree insertion on either edge; the
# arrival carries any source latency once), macro / hard-child pins excluded.  Macro-free blocks are unchanged.
proc ot_lb_reg_lat {} {
  set has_block 0; set pins {}
  foreach inst [[ord::get_db_block] getInsts] {
    set m [$inst getMaster]
    if {[$m isBlock]} { set has_block 1; continue }
    if {![regexp {^(DFF|DHL|DLL|SDF|ASYNC)} [$m getName]]} continue
    foreach cp {CLK clk CK ck} {
      set ck [get_pins -quiet "[string map {/ .} [$inst getName]]/$cp"]
      if {[llength $ck] == 0} { set ck [get_pins -quiet "[$inst getName]/$cp"] }
      if {[llength $ck]} { lappend pins $ck; break }
    }
  }
  set r [dict create]
  set ::ot_lb_arr [dict create]    ;# CLOCK-CLASS: clock -> every standard-cell register clock arrival
  foreach ck $pins {
    set a {}
    foreach pr {arrival_max_rise arrival_max_fall} { set v [get_property $ck $pr]; if {[string is double -strict $v]} { lappend a $v } }
    if {![llength $a]} continue
    set a [tcl::mathfunc::min {*}$a]
    foreach c [get_property $ck clocks] {
      set n [get_full_name $c]
      dict lappend ::ot_lb_arr $n $a
      if {!$has_block} continue
      if {![dict exists $r $n]} { dict set r $n [list $a $a 1]; continue }
      lassign [dict get $r $n] lo hi k
      dict set r $n [list [expr {min($lo, $a)}] [expr {max($hi, $a)}] [incr k]]
    }
  }
  return $r
}
# CLOCK-CLASS 2026-10-13 (export-sdc; smh_tile_eg r10, codex/hbm-sm-cluster 4a8f09870): one L per clock is wrong for a
# block with two clock classes on one port clock (9 raw flops + ICG at 0.5 ps beside 967 gated flops at TT ~1.9 ns: L
# 950.6 = the midrange, matching no flop; 3,905 outputs -783..-974 against ot_lb_v_core_clk).  The standard-cell
# register arrivals of a clock are split into classes wherever neighbours are more than OT_IOREF_CLASS_GAP apart
# (default max(0.25 T, 150 ps)); L is the mid of the DOMINANT class (most registers), and a port whose first register
# is in another class k gets its consistent max delay referenced to that class (input + (Lk - L0), output - (Lk - L0)).
# The adjustment is recorded in ::ot_cls_adj so physical/common_flow/io_ref_routed.sdc (read last at sign-off, same
# rule, all registers of the port checked) replaces it instead of adding its own.  One class = unchanged.
proc ot_lb_split {vals gap} {
  set out {}; set lo ""; set hi ""; set n 0
  foreach v [lsort -real $vals] {
    if {$lo eq ""} { set lo $v; set hi $v; set n 1; continue }
    if {$v - $hi > $gap} { lappend out [list $lo $hi $n]; set lo $v; set n 0 }
    set hi $v; incr n
  }
  if {$lo ne ""} { lappend out [list $lo $hi $n] }
  return $out
}
proc ot_lb_class_of {v cls} {
  set best 0; set bd ""; set i 0
  foreach c $cls {
    lassign $c lo hi
    set d [expr {$v < $lo ? $lo - $v : ($v > $hi ? $v - $hi : 0.0)}]
    if {$bd eq "" || $d < $bd} { set bd $d; set best $i }
    incr i
  }
  return $best
}
proc ot_lb_inst_arr {inst} {
  foreach cp {CLK clk CK ck} {
    set ck [get_pins -quiet "[string map {/ .} [$inst getName]]/$cp"]
    if {[llength $ck] == 0} { set ck [get_pins -quiet "[$inst getName]/$cp"] }
    if {[llength $ck] == 0} continue
    set a {}
    foreach pr {arrival_max_rise arrival_max_fall} { set v [get_property $ck $pr]; if {[string is double -strict $v]} { lappend a $v } }
    if {[llength $a]} { return [tcl::mathfunc::min {*}$a] }
  }
  return ""
}
if {![info exists ::ot_cls_adj]} { set ::ot_cls_adj [dict create] }
set ::ot_lb_cls [dict create]   ;# clock -> {classes dominant L0}
set ot_lb_vmap [dict create]
catch {unset ot_lb_reglat}
foreach c $ot_lb_clks {
  set cn [get_full_name $c]
  set T [get_property $c period]
  sta::redirect_string_begin
  report_clock_latency -clock $c
  set rs [sta::redirect_string_end]
  if {![regexp {rise -> rise.*?([0-9.]+)\s+([0-9.]+)\s+latency} $rs -> lo hi]} { puts "OT_LINK_BUDGET no latency for $cn (no sinks?)"; continue }
  set L [expr {($lo + $hi) / 2.0}]
  # mtp-mx1 2026-10-10: on a clock with port source latency (die leaf delivered by the die tree, e.g. MX1 face leaves)
  # this OpenSTA's report_clock_latency already includes the source latency in each "network latency" line and adds it
  # AGAIN in the "latency" total (FT8 ckn: source 782.1, real port->CLK tree 74 ps, reported network 846, total 1628).
  # The virtual clock then sat one source latency late: inputs over-constrained (-625 ps fake on xb), outputs optimistic
  # by the same amount.  Remove the duplicate; clocks without source latency are unchanged.
  if {[regexp {([0-9.]+)\s+([0-9.]+)\s+source latency} $rs -> slo shi] && ($slo + $shi) > 0.0} {
    set L [expr {$L - ($slo + $shi) / 2.0}]
  }
  set ot_lb_ref "clock_latency"
  # read pin arrivals only after report_clock_latency has built the timing graph (get_property arrival_* on a session
  # with no graph yet segfaults in Graph::pinVertices)
  if {![info exists ot_lb_reglat]} { set ot_lb_reglat [ot_lb_reg_lat] }
  if {[dict exists $ot_lb_reglat $cn]} {
    lassign [dict get $ot_lb_reglat $cn] lo hi ot_lb_nreg
    set L [expr {($lo + $hi) / 2.0}]
    set ot_lb_ref "std_regs $ot_lb_nreg (macro pins excluded)"
  }
  if {[ot_lb_get OT_IOREF_CLASS 1] ne "0" && [dict exists $::ot_lb_arr $cn]} {
    set ot_lb_cl [ot_lb_split [dict get $::ot_lb_arr $cn] [ot_lb_get OT_IOREF_CLASS_GAP [expr {max(0.25 * $T, 150.0)}]]]
    if {[llength $ot_lb_cl] > 1} {
      set ot_lb_dom 0; set i 0
      foreach c $ot_lb_cl { if {[lindex $c 2] > [lindex $ot_lb_cl $ot_lb_dom 2]} { set ot_lb_dom $i }; incr i }
      lassign [lindex $ot_lb_cl $ot_lb_dom] lo hi ot_lb_nreg
      set L [expr {($lo + $hi) / 2.0}]
      set ot_lb_ref "class $ot_lb_dom of [llength $ot_lb_cl] clock classes, std_regs $ot_lb_nreg"
      dict set ::ot_lb_cls $cn [list $ot_lb_cl $ot_lb_dom $L]
      set i 0
      foreach c $ot_lb_cl { puts [format "OT_LINK_BUDGET clock %s class %d%s %.1f..%.1f n %d" $cn $i [expr {$i == $ot_lb_dom ? " dominant" : ""}] [lindex $c 0] [lindex $c 1] [lindex $c 2]]; incr i }
    }
  }
  set B [expr {$T - 60.0 - $ot_lb_skew - $ot_lb_link}]
  set S [expr {$ot_lb_sfrac * $B}]; set R [expr {$B - $S}]
  create_clock -name ot_lb_v_$cn -period $T
  set_clock_latency $L [get_clocks ot_lb_v_$cn]
  set_clock_uncertainty -setup 60 [get_clocks ot_lb_v_$cn]
  dict set ot_lb_vmap $cn [list ot_lb_v_$cn [expr {$T - 60.0 - $R}] [expr {$T - 60.0 - $S}]]
  puts [format "OT_LINK_BUDGET clock %s T %.3f L %.1f (%.1f..%.1f %s) skew %s link %s -> S %.1f R %.1f; in max %.1f out max %.1f" $cn $T $L $lo $hi $ot_lb_ref $ot_lb_skew $ot_lb_link $S $R [expr {$T - 60.0 - $R}] [expr {$T - 60.0 - $S}]]
}
if {[dict size $ot_lb_vmap] == 0} { error "OT_LINK_BUDGET: no measured clock" }
set ot_lb_default [lindex [dict keys $ot_lb_vmap] 0]
# the port-sourced clock of the first register reached from a port through combinational cells (odb walk; a
# generated clock maps to its master's port clock)
proc ot_lb_clk_of_inst {inst} {
  foreach cp {CLK clk CK ck} {
    set ck [get_pins -quiet "[string map {/ .} [$inst getName]]/$cp"]
    if {[llength $ck] == 0} { set ck [get_pins -quiet "[$inst getName]/$cp"] }
    if {[llength $ck] == 0} continue
    foreach c [get_property $ck clocks] {
      set n [get_full_name $c]
      for {set i 0} {$i < 8 && [get_property [get_clocks $n] is_generated]} {incr i} { set n [get_full_name [get_property [get_clocks $n] master_clock]] }
      if {[dict exists $::ot_lb_vmap $n]} { return $n }
      if {[info exists ::ot_lb_fwd] && [lsearch -exact $::ot_lb_fwd $n] >= 0} { return FWD }
    }
  }
  return ""
}
# a hard macro (block master: SRAM, register bank, hardened sub-tile) is a timing endpoint like a register; walking
# through it as combinational fanned every port across all macro outputs (hfd_attn_half 2026-10-11: ~5k ports x 4,000
# nets each through the 544-bit banks kept cts.tcl in this Tcl loop for 10 h after CTS)
proc ot_lb_is_seq {inst} {
  set m [$inst getMaster]
  if {[$m isBlock]} { return 1 }
  return [regexp {^(DFF|DHL|DLL|SDF|ASYNC|ICG)} [$m getName]]
}
proc ot_lb_domain {portname dir} {
  set bt [[ord::get_db_block] findBTerm $portname]
  if {$bt eq "NULL" || $bt eq ""} { return "" }
  set nets [list [$bt getNet]]; set seen [dict create]; set k 0
  set qi 0
  while {$qi < [llength $nets] && $k < 4000} {
    set n [lindex $nets $qi]; incr qi; incr k
    if {$n eq "NULL" || [dict exists $seen [$n getName]]} continue
    dict set seen [$n getName] 1
    foreach it [$n getITerms] {
      set inst [$it getInst]
      if {$dir eq "in" && ![$it isInputSignal]} continue
      if {$dir eq "out" && ![$it isOutputSignal]} continue
      if {[ot_lb_is_seq $inst]} { set d [ot_lb_clk_of_inst $inst]; if {$d ne ""} { set ::ot_lb_hit $inst; return $d }; continue }
      foreach it2 [$inst getITerms] {
        if {$dir eq "in" && [$it2 isOutputSignal]} { lappend nets [$it2 getNet] }
        if {$dir eq "out" && [$it2 isInputSignal]} { set nn [$it2 getNet]; if {$nn ne "NULL" && [$nn getSigType] ni {POWER GROUND CLOCK}} { lappend nets $nn } }
      }
    }
  }
  return ""
}
# CLOCK-CLASS: (Lk - L0) of the class of the register ot_lb_domain just reached; 0 on the dominant class / one class
proc ot_lb_class_delta {d} {
  if {![dict exists $::ot_lb_cls $d] || ![info exists ::ot_lb_hit] || $::ot_lb_hit eq ""} { return 0.0 }
  lassign [dict get $::ot_lb_cls $d] cls dom L0
  if {[[$::ot_lb_hit getMaster] isBlock]} { return 0.0 }
  set a [ot_lb_inst_arr $::ot_lb_hit]
  if {$a eq ""} { return 0.0 }
  set k [ot_lb_class_of $a $cls]
  if {$k == $dom} { return 0.0 }
  lassign [lindex $cls $k] lo hi
  return [expr {($lo + $hi) / 2.0 - $L0}]
}
set ot_lb_gsrc {}
foreach c [all_clocks] { foreach s [get_property $c sources] { lappend ot_lb_gsrc [get_full_name $s] } }
# Reset / async ports are not die-link data: their paths end at recovery/removal checks the block SDCs treat separately
# (synchronised resets, false paths).  setup-triage 2026-10-07 fix: idxq b0 -1763 / svc SE_s1 -1267 were rst -> async
# recovery artefacts.  Exclude ports named like resets and any port whose fan-in register set is only async pins.
set ot_lb_in {}
foreach p [all_inputs -no_clocks] { if {![regexp -nocase {(^|[._])(rst|reset|por|rstn|rst_n|arst)} [get_full_name $p]]} { lappend ot_lb_in $p } }
set ot_lb_out {}
foreach p [all_outputs] { if {[lsearch -exact $ot_lb_gsrc [get_full_name $p]] < 0 && ![regexp -nocase {(^|[._])(rst|reset|por)} [get_full_name $p]]} { lappend ot_lb_out $p } }
# -add_delay against a NEW virtual clock: the block's own min/max delays stay (hold model untouched), and STA takes
# the worse of the old and the consistent max, so the consistent split can only tighten the verdict.
set ot_lb_multi [expr {[dict size $ot_lb_vmap] > 1}]
set ot_lb_n [dict create]
foreach p $ot_lb_in {
  set d $ot_lb_default
  set ::ot_lb_hit ""
  set x [ot_lb_domain [get_full_name $p] in]
  if {$x eq "FWD"} { dict incr ot_lb_n "in:skip_fwd"; continue }
  if {$x ne ""} { set d $x }
  lassign [dict get $ot_lb_vmap $d] vc imax omax
  set ot_lb_cd [ot_lb_class_delta $d]
  if {$ot_lb_cd != 0.0} { set imax [expr {$imax + $ot_lb_cd}]; dict set ::ot_cls_adj "in,$vc,[get_full_name $p]" $ot_lb_cd; dict incr ot_lb_n "in:$d:class" }
  set_input_delay -max -add_delay $imax -clock $vc $p
  dict incr ot_lb_n "in:$d"
}
foreach p $ot_lb_out {
  set d $ot_lb_default
  set ::ot_lb_hit ""
  set x [ot_lb_domain [get_full_name $p] out]
  if {$x eq "FWD"} { dict incr ot_lb_n "out:skip_fwd"; continue }
  if {$x ne ""} { set d $x }
  lassign [dict get $ot_lb_vmap $d] vc imax omax
  set ot_lb_cd [ot_lb_class_delta $d]
  if {$ot_lb_cd != 0.0} { set omax [expr {$omax - $ot_lb_cd}]; dict set ::ot_cls_adj "out,$vc,[get_full_name $p]" [expr {-$ot_lb_cd}]; dict incr ot_lb_n "out:$d:class" }
  set_output_delay -max -add_delay $omax -clock $vc $p
  dict incr ot_lb_n "out:$d"
}
# each virtual clock times only its own domain: no cross-domain (CDC) or async recovery/removal path is a link check
foreach {cn v} $ot_lb_vmap {
  set vc [lindex $v 0]
  foreach c [all_clocks] {
    set n [get_full_name $c]
    if {[string match ot_lb_v_* $n]} continue
    # generated clocks (gated / half-rate / forwarded-out) stay timed; only other port/virtual domains are cut
    if {[get_property $c is_generated]} continue
    if {$n ne $cn} { set_false_path -from [get_clocks $vc] -to $c; set_false_path -from $c -to [get_clocks $vc] }
  }
}
set ot_lb_async {}
foreach pin [get_pins -quiet -hierarchical -filter "direction==input"] {
  if {[regexp {/(RESETN|SETN|RN|SN|RESET|SET)$} [get_full_name $pin]]} { lappend ot_lb_async $pin }
}
if {[llength $ot_lb_async]} { foreach {cn v} $ot_lb_vmap { set_false_path -from [get_clocks [lindex $v 0]] -to $ot_lb_async } }
puts "OT_LINK_BUDGET ports $ot_lb_n async_pins_excluded [llength $ot_lb_async]"
}
# REBUDGET hook (2026-10-08, tools/budgets/rebudget.py): the block's re-derived per-port die-link budget (budget_rb<N>),
# installed beside this file by the closure loop for new routes; it replaces this file's fixed split on the ports it covers
set ot_rb_hook [file join [file dirname [info script]] rebudget_block.sdc]
if {[file exists $ot_rb_hook]} { puts "OT_REBUDGET hook $ot_rb_hook"; source $ot_rb_hook }
