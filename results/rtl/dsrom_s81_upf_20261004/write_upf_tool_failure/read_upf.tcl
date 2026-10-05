read_db /work/route_R4.odb
set block [ord::get_db_block]
set n_before [llength [$block getInsts]]
read_upf -file /src/physical/upf/dsrom_s81_elem.upf
write_upf /work/imported.upf
if {$n_before != [llength [$block getInsts]]} {error {intent import inserted hardware}}
puts "IMPORT supply=$dsrom_s81_upf_supply_import retained_bits=$dsrom_s81_upf_retained_bits instance_count=$n_before"
puts "DOMAINS [llength [$block getPowerDomains]]"
puts {READ_UPF_PASS}
exit
