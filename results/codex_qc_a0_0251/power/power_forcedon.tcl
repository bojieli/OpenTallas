foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*RVT_TT_*] {if {![string match *FAKE* $f]} {read_liberty $f}}
foreach f [glob /work/macros/*_tt.lib] {read_liberty $f}
read_db /work/run/results/asap7/kq_qfd_tile_nl_a0c_a0p10z/base/4_1_cts.odb
read_sdc /work/run/results/asap7/kq_qfd_tile_nl_a0c_a0p10z/base/4_cts.sdc
source /work/setRC_rcx.tcl
set_propagated_clock [all_clocks]
set en [get_pins {g_icg.u_icg/ENA}]
if {[llength $en] != 1} {error "missing real ICG EN power-only forcing"}
set_case_analysis 1 $en
estimate_parasitics -placement
set names [split [string trim [read [open /work/clock_cell_names.txt]]]]
set wanted [dict create];foreach n $names {dict set wanted $n 1}
set cells {};foreach c [get_cells -hierarchical *] {set i [sta::sta_to_db_inst $c];if {$i ne "NULL" && [dict exists $wanted [$i getName]]} {lappend cells $c}}
if {[llength $cells] != [llength $names]} {error "clock power missing cells [llength $cells]/[llength $names]"}
set_power_activity -global -activity 0.5 -duty 0.5
set_power_activity -input -activity 0.5 -duty 0.5
report_power -digits 8 > /work/power_busy_forcedon.rpt
report_power -instances $cells -digits 8 > /work/power_clock_forcedon.rpt
set_power_activity -global -activity 0 -duty 0.5
set_power_activity -input -activity 0 -duty 0.5
report_power -digits 8 > /work/power_floor_forcedon.rpt
puts "ACTUAL_PARENT_POWER clockcells=[llength $cells]"
