set base [lindex [glob /work/results/asap7/*/base] 0]
set plat /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $plat/lef/asap7_tech_1x_201209.lef
read_lef $plat/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob -nocomplain /work/objects/asap7/*/base/lib/*.lib $plat/lib/NLDM/*RVT_TT*] {read_liberty $f}
read_db $base/3_place.odb
read_sdc $base/3_place.sdc
source $plat/setRC.tcl
estimate_parasitics -placement
source /src/tools/preroute_gate.tcl
puts "MESO_FIXED_IDEAL_BEFORE_CTS"
ot_preroute_dump /work/meso_fixed_preroute.json
report_checks -path_delay max -format full_clock_expanded -group_path_count 3
read_sdc /work/meso_original_clock.sdc
estimate_parasitics -placement
puts "MESO_ORIGINAL_PROPAGATED_BEFORE_CTS"
ot_preroute_dump /work/meso_original_preroute.json
report_checks -path_delay max -format full_clock_expanded -group_path_count 3
exit
