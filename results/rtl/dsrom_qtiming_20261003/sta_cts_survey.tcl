set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f {asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz} { read_liberty $L/$f }
read_liberty /src/physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8_ss.lib
read_db $::env(ODB)
read_sdc $::env(SDC)
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -placement
report_checks -path_delay max -group_path_count 200000 -endpoint_path_count 1 -format end -slack_max 0 > $::env(OUT).ends
report_checks -path_delay max -to [get_pins u_e.g_cg.u_cg.u_icg/ENA] -group_path_count 6 -endpoint_path_count 6 -fields {slew cap fanout} > $::env(OUT).icg
foreach s {go rst_n} { report_checks -path_delay max -from [get_ports $s] -to [get_pins u_e.g_cg.u_cg.u_icg/ENA] -format summary >> $::env(OUT).icg }
