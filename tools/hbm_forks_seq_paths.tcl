set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /src/physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.lef
foreach l {asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz} { read_liberty $P/lib/NLDM/$l }
read_liberty /src/physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2_tt.lib
set B [glob /work/results/asap7/*/base]
read_db $B/4_1_cts.odb
read_sdc $B/4_cts.sdc
set_propagated_clock [all_clocks]
source $P/setRC.tcl
estimate_parasitics -placement
foreach c [all_clocks] { puts "CLK [get_name $c] [get_property $c period]" }
set ps [find_timing_paths -path_delay max -group_path_count 20000 -endpoint_path_count 1 -slack_max -50]
puts "NPATHS [llength $ps]"
foreach p $ps {
  puts "PATH [get_property $p slack] [get_full_name [get_property $p startpoint]] [get_full_name [get_property $p endpoint]]"
}
exit
