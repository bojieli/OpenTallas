#!/usr/bin/env bash
# HBM-NSFIX/KQS 10-18: lockstep bench of the registered COLL kq static owner split ot_hgi_coll_kq_share2 vs the
# combinational version shifted by KQ_SHARE_EDGES = 2 (tb_hgi_coll_kq_share2.sv).  Verilator (the closure daemon's 5.050
# when VERILATOR points at it).   Usage: run_coll_kq_share2_bench.sh OUT [MUT]
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
OUT=$(realpath -m "$1"); MUT=${2:-0}; mkdir -p "$OUT"; cd "$ROOT"
V=${VERILATOR:-verilator}
P=rtl/hbm_accel/generic/collective/p2p
"$V" --version | tee "$OUT/verilator.version"
"$V" --binary --timing -O2 -j "${JOBS:-2}" -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-MULTITOP -Wno-TIMESCALEMOD -GMUT=$MUT \
  --top-module tb_hgi_coll_kq_share2 --Mdir "$OUT/obj_m$MUT" "$P/tb_hgi_coll_kq_share2.sv" "$P/ot_hgi_coll_gq.sv" rtl/lib/ot_rst_relay.sv \
  > "$OUT/build_m$MUT.log" 2>&1 || { tail -40 "$OUT/build_m$MUT.log"; exit 2; }
"$OUT/obj_m$MUT/Vtb_hgi_coll_kq_share2" 2>&1 | tee "$OUT/run_m$MUT.log"
grep -q "^KQS_SHARE2 MUT$MUT .* errors0 PASS$" "$OUT/run_m$MUT.log"
