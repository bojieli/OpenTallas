# DIE-KV-34: OT_EDGES v1 readout (DIE-KV-27 edges recipe) on leaf variant A GRT (in-session GRT = clk.tcl settings)
set t0 [clock seconds]
foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_$::env(CORNER)_nldm*.lib*] { read_liberty $f }
read_db /n/access/access.odb
create_clock -name dck -period 833.333 [get_ports root]
set_routing_layers -signal M4-M7 -clock M8-M9
set_global_routing_layer_adjustment M4 0.75
set_global_routing_layer_adjustment M5 0.75
set_global_routing_layer_adjustment M6 0.75
set_global_routing_layer_adjustment M7 0
set_global_routing_layer_adjustment M8 0.4
set_global_routing_layer_adjustment M9 0.4
global_route -congestion_iterations 50 -critical_nets_percentage 0 -allow_congestion -verbose
puts "OT_T grt [expr {[clock seconds]-$t0}]"
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
delete_clock [get_clocks dck]
estimate_parasitics -global_routing
create_clock -name vclk -period 833.333
set_driving_cell -lib_cell BUFx24_ASAP7_75t_R -pin Y [get_ports root]
set_input_delay 0 -clock vclk [get_ports root]
set_load 3.0 [get_ports t_*]
set_output_delay 0 -clock vclk [get_ports t_*]
# set ot_odd: verbatim line from /srv/opentallas-scratch2/claude/die-kv-27-1029/edges/read_TT.tcl (15296-cell dict, omitted here)
set fh [open /out/arr_$::env(CORNER).txt w]
puts $fh "# OT_EDGES v1 T/N=source rise F/M=source fall (late early), polarity-resolved"
foreach p [get_ports t_*] { set n [get_full_name $p]; set smx [get_property $p slack_max_rise]; set smn [get_property $p slack_min_rise]; puts $fh "T $n [expr {833.333 - $smx}] [expr {$smn}] [get_property $p slew_max_rise]" }
foreach p [get_ports t_*] { puts $fh "F [get_full_name $p] [expr {833.333 - [get_property $p slack_max_fall]}] [get_property $p slack_min_fall] [get_property $p slew_max_fall]" }
foreach i [get_cells ck_*] { set q [get_pins [get_full_name $i]/Y]; if {[dict exists $ot_odd [get_full_name $i]]} { set e fall; set g rise } else { set e rise; set g fall }; puts $fh "N [string range [get_full_name $i] 3 end] [get_property $q arrival_max_$e] [get_property $q arrival_min_$e]"; puts $fh "M [string range [get_full_name $i] 3 end] [get_property $q arrival_max_$g] [get_property $q arrival_min_$g]" }
close $fh
puts OT_COMPONENT_READOUT_DONE
