yosys read_verilog -sv ot_rst_relay.sv mem.sv
yosys hierarchy -check -top top
set ::env(DESIGN_NAME) top
set ::env(RESULTS_DIR) .
set ::env(OT_RST_SPLIT_MAX) 256
source ot_keep_regs.tcl
yosys synth -flatten -top top
yosys opt_clean
yosys write_json post.json
