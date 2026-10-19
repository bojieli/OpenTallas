# KV-D2D quick native census synthesis (not the gate): flat, keep hook + reset-copy pass as ORFS, ASAP7 TT RVT
yosys -import
set top $::env(TOP)
set src $::env(SRCROOT)
set files [list rtl/lib/ot_rst_pipe.sv rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv rtl/qwen_sys/split_20261014/ot_qwen_static_slot_link.sv rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv rtl/qwen_sys/split_20261014/qkd_native_attention_record.sv rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_static.sv rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_services.sv rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies.sv rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies_ovl.sv rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_safe_fo.sv rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies_sfo.sv rtl/qwen_split/qfd_kvn_static_transport.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2_bb.v]
foreach f $files { read_verilog -sv -DSYNTHESIS $src/$f }
hierarchy -check -top $top -chparam NTX 3 -chparam TXDP 50529302 -chparam SAFE_RC 1
set ::env(RESULTS_DIR) [pwd]
if {$::env(RSTMAX) ne "0"} { set ::env(OT_RST_COPIES_MAX) $::env(RSTMAX) }
source common_flow/ot_keep_regs.tcl
# generic census as the ROOT-accepted native census (58f622b46): proc/opt-full/techmap/opt-full + native DFF and INV
hierarchy -top $top
flatten
opt -full
techmap
opt -full
set L {}
foreach l [glob libs/*.lib] { lappend L -liberty $l }
dfflibmap -liberty [glob libs/*SEQ*.lib]
techmap -map invmap.v
opt_clean
foreach l [glob libs/*SEQ*.lib libs/*INVBUF*.lib] { read_liberty -lib $l }
stat
write_json $::env(OUT).json
write_verilog -noattr $::env(OUT).v
