set libdir /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f {asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz} { read_liberty $libdir/$f }
read_db /work/run/results/asap7/hbc_ot_hgi_qw_dec/base/4_cts.odb
read_sdc /work/run/results/asap7/hbc_ot_hgi_qw_dec/base/4_cts.sdc
set_propagated_clock [get_clocks clk]
set ::env(OT_VCLK_FF) 202.5
source /work/vclk_corner.tcl
ot_vclk_bind ff
source /work/setRC_rcx.tcl
estimate_parasitics -placement
set same 0; set diff 0; set fp [open /work/hp_pairs.tsv w]
foreach p [find_timing_paths -path_delay min -group_path_count 20000 -endpoint_path_count 1 -slack_max 0] {
  set sp [get_property $p startpoint]; set ep [get_property $p endpoint]
  if {[get_property $sp is_port] || [get_property $ep is_port]} continue
  set li [get_cells -of_objects $sp]; set ci [get_cells -of_objects $ep]
  set ln [get_full_name [get_nets -of_objects [get_pins -of_objects $li -filter "name==CLK"]]]
  set cn [get_full_name [get_nets -of_objects [get_pins -of_objects $ci -filter "name==CLK"]]]
  if {$ln eq $cn} {incr same} else {incr diff}
  set la [get_property [lindex [get_property $p points] 0] arrival]; set ca 0
  puts $fp "[format %.2f [get_property $p slack]]\t$ln\t$cn\t$la\t$ca\t[get_full_name $sp]\t[get_full_name $ep]"
}
close $fp
puts "HP same_leaf $same diff_leaf $diff"
report_checks -path_delay min -format full_clock_expanded -group_path_count 1
