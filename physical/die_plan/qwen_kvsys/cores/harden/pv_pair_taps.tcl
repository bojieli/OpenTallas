# physical/die_plan/qwen_kvsys/cores/harden/pv_pair_taps.tcl (CORES-KITS/KVX 2026-10-26; GEOM-REVIEW-2 2026-10-25 08:12
# verdict on kv3_pv_pair fd4_cc (2): regional clock taps + the SRAMs on the tap of their own launch/capture registers).
# PRE_CTS, same mechanism as head_lane_taps.tcl (one tap buffer per group at the group's sink centroid, driving a new
# CLOCK net with exactly that group's clock pins; CTS -balance_levels builds port -> taps + one tree per tap).
# Groups per slice u_s<k> (ot_qwen_tp8_pv16_slice_gen: SRAM g_mem[m] drives rd[128m+:128] -> old[0..2][128m+:128],
# reduce_a / tree_sum [128m+:128] and lanes g_lane[4m..4m+3] (rd[32l+:32]) directly):
#   u_s<k>_m<m>  = g_mem[m] SRAM CLK + g_lane[4m..4m+3] + old[*]/reduce_a/tree_sum bits [128m, 128m+127]  (~3.5k sinks)
#   u_s<k>_ctl   = every other register of the slice (c_r / wp / cp issue control, ts / v_r / e_r face regs, fault)
#   rest         = anything outside u_s0 / u_s1
# So the failing related pairs of fd4_cc (g_mem[2].CLK -> old[0] / reduce_a / g_lane[11].rd, skew 85.5 TT) share their
# tap; c_r -> g_mem CLK crosses ctl -> m tap through the balanced top tree.  Writes $RESULTS_DIR/ot_pv_taps.json.
uplevel #0 {
set pt_cell [expr {[info exists ::env(OT_LANE_TAP_CELL)] ? $::env(OT_LANE_TAP_CELL) : "BUFx12f_ASAP7_75t_R"}]
set pt_blk [ord::get_db_block]
set pt_u [[ord::get_db_tech] getDbUnitsPerMicron]
set pt_master [[ord::get_db] findMaster $pt_cell]
if {$pt_master eq "NULL" || $pt_master eq ""} { error "OT_PV_TAPS: no master $pt_cell" }
set pt_in ""; set pt_out ""
foreach mt [$pt_master getMTerms] {
  if {[$mt getSigType] ni {SIGNAL CLOCK}} continue
  if {[$mt getIoType] eq "INPUT"} { set pt_in [$mt getName] } elseif {[$mt getIoType] eq "OUTPUT"} { set pt_out [$mt getName] }
}
proc ot_pv_key {name} {
  global pt_blk
  set n [string map {\\ {}} $name]
  if {![regexp {^(u_s[0-9]+)\.(.*)$} $n -> s r]} { return rest }
  if {[regexp {^u_slice\.g_mem\[([0-9]+)\]\.} $r -> m]} { return ${s}_m$m }
  if {[regexp {^u_slice\.g_lane\[([0-9]+)\]\.} $r -> l]} { return ${s}_m[expr {$l / 4}] }
  if {[regexp {^u_slice\.old\[[0-9]+\]\[([0-9]+)\]} $r -> b]} { return ${s}_m[expr {$b / 128}] }
  if {[regexp {^u_slice\.(reduce_a|tree_sum)\[([0-9]+)\]} $r -> _ b]} { return ${s}_m[expr {$b / 128}] }
  # The original control group mixes all face-input/face-output and issue
  # registers across a slice.  A high-capacitance c_r[0] clock leaf arrived
  # 39 ps after an adjacent data group.  Optional spatial sub-roots bound
  # this control clock's wire span without duplicating its dedicated pin FF.
  set regions [expr {[info exists ::env(OT_PV_CONTROL_REGIONS)] ? $::env(OT_PV_CONTROL_REGIONS) : 1}]
  if {$regions > 1} {
    if {$regions != 4} { error "OT_PV_CONTROL_REGIONS must be 1 or 4" }
    set inst [$pt_blk findInst $name]
    if {$inst eq "NULL" || $inst eq ""} { error "OT_PV_TAPS missing control instance $name" }
    set area [$pt_blk getCoreArea]
    set width [expr {double([$area xMax]-[$area xMin])/2.0}]
    regexp {^u_s([0-9]+)$} $s -> slice
    if {$slice ni {0 1}} { error "OT_PV_CONTROL_REGIONS expects exactly two slices" }
    set box [$inst getBBox]
    set cx [expr {0.5*([$box xMin]+[$box xMax])}]
    set group [expr {max(0,min(3,int(floor(($cx-[$area xMin]-$slice*$width)*4.0/$width))))}]
    return ${s}_ctl$group
  }
  return ${s}_ctl
}
set pt_roots {}
foreach clk [all_clocks] {
  foreach src [get_property $clk sources] {
    set bt [$pt_blk findBTerm [get_full_name $src]]
    if {$bt ne "NULL" && $bt ne ""} { lappend pt_roots [$bt getNet] }
  }
}
set pt_js {}
foreach root [lsort -unique $pt_roots] {
  set groups [dict create]
  foreach it [$root getITerms] {
    if {![$it isInputSignal]} continue
    set inst [$it getInst]
    set im [$inst getMaster]
    if {![$im isBlock] && ![regexp {^(DFF|ASYNC|SDF|DHL|DLL|ICG)} [$im getName]]} continue
    dict lappend groups [ot_pv_key [$inst getName]] $it
  }
  set j 0
  dict for {k its} $groups {
    set sx 0.0; set sy 0.0; set nmac 0
    set x0 1e18; set y0 1e18; set x1 -1e18; set y1 -1e18
    foreach it $its {
      set inst [$it getInst]; lassign [$inst getLocation] x y
      if {[[$inst getMaster] isBlock]} { incr nmac }
      set sx [expr {$sx + $x}]; set sy [expr {$sy + $y}]
      set x0 [expr {min($x0,$x)}]; set y0 [expr {min($y0,$y)}]; set x1 [expr {max($x1,$x)}]; set y1 [expr {max($y1,$y)}]
    }
    set cx [expr {round($sx / [llength $its])}]; set cy [expr {round($sy / [llength $its])}]
    set nm "ot_pv_tap_$j"
    set b [odb::dbInst_create $pt_blk $pt_master $nm]
    $b setLocation $cx $cy
    $b setPlacementStatus PLACED
    set net [odb::dbNet_create $pt_blk "${nm}_ck"]
    $net setSigType CLOCK
    [$b findITerm $pt_in] connect $root
    [$b findITerm $pt_out] connect $net
    foreach it $its { $it disconnect; $it connect $net }
    set bb [format "%.1f %.1f %.1f %.1f" [expr {$x0/$pt_u}] [expr {$y0/$pt_u}] [expr {$x1/$pt_u}] [expr {$y1/$pt_u}]]
    puts [format "OT_PV_TAPS %s %s sinks %d macros %d at %.1f %.1f bbox %s" $nm $k [llength $its] $nmac [expr {double($cx) / $pt_u}] [expr {double($cy) / $pt_u}] $bb]
    lappend pt_js "\"$nm\": {\"group\": \"$k\", \"sinks\": [llength $its], \"macros\": $nmac, \"x\": [format %.2f [expr {double($cx) / $pt_u}]], \"y\": [format %.2f [expr {double($cy) / $pt_u}]], \"bbox\": \[[join $bb {, }]\]}"
    incr j
  }
  puts "OT_PV_TAPS [$root getName]: $j taps"
}
if {[info exists ::env(RESULTS_DIR)]} {
  set fh [open $::env(RESULTS_DIR)/ot_pv_taps.json w]; puts $fh "{[join $pt_js {, }]}"; close $fh
}
}
