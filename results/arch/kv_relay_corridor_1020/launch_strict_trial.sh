#!/bin/bash
set -euo pipefail
variant=${1:?A|B}
case "$variant" in A) apron=216;; B) apron=302.4;; *) exit 2;; esac
export KVS14R_REF=codex/kv-relay-plan-2210 KVS14R_TAG=codexcp$variant
export OT_KV_STRICT_CHAIN_ONLY=1 OT_DIE_SIGNAL_TOP_LAYER=M8 OT_ITERS=5 OT_STOP=grt
export KVS14R_EXTRA="OT_KV_MU=1 OT_KV_BOOT_AGES=1 OT_KV_DCAL_BC=1 OT_KV_DCAL_BC4=1 OT_KV_FUNC_OPENS=1 OT_KV_SCHED_STRICT=1 OT_KV_PARAMETER_PROFILES=results/arch/kv_integ13_1020/profiles.json OT_KV_ATTN_R16=1 OT_KV_FACE_LAND=astk_rly_296,kvs_attn OT_KV_HOST_OBS=1 OT_KV_HOST_OBSX=1 OT_KV_KPV_LK=1 OT_KV_D2D_PINS=1 OT_KV_D2D_FIT=1 OT_KV_EMB_WEST=1 OT_KV_RLY_FINE=1 OT_KV_PVFIN_FLOOR=1 OT_KV_AHUB_OFS=-36,-36,-34,-35:-7 OT_KV_AHUB_PAD=1 OT_KV_SEAM_PIN=1 OT_KV_HROOT_LAND=1 OT_KV_ATTN_WEST_HOST=1 OT_KV_EQ_ROW_BANK=1 OT_KV_D2D_ENDPOINT_FIRST=1 OT_KV_D2D_APRON_UM=$apron"
unset OT_KV_ATTN_DXY OT_KV_ATTN_AT_D2D OT_GEN_SAFETY OT_BIND_DIAGNOSTIC OT_PG_OPEN_DIAG OT_KV_PARAM_DIAG
M=/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git
if [ ! -d "$M" ]; then
 mkdir -p "$(dirname "$M")"
 git clone -q --mirror https://github.com/bojieli/OpenTallas "$M"
fi
git -C "$M" fetch -q https://github.com/bojieli/OpenTallas codex/kv-relay-plan-2210
L=/srv/opentallas-scratch/claude/codex-kv-relay-plan-2210-launch-$variant
mkdir -p "$L"
git -C "$M" show c641da67d:tools/qwen_kv_die/chain/kvs14r.sh > "$L/kvs14r.sh"
exec bash "$L/kvs14r.sh" c641da67d
