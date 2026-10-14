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
if {[file exists $base/4_cts.sdc]} { read_sdc $base/4_cts.sdc } else { read_sdc $base/3_place.sdc }
set_propagated_clock [all_clocks]
source $plat/setRC.tcl
estimate_parasitics -placement
# Classify the same die-context boundary constraints as signoff, after RC is
# available. The saved CTS SDC alone can restore plain, primary-clock IO budgets.
if {[info exists ::env(OT_GATE_SIGNOFF_SDC)]} {
  set ot_pc_sdc $::env(OT_GATE_SIGNOFF_SDC)
  if {![file isfile $ot_pc_sdc]} { error "GATE_PC: missing signoff SDC $ot_pc_sdc" }
  set ::ot_ce_corner tt
  read_sdc $ot_pc_sdc
  puts "GATE_PC constraints signoff $ot_pc_sdc (TT placement RC; diagnostic)"
} else {
  puts "GATE_PC constraints saved CTS SDC (diagnostic; no signoff boundary replay)"
}

sta::worst_slack_cmd max
foreach pin {u_enable_mirror/CLK u_enable_aux_mirror/CLK} {
 set p [get_pins $pin]
 puts "SM_ACTUAL_COMMIT $pin arrival_rise=[get_property $p arrival_max_rise] arrival_fall=[get_property $p arrival_max_fall] slew_rise=[get_property $p slew_max_rise]"
}
report_checks -to [get_pins {u_enable_mirror/D u_enable_aux_mirror/D}] -path_delay max -format full_clock_expanded -fields {slew cap input fanout} -group_path_count 8 -digits 6
report_checks -to [get_pins {u_enable_mirror/D u_enable_aux_mirror/D}] -path_delay min -format full_clock_expanded -fields {slew cap input fanout} -group_path_count 8 -digits 6
report_checks -path_delay min -format full_clock_expanded -fields {slew cap input fanout} -group_path_count 5 -digits 6
puts "SM_ACTUAL_DATA_SETUP [sta::worst_slack_cmd max] HOLD [sta::worst_slack_cmd min]"
exit
