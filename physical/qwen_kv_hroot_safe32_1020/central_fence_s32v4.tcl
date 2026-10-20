# KV-RST3 2026-10-20 (s32v4): hard central fence for the SAFE32 HROOT (qkd_kvs_hroot_safe32), sourced by the kit's
# PRE_GLOBAL_PLACE wrapper AFTER io_flop_at_pins.tcl (spec "pin_hook_after_flops").
# Why: the s32v3 gate/route (qkd_kvs_hroot_safe32-s32v3-e52c7bca5) placed the intermediate stage (cap.dat.q1, region
# ctl/sid/rn copies, relay *_mid) freely, so N-face captures drove BUF/INV endpoints 517.2 um away (417 roots > 405 um,
# results/rtl/kv_hroot_safe32_1020/placed_reach_union.json).  The RTL already has capture -> intermediate -> launch;
# fencing every non-boundary cell into an 80 x 80 um box at the tile centre bounds each stage to face -> centre or
# centre -> face: worst L1 from a face point to the far fence corner = 150.12 + 40 + 150.12 + 40 = 380.24 um < 405.
# No RTL or cycle change.  Membership (fail closed on implausible classification):
#   boundary  = cells listed by the pin hooks (ot_out_flop_at_pins.txt, ot_inhold_firm.txt), every FIRM cell, and every
#               BUF / INV / HB cell reachable from a port net through BUF / INV / HB cells only (port <-> pin-flop chains);
#   loose     = TIE* cells (placed beside their loads) and physical-only cells (tap / endcap / no signal pins);
#   central   = every other standard cell -> INCLUSIVE region ot_hroot_center80 through group (gpl honours groups).
set cf_b [ord::get_db_block]
set cf_u [$cf_b getDbUnitsPerMicron]
if {[$cf_b findRegion ot_hroot_center80] ne "NULL"} { error "HROOT_CENTER: region already exists; refuse duplicate hook" }
set cf_half [expr {[info exists ::env(OT_HROOT_FENCE_HALF_UM)] ? $::env(OT_HROOT_FENCE_HALF_UM) : 40.0}]
set cf_die [$cf_b getDieArea]
set cf_cx [expr {0.5 * ([$cf_die xMin] + [$cf_die xMax]) / double($cf_u)}]
set cf_cy [expr {0.5 * ([$cf_die yMin] + [$cf_die yMax]) / double($cf_u)}]
set cf_box [list [expr {$cf_cx - $cf_half}] [expr {$cf_cy - $cf_half}] [expr {$cf_cx + $cf_half}] [expr {$cf_cy + $cf_half}]]
set cf_anchor [dict create]
foreach cf_file {ot_out_flop_at_pins.txt ot_inhold_firm.txt} {
  set cf_path [file join $::env(RESULTS_DIR) $cf_file]
  if {![file exists $cf_path]} { error "HROOT_CENTER: missing boundary ownership list $cf_path (hook must run after io_flop_at_pins)" }
  set cf_f [open $cf_path r]
  foreach cf_n [split [read $cf_f] "\n"] { if {$cf_n ne ""} { dict set cf_anchor $cf_n 1 } }
  close $cf_f
}
proc cf_isbuf {inst} {
  set m [[$inst getMaster] getName]
  return [expr {[string match "INV*" $m] || [string match "BUF*" $m] || [string match "HB*" $m]}]
}
# port-chain buffers: BFS over nets from every port net through BUF/INV/HB cells only
set cf_bnd [dict create]
set cf_q {}
set cf_seen_net [dict create]
foreach bt [$cf_b getBTerms] {
  set n [$bt getNet]
  if {$n ne "NULL" && [$n getSigType] ni {POWER GROUND CLOCK}} { lappend cf_q $n }
}
while {[llength $cf_q]} {
  set n [lindex $cf_q 0]; set cf_q [lrange $cf_q 1 end]
  if {[dict exists $cf_seen_net [$n getName]]} continue
  dict set cf_seen_net [$n getName] 1
  foreach it [$n getITerms] {
    set i [$it getInst]
    if {![cf_isbuf $i] || [dict exists $cf_bnd [$i getName]]} continue
    dict set cf_bnd [$i getName] 1
    foreach ot [$i getITerms] {
      set on [$ot getNet]
      if {$on ne "NULL" && [$on getSigType] ni {POWER GROUND CLOCK} && ![dict exists $cf_seen_net [$on getName]]} { lappend cf_q $on }
    }
  }
}
set cf_members {}; set cf_area 0.0
set cnt [dict create anchor 0 firm_unlisted 0 port_chain 0 tie 0 physical 0 central 0]
set cf_report [open [file join $::env(RESULTS_DIR) ot_hroot_central_members.tsv] w]
puts $cf_report "instance\tmaster\tstatus\tclass"
foreach cf_i [$cf_b getInsts] {
  set nm [$cf_i getName]; set st [$cf_i getPlacementStatus]; set m [$cf_i getMaster]; set mn [$m getName]
  if {[$m isBlock]} { error "HROOT_CENTER: expected no hard macro, found $nm" }
  set sig 0
  foreach it [$cf_i getITerms] { set n [$it getNet]; if {$n ne "NULL" && [$n getSigType] ni {POWER GROUND}} { set sig 1; break } }
  if {[dict exists $cf_anchor $nm]} { set cls anchor
  } elseif {$st in {FIRM LOCKED COVER}} { set cls [expr {$sig ? "firm_unlisted" : "physical"}]
  } elseif {!$sig} { set cls physical
  } elseif {[string match "TIE*" $mn]} { set cls tie
  } elseif {[dict exists $cf_bnd $nm]} { set cls port_chain
  } else {
    set cls central
    if {[$cf_i getGroup] ne "NULL"} { error "HROOT_CENTER: preexisting group on $nm; refuse overwrite" }
    lappend cf_members $cf_i
    set cf_area [expr {$cf_area + double([$m getWidth]) * [$m getHeight] / $cf_u / $cf_u}]
  }
  dict incr cnt $cls
  puts $cf_report "$nm\t$mn\t$st\t$cls"
}
close $cf_report
set cf_cap [expr {(2.0 * $cf_half) * (2.0 * $cf_half)}]
puts [format "HROOT_CENTER classes %s area_um2=%.3f capacity_um2=%.1f util=%.4f box=(%.2f %.2f %.2f %.2f)" $cnt $cf_area $cf_cap [expr {$cf_area / $cf_cap}] {*}$cf_box]
if {[dict get $cnt anchor] < 2500} { error "HROOT_CENTER: only [dict get $cnt anchor] pin-anchored cells (expected ~3100 ports); classification implausible" }
if {[llength $cf_members] < 2500} { error "HROOT_CENTER: only [llength $cf_members] central cells; classification implausible" }
if {$cf_area > 0.6 * $cf_cap} { error "HROOT_CENTER: central cell area $cf_area um2 exceeds 60% of the fence ($cf_cap um2)" }
set cf_r [odb::dbRegion_create $cf_b ot_hroot_center80]
odb::dbBox_create $cf_r {*}[lmap v $cf_box {expr {round($v * $cf_u)}}]
$cf_r setRegionType INCLUSIVE
set cf_g [odb::dbGroup_create $cf_r ot_hroot_center80_group]
foreach cf_i $cf_members { $cf_g addInst $cf_i }
puts "HROOT_CENTER fenced [llength $cf_members] cells into ot_hroot_center80"
