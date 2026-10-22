# HBM-ELEM13/HC-QHUB 10-21: planned equal-depth clock spine for the HC quarter hub glue root clk.
# Cause (C6r actual gate ot-agidock128 hbm_hcq_hub_c6r-20261021-143819, read-only CTS replay reproduced 89.3 ps,
# per-pin dump scratch/hbm-elem13-hc/c6rpos): all 14,990 clk sinks sit in the 345.6 um centre band
# (194.4..540.0); every boundary pin flop has the SAME 15-buffer depth, but TritonCTS's H-tree level-7 taps sit
# on a fixed grid while its 32-sink / 95 um leaf clusters at the band edge hang far off the tap: the last hop
# clkbuf_7_127 (463,512) -> clkbuf_leaf_492 (539,494) costs 113 ps versus 29 ps for clkbuf_7_118 -> leaf_424
# (380,522). NE-corner leaves arrive 735..750 ps, N-centre leaves 660 ps: 89.3 ps boundary spread.
# Fix: the common planned spine (physical/common_flow/clock_spine.tcl, OT_SPINE_SYM=1) owns clk: small leaves
# (OT_SPINE_BIN/LEAF_N), a bounding-box bisection tree whose nodes sit at the centre of their leaves' box,
# EVERY leaf at the same buffer depth (no collapse step), repeated edges, measured-arrival leaf padding.
#   ::ot_qh_mode single : one region (the band is 345.6 um < 600 um), one equal-depth subtree.          (MAIN)
#   ::ot_qh_mode quad   : four regional quadrant subtrees of the band, padded to one depth, joined at a
#                         fork at the band centre so the four fork->quadrant edges are the same length. (FALLBACK)
# Same root port/clock/edges/RTL/SDC/RC/Lib; buffers only; no dummy loads; zero cycles.
if {[info procs ot_sp_sym_build] eq "" || [info procs ot_qh_prev_build] ne ""} {
  error "QHUB_SPINE: expected one fresh symmetric spine build"
}
if {![info exists ::ot_qh_mode] || $::ot_qh_mode ni {single quad}} {error "QHUB_SPINE: ::ot_qh_mode must be single|quad"}
rename ot_sp_sym_build ot_qh_prev_build
proc ot_qh_unary {child} {
  set n "N[incr ::ot_sp_nn]"
  dict set ::ot_sp_pos $n [dict get $::ot_sp_pos $child]
  dict set ::ot_sp_cnt $n [dict get $::ot_sp_cnt $child]
  dict set ::ot_sp_kids $n [list $child]
  return $n
}
proc ot_qh_depth {n} {
  if {![dict exists $::ot_sp_kids $n]} {return 0}
  set heights {};set high 0;set kids [dict get $::ot_sp_kids $n]
  foreach k $kids {set h [ot_qh_depth $k];lappend heights $h;set high [expr {max($high,$h)}]}
  set out {}
  foreach k $kids h $heights {
    for {set i $h} {$i<$high} {incr i} {set k [ot_qh_unary $k]}
    lappend out $k
  }
  dict set ::ot_sp_kids $n $out
  return [expr {$high+1}]
}
proc ot_sp_sym_build {ids lins rx ry} {
  set port [uplevel 1 {set port}]
  if {$port ne "clk"} {return [ot_qh_prev_build $ids $lins $rx $ry]}
  set u $::ot_sp_dbu
  set xs {};set ys {}
  foreach id $ids {lassign [dict get $::ot_sp_pos $id] x y;lappend xs $x;lappend ys $y}
  set x0 [tcl::mathfunc::min {*}$xs];set x1 [tcl::mathfunc::max {*}$xs]
  set y0 [tcl::mathfunc::min {*}$ys];set y1 [tcl::mathfunc::max {*}$ys]
  if {$x1-$x0 > 600*$u || $y1-$y0 > 600*$u} {error "QHUB_SPINE: clk leaves span more than one 600 um region"}
  set cx [expr {($x0+$x1)/2}];set cy [expr {($y0+$y1)/2}]
  set total 0;foreach id $ids {incr total [dict get $::ot_sp_cnt $id]}
  if {$::ot_qh_mode eq "single"} {
    set sub [ot_sp_split_bb $ids]
    set height [ot_qh_depth $sub]
    set kids [list $sub]
    set info "region=1 span=[format %.1fx%.1f [expr {($x1-$x0)/double($u)}] [expr {($y1-$y0)/double($u)}]]"
  } else {
    set groups [dict create]
    foreach id $ids {
      lassign [dict get $::ot_sp_pos $id] x y
      dict lappend groups "[expr {$x<$cx?"W":"E"}][expr {$y<$cy?"S":"N"}]" $id
    }
    set trees {};set heights {};set height 0;set qc {}
    foreach q [lsort [dict keys $groups]] {
      set m [dict get $groups $q]
      set t [ot_sp_split_bb $m];set h [ot_qh_depth $t]
      lappend trees $t;lappend heights $h;set height [expr {max($height,$h)}]
      set c 0;foreach id $m {incr c [dict get $::ot_sp_cnt $id]};lappend qc $q=$c
    }
    set kids {}
    foreach t $trees h $heights {for {set i $h} {$i<$height} {incr i} {set t [ot_qh_unary $t]};lappend kids $t}
    set fork "N[incr ::ot_sp_nn]"
    dict set ::ot_sp_pos $fork [ot_sp_free [expr {int($cx)}] [expr {int($cy)}]]
    dict set ::ot_sp_cnt $fork $total
    dict set ::ot_sp_kids $fork $kids
    incr height
    set kids [list $fork]
    set info "regions=[llength $trees] sinks=$qc fork=[format %.1f,%.1f [expr {$cx/double($u)}] [expr {$cy/double($u)}]]"
  }
  set top "N[incr ::ot_sp_nn]"
  dict set ::ot_sp_pos $top [list $rx $ry]
  dict set ::ot_sp_cnt $top $total
  dict set ::ot_sp_kids $top $kids
  set ::ot_sp_est_t [dict create]
  ot_sp_est $top [ot_sp_env OT_SPINE_SYM_BUF_PS 45.0] \
    [expr {[ot_sp_env OT_SPINE_SYM_WIRE_PS_UM 0.43]/double($u)}] [ot_sp_env OT_SPINE_SYM_BUF_PS 45.0]
  set ::ot_qh_applied 1
  puts "QHUB_SPINE mode=$::ot_qh_mode port=$port leaves=[llength $ids] sinks=$total equal_depth=$height $info"
  return $top
}
