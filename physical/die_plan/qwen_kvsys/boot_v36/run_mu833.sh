#!/bin/bash
# TOK-QK 10-25: KV boot image of record on a KV strict bind, all inputs repo-relative (closure-order rule 3).
#   run_mu833.sh BIND_DIR OUT_DIR      (run from anywhere; the repo root is derived from this file)
# Inputs: BIND_DIR/bus_groups.json(.gz) from tools/die_plan/bind.py (the bind names its own commit in its recipe);
#   as-built rtl6 GEN case = boot_v36/asbuilt_rtl6/ (committed copy of GEN die e33504a6f case_kv: relay_stages, static_model,
#   boot_ages, kv_flags.env minus the GEN-only OT_KV_FAIL_JSON dump path, health_successor, rst_regional);
#   native DIECFG contract = results/rtl/native_die_cfg_contract_1713/contract.json (NRST43/CAP1/AGES1, 96 words).
# Profile: common 833-ps clock (OT_KV_CONTROLLER_CORE=1, 625/625 phase ticks), MU1 471-word layer image, frame F (default 2,
#   frame of record per TOK-QK 20:04; override OT_KV_MU_FRAME_F=3), img44 link profile EMB_WIN 1627 / ROPE_OVL / HEAD_PREP 12.
set -eu
B=$(readlink -f "$1"); O=$(mkdir -p "$2" && readlink -f "$2")
H=$(cd "$(dirname "$0")" && pwd); R=$(cd "$H/../../../.." && pwd); cd "$R"
AS=$O/asbuilt_rtl6; mkdir -p "$AS"
cp "$H/asbuilt_rtl6/kv_flags.env" "$H/asbuilt_rtl6/SOURCE_COMMIT" "$AS/"
for f in "$H"/asbuilt_rtl6/*.json.gz; do zcat "$f" > "$AS/$(basename "${f%.gz}")"; done
BG=$B/bus_groups.json; [ -f "$BG" ] || { zcat "$B/bus_groups.json.gz" > "$O/bus_groups.json"; BG=$O/bus_groups.json; }
KST=${KST:-$(python3 "$H/kst.py" "$BG")}; echo "KST $KST"
T=physical/die_plan/qwen_kvsys/boot_v36/kv_boot_v36.py
set -a; . "$AS/kv_flags.env"; set +a
export OT_KV_RETIRE_SUCCESSOR=$AS/health_successor.json OT_KV_RETIRE_LOGICAL=1 PYTHONDONTWRITEBYTECODE=1
python3 $T prep --rs "$AS/relay_stages.json" --model "$AS/static_model.json" --groups "$BG" --out "$O/prep" > "$O/prep.log"
D2D_K_STAGES=$KST D2D_DIE_STAGES=2,2,2,3,2,2/$KST D2D_MU=1 D2D_EMB_WINDOW=595 D2D_ATTN_TX_SHIFT=1 D2D_STATUS_DELAY=213 \
  bash tools/qwen_split/d2d_cal_image_production.sh "$O/img_bnd" > "$O/img.log" 2>&1
export OT_KV_EMB_WIN=${OT_KV_EMB_WIN_REC:-1627} OT_KV_ROPE_OVL=1 OT_KV_HEAD_PREP_EDGES=12 OT_KV_CONTROLLER_CORE=1
export OT_KV_MU_FRAME_F=${OT_KV_MU_FRAME_F:-2} OT_KV_LINK_IMAGE=$O/img_bnd/d2d_cal_image.svh
/usr/bin/time -f "elapsed %e s maxrss %M KB" python3 $T compile --ages "$O/prep/die_ages_bound_padded.json" \
  --rs "$O/prep/relay_stages_bound.json" --mu --native-contract results/rtl/native_die_cfg_contract_1713/contract.json \
  --capability 1 --out "$O/cmp_mu833" > "$O/compile.log" 2>&1
( cd "$O/cmp_mu833" && sha256sum target*.hex boot_bundle.json ../img_bnd/d2d_cal_image.svh > "$O/targets.sha256" )
echo "RECIPE: commit $(git -C "$R" rev-parse --short=10 HEAD) BIND=$B KST=$KST F=$OT_KV_MU_FRAME_F bash physical/die_plan/qwen_kvsys/boot_v36/run_mu833.sh BIND OUT" > "$O/RECIPE"
tail -3 "$O/compile.log"
