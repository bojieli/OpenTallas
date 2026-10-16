#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT=$(realpath -m "${1:?output directory}")
D="$ROOT/rtl/hbm_accel/generic/vm/static"
mkdir -p "$OUT"
src=("$D/hfd_hgi_vms_static.sv" "$D/ot_vms_slice_static.sv" "$D/ot_vms_bank_strap_physical.sv"
 "$D/ot_vms_bank_static_strap.sv" "$D/ot_vms_ce_counter_pipe.sv"
 "$D/ot_vms_hub_static.sv" "$D/ot_vms_rstop_static.sv" "$D/ot_vms_rcl_static.sv" "$D/ot_vms_status_static.sv"
 "$ROOT/physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v"
 "$D/identity/tb_hbm_vm_strap_parent.sv")
for q in 0 1 2 3; do src+=("$D/physical/hfd_vms_bank_strap_q$q.sv");done
for shape in 0:5:1 1:4:1 2:6:3 3:6:3; do
 IFS=: read -r sid rg wg <<< "$shape"
 for mut in 0 3 4 5; do
  stem="q${sid}_m${mut}"
  iverilog -g2012 -s tb_hbm_vm_strap_parent -Ptb_hbm_vm_strap_parent.SID="$sid" -Ptb_hbm_vm_strap_parent.RG="$rg" -Ptb_hbm_vm_strap_parent.WG="$wg" -Ptb_hbm_vm_strap_parent.MUT="$mut" -o "$OUT/$stem.vvp" "${src[@]}" >"$OUT/$stem.compile.log" 2>&1
  set +e
  vvp "$OUT/$stem.vvp" >"$OUT/$stem.log" 2>&1
  rc=$?
  set -e
  if [[ $mut == 0 ]]; then [[ $rc == 0 ]];grep 'VM_STRAP_PARENT PASS' "$OUT/$stem.log"
  else [[ $rc != 0 ]];grep -m1 -E 'FATAL:.*(bank fault|DMA commit phase|response group mismatch)' "$OUT/$stem.log";fi
  rm "$OUT/$stem.vvp"
 done
done
printf 'PASS actual4quadrant die masters with8physical strap bank children each; wrongbank/wrongslice/missingbankclock rejected\n'
