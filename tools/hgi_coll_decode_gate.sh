#!/usr/bin/env bash
set -eu
src=${1:?pinned source path}; out=${2:?output path}
mkdir -p "$out"
iverilog -g2012 -s tb_hgi_coll_decode -o "$out/golden.vvp" "$src/rtl/hbm_accel/generic/collective/ot_hgi_coll_decode.sv" "$src/rtl/hbm_accel/generic/collective/tb_hgi_coll_decode.sv"
vvp "$out/golden.vvp" > "$out/golden.log" 2>&1
for mut in MUT_GROUP MUT_ROW_BLOCK; do
  iverilog -g2012 -s tb_hgi_coll_decode -P "tb_hgi_coll_decode.$mut=1" -o "$out/$mut.vvp" "$src/rtl/hbm_accel/generic/collective/ot_hgi_coll_decode.sv" "$src/rtl/hbm_accel/generic/collective/tb_hgi_coll_decode.sv"
  set +e
  vvp "$out/$mut.vvp" > "$out/$mut.log" 2>&1
  result=$?
  set -e
  test "$result" -ne 0
  grep -q 'FATAL:' "$out/$mut.log"
done
sha256sum "$src/rtl/hbm_accel/generic/collective/"*.sv > "$out/source.sha256"
