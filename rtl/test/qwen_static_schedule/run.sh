#!/bin/bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
for mutant in 0 1 2 3 4; do
  iverilog -g2012 -s tb_fixed_issue -Ptb_fixed_issue.MUT="$mutant" -o "$work/gate$mutant" "$root/rtl/qwen_sys/static_schedule_20261014/ot_qwen_fixed_issue.sv" "$root/rtl/test/qwen_static_schedule/tb_fixed_issue.sv"
  if [[ "$mutant" == 3 || "$mutant" == 4 ]]; then
    if vvp "$work/gate$mutant"; then echo 'timeline mutant was not observed'; exit 1; fi
  else
    vvp "$work/gate$mutant"
  fi
done
for mutant in 0 1 2; do
  iverilog -g2012 -s tb_fixed_issue_pw -Ptb_fixed_issue_pw.MUT="$mutant" -o "$work/pw$mutant" "$root/rtl/qwen_sys/static_schedule_20261014/ot_qwen_fixed_issue.sv" "$root/rtl/qwen_sys/static_schedule_20261014/ot_qwen_fixed_issue_pw.sv" "$root/rtl/test/qwen_static_schedule/tb_fixed_issue_pw.sv"
  if [[ "$mutant" == 1 ]]; then
    if vvp "$work/pw$mutant"; then echo 'missing configuration mutant was not observed'; exit 1; fi
  else
    vvp "$work/pw$mutant"
  fi
done
