yosys read_liberty -overwrite -setattr liberty_cell -lib /t/b.lib
yosys read_liberty -overwrite -setattr liberty_cell -unit_delay -wb -ignore_miss_func -ignore_buses /t/b.lib
yosys read_verilog -defer -sv /t/t.sv
yosys hierarchy -check -top top
yosys ls
yosys select -list t:*
yosys write_verilog -noattr /t/o2.v
