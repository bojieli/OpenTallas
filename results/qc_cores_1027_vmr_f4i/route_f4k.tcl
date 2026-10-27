# Continue only the saved72-buffer data ECO. Use the established F4G M6-grid/strip method.
source /work/f4k_libs.tcl
read_db /work/input/repaired.odb
read_sdc /work/constraint.sdc
set_propagated_clock [all_clocks]
set ::env(OT_F4G_G1) /work/input/repair.guide
set ::env(OT_M6_STRIP) /work/m6_strip_f4g.txt
set ::env(OT_F4G_LOCK) fixed
set ::env(OT_F4G_SIGTOP) M6
source /work/f4g_pre_drt_sig.tcl
pin_access
detailed_route -output_drc /out/eco_drc.rpt -verbose 1
source /work/f4g_post_drt.tcl
filler_placement {FILLERxp5_ASAP7_75t_R FILLER_ASAP7_75t_R}
global_connect
check_antennas -report_file /out/antenna.rpt
extract_parasitics -ext_model_file /OpenROAD-flow-scripts/flow/platforms/asap7/rcx_patterns.rules
write_spef /out/6_final.spef
write_db /out/6_final.odb
write_verilog /out/6_final.v
puts "F4K_DONE resumed72DATA buffers, pre-routedclockfixed"
