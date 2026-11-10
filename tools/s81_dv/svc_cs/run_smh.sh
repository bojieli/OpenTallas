#!/bin/bash
# run_smh.sh REPO OUTDIR: the existing head-level differential bench tb_smh_fold2 with the box hooks ON
# (-DOT_S81_SVC_CS, contract checks on): ot_s81_su_smh_fold2 against ot_s81_su_smh, real head stimulus.
set -u
R=$1; O=$2; S=$R/rtl; C=$S/dsrom_sys/s81_svc; D=$S/dsrom_sys/s81_dv/su_sm; H=$S/hdc
rm -rf $O; mkdir -p $O
verilator --binary --timing -O2 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module tb_smh_fold2 -Mdir $O/obj -j 8 --unroll-count 4 -fno-dfg \
  -DOT_S81_SVC_CS -DOT_S81_SVC_CS_CHECK -GMUT=0 -CFLAGS -O1 $D/test/tb_smh_fold2.sv $D/ot_s81_su_smh_fold2.sv $D/ot_s81_su_sml_fold2.sv $D/ot_s81_su_smd_fold2.sv \
  $D/ot_s81_su_sms.sv $D/ot_s81_su_smq.sv $D/ot_s81_su_smh.sv $S/dsrom_sys/s81_suhc/hier/ot_s81_su_sm.sv $H/ot_hdc_delay.sv $H/ot_hdc_fastfp_lat_f12.sv \
  $H/ot_hdc_fastfp.sv $H/ot_hdc_fp32_add_lat.sv $H/ot_hdc_fp32_f12.sv $H/ot_hdc_fp32_mul_lat.sv $H/ot_hdc_prefix.sv $H/ot_hdc_sfu.sv $H/v41x/ot_dsrom_fp32_add_l6.sv \
  $H/v41x/ot_dsrom_su_add6.sv $H/v41x/ot_dsrom_su_f12.sv $H/v41x/ot_dsrom_su_fdiv_f12.sv $H/v41x/ot_dsrom_su_softmax_add6.sv $H/v41x/ot_dsrom_su_softmax_add.sv \
  $H/v41x/ot_dsrom_su_softmax_f12r.sv $H/v41x/ot_dsrom_su_softmax_m9.sv $H/v41x/ot_hdc_v41x_sfu.sv $C/ot_s81_svc_fp32_f12_cs.sv $C/ot_s81_svc_exp_cs.sv $C/ot_s81_svc_fdiv_f12_cs.sv \
  $C/ot_s81_su_sml_fold2_cs.sv $C/ot_s81_su_smd_fold2_cs.sv $C/ot_s81_su_smc_cs.sv $C/ot_s81_su_smr_cs.sv > $O/build.log 2>&1 || { echo "BUILD FAIL"; tail -n 15 $O/build.log | cut -c1-200; exit 4; }
$O/obj/Vtb_smh_fold2 > $O/run.log 2>&1; rc=$?; echo "tb_smh_fold2 hooks on: rc=$rc"; grep -E "PASS|FAIL|mismatch|ASSERT|Fatal" $O/run.log | head -n 8 | cut -c1-200; tail -n 2 $O/run.log | cut -c1-200
