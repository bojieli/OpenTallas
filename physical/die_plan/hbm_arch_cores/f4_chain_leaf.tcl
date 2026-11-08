# HBM-CORES 2026-10-25 F4 (GEOM-REVIEW-2 argmax_r2 / cqb F4): zero-logic register chains on ONE clock leaf.
# Post-CTS: every flop whose D is driven by another flop's Q directly or through one INV/BUF (shift / pin-reg ->
# stage-2 pairs) is moved, chain by chain, onto the clock leaf net of the chain head, so launch and capture share a
# leaf (skew ~ wire only) instead of relying on hold-buffer fill.  Chains > OT_F4_MAX (16) flops are left as is;
# a leaf grows by at most OT_F4_LEAF_ADD (12) sinks.  Then the platform POST_CTS hook (tap balance) runs.
# 10-25 05:12 gq_rr19: a capture is moved only when it lies within OT_F4_MAX_UM (20 um, Manhattan) of the head
# leaf driver; without that bound F4 hung far face flops on a near leaf (256 ps leaf wire, FF hold -204 ps).
# HBM-CORES-KITS-20 10-29 (qwdec_v1 post-CTS hold -28.98 / 2736 r2r): every failing pair was an ADJACENT flop pair
# (median 2.4 um) on two different leaves (leaf arrivals ~40 ps apart); the head-leaf rule skipped chains > OT_F4_MAX
# and judged distance from the chain HEAD leaf.  OT_F4_PAIR=1 (opt-in, default off = unchanged) co-leafs each capture
# with its own launch flop instead: qwdec CTS probe 2736 -> 1278 r2r endpoints, gate PASS (-22.90 ps).
set ::f4_max [expr {[info exists ::env(OT_F4_MAX)] ? $::env(OT_F4_MAX) : 16}]
set ::f4_um [expr {[info exists ::env(OT_F4_MAX_UM)] ? $::env(OT_F4_MAX_UM) : 20}]
set ::f4_add [expr {[info exists ::env(OT_F4_LEAF_ADD)] ? $::env(OT_F4_LEAF_ADD) : 12}]
namespace eval f4 {}
namespace eval f4 { variable roots [dict create] }
proc f4::is_ff {i} { return [string match DFF* [[$i getMaster] getName]] }
proc f4::it {i name} { foreach t [$i getITerms] { if {[[$t getMTerm] getName] eq $name} { return $t } }; return "" }
proc f4::drv {n} { if {$n eq "" || $n eq "NULL"} { return "" }; foreach t [$n getITerms] { if {[$t isOutputSignal]} { return [$t getInst] } }; return "" }
# A reviewed native multiport contract preserves each input's sink membership,
# not merely the number of connected ports. F4 must never re-clock a capture
# onto another native input. Unknown/gated ancestry is conservatively skipped.
proc f4::native_root {n} {
  variable roots
  set path {}; set seen [dict create]; set cur $n; set root ""
  for {set depth 0} {$depth < 128} {incr depth} {
    if {$cur eq "" || $cur eq "NULL" || [dict exists $seen $cur]} break
    if {[dict exists $roots $cur]} {set root [dict get $roots $cur]; break}
    dict set seen $cur 1; lappend path $cur
    set ports {}
    foreach p [$cur getBTerms] {if {[$p getIoType] eq "INPUT"} {lappend ports [$p getName]}}
    if {[llength $ports]} {
      if {[llength $ports] == 1} {set root [lindex $ports 0]}
      break
    }
    set drv [f4::drv $cur]
    if {$drv eq "" || ![regexp {^(BUF|INV|CKINV|HB)} [[$drv getMaster] getName]]} break
    set inputs {}
    foreach t [$drv getITerms] {if {[$t isInputSignal]} {lappend inputs [$t getNet]}}
    if {[llength $inputs] != 1} break
    set cur [lindex $inputs 0]
  }
  foreach net $path {dict set roots $net $root}
  return $root
}
proc f4::same_native_root {a b} {
  if {![info exists ::env(OT_DTAP_PORTS)] || ![llength $::env(OT_DTAP_PORTS)]} {return 1}
  set ar [f4::native_root $a]; set br [f4::native_root $b]
  return [expr {$ar ne "" && $ar eq $br && [lsearch -exact $::env(OT_DTAP_PORTS) $ar] >= 0}]
}
# S81-RCK-9 11-07 OT_F4_XLEAF_HOLD_PS (opt-in, default off = unchanged): hold-safe shift form for the zero-logic
# pairs that F4 PAIR could not co-leaf.  SVC SMD form C / SML form C routed with FF hold -5.58/36 and -3.88/60: the GRT
# hold repair padded every pair to >= 0 on the estimated clock RC, and the routed leaf-to-leaf skew moved 35 of the 280
# cross-leaf zero-logic captures within 10 ps below 0 (1 of 1864 same-leaf captures).  For each capture still on another
# leaf than its launch, this sets a pin hold uncertainty of OT_F4_XLEAF_BASE_PS (the kit clock hold uncertainty, 25) +
# OT_F4_XLEAF_HOLD_PS on its CLK pin, so the route-stage hold repair pads exactly those pairs for routed leaf drift.  The
# guard is a repair target only: write_sdc carries it into the stage SDCs; sign-off reads its own golden SDC (gate
# FF hold >= 0 unchanged, no margin there).
proc f4::xleaf_guard {pairs} {
  set g $::env(OT_F4_XLEAF_HOLD_PS)
  set base [expr {[info exists ::env(OT_F4_XLEAF_BASE_PS)] ? $::env(OT_F4_XLEAF_BASE_PS) : 25}]
  set b [ord::get_db_block]
  set pins {}; set miss 0
  foreach {c p} $pairs {
    set ci [$b findInst $c]; set pi [$b findInst $p]
    if {$ci eq "NULL" || $pi eq "NULL"} continue
    set cc [f4::it $ci CLK]; set pc [f4::it $pi CLK]
    if {$cc eq "" || $pc eq ""} continue
    if {[$cc getNet] eq [$pc getNet]} continue
    set nm [regsub -all {([\[\]])} "[string map {"\\" ""} $c]/CLK" {\\\1}]
    set pin [get_pins -quiet $nm]
    if {[llength $pin] != 1} { incr miss; continue }
    lappend pins $pin
  }
  if {[llength $pins]} { set_clock_uncertainty -hold [expr {$base + $g}] $pins }
  puts "OT_F4 XLEAF hold guard: [llength $pins] cross-leaf zero-logic captures at [expr {$base + $g}] ps hold uncertainty (+$g), unresolved $miss"
  if {$miss} { error "OT_F4 XLEAF: $miss capture CLK pins did not resolve in STA" }
}
proc f4::run {} {
  variable roots; set roots [dict create]
  set b [ord::get_db_block]
  array set pred {}
  foreach i [$b getInsts] {
    if {![f4::is_ff $i]} continue
    set d [f4::it $i D]; if {$d eq ""} continue
    set s [f4::drv [$d getNet]]; if {$s eq ""} continue
    set m [[$s getMaster] getName]
    if {[regexp {^(INV|BUF)} $m] && ![string match *clk* [$s getName]]} {
      set a ""; foreach t [$s getITerms] { if {[$t isInputSignal]} { set a [$t getNet]; break } }
      set s [f4::drv $a]; if {$s eq ""} continue
    }
    if {![f4::is_ff $s] || $s eq $i} continue
    set pred([$i getName]) [$s getName]
  }
  # chains: follow pred to the head
  array set head {}; array set size {}
  foreach c [array names pred] {
    set h $c; set k 0
    while {[info exists pred($h)] && $k < 64} { set h $pred($h); incr k }
    set head($c) $h; incr size($h)
  }
  set moved 0; set skipped 0; set far 0; set rootskip 0; array set added {}
  if {[info exists ::env(OT_F4_PAIR)] && $::env(OT_F4_PAIR)} {
    # HBM-CORES-KITS-20 OT_F4_PAIR (opt-in): walk every chain head->tail and put each capture on the CURRENT leaf of
    # its own launch flop (not the chain head), bounded by OT_F4_MAX_UM from that leaf driver and OT_F4_LEAF_ADD per leaf.
    set dbu [[$b getTech] getDbUnitsPerMicron]
    set ord {}
    foreach c [array names head] {
      set k 0; set x $c
      while {[info exists pred($x)] && $k < 64} { set x $pred($x); incr k }
      lappend ord [list $k $c]
    }
    foreach e [lsort -integer -index 0 $ord] {
      set c [lindex $e 1]; set p $pred($c)
      set pi [$b findInst $p]; set ci [$b findInst $c]
      set pc [f4::it $pi CLK]; set cc [f4::it $ci CLK]
      if {$pc eq "" || $cc eq ""} continue
      set pn [$pc getNet]; set cn [$cc getNet]
      if {$pn eq "NULL" || $cn eq "NULL" || $pn eq $cn} continue
      if {![f4::same_native_root $pn $cn]} {incr rootskip; continue}
      set key [$pn getName]; set ld [f4::drv $pn]
      if {$ld eq ""} { incr skipped; continue }
      set lp [$ld getLocation]; set cp [$ci getLocation]
      if {(abs([lindex $lp 0]-[lindex $cp 0]) + abs([lindex $lp 1]-[lindex $cp 1])) > $::f4_um * $dbu} { incr far; continue }
      if {[info exists added($key)] && $added($key) >= $::f4_add} { incr skipped; continue }
      $cc disconnect; $cc connect $pn
      incr added($key); incr moved
    }
    set note ""; if {[info exists ::env(OT_DTAP_PORTS)]} {set note " cross_root_skipped $rootskip"}
    puts "OT_F4 PAIR pairs [array size pred] moved $moved skipped $skipped far $far leaves_touched [array size added]$note"
    if {[info exists ::env(OT_F4_XLEAF_HOLD_PS)] && $::env(OT_F4_XLEAF_HOLD_PS) > 0} { f4::xleaf_guard [array get pred] }
    return
  }
  set dbu [[$b getTech] getDbUnitsPerMicron]
  foreach c [array names head] {
    set h $head($c)
    if {$size($h) + 1 > $::f4_max} { incr skipped; continue }
    set hi [$b findInst $h]; set ci [$b findInst $c]
    set hc [f4::it $hi CLK]; set cc [f4::it $ci CLK]
    if {$hc eq "" || $cc eq ""} continue
    set hn [$hc getNet]; set cn [$cc getNet]
    if {$hn eq "NULL" || $cn eq "NULL" || $hn eq $cn} continue
    if {![f4::same_native_root $hn $cn]} {incr rootskip; continue}
    set key [$hn getName]
    set ld [f4::drv $hn]
    if {$ld eq ""} { incr skipped; continue }
    set lp [$ld getLocation]; set cp [$ci getLocation]
    if {(abs([lindex $lp 0]-[lindex $cp 0]) + abs([lindex $lp 1]-[lindex $cp 1])) > $::f4_um * $dbu} { incr far; continue }
    if {[info exists added($key)] && $added($key) >= $::f4_add} { incr skipped; continue }
    $cc disconnect; $cc connect $hn
    incr added($key); incr moved
  }
  set note ""; if {[info exists ::env(OT_DTAP_PORTS)]} {set note " cross_root_skipped $rootskip"}
  puts "OT_F4 pairs [array size pred] moved $moved skipped $skipped far $far leaves_touched [array size added]$note"
}
f4::run
if {[info exists ::env(OT_F4_NEXT_TCL)] && $::env(OT_F4_NEXT_TCL) ne ""} { source $::env(OT_F4_NEXT_TCL) }
