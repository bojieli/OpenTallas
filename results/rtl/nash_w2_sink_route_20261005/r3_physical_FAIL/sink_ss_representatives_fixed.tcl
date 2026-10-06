
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef

read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz

read_db /work/results/asap7/opentallas_ot_hbm_integrated_w2_result_sink_asap7_nash_w2_sink_f835_r1/base/6_final.odb
read_sdc /work/results/asap7/opentallas_ot_hbm_integrated_w2_result_sink_asap7_nash_w2_sink_f835_r1/base/6_final.sdc
read_spef /work/results/asap7/opentallas_ot_hbm_integrated_w2_result_sink_asap7_nash_w2_sink_f835_r1/base/6_final.spef
set_propagated_clock [all_clocks]
puts {SOURCE_CLASS control -1161.007568 on.code[24][49]$_DFF_PN0_/QN -> on.code[24][71]$_DFF_PN0_/D}
set target {}
foreach pin [all_registers -data_pins] {if {[get_full_name $pin] eq {on.code[24][71]$_DFF_PN0_/D}} {set target $pin;break}}
if {$target eq {}} {error "missing exact endpoint"}
report_checks -path_delay max -to $target -group_path_count 1 -format full_clock_expanded -fields {fanout capacitance slew input_pin net}
puts {SOURCE_CLASS req_address -1133.213013 on.code[3][24]$_DFF_PN0_/QN -> req[332]}
set target {}
foreach pin [all_outputs] {if {[get_full_name $pin] eq {req[332]}} {set target $pin;break}}
if {$target eq {}} {error "missing exact endpoint"}
report_checks -path_delay max -to $target -group_path_count 1 -format full_clock_expanded -fields {fanout capacitance slew input_pin net}
puts {SOURCE_CLASS payload -984.646057 on.code[2][53]$_DFF_PN0_/QN -> on.code[21][27]$_DFFE_PN0P_/D}
set target {}
foreach pin [all_registers -data_pins] {if {[get_full_name $pin] eq {on.code[21][27]$_DFFE_PN0P_/D}} {set target $pin;break}}
if {$target eq {}} {error "missing exact endpoint"}
report_checks -path_delay max -to $target -group_path_count 1 -format full_clock_expanded -fields {fanout capacitance slew input_pin net}
puts {SOURCE_CLASS source_permit -975.986206 on.code[20][37]$_DFFE_PN0P_/QN -> source_permit}
set target {}
foreach pin [all_outputs] {if {[get_full_name $pin] eq {source_permit}} {set target $pin;break}}
if {$target eq {}} {error "missing exact endpoint"}
report_checks -path_delay max -to $target -group_path_count 1 -format full_clock_expanded -fields {fanout capacitance slew input_pin net}
puts {SOURCE_CLASS fault -970.058594 on.code[20][37]$_DFFE_PN0P_/QN -> fault}
set target {}
foreach pin [all_outputs] {if {[get_full_name $pin] eq {fault}} {set target $pin;break}}
if {$target eq {}} {error "missing exact endpoint"}
report_checks -path_delay max -to $target -group_path_count 1 -format full_clock_expanded -fields {fanout capacitance slew input_pin net}
puts {SOURCE_CLASS rsp_r -963.023315 on.code[20][37]$_DFFE_PN0P_/QN -> rsp_r}
set target {}
foreach pin [all_outputs] {if {[get_full_name $pin] eq {rsp_r}} {set target $pin;break}}
if {$target eq {}} {error "missing exact endpoint"}
report_checks -path_delay max -to $target -group_path_count 1 -format full_clock_expanded -fields {fanout capacitance slew input_pin net}
puts {SOURCE_CLASS req_v -951.395386 on.code[20][37]$_DFFE_PN0P_/QN -> req_v}
set target {}
foreach pin [all_outputs] {if {[get_full_name $pin] eq {req_v}} {set target $pin;break}}
if {$target eq {}} {error "missing exact endpoint"}
report_checks -path_delay max -to $target -group_path_count 1 -format full_clock_expanded -fields {fanout capacitance slew input_pin net}
puts {SOURCE_CLASS done -944.632385 on.code[20][37]$_DFFE_PN0P_/QN -> done}
set target {}
foreach pin [all_outputs] {if {[get_full_name $pin] eq {done}} {set target $pin;break}}
if {$target eq {}} {error "missing exact endpoint"}
report_checks -path_delay max -to $target -group_path_count 1 -format full_clock_expanded -fields {fanout capacitance slew input_pin net}
puts {SOURCE_CLASS req_payload -938.394714 on.code[24][49]$_DFF_PN0_/QN -> req[199]}
set target {}
foreach pin [all_outputs] {if {[get_full_name $pin] eq {req[199]}} {set target $pin;break}}
if {$target eq {}} {error "missing exact endpoint"}
report_checks -path_delay max -to $target -group_path_count 1 -format full_clock_expanded -fields {fanout capacitance slew input_pin net}
puts {SOURCE_CLASS retire_r -919.871277 on.code[20][37]$_DFFE_PN0P_/QN -> retire_r}
set target {}
foreach pin [all_outputs] {if {[get_full_name $pin] eq {retire_r}} {set target $pin;break}}
if {$target eq {}} {error "missing exact endpoint"}
report_checks -path_delay max -to $target -group_path_count 1 -format full_clock_expanded -fields {fanout capacitance slew input_pin net}
puts {SOURCE_CLASS reserve_r -846.425354 on.code[24][49]$_DFF_PN0_/QN -> reserve_r}
set target {}
foreach pin [all_outputs] {if {[get_full_name $pin] eq {reserve_r}} {set target $pin;break}}
if {$target eq {}} {error "missing exact endpoint"}
report_checks -path_delay max -to $target -group_path_count 1 -format full_clock_expanded -fields {fanout capacitance slew input_pin net}
puts {SOURCE_CLASS req_direction -822.409729 on.code[24][49]$_DFF_PN0_/QN -> req[336]}
set target {}
foreach pin [all_outputs] {if {[get_full_name $pin] eq {req[336]}} {set target $pin;break}}
if {$target eq {}} {error "missing exact endpoint"}
report_checks -path_delay max -to $target -group_path_count 1 -format full_clock_expanded -fields {fanout capacitance slew input_pin net}
puts {SOURCE_CLASS req_strobe -822.205322 on.code[24][49]$_DFF_PN0_/QN -> req[27]}
set target {}
foreach pin [all_outputs] {if {[get_full_name $pin] eq {req[27]}} {set target $pin;break}}
if {$target eq {}} {error "missing exact endpoint"}
report_checks -path_delay max -to $target -group_path_count 1 -format full_clock_expanded -fields {fanout capacitance slew input_pin net}
puts {SOURCE_CLASS metadata -793.70752 on.code[24][49]$_DFF_PN0_/QN -> on.code[4][14]$_DFF_PN0_/D}
set target {}
foreach pin [all_registers -data_pins] {if {[get_full_name $pin] eq {on.code[4][14]$_DFF_PN0_/D}} {set target $pin;break}}
if {$target eq {}} {error "missing exact endpoint"}
report_checks -path_delay max -to $target -group_path_count 1 -format full_clock_expanded -fields {fanout capacitance slew input_pin net}
puts {SOURCE_CLASS quiet -778.834656 on.code[24][49]$_DFF_PN0_/QN -> quiet}
set target {}
foreach pin [all_outputs] {if {[get_full_name $pin] eq {quiet}} {set target $pin;break}}
if {$target eq {}} {error "missing exact endpoint"}
report_checks -path_delay max -to $target -group_path_count 1 -format full_clock_expanded -fields {fanout capacitance slew input_pin net}
puts {SOURCE_CLASS retained -712.403381 on.code[24][49]$_DFF_PN0_/QN -> retained}
set target {}
foreach pin [all_outputs] {if {[get_full_name $pin] eq {retained}} {set target $pin;break}}
if {$target eq {}} {error "missing exact endpoint"}
report_checks -path_delay max -to $target -group_path_count 1 -format full_clock_expanded -fields {fanout capacitance slew input_pin net}
puts {SOURCE_CLASS req_tag -662.150696 on.code[7][10]$_DFF_PN0_/QN -> req[7]}
set target {}
foreach pin [all_outputs] {if {[get_full_name $pin] eq {req[7]}} {set target $pin;break}}
if {$target eq {}} {error "missing exact endpoint"}
report_checks -path_delay max -to $target -group_path_count 1 -format full_clock_expanded -fields {fanout capacitance slew input_pin net}
exit
