# HBM-CORES 2026-10-25 F4 (GEOM-REVIEW-2 argmax_r2 / cqb F4): zero-logic register chains on ONE clock leaf.
# Post-CTS: every flop whose D is driven by another flop's Q directly or through one INV/BUF (shift / pin-reg ->
# stage-2 pairs) is moved, chain by chain, onto the clock leaf net of the chain head, so launch and capture share a
# leaf (skew ~ wire only) instead of relying on hold-buffer fill.  Chains > OT_F4_MAX (16) flops are left as is;
# a leaf grows by at most OT_F4_LEAF_ADD (12) sinks.  Then the platform POST_CTS hook (tap balance) runs.
# 10-25 05:12 gq_rr19: a capture is moved only when it lies within OT_F4_MAX_UM (20 um, Manhattan) of the head
# leaf driver; without that bound F4 hung far face flops on a near leaf (256 ps leaf wire, FF hold -204 ps).
set ::f4_max [expr {[info exists ::env(OT_F4_MAX)] ? $::env(OT_F4_MAX) : 16}]
set ::f4_um [expr {[info exists ::env(OT_F4_MAX_UM)] ? $::env(OT_F4_MAX_UM) : 20}]
set ::f4_add [expr {[info exists ::env(OT_F4_LEAF_ADD)] ? $::env(OT_F4_LEAF_ADD) : 12}]
namespace eval f4 {}
proc f4::is_ff {i} { return [string match DFF* [[$i getMaster] getName]] }
proc f4::it {i name} { foreach t [$i getITerms] { if {[[$t getMTerm] getName] eq $name} { return $t } }; return "" }
proc f4::drv {n} { if {$n eq "" || $n eq "NULL"} { return "" }; foreach t [$n getITerms] { if {[$t isOutputSignal]} { return [$t getInst] } }; return "" }
proc f4::run {} {
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
  set moved 0; set skipped 0; set far 0; array set added {}
  set dbu [[$b getTech] getDbUnitsPerMicron]
  foreach c [array names head] {
    set h $head($c)
    if {$size($h) + 1 > $::f4_max} { incr skipped; continue }
    set hi [$b findInst $h]; set ci [$b findInst $c]
    set hc [f4::it $hi CLK]; set cc [f4::it $ci CLK]
    if {$hc eq "" || $cc eq ""} continue
    set hn [$hc getNet]; set cn [$cc getNet]
    if {$hn eq "NULL" || $cn eq "NULL" || $hn eq $cn} continue
    set key [$hn getName]
    set ld [f4::drv $hn]
    if {$ld eq ""} { incr skipped; continue }
    set lp [$ld getLocation]; set cp [$ci getLocation]
    if {(abs([lindex $lp 0]-[lindex $cp 0]) + abs([lindex $lp 1]-[lindex $cp 1])) > $::f4_um * $dbu} { incr far; continue }
    if {[info exists added($key)] && $added($key) >= $::f4_add} { incr skipped; continue }
    $cc disconnect; $cc connect $hn
    incr added($key); incr moved
  }
  puts "OT_F4 pairs [array size pred] moved $moved skipped $skipped far $far leaves_touched [array size added]"
}
f4::run
if {[info exists ::env(OT_F4_NEXT_TCL)] && $::env(OT_F4_NEXT_TCL) ne ""} { source $::env(OT_F4_NEXT_TCL) }
