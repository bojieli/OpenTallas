# re-extract the spliced c1 DEF exactly as pilot_clip run.tcl (RCX TT) and dump drt TT tree
set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob $::env(LIBDIR)/*RVT_TT_nldm*.lib*] { read_liberty $f }
read_def /o/drt.def
create_clock -name vclk -period 833.0
set_input_transition $::env(SLEW) [get_ports root]
set_input_delay 0 -clock vclk [get_ports root]
foreach c [get_cells M*] { set_disable_timing $c }
define_process_corner -ext_model_index 0 X
extract_parasitics -ext_model_file $P/rcx_patterns.rules
write_spef /o/drt.spef
write_db /o/drt.odb
puts OT_RCX_DONE
