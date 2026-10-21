#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
for mode in positive mutant; do
  P=rtl/qwen_split/qfd_sys_face_ovl_fault1.sv
  [ "$mode" = mutant ] && P=wrong_omit_capture.sv
  iverilog -g2012 -D SYNTHESIS -I rtl/qwen_sys/d2d_static_20261015 -s tb -o "$mode.vvp" -f common.f "$P" tb.sv > "$mode.build.log" 2>&1
  set +e
  vvp "$mode.vvp" > "$mode.log" 2>&1
  rc=$?
  set -e
  if [ "$mode" = positive ]; then
    [ "$rc" = 0 ] && grep -q FAULT_FACE_SOURCE_CUT_PASS "$mode.log"
  else
    [ "$rc" != 0 ] && grep -q 'actual sticky root capture edge' "$mode.log"
  fi
  cat "$mode.log"
done
echo FAULT_FACE_CAUSAL_PASS
