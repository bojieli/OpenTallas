#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../../../.."
out=$(realpath -m "${1:-/tmp/sfu-bankhome-clocks}");mkdir -p "$out"
src=(rtl/test/hbm_accel/generic/tb_hgi_sfu_bankhome_clocks.sv rtl/hbm_accel/generic/peers/ot_hgi_sfu_bankhome_{store,leaf,core,group}.sv rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v)
sha256sum "${src[@]}" > "$out/sources.sha256"
for m in 0 1 2;do
 iverilog -g2012 -s tb_hgi_sfu_bankhome_clocks -Ptb_hgi_sfu_bankhome_clocks.MUT="$m" -o "$out/m$m.vvp" "${src[@]}" > "$out/m$m.compile.log" 2>&1
 set +e
 vvp "$out/m$m.vvp" > "$out/m$m.log" 2>&1
 rc=$?
 set -e
 tail -3 "$out/m$m.log"
 if test "$m" = 0;then test "$rc" = 0;grep -q SFU_HOME_CLOCKS_PASS "$out/m$m.log";else test "$rc" != 0;fi
done
echo SFU_HOME_CLOCK_GATES_PASS
