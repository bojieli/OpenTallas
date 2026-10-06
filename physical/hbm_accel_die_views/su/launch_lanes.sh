#!/bin/bash
# CLAUDE HBM-ABSTRACTS (hub): r2 lane re-harden variants (route_lane.sh defaults: signals M2-M5, pins M4 left edge,
# PDN top M6).  Footprints: x on the 0.432 um grid, y on 0.54; every variant fits its quarter (r16g hfd_su 703.272 /
# hfd_sfu 398.712 / hfd_hc 275.592 x 5529.576) as 6 / 2 / 2 columns of 32 / 16 / 44 lanes with >= 30 um channels and
# 10 um edge strips.     launch_lanes.sh <scratch base> <src dir name> light|sfu|hc
E=$1; SRC=$2; cd $E
SU="rtl/hdc/v41x/phys/ot_hdc_v41x_su_c12_phys.sv rtl/hdc/v41x/ot_hdc_v41x_vec_lane_c12.sv rtl/hdc/v41x/ot_hdc_v41x_sfu_c12.sv rtl/hdc/v41x/ot_hdc_v41x_vec_side_c12.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/v41/ot_hdc_softplus.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat_c12.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv rtl/hdc/v41x/ot_dsrom_su_f12.sv rtl/hdc/v41/ot_hdc_fsqrt_c12.sv rtl/hdc/v41/ot_hdc_fsqrt.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv"
K="ot_hdc_fp32_mul_f12_l6 ot_hdc_fp32_add_f12_l6x ot_dsrom_fdiv_f12 ot_hdc_fsqrt_c12"
HCS="rtl/hdc/v41x/ot_dsrom_su_hcpost.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_delay.sv"
RL=$E/$SRC/physical/hbm_accel_die_views/su/route_lane.sh
case $3 in
light) for v in "a:75.6:162.0" "b:79.92:162.0" "c:84.24:162.0" "d:88.56:162.0"; do l=${v%%:*}; r=${v#*:}; R=$E SRC=$SRC SRCS="$SU" KEEP="$K" CORES=8 NEED=14 nohup $RL l2light_$l ot_su12_light ${r%%:*} ${r#*:} > l2light_$l.launch 2>&1 & done;;
sfu) for v in "a:164.16:320.76" "b:159.84:330.48" "c:168.48:313.2"; do l=${v%%:*}; r=${v#*:}; R=$E SRC=$SRC SRCS="$SU" KEEP="$K" CORES=12 NEED=24 nohup $RL l2sfu_$l ot_su12_sfu ${r%%:*} ${r#*:} > l2sfu_$l.launch 2>&1 & done;;
hc) for v in "a:85.32:115.02" "b:90.72:110.16" "c:79.92:120.42"; do l=${v%%:*}; r=${v#*:}; R=$E SRC=$SRC SRCS="$HCS" CORES=6 NEED=8 nohup $RL l2hc_$l ot_dsrom_su_hcpost_lane ${r%%:*} ${r#*:} --param ML=5 --param AL=5 > l2hc_$l.launch 2>&1 & done;;
esac
