#!/usr/bin/env bash
# Lane HBM-IDXAM 10-18: ot_hbm_idx_rootctl_static_am (d4g idx_ctl, merged 264-b argmax word) benches.
#   run_idx_rootctl_am.sh OUT              -> full: bench 1 (structural, AMMUT 0) + bench 2 path at TIES 0/1/2 (AMMUT 0)
#                                             + bench 3 TOPK path (AMMUT 0) PASS, and every mutant FAILS: bench 1
#                                             AMMUT 1..4, 6, 7, bench 2 TIES 1 AMMUT 4, bench 3 AMMUT 5
#                                             -> prints IDX_ROOTCTL_AM_BENCH PASS|FAIL
#   r3 (lane HBM-IDXAM2 10-18): pin-registered boundary (share ot_hbm_idx_vm_share_static_amr); bench 3 added.
#   run_idx_rootctl_am.sh OUT eq <m>       -> bench 1 only at AMMUT=<m> (exit 0 iff IDX_ROOTCTL_AM PASS)
#   run_idx_rootctl_am.sh OUT path <t> <m> -> bench 2 only at TIES=<t> AMMUT=<m> (exit 0 iff IDX_AM_PATH PASS)
#   run_idx_rootctl_am.sh OUT topk <m>     -> bench 3 only at AMMUT=<m> (exit 0 iff IDX_AM_TOPK PASS)
#   VMX=1 (env; VEH-TOPKFIX2 10-19): pin-registered d4g VM banks (benches 1 and 3 run REF rootctl PIN_IN 1 vs DUT
#   rootctl_am VM_RT 1 / CR_RT 1 = ot_hbm_idx_rootctl_static_am_pin on a VM model RD 8 / ACKD 12); bench 2 (ARGMAX path,
#   r2 consumer VMX not shifted here) runs only at VMX 0; extra mutant: bench 3 DUT_RT 0 (the r3 master on faces banks)
#   must FAIL.
set -u
VMX=${VMX:-0}
out=${1:-$(mktemp -d)}; mode=${2:-full}; mkdir -p "$out"
IDX=(rtl/hbm_accel/index/quad_1017/ot_hbm_idx_rootctl_static.sv rtl/hbm_accel/index/quad_1017/ot_hbm_idx_rootctl_static_am.sv rtl/hbm_accel/index/quad_1017/ot_hbm_idx_rootctl_static_am_pin.sv
     rtl/hbm_accel/index/ot_hbm_idx_calendar_static.sv rtl/hbm_accel/index/ot_hbm_idx_topk_static.sv rtl/hbm_accel/generic/idx/ot_hgi_idx_tk2.sv
     rtl/hbm_accel/index/ot_hbm_idx_vm_share_static.sv rtl/hbm_accel/index/ot_hbm_idx_vm_share_static_amr.sv rtl/lib/ot_rst_relay.sv
     physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v)
AM=(rtl/hbm_accel/generic/ot_hbm_argmax_static_sw_vm_r2.sv rtl/hbm_accel/generic/ot_hbm_argmax_static_sw_vm.sv
    rtl/hbm_accel/generic/ot_hbm_argmax_static.sv physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_m.sv
    physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_value_m.sv physical/hbm_mtp/rtl/ot_dshbm_argmax_m.sv rtl/gpu/ot_gpu_fadd.sv
    rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv)
eq() {  # $1 = AMMUT
  iverilog -g2012 -DVMX=$VMX -DAMMUT=$1 -o "$out/eq$1" rtl/test/hbm_idx_static/tb_idx_rootctl_am.sv "${IDX[@]}" > "$out/build_eq$1.log" 2>&1 \
    || { echo "BUILD FAIL eq $1"; tail -5 "$out/build_eq$1.log"; return 2; }
  r=$(vvp -n "$out/eq$1" 2>&1 | grep -Ev '\$finish|^VCD' | tail -2 | tr '\n' ' '); echo "EQ AMMUT=$1 $r"
  case "$r" in *"IDX_ROOTCTL_AM PASS"*) return 0;; *) return 1;; esac
}
path() {  # $1 = TIES, $2 = AMMUT
  iverilog -g2012 -DTIES=$1 -DAMMUT=$2 -o "$out/p$1_$2" rtl/test/hbm_idx_static/tb_idx_rootctl_am_path.sv "${IDX[@]}" "${AM[@]}" \
    > "$out/build_p$1_$2.log" 2>&1 || { echo "BUILD FAIL path $1 $2"; tail -5 "$out/build_p$1_$2.log"; return 2; }
  r=$(vvp -n "$out/p$1_$2" 2>&1 | grep -Ev '\$finish|^VCD' | tail -2 | tr '\n' ' '); echo "PATH TIES=$1 AMMUT=$2 $r"
  case "$r" in *"IDX_AM_PATH PASS"*) return 0;; *) return 1;; esac
}
topk() {  # $1 = AMMUT [$2 = DUT_RT override]
  iverilog -g2012 -DVMX=$VMX ${2:+-DDUT_RT=$2} -DAMMUT=$1 -o "$out/t$1${2:+_rt$2}" rtl/test/hbm_idx_static/tb_idx_rootctl_am_topk.sv "${IDX[@]}" > "$out/build_t$1${2:+_rt$2}.log" 2>&1 \
    || { echo "BUILD FAIL topk $1"; tail -5 "$out/build_t$1${2:+_rt$2}.log"; return 2; }
  r=$(vvp -n "$out/t$1${2:+_rt$2}" 2>&1 | grep -Ev '\$finish|^VCD' | tail -2 | tr '\n' ' '); echo "TOPK AMMUT=$1 $r"
  case "$r" in *"IDX_AM_TOPK PASS"*) return 0;; *) return 1;; esac
}
case "$mode" in
  eq) eq "${3:-0}"; exit $?;;
  path) path "${3:-0}" "${4:-0}"; exit $?;;
  topk) topk "${3:-0}" "${4:-}"; exit $?;;
esac
rc=0
eq 0 || rc=1
[ "$VMX" = 0 ] && for t in 0 1 2; do path $t 0 || rc=1; done
topk 0 || rc=1
for m in 1 2 3 4 6 7; do eq $m; [ $? -eq 1 ] || rc=1; done
if [ "$VMX" = 0 ]; then path 1 4; [ $? -eq 1 ] || rc=1; fi
topk 5; [ $? -eq 1 ] || rc=1
if [ "$VMX" != 0 ]; then topk 0 0; [ $? -eq 1 ] || rc=1; fi
echo "VMX=$VMX"
[ $rc -eq 0 ] && echo "IDX_ROOTCTL_AM_BENCH PASS" || echo "IDX_ROOTCTL_AM_BENCH FAIL"; exit $rc
