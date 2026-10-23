#!/bin/bash
# qfd_c_b16_dv fabric exactness bench (Q-CLUSTER 2026-10-17).  From the repo root (fleet host via ot-run):
#   tools/qwen_cluster/bench.sh OUTDIR
# MUT 0 at FAR 0 / 1 must PASS; MUT 1..5 must FAIL (1 leg misalignment, 2 wrong pairing, 3 late column run,
# 4 feedthrough one edge late, 5 feedthrough bit swap; Q-CL16-LAND landing mutants: 6 read slot K = E + 1, 7 read-side epoch
# one edge late).  The compiled rs latency (qcluster_lat.svh) includes the landed crossing's E + 1 = 3 edges.
# Q-CB16RST (10-19): MUT 8 = region c1r2's regional reset released one edge late (must FAIL).
# SQC-CB8 10-22: QC_VARIANT=b8 / b8n benches the CB8 fabric (qc_gen.py --variant; 8 K-slices, 3 node levels); default b16.
set -uo pipefail
OUT=$(mkdir -p "$1" && realpath "$1")
V=${VERILATOR:-verilator}
case "${QC_VARIANT:-b16}" in
  b16) FAB=qfd_c_b16_dv_fabric; TB=tb_qcluster_fabric; LATH=qcluster_lat.svh; NK=16 ;;
  b8)  FAB=qfd_c_b8_dv_fabric;  TB=tb_qcluster_b8_fabric;  LATH=qcluster_b8_lat.svh;  NK=8 ;;
  b8n) FAB=qfd_c_b8n_dv_fabric; TB=tb_qcluster_b8n_fabric; LATH=qcluster_b8n_lat.svh; NK=8 ;;
  *) echo "unknown QC_VARIANT"; exit 2 ;;
esac
SRC=(rtl/physical/qcluster/qfd_c_stn.sv rtl/physical/qcluster/qfd_q3h_stn.sv rtl/physical/qcluster/qfd_c_land.sv rtl/physical/qcluster/$FAB.sv
     rtl/qwen_sys/dvm_20261014/ot_qfd_xslice_slots.sv rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv rtl/hdc/ot_hdc_delay.sv
     rtl/physical/ot_qwen_tile_node.sv rtl/lib/ot_rst_relay.sv rtl/hdc/ot_qwen_w12_matvec.sv
     rtl/hdc/ot_hdc_fp32_add_lat_nr.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/proto/ot_fp32_add_rne_pipe.sv
     rtl/test/tb_q3h_tile_face.sv rtl/test/$TB.sv)
python3 tools/qwen_cluster/vectors.py "$OUT" $NK
{ sha256sum "${SRC[@]}" rtl/test/$LATH rtl/test/q3h_cb16_tbdefs.svh "$0" tools/qwen_cluster/vectors.py; "$V" --version; } > "$OUT/sources.sha256"
rc=0
for MUT in 0 1 2 3 4 5 6 7 8; do
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
