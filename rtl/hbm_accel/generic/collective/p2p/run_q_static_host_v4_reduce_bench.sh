#!/usr/bin/env bash
# Host V4 native reduce bench (q2 host parent, QID 1): positive + 2 mutants.
# Simulator: Verilator 5.050 (H-NETLIST/idxreg 2026-10-16). Icarus 11 reports a SPURIOUS reduce_fault at compiled
# cycle 33 on this parent -- on origin/main 9ac2560f0 with the plain ring as well (u_reduce, not the ring; the
# same Icarus propagation defect as tb_hgi_coll_native_vm, 1c1ce750b) -- so the verdict is taken under Verilator.
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=${HCOLL_ROOT:-$(git -C "$HERE" rev-parse --show-toplevel)}
OUT=$(realpath -m "${1:?output directory}")
mkdir -p "$OUT"
p=$ROOT/rtl/hbm_accel/generic/collective/p2p
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x "$vl" ] || vl=verilator
src=("$p/tb_hgi_coll_q_static_host_v4_reduce.sv" "$p/ot_hfd_coll_q2_static_host_v4.sv"
   "$p/ot_hgi_coll_static_program_target.sv" "$p/ot_hfd_coll_q_static_v4.sv" "$p/ot_hgi_coll_static_issuer.sv"
   "$p/ot_hgi_coll_qslots.sv" "$p/ot_hgi_coll_pring_static.sv" "$p/ot_hgi_coll_pring_captured_static.sv"
   "$p/ot_hgi_coll_pring_static_state_capture.sv" "$p/ot_hgi_coll_reduce_static.sv"
   "$p/ot_hgi_coll_static_vmwrite.sv" "$p/ot_hgi_coll_static_link_capture.sv" "$p/ot_hgi_coll_static_capture_ctl.sv"
   "$p/ot_hgi_coll_static_pinreg_ctl.sv" "$p/ot_hgi_coll_static_pinreg_store.sv" "$p/ot_hgi_coll_static_seq_ctl.sv"
   "$ROOT/rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv" "$ROOT/rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv"
   "$ROOT/rtl/hdc/ot_hdc_fp32_add_lat.sv" "$ROOT/rtl/hdc/ot_hdc_prefix.sv" "$ROOT/rtl/hdc/ot_hdc_fastfp.sv"
   "$ROOT/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v")
sha256sum "${src[@]}" > "$OUT/sources.sha256"
for mutant in 0 1 2;do
  "$vl" --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -GMUT="$mutant" --top-module tb_hgi_coll_q_static_host_v4_reduce \
   --Mdir "$OUT/obj$mutant" "${src[@]}" > "$OUT/m$mutant.compile.log" 2>&1 || { tail -20 "$OUT/m$mutant.compile.log";exit 2; }
  set +e
  "$OUT/obj$mutant/Vtb_hgi_coll_q_static_host_v4_reduce" > "$OUT/m$mutant.log" 2>&1
  rc=$?
  set -e
  grep -vE '^- ' "$OUT/m$mutant.log" || true
  if [[ "$mutant" == 0 ]];then
   [[ "$rc" == 0 ]] && grep -q '^HCOLL_Q2_HOST_V4_NATIVE_REDUCE PASS' "$OUT/m$mutant.log" || { echo 'positive FAILED';exit 1; }
  else
   [[ "$rc" != 0 ]] && ! grep -q '^HCOLL_Q2_HOST_V4_NATIVE_REDUCE PASS' "$OUT/m$mutant.log" || { echo 'mutant survived';exit 1; }
   echo "Host V4 reduction mutant $mutant rejected"
  fi
  rm -rf "$OUT/obj$mutant"
done
echo HCOLL_Q2_HOST_V4_REDUCE_GATE_PASS
