# CLAUDE HBM-ABSTRACTS (hub) post-DETAILED-route FF-corner hold ECO (coordinator decision 2026-10-06): hold is closed
# by repair under FF-corner constraints on the ROUTED design, not by a larger CTS / GRT HOLD_SLACK_MARGIN (which costs
# 20-40 ps of SS setup on the hub lanes: m6light_b HM .02 +41.0/+5.2 vs m9light HM .03 +19.8/+12.3).
#   SS + FF libraries as two STA corners, the routed 6_final.odb (fillers removed), its routed SDC plus the sign-off
#   post-SDC(s), RCX parasitics of the detailed route (ASAP7 ships one RC deck: the FF corner's parasitics are the
#   extracted ones) -> repair_timing -hold to OT_HOLD_MARGIN ps (FF) while keeping setup >= OT_SETUP_MARGIN ps (SS)
#   -> legalise -> incremental global route of the changed nets -> detailed route (existing wires kept) -> fillers
#   -> re-extract -> 6_final.{odb,spef,v}.  Constraints are unchanged (the routed SDC + post-SDC are re-read by the
#   sign-off STA, tools/w18/corner_sta.py); the ECO only adds/resizes hold buffers.
# env: OT_IN (routed base dir), OT_OUT (output base dir), OT_POST_SDC (space-separated), OT_HOLD_MARGIN (ps, default 22),
#      OT_SETUP_MARGIN (ps, default 45), OT_THREADS (default 8), OT_MAX_BUF_PCT (default 10), OT_MINL/OT_MAXL (M2/M5),
#      OT_MINCLKL (M4)
set P /OpenROAD-flow-scripts/flow/platforms/asap7
proc envd {n d} { expr {[info exists ::env($n)] && $::env($n) ne "" ? $::env($n) : $d} }
set hm [envd OT_HOLD_MARGIN 22]; set sm [envd OT_SETUP_MARGIN 45]
set_thread_count [envd OT_THREADS 8]
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
define_corners ss ff
foreach c {ss ff} C {SS FF} {
  foreach l [list asap7sc7p5t_AO_RVT_${C}_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_${C}_nldm_220122.lib.gz \
               asap7sc7p5t_OA_RVT_${C}_nldm_211120.lib.gz asap7sc7p5t_SEQ_RVT_${C}_nldm_220123.lib \
               asap7sc7p5t_SIMPLE_RVT_${C}_nldm_211120.lib.gz] { read_liberty -corner $c $P/lib/NLDM/$l }
}
read_db $::env(OT_IN)/6_final.odb
read_sdc $::env(OT_IN)/6_final.sdc
foreach s [envd OT_POST_SDC ""] { read_sdc $s }
set_propagated_clock [all_clocks]
source $P/setRC.tcl
set_dont_use {*x1p*_ASAP7* *xp*_ASAP7* SDF* ICG*}
remove_fillers
proc rep {tag} {
  puts "OT_ECO $tag"
  report_worst_slack -max -digits 2
  report_worst_slack -min -digits 2
  catch {report_checks -path_delay min -scenes ff -format slack_only -digits 2}
  catch {report_checks -path_delay max -scenes ss -format slack_only -digits 2}
}
# guides for the incremental router (the routed nets' detailed wires stay in the db); the route's layer range
set lo [envd OT_MINL M2]; set hi [envd OT_MAXL M5]
set_global_routing_layer_adjustment $lo-$hi 0.25
set_routing_layers -clock [envd OT_MINCLKL M4]-$hi
set_routing_layers -signal $lo-$hi
global_route -allow_congestion
global_route -start_incremental
extract_parasitics -ext_model_file $P/rcx_patterns.rules
rep pre
set n0 [llength [get_cells *]]
if {[catch {repair_timing -hold -hold_margin $hm -setup_margin $sm -max_buffer_percent [envd OT_MAX_BUF_PCT 10] -verbose} err]} {
  puts "OT_ECO repair_timing caught: $err"
}
puts "OT_ECO cells_added [expr {[llength [get_cells *]] - $n0}]"
detailed_placement
check_placement -verbose
global_route -end_incremental -allow_congestion
detailed_route -output_drc $::env(OT_OUT)/eco_drc.rpt -bottom_routing_layer $lo -top_routing_layer $hi -verbose 1
filler_placement {FILLERxp5_ASAP7_75t_R FILLER_ASAP7_75t_R}
check_placement -verbose
extract_parasitics -ext_model_file $P/rcx_patterns.rules
rep post
write_db $::env(OT_OUT)/6_final.odb
write_spef $::env(OT_OUT)/6_final.spef
write_verilog $::env(OT_OUT)/6_final.v
puts "OT_ECO done"
