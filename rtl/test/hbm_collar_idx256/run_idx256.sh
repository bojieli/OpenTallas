#!/bin/bash
set -euo pipefail
out=${1:?output};mkdir -p "$out";out=$(realpath "$out")
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version > "$out/verilator.txt"
for pair in 0:0 1:0 1:9 1:10 1:11 1:12;do
 fan=${pair%:*};mut=${pair#*:};tag=f${fan}_m${mut}
 verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_idx256 -GMUT=$mut -GFAN32=$fan --Mdir "$out/obj$tag" -o tb rtl/test/hbm_collar_idx256/tb_idx256.sv rtl/hbm_accel/host_static_20261015/ot_hbm_static_cfg_collar.sv rtl/hbm_accel/host_static_20261015/ot_hbm_static_cfg_collar_idx256.sv > "$out/build$tag.log" 2>&1
 if "$out/obj$tag/tb" > "$out/run$tag.log" 2>&1;then
  test "$mut" = 0 || { echo "IDX256_MUTANT_SURVIVED $mut";exit 1; }
  grep IDX256_PASS "$out/run$tag.log"
 else
  test "$mut" != 0 || { tail -10 "$out/run$tag.log";exit 1; }
  grep IDX256_FAIL "$out/run$tag.log"
 fi
done
