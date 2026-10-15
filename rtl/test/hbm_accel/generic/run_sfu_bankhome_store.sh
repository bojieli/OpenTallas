#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../../../.."
out=$(realpath -m "${1:-/tmp/sfu-bankhome}");mkdir -p "$out"
src=(rtl/test/hbm_accel/generic/tb_hgi_sfu_bankhome_store.sv
 rtl/hbm_accel/generic/peers/ot_hgi_sfu_bankhome_{store,leaf,core,group}.sv
 rtl/hbm_accel/generic/peers/ot_hgi_sfu_static_operand_store.sv
 rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv
 physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v)
sha256sum "${src[@]}" > "$out/sources.sha256"
for mut in 0 1 2 3;do
 iverilog -g2012 -s tb_hgi_sfu_bankhome_store -Ptb_hgi_sfu_bankhome_store.MUT="$mut" -o "$out/m$mut.vvp" "${src[@]}" > "$out/m$mut.compile.log" 2>&1
 set +e
 vvp "$out/m$mut.vvp" > "$out/m$mut.log" 2>&1
 rc=$?
 set -e
 tail -4 "$out/m$mut.log"
 if test "$mut" = 0;then test "$rc" = 0;grep -q 'SFU_BANKHOME PASS' "$out/m$mut.log";else test "$rc" != 0;fi
done
echo SFU_BANKHOME_ALL_GATES_PASS
