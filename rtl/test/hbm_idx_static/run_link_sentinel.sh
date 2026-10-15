#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd);cd "$root"
out=${1:?out};mkdir -p "$out"
src=(rtl/hbm_accel/index/ot_hbm_idx_topk_link_static.sv rtl/test/hbm_idx_static/tb_link_sentinel_static.sv physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v)
for m in 0 1 2;do
 iverilog -g2012 -s tb_link_sentinel_static -Ptb_link_sentinel_static.MUT=$m -o "$out/m$m.vvp" "${src[@]}" >"$out/build$m.log" 2>&1
 set +e;vvp "$out/m$m.vvp" >"$out/run$m.log" 2>&1;rc=$?;set -e
 cat "$out/run$m.log"
 if [ "$m" = 0 ];then [ "$rc" = 0 ];else [ "$rc" != 0 ];grep -q 'producer sentinel encoding mismatch' "$out/run$m.log";fi
done
sha256sum "${src[@]}" >"$out/sources.sha256"
echo IDX_LINK_SENTINEL_GATE_PASS
