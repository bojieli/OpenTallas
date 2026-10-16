#!/bin/bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd);cd "$root"
out=$(realpath -m "${1:?OUT}");mkdir -p "$out"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator;[ -x "$vl" ]||vl=verilator
src=(rtl/test/hbm_idx_static/tb_idx_link_dense_0905.sv rtl/hbm_accel/index/ot_hbm_idx_topk_link_static.sv rtl/hbm_accel/index/ot_hbm_idx_topk_link_static_dense.sv physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v)
sha256sum "${src[@]}" > "$out/sources.sha256"
for m in 0 1 2;do
 "$vl" --binary --timing -j 4 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_idx_link_dense_0905 -GMUT="$m" --Mdir "$out/obj$m" "${src[@]}" > "$out/build$m.log" 2>&1
 set +e
 (cd "$out"&&"$out/obj$m/Vtb_idx_link_dense_0905") > "$out/run$m.log" 2>&1
 rc=$?
 set -e
 grep 'IDX_LINK_DENSE' "$out/run$m.log"
 if [ "$m" = 0 ];then [ "$rc" = 0 ];grep -q 'IDX_LINK_DENSE PASS' "$out/run$m.log"
 else [ "$rc" != 0 ];grep -q 'dense compaction exact/miter/timeline mismatch' "$out/run$m.log";echo "DENSE_MUTANT $m rejected";fi
done
echo IDX_LINK_DENSE_GATE_PASS
