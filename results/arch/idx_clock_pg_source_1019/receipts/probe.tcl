read_db [lindex [glob /route/work/orfs/results/asap7/*/base/6_final.odb] 0]
set b [ord::get_db_block]
puts "PG_API_RULES [llength [$b getGlobalConnects]]"
foreach r [$b getGlobalConnects] {puts "PG_API_RULE [$r getInstPattern] [$r getPinPattern] [[$r getNet] getName] region=[$r getRegion] instances=[llength [$r getInsts]]"}
exit
