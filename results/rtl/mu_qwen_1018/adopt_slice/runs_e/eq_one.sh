#!/usr/bin/env bash
# eq lockstep qfd_dv_slice2_e (SU_LT 1, HD_W130 1, MU_NU 4) vs regenerated qfd_dv_slice2_e_lpf (MU_NU 4), + MUT1/MUT3 defines; and dv_bench2 m/f/j on the HEAD slice (SU_LT/HD_W130 1, MU_NU 4)
set -u; export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH; O=$1; mkdir -p $O; verilator --version > $O/verilator_version.txt
S="rtl/qwen_dv/qfd_dv_slice2_e_lpf.sv rtl/qwen_dv/qfd_dv_slice2_lpf_parts.sv rtl/qwen_dv/qfd_dv_slice2_faces.sv rtl/qwen_dv/qfd_dv_slice2.sv rtl/qwen_dv/mu/qfd_dv_amax_mu.sv rtl/qwen_dv/qfd_dv_redstn2.sv rtl/qwen_dv/qfd_dv_scalar2.sv rtl/qwen_dv/qfd_dv_vm.sv rtl/qwen_dv/qfd_dv_stream.sv rtl/qwen_dv/qfd_dv_su8_entries.sv rtl/qwen_dv/qfd_dv_heads.sv rtl/hdc/ot_hdc_vstream_lane.sv rtl/hdc/ot_hdc_vreduce.sv rtl/physical/ot_hdc_vred_pending_guard.sv rtl/hdc/ot_hdc_sfu_q.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv rtl/lib/ot_rst_pipe.sv rtl/qwen_dv/qfd_dv_su_lane.sv rtl/test/full_sm_service/sram_models.sv rtl/test/hbm_rf_visibility/scale_sram_model.sv rtl/hdc/ot_hdc_vstream_lane_t.sv rtl/hdc/ot_hdc_vstream_sfu_t.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/physical/ot_hdc_vstream_lane_clock_entries_candidate.sv rtl/test/qwen_dv/tb_qfd_dv_slice2_e_lpf.sv"
for f in $S; do [ -f $f ] || echo "MISSING $f"; done
c=$2
case $c in
eq*) m=${c#eq}; d=""; [ $m -gt 0 ] && d="+define+OT_LPF_MUT$m"
  verilator --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style $d --top-module tb_qfd_dv_slice2_e_lpf $S -Mdir $O/eq$m > $O/eq${m}_build.log 2>&1 && $O/eq$m/Vtb_qfd_dv_slice2_e_lpf > $O/eq$m.log 2>&1; echo "eq MUT $m: $(grep -o 'LPF_EQ [A-Z]*.*' $O/eq$m.log | head -1)" ;;
b2) python3 rtl/test/qwen_dv/dv_bench2.py f j m o --vflags "-GSU_LT=1 -GHD_W130=1 -GMU_NU=4" --work $O/b2_nu4 > $O/b2_nu4.log 2>&1; echo "b2 nu4: $(grep 'bench2' $O/b2_nu4.log | tr '\n' ';')" ;;
esac
