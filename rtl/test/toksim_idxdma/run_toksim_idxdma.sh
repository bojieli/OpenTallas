#!/usr/bin/env bash
# TOKSIM-HBM-idxdma 2026-10-19: production-shape cycle benches (Verilator 5.050) of the die-bound IDX root / argmax / DMA back.
#   run_toksim_idxdma.sh OUT CASE
#   topk_bound   rootctl_am VM_RT 0 / CR_RT 0 (as bound in GEN2e3 die.v) on its contract VM (RD 7, ack 11)
#   topk_faces   VM_RT 1 / CR_RT 1 (= rootctl_am_pin, d4g faces banks, zero die lanes)
#   topk_budget  VM_RT 65 / CR_RT 36 (HBM-BANKLAT-IDX GEN2c budget, die lanes padded)
#   am_ds_bound / am_ds_budget / am_qw_bound / am_qw_budget   ARGMAX.LOCAL n 1347 / 37984 (VM mode)
#     bound: VMX 5 / ACK 13 / lanes 0; budget: root VM_RT 65, LAQ 4, LAR 3, VMX 77, ACK 52
#   pc_<reqs>x<len>_rl<RL>   DMA.LOAD HBM side: PC controller leaf h9b, <reqs> back-to-back k requests of <len> beats, DRAM read latency RL
#   dma_kvwb_bound|budget, dma_st8_bound|budget, dma_st32_bound|budget   dbk moves (bound = RR_RT 7 bare bank; budget = RR_RT 80 + GEN2c NE lanes)
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd); cd "$root"
out=$(realpath -m "${1:?out}"); c=${2:?case}; mkdir -p "$out/$c"; o=$out/$c
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; [ -x "$VL" ] || VL=$(command -v verilator)
"$VL" --version | tee "$o/verilator.txt"
W="-Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN"
T=rtl/test/toksim_idxdma
IDX=(rtl/hbm_accel/index/quad_1017/ot_hbm_idx_rootctl_static_am.sv rtl/hbm_accel/index/quad_1017/ot_hbm_idx_rootctl_static.sv rtl/hbm_accel/generic/ot_hbm_argmax_static_sw_vm.sv rtl/hbm_accel/generic/ot_hbm_argmax_static.sv rtl/hbm_accel/index/ot_hbm_idx_calendar_static.sv
     rtl/hbm_accel/index/ot_hbm_idx_topk_static.sv rtl/hbm_accel/generic/idx/ot_hgi_idx_tk2.sv
     rtl/hbm_accel/index/ot_hbm_idx_vm_share_static.sv rtl/hbm_accel/index/ot_hbm_idx_vm_share_static_amr.sv rtl/lib/ot_rst_relay.sv
     physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
     rtl/hbm_accel/generic/ot_hbm_argmax_static_sw_vm_r2.sv physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_m.sv
     physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_value_m.sv physical/hbm_mtp/rtl/ot_dshbm_argmax_m.sv rtl/gpu/ot_gpu_fadd.sv
     rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv)
idx() { # kind N defines...
  local kind=$1 n=$2; shift 2
  python3 $T/toksim_idx_vectors.py "$o" "$kind" "$n" 4 | tee "$o/vectors.log"
  "$VL" --binary --timing -j 8 $W "$@" --top-module tb_toksim_idx --Mdir "$o/obj" "${IDX[@]}" $T/tb_toksim_idx.sv > "$o/build.log" 2>&1 || { tail -30 "$o/build.log"; exit 2; }
  (cd "$o" && ./obj/Vtb_toksim_idx) > "$o/run.log" 2>&1 || true
  grep -E 'TOKSIM|MISMATCH' "$o/run.log"; sha256sum "${IDX[@]}" $T/tb_toksim_idx.sv $T/toksim_idx_vectors.py > "$o/sources.sha256"; rm -rf "$o/obj"
  grep -q 'TOKSIM_IDX PASS' "$o/run.log"
}
D=rtl/hbm_accel/generic/peers/static; M=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
dma() { # moves defines...
  local mv=$1; shift
  "$VL" --binary --timing -j 8 $W -DMOVES=$mv "$@" --top-module tb_toksim_dma_store -Mdir "$o/obj" -o sim "$M" $D/ot_hgi_dma_back_static_vp_banks.sv \
    $D/ot_hgi_dma_back_static_vp4_banks.sv $T/tb_toksim_dma_store.sv > "$o/build.log" 2>&1 || { tail -30 "$o/build.log"; exit 2; }
  "$o/obj/sim" > "$o/run.log" 2>&1 || true
  grep -E 'TOKSIM|BANKLAT (PASS|FAIL)' "$o/run.log"; sha256sum "$M" $D/ot_hgi_dma_back_static_vp_banks.sv $D/ot_hgi_dma_back_static_vp4_banks.sv $T/tb_toksim_dma_store.sv > "$o/sources.sha256"; rm -rf "$o/obj"
  grep -q 'BANKLAT PASS' "$o/run.log"
}
SV=rtl/hbm_accel/loader/service_native
PC=($SV/ot_hbm_svc_pc_ctrl_leaf_cfg_h9b.sv rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc_strap_h9.sv $SV/ot_hbm_svc_pin_skid2_h9.sv
    $SV/ot_hbm_svc_ring_h9b.sv $SV/ot_hbm_svc_ring_h9b_ff.sv rtl/lib/ot_rst_relay.sv $M)
pc() { # RL NREQ LEN
  "$VL" --binary --timing -j 8 $W -GRL=$1 -GNREQ_REC=$2 -GLEN=$3 --top-module tb_toksim_pc_load -Mdir "$o/obj" -o sim "${PC[@]}" $T/tb_toksim_pc_load.sv > "$o/build.log" 2>&1 || { tail -30 "$o/build.log"; exit 2; }
  "$o/obj/sim" > "$o/run.log" 2>&1 || true
  grep -E 'TOKSIM|MISMATCH|FAULT' "$o/run.log" | head -20; sha256sum "${PC[@]}" $T/tb_toksim_pc_load.sv > "$o/sources.sha256"; rm -rf "$o/obj"
  grep -q 'TOKSIM_PC_LOAD PASS' "$o/run.log"
}
BUD="-DRR_RT=80 -DDIE_RT=80 -DFACES_D=8 -DLANES=1"
case $c in
  topk_bound) idx topk 384;;
  topk_faces) idx topk 384 -DVM_RT=1 -DCR_RT=1;;
  topk_budget) idx topk 384 -DVM_RT=65 -DCR_RT=36;;
  am_ds_bound) idx argmax 1347 -DKIND_ARGMAX;;
  am_qw_bound) idx argmax 37984 -DKIND_ARGMAX;;
  am_ds_budget) idx argmax 1347 -DKIND_ARGMAX -DVM_RT=65 -DCR_RT=36 -DLAQ=4 -DLAR=3 -DVMX_P=77 -DACK_P=52;;
  am_qw_budget) idx argmax 37984 -DKIND_ARGMAX -DVM_RT=65 -DCR_RT=36 -DLAQ=4 -DLAR=3 -DVMX_P=77 -DACK_P=52;;
  dma_kvwb_bound) dma 1;; dma_kvwb_budget) dma 1 $BUD;;
  dma_st8_bound) dma 2;; dma_st8_budget) dma 2 $BUD;;
  dma_st32_bound) dma 3;; dma_st32_budget) dma 3 $BUD;;
  pc_1x1_rl23) pc 23 1 1;; pc_1x4_rl23) pc 23 1 4;; pc_4x4_rl23) pc 23 4 4;; pc_40x4_rl23) pc 23 40 4;; pc_64x4_rl23) pc 23 64 4;;
  pc_1x1_rl14) pc 14 1 1;; pc_40x4_rl14) pc 14 40 4;;
  *) echo "unknown case $c"; exit 2;;
esac
