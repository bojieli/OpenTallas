#!/bin/bash
# DIE-KV-46: lockstep bench + FDR=0 structural check. Usage: run.sh <repo root> [seeds...]
set -euo pipefail
R=$(cd "$1" && pwd); shift; H=$(cd "$(dirname "$0")" && pwd); T=$(mktemp -d)
git -C "$R" show 'origin/main:rtl/qwen_sys/host_20261013/qkd_host_rx_class_admission.sv' \
  | sed 's/module qkd_host_rx_class_admission #/module qkd_host_rx_class_admission_ref #/' > $T/ref.sv
for s in "${@:-1 2 3}"; do for ir in 0 1; do
  iverilog -g2012 -o $T/sim -Ptb.SEED=$s -Ptb.IR_REPL=$ir $H/tb_rx_fault_dreg_lockstep.sv $T/ref.sv \
    $R/rtl/qwen_sys/host_20261013/fault_dreg/qkd_host_rx_class_admission.sv $R/rtl/qwen_sys/host_20261013/qkd_host_rx_class.sv
  echo -n "IR_REPL=$ir "; vvp -n $T/sim | grep -E 'PASS|FATAL|MISMATCH|DATA|GRANT' 
done; done
rm -rf $T
