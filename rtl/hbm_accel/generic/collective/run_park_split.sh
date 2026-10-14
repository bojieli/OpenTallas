#!/usr/bin/env bash
set -euo pipefail
OUT=$(realpath -m "$1"); shift
ROOT=$(cd "$(dirname "$0")/../../../.." && pwd)
cd "$ROOT";mkdir -p "$OUT"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$VL" --binary --timing -O2 -j "${JOBS:-8}" -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --top-module tb_hgi_coll_park_split --Mdir "$OUT/obj" "$@" rtl/hbm_accel/generic/collective/ot_hgi_coll_park{,_queue,_fault,_flat_ref}.sv rtl/hbm_accel/generic/collective/ot_coll_park_fifo.sv rtl/hbm_accel/generic/collective/tb_hgi_coll_park_split.sv rtl/link/ot_fifo_sram_fwft.sv rtl/lib/ot_rst_relay.sv rtl/model/hbm_pc40_native_sim_20261003/ot_sram_1r1w_128x256_m1_r2c2_sim.sv > "$OUT/build.log" 2>&1
"$OUT/obj/Vtb_hgi_coll_park_split" | tee "$OUT/run.log"
