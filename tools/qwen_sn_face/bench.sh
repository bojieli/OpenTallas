#!/usr/bin/env bash
set -euo pipefail
out=${1:?output}; mode=${2:-0}
mkdir -p "$out"
iverilog -g2012 -s tb_face -Ptb_face.MUT="$mode" -o "$out/face-$mode.vvp" rtl/qwen_sys/vm_plane_20261013/face/ot_qfd_vm_face.sv rtl/qwen_sys/vm_plane_20261013/face/tb_face.sv
vvp "$out/face-$mode.vvp"
