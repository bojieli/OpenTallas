# BF-FLAT-1011 2026-10-10 (OWNER full-rate push): per-pipeline-instance CTS leaf groups for the BF lane / tree adders.
# OT_CTS_FIX_HOOKS PRE_CTS hook for ot_s81_bf_native (full rate), chain AFTER pinclk_group.tcl.
# Why: with the pin->gated class removed (PINLAT, bfp_lat_c900: 1,407 -> 2), the routed FF hold residue is ~2,000 R2R
# gated->gated endpoints on the SHORT pipeline hops inside one adder (ot_v41_fadd u_cK.g_r.r -> u_cK+1, BF lane chain
# u_c.u_add, BF tree u_bf.g_lv[].g_n[].u_a, the multiplier u_m s4_y -> y): data ~45 ps (pass-through bits: clk->q + wire),
# capture-launch skew +30 ps.  Launch and capture sit in the SAME gated tree but on different TritonCTS leaf clusters,
# because sink clustering is purely geometric over the whole column/lane gated net (thousands of sinks), so two stage
# registers 5 um apart can land on leaves whose insertion differs by tens of ps.
# Fix (flow only, RTL unchanged): every adder / multiplier instance (hierarchy key = the outermost .u_a / .u_add / .u_m
# instance in the flop's name) gets its own clock buffer, placed at the instance's sink centroid and driven from the
# group's current (gated) clock net; the instance's register clock pins move to the buffer's new net.  TritonCTS then
# builds one compact child tree per instance (as for the ICG gclk nets) and latency-balances the child trees (CTS-0033),
# so the stage-to-stage hops inside one adder share a small local tree: their skew is the local tree's, not the column's.
# Function is unchanged (a clock buffer); STA times the real result.  Fails closed if no group is built.
# Post-CTS it prints BF_LANEGRP intra-group arrival spread statistics (the early signal).
proc bf_lg_is_seq {m} { return [regexp {^(DFF|DHL|DLL|SDF|ASYNC_DFF)} [$m getName]] }
proc bf_lanegrp {} {
  set blk [ord::get_db_block]
  set re [expr {[info exists ::env(BF_LANEGRP_RE)] ? $::env(BF_LANEGRP_RE) : {^(.*?\.(?:u_a|u_add|u_m))\.}}]
  set minn [expr {[info exists ::env(BF_LANEGRP_MIN)] ? $::env(BF_LANEGRP_MIN) : 8}]
  array set G {}
  set nsk 0
  foreach inst [$blk getInsts] {
    set n [$inst getName]
    if {![regexp $re $n -> key]} continue
    if {![bf_lg_is_seq [$inst getMaster]]} continue
    set ck [$inst findITerm CLK]
    if {$ck eq "NULL" || $ck eq ""} continue
    set net [$ck getNet]
    if {$net eq "NULL" || $net eq ""} continue
    lappend G([list $key [$net getName]]) $ck
  }
  set bm [[ord::get_db] findMaster [expr {[info exists ::env(BF_LANEGRP_BUF)] ? $::env(BF_LANEGRP_BUF) : "BUFx12f_ASAP7_75t_R"}]]
  if {$bm eq "NULL" || $bm eq ""} { error "BF_LANEGRP: no buffer master" }
  set core [$blk getCoreArea]; set w [$bm getWidth]; set h [$bm getHeight]
  set g 0; set small 0
  foreach k [array names G] {
    set cl $G($k)
    if {[llength $cl] < $minn} { incr small; continue }
    set src [[lindex $cl 0] getNet]
    set bn "bf_lanegrp_buf$g"; set nnn "bf_lanegrp$g"
    set b [odb::dbInst_create $blk $bm $bn]
    set nn [odb::dbNet_create $blk $nnn]
    $nn setSigType CLOCK
    [$b findITerm A] connect $src
    [$b findITerm Y] connect $nn
    set sx 0; set sy 0
    foreach it $cl { lassign [[$it getInst] getLocation] x y; incr sx $x; incr sy $y; $it disconnect; $it connect $nn }
    set x [expr {max([$core xMin], min($sx / [llength $cl], [$core xMax] - $w))}]
    set y [expr {max([$core yMin], min($sy / [llength $cl], [$core yMax] - $h))}]
    $b setLocation $x $y
    $b setPlacementStatus PLACED
    lappend ::bf_lanegrp_nets $nnn
    incr nsk [llength $cl]
    incr g
  }
  if {$g == 0} { error "BF_LANEGRP: no adder/multiplier register group found (re $re)" }
  puts "BF_LANEGRP groups: $g ($nsk register clock pins; $small groups below $minn sinks left in place)"
  # legalise the new buffers (they overlap placed cells); detailed_placement runs again after CTS anyway
  catch { detailed_placement }
}
proc bf_lanegrp_stats {tag} {
  catch { set_propagated_clock [all_clocks]; estimate_parasitics -placement }
  if {[catch {
    set ns 0; set ssum 0.0; set smax 0.0
    foreach r [all_registers -clock_pins] {
      set n [get_full_name $r]
      if {![regexp {^(.*?\.(?:u_a|u_add|u_m))\.} $n -> key]} continue
      set a [get_property $r arrival_max_rise]
      if {![string is double -strict $a]} continue
      if {![info exists MN($key)] || $a < $MN($key)} { set MN($key) $a }
      if {![info exists MX($key)] || $a > $MX($key)} { set MX($key) $a }
    }
    foreach key [array names MN] {
      set s [expr {$MX($key) - $MN($key)}]; incr ns; set ssum [expr {$ssum + $s}]; set smax [expr {max($smax, $s)}]
    }
    if {$ns} { puts [format "BF_LANEGRP %s intra-group arrival spread: groups %d mean %.1f max %.1f" $tag $ns [expr {$ssum/$ns}] $smax] }
  } e]} { puts "BF_LANEGRP $tag stats failed: $e" }
}
if {[info procs clock_tree_synthesis] ne "" && [info procs bf_lg_cts_orig] eq ""} {
  rename clock_tree_synthesis bf_lg_cts_orig
  proc clock_tree_synthesis {args} {
    bf_lanegrp
    bf_lg_cts_orig {*}$args
    bf_lanegrp_stats post_cts
  }
}
