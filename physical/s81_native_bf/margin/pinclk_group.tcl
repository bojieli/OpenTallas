# BF-PINCLK 2026-10-09 (OWNER, CRITICAL_PATH 1): the PINREG input capture registers as ONE CTS sink group.
# OT_CTS_FIX_HOOKS PRE_CTS hook for ot_s81_bf_native (full rate, PINREG=1).
# Why: every full-rate route misses FF hold on the ~1,650 input pin-register endpoints (g_pin.r_xb_d / r_xs_q0 / r_xs_q1 /
# r_xb_u / cfg_*).  The sign-off input min is L = the MEAN clock arrival of the g_pin.r_* registers (signoff_ref.sdc), so
# an input endpoint's hold slack is L - arrival_i - 25 (uncertainty) - ~13 (t_hold) + path: every pin register above the
# mean loses its skew.  Before this hook the pin registers share TritonCTS's ungated clk_regs tree with ~1,000 other
# registers spread over the die (32-sink clusters picked by geometry), so their arrivals span tens of ps.
# Fix (flow only, RTL unchanged; the pin registers are already ungated in full rate: pclk = clk when HALF = 0):
# one dedicated clock buffer (bf_pinclk_root, the CTS buffer master), placed at the clock root (the clk port), drives a
# new clock net bf_pinclk that carries ONLY the g_pin.r_* register clock pins.  TritonCTS builds that net as its own
# child tree (as it does for the element ICG's gclk) and latency-balances it against the other trees (CTS-0033), so the
# pin registers are balanced as one group instead of being mixed into clusters with internal registers.
# Function is unchanged (a clock buffer); STA times the real result.  Fails closed if no pin register is found.
# Post-CTS the hook prints BF_PINCLK arrival statistics (pin group vs all other registers) = the early signal.
proc bf_pc_is_seq {m} { return [regexp {^(DFF|DHL|DLL|SDF|ASYNC_DFF)} [$m getName]] }
proc bf_pinclk_group {} {
  set blk [ord::get_db_block]
  set bt [$blk findBTerm clk]
  if {$bt eq "NULL" || $bt eq ""} { error "BF_PINCLK: no clk port" }
  set root [$bt getNet]
  set pat [expr {[info exists ::env(BF_PINCLK_PATTERN)] ? $::env(BF_PINCLK_PATTERN) : "g_pin.r_*"}]
  set sinks {}; set skipped 0
  foreach inst [$blk getInsts] {
    set iname [$inst getName]
    if {![string match $pat $iname] && ![string match {cfg_d_i*} $iname]} continue
    if {![bf_pc_is_seq [$inst getMaster]]} continue
    set ck [$inst findITerm CLK]
    if {$ck eq "NULL" || $ck eq ""} continue
    if {[$ck getNet] ne $root} { incr skipped; continue }
    lappend sinks $ck
  }
  if {[llength $sinks] == 0} { error "BF_PINCLK: no $pat register on the root clock net [$root getName] (skipped $skipped)" }
  set bm [[ord::get_db] findMaster [expr {[info exists ::env(BF_PINCLK_BUF)] ? $::env(BF_PINCLK_BUF) : "BUFx24_ASAP7_75t_R"}]]
  if {$bm eq "NULL" || $bm eq ""} { error "BF_PINCLK: no buffer master" }
  set b [odb::dbInst_create $blk $bm bf_pinclk_root]
  set nn [odb::dbNet_create $blk bf_pinclk]
  $nn setSigType CLOCK
  [$b findITerm A] connect $root
  [$b findITerm Y] connect $nn
  foreach it $sinks { $it disconnect; $it connect $nn }
  # at the clock root: the clk port, pulled inside the core area
  set bb [$bt getBBox]
  set x [expr {([$bb xMin] + [$bb xMax]) / 2}]; set y [expr {([$bb yMin] + [$bb yMax]) / 2}]
  set core [$blk getCoreArea]
  set w [$bm getWidth]; set h [$bm getHeight]
  set x [expr {max([$core xMin], min($x, [$core xMax] - $w))}]
  set y [expr {max([$core yMin], min($y, [$core yMax] - $h))}]
  $b setLocation $x $y
  $b setPlacementStatus PLACED
  puts "BF_PINCLK group: [llength $sinks] $pat register clock pins moved from [$root getName] to bf_pinclk (driver bf_pinclk_root [$bm getName] at [expr {$x/1000.0}] [expr {$y/1000.0}] um); $skipped matching registers on other clock nets left in place"
  set ::bf_pinclk_n [llength $sinks]
}
proc bf_pinclk_stats {tag} {
  if {[catch {
    set_propagated_clock [all_clocks]
    estimate_parasitics -placement
    set w [sta::worst_slack_cmd max]
    set pn 0; set ps 0.0; set pmin 1e9; set pmax -1e9; set on 0; set os 0.0; set omin 1e9; set omax -1e9
    set pins {}
    foreach p [all_registers -clock_pins] {
      set a [get_property $p arrival_max_rise]
      if {$a eq "INF" || $a eq "" || ![string is double -strict $a]} continue
      set n [get_full_name $p]
      if {[string match "g_pin.r_*" $n]} {
        incr pn; set ps [expr {$ps + $a}]; set pmin [expr {min($pmin, $a)}]; set pmax [expr {max($pmax, $a)}]
      } else {
        incr on; set os [expr {$os + $a}]; set omin [expr {min($omin, $a)}]; set omax [expr {max($omax, $a)}]
      }
    }
    if {$pn > 0 && $on > 0} {
      puts [format "BF_PINCLK %s pin group n %d arrival min %.1f mean %.1f max %.1f (max-mean %.1f) | other regs n %d min %.1f mean %.1f max %.1f" \
        $tag $pn $pmin [expr {$ps/$pn}] $pmax [expr {$pmax - $ps/$pn}] $on $omin [expr {$os/$on}] $omax]
    }
  } e]} { puts "BF_PINCLK $tag stats failed: $e" }
}

# v3 (2026-10-09 19:30, owner STRUCTURAL hold): hold classification of the routed c900 / a / b dbs: the dominant class is R2R
# g_pin.r_* (pin group, ungated) -> g_rc.u_elem.g_qb.g_bx.b_* (element input regs on the ICG-gated eclk tree): 1,407 endpoints,
# worst -37.4, mean capture-launch skew +52 ps with ~73 ps of data path.  TritonCTS balanced the pin group to the overall mean,
# but its capture regs sit on the deeper gated tree.  Fix: after CTS, delay the WHOLE pin group (a buffer chain in front of
# bf_pinclk_root, one point, so the group stays tight) until its mean clock arrival reaches the mean arrival of the b_* capture
# registers + ::bf_pinclk_shift_extra ps.  I2R / outputs are unaffected: the sign-off IO reference L is the pin group's own
# mean.  Setup on pin -> b_* is short (data ~73 ps).  The 48 cfg_d capture flops (yosys name cfg_d_i*) join the group.
proc bf_pc_mean {pat} {
  set s 0.0; set n 0
  foreach p [get_pins -quiet -hierarchical $pat] { set a [get_property $p arrival_max_rise]; if {[string is double -strict $a]} { set s [expr {$s+$a}]; incr n } }
  return [expr {$n ? $s/$n : -1}]
}
proc bf_pinclk_shift {} {
  set ex [expr {[info exists ::bf_pinclk_shift_extra] ? $::bf_pinclk_shift_extra : 0}]
  set blk [ord::get_db_block]
  set rb [$blk findInst bf_pinclk_root]; if {$rb eq "NULL" || $rb eq ""} { puts "BF_PINCLK shift: no root"; return }
  set root [[$rb findITerm A] getNet]
  set bm [[ord::get_db] findMaster BUFx4_ASAP7_75t_R]
  lassign [$rb getLocation] x y
  set_propagated_clock [all_clocks]
  for {set i 0} {$i < 40} {incr i} {
    estimate_parasitics -placement
    set w [sta::worst_slack_cmd max]
    set mp [bf_pc_mean g_pin.r_*/CLK]; set mb [bf_pc_mean g_rc.u_elem.g_qb.g_bx.b_*/CLK]
    puts [format "BF_PINCLK shift it %d: pin mean %.1f, b_* capture mean %.1f, target +%s" $i $mp $mb $ex]
    if {$mp < 0 || $mb < 0 || $mp >= $mb + $ex - 4} break
    # one more buffer at the head of the chain (between the root clock net and the current chain input)
    set a [$rb findITerm A]
    set cur [$a getNet]
    set b [odb::dbInst_create $blk $bm bf_pinclk_dly$i]
    set nn [odb::dbNet_create $blk bf_pinclk_dly${i}_n]; $nn setSigType CLOCK
    $a disconnect; $a connect $nn
    [$b findITerm Y] connect $nn
    [$b findITerm A] connect $cur
    $b setLocation $x $y; $b setPlacementStatus PLACED
    set rb $b
  }
  puts "BF_PINCLK shift: $i delay buffers in front of bf_pinclk_root"
}
if {[info procs clock_tree_synthesis] ne "" && [info procs bf_pc_cts_orig] eq ""} {
  rename clock_tree_synthesis bf_pc_cts_orig
  proc clock_tree_synthesis {args} {
    bf_pinclk_group
    bf_pc_cts_orig {*}$args
    bf_pinclk_stats post_cts
    bf_pinclk_shift
    bf_pinclk_stats post_shift
  }
}
