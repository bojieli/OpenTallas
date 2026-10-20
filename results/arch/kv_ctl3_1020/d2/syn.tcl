yosys -import
set top $::env(TOP)
read_verilog -sv ot_s32_cells.sv qkd_static_kv_boot_dispatch.sv qkd_static_kv_boot_dispatch_mu.sv qkd_kv_ctl_s32_boot.sv
foreach {k v} $::env(PARAMS) { chparam -set $k $v $top }
hierarchy -check -top $top
source ot_keep_regs.tcl
synth -top $top -flatten
dfflibmap -liberty SEQ.lib
abc -liberty AO.lib -liberty INVBUF.lib -liberty OA.lib -liberty SIMPLE.lib
opt_clean
write_verilog -noattr out_$::env(TAG).v
write_verilog out_$::env(TAG)_attr.v
