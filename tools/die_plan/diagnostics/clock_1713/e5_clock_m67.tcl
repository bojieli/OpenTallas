# One isolated routing diagnostic; reads an immutable native-TT CTS checkpoint.
# Data routing stays M2-M5. No placement, CTS, hold repair, or SDC edits.
source /scripts/timing_libs.tcl
ot_lib_load TT /out/libraries_TT.json /work/config.mk
read_db /work/checkpoint/4_cts.odb
read_sdc /work/checkpoint/4_cts.sdc
source /work/setRC_rcx.tcl
set_propagated_clock [get_clocks clk]
set_routing_layers -signal M2-M5 -clock M6-M7
set_global_routing_layer_adjustment M2-M7 0.0
puts "E5_CLOCK_M67_DIAGNOSTIC data=M2-M5 clock=M6-M7 native_CTS_unchanged=1 no_STA_or_signoff=1"
pin_access
global_route -congestion_report_file /out/congestion.rpt -congestion_iterations 30 -congestion_report_iter_step 5 -verbose -resistance_aware
write_guides /out/route.guide
write_db /out/5_clock_m67.odb
puts "E5_CLOCK_M67_GRT_COMPLETE: accounting classification and actual-route review remain required"
