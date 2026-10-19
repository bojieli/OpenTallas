yosys read_verilog -sv ot_rst_relay.sv mem.sv
yosys hierarchy -check -top top
set ::env(DESIGN_NAME) top
set ::env(RESULTS_DIR) $::env(OUTD)
set ::env(OT_RST_LAND) 1
set ::env(OT_RST_LAND_STAGES) 2
set ::env(OT_PIN_REGS_CLOCK) ck
set ::env(OT_PIN_REGS_RESET_PORTS) ld_rst_n
set ::env(OT_PIN_REGS_RESET) {^(ld_rst_n)$}
if {$::env(SPLIT) eq "1"} { set ::env(OT_RST_COPIES_MAX) 256; set ::env(OT_RST_LAND_COPIES) ld_rst_n=3 }
source ot_keep_regs.tcl
yosys synth -flatten -top top
yosys opt_clean
yosys write_json $::env(OUTD)/post.json
yosys rename top $::env(TOPN)
yosys write_verilog -noattr $::env(OUTD)/net.v
