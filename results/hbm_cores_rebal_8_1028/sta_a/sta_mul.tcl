foreach f {asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib} { read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/$f }
read_liberty /work/macros/ot_sram_1r1w_128x256_m1_r2c2_tt.lib
read_db /work/run/results/asap7/hbc_ot_hbm_su_static_pgslice_lg__lanes__canon_cf1e77/base/3_place.odb
read_sdc /out/3_place_rstio.sdc
source /work/setRC_rcx.tcl
estimate_parasitics -placement
foreach u {u_m1 u_m2 u_q u_e1m u_me2} {
  foreach st {s1_rows} {
    set ps [get_pins -hierarchical -quiet *u_lane.${u}.*${st}*/D]
    if {[llength $ps]} { set p [lindex [find_timing_paths -path_delay max -to $ps] 0]; puts "MUL $u [llength $ps] [get_property $p slack] [get_full_name [get_property $p startpoint]]" }
  }
  set ps [get_pins -hierarchical -quiet *u_lane.${u}.*/D]
  set p [lindex [find_timing_paths -path_delay max -to $ps -group_path_count 1] 0]; puts "MULALL $u [llength $ps] [get_property $p slack] [get_full_name [get_property $p endpoint]] from [get_full_name [get_property $p startpoint]]"
}
set ps [get_pins -hierarchical -quiet *u_exp*/D]; set p [lindex [find_timing_paths -path_delay max -to $ps] 0]; puts "EXP [llength $ps] [get_property $p slack] [get_full_name [get_property $p endpoint]]"
foreach pat {*u_lane.u_* *u_bank*} { set ps [get_pins -hierarchical -quiet $pat/D] }
puts "TOP20"; report_checks -path_delay max -group_path_count 40 -endpoint_path_count 1 -unique_paths_to_endpoint -format end
