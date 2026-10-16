#!/bin/bash
set -euo pipefail
out=${1:?output directory};kind=${2:?return or control};mkdir -p "$out"
extra=""
if [ "$kind" = return ] || [ "$kind" = return_pin ]; then top=tb_return_plane; else top=tb_read_control_ro6; fi
if [ "$kind" = return_pin ]; then extra="-Ptb_return_plane.PIN_INPUT=1"; fi
selection=${3:-both}
if [ "$selection" = both ]; then cases="0 1"; else cases="$selection"; fi
for mutant in $cases; do
  iverilog -g2012 $extra -s "$top" -P"$top.MUT=$mutant" -o "$out/m$mutant.vvp" rtl/qwen_sys/vm_me_20261008/ot_qfd_sp_vector_memory_bv.sv rtl/qwen_sys/vm_native_physical_20261015/qvm_return_plane_pin_native.sv "rtl/test/qwen_vm_residual/$top.sv" > "$out/m$mutant.build.log" 2>&1
  sha256sum "$out/m$mutant.vvp" > "$out/m$mutant.binary.sha256"
  if [ "$selection" != both ]; then
    if vvp "$out/m$mutant.vvp" > "$out/m$mutant.run.log" 2>&1; then result=0; else result=$?; fi
    cat "$out/m$mutant.run.log"
    exit "$result"
  fi
  if vvp "$out/m$mutant.vvp" > "$out/m$mutant.run.log" 2>&1; then
    test "$mutant" = 0;grep -q '^PASS' "$out/m$mutant.run.log"
  else
    test "$mutant" = 1;grep -q 'FAIL' "$out/m$mutant.run.log"
  fi
done
sha256sum rtl/qwen_sys/vm_me_20261008/ot_qfd_sp_vector_memory_bv.sv rtl/qwen_sys/vm_native_physical_20261015/qvm_return_plane_pin_native.sv "rtl/test/qwen_vm_residual/$top.sv" > "$out/source.sha256"
echo "PASS exact local $kind positive and observed hardware mutant"
