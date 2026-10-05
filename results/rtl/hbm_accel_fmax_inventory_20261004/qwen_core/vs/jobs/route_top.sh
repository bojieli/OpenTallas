#!/bin/bash
# Hierarchical route of the Qwen SU (ot_hdc_vstream_rt_f12_hw: controller + reducer flat, 64 lanes as the hardened
# lane macro ot_hdc_vstream_lane_f12_m with its routed LEF + SS/FF ETMs from export_abstract.sh).
# Usage: route_top.sh <label> <src snapshot holding physical/qwen_hbmacc_vs/ot_hdc_vstream_lane_f12_m>
R=/srv/opentallas-scratch/claude/hbm-fmax-qcore
M=ot_hdc_vstream_lane_f12_m; MD=physical/qwen_hbmacc_vs/$M
cd $R
OT_FLOW_TIMEOUT_SECONDS=${TMO:-172800} STAGES=pnr MACRO=$MD NEED=${NEED:-60} CORES=${CORES:-24} UTIL=${UTIL:-40} PD=${PD:-0.55} \
  jobs/route.sh vs $1 $2 --top ot_hdc_vstream_rt_f12_hw \
  --source rtl/hbm_accel/qwen/fmax/ot_hdc_vstream_rt_f12_h.sv --source rtl/hbm_accel/qwen/fmax/ot_hdc_vstream_f12.sv \
  --source $MD/${M}_bb.v --source rtl/hdc/ot_hdc_fastfp.sv --source rtl/hdc/ot_hdc_fp32_add_lat.sv \
  --source rtl/hdc/ot_hdc_fp32_mul_lat.sv --source rtl/hdc/ot_hdc_prefix.sv --source rtl/hdc/ot_hdc_delay.sv \
  --source rtl/hdc/ot_hdc_sfu.sv --macro-view $M=$MD --macro-place-halo ${HALO:-5} ${HALO:-5}
