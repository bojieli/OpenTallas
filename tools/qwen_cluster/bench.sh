#!/bin/bash
# qfd_c_b16_dv fabric exactness bench (Q-CLUSTER 2026-10-17).  From the repo root (fleet host via ot-run):
#   tools/qwen_cluster/bench.sh OUTDIR
# MUT 0 at FAR 0 / 1 must PASS; MUT 1..5 must FAIL (1 leg misalignment, 2 wrong pairing, 3 late column run,
# 4 feedthrough one edge late, 5 feedthrough bit swap).
set -uo pipefail
OUT=$(mkdir -p "$1" && realpath "$1")
V=${VERILATOR:-verilator}
SRC=(rtl/physical/qcluster/qfd_q3h_stn.sv rtl/physical/qcluster/qfd_c_b16_dv_fabric.sv
     rtl/qwen_sys/dvm_20261014/ot_qfd_xslice_slots.sv rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv rtl/hdc/ot_hdc_delay.sv
     rtl/physical/ot_qwen_tile_node.sv rtl/lib/ot_rst_relay.sv rtl/hdc/ot_qwen_w12_matvec.sv
     rtl/hdc/ot_hdc_fp32_add_lat_nr.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/proto/ot_fp32_add_rne_pipe.sv
     rtl/test/tb_q3h_tile_face.sv rtl/test/tb_qcluster_fabric.sv)
python3 tools/qwen_cluster/vectors.py "$OUT"
{ sha256sum "${SRC[@]}" rtl/test/qcluster_lat.svh rtl/test/q3h_cb16_tbdefs.svh "$0" tools/qwen_cluster/vectors.py; "$V" --version; } > "$OUT/sources.sha256"
rc=0
for MUT in 0 1 2 3 4 5; do
  "$V" --binary --timing -j 8 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Irtl/test \
     --top-module tb -GMUT=$MUT -Mdir "$OUT/obj$MUT" "${SRC[@]}" > "$OUT/build_$MUT.log" 2>&1 || { echo "BUILD_FAIL MUT $MUT"; rc=1; continue; }
  if [[ $MUT == 0 ]]; then FARS="0 1"; else FARS="0"; fi
  for FAR in $FARS; do
    ARG=""; [[ $FAR == 1 ]] && ARG="+FAR"
    (cd "$OUT" && ./obj$MUT/Vtb $ARG) > "$OUT/run_m${MUT}_f${FAR}.log" 2>&1
    if grep -q '^QCLUSTER_PASS ' "$OUT/run_m${MUT}_f${FAR}.log" && ! grep -q '^FAIL\|%Error\|%Fatal' "$OUT/run_m${MUT}_f${FAR}.log"; then
      v=PASS; else v=FAIL; fi
    if [[ $MUT == 0 ]]; then want=PASS; else want=FAIL; fi
    echo "RESULT MUT $MUT FAR $FAR: $v (expected $want)"
    [[ $v == "$want" ]] || rc=1
  done
  rm -rf "$OUT/obj$MUT"
done
echo "BENCH_EXIT $rc"
exit $rc
