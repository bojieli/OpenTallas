set c $::env(CORNER)
set lo [string tolower $c]
set P /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [glob $P/*_RVT_${c}_*] {read_liberty $f}
read_liberty /work/macros/ot_sram_1r1w_1024x256_m2_r2c2_${lo}.lib
read_db /work/prepared.odb
read_sdc /work/prepared.sdc
source /work/setRC.tcl
set_routing_layers -signal M2-M5 -clock M4-M5
# Synchronous logger capture: preserve partialroute, then fail closed BEFORE any qualified arrival extraction.
tee -variable grt_messages {global_route -congestion_iterations 50 -allow_congestion}
write_guides /work/route_${c}.guide
write_db /work/grt_${c}.odb
if {[string match *GRT-0273* $grt_messages]} {error CLOCK_NDR_FALLBACK_REFUSED}
estimate_parasitics -global_routing
set_propagated_clock [all_clocks]
set f [open /work/native_${c}.tsv w];set n 0
foreach cp [get_pins -hierarchical */CLK] {
 set arr [get_property $cp arrival_max_rise]
 if {$arr eq ""} continue
 set net [get_nets -of_objects $cp]
 puts $f "[get_full_name $cp]\t$arr\t[get_full_name $net]"
 incr n
}
close $f
write_guides /work/route_${c}.guide
write_db /work/grt_${c}.odb
report_worst_slack -max
report_worst_slack -min
puts "NATIVE_GRT_CLOCK $c sinks=$n period833 setup_unc60 hold_unc25 DIAGNOSTIC_NOT_SIGNED"
