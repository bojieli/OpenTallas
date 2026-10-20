yosys -import
set top $::env(TOP)
read_verilog -lib ctl_sram_1r1w_64x64_p192_bb.v ctl_sram_1r1w_64x128_p192_bb.v ot_sram_1r1w_128x256_m1_r2c2_bb.v
set fh [open srcs.f r]; set srcs [split [string trim [read $fh]] "\n"]; close $fh
read_verilog -sv {*}$srcs
foreach {k v} $::env(PARAMS) { chparam -set $k $v $top }
hierarchy -check -top $top
source ot_keep_regs.tcl
synth -top $top -flatten
dfflibmap -liberty SEQ.lib
abc -liberty AO.lib -liberty INVBUF.lib -liberty OA.lib -liberty SIMPLE.lib
opt_clean
write_verilog -noattr out_$::env(TAG).v
write_verilog out_$::env(TAG)_attr.v
