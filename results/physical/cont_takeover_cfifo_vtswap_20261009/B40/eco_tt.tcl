read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_LVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_LVT_TT_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_LVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_LVT_TT_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_LVT_TT_nldm_211120.lib.gz
read_db /work/results/asap7/opentallas_dsfd_cfifo_asap7_s81g_s81_dsfd_cfifo_colck_a6ca75fbe_tt_srcfix/base/6_final.odb
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_L_1x_220121a.lef
read_sdc /work/results/asap7/opentallas_dsfd_cfifo_asap7_s81g_s81_dsfd_cfifo_colck_a6ca75fbe_tt_srcfix/base/6_final.sdc
read_spef /work/results/asap7/opentallas_dsfd_cfifo_asap7_s81g_s81_dsfd_cfifo_colck_a6ca75fbe_tt_srcfix/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /src/physical/s81_die_views/common/signoff_unc60.sdc
read_sdc /meas/app0_io_ref_routed.sdc
puts "OT_CORNER tt"
set MARGIN 40.0

proc ot_l {m} { regsub {_ASAP7_75t_R$} $m {_ASAP7_75t_L} }
set ot_db [ord::get_db]; set ot_block [ord::get_db_block]
set ot_ncell [llength [$ot_block getInsts]]
puts "OT_BASE_SETUP [sta::worst_slack_cmd max]"
set ot_sw [dict create]
for {set ot_it 0} {$ot_it < 6} {incr ot_it} {
  set ot_new 0
  foreach ot_p [find_timing_paths -path_delay max -slack_max $MARGIN -group_path_count 2000 -endpoint_path_count 1] {
    foreach ot_pt [get_property $ot_p points] {
      set ot_pin [get_property $ot_pt pin]
      set ot_pn [get_full_name $ot_pin]; set ot_k [string last / $ot_pn]; if {$ot_k < 1} continue; set ot_nm [string range $ot_pn 0 [expr {$ot_k - 1}]]
      set ot_in [$ot_block findInst $ot_nm]
      if {$ot_in eq "NULL"} continue
      set ot_m [[$ot_in getMaster] getName]
      if {![string match *_ASAP7_75t_R $ot_m]} continue
      if {[string match *clkbuf* [$ot_in getName]] || [string match clkload* [$ot_in getName]]} continue
      set ot_lm [$ot_db findMaster [ot_l $ot_m]]
      if {$ot_lm eq "NULL"} { puts "OT_NOLVT $ot_m"; continue }
      set ot_om [$ot_in getMaster]
      if {[$ot_om getWidth] != [$ot_lm getWidth] || [$ot_om getHeight] != [$ot_lm getHeight]} { error "footprint mismatch $ot_m" }
      $ot_in swapMaster $ot_lm
      dict set ot_sw [$ot_in getName] "$ot_m [$ot_lm getName]"
      incr ot_new
    }
  }
  puts "OT_ITER $ot_it swapped_new=$ot_new total=[dict size $ot_sw] setup=[sta::worst_slack_cmd max]"
  if {$ot_new == 0} break
}
dict for {k v} $ot_sw { puts "OT_SWAP $k $v" }
puts "OT_LVT_CELLS [dict size $ot_sw] of $ot_ncell ([expr {100.0*[dict size $ot_sw]/$ot_ncell}] %)"
set ot_ws [sta::worst_slack_cmd max]
puts "OT_ECO_SETUP $ot_ws"
report_checks -path_delay max -group_path_count 1 -format full_clock_expanded
foreach p [all_outputs] { set s [get_property $p slack_max]; if {$s ne "INF" && (![info exists wo] || $s < $wo)} { set wo $s } }
puts "OT_ECO_WS_OUT $wo"
write_db /out/6_final_vtswap.odb
write_verilog /out/6_final_vtswap.v
puts "OT_WROTE"
exit
