#!/bin/bash
# eq.sh : build + run the edge _pr equivalence bench (PATH-HBM/Q3 10-25)
D=/srv/opentallas-scratch2/claude/path-hbm/q3split/edge_pr; WT=/srv/opentallas-scratch2/claude/wt/path-hbm-q3-1025; P=$WT/rtl/hbm_accel/generic/collective/p2p
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
cd $D; rm -rf obj
$V --binary -j 8 --top-module tb -Mdir obj -o sim -O3 --x-assign 0 --x-initial 0 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-PINMISSING -Wno-TIMESCALEMOD \
 -DSYNTHESIS $P/ot_hfd_coll_q_hard_v5.sv $P/ot_hgi_coll_argmax_static.sv $WT/rtl/hbm_accel/generic/collective/ot_hgi_coll_amerge.sv \
 $P/ot_hgi_coll_static_capture_ctl.sv $P/ot_hgi_coll_static_pinreg_ctl.sv $P/ot_hgi_coll_static_pinreg_store.sv $P/ot_hgi_coll_static_seq_ctl.sv \
 $WT/rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv $WT/rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv $(for m in ot_sram_1r1w_64x512_m1_r2c2 ot_sram_1rw_256x64_m4_r2c2 ot_sram_1r1w_256x256_m2_r2c2; do echo $WT/physical/asap7_memory_macros_v2/$m/$m.v; done) \
 ${PRFILE:-$D/ot_hgi_coll_edge_pr.sv} $D/tb_edge_pr.sv > build.log 2>&1 || { tail -30 build.log; exit 2; }
: > eq.log
for s in 1 2 3; do for d in 2 4 16; do ./obj/sim +seed=$s +dens=$d +cycles=30000 | grep -E "EDGE_PR_EQ|MISMATCH" | tail -1 >> eq.log; done; done
./obj/sim +seed=1 +dens=4 +mut=1 +cycles=30000 | grep EDGE_PR_EQ >> eq.log
./obj/sim +seed=1 +dens=4 +mut=2 +cycles=30000 | grep EDGE_PR_EQ >> eq.log
cat eq.log
