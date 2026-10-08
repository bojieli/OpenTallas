#!/bin/bash
cd /srv/opentallas-scratch/claude/tk-qwen-go2
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
Y=$(cat ydirs.txt)
TB=rtl/test/qwen_rom_runtime/realmem/tb_qwen_p0_parallel_context_go.sv
build(){ s=$1; $V --binary -Wno-fatal --timing --top-module tb_qwen_p0_parallel_context_go -GSCG=$s -Mdir obj_s$s -j 24 -CFLAGS -O1 $Y rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv $TB > b_s$s.log 2>&1; echo $? > b_s$s.rc
  for c in "0 0" "1 0" "2 1" "3 0"; do set -- $c; obj_s$s/Vtb_qwen_p0_parallel_context_go +MODE=$1 +EXPECT_FAULT=$( [ $s = 0 ] && [ $1 = 0 ] && echo 1 || echo $2) > r_s${s}_m$1.log 2>&1; echo "s$s m$1 rc=$?" >> summary.txt; done; }
build 1 & build 0 & wait
echo done > DONE
