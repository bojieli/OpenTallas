#!/bin/bash
# VISLAYOUT3-KVHEAD SD-GROW kit_rtl wrapper: KV kit_rtl.sh (bind kit-rtl + specialize_serdes_phy) on this form's own strict bind
set -euo pipefail
export KV_BIND_OUT=/srv/opentallas-scratch2/claude/vislayout3-kvhead/sd_grow/bind
export KV_ASBUILT=/srv/opentallas-scratch2/claude/dkv98/asbuilt_rel.json
exec bash physical/die_plan/qwen_kvsys/kit_wave/kit_rtl.sh
