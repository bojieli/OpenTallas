#!/bin/bash
set -euo pipefail
out=$1;mkdir -p "$out"
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$vl" --binary --timing -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_hbm_attn_transpose_regs --Mdir "$out/obj" -o sim \
 rtl/hdc/v41x/static/ot_hbm_attn_transpose_regs.sv rtl/hdc/v41x/ot_hdc_v41x_attn.sv rtl/test/hbm_accel/generic/tb_hbm_attn_transpose_regs.sv > "$out/build.log" 2>&1
for m in 0 1 2;do
 set +e;"$out/obj/sim" +MUT=$m > "$out/m$m.log" 2>&1;rc=$?;set -e;echo "$rc" > "$out/m$m.rc"
 if [ "$m" = 0 ];then grep -q 'PASS TRANSPOSE_REGS' "$out/m$m.log";else grep -qE 'TRANSPOSE_REGS (phase fault|exactsource mismatch)' "$out/m$m.log";fi
done
echo 'PASS explicitFF transpose18,432bits/tile+mixedformat/overlap+2mutants; full32tile589824FFmappedclosureOPEN' > "$out/gate"
