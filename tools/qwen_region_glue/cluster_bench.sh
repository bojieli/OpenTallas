#!/bin/bash
set -euo pipefail
OUT=$(mkdir -p "$1" && realpath "$1")
V=${VERILATOR:-verilator}
SRC=(rtl/physical/q3h/qfd_q3h_stn.sv rtl/physical/q3h_regional/qfd_q3h_run_regional.sv rtl/physical/q3h_regional/qfd_c_b16_fabric_regional.sv
 rtl/qwen_sys/dvm_20261014/ot_qfd_xslice_slots.sv rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv rtl/hdc/ot_hdc_delay.sv
 rtl/physical/ot_qwen_tile_node.sv rtl/lib/ot_rst_relay.sv rtl/hdc/ot_qwen_w12_matvec.sv rtl/physical/ot_qwen_tile_operand.sv
 rtl/hdc/ot_hdc_fp32_add_lat_nr.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/proto/ot_fp32_add_rne_pipe.sv
 rtl/test/tb_q3h_tile_face.sv rtl/test/tb_q3h_cb16_regional.sv)
python3 tools/qwen_split/q3h_cb16_vectors.py "$OUT"
sha256sum "${SRC[@]}" rtl/test/q3h_cb16_lat.svh rtl/test/q3h_cb16_tbdefs.svh "$0" > "$OUT/sources.sha256"
for MUT in 0 1 2; do
 "$V" --binary --timing -j 4 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Irtl/test --top-module tb -GMUT=$MUT -Mdir "$OUT/obj$MUT" "${SRC[@]}" > "$OUT/build_$MUT.log" 2>&1
 if [[ $MUT == 0 ]]; then FARS="0 1"; else FARS="0"; fi
 for FAR in $FARS; do
  ARG=(); [[ $FAR == 1 ]] && ARG+=(+FAR)
  set +e
  (cd "$OUT" && ./obj$MUT/Vtb "${ARG[@]}") > "$OUT/run_m${MUT}_f${FAR}.log" 2>&1
  status=$?
  set -e
  if [[ $MUT == 0 ]]; then
   [[ $status == 0 ]]
   grep -q '^Q3H_REGIONAL_FABRIC_PASS ' "$OUT/run_m${MUT}_f${FAR}.log"
   ! grep -q '^FAIL\|%Error\|%Fatal' "$OUT/run_m${MUT}_f${FAR}.log"
  else
   ! grep -q '^Q3H_REGIONAL_FABRIC_PASS ' "$OUT/run_m${MUT}_f${FAR}.log"
   grep -q '^FAIL\|%Error\|%Fatal' "$OUT/run_m${MUT}_f${FAR}.log"
  fi
  echo REGIONAL_FABRIC_RESULT MUT=$MUT FAR=$FAR status=$status
 done
done
