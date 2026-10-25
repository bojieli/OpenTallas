# GENERATED-COPY of physical/die_plan/qwen_kvsys/cores/harden/head_lane_taps.tcl (gen_core_kit_kv.py --head-lane-taps;
# KV-HEADCLK 2026-10-25, COORD verdict: regional clock tap per lane, not a hold ECO).
# PRE_CTS: the head core has ONE clock port.  Every head lane (ot_qkh_lane8 g_d[k], OT_LANE_RE) gets its own regional
# tap: one clock buffer (OT_LANE_TAP_CELL) placed at the centroid of the lane's flops, driving a new CLOCK net that
# carries exactly that lane's register clock pins; every register outside a lane (front / stin / stk / l8 ctl / ltd) hangs
# on one more tap at its own centroid.  TritonCTS builds one tree per tap net (a buffer-driven clock net is its own
# tree) and the top tree from the port to the taps (CTS_ARGS -balance_levels), so every launch / capture pair inside a
# lane shares the path down to its tap (CPPR credit) and the lane tree spans only the compact lane region
# (head_lane_fence.tcl), instead of one generic H-tree whose level-1..6 splits cut the lane columns (e4/e6 FF -13..-15).
# Writes $RESULTS_DIR/ot_lane_taps.json {tap: sinks}.  Env: OT_LANE_RE, OT_LANE_TAP_CELL (BUFx12f_ASAP7_75t_R)
uplevel #0 {
set lt_re [expr {[info exists ::env(OT_LANE_RE)] && $::env(OT_LANE_RE) ne "" ? $::env(OT_LANE_RE) : {^(u_g_t_[0-9a-z]+_u_l8\.g_d\\?\[[0-9]+\\?\])[./]}}]
set lt_cell [expr {[info exists ::env(OT_LANE_TAP_CELL)] ? $::env(OT_LANE_TAP_CELL) : "BUFx12f_ASAP7_75t_R"}]
set lt_blk [ord::get_db_block]
set lt_u [[ord::get_db_tech] getDbUnitsPerMicron]
set lt_master [[ord::get_db] findMaster $lt_cell]
if {$lt_master eq "NULL" || $lt_master eq ""} { error "OT_LANE_TAPS: no master $lt_cell" }
set lt_in ""; set lt_out ""
foreach mt [$lt_master getMTerms] {
  if {[$mt getSigType] ni {SIGNAL CLOCK}} continue
  if {[$mt getIoType] eq "INPUT"} { set lt_in [$mt getName] } elseif {[$mt getIoType] eq "OUTPUT"} { set lt_out [$mt getName] }
}
# the clock root net(s): nets of the SDC clock source ports
set lt_roots {}
foreach clk [all_clocks] {
  foreach src [get_property $clk sources] {
    set bt [$lt_blk findBTerm [get_full_name $src]]
    if {$bt ne "NULL" && $bt ne ""} { lappend lt_roots [$bt getNet] }
  }
}
set lt_js {}
foreach root [lsort -unique $lt_roots] {
  set groups [dict create]
  foreach it [$root getITerms] {
    if {![$it isInputSignal]} continue
    set inst [$it getInst]
    # SRAM clock pins share the lane tap with their read-capture flops. Leaving
    # macros on the root splits that related pair across CTS branches (PV failure).
    set im [$inst getMaster]
    if {![$im isBlock] && ![regexp {^(DFF|ASYNC|SDF|DHL|DLL|ICG)} [$im getName]]} continue
    set k [expr {[regexp $lt_re [$inst getName] -> kk] ? $kk : "rest"}]
    dict lappend groups $k $it
  }
  if {[dict size $groups] < 2} { puts "OT_LANE_TAPS [$root getName]: [dict size $groups] group(s), no lane taps"; continue }
  set j 0
  dict for {k its} $groups {
    set sx 0.0; set sy 0.0
    foreach it $its { lassign [[$it getInst] getLocation] x y; set sx [expr {$sx + $x}]; set sy [expr {$sy + $y}] }
    set cx [expr {round($sx / [llength $its])}]; set cy [expr {round($sy / [llength $its])}]
    set nm "ot_lane_tap_$j"
    set b [odb::dbInst_create $lt_blk $lt_master $nm]
    $b setLocation $cx $cy
    $b setPlacementStatus PLACED
    set net [odb::dbNet_create $lt_blk "${nm}_ck"]
    $net setSigType CLOCK
    [$b findITerm $lt_in] connect $root
    [$b findITerm $lt_out] connect $net
    foreach it $its { $it disconnect; $it connect $net }
    puts [format "OT_LANE_TAPS %s %s sinks %d at %.1f %.1f" $nm $k [llength $its] [expr {double($cx) / $lt_u}] [expr {double($cy) / $lt_u}]]
    lappend lt_js "\"$nm\": {\"group\": \"[string map {\\ {}} $k]\", \"sinks\": [llength $its], \"x\": [format %.2f [expr {double($cx) / $lt_u}]], \"y\": [format %.2f [expr {double($cy) / $lt_u}]]}"
    incr j
  }
  puts "OT_LANE_TAPS [$root getName]: $j taps"
}
if {[info exists ::env(RESULTS_DIR)]} {
  set fh [open $::env(RESULTS_DIR)/ot_lane_taps.json w]; puts $fh "{[join $lt_js {, }]}"; close $fh
}
}
