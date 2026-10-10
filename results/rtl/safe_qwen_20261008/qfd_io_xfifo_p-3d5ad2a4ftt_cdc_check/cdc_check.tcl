set PLAT /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $PLAT/lef/asap7_tech_1x_201209.lef
read_lef $PLAT/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach l {asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz} { read_liberty $PLAT/lib/NLDM/$l }
set base [lindex [glob /work/results/asap7/*/base] 0]
read_db $base/4_cts.odb
read_sdc $base/4_cts.sdc
set_propagated_clock [all_clocks]
read_sdc /chk/signoff.sdc
puts "OT_WS_HOLD [sta::worst_slack_cmd min]"
set cnt [dict create]; set worst [dict create]
foreach p [find_timing_paths -path_delay min -group_path_count 200000 -endpoint_path_count 1 -slack_max 0] {
  set sp [get_property $p startpoint]; set ep [get_property $p endpoint]
  set sc [get_property $p startpoint_clock]; set ec [get_property $p endpoint_clock]
  set scn [expr {$sc eq "" ? "-" : [get_full_name $sc]}]; set ecn [expr {$ec eq "" ? "-" : [get_full_name $ec]}]
  set spk [expr {[get_property $sp is_port] ? "port" : "reg"}]
  set epk [expr {[catch {get_property $ep is_port} r] ? "reg" : ($r ? "port" : "reg")}]
  set k "$scn->$ecn $spk->$epk"
  dict incr cnt $k
  set s [get_property $p slack]
  if {![dict exists $worst $k] || $s < [lindex [dict get $worst $k] 0]} { dict set worst $k [list $s [get_full_name $sp] [get_full_name $ep]] }
}
foreach k [dict keys $cnt] { puts "OT_CLASS $k n=[dict get $cnt $k] worst=[dict get $worst $k]" }
# one worst cross-clock path in full
set xp {}
foreach p [find_timing_paths -path_delay min -group_path_count 5000 -endpoint_path_count 1 -slack_max 0] {
  if {[get_property $p startpoint_clock] ne [get_property $p endpoint_clock] && [get_property $p startpoint_clock] ne ""} { set xp $p; break } }
if {$xp ne ""} { report_checks -path_delay min -from [get_property $xp startpoint] -to [get_property $xp endpoint] -format full_clock_expanded }
report_checks -path_delay min -group_path_count 1 -format full_clock_expanded
exit
