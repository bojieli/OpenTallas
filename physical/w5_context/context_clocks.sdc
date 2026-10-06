# Scoped W5 mapped context, one root plus its real latch-low ICG descendants.
# Same Copernicus streaming/check policy; no invented full-field VM anchors.
set_units -time ps -capacitance fF
create_clock -name core_clk -period 833.333333333333 [get_ports clk]
proc w5_pin {n} {
 set p [get_pins -quiet $n]
 if {[llength $p]!=1} {error "W5 missing/ambiguous mapped pin $n"}
 return $p
}
foreach {name source target master} {
 w5_ao {u_stage.u_ao.g_checked.u_freeze.u_icg/CLK} {u_stage.u_ao.g_checked.u_freeze.u_icg/GCLK} core_clk
 w5_spine {u_stage.u_ao.u_p.u_ctl.u_spine_cg.u_icg/CLK} {u_stage.u_ao.u_p.u_ctl.u_spine_cg.u_icg/GCLK} core_clk
 w5_domain {u_stage.u_ao.u_fault_spine.u_icg/CLK} {u_stage.u_ao.u_fault_spine.u_icg/GCLK} w5_spine
 w5_loader {u_ld.g_protected.u_freeze.u_icg/CLK} {u_ld.g_protected.u_freeze.u_icg/GCLK} core_clk
} {
 create_generated_clock -name $name -master_clock $master -source [w5_pin $source] -combinational [w5_pin $target]
}
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set gates {}
set roms {}
foreach c [get_cells -hierarchical *] {
 set ref [get_property $c ref_name]
 if {$ref eq "ICGx1_ASAP7_75t_R"} {lappend gates $c}
 if {$ref eq "ot_rom_4096x274_m8"} {lappend roms $c}
}
if {[llength $gates]<8} {error "W5 actual ICG inventory missing"}
set_clock_gating_check -setup 60 -hold 25 $gates
# Ping-pong protocol: four real macros alternate, captured two edges after read.
if {[llength $roms]!=4} {error "W5 must retain four real 4096-row macros"}
set_multicycle_path -setup 2 -from $roms
set_multicycle_path -hold 1 -from $roms
# No legacy asynchronous first-stage falsepaths, quasi-static hold waiver,
# false IO paths or isolation MCP: this context derives every clock from clk.
