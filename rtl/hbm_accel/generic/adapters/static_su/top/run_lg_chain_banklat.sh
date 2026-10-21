#!/usr/bin/env bash
# HBM-BANKLAT-SU 2026-10-19: Verilator 5.050 bench of the SU/SFU/HC LG tap chain against the pin-registered bank.
# usage: run_lg_chain_banklat.sh OUTDIR NAME [-G...]   (run from the repo root; prints the CHAIN PASS/FAIL line)
set -euo pipefail
OUT=$1; NAME=$2; shift 2
VERILATOR=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
D=rtl/hbm_accel/generic/adapters/static_su
SRC=(
 $D/top/tb_hbm_su_lg_chain_banklat.sv
 $D/programme/multirate_bridge.sv
 $D/ot_hbm_su_static_vm_ports.sv
 $D/top/ot_hbm_su_static_pg_lg_tap.sv
 rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_pair_tap.sv
 rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_bank.sv
 rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_bank_term.sv
 rtl/hbm_accel/generic/peers/ot_hgi_sfu_lg_pair_tap_leaf.sv
 rtl/hbm_accel/generic/peers/ot_hgi_sfu_lg_pair_leaf.sv
 rtl/hdc/ot_hdc_delay.sv
)
mkdir -p "$OUT/$NAME"
"$VERILATOR" --version
"$VERILATOR" --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN \
  --top-module tb_hbm_su_lg_chain_banklat -Mdir "$OUT/$NAME/obj" "$@" "${SRC[@]}" > "$OUT/$NAME/build.log" 2>&1 \
  || { tail -30 "$OUT/$NAME/build.log"; echo "CHAIN BUILD-FAIL $NAME"; exit 2; }
"$OUT/$NAME/obj/Vtb_hbm_su_lg_chain_banklat" | tee "$OUT/$NAME/sim.log"
grep -q "^CHAIN PASS" "$OUT/$NAME/sim.log"
