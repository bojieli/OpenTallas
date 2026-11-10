#!/bin/bash
# DIE-QC-97 lock-step benches (rtl/test/meso/status_reg/run.sh harness, same phases + STATUS_REG mutants):
#   tb_status_reg_fo32_rf.sv   gold = cas legacy (STATUS_REG 0, DSREP 1, WRITE_CHUNK 64)
#                              cand = clock.landing_ring_fanout_max 32 + landing_ring_status_reg (STATUS_REG 1, DSREP 2, WRITE_CHUNK 32 on WREG)
#   tb_status_reg_fo32both.sv  gold/cand both fanout-32, STATUS_REG 0 vs 1 (stock stimulus)
# usage: run.sh TB OUT
set -uo pipefail
R=$(cd "$(dirname "$0")/../.." && pwd)
TB=${1:?tb file}; OUT=${2:?output directory}; mkdir -p "$OUT"
T=$(mktemp -d); mkdir -p "$T/rtl/common" "$T/rtl/test/meso/status_reg"
cp "$R/rtl/common/ot_dp_clk_landing_ca.sv" "$R/rtl/common/ot_meso_fifo.sv" "$R/rtl/common/ot_dp_clk_landing.sv" "$T/rtl/common/"
cp "$R/rtl/test/meso/status_reg/run.sh" "$T/rtl/test/meso/status_reg/"; cp "$TB" "$T/rtl/test/meso/status_reg/tb_status_reg.sv"
bash "$T/rtl/test/meso/status_reg/run.sh" "$OUT"; rc=$?; rm -rf "$T"; exit $rc
