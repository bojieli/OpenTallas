#!/bin/bash
# Smallest lockstep vehicles: existing controller command launch edge and
# fault collection's local/external edge contract. Mutants must be caught.
set -euo pipefail
R=$(cd "$(dirname "$0")/../.." && pwd)
OUT=$(mkdir -p "$1" && cd "$1" && pwd)
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
for c in tc tc_mut qo_mut fault fault_mut; do
  mkdir -p "$OUT/$c/obj"
  def=(); top=tb_astk_tc_faces
  src=$R/rtl/qwen_sys/split_20261014/qkd_astk_static_leaves.sv
  case $c in
    tc_mut) def=(-DKVG3_ASTK_TCMUT);;
    qo_mut) def=(-DKVG3_ASTK_QOMUT);;
    fault|fault_mut) top=tb_astk_fault_face; src=$R/rtl/qwen_sys/split_20261014/qkd_astk_phys.sv;;
  esac
  [ "$c" = fault_mut ] && def=(-DKVG3_ASTK_FMUT)
  verilator --binary -j 8 --timing -Wno-fatal -Wno-lint -Wno-style --top-module "$top" "${def[@]}" \
    -Mdir "$OUT/$c/obj" -o Vtb "$R/rtl/test/kv_core_harden/$top.sv" "$src" > "$OUT/$c/build.log" 2>&1
  "$OUT/$c/obj/Vtb" > "$OUT/$c/run.log" 2>&1
  grep -E '^(PASS|FAIL)' "$OUT/$c/run.log"
  expected=PASS; [[ "$c" = *_mut ]] && expected=FAIL
  grep -q "^$expected " "$OUT/$c/run.log"
done
