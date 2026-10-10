#!/bin/bash
cd "$(dirname "$0")/../../.."
SR="rtl/hdc/v41x/phys/ot_hdc_v41x_su_c12_phys.sv rtl/hdc/v41x/ot_hdc_v41x_vec_lane_c12.sv rtl/hdc/v41x/ot_hdc_v41x_sfu_c12.sv rtl/hdc/v41x/ot_hdc_v41x_vec_side_c12.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/v41/ot_hdc_softplus.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat_c12.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv rtl/hdc/v41x/ot_dsrom_su_f12.sv rtl/hdc/v41/ot_hdc_fsqrt_c12.sv rtl/hdc/v41/ot_hdc_fsqrt.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_delay_ring.sv"
O=${1:-/tmp/sc/su}; M=${2:-0}; N=${3:-1500}; mkdir -p $O
iverilog -g2012 -Ptb_sfu_reset_tree.MUT=$M -Ptb_sfu_reset_tree.NCYC=$N -s tb_sfu_reset_tree -o $O/su$M.vvp $SR tests/rtl/hub_reset/tb_sfu_reset_tree.sv > $O/build$M.log 2>&1 || { echo "SU12_RSTPIPE BUILD_ERROR"; exit 2; }
vvp -n $O/su$M.vvp | grep -E "^SU12_RSTPIPE|MISMATCH" | head -5
