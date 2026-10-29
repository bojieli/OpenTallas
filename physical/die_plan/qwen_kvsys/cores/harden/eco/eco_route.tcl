# KV-CORES 10-24: warm post-route ECO of a routed KV hard core (ORFS POST_GLOBAL_ROUTE_TCL hook of a do-route that starts
# from the core's own 5_2_route.odb, copied in as 4_cts.odb; 6_final.spef in RESULTS_DIR = that route's RCX).
# Derived from ELEM-QK recipe b (tools/elem_qk/hold_eco/hold_route.tcl on claude/elem-qk-1024: FF-only hold margin 3
# left -1.6..+0.09 ps residual on the 285 heads), plus the DRV fix the 216 heads need: the TT/FF max-slew violators
# are all placement-buffer nets with fanout 55-174 (ASAP7 liberty has no max_fanout) whose routed RC gives 320-507 ps
# at the far loads while the driver slew is ~60 ps (probe tools/kv_cores/slew_nets.tcl).  Steps (env knobs):
#   OT_MAX_FANOUT   set_max_fanout on the design, then repair_design splits the high-fanout nets      (0 = skip)
#   OT_SLEW_MARGIN  repair_design -slew_margin / -cap_margin (percent)
#   OT_SETUP_MARGIN repair_timing -setup -setup_margin (ps; "" = skip; MCMM tc+bc variants)
#   OT_HOLD_MARGIN  repair_timing -hold -hold_margin (ps), OT_HOLD_ALLOW_SETUP, OT_HOLD_MAXBUF
# No RTL / cycle / clock-tree / SDC change; the verdict is tools/die_plan/signoff.py TT setup / FF hold on the re-routed DB.
read_spef $::env(RESULTS_DIR)/6_final.spef
# FLOW-CLKFREEZE 2026-10-27: lock the routed clock network (FIXED wires, FIXED + dont_touch clock-net instances)
# before any repair, so incremental GRT / DRT never re-route a clock net (tools/die_plan/clk_freeze.tcl; blocking
# geometry diff = tools/die_plan/clk_freeze_check.sh in the chain).  Staged next to this file by every ECO chain.
set _ckf [file join [file dirname [info script]] clk_freeze.tcl]
if {![file exists $_ckf]} { error "OT_CLK_FREEZE FAIL: $_ckf not staged (ECO refuses to run without the clock lock)" }
source $_ckf
ot_clk_freeze
global_route -start_incremental
proc kvc_drv {} {
  if {$::env(OT_MAX_FANOUT) > 0} {
    set_max_fanout $::env(OT_MAX_FANOUT) [current_design]
  }
  puts "KVCORES_ECO repair_design slew_margin $::env(OT_SLEW_MARGIN) max_fanout $::env(OT_MAX_FANOUT)"
  repair_design -slew_margin $::env(OT_SLEW_MARGIN) -cap_margin $::env(OT_SLEW_MARGIN)
}
# OT_DRV_LAST=1: hold/setup repair first on the routed SPEF + GRT source (ELEM-QK recipe order), then the fanout / slew
# repair on placement parasitics: repair_design on the incremental GRT source of a routed DB dies with RSZ-0074
# ("failed to build tree from global routes", head e3 10-24); a split can also speed far loads, so FF hold is re-judged by signoff.py (not assumed safe).
set drv_last [expr {[info exists ::env(OT_DRV_LAST)] && $::env(OT_DRV_LAST) == 1}]
# OT_DRV_PLACE=1 (KV-CORES-PAR 10-24, head e3): DRV-first like m8 (the e1/e5/e7 SIGNED order) but the fanout / slew repair
# runs on placement parasitics (no RSZ-0074 tree build from the routed DB's GRT), then the new buffers are legalized and
# globally routed (end/start incremental) and setup / hold repair run on fresh GRT parasitics.
set drv_place [expr {[info exists ::env(OT_DRV_PLACE)] && $::env(OT_DRV_PLACE) == 1}]
if {$drv_place && !$drv_last} {
  puts "KVCORES_ECO drv-place: repair_design on placement parasitics, then incremental GRT + GRT parasitics"
  estimate_parasitics -placement
  kvc_drv
  detailed_placement
  global_route -end_incremental
  ot_clk_freeze_assert post_grt
  global_route -start_incremental
  estimate_parasitics -global_routing
} elseif {!$drv_last} { kvc_drv }
if {$::env(OT_SETUP_MARGIN) ne ""} {
  puts "KVCORES_ECO repair_timing -setup -setup_margin $::env(OT_SETUP_MARGIN)"
  repair_timing -setup -setup_margin $::env(OT_SETUP_MARGIN) -skip_last_gasp
}
set args [list -hold -hold_margin $::env(OT_HOLD_MARGIN) -max_buffer_percent $::env(OT_HOLD_MAXBUF)]
if {$::env(OT_HOLD_ALLOW_SETUP) == 1} { lappend args -allow_setup_violations }
puts "KVCORES_ECO repair_timing $args"
# OT_PAD_NEW_HOLD=SITES (DIE-KV-32 10-29, COORD KV-010 variant C ruling 11:12): the hold buffers THIS repair inserts get
# placement padding (left = right = SITES) before the ECO legalization, so they spread next to their capture FFs instead
# of packing a dense pin-face band (KV-010 B: 461 BUFx2 into the E-face hold-buffer band -> DRT oscillating 139..861).
set pad_new_hold [expr {[info exists ::env(OT_PAD_NEW_HOLD)] ? $::env(OT_PAD_NEW_HOLD) : 0}]
if {$pad_new_hold > 0} { set _pre_insts [dict create]; foreach i [[ord::get_db_block] getInsts] { dict set _pre_insts [$i getName] 1 } }
repair_timing {*}$args
if {$pad_new_hold > 0} {
  set _new_hold {}
  foreach i [[ord::get_db_block] getInsts] { if {![dict exists $_pre_insts [$i getName]]} { lappend _new_hold [$i getName] } }
  puts "KVCORES_ECO pad_new_hold [llength $_new_hold] instances -left $pad_new_hold -right $pad_new_hold"
  if {[llength $_new_hold] > 0} { set_placement_padding -instances [get_cells $_new_hold] -left $pad_new_hold -right $pad_new_hold }
}
if {$drv_last} {
  estimate_parasitics -placement
  kvc_drv
  # OT_RETIME_LAST=1: the DRV-last split/resize cost e3 ~70 ps TT setup (m8_dl -67.3 vs m8 +24 on e5/e7): repair setup
  # again after the DRV pass (same margin), then hold again without setup violations allowed
  if {[info exists ::env(OT_RETIME_LAST)] && $::env(OT_RETIME_LAST) == 1 && $::env(OT_SETUP_MARGIN) ne ""} {
    puts "KVCORES_ECO retime-last: repair_timing -setup -setup_margin $::env(OT_SETUP_MARGIN); hold -hold_margin $::env(OT_HOLD_MARGIN)"
    repair_timing -setup -setup_margin $::env(OT_SETUP_MARGIN) -skip_last_gasp
    repair_timing -hold -hold_margin $::env(OT_HOLD_MARGIN) -max_buffer_percent $::env(OT_HOLD_MAXBUF)
  }
}
# OT_PAD_MASTERS "MASTER:SITES ...": placement padding (left = right = SITES) for masters whose pins lose DRT access when the
# ECO legalizer abuts new buffers to them (e6: DRT-1231 on FAx1 CON at 96.768,146.61 after the m8/b8 hold-buffer fill)
if {[info exists ::env(OT_PAD_MASTERS)] && $::env(OT_PAD_MASTERS) ne ""} {
  foreach mp $::env(OT_PAD_MASTERS) {
    lassign [split $mp :] m n
    puts "KVCORES_ECO set_placement_padding -masters $m -left $n -right $n"
    set_placement_padding -masters [list $m] -left $n -right $n
  }
}
detailed_placement
global_route -end_incremental
ot_clk_freeze_assert post_grt
estimate_parasitics -global_routing
write_guides $::env(RESULTS_DIR)/route.guide
