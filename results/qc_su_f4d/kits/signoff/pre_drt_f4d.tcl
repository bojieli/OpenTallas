# QC-SU-F4D PRE_DETAIL_ROUTE_TCL (sign-off kit): the tree-net-only M5/M6 guide rewrite must reach DRT through the ODB
# (ORFS detail_route.tcl uses the dbGuides in 5_1_grt.odb, not route.guide -- F4C finding).  Steps: write the final GRT
# guides (after hold repair) -> guide_tree_m56.py v2 (tree nets ot_ms_*_n only: H->M6, V->M5, pin GCell stacks M1-M6;
# all other nets byte-identical, asserts 0 non-tree M6) -> read_guides -> census (FAIL on any non-tree M6 guide) ->
# routing layers M2-M6 so DRT may use the M6 tree guides.  No clock cell / net edit (12.8): guides only.
set g0 $::env(RESULTS_DIR)/route_grt_final.guide
set g1 $::env(RESULTS_DIR)/route_tree_m56.guide
write_guides $g0
exec python3 -I /work/guide_tree_m56.py $g0 $g1 /work/guide_m56.json >@ stdout 2>@ stderr
read_guides $g1
set c [dict create]
foreach n [[ord::get_db_block] getNets] {
  set t [expr {[string match ot_ms_*_n [$n getName]] ? "tree" : "other"}]
  foreach g [$n getGuides] { dict incr c "$t:[[$g getLayer] getName]" }
}
puts "OT_TREE_GUIDE loaded $g1 :: $c"
if {[dict exists $c other:M6]} { error "OT_TREE_GUIDE: non-tree net has an M6 guide" }
if {![dict exists $c tree:M6]} { error "OT_TREE_GUIDE: no tree M6 guide after read_guides" }
# M6 keep-out for every other net: DRT may leave a guide to fix DRCs, and with M6 in the routing range the probe showed
# 225 non-tree nets with 583.9 um of off-guide M6 (rp1 F4C DB).  So M6 is obstructed wherever no tree-net M6 guide
# exists (row runs of free GCells); post_drt_f4d.tcl deletes these obstructions before fill/RCX/abstract.
set blk [ord::get_db_block]; set tech [[ord::get_db] getTech]; set m6 [$tech findLayer M6]
set die [$blk getDieArea]; set x0 [$die xMin]; set y0 [$die yMin]; set x1 [$die xMax]; set y1 [$die yMax]
set gs [expr {[$blk getDbUnitsPerMicron] * 1.08}]
set nx [expr {int(ceil(double($x1 - $x0) / $gs))}]; set ny [expr {int(ceil(double($y1 - $y0) / $gs))}]
array set occ {}
foreach n [$blk getNets] {
  if {![string match ot_ms_*_n [$n getName]]} continue
  foreach g [$n getGuides] {
    if {[[$g getLayer] getName] ne "M6"} continue
    set b [$g getBox]
    for {set i [expr {int(([$b xMin] - $x0) / $gs)}]} {$i <= int(([$b xMax] - 1 - $x0) / $gs)} {incr i} {
      for {set j [expr {int(([$b yMin] - $y0) / $gs)}]} {$j <= int(([$b yMax] - 1 - $y0) / $gs)} {incr j} { set occ($i,$j) 1 } }
  }
}
set nob 0
for {set j 0} {$j < $ny} {incr j} {
  set i 0
  while {$i < $nx} {
    if {[info exists occ($i,$j)]} { incr i; continue }
    set s $i; while {$i < $nx && ![info exists occ($i,$j)]} { incr i }
    set ob [odb::dbObstruction_create $blk $m6 [expr {int($x0 + $s * $gs)}] [expr {int($y0 + $j * $gs)}] \
      [expr {min($x1, int($x0 + $i * $gs))}] [expr {min($y1, int($y0 + ($j + 1) * $gs))}]]
    incr nob
  }
}
puts "OT_TREE_M6_KEEPOUT obstructions $nob free_of [expr {$nx * $ny}] gcells, tree M6 gcells [array size occ]"
set_routing_layers -signal M2-M6
