#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:?fresh output directory};mkdir "$out"
for mode in good host stage cmd cap gen tag;do
 p=()
 case "$mode" in gen)p=(-Ptb_qfd_native59_context.BAD_GEN=1);;tag)p=(-Ptb_qfd_native59_context.BAD_TAG=1);;host)p=(-Ptb_qfd_native59_context.BAD_HOST=1);;stage)p=(-Ptb_qfd_native59_context.BAD_STAGE=1);;cmd)p=(-Ptb_qfd_native59_context.BAD_CMD=1);;cap)p=(-Ptb_qfd_native59_context.BAD_CAP=1);;esac
 iverilog -g2012 -s tb_qfd_native59_context "${p[@]}" -o "$out/context.sim" "$root/rtl/qwen_split/qfd_native59_command_context.sv" "$root/rtl/test/qwen_split/tb_qfd_native59_context.sv"
 vvp "$out/context.sim" > "$out/$mode.log"
 cat "$out/$mode.log"
done
rm "$out/context.sim"
sha256sum "$root/rtl/qwen_split/qfd_native59_command_context.sv" "$root/rtl/test/qwen_split/tb_qfd_native59_context.sv" > "$out/source.sha256"
