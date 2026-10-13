# el1011-ds-vm/be 2026-10-12: re-apply the dsfd_vm_be_sl stream-domain boundary (str_clk on cks; vrv/vrq out, rns_in in)
# AFTER the ref_tile io_ref switch, which unsets every IO delay and re-times all ports against core_clk.  Without this the
# stream ports are timed against core_clk (or not at all) from CTS to detail route and only meet str_clk at sign-off.
# Sourced via spec "boundary_tcl" (tools/ref_tile): in PRE_CTS it wraps clock_tree_synthesis (after the io_ref wrapper),
# so the str_clk delays are referenced to the PROPAGATED str_clk tree and baked into 4_cts.sdc; in PRE_GLOBAL_ROUTE and
# POST_DETAIL_ROUTE it runs directly after pre_ref_skew / post_plain.
#
# r3 (2026-10-12): INTER-CLOCK INSERTION BALANCE.  core_clk (ck, 833 ps) and str_clk (cks, 625 ps) are one 4:3
# ratio-synchronous pair; the u_rc0/u_rc1 crossings (mem->sh, w_st->w_st_r, wp_pub->wp_r and back rp->rp_w, r_st->r_st_w)
# are single flop-to-flop hops timed in the 208 ps edge window (core 1667 -> str 1875, str 625 -> core 833).  TritonCTS
# builds the two trees independently: r2 routed ck at 276 ps and cks at 172 ps, so every core->str hop lost 104 ps
# (TT -34.26 on a 68 ps data path) and every str->core hop needed hold buffers.  The die drives ck and cks with one
# arrival (one PLL root, contract clock entry), so the tile must deliver ONE insertion on both: right after CTS a
# dont_touch buffer chain is spliced between the cks port and its tree root until the mean str_clk sink insertion is
# within OT_BESL_BAL_TOL (12 ps; ~14 ps per BUFx12f stage) of core_clk's.  Legalised by the CTS step's detailed placement; the chain nets are
# CLOCK nets, so the exported ETM carries the balanced cks insertion.
set ::ot_besl_sdc [file join [file dirname [info script]] be_sl_clock_ref.sdc]
proc ot_besl_str_boundary {} {
  catch {estimate_parasitics -placement}
  read_sdc $::ot_besl_sdc
  puts "BE_SL str_clk boundary re-applied after io_ref switch"
}
# r4 (2026-10-13, el1011-ds-vm/besl): CROSSING-REFERENCED, TWO-SIDED balance.  r3 routed TT +7.85 / FF -6.57: all 9
# failing endpoints are str_clk -> core_clk pointer / state hops (u_rc*.rp -> rp_w, r_st -> r_st_w; launch cks leaf
# 219.8 ps, capture ck leaf 258.7 ps at FF = 39 ps inter-tree skew against a 38 ps clk->Q).  r3 balanced the mean over
# ALL registers of each clock and stopped as soon as str was within +12 ps EARLY (one-sided), which routed str early by
# 10 ps TT / 18 ps FF: the wrong sign for every str -> core hop.  The reference is now the crossing flops themselves,
# pointer hops and storage hops weighted equally (12 + 12 pointer flops must not be averaged away by 2,048 mem/sh
# flops), and the chain stops at the first stage that brings core - str to <= OT_BESL_BAL_TOL (0 ps; FF ran 8 ps earlier than TT in r3): with a ~12 ps
# stage the TT residual is (-14, 0] ps, i.e. about (-4, +9] at FF.
proc ot_besl_ins_mean {clk} {
  catch {sta::worst_slack_cmd max}
  if {$clk eq "core_clk"} {
    set ptr {\.(rp_w|r_st_w|wp_pub|w_st)\[}; set sto {\.mem\[}
  } else {
    set ptr {\.(rp|r_st|wp_r|w_st_r)\[}; set sto {\.sh\[}
  }
  set sp 0.0; set np 0; set ss 0.0; set ns 0; set sa 0.0; set na 0
  foreach p [all_registers -clock $clk -clock_pins] {
    set a [get_property $p arrival_max_rise]
    if {![string is double -strict $a] || abs($a) >= 1e5} { continue }
    set sa [expr {$sa + $a}]; incr na
    set nm [get_full_name $p]
    if {![regexp {u_rc[01]} $nm]} { continue }
    if {[regexp $ptr $nm]} { set sp [expr {$sp + $a}]; incr np } elseif {[regexp $sto $nm]} { set ss [expr {$ss + $a}]; incr ns }
  }
  if {$na == 0} { return "" }
  if {$np > 0 && $ns > 0} {
    puts [format "BE_SL clk balance ref %s: crossing pointer %.1f (n %d) storage %.1f (n %d) all %.1f (n %d)" $clk [expr {$sp/$np}] $np [expr {$ss/$ns}] $ns [expr {$sa/$na}] $na]
    return [expr {0.5 * ($sp / $np + $ss / $ns)}]
  }
  puts "BE_SL clk balance ref $clk: no crossing flops matched (pointer $np storage $ns); all-register mean"
  return [expr {$sa / $na}]
}
proc ot_besl_clk_balance {} {
  set tol [expr {[info exists ::env(OT_BESL_BAL_TOL)] ? $::env(OT_BESL_BAL_TOL) : 0.0}]
  set blk [ord::get_db_block]
  set db [ord::get_db]
  set bt [$blk findBTerm cks]
  if {$bt eq "NULL"} { set bt [$blk findBTerm {cks[0]}] }
  if {$bt eq "NULL" || [$bt getNet] eq "NULL"} { puts "BE_SL clk balance: no cks port net; skipped"; return }
  set fast BUFx12f_ASAP7_75t_R
  catch {set_propagated_clock [all_clocks]}
  set k 0
  for {set it 0} {$it < 24} {incr it} {
    catch {estimate_parasitics -placement}
    set lc [ot_besl_ins_mean core_clk]
    set ls [ot_besl_ins_mean str_clk]
    if {$lc eq "" || $ls eq ""} { puts "BE_SL clk balance: no insertion (core '$lc' str '$ls'); skipped"; return }
    set d [expr {$lc - $ls}]
    puts [format "BE_SL clk balance it %d: core_clk %.1f ps str_clk %.1f ps (d %.1f, %d chain cells)" $it $lc $ls $d $k]
    if {$d <= $tol} break
    # one strong buffer stage per step (~14 ps at the root, measured on r2); a weak delay cell (HB4) driving the
    # BUFx24 root costs ~100 ps in one step and overshoots, so the chain is built from strong stages only
    set mname $fast
    set m [$db findMaster $mname]
    if {$m eq "NULL"} { puts "BE_SL clk balance: no master $mname"; return }
    set n0 [$bt getNet]
    # the chain stage sits next to the first load of the port net (the tree root), so the hop wire is short
    set loads {}
    foreach it2 [$n0 getITerms] { lappend loads $it2 }
    if {![llength $loads]} { puts "BE_SL clk balance: cks net has no loads"; return }
    set ref [[lindex $loads 0] getInst]
    lassign [$ref getLocation] x y
    set c [odb::dbInst_create $blk $m "ot_besl_cksbal_$k"]
    set n1 [odb::dbNet_create $blk "ot_besl_cksbal_n$k"]
    $n1 setSigType CLOCK
    # the port net and the tree root may be dont_touch (clk_net_protect): lift for the reconnect only, then restore
    set ndt 0
    catch {set ndt [$n0 isDoNotTouch]}
    if {$ndt} { $n0 setDoNotTouch 0 }
    foreach l $loads {
      set li [$l getInst]; set dt 0
      catch {set dt [$li isDoNotTouch]}
      if {$dt} { $li setDoNotTouch 0 }
      $l disconnect; $l connect $n1
      if {$dt} { $li setDoNotTouch 1 }
    }
    [$c findITerm A] connect $n0
    [$c findITerm Y] connect $n1
    if {$ndt} { $n0 setDoNotTouch 1; $n1 setDoNotTouch 1 }
    $c setLocation $x $y
    $c setPlacementStatus PLACED
    catch {$c setDoNotTouch 1}
    incr k
  }
  puts [format "BE_SL clk balance done: %d chain cells, core_clk %.1f str_clk %.1f" $k $lc $ls]
  set ::ot_besl_bal_cells $k
}
if {[llength [info commands ::qdm_cts_orig]] && ![llength [info commands ::ot_besl_cts_inner]]} {
  rename clock_tree_synthesis ::ot_besl_cts_inner
  proc clock_tree_synthesis {args} {
    ::ot_besl_cts_inner {*}$args
    if {![info exists ::env(OT_BESL_BAL)] || $::env(OT_BESL_BAL) ne "0"} { ot_besl_clk_balance }
    ot_besl_str_boundary
  }
} else {
  ot_besl_str_boundary
}
