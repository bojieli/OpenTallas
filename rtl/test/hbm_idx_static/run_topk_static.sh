#!/usr/bin/env bash
# Static IDX.TOPK gate on the actual SW VM slice (H-IDX 2026-10-15). usage: run_topk_static.sh OUT [random_count] [seed]
# MUT0 must PASS; MUT1..6 (rank by score, ties high, lanes skipped, capture early, split write dropped, ack early) must FAIL.
# PIN_IN=1 (env; VEH-TOPKFIX 10-19): pin-registered banks (d4g faces) + rootctl share; adds S1 (share owner one edge
# short = the stale non-face share timing) which must FAIL. MUT4 / MUT6 at PIN_IN 1 = the stale n+8 capture / ACK 12.
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd); cd "$root"
out=$(realpath -m "${1:?out}"); cnt=${2:-24}; seed=${3:-0}; pin=${PIN_IN:-0}; mkdir -p "$out"
python3 tools/hbm_idx_topk_static_vectors.py "$out/vec" "$cnt" "$seed" "$pin" | tee "$out/vectors.log"
src=(rtl/hbm_accel/index/ot_hbm_idx_topk_static.sv rtl/hbm_accel/index/ot_hbm_idx_vm_share_static.sv rtl/hbm_accel/generic/idx/ot_hgi_idx_tk2.sv
 rtl/hbm_accel/generic/vm/static/hfd_hgi_vms_static.sv rtl/hbm_accel/generic/vm/static/ot_vms_slice_static.sv
 rtl/hbm_accel/generic/vm/static/ot_vms_hub_static.sv rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv
 rtl/hbm_accel/generic/vm/static/ot_vms_rstop_static.sv rtl/hbm_accel/generic/vm/static/ot_vms_rcl_static.sv
 rtl/hbm_accel/generic/vm/static/ot_vms_status_static.sv
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
 rtl/test/hbm_idx_static/tb_idx_topk_static.sv)
D=rtl/hbm_accel/generic/vm/static   # PIN_IN 1: the strapped native physical banks (as run_parent_pin.sh)
[ "$pin" = 0 ] || src+=($D/ot_vms_ce_counter_pipe.sv $D/ot_vms_bank_static_strap.sv $D/ot_vms_bank_native_physical.sv
 $D/physical/hfd_vms_bank_native_q*.sv $D/wq_merge/hfd_vms_wq2_merge.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; [ -x "$VL" ] || VL=$(command -v verilator)
rc_all=0
runs="0 1 2 3 4 5 6"; [ "$pin" = 0 ] || runs="$runs S1"
for m in $runs; do
  case $m in S*) G="-GMUT=0 -GSMUT=${m#S}";; *) G="-GMUT=$m";; esac
  # Verilator (H-NETLIST 0600): Icarus 11 leaves the engine's dp[7] array-word continuous read X (same defect as the
  # ARGMAX SW gate, run_argmax_static_sw.sh); the earlier Icarus PASS ran on Icarus 12.
  "$VL" --binary --timing -Wno-fatal -j 4 --top-module tb_idx_topk_static $G -GPIN_IN=$pin --Mdir "$out/obj$m" "${src[@]}" > "$out/build$m.log" 2>&1
  set +e; (cd "$out/vec" && "$out/obj$m/Vtb_idx_topk_static") > "$out/run$m.log" 2>&1; rc=$?; set -e
  grep IDX_TOPK_STATIC "$out/run$m.log" || tail -3 "$out/run$m.log"
  if [ $m = 0 ]; then [ $rc = 0 ] || rc_all=1; else [ $rc != 0 ] || { echo "MUT$m NOT KILLED"; rc_all=1; }; fi
  rm -rf "$out/obj$m"
done
sha256sum "${src[@]}" tools/hbm_idx_topk_static_vectors.py > "$out/sources.sha256"
[ $rc_all = 0 ] && echo "IDX_TOPK_STATIC GATE PASS" || { echo "IDX_TOPK_STATIC GATE FAIL"; exit 1; }
