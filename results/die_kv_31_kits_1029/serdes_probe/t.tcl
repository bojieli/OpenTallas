yosys read_verilog -defer -sv /t/t.sv
yosys hierarchy -check -top top
yosys select -list {t:$paramod\bbx\W=*}
yosys chtype -set bbx_w522 {t:$paramod\bbx\W=*}
yosys select -list t:bbx_w522
yosys hierarchy -top top
yosys ls
yosys write_verilog -noattr /t/o.v
