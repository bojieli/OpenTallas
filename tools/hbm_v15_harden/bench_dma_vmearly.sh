#!/usr/bin/env bash
# HBM-VMEARLY-DMA 10-19: back-to-back DMA-back moves on the RR_RT 80 controller (rtl/.../tb_dma_vp4_vmearly.sv):
# exposed edges per move at the ISSUE_AHEAD-0 calendar, a RAW move behind a producer VM write, and the proof that the
# controller does NOT accept an ISSUE_AHEAD-1 calendar (command during the previous move's drain).  Verilator (fleet 5.050).
#   bench_dma_vmearly.sh OUT CFG
#   pass        K 3 (next command 3 edges before end_at), producer retire at issue_at       -> PASS (prints exposed edges)
#   mut_early   K 4: next command one edge earlier than the controller takes              -> FAIL (mv_fault)
#   mut_ahead1  ISSUE_AHEAD-1 calendar: issue_at(i+1) = drain_at(i)                         -> FAIL (mv_fault)
#   mut_stale   RAW move's reads reach the banks before the producer's write retires        -> FAIL (stale payload)
set -euo pipefail
out=${1:?output};cfg=${2:?cfg};mkdir -p "$out"
d=rtl/hbm_accel/generic/peers/static
m=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
case "$cfg" in
 pass)       D="";;
 mut_early)  D="-DK=4";;
 mut_ahead1) D="-DAHEAD1";;
 mut_stale)  D="-DSTALE";;
 *) echo "unknown cfg $cfg"; exit 2;;
esac
verilator --version
W="-Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN"
# shellcheck disable=SC2086
verilator --binary --timing -j 4 $W -DRR_RT=80 $D --top-module tb_dma_vp4_vmearly -Mdir "$out/obj_$cfg" -o sim \
  "$m" "$d/ot_hgi_dma_back_static_vp_banks.sv" "$d/ot_hgi_dma_back_static_vp4_banks.sv" "$d/tb_dma_vp4_vmearly.sv" > "$out/build_$cfg.log" 2>&1 \
  || { tail -40 "$out/build_$cfg.log"; exit 1; }
"$out/obj_$cfg/sim" > "$out/$cfg.log" 2>&1 || true
cat "$out/$cfg.log"
grep -q 'VMEARLY PASS' "$out/$cfg.log"
