#!/bin/bash
set -euo pipefail
export CAL_SMOKE_CACHE_ROOT=/srv/opentallas-scratch2/claude/path-qc-tok-1025/cache
cd /srv/opentallas-scratch2/claude/path-qc-tok-1025
python3 /srv/opentallas-scratch2/claude/wt/path-qc-tok-1025/tools/die_plan/bind_smoke.py --die qwen_compute --clusters both \
  --bound /srv/opentallas-scratch2/claude/codex-qc-token-current-0719/plan_canonical_394_start/final --constants /srv/opentallas-scratch2/claude/path-qc-tok-1025/constants_own.json --asbuilt /srv/opentallas-scratch2/claude/codex-qc-token-current-0719/plan_canonical_394_start/final_recipe.json \
  --src-rev 394765394378 --repo /home/ubuntu/OpenTallas --inputs /srv/opentallas-scratch2/claude/path-qc-tok-1025/xt1_inputs --work /srv/opentallas-scratch2/claude/path-qc-tok-1025/both --no-report
