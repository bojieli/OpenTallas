set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach l {asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz} { read_liberty $P/lib/NLDM/$l }
set B [glob /work/results/asap7/*/base]
read_db $B/6_final.odb
read_sdc $B/6_final.sdc
read_spef $B/6_final.spef
set_propagated_clock [all_clocks]
foreach c [all_clocks] { puts "CLK [get_name $c] [get_property $c period]" }
set ps [find_timing_paths -path_delay max -group_path_count 20000 -endpoint_path_count 1 -slack_max -20]
puts "NPATHS [llength $ps]"
foreach p $ps { puts "PATH [get_property $p slack] [get_full_name [get_property $p startpoint]] [get_full_name [get_property $p endpoint]]" }
set ph [find_timing_paths -path_delay min -group_path_count 20000 -endpoint_path_count 1 -slack_max -5]
puts "NHOLD [llength $ph]"
foreach p $ph { puts "HOLD [get_property $p slack] [get_full_name [get_property $p startpoint]] [get_full_name [get_property $p endpoint]]" }
exit
