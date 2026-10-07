#!/bin/bash
# build.sh OUT EXTRA_G...
set -euo pipefail
O=$1; shift; S=/srv/opentallas/scratch-overflow/claude/qwen-kvmap-prot/src; T=$S/rtl/test/qwen_rom_runtime/realmem; mkdir -p $O; cd $O
verilator --cc --exe --build -O2 -j 8 --top-module tb_qwen_rt_kv_stream4 -GSYNC=2 -GRSEL=1 -GRNG=10 "$@" -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-TIMESCALEMOD -Wno-BLKSEQ -Wno-PINMISSING -Wno-LATCH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -y $S/rtl/hdc/kv -y $S/rtl/hdc -y $S/rtl/model_ready_hbm_r14 -y $S/rtl/lib -y $S/rtl/hdc/v41x -y $S/rtl/common $S/rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv $T/tb_qwen_rt_kv_stream4_cdc.sv $T/tb_qwen_rt_kv_stream4.cpp -CFLAGS '-O2 -DCDC' -DKVTRACE -DCDC -Mdir obj > build.log 2>&1
echo BUILD_OK
