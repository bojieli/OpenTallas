yosys read_verilog -sv ot_rst_relay.sv mem.sv
yosys hierarchy -check -top top
set ::env(DESIGN_NAME) top
set ::env(RESULTS_DIR) gold
source ot_keep_regs.tcl
yosys synth -flatten -top top
yosys rename top gold
yosys write_verilog -noattr gold.v
