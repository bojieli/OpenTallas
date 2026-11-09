# usage: yosys -c count.tcl  (env KEEP=0/1)
set R /work/rtl
yosys read_verilog -sv -DSYNTHESIS $R/ot_hbm_svc_async_fifo.sv $R/ot_hbm_svc_pc_ctrl_leaf.sv $R/ot_hbm_svc_ring_h9b_ff.sv $R/ot_hbm_svc_vm_kshare_splitstrap.sv $R/ot_reset_sync.sv
yosys hierarchy -check -top ot_hbm_svc_vm_kshare_splitstrap -chparam KRL1 1
if {$::env(KEEP) eq "1"} { source /eq/keep_hook.tcl }
yosys synth -flatten -top ot_hbm_svc_vm_kshare_splitstrap -noabc
yosys opt_clean
yosys tee -o /eq/count_keep$::env(KEEP).txt select -list w:*reset_pipe* %ci1 t:\$*dff* t:\$_*DFF* %u %i
yosys tee -a /eq/count_keep$::env(KEEP).txt select -count w:*reset_pipe* %ci1 t:\$*dff* t:\$_*DFF* %u %i
