#!/bin/bash
# build.sh SRC MODE(ref|cdc) SYNC OUT
set -euo pipefail
S=$1; M=$2; SY=$3; O=$4; mkdir -p $O
T=$S/rtl/test/qwen_rom_runtime/realmem
if [ $M = cdc ]; then TOP=$T/tb_qwen_rt_kv_stream4_cdc.sv; DEF=-DCDC; G="-GSYNC=$SY"; else TOP=$T/tb_qwen_rt_kv_stream4.sv; DEF=; G=; fi
cd $O
verilator --cc --exe --build -O2 -j 16 --top-module tb_qwen_rt_kv_stream4 $G -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-TIMESCALEMOD \
  -Wno-BLKSEQ -Wno-PINMISSING -Wno-LATCH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT \
  -y $S/rtl/hdc/kv -y $S/rtl/hdc -y $S/rtl/model_ready_hbm_r14 -y $S/rtl/lib \
  $TOP $T/tb_qwen_rt_kv_stream4.cpp -CFLAGS "-O2 $DEF" -Mdir obj > build.log 2>&1
echo BUILD_OK
