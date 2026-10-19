set co $::env(INT8_CORNER)
source /work/kit/libs_${co}.tcl
read_db /work/output/cts_checkpoint.odb
source $p/setRC.tcl
source /work/kit/constraints.sdc
set_propagated_clock [all_clocks]
estimate_parasitics -placement
report_checks -group_path_count 1
puts {SOURCE_DCALC $auto$ff.cc:337:slice$26997/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$26997/CLK}] -to [get_pins {$auto$ff.cc:337:slice$26997/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$26997/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$26997/CLK}] -to [get_pins {$auto$ff.cc:337:slice$26997/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27004/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27004/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27004/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27004/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27004/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27004/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27011/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27011/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27011/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27011/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27011/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27011/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27018/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27018/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27018/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27018/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27018/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27018/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27025/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27025/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27025/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27025/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27025/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27025/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27032/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27032/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27032/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27032/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27032/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27032/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27039/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27039/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27039/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27039/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27039/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27039/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27046/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27046/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27046/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27046/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27046/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27046/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27053/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27053/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27053/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27053/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27053/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27053/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27060/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27060/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27060/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27060/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27060/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27060/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27067/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27067/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27067/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27067/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27067/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27067/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27074/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27074/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27074/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27074/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27074/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27074/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27081/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27081/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27081/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27081/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27081/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27081/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27088/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27088/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27088/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27088/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27088/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27088/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27095/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27095/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27095/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27095/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27095/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27095/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27102/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27102/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27102/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27102/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27102/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27102/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27109/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27109/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27109/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27109/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27109/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27109/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27116/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27116/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27116/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27116/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27116/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27116/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27123/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27123/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27123/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27123/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27123/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27123/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27130/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27130/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27130/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27130/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27130/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27130/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27137/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27137/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27137/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27137/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27137/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27137/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27144/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27144/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27144/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27144/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27144/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27144/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27151/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27151/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27151/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27151/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27151/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27151/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27158/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27158/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27158/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27158/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27158/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27158/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27165/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27165/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27165/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27165/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27165/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27165/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27172/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27172/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27172/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27172/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27172/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27172/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27179/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27179/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27179/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27179/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27179/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27179/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27186/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27186/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27186/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27186/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27186/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27186/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27193/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27193/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27193/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27193/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27193/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27193/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27200/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27200/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27200/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27200/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27200/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27200/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27207/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27207/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27207/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27207/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27207/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27207/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27214/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27214/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27214/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27214/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27214/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27214/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27221/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27221/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27221/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27221/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27221/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27221/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27228/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27228/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27228/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27228/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27228/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27228/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27235/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27235/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27235/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27235/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27235/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27235/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27242/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27242/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27242/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27242/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27242/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27242/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27249/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27249/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27249/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27249/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27249/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27249/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27256/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27256/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27256/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27256/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27256/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27256/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27263/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27263/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27263/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27263/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27263/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27263/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27270/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27270/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27270/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27270/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27270/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27270/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27277/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27277/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27277/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27277/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27277/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27277/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27284/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27284/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27284/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27284/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27284/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27284/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27291/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27291/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27291/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27291/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27291/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27291/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27298/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27298/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27298/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27298/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27298/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27298/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27305/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27305/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27305/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27305/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27305/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27305/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27312/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27312/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27312/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27312/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27312/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27312/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27319/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27319/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27319/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27319/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27319/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27319/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27326/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27326/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27326/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27326/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27326/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27326/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27333/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27333/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27333/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27333/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27333/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27333/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27340/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27340/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27340/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27340/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27340/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27340/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27347/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27347/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27347/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27347/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27347/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27347/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27354/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27354/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27354/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27354/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27354/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27354/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27361/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27361/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27361/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27361/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27361/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27361/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27368/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27368/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27368/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27368/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27368/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27368/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27375/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27375/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27375/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27375/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27375/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27375/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27382/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27382/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27382/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27382/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27382/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27382/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27389/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27389/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27389/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27389/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27389/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27389/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27396/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27396/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27396/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27396/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27396/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27396/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27403/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27403/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27403/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27403/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27403/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27403/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27410/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27410/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27410/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27410/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27410/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27410/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27417/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27417/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27417/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27417/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27417/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27417/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27424/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27424/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27424/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27424/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27424/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27424/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27431/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27431/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27431/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27431/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27431/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27431/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27438/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27438/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27438/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27438/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27438/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27438/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27445/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27445/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27445/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27445/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27445/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27445/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27452/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27452/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27452/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27452/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27452/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27452/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27459/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27459/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27459/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27459/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27459/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27459/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27466/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27466/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27466/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27466/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27466/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27466/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27473/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27473/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27473/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27473/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27473/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27473/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27480/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27480/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27480/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27480/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27480/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27480/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27487/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27487/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27487/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27487/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27487/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27487/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27494/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27494/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27494/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27494/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27494/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27494/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27501/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27501/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27501/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27501/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27501/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27501/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27508/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27508/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27508/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27508/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27508/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27508/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27515/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27515/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27515/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27515/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27515/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27515/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27522/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27522/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27522/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27522/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27522/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27522/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27529/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27529/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27529/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27529/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27529/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27529/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27536/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27536/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27536/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27536/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27536/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27536/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27543/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27543/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27543/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27543/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27543/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27543/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27550/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27550/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27550/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27550/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27550/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27550/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27557/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27557/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27557/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27557/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27557/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27557/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27564/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27564/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27564/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27564/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27564/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27564/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27571/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27571/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27571/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27571/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27571/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27571/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27578/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27578/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27578/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27578/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27578/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27578/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27585/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27585/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27585/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27585/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27585/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27585/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27592/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27592/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27592/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27592/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27592/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27592/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27599/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27599/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27599/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27599/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27599/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27599/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27606/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27606/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27606/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27606/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27606/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27606/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27613/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27613/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27613/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27613/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27613/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27613/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27620/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27620/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27620/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27620/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27620/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27620/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27627/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27627/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27627/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27627/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27627/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27627/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27634/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27634/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27634/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27634/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27634/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27634/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27641/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27641/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27641/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27641/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27641/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27641/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27648/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27648/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27648/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27648/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27648/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27648/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27655/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27655/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27655/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27655/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27655/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27655/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27662/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27662/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27662/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27662/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27662/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27662/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27669/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27669/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27669/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27669/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27669/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27669/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27676/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27676/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27676/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27676/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27676/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27676/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27683/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27683/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27683/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27683/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27683/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27683/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27690/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27690/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27690/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27690/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27690/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27690/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27697/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27697/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27697/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27697/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27697/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27697/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27704/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27704/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27704/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27704/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27704/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27704/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27711/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27711/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27711/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27711/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27711/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27711/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27718/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27718/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27718/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27718/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27718/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27718/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27725/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27725/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27725/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27725/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27725/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27725/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27732/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27732/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27732/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27732/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27732/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27732/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27739/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27739/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27739/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27739/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27739/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27739/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27746/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27746/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27746/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27746/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27746/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27746/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27753/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27753/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27753/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27753/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27753/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27753/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27760/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27760/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27760/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27760/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27760/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27760/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27767/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27767/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27767/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27767/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27767/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27767/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27774/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27774/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27774/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27774/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27774/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27774/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27781/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27781/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27781/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27781/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27781/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27781/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27788/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27788/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27788/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27788/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27788/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27788/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27795/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27795/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27795/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27795/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27795/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27795/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27802/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27802/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27802/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27802/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27802/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27802/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27809/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27809/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27809/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27809/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27809/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27809/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27816/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27816/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27816/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27816/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27816/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27816/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27823/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27823/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27823/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27823/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27823/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27823/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27830/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27830/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27830/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27830/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27830/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27830/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27837/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27837/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27837/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27837/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27837/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27837/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27844/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27844/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27844/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27844/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27844/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27844/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27851/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27851/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27851/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27851/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27851/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27851/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27858/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27858/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27858/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27858/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27858/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27858/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27865/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27865/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27865/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27865/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27865/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27865/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27872/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27872/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27872/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27872/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27872/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27872/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27879/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27879/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27879/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27879/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27879/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27879/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27886/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27886/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27886/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27886/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27886/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27886/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27893/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27893/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27893/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27893/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27893/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27893/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27900/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27900/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27900/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27900/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27900/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27900/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27907/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27907/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27907/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27907/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27907/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27907/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27914/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27914/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27914/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27914/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27914/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27914/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27921/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27921/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27921/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27921/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27921/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27921/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27928/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27928/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27928/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27928/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27928/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27928/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27935/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27935/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27935/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27935/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27935/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27935/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27942/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27942/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27942/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27942/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27942/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27942/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27949/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27949/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27949/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27949/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27949/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27949/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27956/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27956/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27956/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27956/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27956/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27956/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27963/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27963/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27963/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27963/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27963/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27963/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27970/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27970/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27970/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27970/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27970/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27970/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27977/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27977/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27977/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27977/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27977/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27977/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27984/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27984/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27984/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27984/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27984/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27984/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27991/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27991/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27991/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27991/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27991/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27991/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27998/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27998/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27998/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$27998/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$27998/CLK}] -to [get_pins {$auto$ff.cc:337:slice$27998/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28005/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28005/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28005/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28005/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28005/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28005/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28012/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28012/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28012/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28012/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28012/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28012/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28019/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28019/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28019/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28019/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28019/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28019/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28026/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28026/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28026/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28026/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28026/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28026/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28033/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28033/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28033/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28033/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28033/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28033/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28040/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28040/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28040/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28040/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28040/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28040/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28047/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28047/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28047/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28047/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28047/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28047/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28054/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28054/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28054/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28054/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28054/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28054/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28061/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28061/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28061/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28061/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28061/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28061/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28068/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28068/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28068/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28068/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28068/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28068/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28075/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28075/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28075/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28075/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28075/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28075/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28082/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28082/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28082/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28082/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28082/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28082/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28089/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28089/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28089/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28089/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28089/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28089/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28096/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28096/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28096/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28096/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28096/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28096/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28103/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28103/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28103/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28103/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28103/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28103/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28110/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28110/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28110/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28110/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28110/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28110/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28117/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28117/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28117/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28117/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28117/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28117/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28124/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28124/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28124/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28124/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28124/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28124/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28131/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28131/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28131/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28131/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28131/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28131/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28138/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28138/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28138/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28138/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28138/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28138/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28145/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28145/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28145/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28145/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28145/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28145/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28152/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28152/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28152/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28152/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28152/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28152/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28159/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28159/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28159/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28159/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28159/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28159/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28166/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28166/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28166/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28166/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28166/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28166/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28173/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28173/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28173/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28173/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28173/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28173/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28180/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28180/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28180/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28180/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28180/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28180/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28187/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28187/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28187/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28187/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28187/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28187/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28194/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28194/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28194/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28194/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28194/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28194/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28201/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28201/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28201/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28201/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28201/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28201/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28208/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28208/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28208/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28208/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28208/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28208/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28215/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28215/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28215/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28215/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28215/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28215/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28222/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28222/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28222/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28222/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28222/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28222/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28229/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28229/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28229/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28229/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28229/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28229/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28236/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28236/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28236/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28236/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28236/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28236/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28243/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28243/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28243/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28243/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28243/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28243/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28250/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28250/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28250/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28250/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28250/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28250/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28257/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28257/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28257/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28257/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28257/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28257/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28264/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28264/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28264/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28264/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28264/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28264/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28271/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28271/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28271/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28271/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28271/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28271/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28278/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28278/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28278/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28278/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28278/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28278/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28285/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28285/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28285/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28285/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28285/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28285/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28292/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28292/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28292/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28292/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28292/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28292/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28299/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28299/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28299/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28299/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28299/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28299/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28306/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28306/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28306/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28306/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28306/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28306/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28313/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28313/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28313/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28313/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28313/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28313/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28320/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28320/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28320/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28320/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28320/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28320/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28327/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28327/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28327/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28327/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28327/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28327/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28334/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28334/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28334/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28334/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28334/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28334/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28341/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28341/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28341/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28341/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28341/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28341/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28348/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28348/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28348/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28348/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28348/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28348/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28355/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28355/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28355/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28355/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28355/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28355/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28362/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28362/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28362/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28362/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28362/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28362/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28369/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28369/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28369/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28369/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28369/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28369/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28376/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28376/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28376/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28376/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28376/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28376/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28383/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28383/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28383/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28383/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28383/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28383/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28390/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28390/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28390/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28390/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28390/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28390/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28397/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28397/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28397/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28397/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28397/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28397/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28404/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28404/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28404/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28404/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28404/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28404/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28411/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28411/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28411/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28411/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28411/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28411/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28418/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28418/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28418/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28418/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28418/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28418/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28425/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28425/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28425/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28425/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28425/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28425/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28432/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28432/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28432/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28432/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28432/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28432/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28439/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28439/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28439/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28439/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28439/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28439/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28446/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28446/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28446/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28446/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28446/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28446/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28453/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28453/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28453/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28453/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28453/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28453/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28460/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28460/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28460/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28460/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28460/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28460/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28467/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28467/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28467/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28467/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28467/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28467/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28474/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28474/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28474/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28474/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28474/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28474/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28481/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28481/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28481/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28481/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28481/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28481/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28488/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28488/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28488/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28488/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28488/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28488/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28495/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28495/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28495/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28495/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28495/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28495/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28502/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28502/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28502/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28502/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28502/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28502/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28509/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28509/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28509/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28509/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28509/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28509/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28516/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28516/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28516/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28516/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28516/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28516/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28523/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28523/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28523/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28523/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28523/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28523/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28530/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28530/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28530/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28530/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28530/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28530/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28537/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28537/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28537/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28537/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28537/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28537/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28544/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28544/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28544/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28544/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28544/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28544/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28551/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28551/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28551/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28551/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28551/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28551/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28558/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28558/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28558/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28558/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28558/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28558/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28565/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28565/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28565/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28565/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28565/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28565/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28572/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28572/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28572/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28572/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28572/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28572/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28579/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28579/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28579/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28579/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28579/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28579/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28586/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28586/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28586/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28586/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28586/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28586/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28593/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28593/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28593/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28593/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28593/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28593/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28600/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28600/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28600/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28600/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28600/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28600/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28607/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28607/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28607/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28607/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28607/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28607/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28614/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28614/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28614/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28614/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28614/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28614/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28621/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28621/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28621/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28621/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28621/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28621/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28628/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28628/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28628/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28628/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28628/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28628/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28635/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28635/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28635/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28635/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28635/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28635/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28642/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28642/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28642/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28642/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28642/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28642/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28649/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28649/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28649/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28649/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28649/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28649/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28656/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28656/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28656/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28656/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28656/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28656/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28663/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28663/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28663/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28663/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28663/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28663/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28670/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28670/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28670/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28670/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28670/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28670/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28677/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28677/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28677/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28677/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28677/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28677/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28684/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28684/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28684/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28684/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28684/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28684/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28691/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28691/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28691/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28691/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28691/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28691/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28698/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28698/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28698/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28698/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28698/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28698/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28705/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28705/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28705/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28705/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28705/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28705/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28712/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28712/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28712/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28712/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28712/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28712/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28719/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28719/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28719/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28719/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28719/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28719/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28726/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28726/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28726/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28726/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28726/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28726/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28733/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28733/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28733/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28733/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28733/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28733/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28740/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28740/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28740/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28740/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28740/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28740/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28747/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28747/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28747/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28747/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28747/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28747/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28754/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28754/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28754/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28754/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28754/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28754/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28761/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28761/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28761/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28761/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28761/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28761/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28768/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28768/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28768/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28768/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28768/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28768/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28775/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28775/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28775/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28775/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28775/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28775/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28782/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28782/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28782/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28782/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28782/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28782/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28789/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28789/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28789/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28789/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28789/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28789/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28796/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28796/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28796/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28796/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28796/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28796/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28803/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28803/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28803/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28803/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28803/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28803/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28810/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28810/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28810/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28810/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28810/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28810/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28817/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28817/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28817/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28817/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28817/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28817/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28824/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28824/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28824/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28824/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28824/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28824/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28831/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28831/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28831/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$28831/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$28831/CLK}] -to [get_pins {$auto$ff.cc:337:slice$28831/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4883/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4883/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4883/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4883/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4883/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4883/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4884/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4884/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4884/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4884/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4884/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4884/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4885/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4885/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4885/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4885/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4885/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4885/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4886/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4886/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4886/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4886/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4886/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4886/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4887/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4887/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4887/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4887/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4887/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4887/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4888/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4888/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4888/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4888/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4888/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4888/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4889/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4889/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4889/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4889/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4889/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4889/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4890/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4890/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4890/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4890/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4890/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4890/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4891/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4891/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4891/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4891/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4891/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4891/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4892/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4892/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4892/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4892/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4892/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4892/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4893/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4893/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4893/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4893/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4893/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4893/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4894/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4894/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4894/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4894/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4894/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4894/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4895/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4895/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4895/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4895/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4895/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4895/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4896/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4896/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4896/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4896/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4896/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4896/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4897/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4897/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4897/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4897/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4897/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4897/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4898/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4898/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4898/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4898/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4898/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4898/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4899/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4899/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4899/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4899/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4899/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4899/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4900/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4900/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4900/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4900/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4900/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4900/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4901/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4901/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4901/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4901/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4901/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4901/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4902/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4902/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4902/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4902/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4902/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4902/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4903/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4903/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4903/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4903/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4903/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4903/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4904/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4904/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4904/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4904/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4904/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4904/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4905/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4905/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4905/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4905/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4905/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4905/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4906/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4906/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4906/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4906/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4906/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4906/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4907/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4907/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4907/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4907/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4907/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4907/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4908/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4908/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4908/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4908/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4908/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4908/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4909/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4909/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4909/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4909/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4909/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4909/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4910/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4910/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4910/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4910/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4910/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4910/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4911/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4911/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4911/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4911/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4911/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4911/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4912/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4912/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4912/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4912/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4912/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4912/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4913/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4913/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4913/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4913/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4913/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4913/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4914/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4914/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4914/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4914/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4914/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4914/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4915/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4915/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4915/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4915/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4915/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4915/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4916/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4916/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4916/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4916/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4916/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4916/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4917/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4917/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4917/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4917/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4917/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4917/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4918/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4918/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4918/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4918/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4918/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4918/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4919/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4919/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4919/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4919/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4919/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4919/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4920/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4920/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4920/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4920/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4920/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4920/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4921/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4921/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4921/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4921/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4921/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4921/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4922/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4922/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4922/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$4922/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$4922/CLK}] -to [get_pins {$auto$ff.cc:337:slice$4922/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$5052/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$5052/CLK}] -to [get_pins {$auto$ff.cc:337:slice$5052/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$5052/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$5052/CLK}] -to [get_pins {$auto$ff.cc:337:slice$5052/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$5053/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$5053/CLK}] -to [get_pins {$auto$ff.cc:337:slice$5053/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$5053/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$5053/CLK}] -to [get_pins {$auto$ff.cc:337:slice$5053/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$5073/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$5073/CLK}] -to [get_pins {$auto$ff.cc:337:slice$5073/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$5073/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$5073/CLK}] -to [get_pins {$auto$ff.cc:337:slice$5073/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6100/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6100/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6100/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6100/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6100/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6100/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6101/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6101/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6101/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6101/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6101/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6101/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6102/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6102/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6102/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6102/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6102/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6102/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6103/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6103/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6103/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6103/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6103/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6103/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6104/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6104/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6104/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6104/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6104/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6104/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6105/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6105/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6105/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6105/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6105/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6105/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6109/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6109/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6109/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6109/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6109/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6109/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6110/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6110/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6110/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6110/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6110/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6110/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6111/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6111/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6111/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6111/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6111/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6111/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6112/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6112/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6112/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6112/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6112/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6112/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6113/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6113/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6113/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6113/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6113/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6113/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6114/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6114/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6114/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6114/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6114/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6114/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6115/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6115/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6115/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6115/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6115/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6115/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6116/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6116/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6116/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6116/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6116/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6116/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6117/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6117/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6117/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6117/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6117/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6117/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6118/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6118/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6118/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6118/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6118/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6118/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6119/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6119/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6119/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6119/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6119/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6119/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6124/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6124/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6124/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6124/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6124/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6124/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6125/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6125/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6125/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6125/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6125/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6125/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6126/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6126/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6126/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6126/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6126/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6126/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6127/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6127/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6127/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6127/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6127/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6127/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6128/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6128/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6128/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6128/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6128/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6128/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6129/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6129/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6129/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6129/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6129/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6129/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6130/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6130/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6130/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6130/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6130/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6130/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6131/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6131/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6131/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6131/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6131/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6131/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6132/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6132/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6132/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6132/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6132/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6132/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6133/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6133/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6133/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6133/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6133/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6133/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6134/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6134/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6134/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6134/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6134/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6134/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6135/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6135/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6135/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6135/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6135/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6135/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6136/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6136/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6136/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6136/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6136/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6136/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6137/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6137/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6137/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6137/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6137/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6137/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6138/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6138/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6138/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6138/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6138/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6138/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6143/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6143/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6143/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6143/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6143/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6143/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6144/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6144/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6144/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6144/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6144/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6144/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6149/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6149/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6149/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6149/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6149/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6149/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6150/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6150/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6150/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6150/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6150/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6150/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6151/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6151/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6151/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6151/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6151/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6151/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6152/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6152/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6152/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6152/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6152/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6152/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6153/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6153/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6153/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6153/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6153/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6153/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6154/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6154/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6154/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6154/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6154/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6154/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6155/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6155/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6155/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6155/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6155/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6155/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6156/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6156/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6156/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6156/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6156/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6156/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6157/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6157/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6157/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6157/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6157/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6157/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6158/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6158/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6158/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6158/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6158/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6158/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6159/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6159/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6159/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6159/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6159/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6159/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6160/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6160/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6160/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6160/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6160/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6160/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6165/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6165/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6165/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6165/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6165/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6165/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6166/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6166/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6166/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6166/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6166/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6166/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6167/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6167/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6167/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6167/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6167/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6167/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6168/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6168/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6168/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6168/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6168/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6168/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6169/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6169/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6169/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6169/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6169/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6169/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6170/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6170/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6170/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6170/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6170/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6170/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6171/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6171/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6171/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6171/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6171/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6171/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6172/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6172/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6172/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6172/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6172/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6172/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6173/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6173/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6173/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6173/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6173/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6173/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6174/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6174/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6174/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6174/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6174/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6174/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6175/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6175/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6175/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6175/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6175/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6175/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6176/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6176/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6176/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6176/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6176/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6176/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6181/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6181/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6181/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6181/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6181/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6181/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6182/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6182/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6182/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6182/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6182/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6182/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6183/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6183/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6183/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6183/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6183/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6183/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6184/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6184/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6184/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6184/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6184/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6184/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6185/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6185/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6185/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6185/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6185/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6185/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6186/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6186/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6186/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6186/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6186/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6186/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6187/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6187/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6187/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6187/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6187/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6187/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6188/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6188/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6188/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6188/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6188/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6188/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6189/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6189/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6189/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6189/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6189/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6189/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6190/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6190/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6190/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6190/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6190/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6190/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6191/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6191/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6191/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6191/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6191/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6191/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6192/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6192/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6192/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6192/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6192/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6192/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6197/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6197/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6197/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6197/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6197/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6197/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6198/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6198/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6198/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6198/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6198/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6198/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6199/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6199/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6199/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6199/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6199/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6199/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6200/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6200/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6200/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6200/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6200/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6200/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6201/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6201/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6201/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6201/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6201/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6201/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6202/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6202/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6202/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6202/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6202/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6202/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6203/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6203/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6203/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6203/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6203/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6203/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6204/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6204/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6204/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6204/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6204/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6204/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6205/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6205/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6205/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6205/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6205/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6205/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6206/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6206/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6206/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6206/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6206/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6206/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6207/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6207/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6207/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6207/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6207/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6207/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6208/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6208/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6208/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6208/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6208/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6208/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6213/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6213/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6213/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6213/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6213/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6213/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6214/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6214/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6214/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6214/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6214/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6214/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6215/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6215/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6215/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6215/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6215/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6215/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6216/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6216/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6216/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6216/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6216/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6216/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6217/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6217/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6217/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6217/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6217/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6217/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6218/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6218/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6218/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6218/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6218/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6218/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6219/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6219/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6219/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6219/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6219/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6219/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6220/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6220/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6220/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6220/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6220/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6220/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6221/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6221/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6221/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6221/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6221/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6221/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6222/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6222/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6222/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6222/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6222/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6222/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6223/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6223/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6223/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6223/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6223/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6223/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6224/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6224/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6224/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6224/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6224/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6224/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6229/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6229/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6229/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6229/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6229/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6229/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6230/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6230/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6230/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6230/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6230/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6230/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6231/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6231/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6231/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6231/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6231/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6231/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6232/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6232/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6232/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6232/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6232/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6232/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6233/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6233/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6233/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6233/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6233/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6233/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6234/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6234/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6234/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6234/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6234/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6234/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6235/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6235/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6235/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6235/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6235/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6235/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6236/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6236/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6236/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6236/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6236/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6236/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6237/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6237/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6237/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6237/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6237/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6237/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6238/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6238/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6238/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6238/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6238/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6238/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6239/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6239/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6239/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6239/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6239/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6239/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6240/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6240/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6240/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6240/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6240/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6240/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6245/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6245/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6245/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6245/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6245/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6245/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6246/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6246/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6246/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6246/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6246/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6246/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6247/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6247/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6247/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6247/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6247/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6247/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6248/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6248/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6248/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6248/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6248/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6248/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6249/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6249/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6249/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6249/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6249/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6249/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6250/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6250/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6250/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6250/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6250/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6250/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6251/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6251/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6251/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6251/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6251/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6251/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6252/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6252/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6252/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6252/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6252/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6252/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6253/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6253/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6253/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6253/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6253/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6253/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6254/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6254/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6254/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6254/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6254/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6254/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6255/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6255/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6255/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6255/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6255/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6255/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6256/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6256/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6256/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6256/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6256/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6256/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6261/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6261/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6261/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6261/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6261/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6261/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6262/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6262/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6262/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6262/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6262/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6262/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6263/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6263/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6263/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6263/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6263/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6263/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6264/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6264/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6264/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6264/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6264/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6264/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6265/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6265/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6265/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6265/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6265/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6265/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6266/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6266/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6266/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6266/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6266/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6266/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6267/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6267/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6267/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6267/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6267/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6267/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6268/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6268/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6268/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6268/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6268/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6268/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6269/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6269/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6269/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6269/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6269/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6269/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6270/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6270/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6270/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6270/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6270/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6270/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6271/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6271/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6271/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6271/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6271/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6271/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6272/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6272/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6272/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6272/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6272/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6272/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6277/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6277/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6277/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6277/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6277/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6277/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6278/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6278/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6278/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6278/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6278/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6278/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6279/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6279/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6279/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6279/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6279/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6279/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6280/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6280/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6280/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6280/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6280/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6280/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6281/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6281/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6281/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6281/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6281/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6281/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6282/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6282/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6282/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6282/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6282/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6282/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6283/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6283/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6283/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6283/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6283/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6283/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6284/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6284/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6284/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6284/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6284/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6284/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6285/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6285/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6285/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6285/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6285/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6285/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6286/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6286/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6286/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6286/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6286/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6286/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6287/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6287/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6287/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6287/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6287/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6287/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6288/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6288/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6288/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6288/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6288/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6288/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6293/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6293/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6293/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6293/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6293/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6293/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6294/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6294/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6294/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6294/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6294/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6294/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6295/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6295/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6295/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6295/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6295/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6295/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6296/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6296/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6296/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6296/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6296/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6296/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6297/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6297/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6297/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6297/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6297/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6297/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6298/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6298/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6298/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6298/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6298/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6298/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6299/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6299/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6299/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6299/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6299/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6299/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6300/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6300/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6300/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6300/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6300/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6300/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6301/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6301/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6301/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6301/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6301/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6301/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6302/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6302/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6302/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6302/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6302/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6302/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6303/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6303/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6303/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6303/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6303/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6303/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6304/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6304/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6304/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6304/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6304/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6304/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6309/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6309/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6309/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6309/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6309/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6309/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6310/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6310/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6310/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6310/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6310/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6310/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6311/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6311/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6311/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6311/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6311/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6311/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6312/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6312/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6312/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6312/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6312/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6312/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6313/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6313/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6313/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6313/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6313/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6313/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6314/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6314/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6314/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6314/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6314/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6314/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6315/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6315/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6315/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6315/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6315/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6315/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6316/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6316/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6316/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6316/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6316/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6316/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6317/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6317/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6317/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6317/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6317/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6317/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6318/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6318/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6318/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6318/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6318/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6318/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6319/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6319/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6319/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6319/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6319/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6319/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6320/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6320/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6320/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6320/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6320/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6320/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6325/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6325/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6325/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6325/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6325/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6325/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6326/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6326/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6326/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6326/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6326/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6326/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6327/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6327/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6327/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6327/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6327/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6327/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6328/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6328/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6328/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6328/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6328/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6328/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6329/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6329/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6329/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6329/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6329/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6329/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6330/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6330/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6330/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6330/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6330/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6330/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6331/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6331/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6331/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6331/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6331/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6331/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6332/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6332/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6332/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6332/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6332/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6332/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6333/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6333/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6333/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6333/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6333/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6333/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6334/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6334/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6334/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6334/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6334/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6334/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6335/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6335/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6335/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6335/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6335/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6335/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6336/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6336/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6336/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6336/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6336/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6336/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6341/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6341/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6341/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6341/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6341/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6341/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6342/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6342/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6342/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6342/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6342/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6342/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6343/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6343/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6343/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6343/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6343/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6343/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6344/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6344/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6344/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6344/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6344/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6344/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6345/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6345/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6345/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6345/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6345/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6345/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6346/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6346/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6346/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6346/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6346/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6346/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6347/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6347/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6347/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6347/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6347/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6347/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6348/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6348/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6348/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6348/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6348/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6348/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6349/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6349/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6349/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6349/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6349/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6349/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6350/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6350/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6350/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6350/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6350/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6350/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6351/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6351/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6351/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6351/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6351/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6351/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6352/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6352/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6352/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6352/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6352/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6352/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6357/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6357/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6357/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6357/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6357/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6357/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6358/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6358/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6358/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6358/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6358/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6358/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6359/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6359/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6359/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6359/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6359/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6359/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6360/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6360/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6360/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6360/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6360/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6360/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6361/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6361/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6361/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6361/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6361/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6361/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6362/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6362/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6362/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6362/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6362/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6362/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6363/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6363/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6363/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6363/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6363/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6363/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6364/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6364/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6364/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6364/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6364/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6364/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6365/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6365/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6365/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6365/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6365/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6365/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6366/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6366/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6366/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6366/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6366/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6366/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6367/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6367/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6367/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6367/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6367/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6367/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6368/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6368/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6368/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6368/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6368/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6368/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6373/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6373/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6373/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6373/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6373/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6373/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6374/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6374/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6374/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6374/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6374/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6374/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6375/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6375/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6375/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6375/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6375/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6375/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6376/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6376/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6376/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6376/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6376/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6376/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6377/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6377/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6377/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6377/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6377/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6377/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6378/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6378/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6378/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6378/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6378/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6378/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6379/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6379/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6379/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6379/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6379/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6379/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6380/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6380/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6380/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6380/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6380/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6380/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6381/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6381/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6381/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6381/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6381/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6381/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6382/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6382/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6382/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6382/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6382/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6382/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6383/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6383/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6383/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6383/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6383/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6383/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6384/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6384/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6384/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6384/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6384/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6384/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6389/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6389/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6389/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6389/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6389/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6389/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6390/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6390/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6390/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6390/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6390/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6390/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6391/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6391/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6391/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6391/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6391/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6391/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6392/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6392/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6392/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6392/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6392/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6392/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6393/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6393/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6393/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6393/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6393/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6393/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6394/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6394/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6394/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6394/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6394/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6394/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6395/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6395/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6395/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6395/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6395/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6395/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6396/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6396/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6396/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6396/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6396/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6396/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6397/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6397/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6397/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6397/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6397/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6397/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6398/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6398/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6398/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6398/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6398/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6398/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6399/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6399/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6399/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6399/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6399/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6399/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6400/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6400/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6400/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6400/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6400/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6400/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6405/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6405/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6405/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6405/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6405/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6405/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6406/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6406/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6406/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6406/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6406/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6406/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6407/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6407/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6407/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6407/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6407/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6407/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6408/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6408/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6408/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6408/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6408/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6408/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6409/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6409/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6409/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6409/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6409/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6409/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6410/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6410/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6410/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6410/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6410/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6410/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6411/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6411/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6411/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6411/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6411/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6411/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6412/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6412/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6412/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6412/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6412/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6412/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6413/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6413/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6413/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6413/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6413/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6413/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6414/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6414/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6414/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6414/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6414/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6414/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6415/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6415/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6415/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6415/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6415/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6415/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6416/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6416/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6416/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6416/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6416/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6416/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6421/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6421/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6421/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6421/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6421/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6421/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6422/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6422/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6422/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6422/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6422/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6422/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6423/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6423/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6423/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6423/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6423/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6423/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6424/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6424/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6424/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6424/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6424/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6424/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6425/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6425/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6425/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6425/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6425/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6425/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6426/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6426/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6426/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6426/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6426/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6426/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6427/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6427/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6427/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6427/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6427/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6427/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6428/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6428/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6428/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6428/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6428/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6428/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6429/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6429/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6429/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6429/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6429/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6429/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6430/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6430/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6430/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6430/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6430/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6430/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6431/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6431/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6431/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6431/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6431/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6431/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6432/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6432/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6432/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6432/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6432/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6432/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6437/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6437/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6437/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6437/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6437/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6437/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6438/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6438/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6438/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6438/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6438/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6438/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6439/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6439/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6439/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6439/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6439/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6439/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6440/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6440/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6440/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6440/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6440/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6440/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6441/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6441/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6441/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6441/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6441/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6441/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6442/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6442/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6442/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6442/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6442/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6442/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6443/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6443/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6443/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6443/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6443/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6443/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6444/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6444/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6444/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6444/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6444/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6444/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6445/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6445/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6445/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6445/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6445/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6445/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6446/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6446/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6446/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6446/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6446/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6446/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6447/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6447/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6447/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6447/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6447/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6447/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6448/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6448/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6448/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6448/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6448/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6448/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6453/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6453/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6453/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6453/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6453/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6453/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6454/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6454/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6454/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6454/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6454/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6454/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6455/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6455/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6455/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6455/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6455/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6455/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6456/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6456/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6456/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6456/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6456/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6456/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6457/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6457/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6457/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6457/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6457/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6457/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6458/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6458/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6458/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6458/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6458/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6458/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6459/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6459/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6459/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6459/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6459/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6459/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6460/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6460/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6460/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6460/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6460/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6460/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6461/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6461/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6461/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6461/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6461/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6461/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6462/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6462/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6462/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6462/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6462/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6462/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6463/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6463/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6463/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6463/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6463/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6463/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6464/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6464/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6464/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6464/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6464/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6464/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6469/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6469/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6469/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6469/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6469/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6469/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6470/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6470/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6470/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6470/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6470/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6470/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6471/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6471/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6471/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6471/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6471/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6471/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6472/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6472/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6472/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6472/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6472/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6472/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6473/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6473/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6473/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6473/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6473/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6473/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6474/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6474/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6474/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6474/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6474/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6474/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6475/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6475/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6475/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6475/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6475/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6475/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6476/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6476/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6476/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6476/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6476/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6476/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6477/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6477/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6477/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6477/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6477/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6477/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6478/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6478/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6478/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6478/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6478/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6478/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6479/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6479/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6479/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6479/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6479/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6479/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6480/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6480/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6480/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6480/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6480/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6480/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6485/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6485/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6485/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6485/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6485/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6485/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6486/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6486/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6486/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6486/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6486/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6486/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6487/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6487/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6487/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6487/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6487/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6487/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6488/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6488/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6488/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6488/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6488/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6488/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6489/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6489/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6489/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6489/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6489/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6489/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6490/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6490/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6490/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6490/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6490/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6490/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6491/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6491/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6491/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6491/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6491/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6491/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6492/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6492/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6492/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6492/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6492/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6492/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6493/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6493/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6493/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6493/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6493/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6493/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6494/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6494/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6494/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6494/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6494/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6494/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6495/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6495/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6495/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6495/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6495/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6495/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6496/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6496/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6496/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6496/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6496/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6496/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6501/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6501/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6501/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6501/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6501/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6501/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6502/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6502/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6502/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6502/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6502/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6502/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6503/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6503/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6503/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6503/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6503/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6503/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6504/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6504/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6504/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6504/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6504/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6504/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6505/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6505/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6505/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6505/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6505/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6505/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6506/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6506/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6506/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6506/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6506/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6506/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6507/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6507/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6507/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6507/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6507/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6507/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6508/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6508/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6508/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6508/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6508/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6508/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6509/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6509/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6509/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6509/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6509/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6509/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6510/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6510/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6510/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6510/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6510/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6510/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6511/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6511/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6511/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6511/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6511/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6511/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6512/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6512/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6512/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6512/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6512/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6512/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6517/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6517/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6517/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6517/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6517/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6517/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6518/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6518/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6518/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6518/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6518/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6518/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6519/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6519/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6519/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6519/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6519/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6519/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6520/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6520/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6520/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6520/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6520/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6520/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6521/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6521/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6521/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6521/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6521/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6521/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6522/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6522/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6522/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6522/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6522/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6522/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6523/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6523/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6523/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6523/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6523/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6523/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6524/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6524/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6524/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6524/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6524/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6524/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6525/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6525/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6525/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6525/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6525/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6525/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6526/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6526/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6526/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6526/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6526/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6526/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6527/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6527/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6527/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6527/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6527/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6527/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6528/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6528/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6528/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6528/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6528/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6528/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6533/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6533/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6533/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6533/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6533/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6533/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6534/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6534/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6534/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6534/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6534/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6534/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6535/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6535/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6535/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6535/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6535/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6535/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6536/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6536/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6536/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6536/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6536/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6536/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6537/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6537/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6537/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6537/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6537/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6537/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6538/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6538/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6538/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6538/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6538/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6538/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6539/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6539/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6539/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6539/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6539/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6539/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6540/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6540/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6540/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6540/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6540/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6540/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6541/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6541/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6541/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6541/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6541/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6541/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6542/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6542/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6542/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6542/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6542/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6542/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6543/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6543/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6543/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6543/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6543/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6543/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6544/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6544/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6544/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6544/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6544/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6544/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6549/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6549/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6549/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6549/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6549/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6549/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6550/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6550/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6550/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6550/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6550/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6550/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6551/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6551/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6551/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6551/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6551/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6551/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6552/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6552/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6552/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6552/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6552/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6552/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6553/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6553/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6553/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6553/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6553/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6553/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6554/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6554/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6554/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6554/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6554/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6554/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6555/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6555/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6555/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6555/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6555/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6555/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6556/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6556/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6556/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6556/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6556/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6556/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6557/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6557/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6557/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6557/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6557/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6557/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6558/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6558/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6558/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6558/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6558/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6558/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6559/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6559/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6559/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6559/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6559/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6559/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6560/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6560/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6560/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6560/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6560/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6560/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6565/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6565/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6565/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6565/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6565/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6565/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6566/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6566/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6566/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6566/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6566/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6566/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6567/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6567/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6567/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6567/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6567/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6567/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6568/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6568/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6568/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6568/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6568/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6568/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6569/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6569/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6569/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6569/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6569/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6569/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6570/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6570/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6570/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6570/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6570/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6570/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6571/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6571/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6571/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6571/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6571/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6571/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6572/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6572/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6572/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6572/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6572/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6572/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6573/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6573/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6573/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6573/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6573/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6573/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6574/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6574/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6574/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6574/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6574/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6574/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6575/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6575/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6575/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6575/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6575/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6575/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6576/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6576/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6576/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6576/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6576/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6576/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6581/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6581/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6581/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6581/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6581/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6581/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6582/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6582/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6582/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6582/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6582/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6582/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6583/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6583/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6583/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6583/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6583/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6583/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6584/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6584/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6584/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6584/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6584/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6584/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6585/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6585/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6585/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6585/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6585/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6585/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6586/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6586/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6586/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6586/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6586/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6586/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6587/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6587/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6587/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6587/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6587/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6587/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6588/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6588/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6588/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6588/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6588/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6588/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6589/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6589/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6589/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6589/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6589/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6589/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6590/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6590/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6590/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6590/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6590/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6590/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6591/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6591/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6591/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6591/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6591/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6591/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6592/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6592/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6592/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6592/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6592/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6592/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6597/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6597/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6597/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6597/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6597/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6597/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6598/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6598/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6598/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6598/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6598/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6598/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6599/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6599/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6599/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6599/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6599/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6599/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6600/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6600/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6600/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6600/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6600/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6600/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6601/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6601/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6601/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6601/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6601/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6601/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6602/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6602/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6602/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6602/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6602/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6602/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6603/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6603/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6603/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6603/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6603/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6603/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6604/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6604/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6604/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6604/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6604/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6604/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6605/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6605/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6605/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6605/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6605/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6605/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6606/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6606/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6606/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6606/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6606/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6606/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6607/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6607/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6607/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6607/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6607/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6607/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6608/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6608/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6608/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6608/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6608/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6608/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6613/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6613/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6613/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6613/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6613/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6613/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6614/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6614/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6614/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6614/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6614/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6614/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6615/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6615/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6615/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6615/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6615/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6615/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6616/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6616/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6616/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6616/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6616/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6616/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6617/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6617/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6617/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6617/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6617/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6617/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6618/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6618/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6618/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6618/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6618/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6618/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6619/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6619/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6619/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6619/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6619/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6619/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6620/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6620/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6620/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6620/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6620/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6620/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6621/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6621/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6621/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6621/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6621/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6621/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6622/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6622/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6622/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6622/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6622/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6622/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6623/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6623/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6623/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6623/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6623/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6623/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6624/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6624/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6624/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6624/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6624/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6624/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6629/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6629/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6629/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6629/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6629/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6629/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6630/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6630/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6630/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6630/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6630/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6630/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6631/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6631/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6631/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6631/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6631/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6631/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6632/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6632/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6632/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6632/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6632/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6632/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6633/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6633/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6633/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6633/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6633/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6633/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6634/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6634/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6634/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6634/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6634/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6634/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6635/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6635/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6635/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6635/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6635/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6635/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6636/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6636/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6636/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6636/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6636/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6636/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6637/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6637/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6637/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6637/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6637/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6637/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6638/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6638/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6638/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6638/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6638/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6638/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6639/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6639/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6639/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6639/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6639/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6639/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6640/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6640/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6640/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6640/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6640/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6640/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6645/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6645/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6645/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6645/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6645/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6645/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6646/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6646/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6646/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6646/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6646/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6646/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6647/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6647/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6647/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6647/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6647/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6647/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6648/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6648/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6648/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6648/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6648/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6648/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6649/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6649/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6649/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6649/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6649/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6649/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6650/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6650/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6650/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6650/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6650/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6650/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6651/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6651/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6651/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6651/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6651/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6651/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6652/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6652/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6652/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6652/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6652/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6652/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6653/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6653/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6653/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6653/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6653/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6653/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6654/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6654/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6654/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6654/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6654/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6654/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6655/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6655/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6655/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6655/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6655/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6655/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6656/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6656/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6656/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6656/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6656/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6656/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6661/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6661/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6661/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6661/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6661/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6661/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6662/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6662/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6662/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6662/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6662/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6662/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6663/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6663/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6663/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6663/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6663/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6663/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6664/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6664/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6664/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6664/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6664/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6664/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6665/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6665/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6665/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6665/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6665/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6665/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6666/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6666/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6666/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6666/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6666/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6666/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6667/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6667/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6667/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6667/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6667/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6667/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6668/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6668/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6668/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6668/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6668/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6668/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6669/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6669/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6669/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6669/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6669/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6669/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6670/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6670/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6670/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6670/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6670/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6670/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6671/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6671/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6671/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6671/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6671/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6671/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6672/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6672/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6672/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6672/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6672/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6672/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6677/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6677/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6677/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6677/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6677/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6677/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6678/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6678/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6678/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6678/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6678/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6678/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6679/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6679/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6679/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6679/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6679/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6679/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6680/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6680/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6680/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6680/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6680/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6680/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6681/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6681/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6681/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6681/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6681/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6681/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6682/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6682/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6682/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6682/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6682/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6682/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6683/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6683/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6683/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6683/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6683/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6683/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6684/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6684/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6684/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6684/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6684/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6684/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6685/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6685/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6685/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6685/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6685/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6685/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6686/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6686/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6686/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6686/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6686/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6686/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6687/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6687/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6687/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6687/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6687/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6687/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6688/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6688/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6688/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6688/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6688/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6688/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6693/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6693/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6693/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6693/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6693/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6693/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6694/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6694/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6694/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6694/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6694/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6694/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6695/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6695/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6695/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6695/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6695/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6695/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6696/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6696/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6696/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6696/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6696/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6696/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6697/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6697/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6697/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6697/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6697/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6697/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6698/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6698/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6698/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6698/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6698/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6698/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6699/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6699/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6699/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6699/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6699/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6699/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6700/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6700/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6700/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6700/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6700/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6700/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6701/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6701/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6701/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6701/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6701/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6701/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6702/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6702/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6702/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6702/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6702/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6702/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6703/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6703/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6703/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6703/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6703/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6703/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6704/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6704/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6704/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6704/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6704/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6704/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6709/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6709/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6709/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6709/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6709/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6709/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6710/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6710/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6710/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6710/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6710/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6710/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6711/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6711/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6711/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6711/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6711/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6711/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6712/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6712/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6712/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6712/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6712/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6712/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6713/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6713/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6713/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6713/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6713/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6713/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6714/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6714/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6714/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6714/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6714/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6714/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6715/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6715/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6715/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6715/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6715/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6715/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6716/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6716/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6716/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6716/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6716/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6716/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6717/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6717/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6717/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6717/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6717/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6717/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6718/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6718/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6718/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6718/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6718/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6718/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6719/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6719/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6719/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6719/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6719/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6719/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6720/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6720/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6720/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6720/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6720/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6720/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6725/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6725/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6725/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6725/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6725/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6725/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6726/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6726/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6726/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6726/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6726/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6726/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6727/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6727/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6727/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6727/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6727/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6727/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6728/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6728/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6728/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6728/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6728/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6728/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6729/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6729/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6729/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6729/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6729/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6729/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6730/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6730/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6730/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6730/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6730/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6730/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6731/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6731/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6731/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6731/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6731/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6731/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6732/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6732/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6732/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6732/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6732/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6732/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6733/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6733/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6733/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6733/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6733/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6733/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6734/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6734/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6734/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6734/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6734/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6734/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6735/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6735/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6735/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6735/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6735/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6735/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6736/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6736/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6736/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6736/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6736/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6736/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6741/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6741/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6741/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6741/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6741/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6741/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6742/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6742/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6742/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6742/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6742/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6742/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6743/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6743/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6743/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6743/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6743/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6743/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6744/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6744/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6744/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6744/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6744/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6744/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6745/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6745/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6745/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6745/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6745/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6745/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6746/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6746/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6746/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6746/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6746/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6746/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6747/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6747/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6747/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6747/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6747/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6747/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6748/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6748/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6748/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6748/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6748/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6748/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6749/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6749/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6749/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6749/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6749/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6749/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6750/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6750/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6750/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6750/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6750/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6750/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6751/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6751/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6751/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6751/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6751/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6751/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6752/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6752/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6752/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6752/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6752/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6752/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6757/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6757/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6757/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6757/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6757/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6757/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6758/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6758/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6758/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6758/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6758/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6758/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6759/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6759/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6759/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6759/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6759/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6759/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6760/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6760/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6760/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6760/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6760/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6760/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6761/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6761/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6761/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6761/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6761/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6761/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6762/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6762/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6762/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6762/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6762/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6762/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6763/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6763/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6763/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6763/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6763/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6763/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6764/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6764/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6764/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6764/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6764/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6764/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6765/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6765/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6765/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6765/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6765/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6765/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6766/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6766/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6766/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6766/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6766/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6766/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6767/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6767/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6767/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6767/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6767/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6767/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6768/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6768/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6768/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6768/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6768/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6768/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6773/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6773/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6773/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6773/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6773/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6773/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6774/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6774/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6774/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6774/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6774/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6774/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6775/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6775/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6775/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6775/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6775/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6775/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6776/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6776/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6776/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6776/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6776/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6776/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6777/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6777/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6777/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6777/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6777/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6777/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6778/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6778/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6778/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6778/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6778/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6778/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6779/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6779/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6779/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6779/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6779/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6779/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6780/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6780/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6780/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6780/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6780/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6780/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6781/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6781/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6781/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6781/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6781/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6781/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6782/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6782/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6782/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6782/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6782/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6782/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6783/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6783/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6783/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6783/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6783/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6783/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6784/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6784/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6784/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6784/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6784/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6784/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6789/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6789/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6789/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6789/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6789/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6789/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6790/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6790/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6790/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6790/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6790/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6790/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6791/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6791/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6791/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6791/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6791/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6791/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6792/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6792/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6792/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6792/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6792/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6792/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6793/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6793/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6793/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6793/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6793/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6793/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6794/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6794/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6794/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6794/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6794/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6794/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6795/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6795/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6795/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6795/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6795/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6795/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6796/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6796/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6796/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6796/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6796/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6796/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6797/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6797/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6797/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6797/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6797/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6797/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6798/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6798/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6798/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6798/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6798/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6798/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6799/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6799/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6799/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6799/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6799/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6799/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6800/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6800/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6800/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6800/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6800/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6800/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6805/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6805/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6805/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6805/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6805/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6805/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6806/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6806/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6806/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6806/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6806/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6806/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6807/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6807/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6807/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6807/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6807/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6807/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6808/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6808/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6808/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6808/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6808/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6808/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6809/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6809/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6809/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6809/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6809/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6809/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6810/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6810/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6810/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6810/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6810/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6810/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6811/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6811/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6811/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6811/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6811/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6811/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6812/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6812/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6812/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6812/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6812/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6812/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6813/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6813/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6813/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6813/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6813/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6813/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6814/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6814/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6814/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6814/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6814/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6814/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6815/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6815/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6815/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6815/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6815/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6815/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6816/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6816/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6816/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6816/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6816/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6816/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6821/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6821/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6821/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6821/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6821/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6821/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6822/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6822/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6822/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6822/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6822/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6822/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6823/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6823/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6823/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6823/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6823/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6823/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6824/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6824/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6824/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6824/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6824/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6824/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6825/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6825/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6825/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6825/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6825/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6825/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6826/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6826/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6826/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6826/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6826/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6826/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6827/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6827/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6827/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6827/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6827/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6827/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6828/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6828/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6828/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6828/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6828/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6828/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6829/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6829/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6829/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6829/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6829/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6829/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6830/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6830/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6830/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6830/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6830/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6830/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6831/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6831/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6831/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6831/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6831/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6831/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6832/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6832/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6832/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6832/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6832/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6832/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6837/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6837/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6837/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6837/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6837/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6837/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6838/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6838/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6838/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6838/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6838/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6838/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6839/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6839/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6839/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6839/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6839/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6839/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6840/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6840/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6840/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6840/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6840/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6840/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6841/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6841/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6841/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6841/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6841/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6841/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6842/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6842/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6842/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6842/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6842/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6842/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6843/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6843/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6843/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6843/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6843/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6843/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6844/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6844/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6844/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6844/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6844/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6844/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6845/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6845/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6845/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6845/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6845/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6845/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6846/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6846/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6846/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6846/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6846/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6846/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6847/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6847/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6847/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6847/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6847/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6847/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6848/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6848/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6848/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6848/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6848/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6848/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6853/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6853/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6853/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6853/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6853/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6853/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6854/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6854/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6854/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6854/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6854/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6854/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6855/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6855/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6855/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6855/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6855/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6855/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6856/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6856/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6856/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6856/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6856/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6856/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6857/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6857/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6857/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6857/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6857/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6857/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6858/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6858/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6858/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6858/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6858/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6858/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6859/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6859/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6859/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6859/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6859/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6859/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6860/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6860/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6860/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6860/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6860/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6860/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6861/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6861/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6861/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6861/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6861/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6861/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6862/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6862/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6862/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6862/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6862/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6862/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6863/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6863/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6863/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6863/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6863/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6863/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6864/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6864/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6864/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6864/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6864/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6864/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6869/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6869/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6869/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6869/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6869/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6869/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6870/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6870/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6870/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6870/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6870/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6870/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6871/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6871/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6871/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6871/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6871/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6871/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6872/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6872/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6872/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6872/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6872/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6872/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6873/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6873/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6873/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6873/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6873/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6873/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6874/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6874/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6874/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6874/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6874/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6874/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6875/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6875/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6875/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6875/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6875/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6875/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6876/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6876/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6876/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6876/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6876/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6876/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6877/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6877/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6877/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6877/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6877/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6877/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6878/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6878/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6878/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6878/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6878/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6878/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6879/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6879/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6879/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6879/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6879/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6879/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6880/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6880/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6880/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6880/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6880/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6880/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6885/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6885/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6885/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6885/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6885/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6885/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6886/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6886/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6886/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6886/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6886/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6886/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6887/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6887/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6887/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6887/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6887/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6887/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6888/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6888/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6888/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6888/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6888/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6888/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6889/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6889/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6889/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6889/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6889/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6889/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6890/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6890/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6890/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6890/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6890/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6890/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6891/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6891/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6891/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6891/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6891/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6891/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6892/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6892/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6892/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6892/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6892/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6892/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6893/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6893/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6893/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6893/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6893/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6893/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6894/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6894/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6894/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6894/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6894/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6894/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6895/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6895/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6895/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6895/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6895/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6895/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6896/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6896/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6896/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6896/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6896/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6896/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6901/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6901/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6901/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6901/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6901/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6901/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6902/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6902/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6902/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6902/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6902/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6902/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6903/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6903/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6903/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6903/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6903/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6903/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6904/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6904/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6904/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6904/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6904/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6904/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6905/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6905/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6905/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6905/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6905/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6905/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6906/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6906/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6906/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6906/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6906/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6906/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6907/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6907/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6907/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6907/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6907/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6907/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6908/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6908/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6908/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6908/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6908/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6908/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6909/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6909/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6909/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6909/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6909/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6909/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6910/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6910/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6910/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6910/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6910/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6910/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6911/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6911/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6911/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6911/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6911/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6911/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6912/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6912/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6912/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6912/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6912/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6912/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6917/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6917/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6917/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6917/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6917/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6917/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6918/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6918/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6918/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6918/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6918/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6918/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6919/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6919/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6919/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6919/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6919/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6919/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6920/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6920/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6920/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6920/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6920/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6920/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6921/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6921/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6921/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6921/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6921/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6921/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6922/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6922/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6922/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6922/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6922/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6922/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6923/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6923/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6923/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6923/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6923/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6923/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6924/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6924/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6924/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6924/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6924/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6924/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6925/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6925/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6925/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6925/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6925/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6925/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6926/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6926/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6926/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6926/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6926/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6926/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6927/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6927/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6927/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6927/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6927/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6927/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6928/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6928/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6928/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6928/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6928/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6928/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6933/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6933/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6933/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6933/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6933/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6933/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6934/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6934/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6934/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6934/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6934/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6934/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6935/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6935/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6935/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6935/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6935/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6935/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6936/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6936/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6936/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6936/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6936/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6936/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6937/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6937/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6937/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6937/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6937/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6937/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6938/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6938/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6938/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6938/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6938/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6938/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6939/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6939/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6939/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6939/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6939/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6939/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6940/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6940/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6940/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6940/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6940/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6940/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6941/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6941/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6941/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6941/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6941/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6941/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6942/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6942/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6942/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6942/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6942/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6942/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6943/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6943/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6943/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6943/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6943/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6943/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6944/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6944/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6944/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6944/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6944/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6944/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6949/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6949/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6949/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6949/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6949/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6949/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6950/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6950/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6950/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6950/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6950/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6950/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6951/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6951/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6951/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6951/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6951/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6951/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6952/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6952/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6952/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6952/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6952/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6952/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6953/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6953/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6953/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6953/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6953/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6953/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6954/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6954/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6954/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6954/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6954/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6954/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6955/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6955/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6955/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6955/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6955/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6955/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6956/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6956/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6956/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6956/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6956/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6956/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6957/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6957/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6957/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6957/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6957/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6957/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6958/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6958/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6958/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6958/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6958/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6958/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6959/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6959/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6959/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6959/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6959/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6959/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6960/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6960/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6960/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6960/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6960/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6960/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6965/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6965/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6965/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6965/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6965/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6965/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6966/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6966/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6966/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6966/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6966/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6966/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6967/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6967/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6967/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6967/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6967/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6967/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6968/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6968/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6968/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6968/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6968/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6968/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6969/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6969/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6969/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6969/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6969/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6969/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6970/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6970/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6970/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6970/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6970/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6970/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6971/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6971/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6971/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6971/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6971/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6971/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6972/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6972/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6972/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6972/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6972/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6972/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6973/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6973/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6973/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6973/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6973/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6973/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6974/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6974/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6974/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6974/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6974/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6974/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6975/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6975/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6975/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6975/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6975/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6975/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6976/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6976/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6976/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6976/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6976/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6976/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6981/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6981/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6981/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6981/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6981/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6981/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6982/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6982/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6982/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6982/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6982/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6982/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6983/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6983/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6983/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6983/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6983/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6983/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6984/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6984/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6984/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6984/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6984/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6984/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6985/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6985/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6985/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6985/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6985/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6985/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6986/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6986/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6986/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6986/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6986/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6986/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6987/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6987/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6987/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6987/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6987/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6987/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6988/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6988/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6988/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6988/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6988/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6988/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6989/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6989/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6989/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6989/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6989/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6989/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6990/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6990/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6990/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6990/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6990/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6990/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6991/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6991/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6991/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6991/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6991/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6991/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6992/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6992/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6992/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6992/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6992/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6992/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6997/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6997/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6997/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6997/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6997/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6997/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6998/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6998/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6998/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6998/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6998/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6998/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6999/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6999/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6999/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$6999/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$6999/CLK}] -to [get_pins {$auto$ff.cc:337:slice$6999/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7000/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7000/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7000/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7000/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7000/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7000/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7001/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7001/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7001/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7001/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7001/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7001/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7002/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7002/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7002/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7002/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7002/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7002/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7003/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7003/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7003/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7003/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7003/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7003/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7004/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7004/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7004/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7004/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7004/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7004/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7005/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7005/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7005/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7005/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7005/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7005/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7006/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7006/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7006/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7006/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7006/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7006/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7007/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7007/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7007/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7007/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7007/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7007/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7008/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7008/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7008/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7008/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7008/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7008/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7013/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7013/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7013/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7013/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7013/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7013/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7014/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7014/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7014/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7014/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7014/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7014/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7015/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7015/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7015/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7015/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7015/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7015/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7016/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7016/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7016/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7016/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7016/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7016/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7017/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7017/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7017/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7017/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7017/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7017/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7018/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7018/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7018/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7018/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7018/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7018/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7019/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7019/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7019/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7019/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7019/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7019/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7020/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7020/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7020/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7020/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7020/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7020/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7021/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7021/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7021/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7021/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7021/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7021/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7022/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7022/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7022/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7022/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7022/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7022/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7023/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7023/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7023/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7023/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7023/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7023/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7024/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7024/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7024/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7024/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7024/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7024/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7029/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7029/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7029/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7029/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7029/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7029/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7030/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7030/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7030/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7030/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7030/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7030/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7031/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7031/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7031/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7031/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7031/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7031/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7032/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7032/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7032/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7032/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7032/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7032/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7033/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7033/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7033/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7033/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7033/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7033/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7034/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7034/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7034/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7034/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7034/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7034/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7035/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7035/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7035/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7035/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7035/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7035/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7036/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7036/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7036/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7036/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7036/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7036/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7037/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7037/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7037/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7037/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7037/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7037/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7038/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7038/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7038/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7038/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7038/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7038/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7039/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7039/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7039/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7039/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7039/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7039/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7040/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7040/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7040/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7040/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7040/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7040/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7045/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7045/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7045/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7045/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7045/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7045/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7046/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7046/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7046/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7046/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7046/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7046/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7047/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7047/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7047/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7047/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7047/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7047/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7048/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7048/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7048/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7048/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7048/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7048/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7049/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7049/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7049/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7049/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7049/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7049/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7050/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7050/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7050/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7050/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7050/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7050/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7051/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7051/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7051/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7051/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7051/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7051/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7052/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7052/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7052/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7052/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7052/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7052/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7053/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7053/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7053/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7053/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7053/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7053/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7054/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7054/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7054/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7054/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7054/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7054/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7055/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7055/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7055/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7055/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7055/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7055/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7056/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7056/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7056/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7056/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7056/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7056/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7061/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7061/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7061/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7061/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7061/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7061/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7062/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7062/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7062/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7062/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7062/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7062/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7063/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7063/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7063/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7063/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7063/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7063/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7064/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7064/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7064/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7064/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7064/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7064/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7065/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7065/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7065/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7065/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7065/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7065/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7066/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7066/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7066/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7066/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7066/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7066/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7067/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7067/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7067/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7067/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7067/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7067/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7068/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7068/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7068/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7068/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7068/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7068/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7069/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7069/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7069/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7069/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7069/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7069/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7070/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7070/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7070/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7070/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7070/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7070/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7071/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7071/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7071/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7071/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7071/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7071/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7072/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7072/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7072/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7072/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7072/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7072/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7077/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7077/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7077/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7077/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7077/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7077/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7078/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7078/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7078/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7078/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7078/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7078/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7079/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7079/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7079/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7079/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7079/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7079/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7080/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7080/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7080/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7080/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7080/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7080/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7081/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7081/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7081/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7081/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7081/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7081/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7082/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7082/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7082/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7082/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7082/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7082/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7083/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7083/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7083/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7083/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7083/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7083/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7084/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7084/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7084/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7084/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7084/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7084/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7085/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7085/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7085/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7085/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7085/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7085/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7086/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7086/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7086/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7086/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7086/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7086/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7087/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7087/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7087/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7087/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7087/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7087/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7088/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7088/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7088/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7088/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7088/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7088/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7093/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7093/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7093/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7093/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7093/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7093/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7094/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7094/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7094/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7094/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7094/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7094/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7095/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7095/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7095/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7095/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7095/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7095/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7096/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7096/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7096/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7096/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7096/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7096/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7097/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7097/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7097/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7097/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7097/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7097/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7098/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7098/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7098/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7098/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7098/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7098/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7099/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7099/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7099/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7099/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7099/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7099/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7100/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7100/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7100/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7100/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7100/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7100/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7101/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7101/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7101/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7101/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7101/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7101/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7102/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7102/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7102/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7102/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7102/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7102/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7103/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7103/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7103/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7103/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7103/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7103/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7104/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7104/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7104/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7104/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7104/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7104/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7109/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7109/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7109/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7109/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7109/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7109/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7110/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7110/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7110/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7110/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7110/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7110/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7111/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7111/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7111/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7111/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7111/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7111/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7112/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7112/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7112/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7112/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7112/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7112/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7113/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7113/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7113/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7113/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7113/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7113/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7114/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7114/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7114/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7114/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7114/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7114/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7115/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7115/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7115/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7115/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7115/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7115/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7116/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7116/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7116/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7116/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7116/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7116/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7117/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7117/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7117/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7117/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7117/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7117/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7118/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7118/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7118/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7118/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7118/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7118/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7119/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7119/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7119/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7119/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7119/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7119/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7120/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7120/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7120/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7120/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7120/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7120/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7125/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7125/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7125/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7125/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7125/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7125/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7126/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7126/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7126/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7126/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7126/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7126/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7127/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7127/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7127/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7127/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7127/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7127/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7128/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7128/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7128/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7128/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7128/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7128/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7129/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7129/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7129/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7129/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7129/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7129/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7130/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7130/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7130/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7130/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7130/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7130/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7131/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7131/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7131/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7131/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7131/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7131/QN}] -max -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7132/QN min}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7132/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7132/QN}] -min -digits 8
puts {SOURCE_DCALC $auto$ff.cc:337:slice$7132/QN max}
report_dcalc -from [get_pins {$auto$ff.cc:337:slice$7132/CLK}] -to [get_pins {$auto$ff.cc:337:slice$7132/QN}] -max -digits 8
puts READONLY_NO_WRITE_NO_ECO
