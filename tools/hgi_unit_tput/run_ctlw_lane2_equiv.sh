#!/bin/bash
set -euo pipefail
out=$(realpath -m "$1"); mkdir -p "$out"
"${VERILATOR:-verilator}" --binary --timing -O3 -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -GMUT=${MUT:-0} --top-module tb_hgi_ctlw_lane2_equiv -Mdir "$out/obj" -o sim \
 rtl/hbm_accel/generic/peers/ot_hgi_su_ctlw_lane2.sv rtl/hbm_accel/generic/peers/ot_hgi_su_ctlw_slice_h.sv rtl/hbm_accel/generic/peers/ot_hgi_su_ctlw_slice_hp.sv \
 rtl/test/hbm_accel/generic/fixtures/ctlw_slice_pre_ref.sv rtl/test/hbm_accel/generic/tb_hgi_ctlw_lane2_equiv.sv \
 rtl/link/ot_fifo_sram_fwft.sv physical/asap7_memory_macros/ot_sram_1r1w_64x16_m1/ot_sram_1r1w_64x16_m1.v > "$out/build.log" 2>&1
set +e
"$out/obj/sim" > "$out/run.log" 2>&1
rc=$?
cat "$out/run.log"
exit "$rc"
