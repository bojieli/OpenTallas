#!/bin/bash
# HBM-NEXT-VEH 10-19 step 4: value-exact P = 4 layer front (p4_value_front.py cases) on the hnx RTL. Fleet only,
# Verilator 5.050, run from a bundle root (rtl/ + physical/asap7_memory_macros/ of the lane commit):
#   tools/hbm_next/vehicle/run_value_front.sh CASES OUT
# Per mode (ar N 1, mtp N 6):
#   FUSED  KX 4 MUT 0: pre_emit / post_emit (records as emitted: job_ok broken -> must FAULT = contract witness),
#                      pre_legal / post_legal (job_ok relocation, REAL golden operands) -> HNX_FUSED PASS bit-exact
#          KX 4 MUT 1: pre_legal, post_legal -> HNX_FUSED FAIL (fail witnesses on the real operands)
#   HC     tb_hnx_hc_eng4 MUT 0: hcmix (real fn / x / base / scale, released eps) -> HC_ENG PASS; MUT 1 -> HC_ENG FAIL
set -u
B=$(pwd); C=$(realpath "${1:?CASES}"); O=$(realpath -m "${2:?OUT}"); mkdir -p "$O"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
VL=$(command -v verilator); echo "verilator: $VL $($VL --version)" > "$O/verilator.txt"
V(){ echo "$(date -Is) $*" | tee -a "$O/verdict.txt"; }
V "start host=$(hostname) bundle=$(cat $B/BUNDLE_COMMIT 2>/dev/null)"
FSRC=(rtl/hbm_next/fused/tb/tb_hnx_fused.sv rtl/hbm_next/fused/ot_hnx_fused_eng.sv
  rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv
  rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv
  rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_f12.sv
  rtl/hdc/v41x/ot_dsrom_divc.sv rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv
  rtl/hdc/v41x/ot_dsrom_su_norm.sv rtl/hdc/v41x/ot_dsrom_su_hcpost.sv rtl/hdc/v41/ot_hdc_actquant.sv
  rtl/hdc/v41x/ot_dsrom_aq12.sv rtl/lib/ot_rst_relay.sv)
FVF=(tools/hbm_next/hnx_fused.vlt --hierarchical -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT --top-module tb_hnx_fused)
H=rtl/hbm_next/hc
ESRC=(rtl/hbm_next/hc/tb/tb_hnx_hc_eng4.sv $H/ot_hnx_hc_root.sv $H/ot_hnx_hc_qeng.sv $H/ot_hnx_hc_qcen.sv $H/ot_hnx_hc_bankq.sv
  $H/ot_hnx_hc_eng_seq.sv $H/ot_hnx_hc_bank.sv $H/ot_hnx_hc_tail_unit.sv $H/ot_hnx_hcp_sys1.sv $H/ot_hnx_hgi_hc_tail.sv
  $H/ot_hnx_hc_xw_rx.sv rtl/hbm_accel/die_glue/ot_hbm_rly.sv rtl/hdc/v41x/ot_hdc_v41x_hcp.sv rtl/hdc/ot_hdc_prefix.sv
  rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv
  rtl/hdc/ot_hdc_sfu.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/v41/ot_hdc_sinkhorn.sv
  rtl/hdc/v41/ot_hdc_sk_arith.sv rtl/hdc/v41/ot_hdc_sk_recip_rom.sv
  rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv rtl/lib/ot_rst_relay.sv rtl/hdc/ot_hdc_delay.sv
  physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
  physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v)
fbuild(){ # tag mut
  local d=$O/obj_f$1; rm -rf $d
  verilator --binary --timing -O1 -j 16 "${FVF[@]}" -GKX=4 -GMUT=$2 -Mdir $d -o Vf$1 "${FSRC[@]}" > $O/build_f$1.log 2>&1 || {
    sleep 5; verilator --binary --timing -O1 -j 4 "${FVF[@]}" -GKX=4 -GMUT=$2 -Mdir $d -o Vf$1 "${FSRC[@]}" > $O/build_f$1.log 2>&1; }
  V "build f$1 rc=$? bin=$( [ -x $d/Vf$1 ] && echo ok || echo MISSING)"
}
ebuild(){ # tag mut
  local d=$O/obj_e$1; rm -rf $d
  verilator --binary --timing --hierarchical -j 16 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN \
    --top-module tb_hnx_hc_eng4 +define+MUT=$2 +define+OT_FP_DATA_NORST +define+HC_DRLY=2 +define+HC_XRLY=1 +define+HC_QDRLY=2 \
    -Mdir $d -o Ve$1 rtl/hbm_next/hc/tb/tb_hnx_hc_eng4_hier.vlt "${ESRC[@]}" > $O/build_e$1.log 2>&1 || {
    sleep 5; verilator --binary --timing --hierarchical -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN \
    --top-module tb_hnx_hc_eng4 +define+MUT=$2 +define+OT_FP_DATA_NORST +define+HC_DRLY=2 +define+HC_XRLY=1 +define+HC_QDRLY=2 \
    -Mdir $d -o Ve$1 rtl/hbm_next/hc/tb/tb_hnx_hc_eng4_hier.vlt "${ESRC[@]}" > $O/build_e$1.log 2>&1; }
  V "build e$1 rc=$? bin=$( [ -x $d/Ve$1 ] && echo ok || echo MISSING)"
}
run(){ # bin mode case tag
  local od=$O/$2/$4; rm -rf $od; mkdir -p $O/$2; cp -r $C/$2/$3 $od
  ( cd $od && $1 $(cat plus.txt) > run.log 2>&1; echo RUN_RC=$? >> run.log
    V "$2 $4: $(grep -h 'HNX_FUSED_CYCLES\|HNX_FUSED PASS\|HNX_FUSED FAIL\|HC_MIX_CYCLES\|^HC_ENG PASS\|^HC_ENG FAIL' run.log | head -3 | tr '\n' ' ') $(grep -h MISMATCH run.log | head -1)"
    rm -f vmi.mem wmem.mem xmem.mem )
}
fbuild 0 0 & fbuild 1 1 & ebuild 0 0 & ebuild 1 1 & wait
for m in ar mtp; do
  for c in pre_emit pre_legal post_emit post_legal; do run $O/obj_f0/Vf0 $m $c $c & done
  run $O/obj_f1/Vf1 $m pre_legal pre_legal_mut1 & run $O/obj_f1/Vf1 $m post_legal post_legal_mut1 &
  run $O/obj_e0/Ve0 $m hcmix hcmix & run $O/obj_e1/Ve1 $m hcmix hcmix_mut1 &
done
wait
rm -rf $O/obj_*
V "done"
