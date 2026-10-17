foreach l [split $::env(BH_LEFS) " "] { if {$l ne ""} { read_lef $l } }
foreach l [split $::env(BH_LIBS) " "] { if {$l ne ""} { read_liberty $l } }
read_db $::env(BH_BASE)/6_final.odb
read_sdc $::env(BH_BASE)/6_final.sdc
read_spef $::env(BH_BASE)/6_final.spef
read_sdc $::env(BH_SDC)
set_propagated_clock [all_clocks]
write_timing_model -library_name a $::env(BH_OUT)/etm_old.lib
set clk [get_clocks core_clk]
set_input_delay 300 -min -clock $clk [all_inputs -no_clocks]
set_output_delay -300 -min -clock $clk [all_outputs]
write_timing_model -library_name a $::env(BH_OUT)/etm_new.lib
exit
