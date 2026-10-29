#!/bin/bash
set -eu
ROOT=${ROOT:-$(git rev-parse --show-toplevel)}
for spec in 'head_current 0 8 3 fail' 'witness_current 1 4 3 fail' 'head_actual 0 8 18 pass' 'witness_actual 1 4 14 pass' 'witness_unaligned 1 4 18 fail' 'witness_aligned 1 8 18 pass' 'head_early 0 8 17 fail' 'head_late 0 8 19 fail'; do
  read -r name mode fwd txd expected <<< "$spec"
  iverilog -g2012 -s tb -Ptb.MODE=$mode -Ptb.FWD=$fwd -Ptb.TXD=$txd -o sim_$name "$ROOT/rtl/qwen_split/mu/qfd_mu_head_context_tx_lctx32.sv" "$ROOT/rtl/qwen_split/mu/qfd_mu_head_context_tx_lctx32_helpers.sv" "$ROOT/rtl/qwen_split/qfd_sys_face_record_port_n32.sv" tb.sv > compile_$name.log 2>&1
  if vvp sim_$name > $name.log 2>&1; then actual=pass; else actual=fail; fi
  [ "$actual" = "$expected" ] || exit 3
done
echo PASS
