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
    if {![string match $pat [$inst getName]]} continue
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
if {[info procs clock_tree_synthesis] ne "" && [info procs bf_pc_cts_orig] eq ""} {
  rename clock_tree_synthesis bf_pc_cts_orig
  proc clock_tree_synthesis {args} {
    bf_pinclk_group
    bf_pc_cts_orig {*}$args
    bf_pinclk_stats post_cts
  }
}
