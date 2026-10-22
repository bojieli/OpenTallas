set ::env(DESIGN_NAME) qkd_kvs_attn_fl
set ::env(OT_PIN_REGS_CLOCK) ck
set ::env(OT_PIN_REGS_RESET_PORTS) rst_n
set ::env(OT_RST_COPIES_MAX) 32
set ::env(OT_RST_COPIES_WIDE) 1
set ::env(OT_RST_LAND) 1
set ::env(OT_RST_LAND_COPIES) rst_n=64
set ::env(OT_RST_LAND_FIRST_COPIES) rst_n=2
set ::env(OT_RST_LAND_STAGES) 2
set ::env(RESULTS_DIR) {/home/ubuntu/scratch/kv-attn7/wrap/out}
proc yosys {args} { if {[lindex $args 0] eq "tee"} { file copy -force {/home/ubuntu/scratch/kv-attn7/wrap/ports.txt} [lindex $args 3] } }
if {[catch {source {/home/ubuntu/scratch/kv-attn7/wrap/ot_pin_regs.tcl}} msg]} {puts stderr $msg; exit 1}
