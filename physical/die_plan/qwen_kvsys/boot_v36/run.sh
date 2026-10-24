#!/bin/bash
# KV-P6-BOOT 10-23: regenerate the KV boot image on bound depths (drop in v3.7 depths by changing BG / the image stages).
# Inputs: AS = rtl6 GEN case (ot-epyc5:/srv/opentallas-scratch/claude/codex-kvgen-2140/run_main_rtl6/{case_kv/relay_stages.json,
#   case_kv/static_model.json, case_kv/boot_ages.json, kv_flags.env, health_successor.json, rst_regional.json}); BG = bus_groups.
set -eu
AS=${AS:-/home/ubuntu/scratch/kv-p6-1023/boot/asbuilt_rtl6}; S=${S:-/home/ubuntu/scratch/kv-p6-1023/boot}
BG=${BG:-/home/ubuntu/wt/binder3-1023/physical/die_plan/qwen_kvsys/bind/bus_groups_binder2.json.gz}
KST=${KST:-32,32,32,32,32,31,31}   # KV seam KS_RXV,KS_RXP,KS_TXS,KS_TXK,KS_TXB,SK_TXV,SK_TXP = bound d2d_kv<->kvs_attn depths
T=physical/die_plan/qwen_kvsys/boot_v36/kv_boot_v36.py
set -a; . $AS/kv_flags.env; set +a
export OT_KV_RETIRE_SUCCESSOR=$AS/health_successor.json OT_KV_RETIRE_LOGICAL=1
python3 $T prep --rs $AS/relay_stages.json --model $AS/static_model.json --groups $BG --out $S/prep > $S/prep.log
D2D_K_STAGES=$KST D2D_DIE_STAGES=2,2,2,3,2,2/$KST D2D_MU=1 D2D_EMB_WINDOW=595 D2D_ATTN_TX_SHIFT=1 D2D_STATUS_DELAY=213 \
  bash tools/qwen_split/d2d_cal_image_production.sh $S/img_bnd
python3 $T compile --ages $S/prep/die_ages_asbuilt.json --rs $S/prep/relay_stages_asbuilt.json --out $S/cmp_asbuilt
OT_KV_LINK_IMAGE=$S/img_bnd/d2d_cal_image.svh python3 $T compile --ages $S/prep/die_ages_bound_padded.json \
  --rs $S/prep/relay_stages_bound.json --out $S/cmp_bound
