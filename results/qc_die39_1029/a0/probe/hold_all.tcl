# DIE-QC-39 A0: FF hold paths (all endpoints, slack <= +SMAX, up to 3 starts per endpoint) on the kept V2 cts_prehold.odb. STA user time unit here = ps (find_timing_paths -slack_max and the slack property).
# Same session setup as DIE-QC-38 ck_stage_dump.tcl (FF NLDM + macro libs, 3_place.sdc + vclk_ff.sdc, setRC_rcx, placement RC, propagated).
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
read_db $::env(ODB)
foreach f [lsort [glob $L/asap7sc7p5t_*_RVT_FF_nldm_*.lib*]] { read_liberty $f }
foreach f [glob -nocomplain /work/macros/*_ff.lib] { read_liberty $f }
read_sdc $::env(PLACE_SDC)
read_sdc /work/vclk_ff.sdc
source /work/setRC_rcx.tcl
set_propagated_clock [all_clocks]
estimate_parasitics -placement
puts "OT39_WS_MIN [expr {[sta::worst_slack_cmd min]*1e12}]"
set pes [find_timing_paths -path_delay min -group_path_count 400000 -endpoint_path_count 3 -unique_paths_to_endpoint -slack_max $::env(SMAX)]
set fh [open $::env(OUT) w]
puts $fh "slack_ps\tstartpoint\tendpoint\tstart_clock\tend_clock"
set n 0
foreach pe $pes {
  set sp [get_property $pe startpoint]; set ep [get_property $pe endpoint]
  set sc [get_property $pe startpoint_clock]; set ec [get_property $pe endpoint_clock]
  puts $fh "[format %.2f [get_property $pe slack]]\t[get_full_name $sp]\t[get_full_name $ep]\t[expr {$sc eq "" ? "-" : [get_name $sc]}]\t[expr {$ec eq "" ? "-" : [get_name $ec]}]"
  incr n
}
close $fh
puts "OT39_PATHS $n"
