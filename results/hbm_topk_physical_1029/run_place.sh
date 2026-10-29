#!/bin/bash
set -euo pipefail
K=/srv/opentallas-scratch2/claude/codex-topk-physical-1029/gen_v5/kits/ot_hbm_idx_topk_link_static_b9b8c72b4dc6-_current_wpipe2
bash "$K/run_kit_hbm.sh" "$K" place 64 8
