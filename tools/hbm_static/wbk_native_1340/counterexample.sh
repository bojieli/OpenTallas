#!/bin/bash
set -euo pipefail
out=${1:?output};mkdir -p "$out"
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
files=(tools/hbm_static/wbk_native_1340/pp_counterexample.sv rtl/hbm_accel/loader/service_native/ot_hbm_svc_wb_kq8.sv rtl/link/ot_link_afifo.sv rtl/lib/ot_reset_sync.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v)
sha256sum "${files[@]}" > "$out/source.sha256"
for m in 0 11;do
 "$vl" --binary --timing -j 8 -O1 -Wno-fatal -Wno-lint -Wno-style --top-module tb_wbk_pp_counterexample -GMUT="$m" --Mdir "$out/obj_m$m" -o sim "${files[@]}" > "$out/build_m$m.log" 2>&1
 set +e
 "$out/obj_m$m/sim" > "$out/run_m$m.log" 2>&1
 rc=$?
 set -e
 printf '%s\n' "$rc" > "$out/run_m$m.rc"
 if [[ $m == 0 ]];then test "$rc" = 0;grep -q '^WBK_PP_COUNTEREXAMPLE_PASS' "$out/run_m$m.log"
 else test "$rc" != 0;grep -q 'WBK_PP_INTEGRITY' "$out/run_m$m.log";! grep -q '^WBK_PP_COUNTEREXAMPLE_PASS' "$out/run_m$m.log";fi
 tail -3 "$out/run_m$m.log"
done
