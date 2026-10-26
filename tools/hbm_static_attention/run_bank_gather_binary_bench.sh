#!/bin/bash
# Exact bit-level bench of ot_hbm_attn_pv_bank_gather_binary against the registered baseline (5000 cycles, full rate
# and bubbles). Usage: run_bank_gather_binary_bench.sh OUT [none|select|reset]  (mutant define; select/reset must FAIL)
set -euo pipefail
out=$1;mut=${2:-none};mkdir -p "$out"
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
def=();case $mut in select)def=(-DATT_GATHER_BINARY_MUTANT);;reset)def=(-DATT_GATHER_RESET_MUTANT);;none);;*)echo bad mutant;exit 2;;esac
"$vl" --binary --timing -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD "${def[@]}" --top-module tb_hbm_attn_bank_gather_binary \
 --Mdir "$out/obj" -o sim rtl/hdc/v41x/static/ot_hbm_attn_pv_bank_gather_binary.sv rtl/hdc/v41x/static/ot_hbm_attn_pv_bank_gather_registered.sv \
 rtl/test/hbm_accel/generic/tb_hbm_attn_bank_gather_binary.sv > "$out/build.log" 2>&1
"$out/obj/sim" 2>&1 | tee "$out/sim.log"
grep -q 'PASS BANK_GATHER_BINARY' "$out/sim.log"
