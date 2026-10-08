
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef

read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz

read_db /work/results/asap7/opentallas_ot_s81ph_root_tile_asap7_s81ph_s81ph_root_tile_77bcb3f3c/base/6_final.odb
read_sdc /work/results/asap7/opentallas_ot_s81ph_root_tile_asap7_s81ph_s81ph_root_tile_77bcb3f3c/base/6_final.sdc
read_spef /work/results/asap7/opentallas_ot_s81ph_root_tile_asap7_s81ph_s81ph_root_tile_77bcb3f3c/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /src/physical/s81_ph_views/common/signoff_unc60.sdc
set_thread_count 1
set target {}
foreach p [get_pins -hierarchical */D] {if {[get_full_name $p] eq {u_root.r2_w[13]$_DFF_P_/D}} {lappend target $p}}
if {[llength $target] != 1} {error "Target mismatch"}
puts "ROOT_A1_EDGE 13 _130070_/A1 rise"
report_checks -path_delay min -through [get_pins {_130070_/A1}] -rise_to $target -group_path_count 1 -format full_clock_expanded -fields {slew cap input_pin fanout}
puts "ROOT_A1_EDGE 13 _130070_/A1 fall"
report_checks -path_delay min -through [get_pins {_130070_/A1}] -fall_to $target -group_path_count 1 -format full_clock_expanded -fields {slew cap input_pin fanout}
set target {}
foreach p [get_pins -hierarchical */D] {if {[get_full_name $p] eq {u_root.r2_w[42]$_DFF_P_/D}} {lappend target $p}}
if {[llength $target] != 1} {error "Target mismatch"}
puts "ROOT_A1_EDGE 42 _129371_/A1 rise"
report_checks -path_delay min -through [get_pins {_129371_/A1}] -rise_to $target -group_path_count 1 -format full_clock_expanded -fields {slew cap input_pin fanout}
puts "ROOT_A1_EDGE 42 _129371_/A1 fall"
report_checks -path_delay min -through [get_pins {_129371_/A1}] -fall_to $target -group_path_count 1 -format full_clock_expanded -fields {slew cap input_pin fanout}
set target {}
foreach p [get_pins -hierarchical */D] {if {[get_full_name $p] eq {u_root.r2_w[7]$_DFF_P_/D}} {lappend target $p}}
if {[llength $target] != 1} {error "Target mismatch"}
puts "ROOT_A1_EDGE 7 _130136_/A1 rise"
report_checks -path_delay min -through [get_pins {_130136_/A1}] -rise_to $target -group_path_count 1 -format full_clock_expanded -fields {slew cap input_pin fanout}
puts "ROOT_A1_EDGE 7 _130136_/A1 fall"
report_checks -path_delay min -through [get_pins {_130136_/A1}] -fall_to $target -group_path_count 1 -format full_clock_expanded -fields {slew cap input_pin fanout}
exit
