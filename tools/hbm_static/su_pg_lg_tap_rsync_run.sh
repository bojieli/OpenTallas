#!/bin/bash
# HBM-SU3 10-17: kit bench of ot_hbm_su_static_pg_lg_tap (lockstep vs pair tap + exact reset edges). usage: OUT [MUT] [SMUT]  (SMUT: NATIVE-FIX3 LOCAL_SPLIT mutant 1/2)
set -euo pipefail
cd "$(dirname "$0")/../.."
out=$(realpath -m "$1"); mut=${2:-0}; smut=${3:-0}; mkdir -p "$out"
iverilog -g2012 -s tb_hbm_su_pg_lg_tap_rsync -Ptb_hbm_su_pg_lg_tap_rsync.MUT=$mut -Ptb_hbm_su_pg_lg_tap_rsync.SMUT=$smut -o "$out/tap.vvp" \
 rtl/hbm_accel/generic/adapters/static_su/top/ot_hbm_su_static_pg_lg_tap.sv rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_pair_tap.sv \
 rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_bank.sv rtl/hdc/ot_hdc_delay.sv rtl/test/hbm_accel/generic/tb_hbm_su_pg_lg_tap_rsync.sv
vvp -n "$out/tap.vvp" | tee "$out/bench.log" | tail -8
