#!/bin/bash
set -euo pipefail
S=/srv/opentallas-scratch/claude/mu-die-qw/dv2f21g5r8bfp
B=/srv/opentallas-scratch/claude/codex-q-faultpins-1021
export ONE_HARD_M=qfd_c_b16_dv,qfd_dv_slice2
export OT_SPLIT_RST_REGION_LAND=1 OT_SPLIT_FWD_RST_SYNC=1
export OT_BIND_VIEW_SELECT=results/arch/qwen_split_compute_1014/bind_view_select.json
export OT_SPLIT_FWD_CLASSES=0 OT_SPLIT_FWD_CLASS_PACK=0 OT_BIND_FWD_CLASSES=0
export OT_QWEN_D2D_IMAGE=rtl/qwen_sys/d2d_static_20261015/d2d_cal_image_mu_ew595_r16.svh
export OT_GEN_SAFETY_FACTS_OUT=$B/pre_gen_safety_facts.json
export IN_FACE= CORE_FEED_XY=17280.0,12096.0 OT_SPLIT_FWD_LAND_EW_MASTERS=qfd_dv_slice2 LC_RINGS=400 REACH_OK=380
export LAND_PLAN=$S/land_plan_bi_chain.json RESET_RELEASE=$S/reset_release_prior_g4try3.json
export OT_SPLIT_FAULT_SOURCE_BITS=1 PYTHONDONTWRITEBYTECODE=1
bash "$B/pre_run.sh" full
