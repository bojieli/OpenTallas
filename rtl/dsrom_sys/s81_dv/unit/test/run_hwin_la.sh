#!/usr/bin/env bash
# HARD-S81-SERDES-1: lock-step bench of dsdv_mu_hwin LA (tb_dsdv_mu_hwin_la).  usage: run_hwin_la.sh OUTDIR NS NEV LAN [SEED]
set -u
out=${1:?out}; ns=${2:-47}; nev=${3:-8}; lan=${4:-1}; seed=${5:-11}; mkdir -p "$out"
R=$(cd "$(dirname "$0")/../../../../.." && pwd); U=$R/rtl/dsrom_sys/s81_dv/unit
VL=${VERILATOR:-verilator}
$VL --binary --timing -j 4 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT -Wno-MULTITOP --top-module tb_dsdv_mu_hwin_la \
  -GNS=$ns -GNEV=$nev -GLAN=$lan ${HWIN_EPOCHS:+-GEPOCHS=$HWIN_EPOCHS} --Mdir "$out/obj" -o tb "$R/rtl/lib/ot_rst_relay.sv" "$U/dsdv_mu_hwin.sv" "$U/test/tb_dsdv_mu_hwin_la.sv" \
  > "$out/build.log" 2>&1 || { echo "HWIN_LA BUILD_FAIL"; grep -m5 "%Error" "$out/build.log"; exit 2; }
"$out/obj/tb" +verilator+seed+$seed > "$out/run.log" 2>&1
grep -E '^(HWIN_LA|%Error)' "$out/run.log" | head -3; grep -E '^TB_HWIN_LA' "$out/run.log" | tail -2
grep -qE '^TB_HWIN_LA PASS$' "$out/run.log"
