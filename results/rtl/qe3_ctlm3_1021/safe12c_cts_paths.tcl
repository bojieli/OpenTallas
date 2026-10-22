set base [lindex [glob /work/results/asap7/*/base] 0]
set plat /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $plat/lef/asap7_tech_1x_201209.lef
foreach f [glob $plat/lef/asap7sc7p5t_28_*_1x_220121a.lef] { catch {read_lef $f} }
foreach f [glob -nocomplain $plat/lib/NLDM/*_TT_*] { catch {read_liberty $f} }
foreach l [split [exec sh -c "grep -h 'ADDITIONAL_LEFS\\|ADDITIONAL_LIBS' /work/config.mk || true"] "\n"] {
  foreach w [lrange [split $l " ="] 1 end] {
    if {[string match *.lef $w] && [file exists $w]} { catch {read_lef $w} }
    if {[string match *.lib $w] && [file exists $w]} { catch {read_liberty $w} }
  }
}
read_db $base/4_1_cts.odb
read_sdc /sdc/signoff.sdc
set_propagated_clock [all_clocks]
source $plat/setRC.tcl
estimate_parasitics -placement
report_wns
report_tns
set fo [open /out/endpoints.txt w]
foreach p [find_timing_paths -path_delay max -group_path_count 3000 -endpoint_path_count 1 -sort_by_slack -slack_max 0] {
  set sp [get_property $p startpoint]; set ep [get_property $p endpoint]
  puts $fo "[format %.1f [expr {[get_property $p slack]*1e12}]] [get_full_name $sp] [get_full_name $ep]"
}
close $fo
report_checks -path_delay max -group_path_count 40 -endpoint_path_count 1 -fields {fanout cap slew} -format full_clock_expanded -digits 1 > /out/top40.rpt
foreach o {native_tok[12] native_pos[0]} { report_checks -path_delay max -to [get_ports $o] -fields {fanout cap slew} -digits 1 >> /out/out.rpt }
