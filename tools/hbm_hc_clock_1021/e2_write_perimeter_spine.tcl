# E2 remaining write-root structural model. Preserve the actual-qualified w1
# implementation byte-for-byte through its existing wrapper; repair w2 and ALL
# w3 real sinks together. This is a physical distribution change, not a clock
# domain/reference/edge change. No dummy loads, register additions or SDC edits.
source /src/tools/hbm_hc_clock_1021/e2_perimeter_spine.tcl
rename ot_sp_sym_build ot_e2w_qualified_w1_build
proc ot_sp_sym_build {ids lins rx ry} {
  set port [uplevel 1 {set port}]
  if {$port ni {clk_w2 clk_w3}} {
    return [ot_e2w_qualified_w1_build $ids $lins $rx $ry]
  }
  if {[dict size $lins]} {error "E2_WRITE: no actual hard insertion target may be removed"}
  set u $::ot_sp_dbu
  set left [expr {43.2*$u}];set right [expr {217.944*$u}]
  set far_x [expr {250.0*$u}]
  set column 0;set hard 0
  foreach inst [$::ot_sp_blk getInsts] {
    set master [$inst getMaster]
    if {![$master isBlock]} continue
    incr hard
    if {[$master getName] ne "ot_sram_1r1w_1024x256_m2_r2c2"} continue
    set b [$inst getBBox]
    if {abs([$b xMin]-$left)>$u*0.001 || abs([$b xMax]-$right)>$u*0.001} {
      error "E2_WRITE: immutable measured SRAM geometry differs"
    }
    incr column
  }
  if {$column!=8 || $hard!=20} {error "E2_WRITE: expected8 column macros and20 real hard children"}
  set groups [dict create west {} east {} far {}]
  set counts [dict create west 0 east 0 far 0]
  foreach id $ids {
    set side ""
    foreach pin [dict get $::ot_sp_members $id] {
      if {[[[$pin getInst] getMaster] isBlock] || [[$pin getMTerm] getName] ne "CLK"} {
        error "E2_WRITE: unexpected non-standard-cell CLK sink"
      }
      lassign [$pin getAvgXY] ok x y
      if {!$ok} {error "E2_WRITE: real pin shape absent"}
      set s [expr {$x<$left ? "west" : $x>$far_x ? "far" : $x>$right ? "east" : "inside"}]
      if {$s eq "inside" || ($side ne "" && $s ne $side)} {
        error "E2_WRITE: a real leaf crosses its measured physical island"
      }
      set side $s
      dict incr counts $s
    }
    dict lappend groups $side $id
  }
  set expected_far [expr {$port eq "clk_w3" ? 17 : 0}]
  set expected_leaves [expr {$port eq "clk_w3" ? 134 : 130}]
  if {[dict get $counts west]!=240 || [dict get $counts east]!=795
      || [dict get $counts far]!=$expected_far || [llength $ids]!=$expected_leaves} {
    error "E2_WRITE: ALL actual $port census differs: $counts leaves=[llength $ids]"
  }
  # w3's17 real flag-landing clock pins near(524,710) are a third genuine
  # subtree. They remain in the SAME root and in the ALL1052 measurement.
  set trees {};set heights {};set height 0
  foreach name {west east far} {
    set members [dict get $groups $name]
    if {[llength $members]} {lappend trees [ot_sp_split_bb $members]}
  }
  foreach t $trees {
    set h [ot_e2_equal_depth $t];lappend heights $h
    set height [expr {max($height,$h)}]
  }
  set balanced {}
  foreach t $trees h $heights {
    for {set i $h} {$i<$height} {incr i} {set t [ot_e2_unary $t]}
    lappend balanced $t
  }
  set top "N[incr ::ot_sp_nn]"
  dict set ::ot_sp_pos $top [list $rx $ry]
  dict set ::ot_sp_cnt $top [expr {1035+$expected_far}]
  dict set ::ot_sp_kids $top $balanced
  set ::ot_sp_est_t [dict create]
  ot_sp_est $top [ot_sp_env OT_SPINE_SYM_BUF_PS 45.0] \
    [expr {[ot_sp_env OT_SPINE_SYM_WIRE_PS_UM 0.43]/double($u)}] [ot_sp_env OT_SPINE_SYM_BUF_PS 45.0]
  dict set ::ot_e2_write_applied $port 1
  puts "E2_WRITE same_root=$port ALL_sinks=[expr {1035+$expected_far}] islands=$counts leaves=[llength $ids] equal_subtree_depth=$height hard_children=$hard"
  return $top
}
