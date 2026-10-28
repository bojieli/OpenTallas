foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_TT_nldm_*] { read_liberty $f }
read_liberty /work/macros/ot_rom_4096x266_m8_tt.lib
read_db /base/4_cts.odb
read_sdc /base/4_cts.sdc
source /work/setRC_rcx.tcl
set_propagated_clock [all_clocks]
estimate_parasitics -placement
set s 0; set n 0; set mx -1; set mn 1e9
foreach p [get_pins -of_objects [all_registers -edge_triggered] -filter "is_clock==1"] {
  if {[get_full_name $p] eq "u_rom/clk"} continue
  set a [get_property $p arrival_max_rise]; set s [expr $s+$a]; incr n; set mx [expr max($mx,$a)]; set mn [expr min($mn,$a)]
}
puts [format "CTSM flops n %d mean %.1f min %.1f max %.1f rom %.1f" $n [expr $s/$n] $mn $mx [get_property [get_pins u_rom/clk] arrival_max_rise]]
report_checks -path_delay max -from [get_pins u_rom/clk] -format full_clock_expanded -digits 1 -group_path_count 1
report_checks -path_delay max -to [get_pins -of_objects [get_cells {u_lg.sel_c$_DFF_PN0_}] -filter "direction==input"] -format full_clock_expanded -digits 1
