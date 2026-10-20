yosys -import
set top $::env(TOP)
read_verilog -sv qkd_kv_ctl_half_root_b.sv qkd_kv_die_cfg.sv wrap.sv
foreach {k v} $::env(PARAMS) { chparam -set $k $v $top }
hierarchy -check -top $top
source ot_keep_regs.tcl
synth -top $top -flatten
dfflibmap -liberty SEQ.lib
abc -liberty AO.lib -liberty INVBUF.lib -liberty OA.lib -liberty SIMPLE.lib
opt_clean
write_verilog -noattr out_$::env(TAG).v
