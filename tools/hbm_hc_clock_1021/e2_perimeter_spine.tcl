# E2 only, source-bound successor to b0841730b/rw10sp clk_w1 TT133.6 FAIL.
# Same source clock, real1035 CLK sinks, no added data/reset edges or dummy loads.
# Run AFTER clock_spine_child_ins.tcl, under the unchanged hybrid checker.
if {[info procs ot_sp_sym_build] eq "" || [info procs ot_e2_original_sym_build] ne ""} {
  error "E2_PERIMETER: expected one fresh original symmetric spine source"
}
rename ot_sp_sym_build ot_e2_original_sym_build

# Each unary clock-buffer node serves a genuine downstream subtree. It adds no
# synthetic load and no register; equal depth tracks across TT/FF and wire RC.
proc ot_e2_unary {child} {
  set n "N[incr ::ot_sp_nn]"
  dict set ::ot_sp_pos $n [dict get $::ot_sp_pos $child]
  dict set ::ot_sp_cnt $n [dict get $::ot_sp_cnt $child]
  dict set ::ot_sp_kids $n [list $child]
  return $n
}
proc ot_e2_equal_depth {n} {
  if {![dict exists $::ot_sp_kids $n]} {return 0}
  set children [dict get $::ot_sp_kids $n]
  set heights {};set high 0
  foreach k $children {
    set h [ot_e2_equal_depth $k];lappend heights $h
    set high [expr {max($high,$h)}]
  }
  set out {}
  foreach k $children h $heights {
    for {set i $h} {$i<$high} {incr i} {set k [ot_e2_unary $k]}
    lappend out $k
  }
  dict set ::ot_sp_kids $n $out
  return [expr {$high+1}]
}
proc ot_sp_sym_build {ids lins rx ry} {
  set source_port [uplevel 1 {set port}]
  if {$source_port ne "clk_w1"} {
    return [ot_e2_original_sym_build $ids $lins $rx $ry]
  }
  if {[dict size $lins]} {error "E2_PERIMETER: w1 must remain glue-only, no hard insertion target removed"}
  # The actual immutable3_place model has one contiguous8-SRAM column, with
  # 240 real clock pins west and795 east. Check the physical premise again.
  set u $::ot_sp_dbu;set left [expr {43.2*$u}];set right [expr {217.944*$u}]
  set column 0;set hard 0
  foreach inst [$::ot_sp_blk getInsts] {
    set master [$inst getMaster]
    if {![$master isBlock]} continue
    incr hard
    if {[$master getName] ne "ot_sram_1r1w_1024x256_m2_r2c2"} continue
    set b [$inst getBBox]
    if {abs([$b xMin]-$left)>$u*0.001 || abs([$b xMax]-$right)>$u*0.001} {
      error "E2_PERIMETER: actual SRAM column geometry differs from measured source"
    }
    incr column
  }
  if {$column!=8 || $hard!=20} {error "E2_PERIMETER: expected8 SRAM column macros and20 unchanged hard children"}
  set west {};set east {};set nw 0;set ne 0
  foreach id $ids {
    set side ""
    foreach pin [dict get $::ot_sp_members $id] {
      if {[[[$pin getInst] getMaster] isBlock] || [[$pin getMTerm] getName] ne "CLK"} {
        error "E2_PERIMETER: unexpected non-standard-cell CLK sink"
      }
      lassign [$pin getAvgXY] ok x y
      if {!$ok} {error "E2_PERIMETER: actual clock-pin shape absent"}
      set s [expr {$x<$left ? "west" : $x>$right ? "east" : "inside"}]
      if {$s eq "inside" || ($side ne "" && $s ne $side)} {
        error "E2_PERIMETER: a real leaf crosses the measured SRAM obstacle"
      }
      set side $s
      if {$s eq "west"} {incr nw} else {incr ne}
    }
    if {$side eq "west"} {lappend west $id} else {lappend east $id}
  }
  if {$nw!=240 || $ne!=795 || [llength $ids]!=132} {
    error "E2_PERIMETER: ALL actual w1 sinks/leaf partition differs from model: west=$nw east=$ne leaves=[llength $ids]"
  }
  # Independent perimeter subtrees avoid placing their shared bbox centre in
  # the SRAM. No collapse: every real sink path gets the same buffer depth.
  set w [ot_sp_split_bb $west];set e [ot_sp_split_bb $east]
  set wh [ot_e2_equal_depth $w];set eh [ot_e2_equal_depth $e]
  set height [expr {max($wh,$eh)}]
  for {set i $wh} {$i<$height} {incr i} {set w [ot_e2_unary $w]}
  for {set i $eh} {$i<$height} {incr i} {set e [ot_e2_unary $e]}
  # The common fork stays below the obstacle at the unchanged root pin. The
  # original macro-aware wire emitter reaches each perimeter without making
  # a cross-column branch above the SRAM column.
  set top "N[incr ::ot_sp_nn]"
  dict set ::ot_sp_pos $top [list $rx $ry]
  dict set ::ot_sp_cnt $top [expr {$nw+$ne}]
  dict set ::ot_sp_kids $top [list $w $e]
  set ::ot_sp_est_t [dict create]
  ot_sp_est $top [ot_sp_env OT_SPINE_SYM_BUF_PS 45.0] \
    [expr {[ot_sp_env OT_SPINE_SYM_WIRE_PS_UM 0.43]/double($u)}] [ot_sp_env OT_SPINE_SYM_BUF_PS 45.0]
  set ::ot_e2_perimeter_applied 1
  puts "E2_PERIMETER same_root=$source_port ALL_sinks=[expr {$nw+$ne}] west=$nw east=$ne leaves=[llength $ids] equal_subtree_depth=$height hard_children=$hard"
  return $top
}
