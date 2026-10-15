#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:?output directory required}
mkdir -p "$out"
src=("$root/rtl/qwen_sys/dvm_20261014/ot_qfd_vm_q_export.sv" "$root/rtl/qwen_sys/dvm_20261014/tb_qfd_vm_q_export.sv" "$root/rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_vector_memory.sv")
sha256sum "${src[@]}" > "$out/source.sha256"
iverilog -g2012 -s tb_qfd_vm_q_export -o "$out/positive" "${src[@]}"
vvp "$out/positive" > "$out/positive.log"
for mode in MUT_BEAT MUT_FENCE; do
  iverilog -g2012 -s tb_qfd_vm_q_export -P"tb_qfd_vm_q_export.$mode=1" -o "$out/$mode" "${src[@]}"
  if vvp "$out/$mode" > "$out/$mode.log" 2>&1; then
    echo "mutant unexpectedly passed: $mode" >&2
    exit 1
  fi
  grep -q 'FATAL:' "$out/$mode.log"
done
rm "$out/positive" "$out/MUT_BEAT" "$out/MUT_FENCE"
echo 'PASS positive; observed beat and premature-fence mutant failures'
