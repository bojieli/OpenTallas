# GENERATED-COPY of physical/die_plan/qwen_kvsys/cores/harden/core_grid_taps.tcl (KV-CORE-LAT-REST 2026-10-26).
# OWNER 10-26 / METHODOLOGY 12.3: one common clock latency (KV 250 TT / 202.5 FF) at every hard-core clock pin, no early
# taps.  Cores whose clock port sits at a corner/face of a large outline (qkd_kvs_pc ck at (2.3, 0.1) of 397x363:
# TritonCTS path depth 9-11, avg sink wire 721 um) build one deep generic tree.  Structural fix, same pins:
# PRE_CTS, the outline is cut into an OT_GRID_TAPS = "NX NY" grid of equal regions; every register / macro clock pin on
# a clock-port net moves to one regional tap buffer (OT_GRID_TAP_CELL) placed at the centroid of that region's sinks.
# TritonCTS then builds one SHALLOW tree per tap (equal region size -> equal depth) and the balanced top tree from the
# port to the taps (CTS_ARGS -balance_levels), so the port->tap trunk is shared and every tap tree is short.
# No padding to the worst tap; balance comes from equal regions.  Same mechanism as head_lane_taps.tcl (key = region).
# Writes $RESULTS_DIR/ot_grid_taps.json {tap: {region, sinks, x, y}}.
uplevel #0 {
lassign [expr {[info exists ::env(OT_GRID_TAPS)] ? $::env(OT_GRID_TAPS) : "2 2"}] gt_nx gt_ny
set gt_cell [expr {[info exists ::env(OT_GRID_TAP_CELL)] ? $::env(OT_GRID_TAP_CELL) : "BUFx12f_ASAP7_75t_R"}]
set gt_blk [ord::get_db_block]
set gt_u [[ord::get_db_tech] getDbUnitsPerMicron]
set gt_master [[ord::get_db] findMaster $gt_cell]
if {$gt_master eq "NULL" || $gt_master eq ""} { error "OT_GRID_TAPS: no master $gt_cell" }
set gt_in ""; set gt_out ""
foreach mt [$gt_master getMTerms] {
  if {[$mt getSigType] ni {SIGNAL CLOCK}} continue
  if {[$mt getIoType] eq "INPUT"} { set gt_in [$mt getName] } elseif {[$mt getIoType] eq "OUTPUT"} { set gt_out [$mt getName] }
}
set gt_die [$gt_blk getDieArea]
set gt_x0 [$gt_die xMin]; set gt_y0 [$gt_die yMin]
set gt_w [expr {double([$gt_die xMax] - $gt_x0)}]; set gt_h [expr {double([$gt_die yMax] - $gt_y0)}]
set gt_roots {}
foreach clk [all_clocks] {
  foreach src [get_property $clk sources] {
    set bt [$gt_blk findBTerm [get_full_name $src]]
    if {$bt ne "NULL" && $bt ne ""} { lappend gt_roots [$bt getNet] }
  }
}
set gt_js {}
set j 0
foreach root [lsort -unique $gt_roots] {
  set groups [dict create]
  foreach it [$root getITerms] {
    if {![$it isInputSignal]} continue
    set inst [$it getInst]
    set im [$inst getMaster]
    if {![$im isBlock] && ![regexp {^(DFF|ASYNC|SDF|DHL|DLL|ICG)} [$im getName]]} continue
    lassign [$inst getLocation] x y
    set ix [expr {min($gt_nx - 1, max(0, int(($x - $gt_x0) / $gt_w * $gt_nx)))}]
    set iy [expr {min($gt_ny - 1, max(0, int(($y - $gt_y0) / $gt_h * $gt_ny)))}]
    dict lappend groups "r${ix}_${iy}" $it
  }
  if {[dict size $groups] < 2} { puts "OT_GRID_TAPS [$root getName]: [dict size $groups] region(s), no taps"; continue }
  dict for {k its} $groups {
    set sx 0.0; set sy 0.0
    foreach it $its { lassign [[$it getInst] getLocation] x y; set sx [expr {$sx + $x}]; set sy [expr {$sy + $y}] }
    set cx [expr {round($sx / [llength $its])}]; set cy [expr {round($sy / [llength $its])}]
    set nm "ot_grid_tap_$j"
    set b [odb::dbInst_create $gt_blk $gt_master $nm]
    $b setLocation $cx $cy
    $b setPlacementStatus PLACED
    set net [odb::dbNet_create $gt_blk "${nm}_ck"]
    $net setSigType CLOCK
    [$b findITerm $gt_in] connect $root
    [$b findITerm $gt_out] connect $net
    foreach it $its { $it disconnect; $it connect $net }
    puts [format "OT_GRID_TAPS %s %s sinks %d at %.1f %.1f" $nm $k [llength $its] [expr {double($cx) / $gt_u}] [expr {double($cy) / $gt_u}]]
    lappend gt_js "\"$nm\": {\"region\": \"$k\", \"root\": \"[$root getName]\", \"sinks\": [llength $its], \"x\": [format %.2f [expr {double($cx) / $gt_u}]], \"y\": [format %.2f [expr {double($cy) / $gt_u}]]}"
    incr j
  }
}
puts "OT_GRID_TAPS grid $gt_nx x $gt_ny: $j taps"
# legalise the new tap buffers (placed at sink centroids, may overlap std cells)
detailed_placement
if {[info exists ::env(RESULTS_DIR)]} {
  set fh [open $::env(RESULTS_DIR)/ot_grid_taps.json w]; puts $fh "{[join $gt_js {, }]}"; close $fh
}
}
