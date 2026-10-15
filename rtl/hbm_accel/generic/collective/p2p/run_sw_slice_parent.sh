#!/usr/bin/env bash
# SW slice-parent gate: whole ot_hfd_coll_q3_static_host_v4 + whole hfd_hgi_vms_static_SW via the v15 contract edges.
# MUT0 must PASS; MUT1..4 must FAIL. usage: run_sw_slice_parent.sh OUT
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=${HCOLL_ROOT:-$(cd "$HERE/../../../../.." && pwd)}
OUT=$(realpath -m "${1:?output directory}"); mkdir -p "$OUT"
p=$ROOT/rtl/hbm_accel/generic/collective/p2p; v=$ROOT/rtl/hbm_accel/generic/vm/static; t=$ROOT/rtl/hbm_accel/generic/collective/tkm
src=("$p/tb_hgi_coll_sw_slice_parent.sv" "$p/ot_hfd_coll_q3_static_host_v4.sv" "$p/ot_hgi_coll_static_program_target.sv"
 "$p/ot_hfd_coll_q_static_v4.sv" "$p/ot_hgi_coll_static_issuer.sv" "$p/ot_hgi_coll_qslots.sv" "$p/ot_hgi_coll_pring_static.sv"
 "$p/ot_hgi_coll_reduce_static.sv" "$p/ot_hgi_coll_argmax_static.sv" "$ROOT/rtl/hbm_accel/generic/collective/ot_hgi_coll_amerge.sv"
 "$p/ot_hgi_coll_static_vmwrite.sv" "$p/ot_hgi_coll_static_link_capture.sv" "$p/ot_hgi_coll_static_capture_ctl.sv"
 "$p/ot_hgi_coll_static_pinreg_ctl.sv" "$p/ot_hgi_coll_static_pinreg_store.sv" "$p/ot_hgi_coll_static_seq_ctl.sv"
 "$t/ot_hgi_coll_tkm_static.sv" "$t/ot_hgi_coll_tkm.sv" "$t/ot_hgi_coll_tkm_buffer.sv" "$ROOT/rtl/lib/ot_rst_relay.sv"
 "$ROOT/rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv" "$ROOT/rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv"
 "$ROOT/rtl/hdc/ot_hdc_fp32_add_lat.sv" "$ROOT/rtl/hdc/ot_hdc_prefix.sv" "$ROOT/rtl/hdc/ot_hdc_fastfp.sv"
 "$v/hfd_hgi_vms_static.sv" "$v/ot_vms_slice_static.sv" "$v/ot_vms_hub_static.sv" "$v/ot_vms_bank_static.sv"
 "$v/ot_vms_rstop_static.sv" "$v/ot_vms_rcl_static.sv" "$v/ot_vms_status_static.sv"
 "$ROOT/physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v"
 "$ROOT/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v")
sha256sum "${src[@]}" > "$OUT/sources.sha256"
rc_all=0
for m in ${MUTS:-0 1 2 3 4}; do
  iverilog -g2012 -s tb_hgi_coll_sw_slice_parent -Ptb_hgi_coll_sw_slice_parent.MUT=$m -o "$OUT/m$m.vvp" "${src[@]}" \
    > "$OUT/m$m.compile.log" 2>&1 || { cat "$OUT/m$m.compile.log"; exit 2; }
  set +e; vvp -n "$OUT/m$m.vvp" > "$OUT/m$m.log" 2>&1; rc=$?; set -e
  grep -E 'HCOLL_SW_SLICE_PARENT|FATAL|Fatal|fault|mismatch' "$OUT/m$m.log" | head -3
  if [ $m = 0 ]; then { [ $rc = 0 ] && grep -q '^HCOLL_SW_SLICE_PARENT PASS' "$OUT/m$m.log"; } || rc_all=1
  else [ $rc != 0 ] && ! grep -q '^HCOLL_SW_SLICE_PARENT PASS' "$OUT/m$m.log" && echo "MUT$m rejected" || { echo "MUT$m SURVIVED"; rc_all=1; }; fi
  rm -f "$OUT/m$m.vvp"
done
[ $rc_all = 0 ] && echo "HCOLL_SW_SLICE_PARENT GATE PASS" || { echo "HCOLL_SW_SLICE_PARENT GATE FAIL"; exit 1; }
