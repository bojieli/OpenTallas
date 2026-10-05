read_db /work/route_R4.odb
set block [ord::get_db_block]
set n_before [llength [$block getInsts]]
read_upf -file /src/physical/upf/dsrom_s81_elem.upf
if {$n_before != [llength [$block getInsts]]} {error {intent import inserted hardware}}
set domains [llength [$block getPowerDomains]]
set switches [llength [$block getPowerSwitches]]
if {$domains != 2 || $switches != 4} {error {power-intent census mismatch}}
puts "IMPORT supply=$dsrom_s81_upf_supply_import retained_bits=$dsrom_s81_upf_retained_bits instance_count=$n_before"
puts "DOMAINS $domains POWER_SWITCHES $switches"
puts {READ_UPF_PASS}
exit
