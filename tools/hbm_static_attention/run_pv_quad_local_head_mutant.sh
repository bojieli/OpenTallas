#!/bin/bash
set -euo pipefail
out=$1;mkdir -p "$out"
python3 - "$out/head_mutant.sv" <<'PY'
from pathlib import Path
import sys
p=Path('rtl/hdc/v41x/static/ot_hbm_attn_pv_serializer_quad_local.sv')
s=p.read_text();old='((a/2)*8)+((l/2)*4)+((a%2)*2)+(l%2)'
assert s.count(old)==1
Path(sys.argv[1]).write_text(s.replace(old,'a*4+l'))
PY
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$vl" --binary --timing -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD \
 --top-module tb_hbm_attn_pv_native_output_quad_local --Mdir "$out/obj" -o sim \
 rtl/hdc/v41x/static/ot_hbm_attn_pv_quad_store_registered.sv \
 rtl/hdc/v41x/static/ot_hbm_attn_pv_bank_gather_binary.sv "$out/head_mutant.sv" \
 rtl/hdc/v41x/static/ot_hbm_attn_pv_native_output_quad_local.sv \
 rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v \
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
 rtl/test/hbm_accel/generic/tb_hbm_attn_pv_native_output_quad_local.sv > "$out/build.log" 2>&1
set +e
"$out/obj/sim" +MUT=0 > "$out/mutant.log" 2>&1
rc=$?
set -e
test "$rc" -ne 0
grep -q 'PV_LOCAL_NATIVE readback mismatch' "$out/mutant.log"
echo 'PASS actual RTL contiguous-head quad mapping mutant rejected by real native-bank readback' > "$out/gate"
