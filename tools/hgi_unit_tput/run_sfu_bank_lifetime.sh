#!/bin/bash
set -euo pipefail
mkdir -p "$OUT"
"${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}" --binary --timing -O2 -j 4 -CFLAGS -O0 -Wno-fatal --top-module tb_hgi_sfu_bank_lifetime -GMUT="${MUT:-0}" --Mdir "$OUT/obj" rtl/hbm_accel/generic/peers/ot_hgi_sfu_bank_lifetime.sv rtl/test/hbm_accel/generic/tb_hgi_sfu_bank_lifetime.sv > "$OUT/build.log" 2>&1
"$OUT/obj/Vtb_hgi_sfu_bank_lifetime" > "$OUT/run.log" 2>&1
cat "$OUT/run.log"
