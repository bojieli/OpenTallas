#!/bin/bash
set -u
OUT=$(mkdir -p "$1" && realpath "$1")
V=${VERILATOR:-/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator}
S=(tools/qwen_cluster/tb_a0_model_full.sv rtl/physical/qcluster/qfd_q3h_stn.sv rtl/physical/qcluster/qfd_c_stn.sv rtl/physical/qcluster/qfd_c_xstn_safe.sv rtl/physical/qcluster/qfd_c_land.sv rtl/physical/qcluster/qfd_c_land_r1h.sv rtl/physical/qcluster/qfd_c_b16_dv_fabric.sv rtl/physical/qcluster/qfd_c_b16_full.sv rtl/qwen_sys/dvm_20261014/ot_qfd_xslice_slots.sv rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv rtl/hdc/ot_hdc_delay.sv tools/qwen_cluster/tb_cb16_reset_calendar.sv)
sha256sum "${S[@]}" "$0" > "$OUT/sources.sha256"
for m in 0 8; do
 "$V" --binary --timing -j 4 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-PINMISSING -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN --top-module tb_reset_calendar -GM=$m -Mdir "$OUT/obj$m" "${S[@]}" > "$OUT/build$m.log" 2>&1 || { tail -20 "$OUT/build$m.log"; exit 2; }
 "$OUT/obj$m/Vtb_reset_calendar" > "$OUT/m$m.log" 2>&1; x=$?
 cat "$OUT/m$m.log"
 if [ "$m" = 0 ]; then [ "$x" = 0 ] && grep -q CB16_RESET_CALENDAR_PASS "$OUT/m$m.log" || exit 1
 else [ "$x" != 0 ] && grep -q 'CB16_RESET_CALENDAR_SLIP dut=full ' "$OUT/m$m.log" || exit 1; fi
done
echo CB16_RESET_CALENDAR_BENCH_PASS
