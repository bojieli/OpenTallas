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
set ::stb::blk_sinks [expr {[info exists ::env(OT_STB_BLOCK_SINKS)] ? $::env(OT_STB_BLOCK_SINKS) : "sink"}]
if {![info exists ::stb::n]} { set ::stb::n 0 }

proc stb::arr {pinname} {
  set p [get_pins -quiet $pinname]
  if {![llength $p]} { return "" }
  set a [get_property $p arrival_max_rise]
  if {$a eq "" || $a eq "INF" || $a eq "-INF"} { return "" }
  if {abs($a) < 1.0} { set a [expr {$a * 1e12}] }
  return $a
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
  set todo [list [list PORT [$bt getNet]]]; set nn 0; set ns 0; set seen {}
  while {[llength $todo]} {
    lassign [lindex $todo end] node net; set todo [lrange $todo 0 end-1]
    set ::stb::kids($p,$node) {}; set ::stb::sinks($p,$node) {}; set ::stb::blk($p,$node) 0
    foreach it [$net getITerms] {
      if {![$it isInputSignal]} continue
      set i [$it getInst]
      if {[stb::is_node $i]} {
        set on [stb::out_net $i]
        if {$on eq "" || [dict exists $seen [$i getName]]} continue
        dict set seen [$i getName] 1
        lappend ::stb::kids($p,$node) [$i getName]; incr nn
        lappend todo [list [$i getName] $on]
      } else {
        if {[string match "clkload*" [$i getName]]} continue
        if {[[$i getMaster] isBlock]} {
          set ::stb::blk($p,$node) 1
          if {$::stb::blk_sinks eq "fixed"} continue
        }
        lappend ::stb::sinks($p,$node) "[$i getName]/[[$it getMTerm] getName]"; incr ns
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
  set b [odb::dbInst_create $blk [[ord::get_db] findMaster $::stb::cell] delaybuf_otstb_$k]
  $b setLocation $x $y; $b setPlacementStatus PLACED
  set n1 [odb::dbNet_create $blk otstb_net_$k]; $n1 setSigType CLOCK
  $sink disconnect
  [$b findITerm A] connect $n0
  [$b findITerm Y] connect $n1
  $sink connect $n1
  $n0 setDoNotTouch $dt_n
}
proc stb::rc {} { if {$::stb::est eq "grt"} { estimate_parasitics -global_routing } else { estimate_parasitics -placement } }
proc stb::balance {} {
  set blk [ord::get_db_block]
  set_propagated_clock [all_clocks]
  stb::protected
  set ports [stb::ports]
  set T {}; set tot 0
  stb::rc
  foreach p $ports {
    lassign [stb::build $p] nn ns
    if {$ns < 2} continue
    set m [stb::measure $p]
    if {$m eq ""} continue
    dict set T $p [lindex $m 4]
    puts "OT_STB before $p ($::stb::est RC): $nn tree nodes, [stb::fmt $m]; target [format %.1f [lindex $m 4]] (latest sink, fixed)"
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
    if {$::stb::est eq "grt"} { set ::stb::inc 0; sta::arrivals_invalid; global_route -end_incremental {*}[expr {[info exists ::ot_grt_res_aware] ? $::ot_grt_res_aware : ""}] }
    if {!$added} break
    stb::rc
    set lines {}
    dict for {p Tp} $T { lassign [stb::build $p] nn ns; set m [stb::measure $p]; if {$m ne ""} { lappend lines "$p [stb::fmt $m]" } }
    puts "OT_STB round $r: +$added delay buffers at $nodes nodes; [join $lines {; }]"
    if {$::stb::n - $n0 >= $::stb::maxbuf} { puts "OT_STB cap OT_STB_MAX_BUF $::stb::maxbuf reached"; break }
  }
  set ::stb::added [expr {$::stb::n - $n0}]
  if {$::stb::added} { check_placement -verbose }
  puts "OT_STB done: $::stb::added delay buffers ($::stb::cell, $::stb::est RC) on [dict size $T] clock trees"
}
set ::stb::added 0; set ::stb::inc 0
if {$::stb::mode ne "0"} {
  if {[catch {stb::balance} e]} {
    if {$::stb::inc} { catch { sta::arrivals_invalid; global_route -end_incremental } }
    puts "OT_STB ERROR (buffers already added are kept and legal; no further edits): $e"
  }
} else { puts "OT_STB skipped (OT_STB=0)" }
