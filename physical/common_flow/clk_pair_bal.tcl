# clk_pair_bal.tcl -- OT_CLK_PAIR_BAL (HBM-TAPS 11-12, DIE-HBM-100 approved paper form; DEFAULT OFF): post-GRT, hold-corner
# pair balance of clock-tree subtrees that launch and capture the same hold-critical reg2reg paths.
# Why: core_tap_align.tcl equalises density-tap MEAN insertion at POST_CTS on placement RC at the CTS corner, before the
# leaf repeat and GRT.  Routed FF hold then fails on cross-tree pairs (ksh_t19: 116 of 117 violators cross-tap, launch
# taps 398..419 ps vs capture taps 424..474 ps, WNS -21.07; opsbg_C4A: no taps, 12 of 20 violators diverge at the root
# buffer pair).  A tap-mean target cannot see which pairs are critical; this pass works on the pairs themselves.
# Method (one GRT-RC timing state, the hold corner for hold and the setup corner for setup):
#  1. hold paths with slack < 0 at the hold corner -> launch / capture clock pins; each sink maps to a NODE:
#     the nearest ot_dtap_<n> ancestor (cut dtap, when the design has density taps), else the child of the launch / capture
#     tree divergence (cut branch; may be the register itself).  ROOT = the clock source (fixed).
#  2. potentials phi(node) >= 0 = extra early arrival added in front of the node (cumulative over chosen ancestors):
#       hold   (every path with hold slack < OT_CLK_PAIR_BAL_WIN_PS, both nodes mapped):  phi(L) - phi(C) >= m - slack
#       setup  (paths with setup slack < margin + scale * max shift):                     phi(L) - phi(C) <= (s - ms) / scale
#       nesting phi(child) >= phi(parent node)                       (ROOT stays 0; m = OT_CLK_PAIR_BAL_MARGIN_PS)
#     minimal solution = longest path from 0 (Bellman-Ford).  A launch/capture pair constrained both ways beyond any shift
#     and a same-node path are reported RESIDUAL (hold ECO / leaf class); a positive cycle or a shift above
#     OT_CLK_PAIR_BAL_MAX_PS drops the largest violator requirement into RESIDUAL and re-solves.
#  3. each node gets its d = phi(node) - phi(parent) as delay cells (OT_CLK_PAIR_BAL_CELL) in front of its input pin,
#     top-down, per-node measured ps/cell, inside global_route -start_incremental .. -end_incremental (the
#     clk_leaf_repeat grt pattern), at most OT_CLK_PAIR_BAL_ROUNDS rounds.
#  4. report hold WNS / count at the hold corner and setup WNS at the setup corner before / after.  Nothing else changes:
#     no gate, margin or repair setting; the flow's own hold / setup repair runs afterwards as before.
# Hook: physical/common_flow/grt183_make.sh sources /work/clk_pair_bal.tcl in ORFS global_route.tcl right after the
# clk_leaf_repeat grt pass (CLK-LEAF-BAL-1 owns that file; this pass sees its final tree).  Off unless OT_CLK_PAIR_BAL=1.
# env: OT_CLK_PAIR_BAL_HOLD_CORNER / _SETUP_CORNER (default: the corner named bc|ff / the other one; one corner = both),
#      _MARGIN_PS 2, _WIN_PS 30, _SETUP_MARGIN_PS 10, _SETUP_SCALE 2.0 (setup-corner ps per hold-corner ps of shift),
#      _MAX_PS 40, _CELL BUFx4_ASAP7_75t_R, _STEP_PS 10 (first guess, hold corner), _ROUNDS 4, _TOL_PS 2, _EPC 8,
#      _REG2REG 1 (reg2reg paths only), _CUT auto|dtap|branch, _DRY 1 = solve and report only (no edit), _GRT 0 = routed-copy trial (no route calls).
if {![info exists ::env(OT_CLK_PAIR_BAL)] || $::env(OT_CLK_PAIR_BAL) ne "1"} { return }
uplevel #0 {
proc cpb_env {k d} { expr {[info exists ::env(OT_CLK_PAIR_BAL_$k)] && $::env(OT_CLK_PAIR_BAL_$k) ne "" ? $::env(OT_CLK_PAIR_BAL_$k) : $d} }
set cpb_blk [ord::get_db_block]
set cpb_m [cpb_env MARGIN_PS 2.0]; set cpb_win [cpb_env WIN_PS 30.0]; set cpb_sm [cpb_env SETUP_MARGIN_PS 10.0]
set cpb_scale [cpb_env SETUP_SCALE 2.0]; set cpb_max [cpb_env MAX_PS 40.0]; set cpb_cell [cpb_env CELL BUFx4_ASAP7_75t_R]
set cpb_step0 [cpb_env STEP_PS 10.0]; set cpb_rounds [cpb_env ROUNDS 4]; set cpb_tol [cpb_env TOL_PS 2.0]
set cpb_epc [cpb_env EPC 8]; set cpb_cut [cpb_env CUT auto]; set cpb_dry [cpb_env DRY 0]
# _GRT 0 (read-only trial on a routed copy with its SPEF only): no incremental GRT / legalisation / re-estimate
set cpb_grt [cpb_env GRT 1]
# ---- corners ----
# OpenSTA scenes (OpenROAD 26Q3: define_corners -> scenes, path queries take -scenes) or older corners (-corner)
set cpb_corners {}
if {[llength [info commands sta::scenes]]} {
  set cpb_cflag -scenes
  foreach c [sta::scenes] { if {[catch {lappend cpb_corners [get_name $c]}]} { lappend cpb_corners [sta::scene_property $c name] } }
} else { set cpb_cflag -corner; foreach c [sta::corners] { lappend cpb_corners [$c name] } }
set cpb_hc [cpb_env HOLD_CORNER ""]; set cpb_sc [cpb_env SETUP_CORNER ""]
if {$cpb_hc eq ""} { foreach c $cpb_corners { if {[regexp -nocase {^(bc|ff)$} $c]} { set cpb_hc $c } } }
if {$cpb_hc eq ""} { set cpb_hc [lindex $cpb_corners 0] }
if {$cpb_sc eq ""} { foreach c $cpb_corners { if {$c ne $cpb_hc} { set cpb_sc $c; break } } }
if {$cpb_sc eq ""} { set cpb_sc $cpb_hc }
puts "OT_CLK_PAIR_BAL corners [join $cpb_corners ,]: hold $cpb_hc, setup $cpb_sc"
# reg2reg only by default (_REG2REG 1): the pass balances register pairs; IO paths are the die model's business
set cpb_r2r [cpb_env REG2REG 1]
set cpb_ft {}; if {$cpb_r2r} { set cpb_ft [list -from [all_registers -clock_pins] -to [all_registers -data_pins]] }
proc cpb_paths {dly corner smax {epc 1} {cnt 200000}} {
  return [find_timing_paths -path_delay $dly $::cpb_cflag $corner {*}$::cpb_ft -group_path_count $cnt -endpoint_path_count $epc -slack_max $smax]
}
proc cpb_wns {dly corner} {
  set p [cpb_paths $dly $corner 1e30 1 1]; if {![llength $p]} { return 0.0 }; return [get_property [lindex $p 0] slack]
}
proc cpb_summary {tag} {
  global cpb_hc cpb_sc
  set h [cpb_paths min $cpb_hc 0]
  set wh [cpb_wns min $cpb_hc]; set ws [cpb_wns max $cpb_sc]
  puts [format "OT_CLK_PAIR_BAL %s: hold %s WNS %.2f ps, %d endpoints < 0; setup %s WNS %.2f ps" $tag $cpb_hc $wh [llength $h] $cpb_sc $ws]
  return [list $wh [llength $h] $ws]
}
# ---- clock tree walk (odb) ----
proc cpb_isclk {i} { regexp {^(BUF|INV|CKINV|CLKBUF|ICG)} [[$i getMaster] getName] }
proc cpb_iterm {pin} {
  # sta pin -> odb iterm (register / cell pins only; ports -> ""); db names keep the escapes (\[ \]) that sta full names drop
  if {[catch {set it [sta::sta_to_db_pin $pin]}] || $it eq "" || $it eq "NULL"} { return "" }
  if {![string match "*dbITerm*" $it]} { return "" }
  return $it
}
proc cpb_ckterm {inst} {
  foreach it [$inst getITerms] {
    set mt [$it getMTerm]
    if {[$mt getIoType] eq "INPUT" && ([$mt getSigType] eq "CLOCK" || [regexp {^(CLK|CK|clk)$} [$mt getName]])} { return $it }
  }
  return ""
}
proc cpb_inpin {inst} {
  # the clock input of a tree cell (ICG: its clock pin; buffer / inverter: the one signal input)
  set ck [cpb_ckterm $inst]; if {$ck ne ""} { return $ck }
  foreach it [$inst getITerms] { set mt [$it getMTerm]; if {[$mt getIoType] eq "INPUT" && [$mt getSigType] eq "SIGNAL"} { return $it } }
  return ""
}
# chain of tree cell names from the sink's driver up to the last cell under the clock source: {leaf_driver ... top}
proc cpb_chain {it} {
  if {[info exists ::cpb_cc([$it getId])]} { return $::cpb_cc([$it getId]) }
  set out {}; set cur $it; set guard 0
  while {[incr guard] < 256} {
    set net [$cur getNet]; if {$net eq "NULL" || [llength [$net getBTerms]]} break
    set drv ""; foreach t [$net getITerms] { if {[$t isOutputSignal]} { set drv [$t getInst]; break } }
    if {$drv eq "" || ![cpb_isclk $drv]} break
    lappend out [$drv getName]
    set cur [cpb_inpin $drv]; if {$cur eq ""} break
  }
  set ::cpb_cc([$it getId]) $out
  return $out
}
set cpb_dtaps {}; foreach i [$cpb_blk getInsts] { if {[regexp {^ot_dtap_[0-9]+$} [$i getName]]} { lappend cpb_dtaps [$i getName] } }
if {$cpb_cut eq "auto"} { set cpb_cut [expr {[llength $cpb_dtaps] ? "dtap" : "branch"}] }
puts "OT_CLK_PAIR_BAL cut $cpb_cut ([llength $cpb_dtaps] density taps)"
# path -> {launch_sink_iterm capture_sink_iterm}; "" side = port / unclocked (ROOT)
proc cpb_ends {pe} {
  set l ""; set c ""
  set sp [get_property $pe startpoint]
  if {[catch {set lt [cpb_iterm $sp]}]} { set lt "" }
  if {$lt ne ""} { set l [expr {[[$lt getMTerm] getIoType] eq "INPUT" && [cpb_ckterm [$lt getInst]] eq $lt ? $lt : [cpb_ckterm [$lt getInst]]}] }
  set ep [get_property $pe endpoint]
  if {[catch {set et [cpb_iterm $ep]}]} { set et "" }
  if {$et ne ""} { set c [cpb_ckterm [$et getInst]] }
  return [list $l $c]
}
# node of a sink: dtap cut = nearest ot_dtap ancestor; branch cut = deepest chosen node on its chain (or ROOT)
proc cpb_node {it} {
  if {$it eq ""} { return ROOT }
  set ch [cpb_chain $it]
  if {$::cpb_cut eq "dtap"} { foreach n $ch { if {[regexp {^ot_dtap_[0-9]+$} $n]} { return $n } }; return ROOT }
  set sk "@[[$it getInst] getName]"
  if {[info exists ::cpb_nodes($sk)]} { return $sk }
  foreach n $ch { if {[info exists ::cpb_nodes($n)]} { return $n } }
  return ROOT
}
# ---- 1. violators -> node set ----
set cpb_s0 [cpb_summary before]
set cpb_viol {}
foreach pe [cpb_paths min $cpb_hc 0 $cpb_epc] {
  lassign [cpb_ends $pe] l c
  lappend cpb_viol [list $l $c [get_property $pe slack]]
}
array unset cpb_nodes
if {$cpb_cut eq "dtap"} { foreach n $cpb_dtaps { set cpb_nodes($n) 1 } } else {
  foreach v $cpb_viol {
    lassign $v l c s
    if {$l eq "" || $c eq ""} continue
    set a [lreverse [cpb_chain $l]]; lappend a "@[[$l getInst] getName]"
    set b [lreverse [cpb_chain $c]]; lappend b "@[[$c getInst] getName]"
    set k 0; while {$k < [llength $a] && $k < [llength $b] && [lindex $a $k] eq [lindex $b $k]} { incr k }
    if {$k < [llength $a]} { set cpb_nodes([lindex $a $k]) 1 }
    if {$k < [llength $b]} { set cpb_nodes([lindex $b $k]) 1 }
  }
}
# parent node of every node (nearest chosen ancestor)
array unset cpb_par
foreach n [array names cpb_nodes] {
  if {[string index $n 0] eq "@"} { set it [cpb_ckterm [$cpb_blk findInst [string range $n 1 end]]]; set ch [cpb_chain $it]
  } else { set ch [lrange [cpb_chain [cpb_inpin [$cpb_blk findInst $n]]] 0 end] }
  set cpb_par($n) ROOT
  foreach a $ch { if {$a ne $n && [info exists cpb_nodes($a)]} { set cpb_par($n) $a; break } }
}
# ---- 2. constraints + solve ----
# edge list: {from to w}: phi(to) >= phi(from) + w
proc cpb_solve {edges} {
  global cpb_nodes cpb_max
  array set phi {ROOT 0.0}; foreach n [array names cpb_nodes] { set phi($n) 0.0 }
  set N [expr {[array size phi] + 1}]
  for {set it 0} {$it < $N} {incr it} {
    set ch 0
    foreach e $edges { lassign $e f t w; if {$phi($f) + $w > $phi($t) + 1e-6} { set phi($t) [expr {$phi($f) + $w}]; set ch 1 } }
    if {!$ch} break
  }
  set ok [expr {!$ch && $phi(ROOT) < 1e-6}]
  set mx 0.0; foreach n [array names phi] { if {$phi($n) > $mx} { set mx $phi($n) } }
  if {$mx > $cpb_max} { set ok 0 }
  return [list $ok [array get phi] $mx]
}
set cpb_resid {}; set cpb_hold {}
foreach pe [cpb_paths min $cpb_hc $cpb_win $cpb_epc] {
  lassign [cpb_ends $pe] l c; set s [get_property $pe slack]
  set L [cpb_node $l]; set C [cpb_node $c]
  if {$L eq $C} { if {$s < 0} { lappend cpb_resid [list same-node $L $s] }; continue }
  # violators need slack + shift >= margin; a path already meeting hold only has to keep slack + shift >= 0 (a margin
  # on near-zero paths in both directions would form spurious positive cycles)
  lappend cpb_hold [list $C $L [expr {$s < 0 ? $cpb_m - $s : -$s}] $s]
}
# pair conflicts: L->C needs phi(L)-phi(C) >= a and C->L needs phi(C)-phi(L) >= b with a + b > 0: no shift serves both.
# The violator side(s) (requirement > margin, i.e. slack < 0) go to RESIDUAL; a non-violating side stays as a guard.
array unset cpb_req
foreach h $cpb_hold { lassign $h C L w s; set k "$L|$C"; if {![info exists cpb_req($k)] || $w > $cpb_req($k)} { set cpb_req($k) $w } }
set cpb_drop {}
foreach k [array names cpb_req] {
  lassign [split $k |] L C
  if {[info exists cpb_req($C|$L)] && $cpb_req($k) + $cpb_req($C|$L) > 0 && $cpb_req($k) > $cpb_m} { lappend cpb_drop $k }
}
set cpb_e {}
foreach k [array names cpb_req] {
  lassign [split $k |] L C
  if {[lsearch -exact $cpb_drop $k] >= 0} { lappend cpb_resid [list bidir "$L->$C" [expr {$cpb_m - $cpb_req($k)}]]; continue }
  lappend cpb_e [list $C $L $cpb_req($k)]
}
foreach n [array names cpb_par] { lappend cpb_e [list $cpb_par($n) $n 0.0] }
set cpb_setup {}; set ok 0; set phil {}
set cpb_itmax [expr {[llength $cpb_e] + 16}]
for {set cpb_it 0} {$cpb_it < $cpb_itmax} {incr cpb_it} {
  lassign [cpb_solve [concat $cpb_e $cpb_setup]] ok phil mx
  if {!$ok} {
    # drop the largest remaining violator requirement (positive cycle / above the cap) into RESIDUAL
    set bi -1; set bw -1e9
    for {set i 0} {$i < [llength $cpb_e]} {incr i} { set w [lindex $cpb_e $i 2]; if {$w > $cpb_m && $w > $bw} { set bw $w; set bi $i } }
    if {$bi < 0} { puts "OT_CLK_PAIR_BAL infeasible without any violator requirement: no edit"; set phil {}; set ok 0; break }
    lassign [lindex $cpb_e $bi] C L w; lappend cpb_resid [list dropped "$L->$C" [expr {$cpb_m - $w}]]
    set cpb_e [lreplace $cpb_e $bi $bi]; continue
  }
  # setup constraints for every path whose setup slack could be reached by the solved shift
  set lim [expr {$cpb_sm + $cpb_scale * $mx}]
  set new 0; array unset cpb_sk; foreach e $cpb_setup { set cpb_sk([lindex $e 0]|[lindex $e 1]) [lindex $e 2] }
  foreach pe [cpb_paths max $cpb_sc $lim $cpb_epc] {
    lassign [cpb_ends $pe] l c; set s [get_property $pe slack]
    set L [cpb_node $l]; set C [cpb_node $c]; if {$L eq $C} continue
    # a pair may use only the setup slack above the margin; a pair already below it may not get worse (never asks
    # for a negative shift: the pass repairs hold, setup stays the flow's repair_timing business)
    set w [expr {-max(0.0, $s - $cpb_sm) / $cpb_scale}]
    if {![info exists cpb_sk($L|$C)] || $w > $cpb_sk($L|$C)} { set cpb_sk($L|$C) $w; incr new }
  }
  set cpb_setup {}; foreach k [array names cpb_sk] { lassign [split $k |] L C; lappend cpb_setup [list $L $C $cpb_sk($k)] }
  if {!$new} break
}
# only a converged, feasible solution is ever applied
if {!$ok} { puts "OT_CLK_PAIR_BAL no feasible solution after $cpb_it solves: no edit"; set phil {} }
array unset cpb_phi; array set cpb_phi $phil
set cpb_plan {}
foreach n [lsort [array names cpb_nodes]] {
  if {![info exists cpb_phi($n)]} continue
  set d [expr {$cpb_phi($n) - $cpb_phi($cpb_par($n))}]
  if {$d > $cpb_tol} { lappend cpb_plan [list $n $d] }
}
# predicted hold WNS over the solved constraints (violators only, excluding residuals)
set cpb_pw 1e9
foreach h $cpb_hold { lassign $h C L w s; if {$s >= 0 || ![info exists cpb_phi($L)] || ![info exists cpb_phi($C)]} continue
  set p [expr {$s + $cpb_phi($L) - $cpb_phi($C)}]; if {$p < $cpb_pw} { set cpb_pw $p } }
foreach r $cpb_resid { if {[lindex $r 2] < $cpb_pw} { set cpb_pw [lindex $r 2] } }
puts [format "OT_CLK_PAIR_BAL plan: %d nodes delayed (max shift %.1f ps, hold corner), %d hold pairs, %d setup pairs, predicted hold WNS %.2f ps, %d residual" \
        [llength $cpb_plan] [expr {[array size cpb_phi] ? [tcl::mathfunc::max 0 {*}[lmap {k v} [array get cpb_phi] {set v}]] : 0}] \
        [llength $cpb_hold] [llength $cpb_setup] $cpb_pw [llength $cpb_resid]]
foreach p $cpb_plan { puts [format "OT_CLK_PAIR_BAL node %s +%.1f ps (phi %.1f, parent %s)" [lindex $p 0] [lindex $p 1] $cpb_phi([lindex $p 0]) $cpb_par([lindex $p 0])] }
foreach r $cpb_resid { puts [format "OT_CLK_PAIR_BAL RESIDUAL %s %s slack %.2f ps" {*}$r] }
# ---- 3. insertion ----
proc cpb_pin {n} {
  if {[string index $n 0] eq "@"} { set it [cpb_ckterm [$::cpb_blk findInst [string range $n 1 end]]] } else { set it [cpb_inpin [$::cpb_blk findInst $n]] }
  return [list $it [sta::find_pin "[[$it getInst] getName]/[[$it getMTerm] getName]"]]
}
proc cpb_arr {n} { lassign [cpb_pin $n] it p; return [get_property $p arrival_min_rise] }
proc cpb_depth {n} { set d 0; while {$n ne "ROOT"} { set n $::cpb_par($n); incr d }; return $d }
if {!$cpb_dry && [llength $cpb_plan]} {
  set cpb_master [[ord::get_db] findMaster $cpb_cell]
  if {$cpb_master eq "NULL"} { error "OT_CLK_PAIR_BAL: no master $cpb_cell" }
  array unset cpb_a0; array unset cpb_tgt; array unset cpb_st; array unset cpb_used
  foreach n [array names cpb_phi] { if {$n ne "ROOT"} { set cpb_a0($n) [cpb_arr $n] } }
  foreach p $cpb_plan { lassign $p n d; set cpb_tgt($n) 1; set cpb_st($n) $cpb_step0; set cpb_used($n) 0 }
  set cpb_seq 0; set cpb_cells 0
  for {set r 1} {$r <= $cpb_rounds} {incr r} {
    # deficit of every planned node against a0 + phi relative to its parent's realised shift; top-down (a node waits while
    # any chosen ancestor still has a deficit)
    set todo {}; array unset cpb_def
    foreach n [array names cpb_tgt] {
      # phi is cumulative and so is the measured shift (a chosen ancestor's cells move this node too)
      set cpb_def($n) [expr {$cpb_phi($n) - ([cpb_arr $n] - $cpb_a0($n))}]
    }
    foreach n [lsort -command {apply {{a b} {expr {[cpb_depth $a] - [cpb_depth $b]}}}} [array names cpb_tgt]] {
      if {$cpb_def($n) <= $cpb_tol} continue
      set blocked 0; set a $cpb_par($n)
      while {$a ne "ROOT"} { if {[info exists cpb_def($a)] && $cpb_def($a) > $cpb_tol} { set blocked 1; break }; set a $cpb_par($a) }
      if {$blocked} continue
      set nb [expr {max(1, int(floor($cpb_def($n) / $cpb_st($n) + 0.5)))}]
      set cap [expr {int(ceil($cpb_phi($n) / 4.0)) + 1 - $cpb_used($n)}]
      set nb [expr {min($nb, $cap)}]; if {$nb < 1} continue
      lappend todo [list $n $nb [cpb_arr $n]]
    }
    if {![llength $todo]} break
    if {$cpb_grt} { global_route -start_incremental; detailed_placement }
    foreach t $todo {
      lassign $t n nb a
      for {set b 0} {$b < $nb} {incr b} {
        lassign [cpb_pin $n] it p
        set inst [$it getInst]; lassign [$inst getLocation] x y
        set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
        incr cpb_seq
        insert_buffer -buffer_cell $cpb_cell -load_pins [list $p] -location [list [expr {double($x)/$dbu}] [expr {double($y)/$dbu}]] \
          -buffer_name "clkpairbal_${cpb_seq}" -net_name "clknet_clkpairbal_${cpb_seq}"
        set nn [$it getNet]; if {$nn ne "NULL"} { $nn setSigType CLOCK }
        incr cpb_cells
      }
      set cpb_used($n) [expr {$cpb_used($n) + $nb}]
    }
    if {$cpb_grt} { detailed_placement; global_route -end_incremental; estimate_parasitics -global_routing }
    foreach t $todo { lassign $t n nb a; set st [expr {([cpb_arr $n] - $a) / double($nb)}]; set cpb_st($n) [expr {$st < 4.0 ? 4.0 : ($st > 30.0 ? 30.0 : $st)}] }
    puts "OT_CLK_PAIR_BAL round $r: [llength $todo] nodes, $cpb_cells cells so far"
  }
  foreach p $cpb_plan { set n [lindex $p 0]; puts [format "OT_CLK_PAIR_BAL realised %s shift %.1f ps (target %.1f, %d cells)" $n [expr {[cpb_arr $n] - $cpb_a0($n)}] $cpb_phi($n) $cpb_used($n)] }
  if {$cpb_grt} { check_placement -verbose }
  set cpb_s1 [cpb_summary after]
  puts [format "OT_CLK_PAIR_BAL done: %d cells; hold WNS %.2f -> %.2f ps (%d -> %d endpoints), setup WNS %.2f -> %.2f ps" \
          $cpb_cells [lindex $cpb_s0 0] [lindex $cpb_s1 0] [lindex $cpb_s0 1] [lindex $cpb_s1 1] [lindex $cpb_s0 2] [lindex $cpb_s1 2]]
} else { puts "OT_CLK_PAIR_BAL done: no edit ([expr {$cpb_dry ? "DRY" : "empty plan"}])" }
}
