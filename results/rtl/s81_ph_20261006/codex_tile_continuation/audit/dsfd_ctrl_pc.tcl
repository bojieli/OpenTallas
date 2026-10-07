
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef

read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz

read_db /work/results/asap7/opentallas_dsfd_ctrl_pc_asap7_s81ph_s81ph_dsfd_ctrl_pc_093da5918/base/6_final.odb
read_sdc /work/results/asap7/opentallas_dsfd_ctrl_pc_asap7_s81ph_s81ph_dsfd_ctrl_pc_093da5918/base/6_final.sdc
read_spef /work/results/asap7/opentallas_dsfd_ctrl_pc_asap7_s81ph_s81ph_dsfd_ctrl_pc_093da5918/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /src/physical/s81_ph_views/common/signoff_unc60.sdc

proc outs {} {
 set d [dict create]
 foreach p [all_outputs] {set s [get_property $p slack_min]; if {$s ne "INF"} {dict set d [get_full_name $p] $s}}
 return $d
}
proc summary {name d} {
 set worst 1e9
 dict for {p s} $d {if {$s < $worst} {set worst $s}}
 puts "AUDIT $name output_worst_ps=$worst pins=[dict size $d]"
}
summary original [outs]
set oc {}; set oh {}
foreach p [all_outputs] {
 set n [get_full_name $p]
 if {[llength [get_clocks -quiet vclk_h]] && [regexp {^(k_v|k_addr|k_len|k_tag|k_we|k_wdata|k_wstrb|kr_rdy|phy_rst_n)(\[|$)} $n]} {lappend oh $p} else {lappend oc $p}
}
set_output_delay -min 101 -clock vclk $oc
set_output_delay -min 94 -clock vclk_h $oh
set new [outs]
summary new_formula $new
set_clock_latency 191 [get_clocks vclk]
set_output_delay -min -15 -clock vclk $oc
set_clock_uncertainty -hold 50 -from [get_clocks core_clk] -to [get_clocks vclk]
set_clock_latency 196 [get_clocks vclk_h]
set_output_delay -min -15 -clock vclk_h $oh
set_clock_uncertainty -hold 50 -from [get_clocks hbm_clk] -to [get_clocks vclk_h]
set explicit [outs]
summary explicit_zero_wire_FF_model $explicit
set maxdiff 0
set worstport ""
dict for {p s} $new {set diff [expr {abs($s-[dict get $explicit $p])}]; if {$diff>$maxdiff} {set maxdiff $diff;set worstport $p}}
puts "AUDIT equivalence max_abs_diff_ps=$maxdiff worstport=$worstport"
if {$maxdiff > 0.001} {exit 1}
exit
