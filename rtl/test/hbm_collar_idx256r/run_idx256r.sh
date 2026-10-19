#!/bin/bash
# LH-UNREAD F-P: run from the repo root on the fleet (Verilator 5.050 = closure daemon). MUT0 must PASS, MUT12 must FAIL.
set -euo pipefail
out=${1:?output};mkdir -p "$out";out=$(realpath "$out")
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version > "$out/verilator.txt"
for mut in 0 12;do
 verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_idx256r -GMUT=$mut --Mdir "$out/obj$mut" -o tb rtl/test/hbm_collar_idx256r/tb_idx256r.sv rtl/hbm_accel/host_static_20261015/ot_hbm_static_cfg_collar_idx256.sv rtl/hbm_accel/host_static_20261015/ot_hbm_static_cfg_collar_idx256r.sv > "$out/build$mut.log" 2>&1
 if "$out/obj$mut/tb" +verilator+seed+7 > "$out/run$mut.log" 2>&1;then
  test "$mut" = 0 || { echo "IDX256R_MUTANT_SURVIVED $mut";exit 1; }
  grep IDX256R_PASS "$out/run$mut.log"
 else
  test "$mut" != 0 || { tail -10 "$out/run$mut.log";exit 1; }
  grep IDX256R_FAIL "$out/run$mut.log"
 fi
done
echo IDX256R_BENCH_OK
