set co $::env(INT8_CORNER)
source /work/kit/libs_${co}.tcl
read_db /work/output/cts_checkpoint.odb
source $p/setRC.tcl
source /work/kit/constraints.sdc
set_propagated_clock [all_clocks]
estimate_parasitics -placement
report_checks -group_path_count 1
puts {SOURCE $auto$ff.cc:337:slice$26997/QN}
set qp [get_pins {$auto$ff.cc:337:slice$26997/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$26997/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27004/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27004/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27004/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27011/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27011/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27011/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27018/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27018/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27018/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27025/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27025/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27025/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27032/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27032/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27032/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27039/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27039/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27039/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27046/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27046/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27046/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27053/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27053/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27053/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27060/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27060/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27060/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27067/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27067/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27067/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27074/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27074/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27074/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27081/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27081/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27081/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27088/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27088/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27088/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27095/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27095/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27095/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27102/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27102/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27102/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27109/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27109/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27109/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27116/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27116/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27116/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27123/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27123/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27123/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27130/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27130/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27130/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27137/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27137/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27137/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27144/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27144/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27144/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27151/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27151/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27151/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27158/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27158/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27158/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27165/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27165/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27165/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27172/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27172/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27172/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27179/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27179/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27179/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27186/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27186/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27186/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27193/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27193/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27193/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27200/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27200/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27200/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27207/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27207/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27207/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27214/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27214/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27214/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27221/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27221/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27221/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27228/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27228/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27228/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27235/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27235/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27235/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27242/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27242/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27242/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27249/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27249/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27249/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27256/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27256/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27256/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27263/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27263/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27263/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27270/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27270/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27270/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27277/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27277/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27277/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27284/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27284/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27284/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27291/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27291/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27291/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27298/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27298/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27298/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27305/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27305/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27305/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27312/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27312/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27312/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27319/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27319/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27319/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27326/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27326/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27326/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27333/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27333/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27333/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27340/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27340/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27340/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27347/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27347/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27347/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27354/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27354/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27354/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27361/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27361/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27361/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27368/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27368/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27368/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27375/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27375/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27375/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27382/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27382/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27382/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27389/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27389/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27389/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27396/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27396/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27396/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27403/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27403/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27403/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27410/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27410/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27410/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27417/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27417/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27417/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27424/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27424/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27424/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27431/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27431/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27431/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27438/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27438/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27438/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27445/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27445/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27445/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27452/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27452/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27452/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27459/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27459/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27459/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27466/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27466/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27466/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27473/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27473/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27473/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27480/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27480/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27480/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27487/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27487/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27487/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27494/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27494/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27494/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27501/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27501/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27501/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27508/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27508/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27508/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27515/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27515/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27515/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27522/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27522/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27522/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27529/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27529/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27529/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27536/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27536/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27536/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27543/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27543/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27543/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27550/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27550/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27550/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27557/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27557/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27557/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27564/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27564/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27564/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27571/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27571/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27571/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27578/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27578/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27578/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27585/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27585/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27585/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27592/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27592/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27592/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27599/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27599/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27599/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27606/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27606/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27606/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27613/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27613/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27613/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27620/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27620/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27620/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27627/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27627/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27627/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27634/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27634/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27634/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27641/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27641/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27641/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27648/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27648/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27648/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27655/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27655/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27655/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27662/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27662/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27662/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27669/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27669/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27669/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27676/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27676/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27676/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27683/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27683/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27683/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27690/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27690/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27690/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27697/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27697/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27697/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27704/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27704/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27704/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27711/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27711/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27711/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27718/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27718/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27718/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27725/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27725/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27725/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27732/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27732/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27732/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27739/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27739/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27739/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27746/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27746/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27746/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27753/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27753/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27753/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27760/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27760/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27760/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27767/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27767/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27767/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27774/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27774/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27774/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27781/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27781/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27781/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27788/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27788/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27788/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27795/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27795/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27795/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27802/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27802/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27802/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27809/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27809/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27809/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27816/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27816/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27816/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27823/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27823/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27823/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27830/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27830/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27830/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27837/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27837/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27837/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27844/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27844/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27844/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27851/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27851/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27851/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27858/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27858/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27858/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27865/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27865/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27865/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27872/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27872/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27872/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27879/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27879/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27879/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27886/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27886/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27886/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27893/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27893/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27893/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27900/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27900/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27900/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27907/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27907/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27907/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27914/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27914/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27914/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27921/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27921/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27921/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27928/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27928/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27928/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27935/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27935/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27935/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27942/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27942/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27942/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27949/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27949/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27949/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27956/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27956/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27956/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27963/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27963/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27963/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27970/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27970/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27970/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27977/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27977/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27977/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27984/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27984/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27984/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27991/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27991/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27991/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$27998/QN}
set qp [get_pins {$auto$ff.cc:337:slice$27998/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$27998/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28005/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28005/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28005/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28012/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28012/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28012/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28019/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28019/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28019/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28026/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28026/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28026/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28033/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28033/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28033/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28040/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28040/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28040/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28047/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28047/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28047/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28054/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28054/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28054/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28061/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28061/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28061/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28068/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28068/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28068/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28075/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28075/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28075/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28082/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28082/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28082/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28089/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28089/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28089/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28096/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28096/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28096/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28103/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28103/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28103/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28110/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28110/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28110/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28117/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28117/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28117/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28124/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28124/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28124/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28131/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28131/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28131/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28138/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28138/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28138/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28145/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28145/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28145/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28152/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28152/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28152/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28159/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28159/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28159/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28166/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28166/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28166/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28173/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28173/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28173/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28180/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28180/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28180/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28187/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28187/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28187/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28194/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28194/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28194/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28201/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28201/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28201/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28208/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28208/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28208/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28215/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28215/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28215/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28222/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28222/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28222/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28229/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28229/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28229/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28236/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28236/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28236/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28243/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28243/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28243/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28250/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28250/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28250/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28257/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28257/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28257/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28264/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28264/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28264/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28271/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28271/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28271/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28278/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28278/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28278/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28285/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28285/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28285/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28292/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28292/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28292/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28299/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28299/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28299/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28306/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28306/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28306/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28313/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28313/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28313/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28320/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28320/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28320/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28327/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28327/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28327/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28334/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28334/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28334/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28341/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28341/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28341/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28348/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28348/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28348/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28355/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28355/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28355/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28362/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28362/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28362/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28369/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28369/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28369/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28376/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28376/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28376/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28383/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28383/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28383/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28390/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28390/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28390/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28397/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28397/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28397/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28404/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28404/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28404/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28411/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28411/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28411/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28418/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28418/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28418/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28425/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28425/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28425/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28432/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28432/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28432/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28439/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28439/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28439/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28446/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28446/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28446/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28453/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28453/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28453/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28460/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28460/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28460/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28467/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28467/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28467/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28474/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28474/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28474/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28481/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28481/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28481/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28488/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28488/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28488/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28495/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28495/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28495/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28502/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28502/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28502/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28509/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28509/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28509/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28516/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28516/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28516/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28523/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28523/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28523/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28530/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28530/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28530/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28537/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28537/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28537/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28544/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28544/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28544/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28551/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28551/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28551/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28558/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28558/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28558/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28565/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28565/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28565/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28572/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28572/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28572/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28579/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28579/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28579/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28586/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28586/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28586/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28593/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28593/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28593/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28600/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28600/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28600/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28607/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28607/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28607/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28614/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28614/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28614/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28621/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28621/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28621/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28628/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28628/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28628/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28635/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28635/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28635/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28642/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28642/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28642/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28649/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28649/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28649/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28656/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28656/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28656/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28663/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28663/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28663/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28670/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28670/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28670/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28677/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28677/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28677/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28684/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28684/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28684/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28691/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28691/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28691/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28698/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28698/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28698/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28705/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28705/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28705/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28712/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28712/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28712/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28719/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28719/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28719/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28726/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28726/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28726/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28733/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28733/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28733/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28740/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28740/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28740/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28747/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28747/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28747/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28754/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28754/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28754/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28761/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28761/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28761/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28768/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28768/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28768/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28775/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28775/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28775/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28782/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28782/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28782/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28789/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28789/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28789/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28796/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28796/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28796/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28803/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28803/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28803/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28810/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28810/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28810/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28817/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28817/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28817/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28824/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28824/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28824/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$28831/QN}
set qp [get_pins {$auto$ff.cc:337:slice$28831/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$28831/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4883/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4883/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4883/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4884/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4884/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4884/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4885/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4885/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4885/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4886/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4886/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4886/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4887/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4887/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4887/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4888/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4888/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4888/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4889/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4889/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4889/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4890/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4890/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4890/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4891/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4891/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4891/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4892/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4892/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4892/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4893/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4893/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4893/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4894/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4894/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4894/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4895/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4895/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4895/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4896/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4896/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4896/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4897/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4897/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4897/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4898/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4898/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4898/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4899/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4899/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4899/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4900/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4900/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4900/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4901/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4901/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4901/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4902/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4902/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4902/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4903/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4903/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4903/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4904/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4904/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4904/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4905/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4905/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4905/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4906/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4906/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4906/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4907/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4907/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4907/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4908/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4908/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4908/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4909/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4909/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4909/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4910/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4910/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4910/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4911/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4911/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4911/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4912/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4912/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4912/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4913/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4913/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4913/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4914/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4914/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4914/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4915/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4915/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4915/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4916/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4916/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4916/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4917/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4917/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4917/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4918/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4918/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4918/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4919/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4919/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4919/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4920/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4920/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4920/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4921/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4921/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4921/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$4922/QN}
set qp [get_pins {$auto$ff.cc:337:slice$4922/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$4922/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$5052/QN}
set qp [get_pins {$auto$ff.cc:337:slice$5052/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$5052/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$5053/QN}
set qp [get_pins {$auto$ff.cc:337:slice$5053/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$5053/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$5073/QN}
set qp [get_pins {$auto$ff.cc:337:slice$5073/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$5073/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6100/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6100/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6100/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6101/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6101/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6101/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6102/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6102/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6102/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6103/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6103/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6103/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6104/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6104/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6104/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6105/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6105/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6105/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6109/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6109/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6109/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6110/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6110/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6110/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6111/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6111/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6111/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6112/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6112/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6112/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6113/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6113/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6113/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6114/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6114/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6114/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6115/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6115/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6115/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6116/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6116/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6116/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6117/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6117/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6117/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6118/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6118/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6118/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6119/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6119/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6119/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6124/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6124/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6124/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6125/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6125/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6125/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6126/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6126/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6126/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6127/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6127/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6127/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6128/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6128/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6128/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6129/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6129/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6129/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6130/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6130/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6130/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6131/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6131/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6131/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6132/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6132/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6132/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6133/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6133/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6133/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6134/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6134/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6134/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6135/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6135/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6135/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6136/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6136/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6136/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6137/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6137/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6137/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6138/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6138/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6138/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6143/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6143/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6143/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6144/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6144/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6144/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6149/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6149/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6149/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6150/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6150/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6150/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6151/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6151/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6151/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6152/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6152/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6152/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6153/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6153/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6153/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6154/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6154/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6154/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6155/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6155/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6155/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6156/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6156/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6156/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6157/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6157/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6157/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6158/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6158/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6158/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6159/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6159/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6159/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6160/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6160/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6160/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6165/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6165/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6165/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6166/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6166/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6166/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6167/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6167/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6167/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6168/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6168/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6168/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6169/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6169/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6169/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6170/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6170/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6170/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6171/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6171/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6171/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6172/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6172/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6172/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6173/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6173/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6173/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6174/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6174/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6174/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6175/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6175/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6175/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6176/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6176/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6176/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6181/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6181/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6181/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6182/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6182/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6182/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6183/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6183/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6183/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6184/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6184/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6184/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6185/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6185/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6185/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6186/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6186/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6186/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6187/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6187/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6187/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6188/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6188/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6188/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6189/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6189/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6189/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6190/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6190/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6190/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6191/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6191/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6191/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6192/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6192/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6192/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6197/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6197/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6197/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6198/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6198/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6198/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6199/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6199/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6199/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6200/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6200/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6200/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6201/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6201/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6201/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6202/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6202/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6202/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6203/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6203/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6203/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6204/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6204/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6204/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6205/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6205/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6205/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6206/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6206/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6206/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6207/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6207/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6207/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6208/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6208/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6208/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6213/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6213/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6213/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6214/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6214/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6214/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6215/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6215/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6215/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6216/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6216/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6216/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6217/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6217/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6217/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6218/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6218/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6218/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6219/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6219/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6219/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6220/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6220/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6220/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6221/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6221/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6221/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6222/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6222/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6222/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6223/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6223/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6223/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6224/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6224/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6224/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6229/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6229/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6229/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6230/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6230/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6230/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6231/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6231/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6231/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6232/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6232/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6232/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6233/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6233/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6233/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6234/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6234/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6234/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6235/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6235/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6235/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6236/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6236/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6236/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6237/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6237/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6237/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6238/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6238/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6238/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6239/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6239/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6239/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6240/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6240/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6240/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6245/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6245/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6245/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6246/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6246/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6246/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6247/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6247/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6247/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6248/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6248/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6248/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6249/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6249/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6249/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6250/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6250/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6250/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6251/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6251/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6251/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6252/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6252/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6252/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6253/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6253/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6253/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6254/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6254/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6254/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6255/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6255/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6255/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6256/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6256/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6256/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6261/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6261/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6261/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6262/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6262/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6262/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6263/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6263/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6263/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6264/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6264/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6264/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6265/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6265/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6265/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6266/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6266/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6266/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6267/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6267/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6267/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6268/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6268/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6268/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6269/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6269/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6269/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6270/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6270/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6270/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6271/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6271/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6271/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6272/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6272/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6272/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6277/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6277/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6277/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6278/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6278/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6278/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6279/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6279/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6279/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6280/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6280/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6280/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6281/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6281/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6281/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6282/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6282/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6282/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6283/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6283/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6283/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6284/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6284/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6284/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6285/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6285/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6285/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6286/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6286/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6286/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6287/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6287/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6287/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6288/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6288/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6288/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6293/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6293/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6293/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6294/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6294/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6294/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6295/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6295/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6295/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6296/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6296/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6296/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6297/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6297/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6297/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6298/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6298/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6298/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6299/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6299/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6299/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6300/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6300/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6300/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6301/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6301/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6301/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6302/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6302/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6302/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6303/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6303/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6303/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6304/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6304/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6304/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6309/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6309/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6309/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6310/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6310/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6310/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6311/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6311/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6311/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6312/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6312/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6312/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6313/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6313/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6313/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6314/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6314/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6314/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6315/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6315/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6315/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6316/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6316/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6316/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6317/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6317/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6317/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6318/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6318/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6318/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6319/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6319/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6319/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6320/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6320/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6320/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6325/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6325/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6325/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6326/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6326/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6326/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6327/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6327/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6327/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6328/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6328/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6328/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6329/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6329/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6329/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6330/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6330/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6330/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6331/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6331/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6331/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6332/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6332/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6332/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6333/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6333/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6333/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6334/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6334/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6334/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6335/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6335/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6335/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6336/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6336/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6336/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6341/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6341/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6341/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6342/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6342/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6342/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6343/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6343/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6343/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6344/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6344/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6344/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6345/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6345/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6345/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6346/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6346/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6346/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6347/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6347/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6347/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6348/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6348/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6348/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6349/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6349/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6349/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6350/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6350/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6350/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6351/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6351/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6351/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6352/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6352/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6352/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6357/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6357/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6357/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6358/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6358/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6358/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6359/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6359/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6359/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6360/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6360/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6360/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6361/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6361/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6361/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6362/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6362/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6362/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6363/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6363/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6363/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6364/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6364/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6364/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6365/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6365/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6365/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6366/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6366/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6366/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6367/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6367/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6367/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6368/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6368/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6368/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6373/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6373/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6373/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6374/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6374/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6374/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6375/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6375/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6375/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6376/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6376/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6376/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6377/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6377/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6377/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6378/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6378/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6378/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6379/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6379/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6379/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6380/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6380/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6380/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6381/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6381/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6381/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6382/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6382/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6382/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6383/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6383/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6383/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6384/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6384/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6384/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6389/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6389/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6389/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6390/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6390/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6390/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6391/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6391/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6391/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6392/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6392/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6392/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6393/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6393/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6393/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6394/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6394/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6394/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6395/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6395/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6395/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6396/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6396/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6396/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6397/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6397/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6397/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6398/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6398/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6398/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6399/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6399/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6399/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6400/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6400/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6400/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6405/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6405/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6405/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6406/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6406/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6406/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6407/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6407/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6407/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6408/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6408/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6408/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6409/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6409/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6409/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6410/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6410/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6410/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6411/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6411/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6411/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6412/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6412/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6412/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6413/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6413/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6413/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6414/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6414/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6414/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6415/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6415/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6415/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6416/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6416/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6416/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6421/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6421/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6421/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6422/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6422/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6422/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6423/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6423/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6423/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6424/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6424/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6424/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6425/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6425/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6425/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6426/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6426/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6426/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6427/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6427/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6427/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6428/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6428/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6428/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6429/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6429/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6429/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6430/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6430/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6430/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6431/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6431/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6431/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6432/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6432/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6432/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6437/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6437/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6437/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6438/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6438/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6438/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6439/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6439/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6439/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6440/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6440/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6440/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6441/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6441/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6441/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6442/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6442/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6442/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6443/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6443/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6443/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6444/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6444/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6444/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6445/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6445/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6445/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6446/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6446/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6446/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6447/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6447/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6447/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6448/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6448/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6448/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6453/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6453/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6453/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6454/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6454/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6454/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6455/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6455/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6455/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6456/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6456/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6456/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6457/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6457/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6457/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6458/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6458/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6458/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6459/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6459/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6459/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6460/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6460/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6460/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6461/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6461/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6461/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6462/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6462/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6462/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6463/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6463/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6463/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6464/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6464/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6464/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6469/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6469/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6469/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6470/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6470/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6470/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6471/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6471/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6471/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6472/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6472/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6472/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6473/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6473/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6473/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6474/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6474/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6474/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6475/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6475/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6475/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6476/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6476/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6476/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6477/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6477/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6477/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6478/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6478/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6478/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6479/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6479/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6479/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6480/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6480/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6480/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6485/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6485/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6485/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6486/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6486/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6486/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6487/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6487/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6487/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6488/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6488/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6488/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6489/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6489/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6489/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6490/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6490/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6490/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6491/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6491/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6491/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6492/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6492/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6492/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6493/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6493/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6493/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6494/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6494/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6494/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6495/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6495/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6495/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6496/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6496/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6496/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6501/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6501/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6501/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6502/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6502/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6502/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6503/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6503/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6503/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6504/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6504/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6504/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6505/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6505/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6505/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6506/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6506/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6506/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6507/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6507/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6507/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6508/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6508/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6508/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6509/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6509/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6509/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6510/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6510/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6510/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6511/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6511/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6511/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6512/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6512/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6512/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6517/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6517/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6517/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6518/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6518/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6518/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6519/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6519/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6519/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6520/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6520/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6520/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6521/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6521/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6521/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6522/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6522/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6522/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6523/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6523/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6523/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6524/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6524/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6524/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6525/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6525/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6525/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6526/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6526/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6526/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6527/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6527/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6527/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6528/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6528/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6528/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6533/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6533/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6533/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6534/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6534/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6534/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6535/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6535/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6535/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6536/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6536/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6536/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6537/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6537/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6537/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6538/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6538/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6538/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6539/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6539/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6539/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6540/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6540/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6540/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6541/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6541/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6541/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6542/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6542/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6542/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6543/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6543/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6543/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6544/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6544/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6544/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6549/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6549/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6549/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6550/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6550/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6550/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6551/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6551/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6551/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6552/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6552/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6552/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6553/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6553/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6553/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6554/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6554/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6554/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6555/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6555/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6555/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6556/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6556/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6556/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6557/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6557/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6557/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6558/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6558/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6558/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6559/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6559/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6559/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6560/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6560/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6560/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6565/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6565/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6565/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6566/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6566/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6566/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6567/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6567/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6567/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6568/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6568/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6568/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6569/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6569/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6569/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6570/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6570/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6570/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6571/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6571/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6571/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6572/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6572/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6572/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6573/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6573/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6573/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6574/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6574/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6574/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6575/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6575/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6575/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6576/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6576/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6576/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6581/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6581/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6581/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6582/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6582/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6582/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6583/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6583/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6583/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6584/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6584/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6584/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6585/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6585/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6585/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6586/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6586/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6586/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6587/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6587/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6587/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6588/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6588/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6588/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6589/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6589/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6589/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6590/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6590/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6590/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6591/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6591/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6591/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6592/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6592/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6592/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6597/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6597/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6597/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6598/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6598/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6598/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6599/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6599/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6599/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6600/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6600/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6600/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6601/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6601/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6601/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6602/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6602/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6602/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6603/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6603/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6603/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6604/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6604/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6604/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6605/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6605/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6605/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6606/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6606/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6606/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6607/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6607/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6607/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6608/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6608/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6608/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6613/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6613/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6613/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6614/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6614/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6614/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6615/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6615/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6615/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6616/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6616/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6616/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6617/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6617/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6617/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6618/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6618/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6618/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6619/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6619/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6619/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6620/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6620/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6620/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6621/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6621/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6621/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6622/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6622/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6622/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6623/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6623/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6623/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6624/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6624/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6624/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6629/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6629/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6629/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6630/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6630/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6630/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6631/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6631/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6631/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6632/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6632/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6632/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6633/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6633/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6633/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6634/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6634/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6634/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6635/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6635/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6635/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6636/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6636/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6636/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6637/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6637/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6637/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6638/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6638/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6638/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6639/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6639/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6639/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6640/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6640/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6640/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6645/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6645/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6645/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6646/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6646/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6646/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6647/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6647/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6647/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6648/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6648/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6648/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6649/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6649/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6649/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6650/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6650/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6650/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6651/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6651/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6651/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6652/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6652/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6652/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6653/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6653/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6653/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6654/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6654/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6654/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6655/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6655/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6655/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6656/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6656/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6656/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6661/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6661/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6661/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6662/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6662/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6662/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6663/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6663/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6663/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6664/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6664/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6664/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6665/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6665/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6665/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6666/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6666/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6666/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6667/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6667/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6667/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6668/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6668/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6668/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6669/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6669/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6669/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6670/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6670/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6670/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6671/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6671/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6671/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6672/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6672/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6672/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6677/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6677/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6677/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6678/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6678/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6678/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6679/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6679/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6679/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6680/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6680/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6680/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6681/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6681/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6681/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6682/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6682/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6682/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6683/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6683/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6683/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6684/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6684/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6684/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6685/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6685/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6685/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6686/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6686/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6686/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6687/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6687/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6687/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6688/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6688/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6688/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6693/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6693/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6693/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6694/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6694/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6694/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6695/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6695/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6695/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6696/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6696/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6696/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6697/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6697/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6697/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6698/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6698/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6698/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6699/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6699/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6699/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6700/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6700/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6700/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6701/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6701/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6701/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6702/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6702/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6702/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6703/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6703/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6703/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6704/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6704/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6704/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6709/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6709/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6709/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6710/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6710/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6710/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6711/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6711/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6711/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6712/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6712/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6712/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6713/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6713/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6713/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6714/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6714/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6714/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6715/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6715/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6715/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6716/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6716/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6716/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6717/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6717/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6717/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6718/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6718/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6718/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6719/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6719/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6719/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6720/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6720/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6720/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6725/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6725/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6725/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6726/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6726/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6726/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6727/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6727/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6727/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6728/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6728/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6728/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6729/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6729/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6729/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6730/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6730/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6730/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6731/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6731/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6731/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6732/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6732/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6732/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6733/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6733/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6733/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6734/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6734/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6734/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6735/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6735/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6735/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6736/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6736/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6736/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6741/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6741/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6741/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6742/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6742/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6742/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6743/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6743/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6743/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6744/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6744/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6744/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6745/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6745/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6745/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6746/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6746/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6746/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6747/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6747/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6747/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6748/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6748/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6748/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6749/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6749/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6749/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6750/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6750/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6750/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6751/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6751/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6751/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6752/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6752/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6752/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6757/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6757/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6757/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6758/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6758/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6758/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6759/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6759/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6759/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6760/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6760/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6760/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6761/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6761/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6761/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6762/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6762/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6762/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6763/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6763/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6763/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6764/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6764/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6764/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6765/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6765/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6765/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6766/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6766/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6766/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6767/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6767/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6767/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6768/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6768/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6768/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6773/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6773/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6773/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6774/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6774/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6774/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6775/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6775/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6775/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6776/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6776/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6776/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6777/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6777/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6777/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6778/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6778/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6778/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6779/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6779/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6779/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6780/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6780/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6780/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6781/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6781/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6781/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6782/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6782/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6782/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6783/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6783/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6783/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6784/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6784/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6784/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6789/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6789/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6789/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6790/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6790/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6790/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6791/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6791/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6791/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6792/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6792/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6792/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6793/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6793/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6793/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6794/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6794/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6794/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6795/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6795/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6795/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6796/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6796/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6796/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6797/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6797/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6797/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6798/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6798/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6798/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6799/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6799/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6799/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6800/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6800/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6800/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6805/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6805/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6805/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6806/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6806/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6806/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6807/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6807/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6807/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6808/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6808/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6808/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6809/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6809/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6809/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6810/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6810/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6810/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6811/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6811/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6811/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6812/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6812/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6812/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6813/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6813/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6813/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6814/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6814/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6814/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6815/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6815/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6815/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6816/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6816/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6816/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6821/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6821/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6821/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6822/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6822/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6822/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6823/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6823/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6823/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6824/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6824/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6824/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6825/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6825/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6825/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6826/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6826/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6826/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6827/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6827/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6827/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6828/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6828/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6828/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6829/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6829/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6829/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6830/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6830/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6830/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6831/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6831/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6831/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6832/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6832/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6832/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6837/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6837/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6837/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6838/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6838/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6838/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6839/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6839/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6839/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6840/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6840/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6840/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6841/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6841/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6841/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6842/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6842/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6842/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6843/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6843/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6843/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6844/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6844/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6844/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6845/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6845/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6845/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6846/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6846/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6846/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6847/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6847/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6847/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6848/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6848/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6848/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6853/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6853/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6853/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6854/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6854/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6854/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6855/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6855/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6855/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6856/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6856/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6856/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6857/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6857/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6857/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6858/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6858/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6858/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6859/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6859/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6859/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6860/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6860/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6860/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6861/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6861/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6861/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6862/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6862/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6862/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6863/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6863/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6863/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6864/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6864/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6864/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6869/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6869/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6869/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6870/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6870/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6870/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6871/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6871/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6871/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6872/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6872/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6872/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6873/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6873/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6873/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6874/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6874/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6874/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6875/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6875/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6875/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6876/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6876/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6876/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6877/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6877/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6877/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6878/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6878/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6878/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6879/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6879/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6879/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6880/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6880/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6880/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6885/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6885/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6885/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6886/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6886/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6886/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6887/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6887/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6887/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6888/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6888/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6888/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6889/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6889/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6889/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6890/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6890/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6890/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6891/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6891/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6891/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6892/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6892/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6892/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6893/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6893/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6893/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6894/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6894/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6894/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6895/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6895/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6895/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6896/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6896/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6896/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6901/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6901/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6901/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6902/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6902/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6902/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6903/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6903/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6903/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6904/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6904/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6904/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6905/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6905/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6905/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6906/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6906/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6906/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6907/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6907/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6907/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6908/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6908/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6908/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6909/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6909/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6909/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6910/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6910/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6910/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6911/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6911/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6911/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6912/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6912/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6912/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6917/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6917/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6917/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6918/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6918/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6918/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6919/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6919/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6919/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6920/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6920/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6920/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6921/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6921/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6921/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6922/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6922/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6922/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6923/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6923/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6923/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6924/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6924/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6924/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6925/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6925/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6925/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6926/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6926/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6926/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6927/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6927/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6927/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6928/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6928/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6928/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6933/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6933/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6933/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6934/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6934/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6934/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6935/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6935/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6935/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6936/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6936/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6936/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6937/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6937/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6937/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6938/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6938/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6938/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6939/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6939/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6939/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6940/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6940/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6940/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6941/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6941/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6941/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6942/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6942/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6942/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6943/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6943/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6943/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6944/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6944/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6944/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6949/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6949/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6949/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6950/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6950/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6950/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6951/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6951/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6951/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6952/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6952/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6952/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6953/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6953/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6953/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6954/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6954/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6954/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6955/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6955/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6955/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6956/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6956/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6956/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6957/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6957/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6957/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6958/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6958/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6958/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6959/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6959/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6959/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6960/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6960/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6960/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6965/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6965/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6965/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6966/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6966/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6966/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6967/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6967/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6967/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6968/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6968/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6968/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6969/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6969/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6969/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6970/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6970/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6970/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6971/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6971/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6971/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6972/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6972/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6972/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6973/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6973/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6973/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6974/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6974/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6974/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6975/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6975/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6975/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6976/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6976/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6976/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6981/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6981/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6981/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6982/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6982/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6982/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6983/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6983/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6983/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6984/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6984/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6984/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6985/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6985/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6985/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6986/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6986/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6986/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6987/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6987/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6987/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6988/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6988/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6988/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6989/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6989/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6989/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6990/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6990/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6990/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6991/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6991/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6991/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6992/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6992/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6992/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6997/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6997/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6997/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6998/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6998/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6998/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$6999/QN}
set qp [get_pins {$auto$ff.cc:337:slice$6999/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$6999/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7000/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7000/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7000/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7001/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7001/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7001/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7002/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7002/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7002/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7003/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7003/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7003/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7004/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7004/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7004/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7005/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7005/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7005/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7006/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7006/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7006/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7007/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7007/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7007/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7008/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7008/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7008/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7013/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7013/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7013/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7014/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7014/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7014/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7015/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7015/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7015/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7016/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7016/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7016/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7017/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7017/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7017/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7018/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7018/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7018/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7019/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7019/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7019/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7020/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7020/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7020/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7021/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7021/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7021/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7022/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7022/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7022/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7023/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7023/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7023/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7024/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7024/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7024/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7029/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7029/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7029/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7030/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7030/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7030/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7031/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7031/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7031/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7032/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7032/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7032/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7033/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7033/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7033/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7034/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7034/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7034/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7035/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7035/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7035/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7036/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7036/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7036/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7037/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7037/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7037/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7038/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7038/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7038/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7039/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7039/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7039/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7040/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7040/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7040/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7045/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7045/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7045/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7046/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7046/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7046/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7047/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7047/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7047/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7048/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7048/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7048/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7049/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7049/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7049/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7050/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7050/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7050/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7051/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7051/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7051/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7052/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7052/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7052/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7053/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7053/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7053/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7054/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7054/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7054/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7055/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7055/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7055/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7056/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7056/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7056/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7061/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7061/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7061/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7062/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7062/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7062/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7063/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7063/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7063/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7064/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7064/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7064/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7065/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7065/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7065/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7066/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7066/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7066/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7067/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7067/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7067/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7068/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7068/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7068/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7069/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7069/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7069/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7070/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7070/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7070/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7071/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7071/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7071/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7072/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7072/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7072/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7077/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7077/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7077/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7078/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7078/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7078/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7079/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7079/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7079/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7080/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7080/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7080/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7081/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7081/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7081/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7082/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7082/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7082/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7083/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7083/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7083/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7084/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7084/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7084/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7085/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7085/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7085/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7086/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7086/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7086/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7087/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7087/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7087/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7088/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7088/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7088/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7093/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7093/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7093/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7094/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7094/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7094/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7095/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7095/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7095/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7096/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7096/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7096/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7097/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7097/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7097/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7098/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7098/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7098/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7099/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7099/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7099/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7100/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7100/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7100/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7101/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7101/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7101/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7102/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7102/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7102/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7103/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7103/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7103/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7104/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7104/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7104/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7109/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7109/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7109/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7110/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7110/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7110/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7111/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7111/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7111/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7112/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7112/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7112/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7113/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7113/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7113/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7114/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7114/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7114/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7115/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7115/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7115/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7116/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7116/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7116/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7117/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7117/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7117/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7118/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7118/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7118/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7119/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7119/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7119/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7120/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7120/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7120/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7125/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7125/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7125/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7126/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7126/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7126/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7127/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7127/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7127/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7128/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7128/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7128/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7129/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7129/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7129/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7130/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7130/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7130/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7131/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7131/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7131/CLK}]
puts {SOURCE $auto$ff.cc:337:slice$7132/QN}
set qp [get_pins {$auto$ff.cc:337:slice$7132/QN}]
report_net -digits 8 [get_full_name $qp]
sta::report_slews -digits 8 $qp
sta::report_slews -digits 8 [get_pins {$auto$ff.cc:337:slice$7132/CLK}]
puts {CONE 5264}
report_net -digits 8 {$abc$36464$auto$blifparse.cc:397:parse_blif$38512/Y}
sta::report_slews -digits 8 [get_pins {$abc$36464$auto$blifparse.cc:397:parse_blif$38512/Y}]
report_checks -through [get_pins {$abc$36464$auto$blifparse.cc:397:parse_blif$38512/Y}] -path_delay min -fields {slew cap input_pin nets fanout} -format full_clock_expanded -digits 8 -group_path_count 32
report_checks -through [get_pins {$abc$36464$auto$blifparse.cc:397:parse_blif$38512/Y}] -path_delay max -fields {slew cap input_pin nets fanout} -format full_clock_expanded -digits 8 -group_path_count 32
puts {CONE 5260}
report_net -digits 8 {$abc$36464$auto$blifparse.cc:397:parse_blif$38510/Y}
sta::report_slews -digits 8 [get_pins {$abc$36464$auto$blifparse.cc:397:parse_blif$38510/Y}]
report_checks -through [get_pins {$abc$36464$auto$blifparse.cc:397:parse_blif$38510/Y}] -path_delay min -fields {slew cap input_pin nets fanout} -format full_clock_expanded -digits 8 -group_path_count 32
report_checks -through [get_pins {$abc$36464$auto$blifparse.cc:397:parse_blif$38510/Y}] -path_delay max -fields {slew cap input_pin nets fanout} -format full_clock_expanded -digits 8 -group_path_count 32
puts {CONE 1665}
report_net -digits 8 {$abc$36464$auto$blifparse.cc:397:parse_blif$43300/Y}
sta::report_slews -digits 8 [get_pins {$abc$36464$auto$blifparse.cc:397:parse_blif$43300/Y}]
report_checks -through [get_pins {$abc$36464$auto$blifparse.cc:397:parse_blif$43300/Y}] -path_delay min -fields {slew cap input_pin nets fanout} -format full_clock_expanded -digits 8 -group_path_count 32
report_checks -through [get_pins {$abc$36464$auto$blifparse.cc:397:parse_blif$43300/Y}] -path_delay max -fields {slew cap input_pin nets fanout} -format full_clock_expanded -digits 8 -group_path_count 32
puts {CONE 5274}
report_net -digits 8 {$abc$36464$auto$blifparse.cc:397:parse_blif$38517/Y}
sta::report_slews -digits 8 [get_pins {$abc$36464$auto$blifparse.cc:397:parse_blif$38517/Y}]
report_checks -through [get_pins {$abc$36464$auto$blifparse.cc:397:parse_blif$38517/Y}] -path_delay min -fields {slew cap input_pin nets fanout} -format full_clock_expanded -digits 8 -group_path_count 32
report_checks -through [get_pins {$abc$36464$auto$blifparse.cc:397:parse_blif$38517/Y}] -path_delay max -fields {slew cap input_pin nets fanout} -format full_clock_expanded -digits 8 -group_path_count 32
puts {CONE 1595}
report_net -digits 8 {$abc$36464$auto$blifparse.cc:397:parse_blif$43242/Y}
sta::report_slews -digits 8 [get_pins {$abc$36464$auto$blifparse.cc:397:parse_blif$43242/Y}]
report_checks -through [get_pins {$abc$36464$auto$blifparse.cc:397:parse_blif$43242/Y}] -path_delay min -fields {slew cap input_pin nets fanout} -format full_clock_expanded -digits 8 -group_path_count 32
report_checks -through [get_pins {$abc$36464$auto$blifparse.cc:397:parse_blif$43242/Y}] -path_delay max -fields {slew cap input_pin nets fanout} -format full_clock_expanded -digits 8 -group_path_count 32
puts {CONE 2291}
report_net -digits 8 {$abc$36464$auto$blifparse.cc:397:parse_blif$36556/Y}
sta::report_slews -digits 8 [get_pins {$abc$36464$auto$blifparse.cc:397:parse_blif$36556/Y}]
report_checks -through [get_pins {$abc$36464$auto$blifparse.cc:397:parse_blif$36556/Y}] -path_delay min -fields {slew cap input_pin nets fanout} -format full_clock_expanded -digits 8 -group_path_count 32
report_checks -through [get_pins {$abc$36464$auto$blifparse.cc:397:parse_blif$36556/Y}] -path_delay max -fields {slew cap input_pin nets fanout} -format full_clock_expanded -digits 8 -group_path_count 32
puts {CONE 5268}
report_net -digits 8 {$abc$36464$auto$blifparse.cc:397:parse_blif$38514/Y}
sta::report_slews -digits 8 [get_pins {$abc$36464$auto$blifparse.cc:397:parse_blif$38514/Y}]
report_checks -through [get_pins {$abc$36464$auto$blifparse.cc:397:parse_blif$38514/Y}] -path_delay min -fields {slew cap input_pin nets fanout} -format full_clock_expanded -digits 8 -group_path_count 32
report_checks -through [get_pins {$abc$36464$auto$blifparse.cc:397:parse_blif$38514/Y}] -path_delay max -fields {slew cap input_pin nets fanout} -format full_clock_expanded -digits 8 -group_path_count 32
puts {CONE 5270}
report_net -digits 8 {$abc$36464$auto$blifparse.cc:397:parse_blif$38515/Y}
sta::report_slews -digits 8 [get_pins {$abc$36464$auto$blifparse.cc:397:parse_blif$38515/Y}]
report_checks -through [get_pins {$abc$36464$auto$blifparse.cc:397:parse_blif$38515/Y}] -path_delay min -fields {slew cap input_pin nets fanout} -format full_clock_expanded -digits 8 -group_path_count 32
report_checks -through [get_pins {$abc$36464$auto$blifparse.cc:397:parse_blif$38515/Y}] -path_delay max -fields {slew cap input_pin nets fanout} -format full_clock_expanded -digits 8 -group_path_count 32
puts {GATE_INPUT 5264 $abc$36464$auto$blifparse.cc:397:parse_blif$38512/A}
sta::report_slews -digits 8 [get_pins {$abc$36464$auto$blifparse.cc:397:parse_blif$38512/A}]
puts {GATE_INPUT 5260 $abc$36464$auto$blifparse.cc:397:parse_blif$38510/A}
sta::report_slews -digits 8 [get_pins {$abc$36464$auto$blifparse.cc:397:parse_blif$38510/A}]
puts {GATE_INPUT 1665 $abc$36464$auto$blifparse.cc:397:parse_blif$43300/A}
sta::report_slews -digits 8 [get_pins {$abc$36464$auto$blifparse.cc:397:parse_blif$43300/A}]
puts {GATE_INPUT 1665 $abc$36464$auto$blifparse.cc:397:parse_blif$43300/B}
sta::report_slews -digits 8 [get_pins {$abc$36464$auto$blifparse.cc:397:parse_blif$43300/B}]
puts {GATE_INPUT 5274 $abc$36464$auto$blifparse.cc:397:parse_blif$38517/A}
sta::report_slews -digits 8 [get_pins {$abc$36464$auto$blifparse.cc:397:parse_blif$38517/A}]
puts {GATE_INPUT 1595 $abc$36464$auto$blifparse.cc:397:parse_blif$43242/A}
sta::report_slews -digits 8 [get_pins {$abc$36464$auto$blifparse.cc:397:parse_blif$43242/A}]
puts {GATE_INPUT 1595 $abc$36464$auto$blifparse.cc:397:parse_blif$43242/B}
sta::report_slews -digits 8 [get_pins {$abc$36464$auto$blifparse.cc:397:parse_blif$43242/B}]
puts {GATE_INPUT 2291 $abc$36464$auto$blifparse.cc:397:parse_blif$36556/A}
sta::report_slews -digits 8 [get_pins {$abc$36464$auto$blifparse.cc:397:parse_blif$36556/A}]
puts {GATE_INPUT 5268 $abc$36464$auto$blifparse.cc:397:parse_blif$38514/A}
sta::report_slews -digits 8 [get_pins {$abc$36464$auto$blifparse.cc:397:parse_blif$38514/A}]
puts {GATE_INPUT 5270 $abc$36464$auto$blifparse.cc:397:parse_blif$38515/A}
sta::report_slews -digits 8 [get_pins {$abc$36464$auto$blifparse.cc:397:parse_blif$38515/A}]
puts READONLY_NO_WRITE_NO_ECO
