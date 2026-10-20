# Private text-generation harness only; not elaboration or native qualification.
set ::env(DESIGN_NAME) ot_qkh_lane8_nc32c
set ::env(OT_PIN_REGS) 0
set ::env(OT_RST_LAND) 1
set ::env(OT_RST_LAND_STAGES) 2
set ::env(OT_PIN_REGS_CLOCK) clk
set ::env(OT_PIN_REGS_RESET_PORTS) rst_n
set ::env(RESULTS_DIR) [pwd]
proc yosys {args} {
 if {[lindex $args 0] eq "tee"} {file copy -force core_ports.txt [lindex $args 3]}
 # Remaining rename/read/hierarchy commands are deliberately not emulated.
}
source ot_pin_regs_source.tcl
