#!/bin/bash
set -euo pipefail
K=/srv/opentallas-scratch2/claude/codex-topk-physical-1029/oneclk_gen/kits/ot_hbm_idx_topk_link_static_9ca71a03635e-_current_wpipe2_oneclk
bash "$K/run_kit_hbm.sh" "$K" synth 64 8
