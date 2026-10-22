# HBM-ELEM13/HC 10-21: E2 regional (per-island) equal-depth clock subtrees for
# the remaining glue-only roots. Root cause (ROOT-reviewed baseline replay
# 3b4b14119, EP5 unit 3492160, reproduced d2 platform TT 130.248): the d0..d3
# and h0..h3 row-assembler roots each have ~110 real CLK sinks WEST of the
# 8-SRAM column (x < 43.2) and ~400 EAST of it (x > 217.944); the default
# symmetric build splits one bounding box across the column and its collapse
# step leaves unequal buffer depth (within-bin spread up to 138 ps at platform
# RC). Same mechanism the actual gate already fixed for w1/w2/w3 (17.7/30.1/
# 32.6 TT): one local subtree per physical island, every island padded to the
# same buffer depth, fork at the unchanged root pin. No dummy loads, no added
# registers, no SDC/RC/Lib/phase change, same root/clock/edges.
# Run AFTER e2_write_perimeter_spine.tcl. Roots: $::ot_e2_island_roots.
if {[info procs ot_sp_sym_build] eq "" || [info procs ot_e2i_prev_build] ne ""} {
  error "E2_ISLAND: expected one fresh write-perimeter spine build"
}
if {[info procs ot_e2_equal_depth] eq "" || [info procs ot_e2_unary] eq ""} {
  error "E2_ISLAND: e2_perimeter_spine.tcl helpers absent"
}
if {![info exists ::ot_e2_island_roots]} {error "E2_ISLAND: ::ot_e2_island_roots not set by the kit"}
rename ot_sp_sym_build ot_e2i_prev_build
proc ot_sp_sym_build {ids lins rx ry} {
  set port [uplevel 1 {set port}]
  if {$port ni $::ot_e2_island_roots || $port in {clk_w1 clk_w2 clk_w3}} {
    return [ot_e2i_prev_build $ids $lins $rx $ry]
  }
  if {[dict size $lins]} {
    puts "E2_ISLAND skip=$port hard_insertion_leaves=[dict size $lins] (unchanged original build)"
    return [ot_e2i_prev_build $ids $lins $rx $ry]
  }
  set u $::ot_sp_dbu
  set left [expr {43.2*$u}];set right [expr {217.944*$u}]
  set column 0;set hard 0
  foreach inst [$::ot_sp_blk getInsts] {
    set master [$inst getMaster]
    if {![$master isBlock]} continue
    incr hard
    if {[$master getName] ne "ot_sram_1r1w_1024x256_m2_r2c2"} continue
    set b [$inst getBBox]
    if {abs([$b xMin]-$left)>$u*0.001 || abs([$b xMax]-$right)>$u*0.001} {
      error "E2_ISLAND: measured SRAM column geometry differs"
    }
    incr column
  }
  if {$column!=8 || $hard!=20} {error "E2_ISLAND: expected 8 column macros and 20 hard children"}
  set groups [dict create west {} east {}]
  set counts [dict create west 0 east 0]
  foreach id $ids {
    set side ""
    foreach pin [dict get $::ot_sp_members $id] {
      if {[[[$pin getInst] getMaster] isBlock]} {error "E2_ISLAND: hard sink on glue root $port"}
      lassign [$pin getAvgXY] ok x y
      if {!$ok} {error "E2_ISLAND: real pin shape absent"}
      set s [expr {$x<$left ? "west" : $x>$right ? "east" : "inside"}]
      if {$s eq "inside" || ($side ne "" && $s ne $side)} {
        error "E2_ISLAND: a leaf of $port crosses the SRAM column"
      }
      set side $s
      dict incr counts $s
    }
    dict lappend groups $side $id
  }
  set trees {};set heights {};set height 0
  foreach name {west east} {
    set members [dict get $groups $name]
    if {![llength $members]} continue
    set t [ot_sp_split_bb $members]
    set h [ot_e2_equal_depth $t];lappend trees $t;lappend heights $h
    set height [expr {max($height,$h)}]
  }
  set balanced {}
  foreach t $trees h $heights {
    for {set i $h} {$i<$height} {incr i} {set t [ot_e2_unary $t]}
    lappend balanced $t
  }
  set total [expr {[dict get $counts west]+[dict get $counts east]}]
  set top "N[incr ::ot_sp_nn]"
  dict set ::ot_sp_pos $top [list $rx $ry]
  dict set ::ot_sp_cnt $top $total
  dict set ::ot_sp_kids $top $balanced
  set ::ot_sp_est_t [dict create]
  ot_sp_est $top [ot_sp_env OT_SPINE_SYM_BUF_PS 45.0] \
    [expr {[ot_sp_env OT_SPINE_SYM_WIRE_PS_UM 0.43]/double($u)}] [ot_sp_env OT_SPINE_SYM_BUF_PS 45.0]
  dict set ::ot_e2_island_applied $port 1
  puts "E2_ISLAND same_root=$port ALL_sinks=$total islands=$counts leaves=[llength $ids] equal_subtree_depth=$height hard_children=$hard"
  return $top
}
