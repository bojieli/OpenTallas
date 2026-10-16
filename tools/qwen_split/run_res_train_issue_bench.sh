#!/bin/bash
# Q-ELEM-CMP: qfd_res_train_issue production-shape bench (Verilator 5.050). usage: run_res_train_issue_bench.sh MUT TE OUTDIR
set -u
MUT=$1; TE=$2; O=$3
cd "$(dirname "$0")/../.."; mkdir -p "$O"
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --binary --timing -Wno-fatal -Wno-WIDTH -GMUT=$MUT -GTE=$TE --top-module tb_qfd_res_train_issue -Mdir "$O/obj" -o tb \
  rtl/qwen_split/qfd_res_train_issue.sv rtl/test/qwen_split/tb_qfd_res_train_issue.sv > "$O/build.log" 2>&1 || { echo BUILD_FAILED; tail -5 "$O/build.log"; exit 2; }
"$O/obj/tb" | tee "$O/bench.log" | grep -E "RTI_BENCH|ERR" | head -12
grep -q 'RTI_BENCH PASS' "$O/bench.log"
