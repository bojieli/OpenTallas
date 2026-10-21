#!/usr/bin/env bash
# HBM-BANKLAT-IDX 2026-10-19: benches of the IDX VM clients at the d4g GEN2c latency BUDGET
# (results/arch/hbm_banklat_1019/idx_budget.json; faces bank pin flop + die lanes padded to the budget).
#   run_banklat_idx.sh OUT CASE      one case; prints its result line; exit 0 iff it PASSes
#   run_banklat_idx.sh OUT all       every case: PASS cases must pass, mutants must fail -> BANKLAT_IDX_BENCH PASS|FAIL
# Cases (PASS): n12_dir (reader VM_RT_EXTRA 171, direct per-bank lanes), n12_ctl (reader 171 behind the root share
#   VM_RT 65), topk (root share TOPK at VM_RT 65 / CR_RT 36), am0/am1/am2 (ARGMAX r2 VMX 77 / ACK 52 behind the share,
#   TIES 0/1/2), reg_n12 + reg_topk1 (the as-built benches: n12 default, rootctl_am VMX 1 -- the defaults are unchanged).
# Mutants (must FAIL): n12_dir_m1 (reader at the old 4), n12_dir_m2 (one bank lane unpadded), n12_dir_m3 (reader 170),
#   n12_ctl_m4 (share at the am_pin VM_RT 1), topk_pin (share VM_RT 1 / CR_RT 1 on the budget lanes), topk_vm64, topk_cr35,
#   am_vmx5 (as-built r2), am_vmx76, am_ack51.
set -u
root=$(cd "$(dirname "$0")/../../.." && pwd); cd "$root"
out=$(realpath -m "${1:-/tmp/banklat-idx}"); case_=${2:-all}; mkdir -p "$out"
IDX=(rtl/hbm_accel/index/quad_1017/ot_hbm_idx_rootctl_static.sv rtl/hbm_accel/index/quad_1017/ot_hbm_idx_rootctl_static_am.sv
     rtl/hbm_accel/index/ot_hbm_idx_calendar_static.sv rtl/hbm_accel/index/ot_hbm_idx_topk_static.sv rtl/hbm_accel/generic/idx/ot_hgi_idx_tk2.sv
     rtl/hbm_accel/index/ot_hbm_idx_vm_share_static.sv rtl/hbm_accel/index/ot_hbm_idx_vm_share_static_amr.sv rtl/lib/ot_rst_relay.sv
     physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v)
AM=(rtl/hbm_accel/generic/ot_hbm_argmax_static_sw_vm_r2.sv rtl/hbm_accel/generic/ot_hbm_argmax_static_sw_vm.sv
    rtl/hbm_accel/generic/ot_hbm_argmax_static.sv physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_m.sv
    physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_value_m.sv physical/hbm_mtp/rtl/ot_dshbm_argmax_m.sv rtl/gpu/ot_gpu_fadd.sv
    rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv)
Q=(rtl/hbm_accel/index/ot_hbm_idx_vm_query_static_n12.sv rtl/hbm_accel/index/ot_hbm_idx_vm_query_static.sv rtl/hbm_accel/index/ot_hbm_idx_vm_static.sv
   rtl/hbm_accel/index/ot_hbm_idx_query_static.sv rtl/hbm_accel/index/ot_hbm_idx_query_owned_native.sv rtl/hbm_accel/index/ot_hbm_idx_actquant_owned_native.sv
   rtl/hdc/ot_hdc_delay_rf.sv physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v
   rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv
   rtl/proto/ot_fp32_add_rne_pipe.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
T=rtl/test/hbm_idx_static
sim() {  # $1 name, $2 pass tag, $3 tb, $4.. iverilog defines/sources
  local n=$1 tag=$2 tb=$3; shift 3
  iverilog -g2012 -o "$out/$n.vvp" "$@" "$tb" > "$out/build_$n.log" 2>&1 || { echo "BUILD FAIL $n"; tail -5 "$out/build_$n.log"; return 2; }
  local r; r=$( (cd "$out/$n.d" && vvp -n "$out/$n.vvp") 2>&1 | grep -Ev '\$finish|^VCD' | tail -4 | tr '\n' ' ')
  echo "CASE $n $r"
  case "$r" in *"$tag PASS"*) return 0;; *) return 1;; esac
}
n12() {  # $1 name, $2 VIA_CTL, $3 MUT
  mkdir -p "$out/$1.d"; [ -f "$out/$1.d/query.hex" ] || python3 tools/hbm_idx_static_query_vectors.py "$out/$1.d" > /dev/null
  sim "$1" IDX_VM_QUERY_N12_LAT $T/tb_vm_query_n12_lat.sv -DVIA_CTL=$2 -DMUT=$3 "${Q[@]}" "${IDX[@]}"
}
topk() { mkdir -p "$out/$1.d"; local n=$1; shift; sim "$n" IDX_AM_TOPK_LAT $T/tb_idx_rootctl_am_topk_lat.sv "$@" "${IDX[@]}"; }
am() { mkdir -p "$out/$1.d"; local n=$1; shift; sim "$n" IDX_AM_PATH_LAT $T/tb_idx_rootctl_am_path_lat.sv "$@" "${IDX[@]}" "${AM[@]}"; }
run() {
  case "$1" in
    n12_dir) n12 n12_dir 0 0;; n12_dir_m1) n12 n12_dir_m1 0 1;; n12_dir_m2) n12 n12_dir_m2 0 2;; n12_dir_m3) n12 n12_dir_m3 0 3;;
    n12_ctl) n12 n12_ctl 1 0;; n12_ctl_m4) n12 n12_ctl_m4 1 4;;
    topk) topk topk;; topk_pin) topk topk_pin -DVM_RT_P=1 -DCR_RT_P=1;; topk_vm64) topk topk_vm64 -DVM_RT_P=64;;
    topk_cr35) topk topk_cr35 -DCR_RT_P=35;;
    am0) am am0 -DTIES=0;; am1) am am1 -DTIES=1;; am2) am am2 -DTIES=2;;
    am_vmx5) am am_vmx5 -DVMX_P=5;; am_vmx76) am am_vmx76 -DVMX_P=76;; am_ack51) am am_ack51 -DACK_P=51;;
    reg_n12) bash $T/run_vm_query_n12.sh "$out/reg_n12" 0 | grep "^IDX_VM_QUERY_N12 "; return ${PIPESTATUS[0]};;
    reg_topk1) env VMX=1 bash $T/run_idx_rootctl_am.sh "$out/reg_topk1" topk 0; return $?;;
    *) echo "unknown case $1"; return 2;;
  esac
}
if [ "$case_" != all ]; then run "$case_"; exit $?; fi
rc=0
for c in n12_dir n12_ctl topk am0 am1 am2 reg_n12 reg_topk1; do run $c || rc=1; done
for c in n12_dir_m1 n12_dir_m2 n12_dir_m3 n12_ctl_m4 topk_pin topk_vm64 topk_cr35 am_vmx5 am_vmx76 am_ack51; do run $c; [ $? -eq 1 ] || rc=1; done
[ $rc -eq 0 ] && echo "BANKLAT_IDX_BENCH PASS" || echo "BANKLAT_IDX_BENCH FAIL"; exit $rc
