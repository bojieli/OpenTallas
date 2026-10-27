# HBM-EP-REPACK diagnostic GRT probe (read-only on the placed/CTS odb): pin access + GRT M2-M5, ITERS congestion iterations.
# HBM-CORES-R6 10-27: (1) std-cell liberty read BEFORE setRC (the rp1 grt-stage run failed ORD-0013 "command units
# uninitialized" at setRC and the outer script still printed rc=0); (2) any Tcl error exits 3; (3) the script itself
# prints OT_PROBE_GRT_DONE only after global_route returns, so the wrapper can refuse a run that never reached it.
proc ot_fail {code msg} { puts "OT_PROBE_GRT_FAIL $code $msg"; exit $code }
if {[catch {
  read_db $::env(ODB)
  set libs [glob -nocomplain $::env(PLATFORM_DIR)/lib/NLDM/asap7sc7p5t_*_RVT_TT_nldm_*.lib*]
  if {![llength $libs]} { ot_fail 3 "no std-cell TT liberty under $::env(PLATFORM_DIR)/lib/NLDM" }
  foreach f $libs { read_liberty $f }
  foreach f [glob -nocomplain /work/macros/*_tt.lib] { read_liberty $f }
  source $::env(PLATFORM_DIR)/setRC.tcl
  set_global_routing_layer_adjustment M2-M5 0.25
  set_routing_layers -clock M4-M5
  set_routing_layers -signal M2-M5
  pin_access
} msg]} { ot_fail 3 "setup: $msg" }
set rc [catch {global_route -congestion_report_file $::env(OUT)/congestion.rpt -congestion_iterations $::env(ITERS) -congestion_report_iter_step 5 -verbose -allow_congestion} msg]
puts "OT_PROBE_GRT rc=$rc iters=$::env(ITERS)"
if {$rc} { ot_fail 4 "global_route: $msg" }
puts "OT_PROBE_GRT_DONE"
