set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_def $::env(DEF)
foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT_nldm*.lib*] { read_liberty $f }
foreach d $::env(DRV) { create_clock -name c_$d -period 833 [get_pins $d/Y] }
set i 0
foreach p [get_pins DA*/Y] { create_clock -name cd[incr i] -period 833 $p }
source $P/openRoad/make_tracks.tcl
set_routing_layers -signal M2-M9 -clock M8-M9
set_global_routing_layer_adjustment M8 0.4
set_global_routing_layer_adjustment M9 0.4
foreach L {M2 M3 M4 M5 M6 M7} { set_global_routing_layer_adjustment $L 0.99 }
create_ndr -name CK2W2S -width {M8 0.08 M9 0.08} -spacing {M8 0.32 M9 0.32}
foreach n [get_nets n_*] { assign_ndr -ndr CK2W2S -net [get_full_name $n] }
set rc [catch {global_route -congestion_iterations 3 -allow_congestion -verbose} msg]
puts "CROP rc=$rc $msg"
write_guides $::env(DEF).guide
