# DIE-KV-47-HR: like-for-like placed TT STA (placement parasitics, 3_place.sdc, TT RVT libs) on a 3_place.odb
foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_TT_*.lib*] { if {![string match *FAKE* $f]} {read_liberty $f} }
read_db $::env(ODB)
read_sdc $::env(SDC)
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -placement
puts "WNS [sta::worst_slack -max]"
puts "TNS [sta::total_negative_slack -max]"
report_checks -path_delay max -group_path_count 20000 -endpoint_path_count 1 -slack_max 0 -format end -fields {} > $::env(OUT)
report_checks -path_delay max -group_path_count 3 -fields {fanout} -digits 2 > $::env(OUT).paths
