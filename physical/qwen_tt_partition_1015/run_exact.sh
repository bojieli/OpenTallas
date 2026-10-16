#!/bin/bash
set -euo pipefail
m=${1:?mutant}; p=${2:?production}; out=${3:?output}
mkdir -p "$out"
mapfile -t srcs < rtl/qwen_sys/tt_tree_partition_20261015/sources.txt
verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style \
  --top-module tb_tt_tree_partition -GMUT="$m" -GPROD="$p" -Mdir "$out/obj" \
  "${srcs[@]}" > "$out/build.log" 2>&1 || { tail -20 "$out/build.log"; exit 2; }
"$out/obj/Vtb_tt_tree_partition"
