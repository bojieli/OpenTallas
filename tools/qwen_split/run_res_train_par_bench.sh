#!/bin/bash
# Q-ELEM-CMP: qfd_sp_res_train_par_{0,1,2} composition bench (Verilator 5.050). usage: run_res_train_par_bench.sh MUT OUTDIR
# MUT 0 = production RTL; 1 = no band lag; 2 = end on slot 0; 3 = every bank captures one edge late (all must FAIL)
set -u
MUT=$1; O=$2
cd "$(dirname "$0")/../.."; mkdir -p "$O"
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
DEF=""; [ "$MUT" != 0 ] && DEF="+define+OT_QFD_RTP_MUT=$MUT"
verilator --binary --timing -j 4 -Wno-fatal -Wno-WIDTH $DEF --top-module tb_qfd_sp_res_train_par -Mdir "$O/obj" -o tb \
  rtl/qwen_split/qfd_res_train_par.sv rtl/qwen_split/qfd_sp_res_train_par.sv rtl/test/qwen_split/tb_qfd_sp_res_train_par.sv > "$O/build.log" 2>&1 || { echo BUILD_FAILED; tail -5 "$O/build.log"; exit 2; }
"$O/obj/tb" | tee "$O/bench.log" | grep -E "RTP_BENCH|ERR" | head -10
grep -q 'RTP_BENCH PASS' "$O/bench.log"
