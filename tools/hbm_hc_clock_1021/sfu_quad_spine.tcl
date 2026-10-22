# HBMc/HC-SFU 10-21: planned equal-depth quadrant spine for the SFU core (ot_hgi_sfu_core_split3l) glue root clk,
# beneath the UNCHANGED hybrid entry/root checks (clock_entries.tcl wrapper, OT_HYBRID CLOCK_RULE). Kit pre_cts_extra.
#
# Cause (PD-AUDIT C2; measured on the k11a mapped netlist ot-epyc7 hbm_sfucore_k11a-20261021-205621 1_2_yosys.raw.v,
# same clock structure as k12): ONE root clk drives 18,243 flops + 256 ot_hgi_sfu_scalar_byte cells (2,048 flops) =
# ~20.3k sinks spread over the whole 1,900.8 x 1,900.8 um outline: VM bridge address pipes 6,144, operand store
# 4,612 + 2,048, rotate copies 4,096, per-lane arithmetic control 1,012 (16 perimeter lanes), fault tree / drain.
# k9y measured 13,529 clk flops over 1,896 um with one TritonCTS tree.  One sink-driven tree over ~1.9 mm is not a
# regional clock (owner clock rule: local trees per region, <=80 ps spread TT+FF).
# Fix: the common planned spine (physical/common_flow/clock_spine.tcl, OT_SPINE_SYM=1) owns clk:
#   * leaves = OT_SPINE_BIN um bins of <= OT_SPINE_LEAF_N sinks;
#   * the leaves are split into FOUR quadrants at the core centre (each quadrant <= ~950 um, guard
#     OT_SFU_QSPAN_MAX um); each quadrant is one regional bounding-box bisection subtree;
#   * every subtree is padded with unary buffer stages to ONE depth (all leaves at the same buffer depth, no
#     collapse step), the four subtrees join at a fork at the core centre, the fork is fed from the clk port;
#   * every edge is repeated every OT_SPINE_SEG um (<= 405 um registered-hop reach is not needed: clock only);
#   * leaves are then padded to equal MEASURED arrival (clock_spine.tcl OT_SPINE_ITERS / OT_SPINE_TOL_PS).
# Other roots (clk_pw/clk_pe/clk_st/clk_lg/clk_map) keep TritonCTS (OT_SPINE_CTS_REST=1) exactly as in k12.
# Same root port/clock/edges/RTL/SDC/Lib; buffers only; no dummy loads; zero cycles.
if {[info procs ot_ce_cts_orig] eq "" || [info procs ot_spine_cts_orig] ne ""} {error "SFU_SPINE: expected a fresh hybrid CTS wrapper"}
rename clock_tree_synthesis ot_sfu_hybrid_cts
rename ot_ce_cts_orig clock_tree_synthesis
source /src/physical/common_flow/clock_spine.tcl
if {[info procs ot_sp_sym_build] eq "" || [info procs ot_sfu_prev_build] ne ""} {error "SFU_SPINE: expected one fresh symmetric spine build"}
rename ot_sp_sym_build ot_sfu_prev_build

proc ot_sfu_unary {child} {
  set n "N[incr ::ot_sp_nn]"
  dict set ::ot_sp_pos $n [dict get $::ot_sp_pos $child]
  dict set ::ot_sp_cnt $n [dict get $::ot_sp_cnt $child]
  dict set ::ot_sp_kids $n [list $child]
  return $n
}
# pad every node's children to one height (unary stages) so every leaf sits at the same buffer depth
proc ot_sfu_depth {n} {
  if {![dict exists $::ot_sp_kids $n]} {return 0}
  set heights {};set high 0;set kids [dict get $::ot_sp_kids $n]
  foreach k $kids {set h [ot_sfu_depth $k];lappend heights $h;set high [expr {max($high,$h)}]}
  set out {}
  foreach k $kids h $heights {
    for {set i $h} {$i<$high} {incr i} {set k [ot_sfu_unary $k]}
    lappend out $k
  }
  dict set ::ot_sp_kids $n $out
  return [expr {$high+1}]
}
proc ot_sp_sym_build {ids lins rx ry} {
  set port [uplevel 1 {set port}]
  if {$port ne "clk"} {return [ot_sfu_prev_build $ids $lins $rx $ry]}
  set u $::ot_sp_dbu
  set qmax [expr {[ot_sp_env OT_SFU_QSPAN_MAX 1000] * $u}]
  # quadrant split at the CORE centre (not the leaf centroid): fixed, symmetric regions of the outline
  set cx [expr {($::ot_sp_cx0+$::ot_sp_cx1)/2}];set cy [expr {($::ot_sp_cy0+$::ot_sp_cy1)/2}]
  set total 0;foreach id $ids {incr total [dict get $::ot_sp_cnt $id]}
  set groups [dict create]
  foreach id $ids {
    lassign [dict get $::ot_sp_pos $id] x y
    dict lappend groups "[expr {$y<$cy?"S":"N"}][expr {$x<$cx?"W":"E"}]" $id
  }
  set trees {};set heights {};set height 0;set qc {}
  foreach q [lsort [dict keys $groups]] {
    set m [dict get $groups $q]
    set xs {};set ys {}
    foreach id $m {lassign [dict get $::ot_sp_pos $id] x y;lappend xs $x;lappend ys $y}
    set sx [expr {[tcl::mathfunc::max {*}$xs]-[tcl::mathfunc::min {*}$xs]}]
    set sy [expr {[tcl::mathfunc::max {*}$ys]-[tcl::mathfunc::min {*}$ys]}]
    if {$sx > $qmax || $sy > $qmax} {error "SFU_SPINE: quadrant $q leaves span [expr {$sx/$u}]x[expr {$sy/$u}] um > OT_SFU_QSPAN_MAX"}
    set t [ot_sp_split_bb $m];set h [ot_sfu_depth $t]
    lappend trees $t;lappend heights $h;set height [expr {max($height,$h)}]
    set c 0;foreach id $m {incr c [dict get $::ot_sp_cnt $id]}
    lappend qc "$q=$c/[llength $m]L/[format %.0fx%.0f [expr {$sx/double($u)}] [expr {$sy/double($u)}]]um/h$h"
  }
  set kids {}
  foreach t $trees h $heights {for {set i $h} {$i<$height} {incr i} {set t [ot_sfu_unary $t]};lappend kids $t}
  set fork "N[incr ::ot_sp_nn]"
  dict set ::ot_sp_pos $fork [ot_sp_free [expr {int($cx)}] [expr {int($cy)}]]
  dict set ::ot_sp_cnt $fork $total
  dict set ::ot_sp_kids $fork $kids
  incr height
  set top "N[incr ::ot_sp_nn]"
  dict set ::ot_sp_pos $top [list $rx $ry]
  dict set ::ot_sp_cnt $top $total
  dict set ::ot_sp_kids $top [list $fork]
  set ::ot_sp_est_t [dict create]
  ot_sp_est $top [ot_sp_env OT_SPINE_SYM_BUF_PS 45.0] \
    [expr {[ot_sp_env OT_SPINE_SYM_WIRE_PS_UM 0.43]/double($u)}] [ot_sp_env OT_SPINE_SYM_BUF_PS 45.0]
  set ::ot_sfu_applied 1
  puts "SFU_SPINE port=$port leaves=[llength $ids] sinks=$total equal_depth=$height regions=[llength $trees] fork=[format %.1f,%.1f [expr {$cx/double($u)}] [expr {$cy/double($u)}]] $qc"
  return $top
}

rename clock_tree_synthesis ot_ce_cts_orig
rename ot_sfu_hybrid_cts clock_tree_synthesis
puts "SFU_SPINE: quad regional spine for clk beneath unchanged hybrid root/entry checks"
