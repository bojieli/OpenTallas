yosys read_verilog -sv /work/gold.sv /work/gold_wrap.sv
yosys hierarchy -check -top observe
yosys synth -flatten -top observe
yosys write_verilog -noattr -noexpr /work/gold_mapped.v
