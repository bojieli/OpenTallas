# pre_route_gate.py --cts: worst setup path classes after CTS (placement parasitics).  Run in the ORFS image with the
# case dir at /work: groups the 300 worst setup endpoints by (start kind -> end kind), kind = in (port), reg, macro,
# out (port), and prints one GATE_PC line per class with the count and the worst slack.
set base [lindex [glob /work/results/asap7/*/base] 0]
set plat /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $plat/lef/asap7_tech_1x_201209.lef
read_lef $plat/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob -nocomplain /work/objects/asap7/*/base/lib/*.lib $plat/lib/NLDM/*RVT_TT*] { catch {read_liberty $f} }
foreach l [split [exec sh -c "grep -h 'ADDITIONAL_LEFS\\|ADDITIONAL_LIBS' /work/config.mk || true"] "\n"] {
  foreach w [lrange [split $l " ="] 1 end] {
    if {[string match *.lef $w] && [file exists $w]} { catch {read_lef $w} }
    if {[string match *.lib $w] && [file exists $w]} { catch {read_liberty $w} }
  }
}
read_db $base/4_1_cts.odb
if {[file exists $base/4_cts.sdc]} { read_sdc $base/4_cts.sdc } elseif {[file exists $base/4_1_cts.sdc]} { read_sdc $base/4_1_cts.sdc } else { error "no post-CTS SDC" }
set_propagated_clock [all_clocks]
estimate_parasitics -placement

foreach c {core_clk w_fi0 vw vclk} {
  if {![llength [get_clocks -quiet $c]]} { error "missing required clock $c" }
}
puts "HEND_BOUNDARY_CLOCKS present: core_clk w_fi0 vw vclk"
foreach d {max min} {
  puts "HEND_BOUNDARY_INPUT $d"
  report_checks -from [get_ports {di0*}] -path_delay $d -format full_clock_expanded -group_path_count 3
  puts "HEND_BOUNDARY_OUTPUT $d"
  report_checks -to [get_ports {o*}] -path_delay $d -format full_clock_expanded -group_path_count 3
}
puts HEND_BOUNDARY_AUDIT_DONE
