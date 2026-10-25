# clock arrivals on the routed DB with GRT-estimated parasitics (the basis CTS/GRT hold repair and the 411.8 I used)
set C [string toupper $::env(OT_CORNER)]; set c [string tolower $C]
set B /work/run/results/asap7/kq_qfd_dv_s8x_vmr_rw60/base
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_${C}_*] { read_liberty $l }
read_liberty /work/macros/ot_sram_1r1w_1024x256_m2_r2c2_$c.lib
read_db $B/5_1_grt.odb
read_sdc /work/constraint.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set_routing_layers -signal M2-M5 -clock M2-M5
set_global_routing_layer_adjustment M2-M5 0.25
read_guides $B/route.guide
estimate_parasitics -global_routing
set_propagated_clock [all_clocks]
set f [open /work/geom/ckest_$c.tsv w]
foreach p [all_registers -clock_pins] { set a ""; catch {set a [get_property $p arrival_max_rise]}; puts $f "CK\t[get_full_name $p]\t$a" }
puts $f "HOLDWNS\t[sta::time_sta_ui [sta::worst_slack_cmd min]]\t[sta::endpoint_violation_count min]"
close $f
puts DONE
