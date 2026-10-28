# FLOW-SHARED-4 2026-10-27 (COORD ruling 1): QC warm hold ECO as ONE OpenROAD session (ORFS 'make run RUN_SCRIPT=').
# Same shape as the kit's own one-session eco.tcl (F4J/F4K): load the routed DB, remove fillers, read the route's guides,
# global_route -start_incremental, repair_timing -hold, detailed_placement, -end_incremental, detailed_route, fill, RCX.
# Why: the two-process ORFS chain (do-5_1_grt from a routed DB, then do-5_2_route) cannot hand GRT state across the
# process split on a routed QC kit -- 5_1_grt routes only the ECO nets, so DRT got guides for 24 of 25.5k nets
# (codex/clkfreeze-qc-1351 canary 499769: 4302 guide errors, 442,578 violations, 453 opens).  In one session the
# full guide set read before -start_incremental stays in GRT memory and DRT sees every net's guide.
# The clock lock is the shared tools/die_plan/clk_freeze.tcl (HEAD / KV pattern): ot_clk_freeze before any repair,
# ot_clk_freeze_assert post_grt after -end_incremental, blocking clk_freeze_check.sh after the session (run_hold_1s.sh).
# Pre-routed (FIXED) clock nets carry NO guide into DRT (guide-less pre-routed nets are skipped as route targets and
# seen as shapes: F4G try 4); a kit with an M6 clock trunk + signal strip (f4g_pre_drt_sig.tcl + m6_strip_f4g.txt,
# OT_QC_DRT_PREP=f4g) runs that kit's own proven DRT prep (route_f4k.tcl recipe) instead.
# Inputs (staged by mk_hold_qc.sh): RESULTS_DIR/4_cts.odb = the kit's matched final ODB, 6_final.spef its RCX,
# 4_cts.sdc, OT_QC_GUIDE = that route's full guide file.  Env: OT_HOLD_MARGIN, OT_HOLD_MAXBUF, OT_HOLD_ALLOW_SETUP,
# OT_KIT_PRE_GRT (kit PRE_GLOBAL_ROUTE hook: FF vclk bind), OT_QC_DRT_PREP (generic | f4g), OT_QC_MAXADD (default 500).
source $::env(SCRIPTS_DIR)/load.tcl
load_design 4_cts.odb 4_cts.sdc
set R $::env(RESULTS_DIR)
set block [ord::get_db_block]
proc qc1s {args} { puts "QC1S [join $args { }]" }
if {[info exists ::env(OT_KIT_PRE_GRT)] && $::env(OT_KIT_PRE_GRT) ne ""} { source $::env(OT_KIT_PRE_GRT) }
read_spef $R/6_final.spef
remove_fillers
# clock lock (fail closed when not staged)
set _ckf [file join [file dirname [info script]] clk_freeze.tcl]
if {![file exists $_ckf]} { error "OT_CLK_FREEZE FAIL: $_ckf not staged (ECO refuses to run without the clock lock)" }
source $_ckf
ot_clk_freeze
# every routed instance stays where it is (kit eco.tcl: FIRM): only the new hold cells are legalised.  Without this the
# DPL negotiation legaliser moves routed cells and their wires no longer reach the pins (first 1s try 10-27 15:46:
# 444k DRT markers in iteration 0 + connectivity breaks -- the same signature as the 499769 segment run).
set orig [dict create]; set nfirm 0
foreach i [$block getInsts] {
  dict set orig [$i getName] [$i getLocation]
  if {[$i getPlacementStatus] ni {FIRM LOCKED COVER}} { $i setPlacementStatus FIRM; incr nfirm }
}
qc1s firm $nfirm of [dict size $orig]
set g $::env(OT_QC_GUIDE)
if {![file exists $g]} { error "QC1S FAIL: guide file $g missing" }
read_guides $g
if {![grt::have_routes]} { error "QC1S FAIL: no GRT routes after read_guides $g" }
qc1s guides $g have_routes 1
global_route -start_incremental
set_dont_use {*x1p*_ASAP7* *xp*_ASAP7* SDF* ICG*}
unset_dont_use [get_lib_cells {*/HB1xp67_ASAP7_75t_R */HB2xp67_ASAP7_75t_R}]
set args [list -hold -hold_margin $::env(OT_HOLD_MARGIN) -max_buffer_percent $::env(OT_HOLD_MAXBUF)]
if {$::env(OT_HOLD_ALLOW_SETUP) == 1} { lappend args -allow_setup_violations }
qc1s before_wns_min [sta::time_sta_ui [sta::worst_slack_cmd min]] repair_timing $args
repair_timing {*}$args
detailed_placement
check_placement -verbose
set dirty [dict create]; set added 0; set moved 0
foreach i [$block getInsts] {
  if {[dict exists $orig [$i getName]]} { if {[$i getLocation] ne [dict get $orig [$i getName]]} { incr moved }; continue }
  incr added
  foreach it [$i getITerms] { set n [$it getNet]; if {$n ne "NULL" && ![$n isSpecial]} { dict set dirty [$n getName] 1 } }
}
set maxadd [expr {[info exists ::env(OT_QC_MAXADD)] ? $::env(OT_QC_MAXADD) : 500}]
qc1s repair added $added dirty_nets [dict size $dirty] routed_insts_moved $moved
if {$moved} { error "QC1S FAIL: $moved routed instances moved by the ECO legaliser" }
if {$added > $maxadd} { error "QC1S FAIL: $added cells added > $maxadd (not a sparse warm residual)" }
# the data nets of the new cells re-route; a frozen clock net is never destroyed here (and restored below if GRT does)
set ndes 0
foreach nm [dict keys $dirty] {
  if {[lsearch -exact $::ot_clk_frozen_nets $nm] >= 0} continue
  set n [$block findNet $nm]; set w [$n getWire]
  if {$w ne "NULL" && $w ne ""} { odb::dbWire_destroy $w; incr ndes }
}
qc1s data_wires_destroyed $ndes
global_route -end_incremental
ot_clk_freeze_assert post_grt
write_guides $R/route_eco.guide
set prep [expr {[info exists ::env(OT_QC_DRT_PREP)] ? $::env(OT_QC_DRT_PREP) : "generic"}]
if {$prep eq "f4g"} {
  set ::env(OT_F4G_G1) $R/route_eco.guide
  set ::env(OT_F4G_LOCK) fixed
  if {![info exists ::env(OT_F4G_SIGTOP)]} { set ::env(OT_F4G_SIGTOP) M6 }
  set ::env(OT_M6_STRIP) /work/m6_strip_f4g.txt
  source /work/f4g_pre_drt_sig.tcl
} elseif {$prep eq "generic"} {
  set ncg 0
  foreach nm $::ot_clk_frozen_nets { set n [$block findNet $nm]; if {[llength [$n getGuides]]} { $n clearGuides; incr ncg } }
  qc1s drt_prep generic frozen_clock_guides_cleared $ncg
} else { error "QC1S FAIL: unknown OT_QC_DRT_PREP $prep" }
if {![grt::have_routes]} { error "QC1S FAIL: no GRT routes before DRT" }
pin_access
detailed_route -output_drc $::env(REPORTS_DIR)/5_route_drc.rpt -verbose 1
if {$prep eq "f4g" && [file exists /work/f4g_post_drt.tcl]} { source /work/f4g_post_drt.tcl }
check_antennas -report_file $::env(REPORTS_DIR)/drt_antennas.log
write_db $R/5_2_route.odb
filler_placement {FILLERxp5_ASAP7_75t_R FILLER_ASAP7_75t_R}
global_connect
extract_parasitics -ext_model_file $::env(PLATFORM_DIR)/rcx_patterns.rules
write_spef $R/6_final.spef
write_db $R/6_final.odb
write_verilog $R/6_final.v
write_verilog -remove_cells {TAPCELL_ASAP7_75t_R FILLER_ASAP7_75t_R FILLERxp5_ASAP7_75t_R} $R/6_final_logic.v
qc1s DONE added $added
exit
