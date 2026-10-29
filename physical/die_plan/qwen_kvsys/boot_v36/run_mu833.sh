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
PV_ARGS=(); [ -z "${OT_KV_PV_RESULT_CALENDAR:-}" ] || PV_ARGS=(--pv-result-calendar "$OT_KV_PV_RESULT_CALENDAR")
python3 $T prep "${PV_ARGS[@]}" --rs "$AS/relay_stages.json" --model "$AS/static_model.json" --groups "$BG" --out "$O/prep" > "$O/prep.log"
EMB=${OT_KV_EMB_WIN_REC:-1627}; HP=12   # one link profile for the pair image AND the compile (link_image_check fails closed)
pair_image() {   # $1 = attention-service pad
  D2D_K_STAGES=$KST D2D_DIE_STAGES=2,2,2,3,2,2/$KST D2D_MU=1 D2D_EMB_WINDOW=$EMB D2D_ROPE=1 D2D_HEAD_PREPARE_EDGES=$HP \
    D2D_ATTN_SERVICE_PAD=$1 D2D_ATTN_TX_SHIFT=1 D2D_STATUS_DELAY=213 \
    bash tools/qwen_split/d2d_cal_image_production.sh "$O/img_bnd" > "$O/img.log" 2>&1
}
pair_image "${OT_KV_ATTN_SERVICE_PAD:-0}"
export OT_KV_EMB_WIN=$EMB OT_KV_ROPE_OVL=1 OT_KV_HEAD_PREP_EDGES=$HP OT_KV_CONTROLLER_CORE=1
# DIE-KV-18: the static RESULT slot follows the attention service need of these ages (worst context, one pad for every
# layer; kv_static_programme.service_slot_pad).  An explicit OT_KV_ATTN_SERVICE_PAD is kept as given; pad 0 = unchanged image.
if [ -z "${OT_KV_ATTN_SERVICE_PAD:-}" ]; then
  OT_KV_LINK_IMAGE=$O/img_bnd/d2d_cal_image.svh python3 $T service-pad --mu --ages "$O/prep/die_ages_bound_padded.json" \
    --rs "$O/prep/relay_stages_bound.json" > "$O/service_pad.json"
  OT_KV_ATTN_SERVICE_PAD=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['pad'])" "$O/service_pad.json")
  [ "$OT_KV_ATTN_SERVICE_PAD" = 0 ] || pair_image "$OT_KV_ATTN_SERVICE_PAD"
fi
export OT_KV_ATTN_SERVICE_PAD
# NO_CONTRACT=1: diagnostic compile without target10 DIECFG (layer/MU/static schedule only; never the image of record)
CONTRACT="--native-contract results/rtl/native_die_cfg_contract_1713/contract.json --capability 1"; [ "${NO_CONTRACT:-0}" = 1 ] && CONTRACT=
export OT_KV_MU_FRAME_F=${OT_KV_MU_FRAME_F:-2} OT_KV_LINK_IMAGE=$O/img_bnd/d2d_cal_image.svh
export -p | grep -E " (OT_KV_|PYTHONDONTWRITEBYTECODE)" > "$O/compile.env"   # token_gate.sh recompiles with exactly this env
/usr/bin/time -f "elapsed %e s maxrss %M KB" python3 $T compile --ages "$O/prep/die_ages_bound_padded.json" \
  --rs "$O/prep/relay_stages_bound.json" --mu $CONTRACT --out "$O/cmp_mu833" > "$O/compile.log" 2>&1
( cd "$O/cmp_mu833" && sha256sum target*.hex boot_bundle.json ../img_bnd/d2d_cal_image.svh > "$O/targets.sha256" )
echo "RECIPE: commit $(git -C "$R" rev-parse --short=10 HEAD) BIND=$B KST=$KST F=$OT_KV_MU_FRAME_F SERVICE_PAD=$OT_KV_ATTN_SERVICE_PAD bash physical/die_plan/qwen_kvsys/boot_v36/run_mu833.sh BIND OUT" > "$O/RECIPE"
tail -3 "$O/compile.log"
