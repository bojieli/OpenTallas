#!/bin/bash
# usage: run2.sh NAME WORDS REF_MODE
cd /home/ubuntu/wt-hbm-refpb
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
D=/tmp/claude-1000/-home-ubuntu-OpenTallas/98bed5ce-ef4e-4140-93b4-b898444c4b99/scratchpad/fb/ws/$1
mkdir -p $D
$V --binary --timing -Wno-fatal -Wno-WIDTH -j 8 -CFLAGS -O0 --output-split 5000 --top-module tb_hbmacc_wstream_bw --Mdir $D/obj -GWORDS=$2 -GREF_MODE=$3 -GNSTK=1 \
  rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc.sv rtl/hbm_accel/qwen/ot_hbmacc_qwen_wstream.sv rtl/test/hbm_accel_qwen/tb_hbmacc_wstream_bw.sv rtl/test/ot_hbm_pc_dram_check.sv > $D/build.log 2>&1
$D/obj/Vtb_hbmacc_wstream_bw > $D/run.log 2>&1
grep RESULT $D/run.log
echo "pcs=$(grep -c DRAMCHK_PC $D/run.log) viol_total=$(grep -o 'DRAMCHK_PC.*viol=[0-9]*' $D/run.log | sed 's/.*viol=//' | paste -sd+ | bc)"
grep -m5 DRAMCHK_VIOLATION $D/run.log || true
