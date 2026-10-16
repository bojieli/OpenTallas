read_verilog /tmp/s81_clock_alias_1425.v
link_design clock_alias
create_clock -name ot_entry_0 -period 770 [get_ports ck]
create_clock -name ot_entry_1 -period 770 [get_ports ck_scalar]
foreach c [get_clocks ot_entry_*] {
 foreach p [get_property $c sources] {puts "CLOCK_ALIAS_PROBE [get_full_name $c] SOURCE=[get_full_name $p]"}
}
exit
