set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [glob $L/asap7sc7p5t_*_RVT_FF_nldm_*.lib*] { read_liberty $f }
foreach f [glob -nocomplain /x/ot_rom_4096x274_m8_*.lib] { if {[string match "*_ff.lib" $f]} { read_liberty $f } }
read_db /b/6_final.odb
read_sdc /o/etm.sdc
read_spef /b/6_final.spef
set_propagated_clock [all_clocks]
write_timing_model -library_name ot_v41_rom_elem_q_qx_w10_ff /o/ot_v41_rom_elem_q_qx_w10_ff.lib
puts "OT_ETM_DONE FF"
