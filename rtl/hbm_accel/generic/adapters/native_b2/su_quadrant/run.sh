#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../../../../../.."
root=$(pwd);out=${1:?output};mut=${2:-0};phase=${3:-61};mkdir -p "$out"
d=rtl/hbm_accel/generic/vm/b2;q=rtl/hbm_accel/generic/adapters/native_b2/su_quadrant
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$v" --binary --timing -O2 -j "${JOBS:-4}" -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-UNOPTFLAT -Wno-MULTIDRIVEN -Wno-LATCH -Wno-WIDTHCONCAT -Wno-CASEINCOMPLETE --top-module tb_hbm_b2_su_vm4 -GMUT="$mut" -GPHASE="$phase" --Mdir "$out/obj_${mut}_${phase}" \
 "$q/ot_hgi_su_ctlw_native_q.sv" "$q/ot_hbm_b2_lane_cdc.sv" "$q/ot_hbm_b2_su_vm4.sv" "$q/tb_hbm_b2_su_vm4.sv" \
 rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo_p2.sv "$d/ot_vms_bank.sv" "$d/ot_vms_hub.sv" "$d/ot_vms_rstop.sv" "$d/ot_vms_rcl.sv" "$d/ot_vms_star.sv" "$d/ot_vms_relay.sv" "$d/ot_vms_slice.sv" rtl/link/ot_fifo_sram_fwft.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_64x16_m1/ot_sram_1r1w_64x16_m1.v physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v > "$out/build_${mut}_${phase}.log" 2>&1 || { tail -35 "$out/build_${mut}_${phase}.log";exit 2; }
set +e
"$out/obj_${mut}_${phase}/Vtb_hbm_b2_su_vm4" > "$out/run_${mut}_${phase}.log" 2>&1
rc=$?
set -e
cat "$out/run_${mut}_${phase}.log"
if [ "$rc" -ne 0 ];then exit "$rc";fi
grep -q '^NATIVE_SU_VM4 PASS' "$out/run_${mut}_${phase}.log"
