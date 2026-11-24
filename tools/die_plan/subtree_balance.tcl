# TYPE-SAFE-1 11-06 (COORD RULINGS 19:0x (3), OWNER 18:5x structurally hold-safe clocks): SUBTREE LATENCY BALANCE of every
# clock tree on GLOBAL-ROUTE RC, in the shared GRT step (default on in core kits: core_flow.py grt_post_core.tcl, before
# core_final_repair.tcl; partition kits: tapbal_grt.tcl GRT-RC pre-pass, after the tap balance).
# Why: CTS balances on the placement estimate.  The routed tree is later than that estimate by a NON-uniform amount:
# S81 eng_rr_e (rt16m, FF, all 17289 sinks) placement RC 482..553 (p1..p99 491..530, 39 ps), routed 520..640 (p1..p99
# 529..635, 106 ps); routed - placement +18..+119 ps per sink (median +65), the same on NDR and non-NDR clock nets (no
# GRT-0273 in that run: the late tail is wire RC the placement estimate does not see, not a dropped rule).  590 r2r FF
# hold misses all pass at zero skew; HBM SUX the same class (sux_latbal.tcl, placement RC, 73 -> 28 ps).
# Form (generalised from HBM-FORM-SPLIT-14 sux_latbal.tcl): for EACH clock source port (all_clocks sources; or
# OT_STB_PORTS) the tree = port net through every BUF/INV/CKINV/HB cell; subtree latest-sink arrival M(n) is measured
# (propagated clock, OT_STB_EST grt|placement, default grt); target T(port) = that tree's latest sink before balancing
# (fixed, never chased).  Top-down, delay stages (OT_STB_CELL, BUFx4) are inserted in front of the HIGHEST node whose
# whole subtree is early by >= one stage (k = floor(0.75 (T - M - tol) / stage), <= 12 a node a round); nodes below a
# delayed node wait for the next round (re-measured).  On GRT RC every edit sits inside global_route -start/-end_incremental.
# Never edited: DoNotTouch cells, planned spine pins (/work/ot_rt_spine.tsv, regional_taps OT_RT_PROTECT_SPINE), and
# with OT_STB_BLOCK_SINKS=fixed (partition kits: hard cores carry internal latency) any subtree holding a macro pin.
# Same ports, clocks, flops, cycles and logic: only clock-tree delay buffers (delaybuf_otstb_*, nets otstb_net_*).
# Bounded: OT_STB_MAX_BUF (default 4000) buffers.  Wrapped in catch: a failure stops further edits (logged).
# Env: OT_STB=0 off, =report measure only; OT_STB_TOL (8 ps), OT_STB_STAGE (20 ps), OT_STB_ROUNDS (8).
namespace eval stb {}
set ::stb::mode   [expr {[info exists ::env(OT_STB)] ? $::env(OT_STB) : 1}]
set ::stb::tol    [expr {[info exists ::env(OT_STB_TOL)]    ? $::env(OT_STB_TOL)    : 8.0}]
set ::stb::stage  [expr {[info exists ::env(OT_STB_STAGE)]  ? $::env(OT_STB_STAGE)  : 20.0}]
set ::stb::rounds [expr {[info exists ::env(OT_STB_ROUNDS)] ? $::env(OT_STB_ROUNDS) : 8}]
set ::stb::cell   [expr {[info exists ::env(OT_STB_CELL)]   ? $::env(OT_STB_CELL)   : "BUFx4_ASAP7_75t_R"}]
set ::stb::est    [expr {[info exists ::env(OT_STB_EST)]    ? $::env(OT_STB_EST)    : "grt"}]
set ::stb::maxbuf [expr {[info exists ::env(OT_STB_MAX_BUF)] ? $::env(OT_STB_MAX_BUF) : 4000}]
# S81-RCK-BALANCE 11-17 (FABLE-PD-S81-0600): OT_STB_PAIR=1 pads with an INVERTER PAIR (OT_STB_CELL must then be an inverter, e.g.
# INVx4_ASAP7_75t_R) instead of one same-polarity BUF, so the pad adds no rise/fall (duty) distortion on a long clock tree.
# OT_STB_SPAN_MAX=<ps>: after balancing, every balanced tree reports its sink insertion span (latest - earliest rise sink arrival);
# OT_STB_SPAN_FAIL=1 turns a span over the limit into an error (the hook output then says OT_STB_SPAN FAIL).
set ::stb::pair [expr {[info exists ::env(OT_STB_PAIR)] ? $::env(OT_STB_PAIR) : 0}]
set ::stb::span_max [expr {[info exists ::env(OT_STB_SPAN_MAX)] && $::env(OT_STB_SPAN_MAX) ne "" ? $::env(OT_STB_SPAN_MAX) : ""}]
set ::stb::span_fail [expr {[info exists ::env(OT_STB_SPAN_FAIL)] ? $::env(OT_STB_SPAN_FAIL) : 0}]
set ::stb::blk_sinks [expr {[info exists ::env(OT_STB_BLOCK_SINKS)] ? $::env(OT_STB_BLOCK_SINKS) : "sink"}]
# DIE-CORETAP-1119: OT_STB_TAG names the cells of one pass (delaybuf_otstb_<tag><k>, nets otstb_<tag>net_<k>), so a pass in a
# later process (tapbal_grt.tcl after the POST_CTS pass of cts_post.tcl) never re-creates an existing name.  Unset: unchanged.
set ::stb::tag [expr {[info exists ::env(OT_STB_TAG)] ? $::env(OT_STB_TAG) : ""}]
if {![info exists ::stb::n]} { set ::stb::n 0 }
# STB-BOUND 11-24 (QC-CBX-CLOCK, COORD): the target of a tree is its latest sink, but never above the post-CTS tree bound:
# T = min(latest sink, OT_STB_TARGET_MAX_PS).  QC cbn_q01 clab6e67f2 clk_t66 (sinks 443 um apart, raw 374..753 ps) was padded
# to its 753 ps far sink: 19 delaybuf_otstb in series in front of sinks at ~280, tap at 811 ps vs ~290 beside it, hold -338 /
# setup -405 on the pairs between taps.  Default: the tap balance bound of the kit, OT_TAP_TARGET_PS (or OT_TAP_SLOWEST_MAX_PS
# when OT_TAP_BALANCE_TO=slowest, never below the target) + OT_TAP_WINDOW_PS (default 40); unset when the kit sets no
# OT_TAP_TARGET_PS (core kits: unchanged).  On GRT RC (tapbal_grt.tcl) the routed tree sits later than the placement estimate
# (S81 eng_rr_e median +65 ps), so the default cap there is that bound + OT_STB_GRT_MARGIN_PS (default 65).
# OT_STB_TARGET_MAX_PS=0 = no cap (the old rule).
# STB-BOUND-PORTS 11-24 (S81-SERDES-TAPSKEW): the bound is the TAP bound, so it caps only the tap port family (OT_TAP_PORT,
# default clk, and its clk_<x><n> taps: clk_t5, clk_c3, ...).  Other clock ports keep the latest-sink target: S81 serdes__t2
# io_pma_rck[0] (rck_balance.tcl pass, 26,373 sinks raw 1404..1942 ps) was capped at 250 + 20 = 270 ps, below every sink, so
# the rck tree got no pads (spread 538 ps instead of 44).  OT_STB_CAP_PORTS_RE overrides the family (Tcl ARE).
proc stb::capped_port {p} {
  if {[info exists ::env(OT_STB_CAP_PORTS_RE)] && $::env(OT_STB_CAP_PORTS_RE) ne ""} { return [regexp -- $::env(OT_STB_CAP_PORTS_RE) $p] }
  set base [expr {[info exists ::env(OT_TAP_PORT)] && $::env(OT_TAP_PORT) ne "" ? $::env(OT_TAP_PORT) : "clk"}]
  if {![regexp {^[A-Za-z0-9_]+$} $base]} { return [expr {$p eq $base}] }
  return [regexp -- "^${base}(_\[a-z\]+\[0-9\]+)?\$" $p]
}
proc stb::target_cap {} {
  if {[info exists ::env(OT_STB_TARGET_MAX_PS)] && $::env(OT_STB_TARGET_MAX_PS) ne ""} {
    set v [expr {double($::env(OT_STB_TARGET_MAX_PS))}]
    return [expr {$v > 0 ? $v : ""}]
  }
  if {![info exists ::env(OT_TAP_TARGET_PS)] || $::env(OT_TAP_TARGET_PS) eq ""} { return "" }
  set b [expr {double($::env(OT_TAP_TARGET_PS))}]
  if {[info exists ::env(OT_TAP_BALANCE_TO)] && $::env(OT_TAP_BALANCE_TO) eq "slowest" && [info exists ::env(OT_TAP_SLOWEST_MAX_PS)]} {
    set b [expr {max($b, double($::env(OT_TAP_SLOWEST_MAX_PS)))}]
  }
  set w [expr {[info exists ::env(OT_TAP_WINDOW_PS)] ? double($::env(OT_TAP_WINDOW_PS)) : 40.0}]
  set g [expr {$::stb::est eq "grt" ? ([info exists ::env(OT_STB_GRT_MARGIN_PS)] ? double($::env(OT_STB_GRT_MARGIN_PS)) : 65.0) : 0.0}]
  return [expr {$b + $w + $g}]
}

# OpenSTA pin arrival properties use command time units, including values
# below one unit. Convert by the declared scale before budgeting in ps.
set ::stb::ui_per_ps [sta::time_sta_ui 1.0e-12]
# TAP-GRID-R5 11-22: an arrival beyond +-1 us is not a clock insertion but an unset/sentinel STA value (QC slw_hc1
# cle683a076 clk_t11/t18 read -9.8e11..9.4e11 ps; the latest-sink target then padded long delay chains per tap -> 2,062 ps
# raw tap insertion).  Such a sink is unmeasured: skipped like INF.
set ::stb::arr_max_ps [expr {[info exists ::env(OT_STB_ARR_MAX_PS)] ? $::env(OT_STB_ARR_MAX_PS) : 1.0e6}]
proc stb::time_ps {a} {
  if {$a eq "" || $a eq "INF" || $a eq "-INF"} { return "" }
  set v [expr {double($a) / $::stb::ui_per_ps}]
  if {abs($v) > $::stb::arr_max_ps} { return "" }
  return $v
}
proc stb::arr {pinname} {
  set p [get_pins -quiet $pinname]
  if {![llength $p]} { return "" }
  # STB-EDGE-1: a sink below an odd number of inverters sees the source RISE as its FALL; measure that edge, so every
  # sink reads insertion delay from the same source edge (not rise + half a period)
  set a [get_property $p [expr {[info exists ::stb::par($pinname)] && $::stb::par($pinname) ? "arrival_max_fall" : "arrival_max_rise"}]]
  return [stb::time_ps $a]
}
proc stb::is_node {inst} {
  if {[[$inst getMaster] isBlock]} { return 0 }
  set m [[$inst getMaster] getName]
  return [expr {[string match "BUF*" $m] || [string match "INV*" $m] || [string match "CKINV*" $m] || [string match "HB*" $m]}]
}
proc stb::in_iterm {inst} {
  foreach t [$inst getITerms] { if {[$t isInputSignal] && [$t getNet] ne "NULL"} { return $t } }
  return ""
}
proc stb::out_net {inst} {
  foreach t [$inst getITerms] { if {[$t isOutputSignal] && [$t getNet] ne "NULL"} { return [$t getNet] } }
  return ""
}
proc stb::ports {} {
  if {[info exists ::env(OT_STB_PORTS)] && $::env(OT_STB_PORTS) ne ""} { return $::env(OT_STB_PORTS) }
  set out {}
  foreach c [all_clocks] {
    foreach s [get_property $c sources] {
      set nm [get_full_name $s]
      if {[[ord::get_db_block] findBTerm $nm] ne "NULL" && $nm ni $out} { lappend out $nm }
    }
  }
  return $out
}
proc stb::protected {} {
  set ::stb::prot {}
  if {[file exists /work/ot_rt_spine.tsv]} {
    set f [open /work/ot_rt_spine.tsv]
    foreach line [split [string trim [read $f]] "\n"] { dict set ::stb::prot [lindex [split $line "\t"] 0] 1 }
    close $f
  }
}
# tree of port p: ::stb::kids(p,node), ::stb::sinks(p,node), ::stb::fix(p,node) (macro pin below); root node = PORT
proc stb::build {p} {
  set blk [ord::get_db_block]
  set bt [$blk findBTerm $p]
  if {$bt eq "NULL" || [$bt getNet] eq "NULL"} { return [list 0 0] }
  set todo [list [list PORT [$bt getNet] 0]]; set nn 0; set ns 0; set seen {}
  while {[llength $todo]} {
    lassign [lindex $todo end] node net par; set todo [lrange $todo 0 end-1]
    set ::stb::kids($p,$node) {}; set ::stb::sinks($p,$node) {}; set ::stb::blk($p,$node) 0
    foreach it [$net getITerms] {
      if {![$it isInputSignal]} continue
      set i [$it getInst]
      if {[stb::is_node $i]} {
        set on [stb::out_net $i]
        if {$on eq "" || [dict exists $seen [$i getName]]} continue
        dict set seen [$i getName] 1
        lappend ::stb::kids($p,$node) [$i getName]; incr nn
        set mn [[$i getMaster] getName]
        lappend todo [list [$i getName] $on [expr {([string match "INV*" $mn] || [string match "CKINV*" $mn]) ? !$par : $par}]]
      } else {
        if {[string match "clkload*" [$i getName]]} continue
        if {[[$i getMaster] isBlock]} {
          set ::stb::blk($p,$node) 1
          if {$::stb::blk_sinks eq "fixed"} continue
        }
        lappend ::stb::sinks($p,$node) "[$i getName]/[[$it getMTerm] getName]"; incr ns
        set ::stb::par([$i getName]/[[$it getMTerm] getName]) $par
      }
    }
  }
  return [list $nn $ns]
}
proc stb::measure {p} {
  set order {}; set st [list PORT]
  while {[llength $st]} { set n [lindex $st end]; set st [lrange $st 0 end-1]; lappend order $n; foreach k $::stb::kids($p,$n) { lappend st $k } }
  set all {}
  foreach n [lreverse $order] {
    set h -1e9; set b [expr {$::stb::blk_sinks eq "fixed" && $::stb::blk($p,$n)}]
    foreach s $::stb::sinks($p,$n) { set a [stb::arr $s]; if {$a eq ""} continue; lappend all $a; if {$a > $h} { set h $a } }
    foreach k $::stb::kids($p,$n) { if {$::stb::hi($p,$k) > $h} { set h $::stb::hi($p,$k) }; if {$::stb::fix($p,$k)} { set b 1 } }
    set ::stb::hi($p,$n) $h; set ::stb::fix($p,$n) $b
  }
  set all [lsort -real $all]; set c [llength $all]
  if {!$c} { return {} }
  return [list [lindex $all 0] [lindex $all [expr {$c / 100}]] [lindex $all [expr {$c / 2}]] [lindex $all [expr {$c - 1 - $c / 100}]] [lindex $all end] $c]
}
proc stb::fmt {m} { lassign $m mn p1 md p99 mx c; return [format "sinks %d min %.0f p1 %.0f med %.0f p99 %.0f max %.0f (spread %.0f, p1..p99 %.0f)" $c $mn $p1 $md $p99 $mx [expr {$mx - $mn}] [expr {$p99 - $p1}]] }
proc stb::insert {sink x y} {
  set blk [ord::get_db_block]
  set n0 [$sink getNet]; set inst [$sink getInst]
  set dt_n [$n0 isDoNotTouch]
  $n0 setDoNotTouch 0
  set k [incr ::stb::n]
  set master [[ord::get_db] findMaster $::stb::cell]
  set b [odb::dbInst_create $blk $master delaybuf_otstb_${::stb::tag}$k]
  $b setLocation $x $y; $b setPlacementStatus PLACED
  set n1 [odb::dbNet_create $blk otstb_${::stb::tag}net_$k]; $n1 setSigType CLOCK
  $sink disconnect
  if {$::stb::pair} {
    # inverter pair: n0 -> INV a -> mid -> INV b -> n1 -> sink (two cells, same polarity, symmetric rise/fall)
    set b2 [odb::dbInst_create $blk $master delaybuf_otstb_${::stb::tag}${k}_b]
    $b2 setLocation $x $y; $b2 setPlacementStatus PLACED
    set nm [odb::dbNet_create $blk otstb_${::stb::tag}mid_$k]; $nm setSigType CLOCK
    [$b findITerm A] connect $n0
    [$b findITerm Y] connect $nm
    [$b2 findITerm A] connect $nm
    [$b2 findITerm Y] connect $n1
  } else {
    [$b findITerm A] connect $n0
    [$b findITerm Y] connect $n1
  }
  $sink connect $n1
  $n0 setDoNotTouch $dt_n
}
# STB-COMMON 11-24 (S81-SERDES-TAPSKEW, FABLE-RC-ALL 27044af5; opt-in OT_STB_COMMON=1, plan clock.stb_common): ONE balance target
# for every tap of the type, so arrival is equal ACROSS taps, and a late outlier sink no longer sets a tap's target.  S81 serdes__t2
# (-226 P13 kit): clk_t7 raw 360..380 (p99 380) had outliers at 545, so all 1553 ring/bin/lpad sinks were padded to 545 while
# clk_t33 sat at ~290: +313 ps ring skew, 473 hold fails; clk_t29 (p99 225, one sink 354) put 7 pads (+195 ps) in front of the
# u_txl chain, 88 fails.  Form: per tap-family port (stb::capped_port) the in-family arrival = the sinks at most
# OT_STB_OUTLIER_PS (40) above that tap's p99; a sink later than that is an OUTLIER and is RE-HOMED: its clock pin moves to the
# nearest leaf net (a tree node driving sinks, same inversion parity, latest sink <= the common target) of any tap-family tree
# within OT_STB_REHOME_UM (150 um); none in reach = left as built and named.  Common target Tc = the latest in-family arrival over
# all tap-family ports (OT_STB_COMMON_MAX_PS bounds it; the STB-BOUND cap is not applied in this mode, it would leave the taps
# unequal).  Other clock ports (io_pma_rck, fclk_in_*) keep their own latest-sink target.  Same clock, flops and logic: only
# clock pins re-connected inside one clock's tap trees, plus the usual delay buffers.
set ::stb::common [expr {[info exists ::env(OT_STB_COMMON)] && $::env(OT_STB_COMMON) eq "1"}]
set ::stb::outlier [expr {[info exists ::env(OT_STB_OUTLIER_PS)] ? double($::env(OT_STB_OUTLIER_PS)) : 40.0}]
set ::stb::rehome_um [expr {[info exists ::env(OT_STB_REHOME_UM)] ? double($::env(OT_STB_REHOME_UM)) : 150.0}]
proc stb::sink_arrs {p} {
  set r {}
  foreach k [array names ::stb::sinks "$p,*"] { foreach s $::stb::sinks($k) { set a [stb::arr $s]; if {$a ne ""} { lappend r [list $s $a [lindex [split $k ,] 1]] } } }
  return $r
}
# returns the common target; re-homes outliers (rebuilds the trees of the ports it touched)
proc stb::common_target {ports} {
  set blk [ord::get_db_block]
  set dbu [expr {double([[ord::get_db_tech] getDbUnitsPerMicron])}]
  set fam {}; set lim {}; set tc ""
  foreach p $ports {
    if {![stb::capped_port $p] || ![info exists ::stb::kids($p,PORT)]} continue
    set v [stb::sink_arrs $p]; if {[llength $v] < 2} continue
    set a [lsort -real [lmap x $v {lindex $x 1}]]; set c [llength $a]
    set l [expr {[lindex $a [expr {$c - 1 - $c / 100}]] + $::stb::outlier}]
    dict set lim $p $l; lappend fam $p
    foreach x $a { if {$x <= $l && ($tc eq "" || $x > $tc)} { set tc $x } }
  }
  if {$tc eq ""} { return "" }
  if {[info exists ::env(OT_STB_COMMON_MAX_PS)] && $::env(OT_STB_COMMON_MAX_PS) ne "" && $tc > double($::env(OT_STB_COMMON_MAX_PS))} {
    set tc [expr {double($::env(OT_STB_COMMON_MAX_PS))}]
  }
  # leaf candidates: node, port, parity, x, y (node latest sink <= Tc)
  set cand {}
  foreach p $fam {
    foreach k [array names ::stb::sinks "$p,*"] {
      set n [lindex [split $k ,] 1]
      if {$n eq "PORT" || ![llength $::stb::sinks($k)] || $::stb::hi($p,$n) > $tc} continue
      set i [$blk findInst $n]; if {$i eq "NULL" || [$i isDoNotTouch]} continue
      set on [stb::out_net $i]; if {$on eq "" || [$on isDoNotTouch]} continue
      set s0 [lindex $::stb::sinks($k) 0]
      lassign [$i getLocation] x y
      lappend cand [list $n $p [expr {[info exists ::stb::par($s0)] ? $::stb::par($s0) : 0}] $x $y $on]
    }
  }
  set moved 0; set kept 0; set touched {}
  foreach p $fam {
    set l [dict get $lim $p]
    foreach x [stb::sink_arrs $p] {
      lassign $x s a n
      if {$a <= $l} continue
      set si [$blk findInst [string range $s 0 [expr {[string last / $s] - 1}]]]
      set sit [expr {$si eq "NULL" ? "NULL" : [$si findITerm [string range $s [expr {[string last / $s] + 1}] end]]}]
      if {$sit eq "NULL" || [$si isDoNotTouch] || [[$si getMaster] isBlock]} { incr kept; puts [format "OT_STB_REHOME keep %s %s arr %.1f > %.1f (not editable)" $p $s $a $l]; continue }
      lassign [$si getLocation] sx sy
      set par [expr {[info exists ::stb::par($s)] ? $::stb::par($s) : 0}]
      set best ""; set bd 1e30
      foreach c $cand {
        lassign $c cn cp cpar cx cy con
        if {$cpar != $par || $cn eq $n} continue
        set d [expr {(abs($cx - $sx) + abs($cy - $sy)) / $dbu}]
        if {$d < $bd} { set bd $d; set best $c }
      }
      if {$best eq "" || $bd > $::stb::rehome_um} { incr kept; puts [format "OT_STB_REHOME keep %s %s arr %.1f > %.1f (no leaf within %.0f um)" $p $s $a $l $::stb::rehome_um]; continue }
      set on [lindex $best 5]
      set n0 [$sit getNet]; set dt [$n0 isDoNotTouch]; $n0 setDoNotTouch 0
      $sit disconnect; $sit connect $on
      $n0 setDoNotTouch $dt
      incr moved
      puts [format "OT_STB_REHOME move %s %s arr %.1f > %.1f -> %s leaf %s (%.0f um)" $p $s $a $l [lindex $best 1] [lindex $best 0] $bd]
      foreach q [list $p [lindex $best 1]] { if {$q ni $touched} { lappend touched $q } }
    }
  }
  if {$moved} { sta::arrivals_invalid; stb::rc; foreach p $fam { stb::build $p; stb::measure $p } }
  puts [format "OT_STB_COMMON target %.1f over %d tap ports; outliers re-homed %d, kept %d" $tc [llength $fam] $moved $kept]
  return $tc
}
proc stb::rc {} { if {$::stb::est eq "grt"} { estimate_parasitics -global_routing } else { estimate_parasitics -placement } }
proc stb::balance {} {
  set blk [ord::get_db_block]
  set_propagated_clock [all_clocks]
  stb::protected
  set ports [stb::ports]
  set T {}; set tot 0
  set cap [stb::target_cap]
  stb::rc
  foreach p $ports {
    lassign [stb::build $p] nn ns
    if {$ns < 2} continue
    set m [stb::measure $p]
    if {$m eq ""} continue
    if {$::stb::common && [stb::capped_port $p]} {
      dict set T $p COMMON
      puts "OT_STB before $p ($::stb::est RC): $nn tree nodes, [stb::fmt $m]; target common"
    } elseif {$cap ne "" && [stb::capped_port $p] && [lindex $m 4] > $cap} {
      dict set T $p $cap
      puts "OT_STB before $p ($::stb::est RC): $nn tree nodes, [stb::fmt $m]; target [format %.1f $cap] (latest sink [format %.1f [lindex $m 4]] over the bound: capped)"
    } else {
      dict set T $p [lindex $m 4]
      puts "OT_STB before $p ($::stb::est RC): $nn tree nodes, [stb::fmt $m]; target [format %.1f [lindex $m 4]] (latest sink, fixed)"
    }
  }
  if {$::stb::common && [llength [dict keys [dict filter $T value COMMON]]]} {
    if {$::stb::mode eq "report"} { set ::stb::rehome_um -1 }
    set tc [stb::common_target $ports]
    dict for {p Tp} $T { if {$Tp eq "COMMON"} { if {$tc eq ""} { dict unset T $p } else { dict set T $p $tc } } }
  }
  if {$::stb::mode eq "report"} { return }
  set n0 $::stb::n
  for {set r 0} {$r < $::stb::rounds} {incr r} {
    set added 0; set nodes 0
    if {$::stb::est eq "grt"} { global_route -start_incremental; set ::stb::inc 1 }
    dict for {p Tp} $T {
      set st $::stb::kids($p,PORT)
      while {[llength $st]} {
        set n [lindex $st end]; set st [lrange $st 0 end-1]
        # A forwarded-clock output branch has no local sequential sink. Its
        # measure sentinel is not an early arrival: padding it would add the
        # per-round cap forever (HEAD n3_turn: 12 * 8 = 96 needless buffers).
        if {$::stb::hi($p,$n) == -1e9} { continue }
        set gap [expr {$Tp - $::stb::hi($p,$n) - $::stb::tol}]
        set k [expr {$gap >= $::stb::stage ? max(1, int(floor(0.75 * $gap / $::stb::stage))) : 0}]
        if {$k > 12} { set k 12 }
        set i [$blk findInst $n]
        set ok [expr {$k >= 1 && $i ne "NULL" && !$::stb::fix($p,$n) && ![dict exists $::stb::prot $n] && ![$i isDoNotTouch]
                      && $::stb::n - $n0 + $k <= $::stb::maxbuf}]
        set it [expr {$ok ? [stb::in_iterm $i] : ""}]
        if {$it ne ""} {
          lassign [$i getLocation] x y
          for {set j 0} {$j < $k} {incr j} { stb::insert $it $x $y }
          incr added $k; incr nodes
        } else {
          # on time, or this node may not be edited: look one level down; an early node that may not be edited gets
          # its delay in front of each of its own early sink pins instead
          foreach c $::stb::kids($p,$n) { lappend st $c }
          if {$k >= 1} {
            foreach s $::stb::sinks($p,$n) {
              set a [stb::arr $s]; if {$a eq ""} continue
              set g [expr {$Tp - $a - $::stb::tol}]
              set ks [expr {$g >= $::stb::stage ? min(12, max(1, int(floor(0.75 * $g / $::stb::stage)))) : 0}]
              if {!$ks || $::stb::n - $n0 + $ks > $::stb::maxbuf} continue
              set si [$blk findInst [string range $s 0 [expr {[string last / $s] - 1}]]]
              if {$si eq "NULL" || [$si isDoNotTouch]} continue
              set sit [$si findITerm [string range $s [expr {[string last / $s] + 1}] end]]
              if {$sit eq "NULL" || $sit eq ""} continue
              lassign [$si getLocation] x y
              for {set j 0} {$j < $ks} {incr j} { stb::insert $sit $x $y }
              incr added $ks; incr nodes
            }
          }
        }
      }
    }
    if {$added} {
      if {[llength [info commands ot_pg_connect_all]]} { ot_pg_connect_all subtree_balance } elseif {[llength [info procs ot_pg_standard_bind]]} { ot_pg_standard_bind subtree_balance } else { global_connect }
      detailed_placement
    }
    if {$::stb::est eq "grt"} { set ::stb::inc 0; sta::arrivals_invalid; global_route -end_incremental {*}[expr {[info exists ::ot_grt_res_aware] ? $::ot_grt_res_aware : ""}] {*}[expr {[info exists ::ot_grt_inc_allow] ? $::ot_grt_inc_allow : ""}] }
    if {!$added} break
    stb::rc
    set lines {}
    dict for {p Tp} $T { lassign [stb::build $p] nn ns; set m [stb::measure $p]; if {$m ne ""} { lappend lines "$p [stb::fmt $m]" } }
    puts "OT_STB round $r: +$added delay buffers at $nodes nodes; [join $lines {; }]"
    if {$::stb::n - $n0 >= $::stb::maxbuf} { puts "OT_STB cap OT_STB_MAX_BUF $::stb::maxbuf reached"; break }
  }
  set ::stb::added [expr {$::stb::n - $n0}]
  if {$::stb::added} { check_placement -verbose }
  puts "OT_STB done: $::stb::added delay buffers ($::stb::cell, $::stb::est RC[expr {$::stb::pair ? {, inverter pairs} : {}}]) on [dict size $T] clock trees"
  if {$::stb::span_max ne ""} {
    stb::rc
    set bad 0
    dict for {p Tp} $T {
      lassign [stb::build $p] nn ns
      set m [stb::measure $p]
      if {$m eq ""} continue
      set span [expr {[lindex $m 4] - [lindex $m 0]}]
      set ok [expr {$span <= $::stb::span_max}]
      if {!$ok} { incr bad }
      puts [format "OT_STB_SPAN %s sinks %d min %.1f max %.1f span %.1f limit %.1f %s" $p [lindex $m 5] [lindex $m 0] [lindex $m 4] $span $::stb::span_max [expr {$ok ? "PASS" : "FAIL"}]]
    }
    if {$bad && $::stb::span_fail} { error "OT_STB_SPAN FAIL: $bad tree(s) over $::stb::span_max ps" }
  }
}
set ::stb::added 0; set ::stb::inc 0
if {$::stb::mode ne "0"} {
  if {[catch {stb::balance} e]} {
    if {$::stb::inc} { catch { sta::arrivals_invalid; global_route -end_incremental } }
    puts "OT_STB ERROR (buffers already added are kept and legal; no further edits): $e"
  }
} else { puts "OT_STB skipped (OT_STB=0)" }
