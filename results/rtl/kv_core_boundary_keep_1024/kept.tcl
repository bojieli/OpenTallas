yosys read_verilog -sv /work/kept.sv /work/kept_wrap.sv
yosys hierarchy -check -top observe
source /work/ot_keep_regs.tcl
yosys synth -flatten -top observe
yosys write_verilog -noattr -noexpr /work/kept_mapped.v
